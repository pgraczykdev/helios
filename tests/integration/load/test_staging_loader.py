import os
from typing import Any
from dotenv import load_dotenv
import pytest

from helios.db import OracleDatabaseConnector
from helios.elt.extraction.pipeline import Dataset, TemporalResolution
from helios.elt.load import LoadStatus, StagingLoader

load_dotenv()

stg_user = os.getenv("HELIOS_STAGING_USER")
stg_password = os.getenv("HELIOS_STAGING_PASSWORD")
oracle_dsn = os.getenv("ORACLE_DSN")

db_configured = bool(stg_user and stg_password and oracle_dsn)
pytestmark = pytest.mark.skipif(
    not db_configured,
    reason="Oracle STG DB credentials not set in environment.",
)


@pytest.mark.parametrize(
    "dataset, temporal_resolution, target_table, sample_data",
    [
        (
            Dataset.ELECTRICITY_GENERATION,
            TemporalResolution.YEARLY,
            "stg_ember_generation",
            [
                {
                    "entity": "Poland",
                    "entity_code": "POL",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "series": "Solar",
                    "is_aggregate_series": False,
                    "generation_twh": 11.25,
                    "share_of_generation_pct": 6.8,
                },
                {
                    "entity": "Germany",
                    "entity_code": "DEU",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "series": "Wind",
                    "is_aggregate_series": False,
                    "generation_twh": 139.5,
                    "share_of_generation_pct": 27.4,
                },
            ],
        ),
        (
            Dataset.INSTALLED_CAPACITY,
            TemporalResolution.MONTHLY,
            "stg_ember_capacity",
            [
                {
                    "entity": "Poland",
                    "entity_code": "POL",
                    "is_aggregate_entity": False,
                    "date": "2024-01-01",
                    "series": "Solar",
                    "is_aggregate_series": False,
                    "capacity_gw": 17.05,
                    "capacity_w_per_capita": 452.1,
                },
                {
                    "entity": "Germany",
                    "entity_code": "DEU",
                    "is_aggregate_entity": False,
                    "date": "2024-01-01",
                    "series": "Wind",
                    "is_aggregate_series": False,
                    "capacity_gw": 69.5,
                    "capacity_w_per_capita": 824.0,
                },
            ],
        ),
        (
            Dataset.CARBON_INTENSITY,
            TemporalResolution.YEARLY,
            "stg_ember_carbon_intensity",
            [
                {
                    "entity": "Poland",
                    "entity_code": "POL",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "emissions_intensity_gco2_per_kwh": 662.0,
                },
                {
                    "entity": "Germany",
                    "entity_code": "DEU",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "emissions_intensity_gco2_per_kwh": 381.0,
                },
            ],
        ),
        (
            Dataset.ELECTRICITY_DEMAND,
            TemporalResolution.YEARLY,
            "stg_ember_demand",
            [
                {
                    "entity": "Poland",
                    "entity_code": "POL",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "demand_twh": 167.5,
                    "demand_mwh_per_capita": 4.45,
                },
                {
                    "entity": "Germany",
                    "entity_code": "DEU",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "demand_twh": 507.2,
                    "demand_mwh_per_capita": 6.02,
                },
            ],
        ),
        (
            Dataset.POWER_SECTOR_EMISSIONS,
            TemporalResolution.YEARLY,
            "stg_ember_emissions",
            [
                {
                    "entity": "Poland",
                    "entity_code": "POL",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "series": "Coal",
                    "is_aggregate_series": False,
                    "emissions_mtco2": 95.4,
                    "share_of_emissions_pct": 85.2,
                },
                {
                    "entity": "Germany",
                    "entity_code": "DEU",
                    "is_aggregate_entity": False,
                    "date": "2023",
                    "series": "Coal",
                    "is_aggregate_series": False,
                    "emissions_mtco2": 145.1,
                    "share_of_emissions_pct": 74.0,
                },
            ],
        ),
    ],
)
def test_staging_loader_integration(
    dataset: Dataset,
    temporal_resolution: TemporalResolution,
    target_table: str,
    sample_data: list[dict[str, Any]],
) -> None:
    """Verify idempotent batch loading of all 5 datasets into Oracle STG_EMBER_* tables."""
    connector = OracleDatabaseConnector(
        user=stg_user,
        password=stg_password,
    )
    loader = StagingLoader(database_connector=connector)
    test_source_file = f"test_integration_{dataset}_sample.json"

    try:
        # 1. First load
        result = loader.load(
            data=sample_data,
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            source_file=test_source_file,
        )

        assert result.status == LoadStatus.SUCCESS
        assert result.rows_loaded == 2
        assert result.target_table == target_table

        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT entity, stg_status, is_aggregate_entity "
                    f"FROM {target_table} WHERE source_file = :source_file ORDER BY entity",
                    source_file=test_source_file,
                )
                rows = cursor.fetchall()
                assert len(rows) == 2
                assert rows[0][0] == "Germany"
                assert rows[0][1] == "NEW"
                assert rows[0][2] == 0

        # 2. Second load (idempotency check: DELETE + INSERT for same source_file)
        second_result = loader.load(
            data=sample_data,
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            source_file=test_source_file,
        )
        assert second_result.status == LoadStatus.SUCCESS

        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(*) FROM {target_table} WHERE source_file = :source_file",
                    source_file=test_source_file,
                )
                count = cursor.fetchone()[0]
                assert count == 2

    finally:
        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {target_table} WHERE source_file = :source_file",
                    source_file=test_source_file,
                )
        connector.close_pool()
