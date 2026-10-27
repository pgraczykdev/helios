import pytest
import unittest.mock
from helios.db.connector import OracleDatabaseConnector

def test_connector_with_wallet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the connector behaves correctly when an Oracle wallet is configured."""
    monkeypatch.setenv("ORACLE_WALLET_DIR", "/fake/wallet/dir")
    monkeypatch.setenv("ORACLE_WALLET_PASSWORD", "fake_password")
    connector = OracleDatabaseConnector(
        user="fake_user",
        password="fake_ppwd",
        dsn="fake_dns"
    )
    assert connector.wallet_dir == "/fake/wallet/dir"
    assert connector.wallet_password == "fake_password"
    with unittest.mock.patch(target="helios.db.connector.oracledb.create_pool") as mock_create_pool:
        connector._create_pool()
        mock_create_pool.assert_called_once_with(
            user="fake_user",
            password="fake_ppwd",
            dsn="fake_dns",
            config_dir="/fake/wallet/dir",
            wallet_location="/fake/wallet/dir",
            wallet_password="fake_password",
            min=1,
            max=4,
            increment=1
        )


def test_connector_without_wallet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the connector behaves correctly when no Oracle wallet is configured."""
    monkeypatch.delenv("ORACLE_WALLET_DIR", raising=False)
    monkeypatch.delenv("ORACLE_WALLET_PASSWORD", raising=False)
    connector = OracleDatabaseConnector(
        user="fake_user",
        password="fake_ppwd",
        dsn="fake_dns"
    )
    assert connector.wallet_dir is None
    assert connector.wallet_password is None

    with unittest.mock.patch(target="helios.db.connector.oracledb.create_pool") as mock_create_pool:
        connector._create_pool()
        mock_create_pool.assert_called_once_with(
            user="fake_user",
            password="fake_ppwd",
            dsn="fake_dns",
            config_dir=None,
            wallet_location=None,
            wallet_password=None,
            min=1,
            max=4,
            increment=1
        )
