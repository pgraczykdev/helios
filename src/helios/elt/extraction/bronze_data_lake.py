from typing import Any, Protocol


class BronzeDataLake(Protocol):
    """Protocol for Bronze Data Lake storage operations."""

    def get_dataset_prefix(self, dataset: str, temporal_resolution: str) -> str:
        """Return the prefix path for the dataset and temporal resolution within the Bronze Lake."""
        ...

    def save_raw_data(
        self,
        data: list[dict[str, Any]] | dict[str, Any],
        dataset: str,
        temporal_resolution: str,
        filename: str | None = None,
        tag: str | None = None,
    ) -> str | None:
        """Save raw data to the Bronze Lake and return the file path as a string."""
        ...
