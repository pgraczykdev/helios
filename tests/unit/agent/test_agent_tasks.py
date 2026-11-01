"""Unit tests for Helios AI agent DAG tasks."""
import pytest
from unittest.mock import MagicMock
from helios.agent.insights_agent import InsightsAgent
from helios.db import OracleDatabaseConnector
from helios.elt.transform.models import TransformationResult, TransformationStatus
from helios.agent.insights_agent import DEFAULT_MAX_RETRIES, DEFAULT_INITIAL_BACKOFF_SECONDS
from helios.agent.models import InsightGenerationResult, InsightGenerationStatus
from helios.agent.tasks import generate_insights


@pytest.fixture
def mock_agent() -> InsightsAgent:
    """Fixture that provides a mock InsightsAgent."""

    connector = MagicMock(
        spec=OracleDatabaseConnector
    )

    return MagicMock(
        connector=connector,
        client=None,
        model_name="gemini-frontier",
        max_retries=DEFAULT_MAX_RETRIES,
        backoff_seconds=DEFAULT_INITIAL_BACKOFF_SECONDS,
    )


def test_generate_insights_positive() -> None:
    """Test the positive case for get_result."""
    mock_agent = MagicMock()

    result = generate_insights(
        insights_agent=mock_agent,
        transformation_result=None,
        entity_codes=["US", "PL", "DE", "ITA", "FR"],
        year=2024
    )

    assert result.status == InsightGenerationStatus.SUCCESS
    assert result.countries_processed == 5
    assert result.countries_failed == 0
    assert result.year == 2024
    assert result.error_message is None



def test_generate_insights_negative() -> None:
    """Test the negative case for generate_insights."""
    mock_agent = MagicMock()
    def raise_exception(*args, **kwargs):
        raise Exception("FAILED")
    mock_agent.generate_and_save_country_insight.side_effect = raise_exception

    result = generate_insights(
        insights_agent=mock_agent,
        transformation_result=None,
        entity_codes=["US"],
        year=2024
    )
    assert result.status == InsightGenerationStatus.FAILED
    assert result.year == 2024  
    assert result.countries_processed == 0
    assert result.countries_failed == 1
    assert result.error_message == "FAILED"



def test_generate_insights_transformation_error() -> None:
    """Test the case where the transformation result has an error."""
    mock_agent = MagicMock()
   
    result = generate_insights(
        insights_agent=mock_agent,
        transformation_result=TransformationResult(status=TransformationStatus.ERROR, error_message="Transformation failed"),
        entity_codes=["US"],
        year=2024
    )

    assert result.status == InsightGenerationStatus.SKIPPED
    assert result.error_message == "Transformation error: Transformation failed. Skipping insight generation."
    assert result.year == 2024
    assert result.countries_processed == 0
    assert result.countries_failed == 0
