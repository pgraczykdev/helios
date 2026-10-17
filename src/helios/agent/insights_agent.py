"""Module providing the InsightsAgent for generating and saving energy insight reports."""
from http import HTTPStatus
import logging
import os
import time
from typing import Any
from google import genai
from google.genai import errors
from google.genai import types

from helios.agent.exceptions import (
    AgentError,
    AgentQuotaExceededError,
    AgentResponseValidationError,
    AgentServiceUnavailableError,
)
from helios.agent.prompts import (
    EnergyInsightReport,
    build_country_insight_prompt,
)
from helios.db import DatabaseConnector

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES: int = 3
DEFAULT_INITIAL_BACKOFF_SECONDS: float = 2.0


class InsightsAgent:
    """An insights agent for generating and saving energy insight reports."""

    def __init__(
        self,
        connector: DatabaseConnector,
        client: genai.Client | None = None,
        model_name: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_INITIAL_BACKOFF_SECONDS,
    ) -> None:
        """Initializes the AI agent with a database connector, Gemini client, and retry parameters."""
        self.connector = connector
        self.client = client or genai.Client()
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def _fetch_country_mix_data(
        self,
        cursor: Any,
        entity_code: str,
        year: int,
    ) -> tuple[int, dict[str, Any]]:
        """Fetches a row of country energy mix data from the analytical view."""
        sql = """
            SELECT 
                e.entity_id,
                m.entity_code,
                m.entity_name,
                m.year_num,
                m.total_generation_twh,
                m.renewables_twh,
                m.renewables_share_pct,
                m.prev_year_renewables_share_pct,
                m.yoy_renewables_share_change_pp,
                m.fossil_twh,
                m.fossil_share_pct,
                m.nuclear_twh,
                m.clean_total_twh,
                m.clean_share_pct,
                m.solar_twh,
                m.wind_twh,
                m.hydro_twh,
                m.net_imports_twh
            FROM helios_core.v_renewables_mix_overview m
            INNER JOIN helios_core.dim_entity e ON e.entity_code = m.entity_code
            WHERE m.entity_code = :entity_code
              AND m.year_num = :year_num
              AND m.temporal_resolution = 'yearly'
        """
        cursor.execute(sql, entity_code=entity_code, year_num=year)
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"No analytical data available for country {entity_code} in year {year}")

        columns = [col[0].lower() for col in cursor.description]
        row_dict = dict(zip(columns, row))
        entity_id = row_dict["entity_id"]

        return entity_id, row_dict

    def _save_insight(
        self,
        cursor: Any,
        entity_id: int,
        year: int,
        report: EnergyInsightReport,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> None:
        """Saves the generated report to the FACT_AI_INSIGHTS fact table."""
        sql = """
            INSERT INTO helios_core.fact_ai_insights (
                entity_id,
                period_year,
                insight_type,
                title,
                summary_text,
                full_content,
                model_name,
                prompt_tokens,
                completion_tokens
            ) VALUES (
                :entity_id,
                :period_year,
                :insight_type,
                :title,
                :summary_text,
                :full_content,
                :model_name,
                :prompt_tokens,
                :completion_tokens
            )
        """
        cursor.execute(
            sql,
            entity_id=entity_id,
            period_year=year,
            insight_type="EXECUTIVE_SUMMARY",
            title=report.title,
            summary_text=report.summary,
            full_content=report.full_markdown_report,
            model_name=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def generate_and_save_country_insight(
        self,
        entity_code: str,
        year: int,
    ) -> EnergyInsightReport:
        """Generates an analytical report for a given country and year with retries and persists it in Oracle DWH."""
        logger.info(f"Starting AI analysis generation for {entity_code} ({year})...")

        with self.connector.acquire_connection() as conn:
            with conn.cursor() as cursor:
                entity_id, country_data = self._fetch_country_mix_data(
                    cursor=cursor,
                    entity_code=entity_code,
                    year=year,
                )

                prompt = build_country_insight_prompt(country_data=country_data)

                report: EnergyInsightReport | None = None
                prompt_tokens: int | None = None
                completion_tokens: int | None = None

                for attempt in range(1, self.max_retries + 1):
                    try:
                        logger.debug(
                            f"Calling ({self.model_name}), attempt {attempt}/{self.max_retries}..."
                        )
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=EnergyInsightReport.SYSTEM_INSTRUCTION,
                                response_mime_type="application/json",
                                response_schema=EnergyInsightReport,
                                temperature=0.2,
                            ),
                        )

                        if not response.parsed:
                            raise AgentResponseValidationError(
                                f"{self.model_name} returned an empty or unparsed response: {response.text}"
                            )

                        report = response.parsed

                        if response.usage_metadata:
                            prompt_tokens = response.usage_metadata.prompt_token_count
                            completion_tokens = response.usage_metadata.candidates_token_count

                        break

                    except errors.APIError as e:
                        err_detail = e.message or str(e)
                        if e.code == HTTPStatus.TOO_MANY_REQUESTS:
                            logger.warning(
                                f"{self.model_name} quota / rate limit exceeded (HTTP {e.code}). Attempt {attempt}/{self.max_retries}."
                            )
                            if attempt == self.max_retries:
                                raise AgentQuotaExceededError(
                                    f"{self.model_name} API quota exhausted after {self.max_retries} attempts: {err_detail}"
                                ) from e

                        elif e.code in (HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.SERVICE_UNAVAILABLE):
                            logger.warning(
                                f"{self.model_name} service unavailable (HTTP {e.code}). Attempt {attempt}/{self.max_retries}."
                            )
                            if attempt == self.max_retries:
                                raise AgentServiceUnavailableError(
                                    f"{self.model_name} service unavailable after {self.max_retries} attempts: {err_detail}"
                                ) from e

                        else:
                            logger.error(f"Non-retriable {self.model_name} API error (HTTP {e.code}): {err_detail}")
                            raise AgentError(f"{self.model_name} API error (HTTP {e.code}): {err_detail}") from e

                        if self.backoff_seconds > 0:
                            time.sleep(self.backoff_seconds * attempt)

                    except AgentResponseValidationError:
                        raise

                    except Exception as e:
                        logger.error(f"Unexpected error while invoking {self.model_name}: {e}")
                        raise AgentError(f"Unexpected {self.model_name} error: {e}") from e

                if report is None:
                    raise AgentError(f"Failed to obtain a valid report from {self.model_name}.")

                self._save_insight(
                    cursor=cursor,
                    entity_id=entity_id,
                    year=year,
                    report=report,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

                logger.info(
                    f"AI report for {entity_code} ({year}) saved successfully. "
                    f"Tokens: input={prompt_tokens}, output={completion_tokens}"
                )
                return report