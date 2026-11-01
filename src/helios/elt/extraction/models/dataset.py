from enum import StrEnum


class Dataset(StrEnum):
    """Supported datasets for extraction."""

    CARBON_INTENSITY = "carbon-intensity"
    ELECTRICITY_DEMAND = "electricity-demand"
    POWER_SECTOR_EMISSIONS = "power-sector-emissions"
    ELECTRICITY_GENERATION = "electricity-generation"
    INSTALLED_CAPACITY = "installed-capacity"
