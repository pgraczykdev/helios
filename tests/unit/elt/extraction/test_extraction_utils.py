
from helios.elt.extraction.extraction_utils import normalize_date, normalize_dataset_prefix


def test_normalize_date() -> None:
    assert normalize_date(date_str="2024-06-01T00:00:00") == "2024-06-01"
    assert normalize_date(date_str="2024-06-01") == "2024-06-01"
    assert normalize_date(date_str="2024") == "2024"


def test_normalize_dataset_prefix() -> None:
    assert normalize_dataset_prefix(dataset_prefix="carbon-intensity") == "carbon_intensity"
