    SET ECHO ON
    SET SERVEROUTPUT ON
    SET FEEDBACK ON
    WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK;
    
    PROMPT ========================================================================
    PROMPT HELIOS DATABASE DEPLOYMENT: START
    PROMPT ========================================================================
    
    -- ----------------------------------------------------------------------------
    -- STEP 0: ADMINISTRATIVE SETUP (Users, Quotas, System Roles)
    -- ----------------------------------------------------------------------------
    PROMPT [00_ADMIN] 1/7 Creating Helios schemas and assigning roles...
    @@00_admin/01_create_users_and_roles.sql
    
    -- ----------------------------------------------------------------------------
    -- STEP 1: LOGGING INFRASTRUCTURE (OraOpenSource Logger)
    -- ----------------------------------------------------------------------------
    PROMPT [01_LOGGER] 2/7 Setting current schema to HELIOS_LOGGER...
    ALTER SESSION SET CURRENT_SCHEMA = helios_logger;
    
    PROMPT [01_LOGGER] Installing OraOpenSource Logger objects...
    @@01_logger/logger_install.sql
    
    PROMPT [01_LOGGER] Granting logger privileges to CORE, STG, and APEX...
    @@01_logger/grants_for_helios.sql
    
    -- ----------------------------------------------------------------------------
    -- STEP 2: STAGING LAYER (HELIOS_STG)
    -- ----------------------------------------------------------------------------
    PROMPT [02_STG] 3/7 Creating staging landing tables in HELIOS_STG...
    @@02_stg/01_staging_tables.sql
    
    PROMPT [02_STG] Granting staging table access to HELIOS_CORE...
    @@02_stg/02_grants_for_core.sql
    
    -- ----------------------------------------------------------------------------
    -- STEP 3: CORE DWH LAYER (HELIOS_CORE)
    -- ----------------------------------------------------------------------------
    PROMPT [03_CORE] 4/7 Setting current schema to HELIOS_CORE...
    ALTER SESSION SET CURRENT_SCHEMA = helios_core;
    
    PROMPT [03_CORE] Creating private synonyms to STG and LOGGER...
    @@03_core/01_synonyms/01_stg_synonyms.sql
    @@03_core/01_synonyms/02_core_synonyms.sql
    
    PROMPT [03_CORE] Creating Dimension tables (DIM_ENTITY, DIM_SERIES, DIM_PERIOD)...
    @@03_core/02_tables/01_dimensions.sql
    
    PROMPT [03_CORE] Creating Fact tables (FACT_GENERATION, CAPACITY, CI, DEMAND, EMISSIONS)...
    @@03_core/02_tables/02_facts.sql
    
    PROMPT [03_CORE] Compiling ELT constants package specification...
    @@03_core/03_elt/pkg_constants.pks

    PROMPT [03_CORE] Compiling ELT package specification...
    @@03_core/03_elt/pkg_ember_elt.pks

    PROMPT [03_CORE] Compiling ELT package body...
    @@03_core/03_elt/pkg_ember_elt.pkb

    PROMPT [03_CORE] 5/7 Creating SmartDB analytical views...
    @@03_core/04_views/01_analytical_views.sql

    PROMPT [03_CORE] 6/7 Granting view access to HELIOS_APEX...
    @@03_core/04_views/02_grants_for_apex.sql

    -- ----------------------------------------------------------------------------
    -- STEP 4: PRESENTATION LAYER (HELIOS_APEX)
    -- ----------------------------------------------------------------------------
    PROMPT [04_APEX] 7/7 Setting current schema to HELIOS_APEX...
    ALTER SESSION SET CURRENT_SCHEMA = helios_apex;

    PROMPT [04_APEX] Creating private synonyms pointing to CORE analytical views...
    @@04_apex/01_synonyms/01_apex_synonyms.sql

    PROMPT ========================================================================
    PROMPT HELIOS DATABASE DEPLOYMENT: COMPLETED SUCCESSFULLY!
    PROMPT ========================================================================
    PROMPT ------------------------------------------------------------------------