"""Unit tests for agent prompts and Pydantic report schemas."""
import pytest
from pydantic import ValidationError

from helios.agent.prompts import (
    EnergyInsightReport,
    build_country_insight_prompt,
)


def test_energy_insight_report_valid() -> None:
    """Verify that EnergyInsightReport instantiates with valid attributes."""
    report = EnergyInsightReport(
        title="Poland 2023 Energy Mix Analysis",
        summary="- Renewables share grew by 5.9 pp\n- Solar and wind drove the growth",
        key_drivers="Solar PV installations, Onshore wind expansion",
        renewable_trend="Growth",
        full_markdown_report="# Poland 2023 Analysis\n\nFull content...",
    )
    assert report.title == "Poland 2023 Energy Mix Analysis"
    assert report.renewable_trend == "Growth"


def test_energy_insight_report_missing_field() -> None:
    """Verify validation error when required field is missing."""
    with pytest.raises(ValidationError):
        EnergyInsightReport(
            title="Incomplete Report",
            summary="Missing other fields",
        )


def test_build_country_insight_prompt_full_data() -> None:
    """Verify prompt formatting with complete metrics."""
    data = {
        "entity_code": "POL",
        "entity_name": "Poland",
        "year_num": 2023,
        "total_generation_twh": 165.4,
        "renewables_twh": 44.5,
        "renewables_share_pct": 26.91,
        "prev_year_renewables_share_pct": 21.01,
        "yoy_renewables_share_change_pp": 5.90,
        "fossil_twh": 110.2,
        "fossil_share_pct": 66.63,
        "nuclear_twh": 0.0,
        "solar_twh": 11.35,
        "wind_twh": 22.12,
        "hydro_twh": 2.41,
        "clean_total_twh": 44.5,
        "clean_share_pct": 26.91,
        "net_imports_twh": 4.10,
    }
    prompt = build_country_insight_prompt(country_data=data)

    assert "Poland (POL) in 2023" in prompt
    assert "Total Electricity Generation: 165.40 TWh" in prompt
    assert "Renewables Generation: 44.50 TWh (26.91%" in prompt
    assert "+5.90 pp" in prompt
    assert "Prior Year Renewable Share: 21.01%" in prompt


def test_build_country_insight_prompt_missing_prior_year() -> None:
    """Verify fallback string when prior year metrics are None."""
    data = {
        "entity_code": "DEU",
        "entity_name": "Germany",
        "year_num": 2000,
        "total_generation_twh": 500.0,
        "renewables_twh": 50.0,
        "renewables_share_pct": 10.0,
        "prev_year_renewables_share_pct": None,
        "yoy_renewables_share_change_pp": None,
    }
    prompt = build_country_insight_prompt(country_data=data)

    assert "Prior Year Renewable Share: N/A" in prompt
    assert "No prior year data" in prompt
