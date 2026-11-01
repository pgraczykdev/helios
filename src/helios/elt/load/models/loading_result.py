from dataclasses import dataclass

from helios.elt.extraction.models.dataset import Dataset
from helios.elt.extraction.models.temporal_resolution import TemporalResolution
from helios.elt.load.models.load_status import LoadStatus


@dataclass
class LoadingResult:
    """Summary of a staging load operation."""

    dataset: Dataset
    temporal_resolution: TemporalResolution
    target_table: str
    source_file: str
    rows_loaded: int = 0
    status: LoadStatus = LoadStatus.SUCCESS
    error_message: str | None = None
