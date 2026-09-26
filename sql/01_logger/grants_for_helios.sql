GRANT EXECUTE ON helios_logger.logger TO helios_core;
GRANT EXECUTE ON helios_logger.logger TO helios_stg;
GRANT EXECUTE ON helios_logger.logger TO helios_apex;


GRANT SELECT ON helios_logger.logger_logs TO helios_apex;
GRANT SELECT ON helios_logger.logger_logs_5_min TO helios_apex;