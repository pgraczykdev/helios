from typing import Any, Protocol, runtime_checkable

from helios.elt.extraction.models.dataset import Dataset
from helios.elt.extraction.models.temporal_resolution import TemporalResolution
from helios.elt.load.models.loading_result import LoadingResult


@runtime_checkable
class Loader(Protocol):
    """Protocol for staging data loaders."""

    def load(
        self,
        data: list[dict[str, Any]],
        dataset: Dataset,
        temporal_resolution: TemporalResolution,
        source_file: str,
    ) -> LoadingResult:
        """Load the given data into the target system."""
        ...
