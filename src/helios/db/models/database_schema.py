from enum import StrEnum


class DatabaseSchema(StrEnum):
    """Types of existing database schemas in this project."""

    SYS = "SYS"
    ADMIN = "ADMIN"
    LOGGER = "HELIOS_LOGGER"
    STAGING = "HELIOS_STG"
    CORE = "HELIOS_CORE"
    APEX = "HELIOS_APEX"
