import os
from dotenv import load_dotenv
import pytest

from helios.db import DatabaseConnectorFactory, DatabaseSchema
from helios.elt.transform import OracleTransformer, TransformationStatus

load_dotenv()

db_core_user = os.getenv("HELIOS_CORE_USER")
db_core_password = os.getenv("HELIOS_CORE_PASSWORD")
oracle_dsn = os.getenv("ORACLE_DSN")

db_configured = bool(db_core_user and db_core_password and oracle_dsn)
pytestmark = pytest.mark.skipif(not db_configured, reason="Oracle CORE DB credentials not set in environment.")


def test_oracle_transformer_integration() -> None:
    """Live integration test: execute PKG_EMBER_ELT.f_load_all on Oracle ADW."""
    connector = DatabaseConnectorFactory.create_connector(database_schema=DatabaseSchema.CORE)
    transformer = OracleTransformer(connector=connector)

    try:
        result = transformer.transform(commit=True)

        assert result.status in (TransformationStatus.SUCCESS, TransformationStatus.WARNING)
        assert isinstance(result.rows_processed, int)
        assert isinstance(result.rows_merged, int)
        assert isinstance(result.execution_seconds, (int, float))
        assert result.execution_seconds >= 0.0
    finally:
        connector.close_pool()
