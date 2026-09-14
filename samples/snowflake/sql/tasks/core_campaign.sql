-- Snowflake task for the CORE campaign build.
--   proc_7x7b2hFPxu  "Build Core Campaign"  schedule 25 5 * * *
--
-- Runs after the 03:00 partner file ingestion, which is an Airflow DAG rather than a
-- Snowflake task, so there is no task graph edge to attach to; the gap is the margin.
--
-- The FX coverage assertion runs FIRST and must fail the task. It matters more here than
-- for the other builds: campaign spend is a SUM over cost days, and SUM ignores NULLs, so
-- one unresolved conversion would quietly reduce a campaign total and improve its apparent
-- return on ad spend. An understated cost is not a visible failure.
--
-- Full rebuild of both tables: CAMPAIGN and CAMPAIGN_DAILY_COST state the current campaign
-- set, not a delivery history. RAW keeps the history.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA CORE;

CREATE OR REPLACE TASK CORE_CAMPAIGN_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 25 5 * * * UTC'
    COMMENT   = 'Beyond Entity proc_7x7b2hFPxu. Campaign spend per BR-2: sum of daily cost, each day converted on its own COST_DATE.'
AS
BEGIN
    -- Gate: sql/core/fx_coverage/*.sql, then fail if FX_COVERAGE_GAP names
    -- RAW_PARTNER_ACQUISITION_COST. Per build -- an order or subscription gap must not
    -- block campaigns, and a campaign gap must not block them.
    TRUNCATE TABLE CAMPAIGN_DAILY_COST;
    -- sql/core/campaign/1_trans_ujVKXAKMnt_build_campaign_daily_cost.sql
    TRUNCATE TABLE CAMPAIGN;
    -- sql/core/campaign/2_trans_EI0BFv41zV_build_core_campaign.sql
    -- (bodies inlined at deploy time by the release tooling)
END;

ALTER TASK CORE_CAMPAIGN_BUILD RESUME;
