from dataclasses import dataclass


@dataclass
class TransformationResult:
    """Summary of the Oracle DWH transformation run."""

    status: str
    rows_processed: int = 0
    rows_merged: int = 0
    execution_seconds: float = 0.0
    error_message: str | None = None
