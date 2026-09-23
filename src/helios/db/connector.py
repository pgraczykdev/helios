
from contextlib import contextmanager
from typing import Any, Generator, Protocol, runtime_checkable
import oracledb
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@runtime_checkable
class DatabaseConnector(Protocol):

    @contextmanager
    def acquire_connection(self) -> Generator[Any, None, None]:
        """Acquire a connection from the database connection pool and yield it."""
        ...

    def close_pool(self) -> None:
        """Close the database connection pool."""
        ...


class OracleDatabaseConnector:

    def __init__(
        self,
        user: str | None = None,
        password: str | None = None,
        dsn: str | None = None,
        wallet_dir: str | None = None,
        wallet_password: str | None = None,
        min_connections: int = 1,
        max_connections: int = 4,
        increment: int = 1,
    ) -> None:
        self.user = user or os.getenv("ORACLE_ADMIN_USER")
        self.password = password or os.getenv("ORACLE_ADMIN_PASSWORD")
        self.dsn = dsn or os.getenv("ORACLE_DSN")
        self.wallet_dir = wallet_dir or os.getenv("ORACLE_WALLET_DIR")
        self.wallet_password = wallet_password or os.getenv("ORACLE_WALLET_PASSWORD")

        self.min_connections = min_connections
        self.max_connections = max_connections
        self.increment = increment

        self._pool: oracledb.ConnectionPool | None = None

    def _create_pool(self) -> oracledb.ConnectionPool:
        """Ensure that the Oracle connection pool is created."""
        if self._pool is None:
            self._pool = oracledb.create_pool(
                user=self.user,
                password=self.password,
                dsn=self.dsn,
                config_dir=self.wallet_dir,
                wallet_location=self.wallet_dir,
                wallet_password=self.wallet_password,
                min=self.min_connections,
                max=self.max_connections,
                increment=self.increment,
            )
        return self._pool

    @contextmanager
    def acquire_connection(self) -> Generator[oracledb.Connection, None, None]:
        """Acquire a connection from the Oracle connection pool and yield it."""
        pool = self._create_pool()
        conn = pool.acquire()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            logger.error("Error occurred while using Oracle connection: %s", e)
            conn.rollback()
            raise e
        finally:
            conn.close()
            logger.info("Oracle connection closed and returned to the pool.")

    def close_pool(self) -> None:
        """Close the Oracle connection pool."""
        if self._pool is not None:
            self._pool.close()
            self._pool = None
            logger.info("Oracle connection pool closed.")

