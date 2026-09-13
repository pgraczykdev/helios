import json
import os
import requests
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from typing import Any

load_dotenv()

API_KEY = os.getenv("EMBER_API_KEY")
BASE_URL = os.getenv("EMBER_API_URL")
DEFAULT_TIMEOUT = 60


def get_latest_available_date_option(dataset: str, temporal_resolution: str) -> str | None:
    """Fetches the latest available date for Ember data."""
    date_option = "date"
    url = f"{BASE_URL}/v1/options/{dataset}/{temporal_resolution}/{date_option}"
    params = {"api_key": API_KEY}

    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        date_options = payload.get("options", [])
        return max(date_options, default=None)

    except requests.RequestException as e:
        print(f"Error fetching latest available date option: {e}")
        return None


def extract_electricity_generation(period: str) -> list[dict[str, Any]] | None:
    """Extracts electricity generation data for the given period."""
    url = f"{BASE_URL}/v1/electricity-generation/{period}"
    params = {"api_key": API_KEY}

    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", [])

    except requests.RequestException as e:
        print(f"Error fetching electricity generation data: {e}")
        return None


def read_latest_date_in_raw_data(target_dir: Path) -> str | None:
    """Reads the latest date from the JSON files in the specified target directory."""
    raise NotImplementedError("Function read_latest_date_in_raw_data is not yet implemented.")


def save_to_json(data: list[dict[str, Any]], target_dir: Path, filename: str) -> Path | None:
    """Saves the given data to a JSON file at the specified target_dir and filename."""
    target_dir.mkdir(parents=True, exist_ok=True)
    filepath = target_dir / filename
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        return filepath
    except IOError as e:
        print(f"Error saving data to {filepath}: {e}")
        return None


if __name__ == "__main__":
    print(get_latest_available_date_option("electricity-generation", "yearly"))
