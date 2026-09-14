-- Snowflake task for the SUBSCRIPTION_RETENTION mart build.
--   proc_F3jEWvf4lM  "Build Subscription Retention"  schedule 20 6 * * *
--
-- Depends on Build Core Subscription only. No currency conversion happens here -- MRR_USD
-- arrives already converted -- so the FX gate does not apply to this build.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TASK MART_RETENTION_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 20 6 * * * UTC'
    COMMENT   = 'Beyond Entity proc_F3jEWvf4lM. Cohort retention on revenue-bearing states (BR-5).'
AS
BEGIN
    TRUNCATE TABLE SUBSCRIPTION_RETENTION;
    -- sql/analytics/retention/1_trans_7Z6JkKWgiY_compute_retention.sql
    -- (body inlined at deploy time by the release tooling)
END;

ALTER TASK MART_RETENTION_BUILD RESUME;
