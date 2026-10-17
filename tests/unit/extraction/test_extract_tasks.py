from typing import Callable
from unittest.mock import MagicMock, patch
import pytest

from helios.elt.extraction.pipeline import (
    Dataset,
    ExtractionResult,
    TemporalResolution,
)
from helios.elt.extraction.tasks import (
    extract_carbon_intensity,
    extract_electricity_demand,
    extract_electricity_generation,
    extract_installed_capacity,
    extract_power_sector_emissions,
)


@pytest.mark.parametrize(
    "task_fn, expected_dataset, expected_resolution",
    [
        (extract_electricity_generation, Dataset.ELECTRICITY_GENERATION, TemporalResolution.YEARLY),
        (extract_carbon_intensity, Dataset.CARBON_INTENSITY, TemporalResolution.YEARLY),
        (extract_installed_capacity, Dataset.INSTALLED_CAPACITY, TemporalResolution.MONTHLY),
        (extract_electricity_demand, Dataset.ELECTRICITY_DEMAND, TemporalResolution.YEARLY),
        (extract_power_sector_emissions, Dataset.POWER_SECTOR_EMISSIONS, TemporalResolution.YEARLY),
    ],
)
def test_extract_tasks_default_parameters(
    task_fn: Callable[..., ExtractionResult],
    expected_dataset: Dataset,
    expected_resolution: TemporalResolution,
) -> None:
    """Verify each extract_* task initializes PipelineExtractor and calls run with expected defaults."""
    with patch("helios.elt.extraction.tasks.PipelineExtractor") as mock_extractor_cls:
        mock_extractor = MagicMock()
        mock_result = MagicMock(spec=ExtractionResult)
        mock_extractor.run.return_value = mock_result
        mock_extractor_cls.return_value = mock_extractor

        result = task_fn()

        assert result is mock_result
        mock_extractor_cls.assert_called_once_with(
            lake=None,
            watermark_manager=None,
        )
        mock_extractor.run.assert_called_once_with(
            dataset=expected_dataset,
            temporal_resolution=expected_resolution,
            force=False,
        )


def test_extract_task_custom_dependencies_and_force() -> None:
    """Verify custom lake, watermark_manager, and force=True are forwarded to PipelineExtractor."""
    mock_lake = MagicMock()
    mock_wm = MagicMock()

    with patch("helios.elt.extraction.tasks.PipelineExtractor") as mock_extractor_cls:
        mock_extractor = MagicMock()
        mock_extractor_cls.return_value = mock_extractor

        extract_electricity_generation(
            temporal_resolution=TemporalResolution.MONTHLY,
            force=True,
            lake=mock_lake,
            watermark_manager=mock_wm,
        )

        mock_extractor_cls.assert_called_once_with(
            lake=mock_lake,
            watermark_manager=mock_wm,
        )
        mock_extractor.run.assert_called_once_with(
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=TemporalResolution.MONTHLY,
            force=True,
        )
