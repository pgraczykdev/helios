from unittest.mock import MagicMock
import pytest

from helios.db.connector import DatabaseConnector
from helios.elt.transform import OracleTransformer, TransformationStatus
    

@pytest.fixture
def mock_db():
    """Fixture providing mocked DatabaseConnector, connection, and cursor."""
    mock_connector = MagicMock(spec=DatabaseConnector)
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connector.acquire_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    return mock_connector, mock_cursor

def test_oracletransformer_success(mock_db):
    """Verify successful transformation and OUT variable mapping."""
    connector, cursor = mock_db
    transformer = OracleTransformer(connector=connector)

    # Setup mock return values for cursor.var instances
    mock_status = MagicMock()
    mock_status.getvalue.return_value = "SUCCESS"

    mock_processed = MagicMock()
    mock_processed.getvalue.return_value = 7

    mock_merged = MagicMock()
    mock_merged.getvalue.return_value = 7

    mock_seconds = MagicMock()
    mock_seconds.getvalue.return_value = 0.45

    mock_error = MagicMock()
    mock_error.getvalue.return_value = None

    cursor.var.side_effect = [
        mock_status,
        mock_processed,
        mock_merged,
        mock_seconds,
        mock_error,
    ]

    result = transformer.transform(commit=True)

    assert result.status == TransformationStatus.SUCCESS
    assert result.rows_processed == 7
    assert result.rows_merged == 7
    assert result.execution_seconds == 0.45
    assert result.error_message is None

    cursor.execute.assert_called_once()
    call_kwargs = cursor.execute.call_args[1]
    assert call_kwargs["pi_commit"] == True


def test_transformer_commit_false(mock_db):
    """Verify commit=False passes pi_commit=0 to PL/SQL."""
    connector, cursor = mock_db
    transformer = OracleTransformer(connector=connector)

    mock_var = MagicMock()
    mock_var.getvalue.return_value = "SUCCESS"
    cursor.var.return_value = mock_var

    transformer.transform(commit=False)

    call_kwargs = cursor.execute.call_args[1]
    assert call_kwargs["pi_commit"] == False


def test_transformer_handles_exception(mock_db):
    """Verify database exceptions are safely caught and returned as ERROR status."""
    connector, cursor = mock_db
    transformer = OracleTransformer(connector=connector)

    cursor.execute.side_effect = Exception("ORA-03113: end-of-file on communication channel")

    result = transformer.transform(commit=True)

    assert result.status == TransformationStatus.ERROR
    assert result.rows_processed == 0
    assert result.rows_merged == 0
    assert "ORA-03113" in result.error_message