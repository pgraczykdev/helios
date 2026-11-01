"""DAG Tasks for generating insights using the Helios AI agent."""
import os
from helios.db import DatabaseConnector, OracleDatabaseConnector
from helios.elt.transform.models import TransformationResult, TransformationStatus
from helios.agent.models import InsightGenerationResult, InsightGenerationStatus
from helios.agent import InsightsAgent



DEFAULT_TARGET_COUNTRIES: tuple[str, ...] = ("POL", "DEU", "FRA", "ESP", "ITA")
DEFAULT_TARGET_YEAR: int = 2023

def generate_insights(insights_agent: InsightsAgent | None = None,
                      transformation_result: TransformationResult | None = None,
                      entity_codes: list[str] | tuple[str, ...] = DEFAULT_TARGET_COUNTRIES,
                      year: int = DEFAULT_TARGET_YEAR) -> InsightGenerationResult:
    """Generate insights based on the transformation result."""

    if transformation_result is not None and transformation_result.status == TransformationStatus.ERROR:
        return InsightGenerationResult(
                            status=InsightGenerationStatus.SKIPPED,
                            year=year,
                            countries_processed=0,
                            countries_failed=0,
                            error_message=f"Transformation error: {transformation_result.error_message}. Skipping insight generation.")

    countries_processed = 0
    countries_failed = 0
    error_messages: list[str] = []

    connector: DatabaseConnector | None = None

    if insights_agent is None:
        user = os.getenv("HELIOS_CORE_USER")
        password = os.getenv("HELIOS_CORE_PASSWORD")
        connector = OracleDatabaseConnector(user=user, password=password)
        insights_agent = InsightsAgent(connector=connector)

    try:
        for entity_code in entity_codes:
            try:
                insights_agent.generate_and_save_country_insight(entity_code=entity_code, year=year)
                countries_processed += 1
            except Exception as e:
                countries_failed += 1
                error_messages.append(str(e))
    finally:
        if connector is not None:
            connector.close_pool()
                
    if countries_failed > 0:
        return InsightGenerationResult(status=InsightGenerationStatus.FAILED,
                                       year=year,
                                       countries_processed=countries_processed,
                                       countries_failed=countries_failed,
                                       error_message="; ".join(error_messages))
    
    return InsightGenerationResult(status=InsightGenerationStatus.SUCCESS,
                                   year=year,
                                   countries_processed=countries_processed,
                                   countries_failed=countries_failed,
                                   error_message=None)
