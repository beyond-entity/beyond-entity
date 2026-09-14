-- Snowflake task for the CAMPAIGN_PERFORMANCE mart build.
--   proc_EkjDDx59xe  "Build Campaign Performance"  schedule 25 6 * * *
--
-- Depends on Build Core Campaign, Build Core Customer and Build Core Order. It inherits the
-- campaign build's FX gate transitively: if campaign spend could not be resolved, CAMPAIGN
-- was never rebuilt and this mart reports the previous run's spend rather than an
-- understated one.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TASK MART_CAMPAIGN_PERFORMANCE_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 25 6 * * * UTC'
    COMMENT   = 'Beyond Entity proc_EkjDDx59xe. Campaign spend against attributed order revenue.'
AS
BEGIN
    TRUNCATE TABLE CAMPAIGN_PERFORMANCE;
    -- sql/analytics/campaign_performance/1_trans_KUHIpMb3XL_join_spend_to_revenue.sql
    -- (body inlined at deploy time by the release tooling)
END;

ALTER TASK MART_CAMPAIGN_PERFORMANCE_BUILD RESUME;
