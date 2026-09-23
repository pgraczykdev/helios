from unittest.mock import MagicMock
import pytest

from helios.db import DatabaseConnector
from helios.elt.extraction.pipeline import Dataset, TemporalResolution
from helios.elt.loading import StagingLoader, LoadStatus
from helios.elt.loading.mapper import LoadingMapperFactory, GenerationMapper


@pytest.fixture
def mock_db():
    """Fixture providing mocked DatabaseConnector, connection, and cursor."""
    mock_connector = MagicMock(spec=DatabaseConnector)
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connector.acquire_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    return mock_connector, mock_cursor


def test_staging_loader_success(mock_db):
    """Verify successful batch load and idempotent DELETE."""
    connector, cursor = mock_db
    loader = StagingLoader(database_connector=connector)

    sample_data = [
        {"entity": "Poland", "entity_code": "POL", "date": "2023", "series": "Solar", "generation_twh": 10.0}
    ]

    result = loader.load(
        data=sample_data,
        dataset=Dataset.ELECTRICITY_GENERATION,
        temporal_resolution=TemporalResolution.YEARLY,
        source_file="test_sample.json",
    )

    assert result.status == LoadStatus.SUCCESS
    assert result.rows_loaded == 1
    assert result.target_table == "stg_ember_generation"

    cursor.execute.assert_called_once()
    delete_call_args = cursor.execute.call_args
    assert "DELETE FROM stg_ember_generation" in delete_call_args[0][0]
    assert delete_call_args[1]["source_file"] == "test_sample.json"

    cursor.executemany.assert_called_once()
    sql, batch = cursor.executemany.call_args[0]
    assert "INSERT INTO stg_ember_generation" in sql
    assert len(batch) == 1
    assert batch[0]["entity"] == "Poland"
    assert batch[0]["source_file"] == "test_sample.json"


def test_staging_loader_empty_data_skips(mock_db):
    """If data is empty, loading is skipped without touching the database."""
    connector, cursor = mock_db
    loader = StagingLoader(database_connector=connector)

    result = loader.load(
        data=[],
        dataset=Dataset.ELECTRICITY_GENERATION,
        temporal_resolution=TemporalResolution.YEARLY,
        source_file="empty.json",
    )

    assert result.status == LoadStatus.SKIPPED
    assert result.rows_loaded == 0
    connector.acquire_connection.assert_not_called()


def test_staging_loader_database_error_handled(mock_db):
    """Database exceptions should be captured in LoadingResult."""
    connector, cursor = mock_db
    cursor.executemany.side_effect = RuntimeError("ORA-00001: Unique constraint violated")

    loader = StagingLoader(database_connector=connector)

    result = loader.load(
        data=[{"entity": "Poland"}],
        dataset=Dataset.ELECTRICITY_GENERATION,
        temporal_resolution=TemporalResolution.YEARLY,
        source_file="fail.json",
    )

    assert result.status == LoadStatus.FAILED
    assert result.rows_loaded == 0
    assert "ORA-00001" in result.error_message


def test_mapper_boolean_and_date_transformation():
    """Verify that GenerationMapper correctly maps date to raw_date and booleans to integers."""
    mapper = LoadingMapperFactory.get_mapper(dataset=Dataset.ELECTRICITY_GENERATION)

    raw_record = {
        "entity": "Germany",
        "date": "2023-05",
        "is_aggregate_entity": False,
        "is_aggregate_series": True,
    }

    mapped = mapper.map_row(
        record=raw_record,
        source_file="sample.json",
        temporal_resolution=TemporalResolution.MONTHLY,
    )

    assert mapped["raw_date"] == "2023-05"
    assert mapped["is_aggregate_entity"] == 0
    assert mapped["is_aggregate_series"] == 1
    assert mapped["temporal_resolution"] == "monthly"