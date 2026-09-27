from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
import oracledb
import logging

import helios.db.connector

logger = logging.getLogger(__name__)

class TransformationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"

@dataclass
class TransformationResult:
    status: str
    rows_processed: int
    rows_merged: int
    execution_seconds: float
    error_message: str | None


class Transformer(Protocol):
    "Protocol for a data transformer."

    def transform(self, commit: bool = True) -> TransformationResult:
        """Perform the transformation using the given database connector."""
        ...


class OracleTransformer(Transformer):

    def __init__(self, connector: helios.db.connector.DatabaseConnector):
        self.connector = connector

    def transform(self, commit: bool = True) -> TransformationResult:
        # Implement the Oracle-specific transformation logic here
        pl_sql_block = """
        DECLARE
            l_commit BOOLEAN := :pi_commit;
            l_result helios_core.pkg_ember_elt.t_elt_result_rec;
        BEGIN
            l_result := helios_core.pkg_ember_elt.f_load_all(pi_commit => l_commit);
            :out_status            := l_result.status;
            :out_rows_processed    := l_result.rows_processed;
            :out_rows_merged       := l_result.rows_merged;
            :out_execution_seconds := l_result.execution_seconds;
            :out_error_message     := l_result.error_message;
        END;
        """
        try:
            with self.connector.acquire_connection() as connection:
                with connection.cursor() as cursor:
                    out_status = cursor.var(oracledb.STRING)  
                    out_rows_processed = cursor.var(oracledb.NUMBER)
                    out_rows_merged = cursor.var(oracledb.NUMBER)
                    out_execution_seconds = cursor.var(oracledb.NUMBER)
                    out_error_message = cursor.var(oracledb.STRING)

                    cursor.execute(
                        pl_sql_block,
                        pi_commit=commit,
                        out_status=out_status,
                        out_rows_processed=out_rows_processed,
                        out_rows_merged=out_rows_merged,
                        out_execution_seconds=out_execution_seconds,
                        out_error_message=out_error_message
                    )

            return TransformationResult(
                status=out_status.getvalue() or TransformationStatus.SUCCESS,
                rows_processed=out_rows_processed.getvalue(),
                rows_merged=out_rows_merged.getvalue(),
                execution_seconds=out_execution_seconds.getvalue(),
                error_message=out_error_message.getvalue()
            )
        except Exception as e:
            logger.error("Transformation failed with error: %s", e)
            return TransformationResult(
                status=TransformationStatus.ERROR,
                rows_processed=0,
                rows_merged=0,
                execution_seconds=0.0,
                error_message=str(e),
            )