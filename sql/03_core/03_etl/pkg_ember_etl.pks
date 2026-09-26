CREATE OR REPLACE PACKAGE helios_core.pkg_ember_etl AS
    -- ========================================================================
    -- HELIOS DATA PLATFORM - CORE DWH LAYER
    -- Package: helios_core.pkg_ember_etl (Specification)
    -- Description: Core ETL transformation package. Loads staging data into
    --              the Star Schema dimensions and facts with idempotent MERGE.
    -- Standards: Explicit CHAR semantics, anchored types, uppercase keywords,
    --            lowercase identifiers, functional result record contract.
    -- Documentation: PLDoc / Javadoc standard with @param and @return.
    -- ========================================================================

    -- Global Package Constants
    gc_pkg_name        CONSTANT VARCHAR2(30 CHAR) := 'pkg_ember_etl';

    -- Status and Outcome Aliases (Inherited from PKG_CONSTANTS SSOT)
    gc_status_new      CONSTANT VARCHAR2(20 CHAR) := pkg_constants.gc_status_new;
    gc_status_proc     CONSTANT VARCHAR2(20 CHAR) := pkg_constants.gc_status_processed;
    gc_status_err      CONSTANT VARCHAR2(20 CHAR) := pkg_constants.gc_status_error;

    gc_res_success     CONSTANT VARCHAR2(20 CHAR) := pkg_constants.gc_res_success;
    gc_res_warning     CONSTANT VARCHAR2(20 CHAR) := pkg_constants.gc_res_warning;
    gc_res_error       CONSTANT VARCHAR2(20 CHAR) := pkg_constants.gc_res_error;

    -- Anchored Subtypes based on Physical Database Columns
    SUBTYPE t_entity_code         IS helios_core.dim_entity.entity_code%TYPE;
    SUBTYPE t_entity_name         IS helios_core.dim_entity.entity_name%TYPE;
    SUBTYPE t_series_name         IS helios_core.dim_series.series_name%TYPE;
    SUBTYPE t_temporal_resolution IS helios_core.dim_period.temporal_resolution%TYPE;
    SUBTYPE t_raw_date            IS helios_core.dim_period.raw_date%TYPE;
    SUBTYPE t_stg_status          IS helios_stg.stg_ember_generation.stg_status%TYPE;
    SUBTYPE t_error_message       IS helios_stg.stg_ember_generation.error_message%TYPE;
    SUBTYPE t_source_file         IS helios_core.fact_generation.source_file%TYPE;

    -- Result Record Type for Functional ETL Feedback
    TYPE t_etl_result_rec IS RECORD (
        status            VARCHAR2(20 CHAR),
        rows_processed    NUMBER,
        rows_merged       NUMBER,
        start_ts          TIMESTAMP,
        end_ts            TIMESTAMP,
        execution_seconds NUMBER,
        error_message     VARCHAR2(4000 CHAR)
    );

    /**
     * Returns the count of unprocessed (NEW) records in the specified staging table.
     *
     * @param  pi_table_name Name of the staging table (e.g. STG_EMBER_GENERATION).
     * @return Number of records with STG_STATUS = 'NEW'.
     * @throws -20001 If the provided staging table name is unknown or invalid.
     */
    FUNCTION f_get_new_stg_count(
        pi_table_name IN VARCHAR2
    ) RETURN NUMBER;

    /**
     * Extracts distinct dimension attributes from all staging tables and merges them
     * idempotently into DIM_ENTITY, DIM_SERIES, and DIM_PERIOD.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success,
     *                   FALSE keeps transaction uncommitted for parent orchestrator.
     * @return Structured record (t_etl_result_rec) containing status, merged row count,
     *         and execution timings.
     */
    FUNCTION f_merge_dimensions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_etl_result_rec;

    /**
     * Transforms and loads electricity generation data from STG_EMBER_GENERATION
     * into FACT_GENERATION using an idempotent MERGE operation based on the grain
     * (entity_id, series_id, period_id). Updates STG_STATUS to PROCESSED or ERROR.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success,
     *                   FALSE keeps transaction uncommitted for parent orchestrator.
     * @return Structured record (t_etl_result_rec) containing status, processed/merged counts,
     *         and error details if any.
     */
    FUNCTION f_load_generation(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_etl_result_rec;

    /**
     * Transforms and loads installed renewable capacity data from STG_EMBER_CAPACITY
     * into FACT_CAPACITY using an idempotent MERGE operation based on the grain
     * (entity_id, series_id, period_id). Updates STG_STATUS to PROCESSED or ERROR.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success,
     *                   FALSE keeps transaction uncommitted for parent orchestrator.
     * @return Structured record (t_etl_result_rec) containing status, processed/merged counts,
     *         and error details if any.
     */
    FUNCTION f_load_capacity(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_etl_result_rec;

    /**
     * Transforms and loads grid carbon intensity data from STG_EMBER_CARBON_INTENSITY
     * into FACT_CARBON_INTENSITY using an idempotent MERGE operation based on the grain
     * (entity_id, period_id). Updates STG_STATUS to PROCESSED or ERROR.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success,
     *                   FALSE keeps transaction uncommitted for parent orchestrator.
     * @return Structured record (t_etl_result_rec) containing status, processed/merged counts,
     *         and error details if any.
     */
    FUNCTION f_load_carbon_intensity(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_etl_result_rec;

    /**
     * Transforms and loads power demand data from STG_EMBER_DEMAND
     * into FACT_DEMAND using an idempotent MERGE operation based on the grain
     * (entity_id, period_id). Updates STG_STATUS to PROCESSED or ERROR.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success,
     *                   FALSE keeps transaction uncommitted for parent orchestrator.
     * @return Structured record (t_etl_result_rec) containing status, processed/merged counts,
     *         and error details if any.
     */
    FUNCTION f_load_demand(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_etl_result_rec;

    /**
     * Transforms and loads power sector greenhouse gas emissions from STG_EMBER_EMISSIONS
     * into FACT_EMISSIONS using an idempotent MERGE operation based on the grain
     * (entity_id, series_id, period_id). Updates STG_STATUS to PROCESSED or ERROR.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success,
     *                   FALSE keeps transaction uncommitted for parent orchestrator.
     * @return Structured record (t_etl_result_rec) containing status, processed/merged counts,
     *         and error details if any.
     */
    FUNCTION f_load_emissions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_etl_result_rec;

    /**
     * Master ETL orchestrator function. Executes dimension merge followed by all fact
     * table loads in sequential dependency order within a single transaction boundary.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues atomic COMMIT at completion
     *                   or ROLLBACK on failure; FALSE leaves transaction management to caller.
     * @return Aggregated result record (t_etl_result_rec) with total processed/merged rows,
     *         overall elapsed time, and error summary.
     */
    FUNCTION f_load_all(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_etl_result_rec;

    /**
     * Convenience procedure wrapper around f_load_all.
     * Records full execution lifecycle, duration, and outcomes directly into Logger.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT/ROLLBACK, FALSE leaves open.
     */
    PROCEDURE p_load_all(
        pi_commit IN BOOLEAN DEFAULT TRUE
    );

END pkg_ember_etl;
/
