-- Snowflake task for the CORE FX rate build.
--   proc_AsyyNwdM2X  "Build Core FX Rate"  schedule 45 3 * * *
--
-- Runs on its own cron rather than AFTER the ingestion task, because the ingestion is an
-- Airflow DAG rather than a Snowflake task -- there is no task graph edge to attach to.
-- The one-hour gap after the 02:45 ingestion is the margin. If that margin ever proves
-- too thin, the right fix is to make the dependency explicit (an Airflow-triggered task,
-- or a stream/task pair on RAW_FX_RATES) rather than to widen the gap.
--
-- Full rebuild: FX_RATE_DAILY states the current rate set, not a delivery history.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA CORE;

CREATE OR REPLACE TASK CORE_FX_RATE_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 45 3 * * * UTC'
    COMMENT   = 'Beyond Entity proc_AsyyNwdM2X. Rebuilds the FX reference table every revenue build reads.'
AS
BEGIN
    TRUNCATE TABLE FX_RATE_DAILY;
    -- sql/core/fx/1_trans_BJWaMbDz8u_build_fx_rate_daily.sql
    -- (body inlined at deploy time by the release tooling)
END;

ALTER TASK CORE_FX_RATE_BUILD RESUME;
