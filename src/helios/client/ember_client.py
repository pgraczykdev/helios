import logging
import os
from typing import Any
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class EmberClient:
    """HTTP client for communicating with the Ember Energy API (v1)."""
    
    DEFAULT_BASE_URL = "https://api.ember-energy.org"
    DEFAULT_TIMEOUT = 60  # seconds

    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Initialize the Ember API client."""
        self.api_key = api_key or os.getenv("EMBER_API_KEY")
        if not self.api_key:
            raise ValueError("Missing API key! Set the EMBER_API_KEY environment variable in .env "
                            "or pass 'api_key' directly to the constructor.")
        self.base_url = (base_url or os.getenv("EMBER_API_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Helios-ELT/1.0",
            "Accept": "application/json",
        })

    def __enter__(self) -> "EmberClient":
        """Support for context manager entry: with EmberClient() as client:"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Automatically close the session when exiting the 'with' block."""
        self.close()

    def close(self) -> None:
        """Close the underlying requests session and free up connections."""
        self.session.close()

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Internal helper method to execute a GET request and parse JSON."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        request_params: dict[str, Any] = {"api_key": self.api_key}
        if params:
            request_params.update(params)

        try:
            response = self.session.get(url, params=request_params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("Error querying endpoint %s: %s", url, exc)
            raise

    def get_latest_available_date(self, dataset: str, temporal_resolution: str) -> str | None:
        """Fetch the latest available date for a given dataset and temporal resolution."""
        endpoint = f"/v1/options/{dataset}/{temporal_resolution}/date"
        try:
            payload = self._get(endpoint)
            date_options = payload.get("options", [])
            if not date_options:
                return None
            latest = max(date_options)
            return str(latest)
        except requests.RequestException:
            return None

    def get_electricity_generation(
        self,
        temporal_resolution: str = "yearly",
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch electricity generation data for the given temporal resolution."""
        endpoint = f"/v1/electricity-generation/{temporal_resolution}"
        payload = self._get(endpoint, params=params)
        return payload.get("data", [])
