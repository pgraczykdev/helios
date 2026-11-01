from typing import Any

from helios.elt.extraction.models.temporal_resolution import TemporalResolution
from helios.elt.load.mappers.base_loading_mapper import BaseLoadingMapper


class GenerationMapper(BaseLoadingMapper):
    """Row mapper for STG_EMBER_GENERATION."""

    _DEFAULT_TABLE = "stg_ember_generation"
    _DEFAULT_SQL = """
        INSERT INTO stg_ember_generation (
            source_file,
            temporal_resolution,
            entity,
            entity_code,
            is_aggregate_entity,
            raw_date,
            series,
            is_aggregate_series,
            generation_twh,
            share_of_generation_pct
        ) VALUES (
            :source_file,
            :temporal_resolution,
            :entity,
            :entity_code,
            :is_aggregate_entity,
            :raw_date,
            :series,
            :is_aggregate_series,
            :generation_twh,
            :share_of_generation_pct
        )
    """

    def __init__(self, target_table: str = _DEFAULT_TABLE, insert_sql: str = _DEFAULT_SQL) -> None:
        super().__init__(target_table=target_table, insert_sql=insert_sql)

    def map_row(
        self,
        record: dict[str, Any],
        source_file: str,
        temporal_resolution: TemporalResolution | str,
    ) -> dict[str, Any]:
        """Map electricity generation record to staging column dictionary."""
        row = self._map_common_fields(record=record, source_file=source_file, temporal_resolution=temporal_resolution)
        row.update({
            "series": record.get("series"),
            "is_aggregate_series": self._bool_to_int(val=record.get("is_aggregate_series")),
            "generation_twh": record.get("generation_twh"),
            "share_of_generation_pct": record.get("share_of_generation_pct"),
        })
        return row
