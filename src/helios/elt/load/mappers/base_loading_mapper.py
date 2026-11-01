from abc import ABC, abstractmethod
from typing import Any

from helios.elt.extraction.models.temporal_resolution import TemporalResolution


class BaseLoadingMapper(ABC):
    """Abstract base strategy for staging row mappers with properties."""

    def __init__(self, target_table: str, insert_sql: str) -> None:
        self._target_table = target_table
        self._insert_sql = insert_sql

    @property
    def target_table(self) -> str:
        """Get the target staging table name."""
        return self._target_table

    @property
    def insert_sql(self) -> str:
        """Get the INSERT SQL query."""
        return self._insert_sql

    @staticmethod
    def _bool_to_int(val: bool | None) -> int | None:
        return int(val) if isinstance(val, bool) else None

    def _map_common_fields(
        self,
        record: dict[str, Any],
        source_file: str,
        temporal_resolution: TemporalResolution | str,
    ) -> dict[str, Any]:
        """Extract metadata and entity fields common to all Ember datasets."""
        return {
            "source_file": source_file,
            "temporal_resolution": str(temporal_resolution),
            "entity": record.get("entity"),
            "entity_code": record.get("entity_code"),
            "is_aggregate_entity": self._bool_to_int(val=record.get("is_aggregate_entity")),
            "raw_date": record.get("date"),
        }

    @abstractmethod
    def map_row(
        self,
        record: dict[str, Any],
        source_file: str,
        temporal_resolution: TemporalResolution | str,
    ) -> dict[str, Any]:
        """Map a single JSON record into a database row dictionary."""
        ...

    def map_batch(
        self,
        data: list[dict[str, Any]],
        source_file: str,
        temporal_resolution: TemporalResolution | str,
    ) -> list[dict[str, Any]]:
        """Map a collection of raw JSON records."""
        return [
            self.map_row(record=rec, source_file=source_file, temporal_resolution=temporal_resolution)
            for rec in data
        ]
