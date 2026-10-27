from unittest.mock import MagicMock


from helios.elt.extraction.pipeline import (
    Dataset,
    ExtractionStatus,
    PipelineExtractor,
    TemporalResolution,
)


def test_pipeline_up_to_date_skips_extraction() -> None:
    """If watermark matches latest available date, extraction is skipped."""
    mock_client = MagicMock()
    mock_lake = MagicMock()
    mock_wm = MagicMock()

   # Mocks data for the test scenario
    mock_wm.get.return_value = "2024-05-01"
    mock_client.get_latest_available_date.return_value = "2024-05-01"

    pipeline = PipelineExtractor(
        client=mock_client,
        lake=mock_lake,
        watermark_manager=mock_wm,
    )

    result = pipeline.run(
        dataset=Dataset.CARBON_INTENSITY,
        temporal_resolution=TemporalResolution.YEARLY,
        force=False,
    )

    assert result.status == ExtractionStatus.UP_TO_DATE
    assert result.records_count == 0

    # Ensure no API calls or data lake writes occurred.
    mock_client._get.assert_not_called()
    mock_lake.save_raw_data.assert_not_called()


def test_pipeline_force_runs_even_if_up_to_date() -> None:
    """If force=True, pipeline proceeds even if watermark is up to date."""
    mock_client = MagicMock()
    mock_lake = MagicMock()
    mock_wm = MagicMock()

    mock_wm.get.return_value = "2024-01-01"
    mock_client.get_latest_available_date.return_value = "2024-01-01"
    mock_client._get.return_value = {"data": [{"date": "2024-01-01", "value": 100}]}
    mock_lake.save_raw_data.return_value = "data/raw/test.json"

    pipeline = PipelineExtractor(
        client=mock_client,
        lake=mock_lake,
        watermark_manager=mock_wm,
    )

    result = pipeline.run(
        dataset=Dataset.CARBON_INTENSITY,
        temporal_resolution=TemporalResolution.YEARLY,
        force=True,
    )

    assert result.status == ExtractionStatus.SUCCESS
    assert result.records_count == 1
    mock_client._get.assert_called_once()


def test_pipeline_batches_and_updates_watermark() -> None:
    """Pipeline fetches yearly batches and updates watermark."""
    mock_client = MagicMock()
    mock_lake = MagicMock()
    mock_wm = MagicMock()

    # Initial watermark is set to 2022-01-01, latest available date is 2023-12-31
    mock_wm.get.return_value = "2022-01-01"
    mock_client.get_latest_available_date.return_value = "2023-12-31"

    # Returns 2 records for each API request
    mock_client._get.return_value = {
        "data": [
            {"date": "2022-06-01", "value": 50},
            {"date": "2023-06-01", "value": 60},
        ]
    }
    mock_lake.save_raw_data.return_value = "path/to/batch.json"

    pipeline = PipelineExtractor(
        client=mock_client,
        lake=mock_lake,
        watermark_manager=mock_wm,
    )

    result = pipeline.run(
        dataset=Dataset.ELECTRICITY_GENERATION,
        temporal_resolution=TemporalResolution.YEARLY,
    )

    assert result.status == ExtractionStatus.SUCCESS
    assert result.records_count == 4  # 2 batches * 2 records
    assert result.new_watermark == "2023-12-31"
    assert mock_client._get.call_count == 2
    assert mock_lake.save_raw_data.call_count == 2
    assert mock_wm.set.called


def test_pipeline_handles_api_failure() -> None:
    """Pipeline catches API exceptions and returns FAILED status."""
    mock_client = MagicMock()
    mock_lake = MagicMock()
    mock_wm = MagicMock()

    mock_wm.get.return_value = "2024-01-01"
    mock_client.get_latest_available_date.return_value = "2024-05-01"
    
    # Simulate a sudden connection drop during data fetching
    mock_client._get.side_effect = ConnectionError("Ember API timeout")

    pipeline = PipelineExtractor(
        client=mock_client,
        lake=mock_lake,
        watermark_manager=mock_wm,
    )

    result = pipeline.run(
        dataset=Dataset.CARBON_INTENSITY,
        temporal_resolution=TemporalResolution.YEARLY,
    )

    assert result.status == ExtractionStatus.FAILED
    assert "Ember API timeout" in str(result.error_message)