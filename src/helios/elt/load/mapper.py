from abc import ABC, abstractmethod
from typing import Any
from helios.elt.extraction.pipeline import Dataset, TemporalResolution


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


class CapacityMapper(BaseLoadingMapper):
    """Row mapper for STG_EMBER_CAPACITY."""

    _DEFAULT_TABLE = "stg_ember_capacity"
    _DEFAULT_SQL = """
        INSERT INTO stg_ember_capacity (
            source_file,
            temporal_resolution,
            entity,
            entity_code,
            is_aggregate_entity,
            raw_date,
            series,
            is_aggregate_series,
            capacity_gw,
            capacity_w_per_capita
        ) VALUES (
            :source_file,
            :temporal_resolution,
            :entity,
            :entity_code,
            :is_aggregate_entity,
            :raw_date,
            :series,
            :is_aggregate_series,
            :capacity_gw,
            :capacity_w_per_capita
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
        """Map installed capacity record to staging column dictionary."""
        row = self._map_common_fields(record=record, source_file=source_file, temporal_resolution=temporal_resolution)
        row.update({
            "series": record.get("series"),
            "is_aggregate_series": self._bool_to_int(val=record.get("is_aggregate_series")),
            "capacity_gw": record.get("capacity_gw"),
            "capacity_w_per_capita": record.get("capacity_w_per_capita"),
        })
        return row


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


class LoadingMapperFactory:
    """Factory for creating and resolving dataset row mappers."""

    _REGISTRY: dict[str, type[BaseLoadingMapper]] = {
        Dataset.ELECTRICITY_GENERATION: GenerationMapper,
        Dataset.INSTALLED_CAPACITY: CapacityMapper,
        Dataset.CARBON_INTENSITY: CarbonIntensityMapper,
        Dataset.ELECTRICITY_DEMAND: DemandMapper,
        Dataset.POWER_SECTOR_EMISSIONS: EmissionsMapper,
    }

    @classmethod
    def get_mapper(cls, dataset: Dataset | str) -> BaseLoadingMapper:
        """Resolve and instantiate a mapper for given dataset."""
        mapper_cls = cls._REGISTRY.get(str(dataset))
        if not mapper_cls:
            raise ValueError(f"No mapper registered for dataset: '{dataset}'")
        return mapper_cls()
