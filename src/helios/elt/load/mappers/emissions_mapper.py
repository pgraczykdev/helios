from typing import Any

from helios.elt.extraction.models.temporal_resolution import TemporalResolution
from helios.elt.load.mappers.base_loading_mapper import BaseLoadingMapper


class EmissionsMapper(BaseLoadingMapper):
    """Row mapper for STG_EMBER_EMISSIONS."""

    _DEFAULT_TABLE = "stg_ember_emissions"
    _DEFAULT_SQL = """
        INSERT INTO stg_ember_emissions (
            source_file,
            temporal_resolution,
            entity,
            entity_code,
            is_aggregate_entity,
            raw_date,
            series,
            is_aggregate_series,
            emissions_mtco2,
            share_of_emissions_pct
        ) VALUES (
            :source_file,
            :temporal_resolution,
            :entity,
            :entity_code,
            :is_aggregate_entity,
            :raw_date,
            :series,
            :is_aggregate_series,
            :emissions_mtco2,
            :share_of_emissions_pct
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
        """Map power sector emissions record to staging column dictionary."""
        row = self._map_common_fields(record=record, source_file=source_file, temporal_resolution=temporal_resolution)
        row.update({
            "series": record.get("series"),
            "is_aggregate_series": self._bool_to_int(val=record.get("is_aggregate_series")),
            "emissions_mtco2": record.get("emissions_mtco2"),
            "share_of_emissions_pct": record.get("share_of_emissions_pct"),
        })
        return row
