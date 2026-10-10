from unittest.mock import MagicMock, patch

from helios.elt.load.loader import LoadStatus, LoadingResult
from helios.elt.transform.tasks import transform_dwh_core
from helios.elt.transform.transformer import TransformationResult, TransformationStatus


def test_transform_dwh_core_success():
    """Verify transform_dwh_core executes OracleTransformer and returns TransformationResult."""
    with patch("helios.elt.transform.tasks.OracleDatabaseConnector") as mock_conn_cls, \
         patch("helios.elt.transform.tasks.OracleTransformer") as mock_tf_cls:

        mock_conn = MagicMock()
        mock_conn_cls.return_value = mock_conn

        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = TransformationResult(
            status=TransformationStatus.SUCCESS,
            rows_processed=100,
            rows_merged=100,
            execution_seconds=1.23,
            error_message=None,
        )
        mock_tf_cls.return_value = mock_transformer

        mock_load_results = [
            MagicMock(spec=LoadingResult, target_table="stg_ember_generation", rows_loaded=50, status=LoadStatus.SUCCESS)
        ]

        result = transform_dwh_core(load_results=mock_load_results)

        assert isinstance(result, TransformationResult)
        assert result.status == TransformationStatus.SUCCESS
        assert result.rows_processed == 100
        assert result.rows_merged == 100
        assert result.execution_seconds == 1.23
        assert result.error_message is None
        mock_conn.close_pool.assert_called_once()
