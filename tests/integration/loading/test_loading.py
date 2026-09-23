import os
from dotenv import load_dotenv
import pytest

from helios.db import OracleDatabaseConnector
from helios.elt.extraction.pipeline import Dataset, TemporalResolution
from helios.elt.loading import StagingLoader, LoadStatus

load_dotenv()


def test_staging_loader_generation_integration():
    """Verify end-to-end loading of electricity generation records into Oracle STG."""
    connector = OracleDatabaseConnector(user=os.getenv("HELIOS_STAGING_USER"), password=os.getenv("HELIOS_STAGING_PASSWORD"))
    loader = StagingLoader(database_connector=connector)

    test_source_file = "test_integration_generation_sample.json"

    sample_data = [
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
    ]

    try:
        result = loader.load(
            data=sample_data,
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=TemporalResolution.YEARLY,
            source_file=test_source_file,
        )

        assert result.status == LoadStatus.SUCCESS
        assert result.rows_loaded == 2
        assert result.target_table == "stg_ember_generation"


        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT entity, series, generation_twh, stg_status, is_aggregate_entity "
                    "FROM stg_ember_generation WHERE source_file = :source_file ORDER BY entity",
                    source_file=test_source_file,
                )
                rows = cursor.fetchall()
                assert len(rows) == 2

                assert rows[0][0] == "Germany"
                assert rows[0][1] == "Wind"
                assert float(rows[0][2]) == 139.5
                assert rows[0][3] == "NEW"  
                assert rows[0][4] == 0     

        second_result = loader.load(
            data=sample_data,
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=TemporalResolution.YEARLY,
            source_file=test_source_file,
        )
        assert second_result.status == LoadStatus.SUCCESS

        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM stg_ember_generation WHERE source_file = :source_file",
                    source_file=test_source_file,
                )
                count = cursor.fetchone()[0]
                assert count == 2  # Nadal dokładnie 2, brak duplikatów!

    finally:
        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM stg_ember_generation WHERE source_file = :source_file",
                    source_file=test_source_file,
                )
        connector.close_pool()