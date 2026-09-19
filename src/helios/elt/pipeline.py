from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import argparse
import logging
import sys

from dotenv import load_dotenv

# Ensure src/ directory is in sys.path when script is executed directly
_SRC_DIR = Path(__file__).resolve().parents[2]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from helios.client.ember_client import EmberClient
from helios.elt.lake import BronzeDataLake
from helios.elt.watermark import clean_watermark, read_watermark, save_watermark

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)


class ExtractionStatus(str, Enum):
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
        self.lake = lake or BronzeDataLake()

    def _extract_single(self, dataset: str, temporal_resolution: str, params: dict[str, Any], tag: str | None) -> tuple[list[dict[str, Any]], Path | None]:
        """Fetch records from API and save raw payload to Bronze Lake."""
        if dataset == "electricity-generation":
            records = self.client.get_electricity_generation(temporal_resolution, params=params)
        else:
            payload = self.client._get(f"/v1/{dataset}/{temporal_resolution}", params=params)
            records = payload.get("data", [])

        saved_file = self.lake.save_raw_payload(records, dataset, temporal_resolution, tag=tag) if records else None
        return records, saved_file

    def _run_monthly_batches(self, dataset: str, prev_watermark: str | None, latest_available: str | None, additional_params: dict[str, Any] | None) -> ExtractionResult:
        """Fetch monthly data in yearly batches to prevent API server timeouts."""
        partition_dir = self.lake.get_dataset_dir(dataset, "monthly")
        start_date = (additional_params or {}).get("start_date") or prev_watermark or "2000-01-01"
        end_date = latest_available or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        start_yr, end_yr = int(start_date[:4]), int(end_date[:4])
        total_records, last_saved, current_watermark = 0, None, prev_watermark

        for yr in range(start_yr, end_yr + 1):
            b_start = start_date if yr == start_yr else f"{yr}-01-01"
            b_end = end_date if yr == end_yr else f"{yr}-12-31"

            params: dict[str, Any] = {"start_date": b_start, "end_date": b_end}
            if additional_params:
                params.update({k: v for k, v in additional_params.items() if k not in ("start_date", "end_date")})

            logger.info("Batch [%d/%d] Fetching monthly data: %s to %s", yr, end_yr, b_start, b_end)
            try:
                records, saved = self._extract_single(dataset, "monthly", params, tag=f"batch_{yr}")
                if records:
                    total_records += len(records)
                    last_saved = saved
                    extracted_dates = [clean_watermark(r["date"]) for r in records if "date" in r and r["date"] is not None]
                    if extracted_dates:
                        current_watermark = max(extracted_dates)
                        save_watermark(partition_dir, 
                                       current_watermark, 
                                       dataset=dataset, 
                                       temporal_resolution="monthly", 
                                       records_count=len(records))
                        
                    logger.info("Batch [%d] Saved %d records. Watermark -> %s", yr, len(records), current_watermark)
            except Exception as exc:
                logger.exception("Batch [%d] failed: %s", yr, exc)
                return ExtractionResult(dataset=dataset, 
                                        temporal_resolution="monthly", 
                                        status=ExtractionStatus.FAILED, 
                                        records_count=total_records, 
                                        previous_watermark=prev_watermark, 
                                        new_watermark=current_watermark, 
                                        saved_file=last_saved, 
                                        error_message=str(exc))

        status = ExtractionStatus.SUCCESS if total_records > 0 else ExtractionStatus.NO_DATA
        return ExtractionResult(dataset=dataset, temporal_resolution="monthly", status=status, records_count=total_records, previous_watermark=prev_watermark, new_watermark=current_watermark, saved_file=last_saved)

    def _run_single_batch(self, 
                        dataset: str, 
                        temporal_resolution: str, prev_watermark: str | None, 
                        latest_available: str | None,
                        additional_params: dict[str, Any] | None) -> ExtractionResult:
        """Fetch dataset in a single request (standard for yearly resolution)."""
        partition_dir = self.lake.get_dataset_dir(dataset, temporal_resolution)
        params: dict[str, Any] = {}
        if prev_watermark:
            params["start_date"] = prev_watermark
        if additional_params:
            params.update(additional_params)

        try:
            logger.info("Fetching '%s/%s' with params: %s", dataset, temporal_resolution, params)
            tag = f"incremental_{prev_watermark}" if prev_watermark else "full"
            records, saved_file = self._extract_single(dataset, temporal_resolution, params, tag=tag)

            if not records:
                return ExtractionResult(
                    dataset=dataset, 
                    temporal_resolution=temporal_resolution, 
                    status=ExtractionStatus.NO_DATA, 
                    previous_watermark=prev_watermark, 
                    new_watermark=prev_watermark)

            extracted_dates = [clean_watermark(r["date"]) for r in records if "date" in r and r["date"] is not None]
            new_watermark = max(extracted_dates) if extracted_dates else latest_available

            if new_watermark:
                save_watermark(partition_dir, new_watermark, dataset=dataset, temporal_resolution=temporal_resolution, records_count=len(records))

            return ExtractionResult(dataset=dataset, 
                                    temporal_resolution=temporal_resolution, 
                                    status=ExtractionStatus.SUCCESS, 
                                    records_count=len(records), 
                                    previous_watermark=prev_watermark, 
                                    new_watermark=new_watermark,
                                    saved_file=saved_file)
        
        except Exception as exc:
            logger.exception("Extraction failed for '%s/%s': %s", dataset, temporal_resolution, exc)
            return ExtractionResult(
                dataset=dataset, 
                temporal_resolution=temporal_resolution, 
                status=ExtractionStatus.FAILED, 
                previous_watermark=prev_watermark, 
                error_message=str(exc)
            )

    def run(self, dataset: str = "electricity-generation", temporal_resolution: str = "yearly", force: bool = False, additional_params: dict[str, Any] | None = None) -> ExtractionResult:
        """Execute watermark-aware extraction delegating to batch or single-request strategy."""
        if dataset in ("yearly", "monthly"):
            temporal_resolution, dataset = dataset, "electricity-generation"

        partition_dir = self.lake.get_dataset_dir(dataset, temporal_resolution)
        prev_watermark = read_watermark(partition_dir)
        logger.info("Starting extraction for '%s/%s'. Current watermark: %s", dataset, temporal_resolution, prev_watermark)

        latest_available_raw = self.client.get_latest_available_date(dataset, temporal_resolution)
        latest_available = clean_watermark(latest_available_raw) if latest_available_raw else None
        logger.info("Latest date reported by Ember API: %s", latest_available)

        if prev_watermark and latest_available and not force and prev_watermark >= latest_available:
            logger.info("Data for '%s/%s' is already up to date (%s).", dataset, temporal_resolution, prev_watermark)
            return ExtractionResult(
                dataset=dataset, 
                temporal_resolution=temporal_resolution, 
                status=ExtractionStatus.UP_TO_DATE, 
                previous_watermark=prev_watermark, 
                new_watermark=prev_watermark
            )

        if temporal_resolution == "monthly":
            return self._run_monthly_batches(dataset, prev_watermark, latest_available, additional_params)
        return self._run_single_batch(dataset, temporal_resolution, prev_watermark, latest_available, additional_params)


def run_pipeline(dataset: str = "electricity-generation", 
                 temporal_resolution: str = "yearly", 
                 force: bool = False, 
                 additional_params: dict[str, Any] | None = None, 
                 client: EmberClient | None = None, 
                 lake: BronzeDataLake | None = None) -> ExtractionResult:
    """Convenience function to run the extraction pipeline."""
    pipeline = ExtractionPipeline(client=client, lake=lake)
    return pipeline.run(dataset=dataset, 
                        temporal_resolution=temporal_resolution, 
                        force=force, 
                        additional_params=additional_params)


if __name__ == "__main__":
    run_pipeline(temporal_resolution="monthly")