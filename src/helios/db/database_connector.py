from contextlib import contextmanager
from typing import Any, Generator, Protocol, runtime_checkable


@runtime_checkable
class DatabaseConnector(Protocol):
    """Protocol defining the database connection pool contract."""

    def get_user(self) -> str | None:
        """Return the username used for the database connection."""
        ...

    @contextmanager
    def acquire_connection(self) -> Generator[Any, None, None]:
        """Acquire a connection from the database connection pool and yield it."""
        ...

    def close_pool(self) -> None:
        """Close the database connection pool."""
        ...
