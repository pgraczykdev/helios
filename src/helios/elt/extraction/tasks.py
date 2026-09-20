import logging
from helios.elt.extraction.pipeline import Dataset, ExtractionPipeline, ExtractionResult, TemporalResolution
from helios.elt.extraction.lake import BronzeDataLake


def extract_electricity_generation(
        temporal_resolution: TemporalResolution | str = TemporalResolution.YEARLY,
        force: bool = False,
        lake: BronzeDataLake | None = None,
    ) -> ExtractionResult:
        """Extract electricity generation dataset into Bronze Lake."""
        pipeline = ExtractionPipeline(lake=lake)
        return pipeline.run(
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=temporal_resolution,
            force=force,
        )
    
    
def extract_carbon_intensity(
    temporal_resolution: TemporalResolution | str = TemporalResolution.YEARLY,
    force: bool = False,
    lake: BronzeDataLake | None = None,
) -> ExtractionResult:
    """Extract carbon intensity dataset into Bronze Lake."""
    pipeline = ExtractionPipeline(lake=lake)
    return pipeline.run(
        dataset=Dataset.CARBON_INTENSITY,
        temporal_resolution=temporal_resolution,
        force=force,
    )

    
def extract_installed_capacity(
    force: bool = False,
    lake: BronzeDataLake | None = None,
) -> ExtractionResult:
    """Extract installed capacity dataset into Bronze Lake. Only available monthly."""
    pipeline = ExtractionPipeline(lake=lake)
    return pipeline.run(
        dataset=Dataset.INSTALLED_CAPACITY,
        temporal_resolution=TemporalResolution.MONTHLY,
        force=force,
    )

    
def extract_electricity_demand(
    temporal_resolution: TemporalResolution | str = TemporalResolution.YEARLY,
    force: bool = False,
    lake: BronzeDataLake | None = None,
) -> ExtractionResult:
    """Extract electricity demand dataset into Bronze Lake."""
    pipeline = ExtractionPipeline(lake=lake)
    return pipeline.run(
        dataset=Dataset.ELECTRICITY_DEMAND,
        temporal_resolution=temporal_resolution,
        force=force,
    )

    
def extract_power_sector_emissions(
    temporal_resolution: TemporalResolution | str = TemporalResolution.YEARLY,
    force: bool = False,
    lake: BronzeDataLake | None = None,
) -> ExtractionResult:
    """Extract power sector emissions dataset into Bronze Lake."""
    pipeline = ExtractionPipeline(lake=lake)
    return pipeline.run(
        dataset=Dataset.POWER_SECTOR_EMISSIONS,
        temporal_resolution=temporal_resolution,
        force=force,
    )

    
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    res = extract_electricity_generation(temporal_resolution=TemporalResolution.YEARLY)
    print(f"Status: {res.status} | Records: {res.records_count} | Watermark: {res.new_watermark}")