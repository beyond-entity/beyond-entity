-- Snowflake task for the MONTHLY_REVENUE mart build.
--   proc_5WN7LCvuxV  "Build Monthly Revenue"  schedule 10 6 * * *
--
-- Four statements, not one. BR-3 reports each measure in the month it belongs to -- orders
-- in the order month, payments in the settlement month, subscription MRR in the billing
-- period month -- so the three facts are staged separately and aggregated once. Collapsing
-- them back into a single ORDER_FACT-driven GROUP BY both multiplies the measures and
-- silently drops every subscription-only customer's recurring revenue.
--
-- The staging table is a build artifact. It is truncated and rewritten with the mart, and
-- carries a customer key that never reaches the published output.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TASK MART_MONTHLY_REVENUE_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 10 6 * * * UTC'
    COMMENT   = 'Beyond Entity proc_5WN7LCvuxV. Booked, settled and recurring revenue, each in its own month.'
AS
BEGIN
    TRUNCATE TABLE MONTHLY_REVENUE_CONTRIBUTION;
    -- sql/analytics/monthly_revenue/1_trans_J3VLitJCKf_stage_order_contribution.sql
    -- sql/analytics/monthly_revenue/2_trans_PAPFDfxzRI_stage_settled_contribution.sql
    -- sql/analytics/monthly_revenue/3_trans_u3kN64nccb_stage_recurring_contribution.sql
    TRUNCATE TABLE MONTHLY_REVENUE;
    -- sql/analytics/monthly_revenue/4_trans_yl9Yq57zcF_aggregate_monthly_revenue.sql
    -- (bodies inlined at deploy time by the release tooling)
END;

ALTER TASK MART_MONTHLY_REVENUE_BUILD RESUME;
