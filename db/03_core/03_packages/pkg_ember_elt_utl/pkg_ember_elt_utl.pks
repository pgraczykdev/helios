CREATE OR REPLACE PACKAGE helios_core.pkg_ember_elt_utl AS
    -- ========================================================================
    -- HELIOS DATA PLATFORM - CORE DWH LAYER
    -- Package: helios_core.pkg_ember_elt_utl (Specification)
    -- Description: Utility functions, telemetry, and result record builders
    --              (success, error, and step error handling) for ELT pipeline.
    -- Standards: Explicit CHAR semantics, uppercase keywords, lowercase identifiers.
    -- Documentation: PLDoc standard with @param and @return tags.
    -- ========================================================================

    -- Anchored subtype to preserve a single contract source of truth
    SUBTYPE t_elt_result_rec IS helios_core.pkg_ember_elt.t_elt_result_rec;

    /**
     * Calculates total elapsed execution time in seconds with millisecond precision.
     * Handles intervals exceeding 60 seconds (days, hours, minutes conversion).
     *
     * @param  pi_start_ts Starting timestamp.
     * @param  pi_end_ts   Ending timestamp.
     * @return Execution time rounded to 2 decimal places.
     */
    FUNCTION f_calc_execution_seconds(
        pi_start_ts IN TIMESTAMP,
        pi_end_ts   IN TIMESTAMP
    ) RETURN NUMBER;

    /**
     * Constructs a populated SUCCESS t_elt_result_rec record.
     *
     * @param  pi_start_ts  Starting timestamp of the operation.
     * @param  pi_rows_proc Count of staging rows processed.
     * @param  pi_rows_mrg  Count of target fact/dimension rows merged.
     * @return Fully populated t_elt_result_rec with status SUCCESS.
     */
    FUNCTION f_build_success_result(
        pi_start_ts  IN TIMESTAMP,
        pi_rows_proc IN NUMBER DEFAULT 0,
        pi_rows_mrg  IN NUMBER DEFAULT 0
    ) RETURN t_elt_result_rec;

    /**
     * Constructs a populated ERROR t_elt_result_rec record.
     *
     * @param  pi_error_message Detailed explanation of the failure.
     * @param  pi_start_ts      Starting timestamp of the operation.
     * @param  pi_rows_proc     Count of staging rows processed before abort.
     * @param  pi_rows_mrg      Count of target rows merged before abort.
     * @return Fully populated t_elt_result_rec with status ERROR.
     */
    FUNCTION f_build_error_result(
        pi_error_message IN VARCHAR2,
        pi_start_ts      IN TIMESTAMP,
        pi_rows_proc     IN NUMBER DEFAULT 0,
        pi_rows_mrg      IN NUMBER DEFAULT 0
    ) RETURN t_elt_result_rec;

    /**
     * Centralized step error handler: logs the error into Logger and builds
     * an ERROR result record.
     *
     * @param  pi_step_name     Human-readable name of the ELT step (e.g. Dimensions merge).
     * @param  pi_error_details Specific error message or exception details.
     * @param  pi_start_ts      Starting timestamp of the master orchestration.
     * @param  pi_rows_proc     Cumulative processed rows.
     * @param  pi_rows_mrg      Cumulative merged rows.
     * @param  pi_scope         Optional logger scope override.
     * @return Formatted error record for pipeline return.
     */
    FUNCTION f_handle_step_error(
        pi_step_name     IN VARCHAR2,
        pi_error_details IN VARCHAR2,
        pi_start_ts      IN TIMESTAMP,
        pi_rows_proc     IN NUMBER DEFAULT 0,
        pi_rows_mrg      IN NUMBER DEFAULT 0,
        pi_scope         IN VARCHAR2 DEFAULT NULL
    ) RETURN t_elt_result_rec;

END pkg_ember_elt_utl;
/
