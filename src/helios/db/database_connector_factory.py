import os

from helios.db.database_connector import DatabaseConnector
from helios.db.models.database_schema import DatabaseSchema
from helios.db.models.database_type import DatabaseType
from helios.db.oracle_connector import OracleDatabaseConnector


class DatabaseConnectorFactory:
    """Central factory for creating database connectors and configuring connection pools."""

    _SCHEMA_ENV_PREFIX: dict[DatabaseSchema, str] = {
        DatabaseSchema.SYS: "ORACLE_SYS",
        DatabaseSchema.ADMIN: "ORACLE_ADMIN",
        DatabaseSchema.LOGGER: "HELIOS_LOGGER",
        DatabaseSchema.STAGING: "HELIOS_STAGING",
        DatabaseSchema.CORE: "HELIOS_CORE",
        DatabaseSchema.APEX: "HELIOS_APEX",
    }

    @classmethod
    def create_connector(
        cls,
        database_schema: DatabaseSchema,
        database_type: DatabaseType | None = None,
        min_connections: int | None = None,
        max_connections: int | None = None,
        increment: int | None = None,
    ) -> DatabaseConnector:
        """Create a database connector configured for the given schema and database type."""
        resolved_type = cls._resolve_database_type(database_type=database_type)
        if not isinstance(database_schema, DatabaseSchema):
            raise ValueError(f"Unsupported database schema: {database_schema}")

        match resolved_type:
            case DatabaseType.ORACLE:
                user = cls._get_user(database_schema=database_schema)
                password = cls._get_password(database_schema=database_schema)
                dsn = cls._get_required_env(env_var="ORACLE_DSN")
                wallet_dir = cls._get_optional_env(env_var="ORACLE_WALLET_DIR")
                wallet_password = cls._get_optional_env(env_var="ORACLE_WALLET_PASSWORD") if wallet_dir else None

                pool_min = cls._get_pool_int(value=min_connections, env_var="ORACLE_POOL_MIN", default=1)
                pool_max = cls._get_pool_int(value=max_connections, env_var="ORACLE_POOL_MAX", default=4)
                pool_increment = cls._get_pool_int(value=increment, env_var="ORACLE_POOL_INCREMENT", default=1)

                return OracleDatabaseConnector(
                    user=user,
                    password=password,
                    dsn=dsn,
                    wallet_dir=wallet_dir,
                    wallet_password=wallet_password,
                    min_connections=pool_min,
                    max_connections=pool_max,
                    increment=pool_increment,
                )
            case _:
                raise ValueError(f"Unsupported database type: {resolved_type}")

    @classmethod
    def _resolve_database_type(cls, database_type: DatabaseType | None) -> DatabaseType:
        """Resolve database type from explicit argument or DB_TYPE environment variable."""
        if database_type is None:
            raw_type = cls._get_optional_env(env_var="DB_TYPE") or DatabaseType.ORACLE.value
            try:
                return DatabaseType(raw_type.upper())
            except ValueError as exc:
                raise ValueError(f"Unsupported database type: {raw_type}") from exc

        if not isinstance(database_type, DatabaseType):
            raise ValueError(f"Unsupported database type: {database_type}")
        return database_type

    @classmethod
    def _get_schema_env_prefix(cls, database_schema: DatabaseSchema) -> str:
        """Return environment variable prefix mapped to the given database schema."""
        prefix = cls._SCHEMA_ENV_PREFIX.get(database_schema)
        if prefix is None:
            raise ValueError(f"Unsupported database schema: {database_schema}")
        return prefix

    @classmethod
    def _get_user(cls, database_schema: DatabaseSchema) -> str:
        """Read required username for the given database schema."""
        prefix = cls._get_schema_env_prefix(database_schema=database_schema)
        return cls._get_required_env(env_var=f"{prefix}_USER")

    @classmethod
    def _get_password(cls, database_schema: DatabaseSchema) -> str:
        """Read required password for the given database schema."""
        prefix = cls._get_schema_env_prefix(database_schema=database_schema)
        return cls._get_required_env(env_var=f"{prefix}_PASSWORD")

    @staticmethod
    def _get_required_env(env_var: str) -> str:
        """Return a non-empty environment variable or raise ValueError if missing."""
        value = os.getenv(key=env_var)
        if value is None or not value.strip():
            raise ValueError(f"Missing required environment variable: {env_var}")
        return value.strip()

    @staticmethod
    def _get_optional_env(env_var: str) -> str | None:
        """Return a stripped environment variable or None if unset or blank."""
        value = os.getenv(key=env_var)
        if value is None or not value.strip():
            return None
        return value.strip()

    @staticmethod
    def _get_pool_int(value: int | None, env_var: str, default: int) -> int:
        """Resolve an integer pool setting from explicit argument, environment variable, or default."""
        if value is not None:
            return value
        raw = os.getenv(key=env_var)
        if raw is None or not raw.strip():
            return default
        return int(raw.strip())
