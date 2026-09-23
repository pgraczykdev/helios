-- The CORE schema requires SELECT to read raw batches and UPDATE to set STG_STATUS
GRANT SELECT, UPDATE ON helios_stg.stg_ember_generation       TO helios_core;
GRANT SELECT, UPDATE ON helios_stg.stg_ember_capacity         TO helios_core;
GRANT SELECT, UPDATE ON helios_stg.stg_ember_carbon_intensity TO helios_core;
GRANT SELECT, UPDATE ON helios_stg.stg_ember_demand           TO helios_core;
GRANT SELECT, UPDATE ON helios_stg.stg_ember_emissions        TO helios_core;
