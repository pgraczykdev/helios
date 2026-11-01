from enum import StrEnum


class ExtractionStatus(StrEnum):
    """Outcome status of an extraction job."""

    SUCCESS = "SUCCESS"
    UP_TO_DATE = "UP_TO_DATE"
    NO_DATA = "NO_DATA"
    FAILED = "FAILED"
