import pytest

from helios.db.database_connector_factory import DatabaseConnectorFactory
from helios.db.models.database_schema import DatabaseSchema
from helios.db.models.database_type import DatabaseType
from helios.db.oracle_connector import OracleDatabaseConnector


@pytest.mark.parametrize(
    "schema, env_prefix",
    [
        (DatabaseSchema.SYS, "ORACLE_SYS"),
        (DatabaseSchema.ADMIN, "ORACLE_ADMIN"),
        (DatabaseSchema.LOGGER, "HELIOS_LOGGER"),
        (DatabaseSchema.STAGING, "HELIOS_STAGING"),
        (DatabaseSchema.CORE, "HELIOS_CORE"),
        (DatabaseSchema.APEX, "HELIOS_APEX"),
    ],
)
def test_factory_creates_oracle_connector_for_all_schemas(
    monkeypatch: pytest.MonkeyPatch,
    schema: DatabaseSchema,
    env_prefix: str,
) -> None:
    """Verify connector creation and credential mapping for every supported Oracle schema."""
    monkeypatch.setenv(name=f"{env_prefix}_USER", value=schema.value)
    monkeypatch.setenv(name=f"{env_prefix}_PASSWORD", value="secret_pwd")
    monkeypatch.setenv(name="ORACLE_DSN", value="adw_high")
    monkeypatch.setenv(name="ORACLE_WALLET_DIR", value="/fake/wallet/dir")
    monkeypatch.setenv(name="ORACLE_WALLET_PASSWORD", value="wallet_pwd")
    monkeypatch.delenv(name="ORACLE_POOL_MIN", raising=False)
    monkeypatch.delenv(name="ORACLE_POOL_MAX", raising=False)
    monkeypatch.delenv(name="ORACLE_POOL_INCREMENT", raising=False)

    connector = DatabaseConnectorFactory.create_connector(
        database_type=DatabaseType.ORACLE,
        database_schema=schema,
    )

    assert isinstance(connector, OracleDatabaseConnector)
    assert connector.user == schema.value
    assert connector.password == "secret_pwd"
    assert connector.dsn == "adw_high"
    assert connector.wallet_dir == "/fake/wallet/dir"
    assert connector.wallet_password == "wallet_pwd"
    assert connector.min_connections == 1
    assert connector.max_connections == 4
    assert connector.increment == 1


def test_factory_oracle_without_wallet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify TCP mode leaves wallet_dir and wallet_password as None when wallet dir is unset."""
    monkeypatch.setenv(name="HELIOS_CORE_USER", value="HELIOS_CORE")
    monkeypatch.setenv(name="HELIOS_CORE_PASSWORD", value="core_pwd")
    monkeypatch.setenv(name="ORACLE_DSN", value="localhost:1521/FREEPDB1")
    monkeypatch.delenv(name="ORACLE_WALLET_DIR", raising=False)
    monkeypatch.setenv(name="ORACLE_WALLET_PASSWORD", value="unused_wallet_pwd")

    connector = DatabaseConnectorFactory.create_connector(
        database_type=DatabaseType.ORACLE,
        database_schema=DatabaseSchema.CORE,
    )

    assert isinstance(connector, OracleDatabaseConnector)
    assert connector.wallet_dir is None
    assert connector.wallet_password is None


def test_factory_pool_settings_from_env_and_explicit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify pool size settings are read from env vars and can be overridden explicitly."""
    monkeypatch.setenv(name="HELIOS_CORE_USER", value="HELIOS_CORE")
    monkeypatch.setenv(name="HELIOS_CORE_PASSWORD", value="core_pwd")
    monkeypatch.setenv(name="ORACLE_DSN", value="adw_high")
    monkeypatch.setenv(name="ORACLE_POOL_MIN", value="2")
    monkeypatch.setenv(name="ORACLE_POOL_MAX", value="10")
    monkeypatch.setenv(name="ORACLE_POOL_INCREMENT", value="2")

    connector_from_env = DatabaseConnectorFactory.create_connector(database_schema=DatabaseSchema.CORE)
    assert isinstance(connector_from_env, OracleDatabaseConnector)
    assert connector_from_env.min_connections == 2
    assert connector_from_env.max_connections == 10
    assert connector_from_env.increment == 2

    connector_override = DatabaseConnectorFactory.create_connector(
        database_schema=DatabaseSchema.CORE,
        min_connections=3,
        max_connections=8,
        increment=1,
    )
    assert isinstance(connector_override, OracleDatabaseConnector)
    assert connector_override.min_connections == 3
    assert connector_override.max_connections == 8
    assert connector_override.increment == 1


def test_factory_resolves_default_database_type_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DB_TYPE env var is resolved case-insensitively when database_type is omitted."""
    monkeypatch.setenv(name="DB_TYPE", value="oracle")
    monkeypatch.setenv(name="HELIOS_STAGING_USER", value="HELIOS_STG")
    monkeypatch.setenv(name="HELIOS_STAGING_PASSWORD", value="stg_pwd")
    monkeypatch.setenv(name="ORACLE_DSN", value="adw_high")

    connector = DatabaseConnectorFactory.create_connector(database_schema=DatabaseSchema.STAGING)

    assert isinstance(connector, OracleDatabaseConnector)
    assert connector.user == "HELIOS_STG"


def test_factory_raises_on_unsupported_database_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ValueError is raised for an unsupported database type argument or DB_TYPE env var."""
    with pytest.raises(ValueError, match="Unsupported database type"):
        DatabaseConnectorFactory.create_connector(
            database_type="POSTGRES",  # type: ignore[arg-type]
            database_schema=DatabaseSchema.CORE,
        )

    monkeypatch.setenv(name="DB_TYPE", value="POSTGRES")
    with pytest.raises(ValueError, match="Unsupported database type"):
        DatabaseConnectorFactory.create_connector(database_schema=DatabaseSchema.CORE)


def test_factory_raises_on_unsupported_database_schema() -> None:
    """Verify ValueError is raised for an unsupported database schema."""
    with pytest.raises(ValueError, match="Unsupported database schema"):
        DatabaseConnectorFactory.create_connector(
            database_type=DatabaseType.ORACLE,
            database_schema="UNKNOWN",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("missing_var", ["HELIOS_CORE_USER", "HELIOS_CORE_PASSWORD", "ORACLE_DSN"])
def test_factory_raises_on_missing_required_env_var(
    monkeypatch: pytest.MonkeyPatch,
    missing_var: str,
) -> None:
    """Verify missing credentials or DSN raise ValueError instead of falling back to ADMIN."""
    monkeypatch.setenv(name="ORACLE_ADMIN_USER", value="ADMIN")
    monkeypatch.setenv(name="ORACLE_ADMIN_PASSWORD", value="admin_pwd")
    monkeypatch.setenv(name="HELIOS_CORE_USER", value="HELIOS_CORE")
    monkeypatch.setenv(name="HELIOS_CORE_PASSWORD", value="core_pwd")
    monkeypatch.setenv(name="ORACLE_DSN", value="adw_high")
    monkeypatch.delenv(name=missing_var, raising=False)

    with pytest.raises(ValueError, match=f"Missing required environment variable: {missing_var}"):
        DatabaseConnectorFactory.create_connector(
            database_type=DatabaseType.ORACLE,
            database_schema=DatabaseSchema.CORE,
        )
