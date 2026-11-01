from typing import Any

from helios.elt.extraction.models.temporal_resolution import TemporalResolution
from helios.elt.load.mappers.base_loading_mapper import BaseLoadingMapper


class CarbonIntensityMapper(BaseLoadingMapper):
    """Row mapper for STG_EMBER_CARBON_INTENSITY."""

    _DEFAULT_TABLE = "stg_ember_carbon_intensity"
    _DEFAULT_SQL = """
        INSERT INTO stg_ember_carbon_intensity (
            source_file,
            temporal_resolution,
            entity,
            entity_code,
            is_aggregate_entity,
            raw_date,
            emissions_intensity_gco2_per_kwh
        ) VALUES (
            :source_file,
            :temporal_resolution,
            :entity,
            :entity_code,
            :is_aggregate_entity,
            :raw_date,
            :emissions_intensity_gco2_per_kwh
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
        """Map carbon intensity record to staging column dictionary."""
        row = self._map_common_fields(record=record, source_file=source_file, temporal_resolution=temporal_resolution)
        row.update({
            "emissions_intensity_gco2_per_kwh": record.get("emissions_intensity_gco2_per_kwh"),
        })
        return row
