import json
import logging
import os
from pathlib import Path

from helios.db.connector import OracleDatabaseConnector
from helios.elt.extraction.lake import JsonBronzeDataLake
from helios.elt.extraction.pipeline import Dataset, TemporalResolution
from helios.elt.load.loader import LoadStatus, LoadingResult, StagingLoader
from helios.elt.load.mapper import LoadingMapperFactory

logger = logging.getLogger(__name__)


def load_dataset_to_staging(
    dataset: Dataset,
    temporal_resolution: TemporalResolution,
) -> LoadingResult:
    """Load JSON files from Bronze Lake into the corresponding staging table."""
    mapper = LoadingMapperFactory.get_mapper(dataset=str(dataset))
    target_table = mapper.target_table

    lake = JsonBronzeDataLake()
    prefix = Path(lake.get_dataset_prefix(dataset=str(dataset), temporal_resolution=str(temporal_resolution)))

    if not prefix.exists():
        logger.warning("Bronze Lake directory does not exist: %s", prefix)
        return LoadingResult(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            target_table=target_table,
            source_file="",
            rows_loaded=0,
            status=LoadStatus.SKIPPED,
        )

    json_files = sorted(prefix.glob("*.json"))
    if not json_files:
        logger.warning("No JSON files found in Bronze Lake prefix: %s", prefix)
        return LoadingResult(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            target_table=target_table,
            source_file="",
            rows_loaded=0,
            status=LoadStatus.SKIPPED,
        )

    connector = OracleDatabaseConnector(
        user=os.getenv("HELIOS_STG_USER"),
        password=os.getenv("HELIOS_STG_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
        wallet_dir=os.getenv("ORACLE_WALLET_DIR"),
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD"),
    )
    loader = StagingLoader(database_connector=connector)
    total_loaded = 0

    try:
        for file_path in json_files:
            with open(file=file_path, mode="r", encoding="utf-8") as f:
                records = json.load(fp=f)

            if isinstance(records, list) and records:
                res = loader.load(
                    data=records,
                    dataset=dataset,
                    temporal_resolution=temporal_resolution,
                    source_file=file_path.name,
                )
                if res.status == LoadStatus.FAILED:
                    logger.error("Failed loading %s into %s: %s", file_path.name, target_table, res.error_message)
                    return res
                total_loaded += res.rows_loaded
                logger.info("Loaded %d rows from %s into staging.", res.rows_loaded, file_path.name)
    except Exception as exc:
        logger.error("Unexpected error loading %s into staging: %s", dataset, exc)
        return LoadingResult(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            target_table=target_table,
            source_file="",
            rows_loaded=total_loaded,
            status=LoadStatus.FAILED,
            error_message=str(exc),
        )
    finally:
        connector.close_pool()

    source_summary = ", ".join(f.name for f in json_files) if len(json_files) > 1 else json_files[0].name
    return LoadingResult(
        dataset=dataset,
        temporal_resolution=temporal_resolution,
        target_table=target_table,
        source_file=source_summary,
        rows_loaded=total_loaded,
        status=LoadStatus.SUCCESS,
    )


def load_electricity_generation(
    temporal_resolution: TemporalResolution = TemporalResolution.YEARLY,
) -> LoadingResult:
    """Load electricity generation dataset into staging."""
    return load_dataset_to_staging(
        dataset=Dataset.ELECTRICITY_GENERATION,
        temporal_resolution=temporal_resolution,
    )


def load_installed_capacity(
    temporal_resolution: TemporalResolution = TemporalResolution.MONTHLY,
) -> LoadingResult:
    """Load installed capacity dataset into staging."""
    return load_dataset_to_staging(
        dataset=Dataset.INSTALLED_CAPACITY,
        temporal_resolution=temporal_resolution,
    )


def load_carbon_intensity(
    temporal_resolution: TemporalResolution = TemporalResolution.YEARLY,
) -> LoadingResult:
    """Load carbon intensity dataset into staging."""
    return load_dataset_to_staging(
        dataset=Dataset.CARBON_INTENSITY,
        temporal_resolution=temporal_resolution,
    )


def load_electricity_demand(
    temporal_resolution: TemporalResolution = TemporalResolution.YEARLY,
) -> LoadingResult:
    """Load electricity demand dataset into staging."""
    return load_dataset_to_staging(
        dataset=Dataset.ELECTRICITY_DEMAND,
        temporal_resolution=temporal_resolution,
    )


def load_power_sector_emissions(
    temporal_resolution: TemporalResolution = TemporalResolution.YEARLY,
) -> LoadingResult:
    """Load power sector emissions dataset into staging."""
    return load_dataset_to_staging(
        dataset=Dataset.POWER_SECTOR_EMISSIONS,
        temporal_resolution=temporal_resolution,
    )