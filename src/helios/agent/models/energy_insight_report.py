from typing import ClassVar

from pydantic import BaseModel, Field


class EnergyInsightReport(BaseModel):
    """Structured Pydantic output schema for executive energy insights."""

    SYSTEM_INSTRUCTION: ClassVar[str] = """
        You are an energy transformation expert providing insights and analysis on the current trends and key drivers in the energy sector for Helios.
        Your task is to generate comprehensive energy insight reports based on the latest data from the database.
        RULES:
        1. No hallucinations, base all insights on the latest data from the database.
        2. Ensure clarity and conciseness in the report.
        3. Use professional and neutral language.
        4. Use English language for the report.
    """

    title: str = Field(..., description="Short, professional title of the energy insight report (max 100 characters)")
    summary: str = Field(..., description="Concise summary of the energy insight report in 2-3 bullet points for Oracle APEX card element")
    key_drivers: str = Field(..., description="List of 2-4 key drivers influencing the energy insight report")
    renewable_trend: str = Field(..., description="Description of the current trend in renewable energy adoption: (Growth, Stable, or Decline)")
    full_markdown_report: str = Field(..., description="Full energy insight report in markdown format")
