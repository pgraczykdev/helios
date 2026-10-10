CREATE OR REPLACE PACKAGE helios_core.pkg_ember_elt_err AS
    -- ========================================================================
    -- HELIOS DATA PLATFORM - CORE DWH LAYER
    -- Package: helios_core.pkg_ember_elt_err (Specification Only)
    -- Description: Central definition of custom application exceptions and
    --              Oracle error code mappings (-20010 to -20015) for ELT.
    -- Standards: Specification-only pattern, explicit CHAR semantics,
    --            uppercase keywords, lowercase identifiers.
    -- ========================================================================

    -- Error Codes (Oracle User-Defined Range: -20999 to -20000)
    gc_err_code_dimensions       CONSTANT PLS_INTEGER := -20010;
    gc_err_code_generation       CONSTANT PLS_INTEGER := -20011;
    gc_err_code_capacity         CONSTANT PLS_INTEGER := -20012;
    gc_err_code_carbon_intensity CONSTANT PLS_INTEGER := -20013;
    gc_err_code_demand           CONSTANT PLS_INTEGER := -20014;
    gc_err_code_emissions        CONSTANT PLS_INTEGER := -20015;

    -- Pipeline Step Named Exceptions
    e_dimensions_failed       EXCEPTION;
    e_generation_failed       EXCEPTION;
    e_capacity_failed         EXCEPTION;
    e_carbon_intensity_failed EXCEPTION;
    e_demand_failed           EXCEPTION;
    e_emissions_failed        EXCEPTION;

    -- Pragma exception mapping to Oracle error codes
    PRAGMA EXCEPTION_INIT(e_dimensions_failed,       -20010);
    PRAGMA EXCEPTION_INIT(e_generation_failed,       -20011);
    PRAGMA EXCEPTION_INIT(e_capacity_failed,         -20012);
    PRAGMA EXCEPTION_INIT(e_carbon_intensity_failed, -20013);
    PRAGMA EXCEPTION_INIT(e_demand_failed,           -20014);
    PRAGMA EXCEPTION_INIT(e_emissions_failed,        -20015);

END pkg_ember_elt_err;
/
