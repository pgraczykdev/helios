CREATE OR REPLACE PACKAGE helios_core.pkg_ember_elt AS
    -- ========================================================================
    -- HELIOS DATA PLATFORM - CORE DWH LAYER
    -- Package: helios_core.pkg_ember_elt (Specification)
    -- Description: Core ELT transformation package. Loads staging data into
    --              the Star Schema dimensions and facts with idempotent MERGE.
    -- Standards: Explicit CHAR semantics, anchored types, uppercase keywords,
    --            lowercase identifiers, functional result record contract.
    -- Documentation: PLDoc / Javadoc standard with @param and @return.
    -- ========================================================================

    -- Global Package Constants
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

    -- Result Record Type for Functional ELT Feedback
    TYPE t_elt_result_rec IS RECORD (
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
     * Merges unique country and regional aggregate entities into DIM_ENTITY.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success.
     * @return Structured record (t_elt_result_rec) containing status and metrics.
     */
    FUNCTION f_merge_dim_entity(
        pi_commit IN BOOLEAN DEFAULT FALSE
    ) RETURN t_elt_result_rec;

    /**
     * Merges unique energy series and categories into DIM_SERIES.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success.
     * @return Structured record (t_elt_result_rec) containing status and metrics.
     */
    FUNCTION f_merge_dim_series(
        pi_commit IN BOOLEAN DEFAULT FALSE
    ) RETURN t_elt_result_rec;

    /**
     * Merges unique temporal grains (yearly/monthly) into DIM_PERIOD.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT on success.
     * @return Structured record (t_elt_result_rec) containing status and metrics.
     */
    FUNCTION f_merge_dim_period(
        pi_commit IN BOOLEAN DEFAULT FALSE
    ) RETURN t_elt_result_rec;

    /**
     * Master dimensions orchestrator function. Executes entity, series, and period
     * merges sequentially within a single transaction boundary.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues atomic COMMIT on success.
     * @return Structured record (t_elt_result_rec) with aggregated row counts.
     */
    FUNCTION f_merge_dimensions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec;

    /**
     * Convenience console wrapper for f_merge_dimensions.
     *
     * @param  pi_commit Controls transaction autonomy: TRUE issues COMMIT/ROLLBACK.
     */
    PROCEDURE p_merge_dimensions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    );

    /**
     * Transforms and loads electricity generation data into FACT_GENERATION.
     */
    FUNCTION f_load_generation(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec;

    /**
     * Transforms and loads installed renewable capacity data into FACT_CAPACITY.
     */
    FUNCTION f_load_capacity(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec;

    /**
     * Transforms and loads grid carbon intensity data into FACT_CARBON_INTENSITY.
     */
    FUNCTION f_load_carbon_intensity(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec;

    /**
     * Transforms and loads power demand data into FACT_DEMAND.
     */
    FUNCTION f_load_demand(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec;

    /**
     * Transforms and loads power sector greenhouse gas emissions into FACT_EMISSIONS.
     */
    FUNCTION f_load_emissions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec;

    /**
     * Master ELT orchestrator function. Executes dimension merge followed by all fact
     * table loads in sequential dependency order within a single transaction boundary.
     */
    FUNCTION f_load_all(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec;

    /**
     * Convenience console wrapper around f_load_all.
     */
    PROCEDURE p_load_all(
        pi_commit IN BOOLEAN DEFAULT TRUE
    );

END pkg_ember_elt;
/
