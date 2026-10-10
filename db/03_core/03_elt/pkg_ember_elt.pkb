CREATE OR REPLACE PACKAGE BODY helios_core.pkg_ember_elt AS
    -- ========================================================================
    -- HELIOS DATA PLATFORM - CORE DWH LAYER
    -- Package Body: helios_core.pkg_ember_elt
    -- Description: Implementation of Star Schema dimensions merge, fact loads,
    --              and master ELT orchestration.
    -- Standards: Explicit CHAR semantics, anchored types, uppercase keywords,
    --            lowercase identifiers, functional result record contract.
    --            Enterprise Logger instrumentation with scope prefix and params.
    -- Documentation: PLDoc / Javadoc standard with @param and @return.
    -- ========================================================================

    gc_scope_prefix CONSTANT VARCHAR2(31 CHAR) := LOWER($$PLSQL_UNIT) || '.';

    -- ------------------------------------------------------------------------
    -- 0. FUNCTION f_get_new_stg_count
    -- ------------------------------------------------------------------------
    FUNCTION f_get_new_stg_count(
        pi_table_name IN VARCHAR2
    ) RETURN NUMBER IS
        lc_scope CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_get_new_stg_count';
        l_params logger.tab_param;
        l_count  NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_table_name', p_val => pi_table_name);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        CASE UPPER(TRIM(pi_table_name))
            WHEN pkg_constants.gc_stg_generation THEN
                SELECT COUNT(*) INTO l_count FROM stg_ember_generation WHERE stg_status = pkg_constants.gc_status_new;
            WHEN pkg_constants.gc_stg_capacity THEN
                SELECT COUNT(*) INTO l_count FROM stg_ember_capacity WHERE stg_status = pkg_constants.gc_status_new;
            WHEN pkg_constants.gc_stg_carbon_intensity THEN
                SELECT COUNT(*) INTO l_count FROM stg_ember_carbon_intensity WHERE stg_status = pkg_constants.gc_status_new;
            WHEN pkg_constants.gc_stg_demand THEN
                SELECT COUNT(*) INTO l_count FROM stg_ember_demand WHERE stg_status = pkg_constants.gc_status_new;
            WHEN pkg_constants.gc_stg_emissions THEN
                SELECT COUNT(*) INTO l_count FROM stg_ember_emissions WHERE stg_status = pkg_constants.gc_status_new;
            ELSE
                RAISE_APPLICATION_ERROR(
                    pkg_constants.gc_err_code_unknown_stg, 
                    pkg_constants.gc_err_msg_unknown_stg || pi_table_name
                );
        END CASE;

        logger.log(p_text => 'Count for ' || pi_table_name || ': ' || l_count, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_count;
    EXCEPTION
        WHEN OTHERS THEN
            logger.log_error(p_text => 'Failed to count staging rows: ' || pi_table_name, p_scope => lc_scope, p_params => l_params);
            RAISE;
    END f_get_new_stg_count;


    -- ------------------------------------------------------------------------
    -- 1.1 FUNCTION f_merge_dim_entity
    -- ------------------------------------------------------------------------
    FUNCTION f_merge_dim_entity(
        pi_commit IN BOOLEAN DEFAULT FALSE
    ) RETURN t_elt_result_rec IS
        lc_scope   CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_merge_dim_entity';
        l_params   logger.tab_param;
        l_result   t_elt_result_rec;
        l_start_ts TIMESTAMP := SYSTIMESTAMP;
        l_merged   NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        MERGE INTO helios_core.dim_entity tgt
        USING (
            SELECT 
                entity,
                MAX(entity_code)         AS entity_code,
                MAX(is_aggregate_entity) AS is_aggregate_entity
            FROM (
                SELECT entity, entity_code, is_aggregate_entity FROM stg_ember_generation       WHERE stg_status = pkg_constants.gc_status_new AND entity IS NOT NULL
                UNION ALL
                SELECT entity, entity_code, is_aggregate_entity FROM stg_ember_capacity         WHERE stg_status = pkg_constants.gc_status_new AND entity IS NOT NULL
                UNION ALL
                SELECT entity, entity_code, is_aggregate_entity FROM stg_ember_carbon_intensity WHERE stg_status = pkg_constants.gc_status_new AND entity IS NOT NULL
                UNION ALL
                SELECT entity, entity_code, is_aggregate_entity FROM stg_ember_demand           WHERE stg_status = pkg_constants.gc_status_new AND entity IS NOT NULL
                UNION ALL
                SELECT entity, entity_code, is_aggregate_entity FROM stg_ember_emissions        WHERE stg_status = pkg_constants.gc_status_new AND entity IS NOT NULL
            )
            GROUP BY entity
        ) src
        ON (tgt.entity_name = src.entity)
        WHEN MATCHED THEN
            UPDATE SET 
                tgt.entity_code  = NVL(tgt.entity_code, src.entity_code),
                tgt.is_aggregate = NVL(src.is_aggregate_entity, tgt.is_aggregate),
                tgt.updated_at   = SYSTIMESTAMP
        WHEN NOT MATCHED THEN
            INSERT (
                entity_name, 
                entity_code, 
                is_aggregate, 
                created_at, 
                updated_at
            )
            VALUES (
                src.entity, 
                src.entity_code, 
                NVL(src.is_aggregate_entity, 0), 
                SYSTIMESTAMP, 
                SYSTIMESTAMP
            );

        l_merged := SQL%ROWCOUNT;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_merged;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Merged DIM_ENTITY. Rows: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'DIM_ENTITY merge failed', p_scope => lc_scope, p_params => l_params);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'DIM_ENTITY merge failed';
            RETURN l_result;
    END f_merge_dim_entity;


    -- ------------------------------------------------------------------------
    -- 1.2 FUNCTION f_merge_dim_series
    -- ------------------------------------------------------------------------
    FUNCTION f_merge_dim_series(
        pi_commit IN BOOLEAN DEFAULT FALSE
    ) RETURN t_elt_result_rec IS
        lc_scope   CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_merge_dim_series';
        l_params   logger.tab_param;
        l_result   t_elt_result_rec;
        l_start_ts TIMESTAMP := SYSTIMESTAMP;
        l_merged   NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        MERGE INTO helios_core.dim_series tgt
        USING (
            SELECT 
                series,
                MAX(is_aggregate_series) AS is_aggregate_series,
                MAX(CASE 
                    WHEN LOWER(series) IN ('solar', 'wind', 'hydro', 'bioenergy', 'other renewables', 'geothermal') THEN pkg_constants.gc_cat_renewables
                    WHEN LOWER(series) IN ('coal', 'gas', 'other fossil') THEN pkg_constants.gc_cat_fossil
                    WHEN LOWER(series) IN ('nuclear') THEN pkg_constants.gc_cat_nuclear
                    WHEN LOWER(series) IN ('clean') THEN pkg_constants.gc_cat_clean
                    ELSE pkg_constants.gc_cat_other
                END) AS series_category
            FROM (
                SELECT series, is_aggregate_series FROM stg_ember_generation WHERE stg_status = pkg_constants.gc_status_new AND series IS NOT NULL
                UNION ALL
                SELECT series, is_aggregate_series FROM stg_ember_capacity   WHERE stg_status = pkg_constants.gc_status_new AND series IS NOT NULL
                UNION ALL
                SELECT series, is_aggregate_series FROM stg_ember_emissions  WHERE stg_status = pkg_constants.gc_status_new AND series IS NOT NULL
            )
            GROUP BY series
        ) src
        ON (tgt.series_name = src.series)
        WHEN MATCHED THEN
            UPDATE SET 
                tgt.series_category = NVL(tgt.series_category, src.series_category),
                tgt.is_aggregate    = NVL(src.is_aggregate_series, tgt.is_aggregate),
                tgt.updated_at      = SYSTIMESTAMP
        WHEN NOT MATCHED THEN
            INSERT (
                series_name, 
                series_category, 
                is_aggregate, 
                created_at, 
                updated_at
            )
            VALUES (
                src.series, 
                src.series_category, 
                NVL(src.is_aggregate_series, 0), 
                SYSTIMESTAMP, 
                SYSTIMESTAMP
            );

        l_merged := SQL%ROWCOUNT;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_merged;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Merged DIM_SERIES. Rows: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'DIM_SERIES merge failed', p_scope => lc_scope, p_params => l_params);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'DIM_SERIES merge failed';
            RETURN l_result;
    END f_merge_dim_series;


    -- ------------------------------------------------------------------------
    -- 1.3 FUNCTION f_merge_dim_period
    -- ------------------------------------------------------------------------
    FUNCTION f_merge_dim_period(
        pi_commit IN BOOLEAN DEFAULT FALSE
    ) RETURN t_elt_result_rec IS
        lc_scope   CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_merge_dim_period';
        l_params   logger.tab_param;
        l_result   t_elt_result_rec;
        l_start_ts TIMESTAMP := SYSTIMESTAMP;
        l_merged   NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        MERGE INTO helios_core.dim_period tgt
        USING (
            SELECT 
                temporal_resolution,
                raw_date,
                MAX(period_date)  AS period_date,
                MAX(year_num)     AS year_num,
                MAX(month_num)    AS month_num,
                MAX(quarter_num)  AS quarter_num,
                MAX(period_label) AS period_label
            FROM (
                SELECT 
                    temporal_resolution, 
                    raw_date,
                    CASE 
                        WHEN temporal_resolution = pkg_constants.gc_grain_yearly  THEN TO_DATE(raw_date || '-01-01', 'YYYY-MM-DD')
                        WHEN temporal_resolution = pkg_constants.gc_grain_monthly THEN TO_DATE(raw_date || '-01', 'YYYY-MM-DD')
                    END AS period_date,
                    TO_NUMBER(SUBSTR(raw_date, 1, 4)) AS year_num,
                    CASE 
                        WHEN temporal_resolution = pkg_constants.gc_grain_monthly THEN TO_NUMBER(SUBSTR(raw_date, 6, 2))
                        ELSE NULL
                    END AS month_num,
                    CASE 
                        WHEN temporal_resolution = pkg_constants.gc_grain_monthly THEN TO_NUMBER(TO_CHAR(TO_DATE(raw_date || '-01', 'YYYY-MM-DD'), 'Q'))
                        ELSE NULL
                    END AS quarter_num,
                    CASE 
                        WHEN temporal_resolution = pkg_constants.gc_grain_yearly  THEN raw_date
                        WHEN temporal_resolution = pkg_constants.gc_grain_monthly THEN TO_CHAR(TO_DATE(raw_date || '-01', 'YYYY-MM-DD'), 'Mon YYYY')
                    END AS period_label
                FROM (
                    SELECT temporal_resolution, raw_date FROM stg_ember_generation       WHERE stg_status = pkg_constants.gc_status_new AND raw_date IS NOT NULL
                    UNION ALL
                    SELECT temporal_resolution, raw_date FROM stg_ember_capacity         WHERE stg_status = pkg_constants.gc_status_new AND raw_date IS NOT NULL
                    UNION ALL
                    SELECT temporal_resolution, raw_date FROM stg_ember_carbon_intensity WHERE stg_status = pkg_constants.gc_status_new AND raw_date IS NOT NULL
                    UNION ALL
                    SELECT temporal_resolution, raw_date FROM stg_ember_demand           WHERE stg_status = pkg_constants.gc_status_new AND raw_date IS NOT NULL
                    UNION ALL
                    SELECT temporal_resolution, raw_date FROM stg_ember_emissions        WHERE stg_status = pkg_constants.gc_status_new AND raw_date IS NOT NULL
                )
            )
            GROUP BY temporal_resolution, raw_date
        ) src
        ON (tgt.temporal_resolution = src.temporal_resolution AND tgt.raw_date = src.raw_date)
        WHEN NOT MATCHED THEN
            INSERT (
                temporal_resolution, 
                raw_date, 
                period_date, 
                year_num, 
                month_num, 
                quarter_num, 
                period_label, 
                created_at
            )
            VALUES (
                src.temporal_resolution, 
                src.raw_date, 
                src.period_date, 
                src.year_num, 
                src.month_num, 
                src.quarter_num, 
                src.period_label, 
                SYSTIMESTAMP
            );

        l_merged := SQL%ROWCOUNT;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_merged;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Merged DIM_PERIOD. Rows: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'DIM_PERIOD merge failed', p_scope => lc_scope, p_params => l_params);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'DIM_PERIOD merge failed';
            RETURN l_result;
    END f_merge_dim_period;


    -- ------------------------------------------------------------------------
    -- 1.4 FUNCTION f_merge_dimensions (Master Dimension Orchestrator)
    -- ------------------------------------------------------------------------
    FUNCTION f_merge_dimensions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec IS
        lc_scope   CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_merge_dimensions';
        l_params   logger.tab_param;
        l_result   t_elt_result_rec;
        l_step_res t_elt_result_rec;
        l_start_ts TIMESTAMP := SYSTIMESTAMP;
        l_total    NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        -- Step 1: Merge Entities
        l_step_res := f_merge_dim_entity(pi_commit => FALSE);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            ROLLBACK;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total := l_total + l_step_res.rows_merged;

        -- Step 2: Merge Series
        l_step_res := f_merge_dim_series(pi_commit => FALSE);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            ROLLBACK;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total := l_total + l_step_res.rows_merged;

        -- Step 3: Merge Periods
        l_step_res := f_merge_dim_period(pi_commit => FALSE);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            ROLLBACK;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total := l_total + l_step_res.rows_merged;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_total;
        l_result.rows_merged       := l_total;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'All dimensions merged successfully. Total rows: ' || l_total, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'f_merge_dimensions failed', p_scope => lc_scope, p_params => l_params);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := l_total;
            l_result.rows_merged       := l_total;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'Master dimensions merge failed';
            RETURN l_result;
    END f_merge_dimensions;


    -- ------------------------------------------------------------------------
    -- 1.5 PROCEDURE p_merge_dimensions (Console Wrapper)
    -- ------------------------------------------------------------------------
    PROCEDURE p_merge_dimensions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) IS
        l_res t_elt_result_rec;
    BEGIN
        l_res := f_merge_dimensions(pi_commit => pi_commit);
    END p_merge_dimensions;


    -- ------------------------------------------------------------------------
    -- 2. FUNCTION f_load_generation (Deduplicated with ROW_NUMBER)
    -- ------------------------------------------------------------------------
    FUNCTION f_load_generation(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec IS
        lc_scope    CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_load_generation';
        l_params    logger.tab_param;
        l_result    t_elt_result_rec;
        l_start_ts  TIMESTAMP := SYSTIMESTAMP;
        l_processed NUMBER := 0;
        l_merged    NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        l_processed := f_get_new_stg_count(pi_table_name => pkg_constants.gc_stg_generation);

        IF l_processed = 0 THEN
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := 0;
            logger.log(p_text => 'No new staging rows to process. END', p_scope => lc_scope);
            RETURN l_result;
        END IF;

        MERGE INTO helios_core.fact_generation tgt
        USING (
            SELECT 
                entity_id,
                series_id,
                period_id,
                generation_twh,
                share_of_generation_pct,
                source_file
            FROM (
                SELECT 
                    e.entity_id,
                    s.series_id,
                    p.period_id,
                    stg.generation_twh,
                    stg.share_of_generation_pct,
                    stg.source_file,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.entity_id, s.series_id, p.period_id 
                        ORDER BY stg.load_timestamp DESC, stg.stg_id DESC
                    ) AS rn
                FROM stg_ember_generation stg
                JOIN helios_core.dim_entity e ON e.entity_name = stg.entity
                JOIN helios_core.dim_series s ON s.series_name = stg.series
                JOIN helios_core.dim_period p ON p.temporal_resolution = stg.temporal_resolution 
                                             AND p.raw_date = stg.raw_date
                WHERE stg.stg_status = pkg_constants.gc_status_new
            )
            WHERE rn = 1
        ) src
        ON (tgt.entity_id = src.entity_id 
            AND tgt.series_id = src.series_id 
            AND tgt.period_id = src.period_id)
        WHEN MATCHED THEN
            UPDATE SET 
                tgt.generation_twh          = src.generation_twh,
                tgt.share_of_generation_pct = src.share_of_generation_pct,
                tgt.load_timestamp          = SYSTIMESTAMP,
                tgt.source_file             = src.source_file
        WHEN NOT MATCHED THEN
            INSERT (
                entity_id, 
                series_id, 
                period_id, 
                generation_twh, 
                share_of_generation_pct, 
                load_timestamp, 
                source_file
            )
            VALUES (
                src.entity_id, 
                src.series_id, 
                src.period_id, 
                src.generation_twh, 
                src.share_of_generation_pct, 
                SYSTIMESTAMP, 
                src.source_file
            );

        l_merged := SQL%ROWCOUNT;

        UPDATE stg_ember_generation
        SET stg_status    = pkg_constants.gc_status_processed,
            error_message = NULL
        WHERE stg_status  = pkg_constants.gc_status_new;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_processed;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Loaded generation facts. Processed: ' || l_processed || ', Merged: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'Generation facts load failed', p_scope => lc_scope, p_params => l_params);
            UPDATE stg_ember_generation
            SET stg_status    = pkg_constants.gc_status_error,
                error_message = 'Generation facts load failed. See LOGGER_LOGS for details.'
            WHERE stg_status  = pkg_constants.gc_status_new;
            IF pi_commit THEN
                COMMIT;
            END IF;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := l_processed;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'Generation facts load failed';
            RETURN l_result;
    END f_load_generation;


    -- ------------------------------------------------------------------------
    -- 3. FUNCTION f_load_capacity (Deduplicated with ROW_NUMBER)
    -- ------------------------------------------------------------------------
    FUNCTION f_load_capacity(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec IS
        lc_scope    CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_load_capacity';
        l_params    logger.tab_param;
        l_result    t_elt_result_rec;
        l_start_ts  TIMESTAMP := SYSTIMESTAMP;
        l_processed NUMBER := 0;
        l_merged    NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        l_processed := f_get_new_stg_count(pi_table_name => pkg_constants.gc_stg_capacity);

        IF l_processed = 0 THEN
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := 0;
            logger.log(p_text => 'No new staging rows to process. END', p_scope => lc_scope);
            RETURN l_result;
        END IF;

        MERGE INTO helios_core.fact_capacity tgt
        USING (
            SELECT 
                entity_id,
                series_id,
                period_id,
                capacity_gw,
                capacity_w_per_capita,
                source_file
            FROM (
                SELECT 
                    e.entity_id,
                    s.series_id,
                    p.period_id,
                    stg.capacity_gw,
                    stg.capacity_w_per_capita,
                    stg.source_file,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.entity_id, s.series_id, p.period_id 
                        ORDER BY stg.load_timestamp DESC, stg.stg_id DESC
                    ) AS rn
                FROM stg_ember_capacity stg
                JOIN helios_core.dim_entity e ON e.entity_name = stg.entity
                JOIN helios_core.dim_series s ON s.series_name = stg.series
                JOIN helios_core.dim_period p ON p.temporal_resolution = stg.temporal_resolution 
                                             AND p.raw_date = stg.raw_date
                WHERE stg.stg_status = pkg_constants.gc_status_new
            )
            WHERE rn = 1
        ) src
        ON (tgt.entity_id = src.entity_id 
            AND tgt.series_id = src.series_id 
            AND tgt.period_id = src.period_id)
        WHEN MATCHED THEN
            UPDATE SET 
                tgt.capacity_gw           = src.capacity_gw,
                tgt.capacity_w_per_capita = src.capacity_w_per_capita,
                tgt.load_timestamp        = SYSTIMESTAMP,
                tgt.source_file           = src.source_file
        WHEN NOT MATCHED THEN
            INSERT (
                entity_id, 
                series_id, 
                period_id, 
                capacity_gw, 
                capacity_w_per_capita, 
                load_timestamp, 
                source_file
            )
            VALUES (
                src.entity_id, 
                src.series_id, 
                src.period_id, 
                src.capacity_gw, 
                src.capacity_w_per_capita, 
                SYSTIMESTAMP, 
                src.source_file
            );

        l_merged := SQL%ROWCOUNT;

        UPDATE stg_ember_capacity
        SET stg_status    = pkg_constants.gc_status_processed,
            error_message = NULL
        WHERE stg_status  = pkg_constants.gc_status_new;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_processed;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Loaded capacity facts. Processed: ' || l_processed || ', Merged: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'Capacity facts load failed', p_scope => lc_scope, p_params => l_params);
            UPDATE stg_ember_capacity
            SET stg_status    = pkg_constants.gc_status_error,
                error_message = 'Capacity facts load failed. See LOGGER_LOGS for details.'
            WHERE stg_status  = pkg_constants.gc_status_new;
            IF pi_commit THEN
                COMMIT;
            END IF;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := l_processed;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'Capacity facts load failed';
            RETURN l_result;
    END f_load_capacity;


    -- ------------------------------------------------------------------------
    -- 4. FUNCTION f_load_carbon_intensity (Deduplicated with ROW_NUMBER)
    -- ------------------------------------------------------------------------
    FUNCTION f_load_carbon_intensity(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec IS
        lc_scope    CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_load_carbon_intensity';
        l_params    logger.tab_param;
        l_result    t_elt_result_rec;
        l_start_ts  TIMESTAMP := SYSTIMESTAMP;
        l_processed NUMBER := 0;
        l_merged    NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        l_processed := f_get_new_stg_count(pi_table_name => pkg_constants.gc_stg_carbon_intensity);

        IF l_processed = 0 THEN
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := 0;
            logger.log(p_text => 'No new staging rows to process. END', p_scope => lc_scope);
            RETURN l_result;
        END IF;

        MERGE INTO helios_core.fact_carbon_intensity tgt
        USING (
            SELECT 
                entity_id,
                period_id,
                emissions_intensity_gco2_per_kwh,
                source_file
            FROM (
                SELECT 
                    e.entity_id,
                    p.period_id,
                    stg.emissions_intensity_gco2_per_kwh,
                    stg.source_file,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.entity_id, p.period_id 
                        ORDER BY stg.load_timestamp DESC, stg.stg_id DESC
                    ) AS rn
                FROM stg_ember_carbon_intensity stg
                JOIN helios_core.dim_entity e ON e.entity_name = stg.entity
                JOIN helios_core.dim_period p ON p.temporal_resolution = stg.temporal_resolution 
                                             AND p.raw_date = stg.raw_date
                WHERE stg.stg_status = pkg_constants.gc_status_new
            )
            WHERE rn = 1
        ) src
        ON (tgt.entity_id = src.entity_id 
            AND tgt.period_id = src.period_id)
        WHEN MATCHED THEN
            UPDATE SET 
                tgt.emissions_intensity_gco2_per_kwh = src.emissions_intensity_gco2_per_kwh,
                tgt.load_timestamp                  = SYSTIMESTAMP,
                tgt.source_file                     = src.source_file
        WHEN NOT MATCHED THEN
            INSERT (
                entity_id, 
                period_id, 
                emissions_intensity_gco2_per_kwh, 
                load_timestamp, 
                source_file
            )
            VALUES (
                src.entity_id, 
                src.period_id, 
                src.emissions_intensity_gco2_per_kwh, 
                SYSTIMESTAMP, 
                src.source_file
            );

        l_merged := SQL%ROWCOUNT;

        UPDATE stg_ember_carbon_intensity
        SET stg_status    = pkg_constants.gc_status_processed,
            error_message = NULL
        WHERE stg_status  = pkg_constants.gc_status_new;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_processed;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Loaded carbon intensity facts. Processed: ' || l_processed || ', Merged: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'Carbon intensity facts load failed', p_scope => lc_scope, p_params => l_params);
            UPDATE stg_ember_carbon_intensity
            SET stg_status    = pkg_constants.gc_status_error,
                error_message = 'Carbon intensity facts load failed. See LOGGER_LOGS for details.'
            WHERE stg_status  = pkg_constants.gc_status_new;
            IF pi_commit THEN
                COMMIT;
            END IF;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := l_processed;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'Carbon intensity facts load failed';
            RETURN l_result;
    END f_load_carbon_intensity;


    -- ------------------------------------------------------------------------
    -- 5. FUNCTION f_load_demand (Deduplicated with ROW_NUMBER)
    -- ------------------------------------------------------------------------
    FUNCTION f_load_demand(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec IS
        lc_scope    CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_load_demand';
        l_params    logger.tab_param;
        l_result    t_elt_result_rec;
        l_start_ts  TIMESTAMP := SYSTIMESTAMP;
        l_processed NUMBER := 0;
        l_merged    NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        l_processed := f_get_new_stg_count(pi_table_name => pkg_constants.gc_stg_demand);

        IF l_processed = 0 THEN
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := 0;
            logger.log(p_text => 'No new staging rows to process. END', p_scope => lc_scope);
            RETURN l_result;
        END IF;

        MERGE INTO helios_core.fact_demand tgt
        USING (
            SELECT 
                entity_id,
                period_id,
                demand_twh,
                demand_mwh_per_capita,
                source_file
            FROM (
                SELECT 
                    e.entity_id,
                    p.period_id,
                    stg.demand_twh,
                    stg.demand_mwh_per_capita,
                    stg.source_file,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.entity_id, p.period_id 
                        ORDER BY stg.load_timestamp DESC, stg.stg_id DESC
                    ) AS rn
                FROM stg_ember_demand stg
                JOIN helios_core.dim_entity e ON e.entity_name = stg.entity
                JOIN helios_core.dim_period p ON p.temporal_resolution = stg.temporal_resolution 
                                             AND p.raw_date = stg.raw_date
                WHERE stg.stg_status = pkg_constants.gc_status_new
            )
            WHERE rn = 1
        ) src
        ON (tgt.entity_id = src.entity_id 
            AND tgt.period_id = src.period_id)
        WHEN MATCHED THEN
            UPDATE SET 
                tgt.demand_twh            = src.demand_twh,
                tgt.demand_mwh_per_capita = src.demand_mwh_per_capita,
                tgt.load_timestamp        = SYSTIMESTAMP,
                tgt.source_file           = src.source_file
        WHEN NOT MATCHED THEN
            INSERT (
                entity_id, 
                period_id, 
                demand_twh, 
                demand_mwh_per_capita, 
                load_timestamp, 
                source_file
            )
            VALUES (
                src.entity_id, 
                src.period_id, 
                src.demand_twh, 
                src.demand_mwh_per_capita, 
                SYSTIMESTAMP, 
                src.source_file
            );

        l_merged := SQL%ROWCOUNT;

        UPDATE stg_ember_demand
        SET stg_status    = pkg_constants.gc_status_processed,
            error_message = NULL
        WHERE stg_status  = pkg_constants.gc_status_new;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_processed;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Loaded demand facts. Processed: ' || l_processed || ', Merged: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'Demand facts load failed', p_scope => lc_scope, p_params => l_params);
            UPDATE stg_ember_demand
            SET stg_status    = pkg_constants.gc_status_error,
                error_message = 'Demand facts load failed. See LOGGER_LOGS for details.'
            WHERE stg_status  = pkg_constants.gc_status_new;
            IF pi_commit THEN
                COMMIT;
            END IF;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := l_processed;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'Demand facts load failed';
            RETURN l_result;
    END f_load_demand;


    -- ------------------------------------------------------------------------
    -- 6. FUNCTION f_load_emissions (Deduplicated with ROW_NUMBER)
    -- ------------------------------------------------------------------------
    FUNCTION f_load_emissions(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec IS
        lc_scope    CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_load_emissions';
        l_params    logger.tab_param;
        l_result    t_elt_result_rec;
        l_start_ts  TIMESTAMP := SYSTIMESTAMP;
        l_processed NUMBER := 0;
        l_merged    NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        l_processed := f_get_new_stg_count(pi_table_name => pkg_constants.gc_stg_emissions);

        IF l_processed = 0 THEN
            l_result.rows_processed    := 0;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := 0;
            logger.log(p_text => 'No new staging rows to process. END', p_scope => lc_scope);
            RETURN l_result;
        END IF;

        MERGE INTO helios_core.fact_emissions tgt
        USING (
            SELECT 
                entity_id,
                series_id,
                period_id,
                emissions_mtco2,
                share_of_emissions_pct,
                source_file
            FROM (
                SELECT 
                    e.entity_id,
                    s.series_id,
                    p.period_id,
                    stg.emissions_mtco2,
                    stg.share_of_emissions_pct,
                    stg.source_file,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.entity_id, s.series_id, p.period_id 
                        ORDER BY stg.load_timestamp DESC, stg.stg_id DESC
                    ) AS rn
                FROM stg_ember_emissions stg
                JOIN helios_core.dim_entity e ON e.entity_name = stg.entity
                JOIN helios_core.dim_series s ON s.series_name = stg.series
                JOIN helios_core.dim_period p ON p.temporal_resolution = stg.temporal_resolution 
                                             AND p.raw_date = stg.raw_date
                WHERE stg.stg_status = pkg_constants.gc_status_new
            )
            WHERE rn = 1
        ) src
        ON (tgt.entity_id = src.entity_id 
            AND tgt.series_id = src.series_id 
            AND tgt.period_id = src.period_id)
        WHEN MATCHED THEN
            UPDATE SET 
                tgt.emissions_mtco2        = src.emissions_mtco2,
                tgt.share_of_emissions_pct = src.share_of_emissions_pct,
                tgt.load_timestamp         = SYSTIMESTAMP,
                tgt.source_file            = src.source_file
        WHEN NOT MATCHED THEN
            INSERT (
                entity_id, 
                series_id, 
                period_id, 
                emissions_mtco2, 
                share_of_emissions_pct, 
                load_timestamp, 
                source_file
            )
            VALUES (
                src.entity_id, 
                src.series_id, 
                src.period_id, 
                src.emissions_mtco2, 
                src.share_of_emissions_pct, 
                SYSTIMESTAMP, 
                src.source_file
            );

        l_merged := SQL%ROWCOUNT;

        UPDATE stg_ember_emissions
        SET stg_status    = pkg_constants.gc_status_processed,
            error_message = NULL
        WHERE stg_status  = pkg_constants.gc_status_new;

        IF pi_commit THEN
            COMMIT;
        END IF;

        l_result.rows_processed    := l_processed;
        l_result.rows_merged       := l_merged;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Loaded emissions facts. Processed: ' || l_processed || ', Merged: ' || l_merged, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.log_error(p_text => 'Emissions facts load failed', p_scope => lc_scope, p_params => l_params);
            UPDATE stg_ember_emissions
            SET stg_status    = pkg_constants.gc_status_error,
                error_message = 'Emissions facts load failed. See LOGGER_LOGS for details.'
            WHERE stg_status  = pkg_constants.gc_status_new;
            IF pi_commit THEN
                COMMIT;
            END IF;
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := l_processed;
            l_result.rows_merged       := 0;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'Emissions facts load failed';
            RETURN l_result;
    END f_load_emissions;


    -- ------------------------------------------------------------------------
    -- 7. FUNCTION f_load_all (Master Orchestrator)
    -- ------------------------------------------------------------------------
    FUNCTION f_load_all(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) RETURN t_elt_result_rec IS
        lc_scope     CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'f_load_all';
        l_params     logger.tab_param;
        l_result     t_elt_result_rec;
        l_step_res   t_elt_result_rec;
        l_start_ts   TIMESTAMP := SYSTIMESTAMP;
        l_total_proc NUMBER := 0;
        l_total_mrg  NUMBER := 0;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);
        logger.time_start(p_unit => lc_scope);

        l_result.status        := pkg_constants.gc_res_success;
        l_result.start_ts      := l_start_ts;
        l_result.error_message := NULL;

        -- Step 7.1: Merge Dimensions
        l_step_res := f_merge_dimensions(pi_commit => pi_commit);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
            logger.log_error(p_text => 'Dimensions merge failed: ' || l_step_res.error_message, p_scope => lc_scope);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := 'Dimensions merge failed: ' || l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total_mrg := l_total_mrg + l_step_res.rows_merged;

        -- Step 7.2: Load Generation Facts
        l_step_res := f_load_generation(pi_commit => pi_commit);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
            logger.log_error(p_text => 'Generation load failed: ' || l_step_res.error_message, p_scope => lc_scope);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := 'Generation load failed: ' || l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total_proc := l_total_proc + l_step_res.rows_processed;
        l_total_mrg  := l_total_mrg + l_step_res.rows_merged;

        -- Step 7.3: Load Capacity Facts
        l_step_res := f_load_capacity(pi_commit => pi_commit);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
            logger.log_error(p_text => 'Capacity load failed: ' || l_step_res.error_message, p_scope => lc_scope);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := 'Capacity load failed: ' || l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total_proc := l_total_proc + l_step_res.rows_processed;
        l_total_mrg  := l_total_mrg + l_step_res.rows_merged;

        -- Step 7.4: Load Carbon Intensity Facts
        l_step_res := f_load_carbon_intensity(pi_commit => pi_commit);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
            logger.log_error(p_text => 'Carbon intensity load failed: ' || l_step_res.error_message, p_scope => lc_scope);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := 'Carbon intensity load failed: ' || l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total_proc := l_total_proc + l_step_res.rows_processed;
        l_total_mrg  := l_total_mrg + l_step_res.rows_merged;

        -- Step 7.5: Load Demand Facts
        l_step_res := f_load_demand(pi_commit => pi_commit);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
            logger.log_error(p_text => 'Demand load failed: ' || l_step_res.error_message, p_scope => lc_scope);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := 'Demand load failed: ' || l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total_proc := l_total_proc + l_step_res.rows_processed;
        l_total_mrg  := l_total_mrg + l_step_res.rows_merged;

        -- Step 7.6: Load Emissions Facts
        l_step_res := f_load_emissions(pi_commit => pi_commit);
        IF l_step_res.status = pkg_constants.gc_res_error THEN
            logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
            logger.log_error(p_text => 'Emissions load failed: ' || l_step_res.error_message, p_scope => lc_scope);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.error_message     := 'Emissions load failed: ' || l_step_res.error_message;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            RETURN l_result;
        END IF;
        l_total_proc := l_total_proc + l_step_res.rows_processed;
        l_total_mrg  := l_total_mrg + l_step_res.rows_merged;

        IF pi_commit THEN
            COMMIT;
        END IF;

        logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
        l_result.rows_processed    := l_total_proc;
        l_result.rows_merged       := l_total_mrg;
        l_result.end_ts            := SYSTIMESTAMP;
        l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);

        logger.log_info(p_text => 'Master ELT completed. Processed: ' || l_total_proc || ', Merged: ' || l_total_mrg, p_scope => lc_scope);
        logger.log(p_text => 'END', p_scope => lc_scope);
        RETURN l_result;
    EXCEPTION
        WHEN OTHERS THEN
            IF pi_commit THEN
                ROLLBACK;
            END IF;
            logger.time_stop(p_unit => lc_scope, p_scope => lc_scope);
            logger.log_error(p_text => 'Master ELT aborted due to unhandled error', p_scope => lc_scope, p_params => l_params);
            l_result.status            := pkg_constants.gc_res_error;
            l_result.rows_processed    := l_total_proc;
            l_result.rows_merged       := l_total_mrg;
            l_result.end_ts            := SYSTIMESTAMP;
            l_result.execution_seconds := ROUND(EXTRACT(SECOND FROM (l_result.end_ts - l_start_ts)), 2);
            l_result.error_message     := 'Master ELT orchestration failed';
            RETURN l_result;
    END f_load_all;


    -- ------------------------------------------------------------------------
    -- 8. PROCEDURE p_load_all (Convenience Console Wrapper)
    -- ------------------------------------------------------------------------
    PROCEDURE p_load_all(
        pi_commit IN BOOLEAN DEFAULT TRUE
    ) IS
        lc_scope CONSTANT VARCHAR2(100 CHAR) := gc_scope_prefix || 'p_load_all';
        l_params logger.tab_param;
        l_result t_elt_result_rec;
    BEGIN
        logger.append_param(p_params => l_params, p_name => 'pi_commit', p_val => pi_commit);
        logger.log(p_text => 'START', p_scope => lc_scope, p_params => l_params);

        l_result := f_load_all(pi_commit => pi_commit);

        IF l_result.status = pkg_constants.gc_res_error THEN
            logger.log_error(p_text => 'Master ELT finished with errors: ' || l_result.error_message, p_scope => lc_scope, p_params => l_params);
        ELSE
            logger.log_info(p_text => 'Master ELT finished successfully. Merged: ' || l_result.rows_merged, p_scope => lc_scope);
        END IF;

        logger.log(p_text => 'END', p_scope => lc_scope);
    EXCEPTION
        WHEN OTHERS THEN
            logger.log_error(p_text => 'Unhandled exception in p_load_all', p_scope => lc_scope, p_params => l_params);
            RAISE;
    END p_load_all;

END pkg_ember_elt;
/
