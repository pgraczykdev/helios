from enum import StrEnum


class LoadStatus(StrEnum):
    """Outcome status of a staging load operation."""

    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
