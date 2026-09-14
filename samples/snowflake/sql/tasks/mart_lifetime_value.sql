-- Snowflake task for the CUSTOMER_LIFETIME_VALUE mart build.
--   proc_AR6brQlFmY  "Build Customer Lifetime Value"  schedule 15 6 * * *
--
-- Depends on Build Core Order, Build Core Subscription and Build Core Campaign. It inherits
-- the campaign build's FX gate transitively: if campaign spend could not be resolved,
-- CAMPAIGN was not rebuilt and acquisition cost reflects the previous run rather than an
-- understated one.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TASK MART_LIFETIME_VALUE_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 15 6 * * * UTC'
    COMMENT   = 'Beyond Entity proc_AR6brQlFmY. Per-customer revenue net of a share of campaign spend (BR-4).'
AS
BEGIN
    TRUNCATE TABLE CUSTOMER_LIFETIME_VALUE;
    -- sql/analytics/lifetime_value/1_trans_dzGW5MkIYi_build_lifetime_value.sql
    -- (body inlined at deploy time by the release tooling)
END;

ALTER TASK MART_LIFETIME_VALUE_BUILD RESUME;
