from enum import StrEnum


class TemporalResolution(StrEnum):
    """Supported temporal resolutions for datasets."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
