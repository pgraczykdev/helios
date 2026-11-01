from enum import StrEnum


class InsightGenerationStatus(StrEnum):
    """Outcome status of an AI insight generation batch job."""

    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
