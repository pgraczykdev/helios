from dotenv import load_dotenv
import os
import pytest

from helios.client.ember_client import EmberClient

load_dotenv()

api_key_present = bool(os.getenv("EMBER_API_KEY"))

pytestmark = pytest.mark.skipif(not api_key_present, reason="EMBER_API_KEY not set")

def test_ember_client_get_latest_available_date() -> None:
    """Integration test for EmberClient's get_latest_available_date method."""
    with EmberClient(api_key=os.getenv("EMBER_API_KEY")) as client:
        latest_date = client.get_latest_available_date(dataset="electricity-generation", temporal_resolution="yearly")
        assert latest_date is not None
        assert isinstance(latest_date, str)


def test_ember_client_get_data() -> None:
    """Integration test for EmberClient's get_data method."""
    with EmberClient(api_key=os.getenv("EMBER_API_KEY")) as client:
        data = client._get( 
            endpoint="/v1/electricity-generation/yearly",
            params={"start_date": "2023", "end_date": "2023"},
        )
        assert data is not None
        assert "data" in data
        records = data["data"]

        sample_data = records[0]
        assert "entity" in sample_data
        assert "date" in sample_data
        assert "series" in sample_data

