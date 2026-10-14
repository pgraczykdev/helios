CREATE OR REPLACE PACKAGE BODY helios_apex.pkg_apex_queries AS
/**
 * Package Body: PKG_APEX_QUERIES
 * Purpose: SQL Macro (TABLE) queries provider for Oracle APEX application regions and charts.
 */

    FUNCTION f_summary_kpi_cards(
        p_country IN VARCHAR2 DEFAULT NULL,
        p_year    IN NUMBER   DEFAULT NULL
    ) RETURN VARCHAR2 SQL_MACRO(TABLE) IS
    BEGIN
        RETURN q'[
            SELECT
                'ENTITY_INFO'                                              AS kpi_key,
                entity_name || ' (' || entity_code || ')'                  AS kpi_title,
                year_num                                                   AS metric_val,
                CAST(NULL AS VARCHAR2(20 CHAR))                            AS metric_unit,
                CAST(NULL AS NUMBER)                                       AS yoy_val,
                CAST(NULL AS VARCHAR2(20 CHAR))                            AS yoy_unit,
                1                                                          AS is_positive,
                CASE WHEN is_aggregate_entity = 1 THEN 'Regional Aggregate' ELSE 'Sovereign Country' END AS sub_text,
                'fa-globe'                                                 AS kpi_icon
            FROM v_renewables_mix_overview
            WHERE entity_code = NVL(p_country, 'POL')
              AND temporal_resolution = 'yearly'
              AND year_num = NVL(p_year, 2023)
            UNION ALL
            SELECT
                'RENEWABLES'                                               AS kpi_key,
                'Renewables Share'                                         AS kpi_title,
                ROUND(renewables_share_pct, 1)                             AS metric_val,
                '%'                                                        AS metric_unit,
                ROUND(yoy_renewables_share_change_pp, 1)                   AS yoy_val,
                'pp'                                                       AS yoy_unit,
                CASE WHEN yoy_renewables_share_change_pp >= 0 THEN 1 ELSE 0 END AS is_positive,
                CAST(NULL AS VARCHAR2(100 CHAR))                           AS sub_text,
                'fa-leaf'                                                  AS kpi_icon
            FROM v_renewables_mix_overview
            WHERE entity_code = NVL(p_country, 'POL')
              AND temporal_resolution = 'yearly'
              AND year_num = NVL(p_year, 2023)
            UNION ALL
            SELECT
                'SOLAR_WIND'                                               AS kpi_key,
                'Solar & Wind Share'                                       AS kpi_title,
                ROUND(solar_wind_share_pct, 1)                             AS metric_val,
                '%'                                                        AS metric_unit,
                CAST(NULL AS NUMBER)                                       AS yoy_val,
                CAST(NULL AS VARCHAR2(20 CHAR))                            AS yoy_unit,
                1                                                          AS is_positive,
                TO_CHAR(ROUND(solar_twh + wind_twh, 1)) || ' TWh'          AS sub_text,
                'fa-sun-o'                                                 AS kpi_icon
            FROM v_renewables_mix_overview
            WHERE entity_code = NVL(p_country, 'POL')
              AND temporal_resolution = 'yearly'
              AND year_num = NVL(p_year, 2023)
            UNION ALL
            SELECT
                'TOTAL_GEN'                                                AS kpi_key,
                'Total Generation'                                         AS kpi_title,
                ROUND(total_generation_twh, 1)                             AS metric_val,
                'TWh'                                                      AS metric_unit,
                CAST(NULL AS NUMBER)                                       AS yoy_val,
                CAST(NULL AS VARCHAR2(20 CHAR))                            AS yoy_unit,
                1                                                          AS is_positive,
                'Clean: ' || TO_CHAR(ROUND(clean_share_pct, 1)) || '%'     AS sub_text,
                'fa-bolt'                                                  AS kpi_icon
            FROM v_renewables_mix_overview
            WHERE entity_code = NVL(p_country, 'POL')
              AND temporal_resolution = 'yearly'
              AND year_num = NVL(p_year, 2023)
            UNION ALL
            SELECT
                'CARBON_INTENSITY'                                         AS kpi_key,
                'Carbon Intensity'                                         AS kpi_title,
                ROUND(emissions_intensity_gco2_per_kwh)                    AS metric_val,
                'gCO2/kWh'                                                 AS metric_unit,
                ROUND(yoy_intensity_change_gco2, 1)                        AS yoy_val,
                'g/kWh'                                                    AS yoy_unit,
                CASE WHEN yoy_intensity_change_gco2 <= 0 THEN 1 ELSE 0 END AS is_positive,
                CAST(NULL AS VARCHAR2(100 CHAR))                           AS sub_text,
                'fa-cloud'                                                 AS kpi_icon
            FROM v_fact_carbon_intensity_analytics
            WHERE entity_code = NVL(p_country, 'POL')
              AND temporal_resolution = 'yearly'
              AND year_num = NVL(p_year, 2023)
        ]';
    END f_summary_kpi_cards;

    FUNCTION f_summary_fuel_mix(
        p_country IN VARCHAR2 DEFAULT NULL,
        p_year    IN NUMBER   DEFAULT NULL
    ) RETURN VARCHAR2 SQL_MACRO(TABLE) IS
    BEGIN
        RETURN q'[
            SELECT
                series_name,
                series_category,
                generation_twh,
                share_of_generation_pct
            FROM v_fact_generation_analytics
            WHERE entity_code = NVL(p_country, 'POL')
              AND temporal_resolution = 'yearly'
              AND year_num = NVL(p_year, 2023)
              AND is_aggregate_series = 0
            ORDER BY generation_twh DESC
        ]';
    END f_summary_fuel_mix;

    FUNCTION f_summary_generation_history(
        p_country        IN VARCHAR2 DEFAULT NULL,
        p_year           IN NUMBER   DEFAULT NULL,
        p_lookback_years IN NUMBER   DEFAULT 9
    ) RETURN VARCHAR2 SQL_MACRO(TABLE) IS
    BEGIN
        RETURN q'[
            SELECT
                TO_CHAR(year_num) AS year_label,
                series_name,
                generation_twh
            FROM v_fact_generation_analytics
            WHERE entity_code = NVL(p_country, 'POL')
              AND temporal_resolution = 'yearly'
              AND is_aggregate_series = 0
              AND year_num BETWEEN NVL(p_year, 2023) - NVL(p_lookback_years, 9) AND NVL(p_year, 2023)
            ORDER BY year_num, generation_twh DESC
        ]';
    END f_summary_generation_history;

    FUNCTION f_global_renewables_ranking(
        p_year IN NUMBER DEFAULT NULL
    ) RETURN VARCHAR2 SQL_MACRO(TABLE) IS
    BEGIN
        RETURN q'[
            SELECT
                DENSE_RANK() OVER (ORDER BY m.renewables_share_pct DESC) AS rank_num,
                m.entity_name,
                m.entity_code,
                ROUND(m.renewables_share_pct, 1)        AS renewables_share_pct,
                ROUND(m.renewables_twh, 2)              AS renewables_generation_twh,
                ROUND(m.total_generation_twh, 2)        AS total_generation_twh,
                ROUND(m.clean_share_pct, 1)             AS clean_share_pct
            FROM v_renewables_mix_overview m
            WHERE m.temporal_resolution = 'yearly'
              AND m.year_num = NVL(p_year, 2023)
              AND m.is_aggregate_entity = 0
            ORDER BY m.renewables_share_pct DESC
        ]';
    END f_global_renewables_ranking;

    FUNCTION f_global_top_renewables(
        p_year  IN NUMBER DEFAULT NULL,
        p_limit IN NUMBER DEFAULT 15
    ) RETURN VARCHAR2 SQL_MACRO(TABLE) IS
    BEGIN
        RETURN q'[
            SELECT
                m.entity_name,
                m.entity_code,
                ROUND(m.renewables_share_pct, 1) AS renewables_share_pct,
                ROUND(m.total_generation_twh, 1) AS total_generation_twh
            FROM v_renewables_mix_overview m
            WHERE m.temporal_resolution = 'yearly'
              AND m.year_num = NVL(p_year, 2023)
              AND m.is_aggregate_entity = 0
              AND m.total_generation_twh >= 1.0
            ORDER BY m.renewables_share_pct DESC
            FETCH FIRST NVL(p_limit, 15) ROWS ONLY
        ]';
    END f_global_top_renewables;

    FUNCTION f_system_logs(
        p_filter_type IN VARCHAR2 DEFAULT 'ALL'
    ) RETURN VARCHAR2 SQL_MACRO(TABLE) IS
    BEGIN
        RETURN q'[
            SELECT
                l.id,
                l.time_stamp,
                l.logger_level,
                CASE l.logger_level
                    WHEN 1   THEN 'OFF'
                    WHEN 2   THEN 'PERMANENT'
                    WHEN 4   THEN 'ERROR'
                    WHEN 8   THEN 'WARNING'
                    WHEN 16  THEN 'INFORMATION'
                    WHEN 32  THEN 'TIMING'
                    WHEN 64  THEN 'DEBUG'
                    WHEN 128 THEN 'SYS_CONTEXT'
                    ELSE 'LEVEL_' || TO_CHAR(l.logger_level)
                END AS level_name,
                l.scope,
                l.text,
                l.call_stack,
                l.extra,
                l.user_name,
                l.client_identifier,
                l.line_no
            FROM logger_logs l
            WHERE (
                p_filter_type = 'ALL'
                OR (p_filter_type = 'ERRORS' AND l.logger_level <= 8)
                OR (p_filter_type = 'ELT' AND l.scope LIKE 'pkg_ember_elt%')
            )
            ORDER BY l.id DESC
        ]';
    END f_system_logs;

    FUNCTION f_get_current_logger_level RETURN VARCHAR2 IS
    BEGIN
        RETURN logger.get_pref('LEVEL');
    END f_get_current_logger_level;

    PROCEDURE p_set_logger_level(
        p_level IN VARCHAR2
    ) IS
        l_level VARCHAR2(30 CHAR) := UPPER(TRIM(p_level));
    BEGIN
        IF l_level = 'INFO' THEN
            l_level := 'INFORMATION';
        END IF;
        logger.set_level(p_level => l_level);
    END p_set_logger_level;

    FUNCTION f_lov_logger_levels RETURN VARCHAR2 SQL_MACRO(TABLE) IS
    BEGIN
        RETURN q'[
            SELECT
                logger.convert_level_num_to_char(lvl_order) AS d,
                logger.convert_level_num_to_char(lvl_order) AS r,
                lvl_order                            
            FROM (
                  SELECT 16 AS lvl_order FROM dual UNION ALL
                  SELECT 8 AS lvl_order FROM dual UNION ALL
                  SELECT 4 AS lvl_order FROM dual UNION ALL
                  SELECT 2 AS lvl_order FROM dual
                ) 
        ]';
    END f_lov_logger_levels;

END pkg_apex_queries;
/
