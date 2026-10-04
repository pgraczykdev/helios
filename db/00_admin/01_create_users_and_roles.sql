-- ----------------------------------------------------------------------------
-- 0. LOGGING INFRASTRUCTURE (OraOpenSource Logger)
-- ----------------------------------------------------------------------------
CREATE USER helios_logger IDENTIFIED BY "<YOUR_SECURE_PASSWORD_HERE>";

ALTER USER helios_logger DEFAULT TABLESPACE data QUOTA UNLIMITED ON data;

GRANT CREATE SESSION TO helios_logger;
GRANT DWROLE TO helios_logger;
GRANT CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, CREATE SEQUENCE, CREATE TRIGGER, CREATE JOB TO helios_logger;
GRANT CREATE ANY CONTEXT TO helios_logger;


-- ----------------------------------------------------------------------------
-- 1. STAGING LAYER (Ingestion / Python Loader)
-- ----------------------------------------------------------------------------
-- Replace the placeholder password with your secure password.
-- Password policy: 12-30 characters, >=1 uppercase, >=1 lowercase, >=1 number.
CREATE USER helios_stg IDENTIFIED BY "<YOUR_SECURE_PASSWORD_HERE>";


ALTER USER helios_stg DEFAULT TABLESPACE data QUOTA UNLIMITED ON data;


GRANT CREATE SESSION TO helios_stg;
GRANT CREATE TABLE TO helios_stg;


-- ----------------------------------------------------------------------------
-- 2. CORE DWH LAYER (SmartDB / Star Schema / TAPI / ETL Packages)
-- ----------------------------------------------------------------------------
CREATE USER helios_core IDENTIFIED BY "<YOUR_SECURE_PASSWORD_HERE>";

ALTER USER helios_core DEFAULT TABLESPACE data QUOTA UNLIMITED ON data;

GRANT CREATE SESSION TO helios_core;
GRANT DWROLE TO helios_core;
GRANT CREATE SYNONYM TO helios_core;


-- ----------------------------------------------------------------------------
-- 3. PRESENTATION LAYER (Oracle APEX Application / Reporting Views)
-- ----------------------------------------------------------------------------
CREATE USER helios_apex IDENTIFIED BY "<YOUR_SECURE_PASSWORD_HERE>";

ALTER USER helios_apex DEFAULT TABLESPACE data QUOTA UNLIMITED ON data;

GRANT CREATE SESSION TO helios_apex;
GRANT DWROLE TO helios_apex;
GRANT CREATE VIEW TO helios_apex;
GRANT CREATE SYNONYM TO helios_apex;
