from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Protocol

from helios.elt.extraction.extraction_utils import normalize_date, normalize_dataset_prefix

logger = logging.getLogger(__name__)

class WatermarkManager(Protocol):
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

class JsonWatermarkManager:
    """Manager for handling watermarks stored as JSON files in a local directory."""
    _default_watermark_dir = Path("data/watermarks")
    _default_watermark_filename = "watermark.json"

    def __init__(self, base_dir: Path | str = _default_watermark_dir):
        self.base_dir = Path(base_dir)

    def get(self, dataset: str, temporal_resolution: str) -> str | None:
        normalized_dataset = normalize_dataset_prefix(dataset)
        target_dir = self.base_dir / normalized_dataset / temporal_resolution
        if not target_dir.exists():
            logger.debug("No watermark file found at %s", target_dir)
            return None
        try:
            with open(file=target_dir / self._default_watermark_filename, mode="r", encoding="utf-8") as file:
                data: dict[str, Any] = json.load(fp=file)
                watermark = data.get("watermark")
                return normalize_date(date_str=watermark) if watermark is not None else None
        except (IOError, json.JSONDecodeError) as exc:
            logger.error("Error reading watermark from %s: %s", target_dir, exc)
            return None
       
    def set(
        self,
        watermark: str,
        dataset: str,
        temporal_resolution: str,
        records_count: int | None = None,
    ) -> str | None:
        normalized_dataset = normalize_dataset_prefix(dataset)
        target_dir = self.base_dir / normalized_dataset / temporal_resolution
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / self._default_watermark_filename

        normalized_watermark = normalize_date(date_str=watermark)
        payload: dict[str, Any] = {"watermark": normalized_watermark, "updated_at": datetime.now(tz=timezone.utc).isoformat()}
        if normalized_dataset is not None:
            payload["dataset"] = normalized_dataset
        if temporal_resolution is not None:
            payload["temporal_resolution"] = temporal_resolution
        if records_count is not None:
            payload["records_count"] = records_count

        try:
            with open(file=filepath, mode="w", encoding="utf-8") as file:
                json.dump(
                    obj=payload,
                    fp=file,
                    indent=4,
                    ensure_ascii=False,
                )
            logger.info("Watermark successfully updated to '%s' at %s", normalized_watermark, filepath)
            return filepath.as_posix()
        except IOError as exc:
            logger.error("Error saving watermark to %s: %s", filepath, exc)
            return None
