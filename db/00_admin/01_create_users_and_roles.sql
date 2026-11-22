DECLARE
    l_tablespace VARCHAR2(30 CHAR);

    PROCEDURE p_ensure_user (
        pi_username   VARCHAR2,
        pi_password   VARCHAR2,
        pi_tablespace VARCHAR2
    )
    AS
    BEGIN
        EXECUTE IMMEDIATE 'CREATE USER IF NOT EXISTS ' || pi_username
                           || ' IDENTIFIED BY "' || pi_password || '"'
                           || ' DEFAULT TABLESPACE ' || pi_tablespace
                           || ' QUOTA UNLIMITED ON ' || pi_tablespace;
    END p_ensure_user;

BEGIN

    SELECT CASE WHEN EXISTS(
        SELECT 1 FROM dba_tablespaces WHERE tablespace_name = UPPER('DATA')
    ) THEN 'DATA' ELSE 'USERS' END
    INTO l_tablespace
    FROM dual;

    p_ensure_user(pi_username => 'helios_logger', pi_password => '<YOUR_SECURE_PASSWORD_HERE>', pi_tablespace => l_tablespace);
    p_ensure_user(pi_username => 'helios_stg', pi_password => '<YOUR_SECURE_PASSWORD_HERE>', pi_tablespace => l_tablespace);
    p_ensure_user(pi_username => 'helios_core', pi_password => '<YOUR_SECURE_PASSWORD_HERE>', pi_tablespace => l_tablespace);
    p_ensure_user(pi_username => 'helios_apex', pi_password => '<YOUR_SECURE_PASSWORD_HERE>', pi_tablespace => l_tablespace);  
END; 
/
-- ----------------------------------------------------------------------------
-- 1. LOGGING INFRASTRUCTURE PRIVILEGES (HELIOS_LOGGER)
-- ----------------------------------------------------------------------------
GRANT CREATE SESSION,
        CREATE TABLE,
        CREATE VIEW,
        CREATE PROCEDURE,
        CREATE SEQUENCE,
        CREATE TRIGGER,
        CREATE JOB,
        CREATE ANY CONTEXT
    TO helios_logger;

-- ----------------------------------------------------------------------------
-- 2. STAGING LAYER PRIVILEGES (HELIOS_STG)
-- ----------------------------------------------------------------------------
GRANT CREATE SESSION,
        CREATE TABLE
    TO helios_stg;

-- ----------------------------------------------------------------------------
-- 3. CORE DWH LAYER PRIVILEGES (HELIOS_CORE)
-- ----------------------------------------------------------------------------
GRANT CREATE SESSION,
        CREATE TABLE,
        CREATE SEQUENCE,
        CREATE VIEW,
        CREATE PROCEDURE,
        CREATE SYNONYM
    TO helios_core;

-- ----------------------------------------------------------------------------
-- 4. PRESENTATION LAYER PRIVILEGES (HELIOS_APEX)
-- ----------------------------------------------------------------------------
GRANT CREATE SESSION,
        CREATE VIEW,
        CREATE PROCEDURE,
        CREATE SYNONYM
    TO helios_apex;