-- Snowflake task for the CUSTOMER_360 mart build.
--   proc_qi2OyAuAAl  "Build Customer 360"  schedule 0 6 * * *
--
-- Depends on all CORE builds: this is the row that combines four independent source
-- systems, and every one of them has to be conformed first.
--
-- Each CORE fact is aggregated in its own scalar subquery rather than joined. Reverting
-- that to joins reintroduces D21, where three one-to-many facts multiplied each other and
-- every measure came out several times too large while still looking plausible.
--
-- PII BOUNDARY. This task publishes into ANALYTICS, where only the hashed customer
-- identifier is permitted. Do not add EMAIL, CUSTOMER_NAME or PHONE_NUMBER to the insert.
--
-- NOT EXECUTED. Warehouse name, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TASK MART_CUSTOMER_360_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 0 6 * * * UTC'
    COMMENT   = 'Beyond Entity proc_qi2OyAuAAl. Cross-system customer view; PII masking boundary.'
AS
BEGIN
    TRUNCATE TABLE CUSTOMER_360;
    -- sql/analytics/customer_360/1_trans_0B0zceN1kv_assemble_customer_360.sql
    -- (body inlined at deploy time by the release tooling)
END;

ALTER TASK MART_CUSTOMER_360_BUILD RESUME;
