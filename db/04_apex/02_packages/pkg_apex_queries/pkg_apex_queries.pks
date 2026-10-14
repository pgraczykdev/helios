CREATE OR REPLACE PACKAGE helios_apex.pkg_apex_queries AS
/**
 * Package: PKG_APEX_QUERIES
 * Purpose: SQL Macro (TABLE) queries provider for Oracle APEX application regions and charts.
 *          Encapsulates UI queries in the database layer, eliminating hardcoded SQL in APEX.
 * Author:  Helios Platform Team
 */

    /**
     * Returns KPI cards for the Executive Dashboard (Summary page).
     * Includes an active entity/country context card as the first item.
     *
     * @param p_country ISO-3 country code (e.g. 'POL')
     * @param p_year    Year number (e.g. 2023)
     * @return SQL query text inlined at parse-time by Oracle CBO
     */
    FUNCTION f_summary_kpi_cards(
        p_country IN VARCHAR2 DEFAULT NULL,
        p_year    IN NUMBER   DEFAULT NULL
    ) RETURN VARCHAR2 SQL_MACRO(TABLE);

    /**
     * Returns fuel mix generation breakdown (shares) for the Donut chart.
     *
     * @param p_country ISO-3 country code (e.g. 'POL')
     * @param p_year    Year number (e.g. 2023)
     * @return SQL query text inlined at parse-time
     */
    FUNCTION f_summary_fuel_mix(
        p_country IN VARCHAR2 DEFAULT NULL,
        p_year    IN NUMBER   DEFAULT NULL
    ) RETURN VARCHAR2 SQL_MACRO(TABLE);

    /**
     * Returns multi-year historical generation breakdown for the Stacked Bar chart.
     *
     * @param p_country        ISO-3 country code (e.g. 'POL')
     * @param p_year           Target year number (e.g. 2023)
     * @param p_lookback_years Number of years back to display (default: 9)
     * @return SQL query text inlined at parse-time
     */
    FUNCTION f_summary_generation_history(
        p_country        IN VARCHAR2 DEFAULT NULL,
        p_year           IN NUMBER   DEFAULT NULL,
        p_lookback_years IN NUMBER   DEFAULT 9
    ) RETURN VARCHAR2 SQL_MACRO(TABLE);

    /**
     * Returns global country rankings by renewable energy share for the given year.
     * Includes dense ranking, entity name/code, renewables share (%), and generation volumes.
     *
     * @param p_year Target year number (e.g. 2023)
     * @return SQL query text inlined at parse-time
     */
    FUNCTION f_global_renewables_ranking(
        p_year IN NUMBER DEFAULT NULL
    ) RETURN VARCHAR2 SQL_MACRO(TABLE);

    /**
     * Returns top N countries by renewable energy share (%) for chart visualization.
     * Filters for non-trivial grid generation (>= 1 TWh).
     *
     * @param p_year  Target year number (e.g. 2023)
     * @param p_limit Maximum number of countries to return (default: 15)
     * @return SQL query text inlined at parse-time
     */
    FUNCTION f_global_top_renewables(
        p_year  IN NUMBER DEFAULT NULL,
        p_limit IN NUMBER DEFAULT 15
    ) RETURN VARCHAR2 SQL_MACRO(TABLE);

    /**
     * Returns application and pipeline system logs from LOGGER_LOGS for Interactive Grid.
     * Supports category filtering ('ALL', 'ERRORS', 'ELT').
     *
     * @param p_filter_type Log filter category: 'ALL', 'ERRORS', 'ELT' (default: 'ALL')
     * @return SQL query text inlined at parse-time by Oracle CBO
     */
    FUNCTION f_system_logs(
        p_filter_type IN VARCHAR2 DEFAULT 'ALL'
    ) RETURN VARCHAR2 SQL_MACRO(TABLE);

    /**
     * Returns the active global logging level name (e.g. 'DEBUG', 'INFORMATION', 'ERROR').
     *
     * @return Current active log level name
     */
    FUNCTION f_get_current_logger_level RETURN VARCHAR2;

    /**
     * Updates the global logging level using OraOpenSource Logger.
     * Maps 'INFO' to 'INFORMATION' if needed.
     *
     * @param p_level Target log level name ('DEBUG', 'TIMING', 'INFORMATION', 'WARNING', 'ERROR')
     */
    PROCEDURE p_set_logger_level(
        p_level IN VARCHAR2
    );

    /**
     * Returns available logger levels for dynamic LOV components.
     * Uses logger.convert_level_num_to_char to resolve level names from the database.
     *
     * @return SQL query text returning (d, r, lvl_order)
     */
    FUNCTION f_lov_logger_levels RETURN VARCHAR2 SQL_MACRO(TABLE);

END pkg_apex_queries;
/
