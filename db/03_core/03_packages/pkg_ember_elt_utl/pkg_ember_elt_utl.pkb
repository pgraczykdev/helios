CREATE OR REPLACE PACKAGE BODY helios_core.pkg_ember_elt_utl AS
    -- ========================================================================
    -- HELIOS DATA PLATFORM - CORE DWH LAYER
    -- Package: helios_core.pkg_ember_elt_utl (Body)
    -- Description: Implementation of ELT pipeline utilities, telemetry,
    --              and result builders (success, error, and step error handling).
    -- Standards: Full Logger instrumentation, explicit CHAR, uppercase SQL.
    -- ========================================================================

    gc_scope_prefix CONSTANT VARCHAR2(31 CHAR) := LOWER($$PLSQL_UNIT) || '.';

    -- ------------------------------------------------------------------------
    -- 1. FUNCTION f_calc_execution_seconds
    -- ------------------------------------------------------------------------
    FUNCTION f_calc_execution_seconds(
        pi_start_ts IN TIMESTAMP,
        pi_end_ts   IN TIMESTAMP
    ) RETURN NUMBER IS
        lc_scope CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_calc_execution_seconds';
        l_diff   INTERVAL DAY(3) TO SECOND(3);
    BEGIN
        IF pi_start_ts IS NULL OR pi_end_ts IS NULL THEN
            RETURN 0;
        END IF;

        l_diff := pi_end_ts - pi_start_ts;

        RETURN ROUND(
            EXTRACT(DAY FROM l_diff) * 86400 +
            EXTRACT(HOUR FROM l_diff) * 3600 +
            EXTRACT(MINUTE FROM l_diff) * 60 +
            EXTRACT(SECOND FROM l_diff),
            2
        );
    EXCEPTION
        WHEN OTHERS THEN
            logger.log_error(p_text => 'Failed to calculate elapsed seconds', p_scope => lc_scope);
            RETURN 0;
    END f_calc_execution_seconds;


    -- ------------------------------------------------------------------------
    -- 2. FUNCTION f_build_success_result
    -- ------------------------------------------------------------------------
    FUNCTION f_build_success_result(
        pi_start_ts  IN TIMESTAMP,
        pi_rows_proc IN NUMBER DEFAULT 0,
        pi_rows_mrg  IN NUMBER DEFAULT 0
    ) RETURN t_elt_result_rec IS
        lc_scope CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_build_success_result';
        l_result t_elt_result_rec;
        l_end_ts TIMESTAMP := SYSTIMESTAMP;
    BEGIN
        l_result.status            := pkg_constants.gc_res_success;
        l_result.rows_processed    := NVL(pi_rows_proc, 0);
        l_result.rows_merged       := NVL(pi_rows_mrg, 0);
        l_result.start_ts          := pi_start_ts;
        l_result.end_ts            := l_end_ts;
        l_result.execution_seconds := f_calc_execution_seconds(pi_start_ts => pi_start_ts, pi_end_ts => l_end_ts);
        l_result.error_message     := NULL;

        logger.log_info(
            p_text  => 'Built success result. Processed: ' || l_result.rows_processed || ', Merged: ' || l_result.rows_merged || ', Sec: ' || l_result.execution_seconds,
            p_scope => lc_scope
        );

        RETURN l_result;
    END f_build_success_result;


    -- ------------------------------------------------------------------------
    -- 3. FUNCTION f_build_error_result
    -- ------------------------------------------------------------------------
    FUNCTION f_build_error_result(
        pi_error_message IN VARCHAR2,
        pi_start_ts      IN TIMESTAMP,
        pi_rows_proc     IN NUMBER DEFAULT 0,
        pi_rows_mrg      IN NUMBER DEFAULT 0
    ) RETURN t_elt_result_rec IS
        lc_scope CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_build_error_result';
        l_result t_elt_result_rec;
        l_end_ts TIMESTAMP := SYSTIMESTAMP;
    BEGIN
        l_result.status            := pkg_constants.gc_res_error;
        l_result.rows_processed    := NVL(pi_rows_proc, 0);
        l_result.rows_merged       := NVL(pi_rows_mrg, 0);
        l_result.start_ts          := pi_start_ts;
        l_result.end_ts            := l_end_ts;
        l_result.execution_seconds := f_calc_execution_seconds(pi_start_ts => pi_start_ts, pi_end_ts => l_end_ts);
        l_result.error_message     := SUBSTR(pi_error_message, 1, 4000);

        logger.log_warn(
            p_text  => 'Built error result: ' || l_result.error_message,
            p_scope => lc_scope
        );

        RETURN l_result;
    END f_build_error_result;


    -- ------------------------------------------------------------------------
    -- 4. FUNCTION f_handle_step_error
    -- ------------------------------------------------------------------------
    FUNCTION f_handle_step_error(
        pi_step_name     IN VARCHAR2,
        pi_error_details IN VARCHAR2,
        pi_start_ts      IN TIMESTAMP,
        pi_rows_proc     IN NUMBER DEFAULT 0,
        pi_rows_mrg      IN NUMBER DEFAULT 0,
        pi_scope         IN VARCHAR2 DEFAULT NULL
    ) RETURN t_elt_result_rec IS
        lc_scope CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_handle_step_error';
        l_params logger.tab_param;
        l_msg    VARCHAR2(4000 CHAR);
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_step_name', p_val => pi_step_name);
        logger.append_param(p_params => l_params, p_name => 'pi_error_details', p_val => pi_error_details);

        l_msg := pi_step_name || ' failed: ' || pi_error_details;

        logger.log_error(
            p_text   => l_msg,
            p_scope  => NVL(pi_scope, lc_scope),
            p_params => l_params
        );

        RETURN f_build_error_result(
            pi_error_message => l_msg,
            pi_start_ts      => pi_start_ts,
            pi_rows_proc     => pi_rows_proc,
            pi_rows_mrg      => pi_rows_mrg
        );
    END f_handle_step_error;

END pkg_ember_elt_utl;
/
