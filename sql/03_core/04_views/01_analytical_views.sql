-- ----------------------------------------------------------------------------
-- 1. V_FACT_GENERATION_ANALYTICS
--  Analytical view for generation metrics with YoY calculations
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW helios_core.v_fact_generation_analytics AS
WITH gen_base AS (
    SELECT
        f.fact_id,
        e.entity_code,
        e.entity_name,
        e.is_aggregate AS is_aggregate_entity,
        s.series_name,
        s.series_category,
        s.is_aggregate AS is_aggregate_series,
        p.temporal_resolution,
        p.raw_date,
        p.period_date,
        p.year_num,
        p.month_num,
        p.quarter_num,
        p.period_label,
        f.generation_twh,
        f.share_of_generation_pct,
        -- Generacja z tego samego okresu poprzedniego roku:
        LAG(f.generation_twh, 1) OVER (
            PARTITION BY f.entity_id, f.series_id, p.temporal_resolution, p.month_num
            ORDER BY p.year_num
        ) AS prev_year_generation_twh
    FROM helios_core.fact_generation f
    INNER JOIN helios_core.dim_entity e ON e.entity_id = f.entity_id
    INNER JOIN helios_core.dim_series s ON s.series_id = f.series_id
    INNER JOIN helios_core.dim_period p ON p.period_id = f.period_id
)
SELECT
    fact_id,
    entity_code,
    entity_name,
    is_aggregate_entity,
    series_name,
    series_category,
    is_aggregate_series,
    temporal_resolution,
    raw_date,
    period_date,
    year_num,
    month_num,
    quarter_num,
    period_label,
    generation_twh,
    share_of_generation_pct,
    prev_year_generation_twh,
    ROUND(generation_twh - prev_year_generation_twh, 6) AS yoy_generation_change_twh,
    ROUND(
        ((generation_twh - prev_year_generation_twh) / NULLIF(prev_year_generation_twh, 0)) * 100,
        2
    ) AS yoy_generation_growth_pct
FROM gen_base;

COMMENT ON TABLE helios_core.v_fact_generation_analytics IS 'SmartDB View: Generation metrics with denormalized dimensions and
YoY window calculations';


