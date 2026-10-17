"""Live integration test for InsightsAgent with real Oracle ADW and Gemini API."""
import os
from dotenv import load_dotenv
import pytest

from helios.agent.insights_agent import InsightsAgent
from helios.agent.prompts import EnergyInsightReport
from helios.db.connector import OracleDatabaseConnector

load_dotenv()

db_core_user = os.getenv("HELIOS_CORE_USER")
db_core_password = os.getenv("HELIOS_CORE_PASSWORD")
oracle_dsn = os.getenv("ORACLE_DSN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

db_configured = bool(db_core_user and db_core_password and oracle_dsn and gemini_api_key)
pytestmark = pytest.mark.skipif(
    not db_configured,
    reason="Oracle CORE DB credentials or GEMINI_API_KEY not set in environment.",
)


def test_insights_agent_live_generation() -> None:
    """Live test: generate real AI report for Poland 2023 and persist in Oracle ADW."""
    connector = OracleDatabaseConnector(
        user=db_core_user,
        password=db_core_password,
        dsn=oracle_dsn,
        wallet_dir=os.getenv("ORACLE_WALLET_DIR"),
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD"),
    )

    agent = InsightsAgent(connector=connector)

    report = agent.generate_and_save_country_insight(
        entity_code="POL",
        year=2023,
    )

    # 1. Verification of the returned Pydantic object (EnergyInsightReport)
    assert isinstance(report, EnergyInsightReport)
    assert report.title
    assert report.summary
    assert report.full_markdown_report
    assert report.renewable_trend in ("Growth", "Stable", "Decline")

    # 2. Verification of the record in the database through the SmartDB analytical view
    with connector.acquire_connection() as conn:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    insight_id,
                    entity_code,
                    period_year,
                    title,
                    summary_text,
                    is_latest,
                    prompt_tokens,
                    completion_tokens
                FROM helios_core.v_ai_insights_overview
                WHERE entity_code = 'POL'
                  AND period_year = 2023
                  AND is_latest = 'Y'
            """
            cursor.execute(sql)
            row = cursor.fetchone()

            assert row is not None
            assert row[1] == "POL"
            assert row[2] == 2023
            assert row[3] == report.title
            assert row[5] == "Y"
            assert row[6] is not None and row[6] > 0  # prompt_tokens
            assert row[7] is not None and row[7] > 0  # completion_tokens
