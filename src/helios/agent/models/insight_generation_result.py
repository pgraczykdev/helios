from dataclasses import dataclass

from helios.agent.models.insight_generation_status import InsightGenerationStatus


@dataclass
class InsightGenerationResult:
    """Summary of the AI executive insight generation batch run."""

    status: InsightGenerationStatus
    year: int
    countries_processed: int = 0
    countries_failed: int = 0
    error_message: str | None = None
