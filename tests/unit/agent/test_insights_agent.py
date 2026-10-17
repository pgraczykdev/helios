"""Unit tests for InsightsAgent with mocked database and Gemini client."""
from http import HTTPStatus
from unittest.mock import MagicMock
import pytest
from google.genai import errors

from helios.agent.exceptions import (
    AgentQuotaExceededError,
    AgentResponseValidationError,
    AgentServiceUnavailableError,
)
from helios.agent.insights_agent import InsightsAgent
from helios.agent.prompts import EnergyInsightReport
from helios.db.connector import DatabaseConnector


@pytest.fixture
def mock_db():
    """Fixture providing mocked DatabaseConnector, connection, and cursor."""
    mock_connector = MagicMock(spec=DatabaseConnector)
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connector.acquire_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    return mock_connector, mock_cursor


@pytest.fixture
def sample_report() -> EnergyInsightReport:
    """Fixture providing a sample EnergyInsightReport instance."""
    return EnergyInsightReport(
        title="Poland 2023 Clean Energy Transition",
        summary="- Renewable share reached 26.9%\n- Solar and wind led the addition",
        key_drivers="PV boom, Onshore wind additions",
        renewable_trend="Growth",
        full_markdown_report="# Full Executive Summary\n\nPoland accelerated decarbonization...",
    )


def test_fetch_country_mix_data_success(mock_db) -> None:
    """Verify fetching and mapping country mix data from database view."""
    connector, cursor = mock_db
    agent = InsightsAgent(connector=connector, client=MagicMock())

    cursor.description = [
        ("ENTITY_ID",),
        ("ENTITY_CODE",),
        ("ENTITY_NAME",),
        ("YEAR_NUM",),
        ("TOTAL_GENERATION_TWH",),
        ("RENEWABLES_TWH",),
        ("RENEWABLES_SHARE_PCT",),
    ]
    cursor.fetchone.return_value = (10, "POL", "Poland", 2023, 165.4, 44.5, 26.91)

    entity_id, row_dict = agent._fetch_country_mix_data(
        cursor=cursor,
        entity_code="POL",
        year=2023,
    )

    assert entity_id == 10
    assert row_dict["entity_code"] == "POL"
    assert row_dict["year_num"] == 2023
    assert row_dict["total_generation_twh"] == 165.4
    cursor.execute.assert_called_once()


def test_fetch_country_mix_data_not_found(mock_db) -> None:
    """Verify ValueError when query returns no row."""
    connector, cursor = mock_db
    agent = InsightsAgent(connector=connector, client=MagicMock())

    cursor.fetchone.return_value = None

    with pytest.raises(ValueError, match="No analytical data available"):
        agent._fetch_country_mix_data(
            cursor=cursor,
            entity_code="XYZ",
            year=2099,
        )


def test_save_insight(mock_db, sample_report) -> None:
    """Verify parameters passed to INSERT statement into FACT_AI_INSIGHTS."""
    connector, cursor = mock_db
    agent = InsightsAgent(connector=connector, client=MagicMock(), model_name="gemini-3.8-flash")

    agent._save_insight(
        cursor=cursor,
        entity_id=10,
        year=2023,
        report=sample_report,
        prompt_tokens=150,
        completion_tokens=320,
    )

    cursor.execute.assert_called_once()
    call_kwargs = cursor.execute.call_args[1]
    assert call_kwargs["entity_id"] == 10
    assert call_kwargs["period_year"] == 2023
    assert call_kwargs["insight_type"] == "EXECUTIVE_SUMMARY"
    assert call_kwargs["title"] == sample_report.title
    assert call_kwargs["summary_text"] == sample_report.summary
    assert call_kwargs["full_content"] == sample_report.full_markdown_report
    assert call_kwargs["model_name"] == "gemini-3.8-flash"
    assert call_kwargs["prompt_tokens"] == 150
    assert call_kwargs["completion_tokens"] == 320


def test_generate_and_save_country_insight_full_flow(mock_db, sample_report) -> None:
    """Verify full end-to-end orchestration with mocked Gemini response."""
    connector, cursor = mock_db
    mock_client = MagicMock()

    # Mock DB fetch
    cursor.description = [
        ("ENTITY_ID",),
        ("ENTITY_CODE",),
        ("ENTITY_NAME",),
        ("YEAR_NUM",),
        ("TOTAL_GENERATION_TWH",),
        ("RENEWABLES_TWH",),
        ("RENEWABLES_SHARE_PCT",),
        ("PREV_YEAR_RENEWABLES_SHARE_PCT",),
        ("YOY_RENEWABLES_SHARE_CHANGE_PP",),
        ("FOSSIL_TWH",),
        ("FOSSIL_SHARE_PCT",),
        ("NUCLEAR_TWH",),
        ("CLEAN_TOTAL_TWH",),
        ("CLEAN_SHARE_PCT",),
        ("SOLAR_TWH",),
        ("WIND_TWH",),
        ("HYDRO_TWH",),
        ("NET_IMPORTS_TWH",),
    ]
    cursor.fetchone.return_value = (
        10, "POL", "Poland", 2023, 165.4, 44.5, 26.91, 21.01, 5.9,
        110.2, 66.63, 0.0, 44.5, 26.91, 11.35, 22.12, 2.41, 4.10,
    )

    # Mock Gemini response
    mock_response = MagicMock()
    mock_response.parsed = sample_report
    mock_response.usage_metadata.prompt_token_count = 142
    mock_response.usage_metadata.candidates_token_count = 280
    mock_client.models.generate_content.return_value = mock_response

    agent = InsightsAgent(
        connector=connector,
        client=mock_client,
        model_name="gemini-3.8-flash",
    )

    result_report = agent.generate_and_save_country_insight(
        entity_code="POL",
        year=2023,
    )

    assert result_report == sample_report
    mock_client.models.generate_content.assert_called_once()
    assert cursor.execute.call_count == 2


