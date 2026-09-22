from helios.db import OracleDatabaseConnector, DatabaseConnector
import os
from dotenv import load_dotenv

load_dotenv()


def test_oracle_connection():

    connector = OracleDatabaseConnector(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
        wallet_dir=os.getenv("ORACLE_WALLET_DIR"),
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
    )

    # Ensure the connector can acquire a connection from the pool
    assert isinstance(connector, DatabaseConnector)

    with connector.acquire_connection() as conn:
        # Execute a simple query to verify the connection works as expected
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM dual")
            result = cursor.fetchone()
            assert result[0] == 1

    with connector.acquire_connection() as conn:
        # Execute another simple query to verify the connection works as expected
        with conn.cursor() as cursor:
            cursor.execute("SELECT sysdate FROM dual")
            result = cursor.fetchone()
            assert result[0] is not None

    # Close the connection pool after the tests
    connector.close_pool()
    assert connector._pool is None