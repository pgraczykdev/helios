from enum import StrEnum


class TransformationStatus(StrEnum):
    """Outcome status of a DWH transformation operation."""

    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
