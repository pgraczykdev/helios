from pathlib import Path
import json     


from helios.elt.extraction.watermark import normalize_date, read_watermark, save_watermark

def test_normalize_date():
    assert normalize_date(date_str="2024-06-01T00:00:00") == "2024-06-01"
    assert normalize_date(date_str="2024-06-01") == "2024-06-01"
    assert normalize_date(date_str="2024") == "2024"


def test_save_and_read_watermark(tmp_path: Path):
    watermark_file = tmp_path / "watermark.json"

    saved_path = save_watermark(
        target_dir=tmp_path,
        watermark="2024-06-01",
        dataset="test_dataset",
        temporal_resolution="yearly",
        records_count=100,
    )

    # Ensure the watermark file path matches the returned path
    assert saved_path is not None
    assert saved_path.exists()
    assert saved_path == watermark_file

    read_date = read_watermark(target_dir=tmp_path)
    assert read_date == "2024-06-01"

    # Verify the contents of the watermark file
    with open(file=watermark_file, mode="r", encoding="utf-8") as file:
        data = json.load(file)
        assert data["watermark"] == "2024-06-01"
        assert data["dataset"] == "test_dataset"
        assert data["temporal_resolution"] == "yearly"
        assert data["records_count"] == 100
        assert "updated_at" in data



def test_read_nonexistent_watermark(tmp_path: Path):
    read_date = read_watermark(target_dir=tmp_path)
    assert read_date is None



def test_read_invalid_watermark(tmp_path: Path):
    watermark_file = tmp_path / "watermark.json"
    # Create an invalid JSON file
    with open(file=watermark_file, mode="w", encoding="utf-8") as file:
        file.write("invalid json")

    read_date = read_watermark(target_dir=tmp_path)
    assert read_date is None