def test_generate_insight_quota_exceeded_retries_and_raises(mock_db) -> None:
    """Verify retries on HTTP 429 and raising AgentQuotaExceededError."""
    connector, cursor = mock_db
    mock_client = MagicMock()

    cursor.description = [("ENTITY_ID",), ("ENTITY_CODE",), ("ENTITY_NAME",), ("YEAR_NUM",)]
    cursor.fetchone.return_value = (10, "POL", "Poland", 2023)

    mock_error = errors.APIError(
        code=HTTPStatus.TOO_MANY_REQUESTS.value,
        response_json={"message": "Resource exhausted"},
    )
    mock_client.models.generate_content.side_effect = mock_error

    agent = InsightsAgent(
        connector=connector,
        client=mock_client,
        max_retries=2,
        backoff_seconds=0.0,
    )

    with pytest.raises(AgentQuotaExceededError, match="API quota exhausted"):
        agent.generate_and_save_country_insight(entity_code="POL", year=2023)

    assert mock_client.models.generate_content.call_count == 2


def test_generate_insight_service_unavailable_retries_and_raises(mock_db) -> None:
    """Verify retries on HTTP 503 and raising AgentServiceUnavailableError."""
    connector, cursor = mock_db
    mock_client = MagicMock()

    cursor.description = [("ENTITY_ID",), ("ENTITY_CODE",), ("ENTITY_NAME",), ("YEAR_NUM",)]
    cursor.fetchone.return_value = (10, "POL", "Poland", 2023)

    mock_error = errors.APIError(
        code=HTTPStatus.SERVICE_UNAVAILABLE.value,
        response_json={"message": "Service unavailable"},
    )
    mock_client.models.generate_content.side_effect = mock_error

    agent = InsightsAgent(
        connector=connector,
        client=mock_client,
        max_retries=2,
        backoff_seconds=0.0,
    )

    with pytest.raises(AgentServiceUnavailableError, match="service unavailable"):
        agent.generate_and_save_country_insight(entity_code="POL", year=2023)

    assert mock_client.models.generate_content.call_count == 2


def test_generate_insight_retry_success(mock_db, sample_report) -> None:
    """Verify that a successful retry after a transient 429 returns the report."""
    connector, cursor = mock_db
    mock_client = MagicMock()

    cursor.description = [("ENTITY_ID",), ("ENTITY_CODE",), ("ENTITY_NAME",), ("YEAR_NUM",)]
    cursor.fetchone.return_value = (10, "POL", "Poland", 2023)

    mock_error = errors.APIError(
        code=HTTPStatus.TOO_MANY_REQUESTS.value,
        response_json={"message": "Temporary rate limit"},
    )
    mock_success_response = MagicMock()
    mock_success_response.parsed = sample_report
    mock_success_response.usage_metadata.prompt_token_count = 100
    mock_success_response.usage_metadata.candidates_token_count = 200

    mock_client.models.generate_content.side_effect = [mock_error, mock_success_response]

    agent = InsightsAgent(
        connector=connector,
        client=mock_client,
        max_retries=3,
        backoff_seconds=0.0,
    )

    result = agent.generate_and_save_country_insight(entity_code="POL", year=2023)

    assert result == sample_report
    assert mock_client.models.generate_content.call_count == 2


def test_generate_insight_unparsed_response_raises(mock_db) -> None:
    """Verify AgentResponseValidationError when response.parsed is None."""
    connector, cursor = mock_db
    mock_client = MagicMock()

    cursor.description = [("ENTITY_ID",), ("ENTITY_CODE",), ("ENTITY_NAME",), ("YEAR_NUM",)]
    cursor.fetchone.return_value = (10, "POL", "Poland", 2023)

    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = "I cannot fulfill this request due to safety filters."
    mock_client.models.generate_content.return_value = mock_response

    agent = InsightsAgent(
        connector=connector,
        client=mock_client,
        max_retries=1,
        backoff_seconds=0.0,
    )

    with pytest.raises(AgentResponseValidationError, match="returned an empty or unparsed response"):
        agent.generate_and_save_country_insight(entity_code="POL", year=2023)
