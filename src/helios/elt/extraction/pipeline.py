from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from helios.client.ember_client import EmberClient
from helios.elt.extraction.lake import BronzeDataLake, JsonBronzeDataLake
from helios.elt.extraction.watermark import read_watermark, save_watermark, normalize_date

import logging

load_dotenv()

logger = logging.getLogger(__name__)


class Dataset(StrEnum):
    """Supported datasets for extraction."""
    CARBON_INTENSITY = "carbon-intensity"
    ELECTRICITY_DEMAND = "electricity-demand"
    POWER_SECTOR_EMISSIONS = "power-sector-emissions"
    ELECTRICITY_GENERATION = "electricity-generation" 
    INSTALLED_CAPACITY = "installed-capacity"



class TemporalResolution(StrEnum):
    """Supported temporal resolutions for datasets."""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ExtractionStatus(StrEnum):
    """Outcome status of an extraction job."""
    SUCCESS = "SUCCESS"
    UP_TO_DATE = "UP_TO_DATE"
    NO_DATA = "NO_DATA"
    FAILED = "FAILED"


@dataclass
class ExtractionResult:
    """Summary of the pipeline extraction run."""
    dataset: str
    temporal_resolution: str
    status: ExtractionStatus
    records_count: int = 0
    previous_watermark: str | None = None
    new_watermark: str | None = None
    start_date: str | None = None
    saved_file: Path | None = None
    error_message: str | None = None


class ExtractionPipeline:
    """Orchestrates watermark-aware data extraction from Ember API into Bronze Lake."""

    def __init__(self, client: EmberClient | None = None, lake: BronzeDataLake | None = None) -> None:
        """Initialize the extraction pipeline with optional client and lake dependencies."""
        self.client = client or EmberClient()
        self.lake = lake or JsonBronzeDataLake()

    def _extract_single(
        self,
        dataset: str,
        temporal_resolution: str,
        params: dict[str, Any],
        tag: str | None,
    ) -> tuple[list[dict[str, Any]], Path | None]:
        """Fetch records from API and save raw payload to Bronze Lake."""
        payload = self.client._get(endpoint=f"/v1/{dataset}/{temporal_resolution}", params=params)
        records = payload.get("data", [])

        saved_file = (
            self.lake.save_raw_data(
                data=records,
                dataset=dataset,
                temporal_resolution=temporal_resolution,
                tag=tag,
            )
            if records
            else None
        )
        return records, saved_file

    def _run_batches(
        self,
        dataset: str,
        temporal_resolution: str,
        prev_watermark: str | None,
        latest_available: str | None,
    ) -> ExtractionResult:
        """Fetch data in yearly batches to prevent API server timeouts."""
        default_start_date = "2000-01-01"
        partition_dir = self.lake.get_dataset_dir(dataset=dataset, temporal_resolution=temporal_resolution)
        start_date = prev_watermark or default_start_date
        end_date = latest_available or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        start_yr, end_yr = int(start_date[:4]), int(end_date[:4])
        total_records, last_saved, current_watermark = 0, None, prev_watermark

        for year in range(start_yr, end_yr + 1):
            b_start = year if temporal_resolution == TemporalResolution.YEARLY else f"{year}-01-01"
            b_end = year if temporal_resolution == TemporalResolution.YEARLY else f"{year}-12-31"

            params: dict[str, Any] = {"start_date": b_start, "end_date": b_end}
            logger.info(f"Batch [{year}/{end_yr}] Fetching {temporal_resolution} data: {b_start} to {b_end}")
            try:
                records, saved = self._extract_single(
                    dataset=dataset,
                    temporal_resolution=temporal_resolution,
                    params=params,
                    tag=f"batch_{year}",
                )
                if records:
                    total_records += len(records)
                    last_saved = saved
                    extracted_dates = [normalize_date(date_str=r["date"]) for r in records if r.get("date")]
                    if extracted_dates:
                        batch_max = max(extracted_dates)
                        current_watermark = max(current_watermark, batch_max) if current_watermark else batch_max
                        save_watermark(
                            target_dir=partition_dir,
                            watermark=current_watermark,
                            dataset=dataset,
                            temporal_resolution=temporal_resolution,
                            records_count=total_records,
                        )
                        
                    logger.info(f"Batch [{year}] Saved {len(records)} records. Watermark -> {current_watermark}")
            except Exception as exc:
                logger.exception(f"Batch [{year}] failed: {exc}")
                return ExtractionResult(
                    dataset=dataset,
                    temporal_resolution=temporal_resolution,
                    status=ExtractionStatus.FAILED,
                    records_count=total_records,
                    previous_watermark=prev_watermark,
                    new_watermark=current_watermark,
                    saved_file=last_saved,
                    error_message=str(exc),
                )
            
        if latest_available and total_records > 0:
            current_watermark = latest_available
            save_watermark(
                target_dir=partition_dir,
                watermark=current_watermark,
                dataset=dataset,
                temporal_resolution=temporal_resolution,
                records_count=total_records,
            )

        status = ExtractionStatus.SUCCESS if total_records > 0 else ExtractionStatus.NO_DATA
        return ExtractionResult(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            status=status,
            records_count=total_records,
            previous_watermark=prev_watermark,
            new_watermark=current_watermark,
            saved_file=last_saved,
        )
    

    def run(
        self,
        dataset: str,
        temporal_resolution: str,
        force: bool = False,
    ) -> ExtractionResult:
        prev_watermark: str | None = None
        try:
            partition_dir = self.lake.get_dataset_dir(dataset=dataset, temporal_resolution=temporal_resolution)
            prev_watermark = read_watermark(target_dir=partition_dir)
            logger.info(f"Starting extraction for '{dataset}/{temporal_resolution}'. Current watermark: {prev_watermark}")

            latest_available_date_raw = self.client.get_latest_available_date(
                dataset=dataset,
                temporal_resolution=temporal_resolution,
            )
            latest_available = normalize_date(date_str=latest_available_date_raw) if latest_available_date_raw else None
            logger.info("Latest date reported by Ember API: %s", latest_available)

            if not force and prev_watermark and latest_available and (prev_watermark >= latest_available):
                logger.info(f"Data for '{dataset}/{temporal_resolution}' is already up to date ({prev_watermark}).")
                return ExtractionResult(
                    dataset=dataset,
                    temporal_resolution=temporal_resolution,
                    status=ExtractionStatus.UP_TO_DATE,
                    previous_watermark=prev_watermark,
                    new_watermark=prev_watermark,
                )
            else:
                logger.info(f"Proceeding with extraction for '{dataset}/{temporal_resolution}'.")
                return self._run_batches(
                    dataset=dataset,
                    temporal_resolution=temporal_resolution,
                    prev_watermark=prev_watermark,
                    latest_available=latest_available,
                )
        except Exception as exc:
            logger.exception(f"Extraction for '{dataset}/{temporal_resolution}' failed: {exc}")
            return ExtractionResult(
                dataset=dataset,
                temporal_resolution=temporal_resolution,
                status=ExtractionStatus.FAILED,
                previous_watermark=prev_watermark,
                new_watermark=prev_watermark,
                error_message=str(exc),
            )

    

