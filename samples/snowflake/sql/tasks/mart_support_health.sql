-- Snowflake task for the CUSTOMER_SUPPORT_HEALTH mart build.
--   proc_tUDyM0IkCx  "Build Customer Support Health"  schedule 30 6 * * *
--
-- Depends on Build Core Support Interaction only. No currency is involved, so the FX gate
-- does not apply to this build.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TASK MART_SUPPORT_HEALTH_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 30 6 * * * UTC'
    COMMENT   = 'Beyond Entity proc_tUDyM0IkCx. Monthly support load by category and priority.'
AS
BEGIN
    TRUNCATE TABLE CUSTOMER_SUPPORT_HEALTH;
    -- sql/analytics/support_health/1_trans_LHiLIVlNkW_aggregate_support_health.sql
    -- (body inlined at deploy time by the release tooling)
END;

ALTER TASK MART_SUPPORT_HEALTH_BUILD RESUME;
