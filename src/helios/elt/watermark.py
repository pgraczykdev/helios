from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_WATERMARK_FILENAME = "watermark.json"


def clean_watermark(watermark: str) -> str:
    """Normalize watermark string by stripping timestamp if present."""
    return str(watermark).split("T")[0]


def read_watermark(target_dir: Path, filename: str = DEFAULT_WATERMARK_FILENAME) -> str | None:
    """Read the latest watermark date from a JSON file in the target directory."""
    filepath = target_dir / filename
    if not filepath.exists():
        logger.debug("No watermark file found at %s", filepath)
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)
            watermark = data.get("watermark")
            return clean_watermark(watermark) if watermark is not None else None
    except (IOError, json.JSONDecodeError) as exc:
        logger.error("Error reading watermark from %s: %s", filepath, exc)
        return None


def save_watermark(
        target_dir: Path, 
        watermark: str, dataset: str | None = None, 
        temporal_resolution: str | None = None, 
        records_count: int | None = None,
        filename: str = DEFAULT_WATERMARK_FILENAME) -> Path | None:
    """Save the watermark date and ingestion metadata to the target directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    filepath = target_dir / filename

    cleaned = clean_watermark(watermark)
    payload: dict[str, Any] = {"watermark": cleaned, "updated_at": datetime.now(timezone.utc).isoformat()}
    if dataset is not None:
        payload["dataset"] = dataset
    if temporal_resolution is not None:
        payload["temporal_resolution"] = temporal_resolution
    if records_count is not None:
        payload["records_count"] = records_count

    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)
        logger.info("Watermark successfully updated to '%s' at %s", cleaned, filepath)
        return filepath
    except IOError as exc:
        logger.error("Error saving watermark to %s: %s", filepath, exc)
        return None