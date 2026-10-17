import os
from pathlib import Path
import pytest
from dotenv import load_dotenv

from helios.client.ember_client import EmberClient
from helios.elt.extraction.lake import JsonBronzeDataLake
from helios.elt.extraction.pipeline import (
    Dataset,
    ExtractionStatus,
    PipelineExtractor,
    TemporalResolution,
)
from helios.elt.extraction.watermark import JsonWatermarkManager

load_dotenv()

api_key_present = bool(os.getenv("EMBER_API_KEY"))
pytestmark = pytest.mark.skipif(
    not api_key_present,
    reason="EMBER_API_KEY not set.",
)


@pytest.mark.parametrize(
    "dataset, temporal_resolution, initial_watermark",
    [
        (Dataset.CARBON_INTENSITY, TemporalResolution.YEARLY, "2023"),
        (Dataset.ELECTRICITY_GENERATION, TemporalResolution.YEARLY, "2023"),
        (Dataset.POWER_SECTOR_EMISSIONS, TemporalResolution.YEARLY, "2023"),
        (Dataset.ELECTRICITY_DEMAND, TemporalResolution.YEARLY, "2023"),
        (Dataset.INSTALLED_CAPACITY, TemporalResolution.MONTHLY, "2024-01-01"),
    ],
)
def test_pipeline_extractor_e2e(
    tmp_path: Path,
    dataset: Dataset,
    temporal_resolution: TemporalResolution,
    initial_watermark: str,
) -> None:
    """End-to-End test for PipelineExtractor across all 5 Ember API datasets."""
    with EmberClient(api_key=os.getenv("EMBER_API_KEY")) as client:
        data_lake = JsonBronzeDataLake(base_dir=tmp_path / "raw")
        watermark_manager = JsonWatermarkManager(base_dir=tmp_path / "watermarks")
        extractor = PipelineExtractor(
            client=client,
            lake=data_lake,
            watermark_manager=watermark_manager,
        )

        watermark_manager.set(
            watermark=initial_watermark,
            dataset=dataset,
            temporal_resolution=temporal_resolution,
        )

        result = extractor.run(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            force=False,
        )
        assert result.status == ExtractionStatus.SUCCESS
        assert result.records_count > 0
        assert result.saved_file is not None

        saved_file_path = Path(result.saved_file)
        assert saved_file_path.exists()

        new_watermark = watermark_manager.get(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
        )
        assert new_watermark is not None
        assert new_watermark >= initial_watermark

        # Second extraction without force=True should return UP_TO_DATE
        second_result = extractor.run(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            force=False,
        )
        assert second_result.status == ExtractionStatus.UP_TO_DATE
        assert second_result.records_count == 0
