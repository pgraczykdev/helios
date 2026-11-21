import os

from dotenv import load_dotenv
import pytest

from helios.db import DatabaseConnector, DatabaseConnectorFactory, DatabaseSchema

load_dotenv()

admin_configured = bool(
    os.getenv("ORACLE_ADMIN_USER") and os.getenv("ORACLE_ADMIN_PASSWORD") and os.getenv("ORACLE_DSN")
)
pytestmark = pytest.mark.skipif(not admin_configured, reason="Oracle ADMIN DB credentials not set in environment.")


def test_oracle_connection() -> None:
    """Verify live Oracle connection pool lifecycle via DatabaseConnectorFactory."""
    connector = DatabaseConnectorFactory.create_connector(database_schema=DatabaseSchema.ADMIN)

    # Ensure the connector satisfies the DatabaseConnector protocol
    assert isinstance(connector, DatabaseConnector)

    try:
        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM dual")
                result = cursor.fetchone()
                assert result[0] == 1

        with connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT sysdate FROM dual")
                result = cursor.fetchone()
                assert result[0] is not None
    finally:
        connector.close_pool()

    assert connector._pool is None