-- ----------------------------------------------------------------------------
-- 2. V_RENEWABLES_MIX_OVERVIEW
-- Aggregated energy mix of the country with the share of renewables and YoY percentage point changes
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW helios_core.v_renewables_mix_overview AS
WITH mix_base AS (
    SELECT
        e.entity_id,
        e.entity_code,
        e.entity_name,
        e.is_aggregate AS is_aggregate_entity,
        p.temporal_resolution,
        p.raw_date,
        p.period_date,
        p.year_num,
        p.month_num,
        p.quarter_num,
        p.period_label,
        -- Sumy generacji per kategoria (wyłącznie paliwa elementarne is_aggregate = 0)
        SUM(CASE WHEN s.series_category = 'Renewables' THEN f.generation_twh ELSE 0 END) AS renewables_twh,
        SUM(CASE WHEN s.series_category = 'Fossil'     THEN f.generation_twh ELSE 0 END) AS fossil_twh,
        SUM(CASE WHEN s.series_category = 'Nuclear'    THEN f.generation_twh ELSE 0 END) AS nuclear_twh,
        SUM(CASE WHEN s.series_category IN ('Renewables', 'Nuclear', 'Clean') THEN f.generation_twh ELSE 0 END) AS
clean_total_twh,
        SUM(f.generation_twh) AS total_generation_twh,
        -- Kluczowe technologie OZE:
        SUM(CASE WHEN LOWER(s.series_name) = 'solar' THEN f.generation_twh ELSE 0 END) AS solar_twh,
        SUM(CASE WHEN LOWER(s.series_name) = 'wind'  THEN f.generation_twh ELSE 0 END) AS wind_twh,
        SUM(CASE WHEN LOWER(s.series_name) = 'hydro' THEN f.generation_twh ELSE 0 END) AS hydro_twh
    FROM helios_core.fact_generation f
    INNER JOIN helios_core.dim_entity e ON e.entity_id = f.entity_id
    INNER JOIN helios_core.dim_series s ON s.series_id = f.series_id
    INNER JOIN helios_core.dim_period p ON p.period_id = f.period_id
    WHERE s.is_aggregate = 0
    GROUP BY
        e.entity_id,
        e.entity_code,
        e.entity_name,
        e.is_aggregate,
        p.temporal_resolution,
        p.raw_date,
        p.period_date,
        p.year_num,
        p.month_num,
        p.quarter_num,
        p.period_label
),
mix_shares AS (
    SELECT
        entity_id,
        entity_code,
        entity_name,
        is_aggregate_entity,
        temporal_resolution,
        raw_date,
        period_date,
        year_num,
        month_num,
        quarter_num,
        period_label,
        ROUND(renewables_twh, 6) AS renewables_twh,
        ROUND(fossil_twh, 6) AS fossil_twh,
        ROUND(nuclear_twh, 6) AS nuclear_twh,
        ROUND(clean_total_twh, 6) AS clean_total_twh,
        ROUND(total_generation_twh, 6) AS total_generation_twh,
        ROUND(solar_twh, 6) AS solar_twh,
        ROUND(wind_twh, 6) AS wind_twh,
        ROUND(hydro_twh, 6) AS hydro_twh,
        -- Udziały procentowe w miksie:
        ROUND((renewables_twh  / NULLIF(total_generation_twh, 0)) * 100, 2) AS renewables_share_pct,
        ROUND((fossil_twh      / NULLIF(total_generation_twh, 0)) * 100, 2) AS fossil_share_pct,
        ROUND((clean_total_twh / NULLIF(total_generation_twh, 0)) * 100, 2) AS clean_share_pct,
        ROUND(((solar_twh + wind_twh) / NULLIF(total_generation_twh, 0)) * 100, 2) AS solar_wind_share_pct
    FROM mix_base
)
SELECT
    entity_code,
    entity_name,
    is_aggregate_entity,
    temporal_resolution,
    raw_date,
    period_date,
    year_num,
    month_num,
    quarter_num,
    period_label,
    renewables_twh,
    fossil_twh,
    nuclear_twh,
    clean_total_twh,
    total_generation_twh,
    solar_twh,
    wind_twh,
    hydro_twh,
    renewables_share_pct,
    fossil_share_pct,
    clean_share_pct,
    solar_wind_share_pct,
    -- Renewable share from the previous year:
    LAG(renewables_share_pct, 1) OVER (
        PARTITION BY entity_id, temporal_resolution, month_num
        ORDER BY year_num
    ) AS prev_year_renewables_share_pct,
    -- YoY change in renewable share in percentage points (pp):
    ROUND(
        renewables_share_pct - LAG(renewables_share_pct, 1) OVER (
            PARTITION BY entity_id, temporal_resolution, month_num
            ORDER BY year_num
        ),
        2
    ) AS yoy_renewables_share_change_pp
FROM mix_shares;

COMMENT ON TABLE helios_core.v_renewables_mix_overview IS 'SmartDB View: Aggregated fuel mix, renewable share, and YoY
percentage point changes for APEX maps and KPI cards';


