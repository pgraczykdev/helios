from typing import Any

from helios.elt.extraction.models.temporal_resolution import TemporalResolution
from helios.elt.load.mappers.base_loading_mapper import BaseLoadingMapper


class DemandMapper(BaseLoadingMapper):
    """Row mapper for STG_EMBER_DEMAND."""

    _DEFAULT_TABLE = "stg_ember_demand"
    _DEFAULT_SQL = """
        INSERT INTO stg_ember_demand (
            source_file,
            temporal_resolution,
            entity,
            entity_code,
            is_aggregate_entity,
            raw_date,
            demand_twh,
            demand_mwh_per_capita
        ) VALUES (
            :source_file,
            :temporal_resolution,
            :entity,
            :entity_code,
            :is_aggregate_entity,
            :raw_date,
            :demand_twh,
            :demand_mwh_per_capita
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
        """Map electricity demand record to staging column dictionary."""
        row = self._map_common_fields(record=record, source_file=source_file, temporal_resolution=temporal_resolution)
        row.update({
            "demand_twh": record.get("demand_twh"),
            "demand_mwh_per_capita": record.get("demand_mwh_per_capita"),
        })
        return row
