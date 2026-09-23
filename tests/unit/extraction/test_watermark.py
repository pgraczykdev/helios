from pathlib import Path
import json
  
from helios.elt.extraction.watermark import JsonWatermarkManager

def test_save_and_get_watermark(tmp_path: Path) -> None:
    manager = JsonWatermarkManager(base_dir=tmp_path)

    saved_path = manager.set(
        watermark="2024-06-01",
        dataset="carbon-intensity",
        temporal_resolution="yearly",
        records_count=100,
    )
    assert saved_path is not None

    # Check if the watermark file was created correctly
    expected_file = tmp_path / "carbon_intensity" / "yearly" / "watermark.json"
    assert expected_file.exists()
    assert saved_path == expected_file.as_posix()

    # Read the watermark using the manager's get() method
    read_date = manager.get(dataset="carbon-intensity", temporal_resolution="yearly")
    assert read_date == "2024-06-01"

    # Verify the contents of the JSON file
    with open(file=expected_file, mode="r", encoding="utf-8") as file:
        data = json.load(fp=file)
        assert data["watermark"] == "2024-06-01"
        assert data["dataset"] == "carbon_intensity"
        assert data["records_count"] == 100
        assert "updated_at" in data


def test_get_nonexistent_watermark(tmp_path: Path) -> None:
    manager = JsonWatermarkManager(base_dir=tmp_path)
    assert manager.get(dataset="nonexistent", temporal_resolution="yearly") is None


def test_get_corrupted_watermark(tmp_path: Path) -> None:
    manager = JsonWatermarkManager(base_dir=tmp_path)
    target_dir = tmp_path / "carbon_intensity" / "yearly"
    target_dir.mkdir(parents=True, exist_ok=True)
    corrupted_file = target_dir / "watermark.json"
    corrupted_file.write_text("invalid json", encoding="utf-8")

    assert manager.get(dataset="carbon-intensity", temporal_resolution="yearly") is None