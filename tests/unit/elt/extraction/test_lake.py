from pathlib import Path
from helios.elt.extraction.lake import JsonBronzeDataLake     
from unittest.mock import patch 
import json


def test_save_raw_data_default_filename_and_content(tmp_path: Path) -> None:
    lake = JsonBronzeDataLake(base_dir=tmp_path)
    records = [{"year": 2023, "value": 150.5}, {"year": 2024, "value": 160.2}]

    saved_path_str = lake.save_raw_data(
        data=records,
        dataset="carbon-intensity",
        temporal_resolution="yearly",
    )

    assert saved_path_str is not None
    saved_file = Path(saved_path_str)
    assert saved_file.exists()
    assert saved_file.name.startswith("carbon_intensity_yearly_")
    assert saved_file.suffix == ".json"

    # Weryfikacja zawartości
    with open(file=saved_file, mode="r", encoding="utf-8") as f:
        data = json.load(fp=f)
        assert data == records


def test_save_raw_data_with_tag(tmp_path: Path) -> None:
    lake = JsonBronzeDataLake(base_dir=tmp_path)
    records = [{"year": 2022, "value": 99.0}]

    saved_path_str = lake.save_raw_data(
        data=records,
        dataset="electricity-generation",
        temporal_resolution="monthly",
        tag="batch_2022",
    )

    assert saved_path_str is not None
    saved_file = Path(saved_path_str)
    assert saved_file.exists()
    assert "batch_2022" in saved_file.name


def test_save_raw_data_with_custom_filename(tmp_path: Path) -> None:
    lake = JsonBronzeDataLake(base_dir=tmp_path)
    records = {"meta": "single_dict_test"}

    saved_path_str = lake.save_raw_data(
        data=records,
        dataset="power-sector-emissions",
        temporal_resolution="yearly",
        filename="custom_payload.json",
    )

    assert saved_path_str is not None
    saved_file = Path(saved_path_str)
    assert saved_file.name == "custom_payload.json"
    assert saved_file.exists()


def test_save_raw_data_handles_io_error(tmp_path: Path) -> None:
    lake = JsonBronzeDataLake(base_dir=tmp_path)

    # Symulujemy awarię zapisu (np. brak uprawnień lub zapełniony dysk)
    with patch("builtins.open", side_effect=IOError("Disk full")):
        result = lake.save_raw_data(
            data=[{"test": 1}],
            dataset="carbon-intensity",
            temporal_resolution="yearly",
        )
        assert result is None