-- ----------------------------------------------------------------------------
-- 3. V_FACT_CAPACITY_ANALYTICS
-- Analytics of installed renewable capacity (GW, W per capita) with YoY dynamics
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW helios_core.v_fact_capacity_analytics AS
WITH cap_base AS (
    SELECT
        f.fact_id,
        e.entity_code,
        e.entity_name,
        e.is_aggregate AS is_aggregate_entity,
        s.series_name,
        s.series_category,
        s.is_aggregate AS is_aggregate_series,
        p.temporal_resolution,
        p.raw_date,
        p.period_date,
        p.year_num,
        p.month_num,
        p.quarter_num,
        p.period_label,
        f.capacity_gw,
        f.capacity_w_per_capita,
        LAG(f.capacity_gw, 1) OVER (
            PARTITION BY f.entity_id, f.series_id, p.temporal_resolution, p.month_num
            ORDER BY p.year_num
        ) AS prev_year_capacity_gw,
        LAG(f.capacity_w_per_capita, 1) OVER (
            PARTITION BY f.entity_id, f.series_id, p.temporal_resolution, p.month_num
            ORDER BY p.year_num
        ) AS prev_year_w_per_capita
    FROM helios_core.fact_capacity f
    INNER JOIN helios_core.dim_entity e ON e.entity_id = f.entity_id
    INNER JOIN helios_core.dim_series s ON s.series_id = f.series_id
    INNER JOIN helios_core.dim_period p ON p.period_id = f.period_id
)
SELECT
    fact_id,
    entity_code,
    entity_name,
    is_aggregate_entity,
    series_name,
    series_category,
    is_aggregate_series,
    temporal_resolution,
    raw_date,
    period_date,
    year_num,
    month_num,
    quarter_num,
    period_label,
    capacity_gw,
    capacity_w_per_capita,
    prev_year_capacity_gw,
    ROUND(capacity_gw - prev_year_capacity_gw, 6) AS yoy_capacity_change_gw,
    ROUND(
        ((capacity_gw - prev_year_capacity_gw) / NULLIF(prev_year_capacity_gw, 0)) * 100,
        2
    ) AS yoy_capacity_growth_pct,
    prev_year_w_per_capita,
    ROUND(capacity_w_per_capita - prev_year_w_per_capita, 2) AS yoy_w_per_capita_change
FROM cap_base;

COMMENT ON TABLE helios_core.v_fact_capacity_analytics IS 'SmartDB View: Installed capacity metrics in GW and W/capita with YoY
growth dynamics';


-- ----------------------------------------------------------------------------
-- 4. V_FACT_CARBON_INTENSITY_ANALYTICS
-- Analytics of grid carbon intensity (gCO2/kWh) and decarbonization progress
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW helios_core.v_fact_carbon_intensity_analytics AS
WITH ci_base AS (
    SELECT
        f.fact_id,
        e.entity_code,
        e.entity_name,
        e.is_aggregate AS is_aggregate_entity,
        p.temporal_resolution,
        p.raw_date,
        p.period_date,
        p.year_num,
        p.month_num,
        p.quarter_num,
        p.period_label,
        f.emissions_intensity_gco2_per_kwh,
        LAG(f.emissions_intensity_gco2_per_kwh, 1) OVER (
            PARTITION BY f.entity_id, p.temporal_resolution, p.month_num
            ORDER BY p.year_num
        ) AS prev_year_intensity_gco2
    FROM helios_core.fact_carbon_intensity f
    INNER JOIN helios_core.dim_entity e ON e.entity_id = f.entity_id
    INNER JOIN helios_core.dim_period p ON p.period_id = f.period_id
)
SELECT
    fact_id,
    entity_code,
    entity_name,
    is_aggregate_entity,
    temporal_resolution,
    raw_date,
    period_date,
    year_num,
    month_num,
    quarter_num,
    period_label,
    emissions_intensity_gco2_per_kwh,
    prev_year_intensity_gco2,
    ROUND(emissions_intensity_gco2_per_kwh - prev_year_intensity_gco2, 2) AS yoy_intensity_change_gco2,
    ROUND(
        ((emissions_intensity_gco2_per_kwh - prev_year_intensity_gco2) / NULLIF(prev_year_intensity_gco2, 0)) * 100,
        2
    ) AS yoy_intensity_change_pct
FROM ci_base;

COMMENT ON TABLE helios_core.v_fact_carbon_intensity_analytics IS 'SmartDB View: Carbon intensity metrics with YoY
decarbonization progress';


