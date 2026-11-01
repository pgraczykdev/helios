from helios.elt.extraction.models.dataset import Dataset
from helios.elt.load.mappers.base_loading_mapper import BaseLoadingMapper
from helios.elt.load.mappers.capacity_mapper import CapacityMapper
from helios.elt.load.mappers.carbon_intensity_mapper import CarbonIntensityMapper
from helios.elt.load.mappers.demand_mapper import DemandMapper
from helios.elt.load.mappers.emissions_mapper import EmissionsMapper
from helios.elt.load.mappers.generation_mapper import GenerationMapper


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
