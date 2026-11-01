"""Prompt builder functions for the Helios AI agent."""
from typing import Any


def build_country_insight_prompt(country_data: dict[str, Any]) -> str:
    """Builds a structured prompt for the Helios AI agent based on country data."""
    entity_code = country_data.get("entity_code", "UNKNOWN")
    entity_name = country_data.get("entity_name", entity_code)
    year = country_data.get("year_num", "N/A")
    total_gen = country_data.get("total_generation_twh", 0.0)
    renewables_twh = country_data.get("renewables_twh", 0.0)
    renewables_share = country_data.get("renewables_share_pct", 0.0)
    prev_renewables_share = country_data.get("prev_year_renewables_share_pct")
    yoy_change_pp = country_data.get("yoy_renewables_share_change_pp")
    fossil_twh = country_data.get("fossil_twh", 0.0)
    fossil_share = country_data.get("fossil_share_pct", 0.0)
    nuclear_twh = country_data.get("nuclear_twh", 0.0)
    solar_twh = country_data.get("solar_twh", 0.0)
    wind_twh = country_data.get("wind_twh", 0.0)
    hydro_twh = country_data.get("hydro_twh", 0.0)
    clean_total = country_data.get("clean_total_twh", 0.0)
    clean_share = country_data.get("clean_share_pct", 0.0)
    net_imports = country_data.get("net_imports_twh", 0.0)

    yoy_str = f"{yoy_change_pp:+.2f} pp" if yoy_change_pp is not None else "No prior year data"
    prev_str = f"{prev_renewables_share:.2f}%" if prev_renewables_share is not None else "N/A"

    return f"""Analyze the power generation and decarbonization metrics for {entity_name} ({entity_code}) in {year}.

    ### Verified Database Metrics:
    - Total Electricity Generation: {total_gen:.2f} TWh
    - Renewables Generation: {renewables_twh:.2f} TWh ({renewables_share:.2f}% of total generation)
      * Solar: {solar_twh:.2f} TWh
      * Wind: {wind_twh:.2f} TWh
      * Hydro: {hydro_twh:.2f} TWh
    - Prior Year Renewable Share: {prev_str} (YoY Change: {yoy_str})
    - Fossil Fuels Generation: {fossil_twh:.2f} TWh ({fossil_share:.2f}% of total generation)
    - Nuclear Generation: {nuclear_twh:.2f} TWh
    - Clean Total (Renewables + Nuclear): {clean_total:.2f} TWh ({clean_share:.2f}% of total generation)
    - Net Imports / Cross-Border Flow: {net_imports:.2f} TWh

    ### Task:
    Synthesize an executive-ready insight report strictly adhering to the schema.
    1. Highlight whether renewables grew, stabilized, or declined compared to the prior year.
    2. Identify the dominant technologies driving the shift (e.g. solar vs. wind vs. coal).
    3. Provide the full markdown report with clear headings, comparison table, and key takeaways.""".strip()
