from typing import Protocol


class WatermarkManager(Protocol):
    """Protocol for dataset watermark management."""

    def get(self, dataset: str, temporal_resolution: str) -> str | None:
        """Get the current watermark for the given dataset and temporal resolution."""
        ...

    def set(
        self,
        watermark: str,
        dataset: str,
        temporal_resolution: str,
        records_count: int | None = None,
    ) -> str | None:
        """Set the watermark for the given dataset and temporal resolution."""
        ...
