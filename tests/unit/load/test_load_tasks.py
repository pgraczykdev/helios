import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from helios.elt.extraction.pipeline import Dataset, TemporalResolution
from helios.elt.load.loader import LoadStatus, LoadingResult
from helios.elt.load.tasks import (
    load_carbon_intensity,
    load_dataset_to_staging,
    load_electricity_demand,
    load_electricity_generation,
    load_installed_capacity,
    load_power_sector_emissions,
)


def test_load_dataset_to_staging_skipped_when_dir_missing(tmp_path):
    """Verify load_dataset_to_staging returns SKIPPED when Bronze Lake directory does not exist."""
    with patch("helios.elt.load.tasks.JsonBronzeDataLake") as mock_lake_cls:
        mock_lake = MagicMock()
        mock_lake.get_dataset_prefix.return_value = (tmp_path / "nonexistent").as_posix()
        mock_lake_cls.return_value = mock_lake

        result = load_dataset_to_staging(
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=TemporalResolution.YEARLY,
        )

        assert isinstance(result, LoadingResult)
        assert result.status == LoadStatus.SKIPPED
        assert result.rows_loaded == 0
        assert result.target_table == "stg_ember_generation"


def test_load_dataset_to_staging_success(tmp_path):
    """Verify load_dataset_to_staging reads JSON files and returns SUCCESS LoadingResult."""
    data_dir = tmp_path / "generation" / "yearly"
    data_dir.mkdir(parents=True, exist_ok=True)
    sample_file = data_dir / "gen_2023.json"
    sample_file.write_text(json.dumps([{"entity": "Poland", "date": "2023"}]), encoding="utf-8")

    with patch("helios.elt.load.tasks.JsonBronzeDataLake") as mock_lake_cls, \
         patch("helios.elt.load.tasks.OracleDatabaseConnector") as mock_conn_cls, \
         patch("helios.elt.load.tasks.StagingLoader") as mock_loader_cls:

        mock_lake = MagicMock()
        mock_lake.get_dataset_prefix.return_value = data_dir.as_posix()
        mock_lake_cls.return_value = mock_lake

        mock_loader = MagicMock()
        mock_loader.load.return_value = LoadingResult(
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=TemporalResolution.YEARLY,
            target_table="stg_ember_generation",
            source_file="gen_2023.json",
            rows_loaded=1,
            status=LoadStatus.SUCCESS,
        )
        mock_loader_cls.return_value = mock_loader

        result = load_dataset_to_staging(
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=TemporalResolution.YEARLY,
        )

        assert isinstance(result, LoadingResult)
        assert result.status == LoadStatus.SUCCESS
        assert result.rows_loaded == 1
        assert result.target_table == "stg_ember_generation"
        assert result.source_file == "gen_2023.json"


def test_dedicated_load_functions():
    """Verify dedicated dataset functions call load_dataset_to_staging with matching arguments."""
    with patch("helios.elt.load.tasks.load_dataset_to_staging") as mock_load:
        mock_load.return_value = MagicMock(spec=LoadingResult)

        load_electricity_generation()
        mock_load.assert_called_with(
            dataset=Dataset.ELECTRICITY_GENERATION,
            temporal_resolution=TemporalResolution.YEARLY,
        )

        load_installed_capacity()
        mock_load.assert_called_with(
            dataset=Dataset.INSTALLED_CAPACITY,
            temporal_resolution=TemporalResolution.MONTHLY,
        )

        load_carbon_intensity()
        mock_load.assert_called_with(
            dataset=Dataset.CARBON_INTENSITY,
            temporal_resolution=TemporalResolution.YEARLY,
        )

        load_electricity_demand()
        mock_load.assert_called_with(
            dataset=Dataset.ELECTRICITY_DEMAND,
            temporal_resolution=TemporalResolution.YEARLY,
        )

        load_power_sector_emissions()
        mock_load.assert_called_with(
            dataset=Dataset.POWER_SECTOR_EMISSIONS,
            temporal_resolution=TemporalResolution.YEARLY,
        )
