from dataclasses import dataclass


@dataclass
class TransformationResult:
    """Summary of the Oracle DWH transformation run."""

    status: str
    rows_processed: int
    rows_merged: int
    execution_seconds: float
    error_message: str | None
