from dataclasses import dataclass

from helios.elt.extraction.models.extraction_status import ExtractionStatus


@dataclass
class ExtractionResult:
    """Summary of the pipeline extraction run."""

    dataset: str
    temporal_resolution: str
    status: ExtractionStatus
    records_count: int = 0
    previous_watermark: str | None = None
    new_watermark: str | None = None
    start_date: str | None = None
    saved_file: str | None = None
    error_message: str | None = None