-- ----------------------------------------------------------------------------
-- 5. V_FACT_DEMAND_ANALYTICS
-- Analytics of electricity demand and consumption
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW helios_core.v_fact_demand_analytics AS
WITH dem_base AS (
    SELECT
        f.fact_id,
        e.entity_code,
        e.entity_name,
        e.is_aggregate AS is_aggregate_entity,
        p.temporal_resolution,
        p.raw_date,
        p.period_date,
        p.year_num,
        p.month_num,
        p.quarter_num,
        p.period_label,
        f.demand_twh,
        f.demand_mwh_per_capita,
        LAG(f.demand_twh, 1) OVER (
            PARTITION BY f.entity_id, p.temporal_resolution, p.month_num
            ORDER BY p.year_num
        ) AS prev_year_demand_twh
    FROM helios_core.fact_demand f
    INNER JOIN helios_core.dim_entity e ON e.entity_id = f.entity_id
    INNER JOIN helios_core.dim_period p ON p.period_id = f.period_id
)
SELECT
    fact_id,
    entity_code,
    entity_name,
    is_aggregate_entity,
    temporal_resolution,
    raw_date,
    period_date,
    year_num,
    month_num,
    quarter_num,
    period_label,
    demand_twh,
    demand_mwh_per_capita,
    prev_year_demand_twh,
    ROUND(demand_twh - prev_year_demand_twh, 6) AS yoy_demand_change_twh,
    ROUND(
        ((demand_twh - prev_year_demand_twh) / NULLIF(prev_year_demand_twh, 0)) * 100,
        2
    ) AS yoy_demand_growth_pct
FROM dem_base;

COMMENT ON TABLE helios_core.v_fact_demand_analytics IS 'SmartDB View: Electricity demand and per capita consumption with YoY
growth';


-- ----------------------------------------------------------------------------
-- 6. V_FACT_EMISSIONS_ANALYTICS
-- Analytics of greenhouse gas emissions in the energy sector
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW helios_core.v_fact_emissions_analytics AS
WITH em_base AS (
    SELECT
        f.fact_id,
        e.entity_code,
        e.entity_name,
        e.is_aggregate AS is_aggregate_entity,
        s.series_name,
        s.series_category,
        s.is_aggregate AS is_aggregate_series,
        p.temporal_resolution,
        p.raw_date,
        p.period_date,
        p.year_num,
        p.month_num,
        p.quarter_num,
        p.period_label,
        f.emissions_mtco2,
        f.share_of_emissions_pct,
        LAG(f.emissions_mtco2, 1) OVER (
            PARTITION BY f.entity_id, f.series_id, p.temporal_resolution, p.month_num
            ORDER BY p.year_num
        ) AS prev_year_emissions_mtco2
    FROM helios_core.fact_emissions f
    INNER JOIN helios_core.dim_entity e ON e.entity_id = f.entity_id
    INNER JOIN helios_core.dim_series s ON s.series_id = f.series_id
    INNER JOIN helios_core.dim_period p ON p.period_id = f.period_id
)
SELECT
    fact_id,
    entity_code,
    entity_name,
    is_aggregate_entity,
    series_name,
    series_category,
    is_aggregate_series,
    temporal_resolution,
    raw_date,
    period_date,
    year_num,
    month_num,
    quarter_num,
    period_label,
    emissions_mtco2,
    share_of_emissions_pct,
    prev_year_emissions_mtco2,
    ROUND(emissions_mtco2 - prev_year_emissions_mtco2, 6) AS yoy_emissions_change_mtco2,
    ROUND(
        ((emissions_mtco2 - prev_year_emissions_mtco2) / NULLIF(prev_year_emissions_mtco2, 0)) * 100,
        2
    ) AS yoy_emissions_growth_pct
FROM em_base;

COMMENT ON TABLE helios_core.v_fact_emissions_analytics IS 'SmartDB View: Power sector emissions metrics and fuel shares with
YoY trends';