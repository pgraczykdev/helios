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


def test_pipeline_extractor_e2e(tmp_path: Path) -> None:
    """End-to-End test for the PipelineExtractor."""
    with EmberClient(api_key=os.getenv("EMBER_API_KEY")) as client:
        data_lake = JsonBronzeDataLake(base_dir=tmp_path/"raw")
        watermark_manager = JsonWatermarkManager(base_dir=tmp_path/"watermarks")
        extractor = PipelineExtractor(
            client=client,
            lake=data_lake,
            watermark_manager=watermark_manager,
        )
        dataset = Dataset.CARBON_INTENSITY
        temporal_resolution = TemporalResolution.YEARLY
        watermark_manager.set(
            watermark="2023",
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
        assert new_watermark >= "2023"

        # new extraction UP to date
        result = extractor.run(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
        )
        assert result.status == ExtractionStatus.UP_TO_DATE
        assert result.records_count == 0
        
