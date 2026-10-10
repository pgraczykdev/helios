import logging
import os

from helios.db.connector import OracleDatabaseConnector
from helios.elt.load.loader import LoadingResult
from helios.elt.transform.transformer import OracleTransformer, TransformationResult

logger = logging.getLogger(__name__)


def transform_dwh_core(load_results: list[LoadingResult] | None = None) -> TransformationResult:
    """Execute PKG_EMBER_ELT.f_load_all() in Oracle ADW to populate Core DWH."""
    valid_results = [r for r in load_results if r is not None] if load_results else []
    if valid_results:
        loaded_summary = [(r.target_table, r.rows_loaded, str(r.status)) for r in valid_results]
        logger.info("Executing DWH transformation after staging loads: %s", loaded_summary)

    connector = OracleDatabaseConnector(
        user=os.getenv("HELIOS_CORE_USER"),
        password=os.getenv("HELIOS_CORE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
        wallet_dir=os.getenv("ORACLE_WALLET_DIR"),
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD"),
    )
    transformer = OracleTransformer(connector=connector)
    result = transformer.transform(commit=True)
    connector.close_pool()

    logger.info(
        "Transformation finished: status=%s, processed=%d, merged=%d, duration=%.2fs",
        result.status,
        result.rows_processed or 0,
        result.rows_merged or 0,
        result.execution_seconds or 0.0,
    )
    return result