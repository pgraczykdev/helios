def normalize_date(date_str: str) -> str:
    """Normalize watermark string by stripping timestamp if present."""
    return str(date_str).split("T")[0]

def normalize_dataset_prefix(dataset_prefix: str) -> str:
    """Normalize dataset prefix by replacing hyphens with underscores."""
    return dataset_prefix.replace("-", "_")