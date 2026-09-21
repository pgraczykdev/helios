from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Protocol

from helios.elt.extraction.extraction_utils import normalize_dataset_prefix


logger = logging.getLogger(__name__)

# Default base directory for raw Bronze Data Lake storage

class BronzeDataLake(Protocol):
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


class JsonBronzeDataLake:
    """Manager for the local Bronze Data Lake storing raw 1:1 API payloads in JSON files."""
    _default_json_bronze_lake_dir = Path("data/raw")
    def __init__(self, base_dir: Path | str = _default_json_bronze_lake_dir) -> None:
        """Initialize Bronze Lake with root raw storage directory."""
        self.base_dir = Path(base_dir)

    def get_dataset_prefix(self, dataset: str, temporal_resolution: str) -> str:
        """Resolve the target directory path for a given dataset and temporal resolution."""
        normalized_dataset = normalize_dataset_prefix(dataset)
        return (self.base_dir / normalized_dataset / temporal_resolution).as_posix()

    def save_raw_data(
        self,
        data: list[dict[str, Any]] | dict[str, Any],
        dataset: str,
        temporal_resolution: str,
        filename: str | None = None,
        tag: str | None = None,
    ) -> str | None:
        """Save raw JSON payload directly to the Bronze Lake."""
        target_dir = Path(self.get_dataset_prefix(dataset=dataset, temporal_resolution=temporal_resolution))
        target_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            normalized_dataset = dataset.replace("-", "_")
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
            tag_suffix = f"_{tag}" if tag else ""
            filename = f"{normalized_dataset}_{temporal_resolution}{tag_suffix}_{timestamp}.json"

        filepath = target_dir / filename
        record_count = len(data) if isinstance(data, list) else 1

        try:
            with open(file=filepath, mode="w", encoding="utf-8") as file:
                json.dump(
                    obj=data,
                    fp=file,
                    indent=4,
                    ensure_ascii=False,
                )
            logger.info("Successfully saved %d raw records to Bronze Lake at: %s", record_count, filepath)
            return filepath.as_posix()
        except IOError as exc:
            logger.error("Failed to save raw data to %s: %s", filepath, exc)
            return None