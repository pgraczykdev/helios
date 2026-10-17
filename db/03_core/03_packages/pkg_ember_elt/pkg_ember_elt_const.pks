CREATE OR REPLACE PACKAGE helios_core.pkg_ember_elt_const AS
    -- ========================================================================
    -- HELIOS DATA PLATFORM - CORE DWH LAYER
    -- Package: helios_core.pkg_ember_elt_const (Specification Only)
    -- Description: Central repository for ELT constants, staging table
    --              identifiers, status flags, and fuel categories.
    -- Standards: Explicit CHAR semantics, uppercase keywords, lowercase identifiers.
    -- Documentation: PLDoc / Javadoc standard.
    -- ========================================================================

    -- ------------------------------------------------------------------------
    -- 1. STAGING TABLE IDENTIFIERS
    -- ------------------------------------------------------------------------
    gc_stg_generation       CONSTANT VARCHAR2(30 CHAR) := 'STG_EMBER_GENERATION';
    gc_stg_capacity         CONSTANT VARCHAR2(30 CHAR) := 'STG_EMBER_CAPACITY';
    gc_stg_carbon_intensity CONSTANT VARCHAR2(30 CHAR) := 'STG_EMBER_CARBON_INTENSITY';
    gc_stg_demand           CONSTANT VARCHAR2(30 CHAR) := 'STG_EMBER_DEMAND';
    gc_stg_emissions        CONSTANT VARCHAR2(30 CHAR) := 'STG_EMBER_EMISSIONS';

    -- ------------------------------------------------------------------------
    -- 2. STAGING & ETL PROCESSING STATUS FLAGS
    -- ------------------------------------------------------------------------
    gc_status_new           CONSTANT VARCHAR2(20 CHAR) := 'NEW';
    gc_status_processed     CONSTANT VARCHAR2(20 CHAR) := 'PROCESSED';
    gc_status_error         CONSTANT VARCHAR2(20 CHAR) := 'ERROR';

    -- ------------------------------------------------------------------------
    -- 3. ETL EXECUTION OUTCOMES
    -- ------------------------------------------------------------------------
    gc_res_success          CONSTANT VARCHAR2(20 CHAR) := 'SUCCESS';
    gc_res_warning          CONSTANT VARCHAR2(20 CHAR) := 'WARNING';
    gc_res_error            CONSTANT VARCHAR2(20 CHAR) := 'ERROR';

    -- ------------------------------------------------------------------------
    -- 4. TEMPORAL RESOLUTION GRAINS
    -- ------------------------------------------------------------------------
    gc_grain_yearly         CONSTANT VARCHAR2(20 CHAR) := 'yearly';
    gc_grain_monthly        CONSTANT VARCHAR2(20 CHAR) := 'monthly';

    -- ------------------------------------------------------------------------
    -- 5. FUEL / SERIES CATEGORIES
    -- ------------------------------------------------------------------------
    gc_cat_renewables       CONSTANT VARCHAR2(30 CHAR) := 'Renewables';
    gc_cat_fossil           CONSTANT VARCHAR2(30 CHAR) := 'Fossil';
    gc_cat_nuclear          CONSTANT VARCHAR2(30 CHAR) := 'Nuclear';
    gc_cat_clean            CONSTANT VARCHAR2(30 CHAR) := 'Clean';
    gc_cat_other            CONSTANT VARCHAR2(30 CHAR) := 'Other';

END pkg_ember_elt_const;
/
