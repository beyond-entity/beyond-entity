-- Snowflake task graph for the CORE customer spine.
--   proc_j3HyTdoXBh  "Resolve Customer Identity"  schedule 0 4 * * *   (after all ingestion)
--   proc_PASXcCWvuz  "Build Core Customer"        schedule 30 4 * * *  (after the above)
--
-- Both processors declare runs_in = "Snowflake task" in the model, so this is their
-- deployment form. The build task runs AFTER the resolution task rather than on its own
-- cron: the modeled depends_on is a real dependency, and two independent crons would let
-- the customer build run against a half-rebuilt crosswalk.
--
-- The statement bodies are the canonical files in sql/core/, unchanged. If you edit them
-- here they will drift from the model -- edit the model, regenerate sql/core/, then this.
--
-- DEPLOYMENT PREREQUISITE. Set the Oracle source timezone before creating these tasks:
--     SET oracle_server_timezone = 'UTC';
-- 'UTC' is this sample's explicit configuration assumption: Oracle source timestamps are
-- treated as already being UTC. VERIFY THIS against the real Oracle system before any
-- production deployment -- if Oracle stores server-local time, every FIRST_SEEN_AT_UTC is
-- wrong by that offset. The value is passed explicitly rather than inherited from the
-- Snowflake session timezone, so correcting the assumption is a one-value change.
--
-- NOT EXECUTED. This file has never been run against Snowflake. Warehouse name, database
-- and role are deployment concerns and are left as placeholders.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA CORE;

CREATE OR REPLACE TASK CORE_CUSTOMER_IDENTITY_RESOLUTION
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 0 4 * * * UTC'
    COMMENT   = 'Beyond Entity proc_j3HyTdoXBh. Full rebuild of the identity crosswalk.'
AS
BEGIN
    TRUNCATE TABLE CUSTOMER_IDENTITY_MAP;
    -- sql/core/customer/1_trans_WU55bR1llr_resolve_oracle_identities.sql
    -- sql/core/customer/2_trans_31gOHrJWBN_resolve_postgres_identities.sql
    -- sql/core/customer/3_trans_1DBXXgcab2_resolve_mysql_identities.sql
    -- sql/core/customer/4_trans_0kIOAUK5gy_resolve_partner_identities.sql
    -- (bodies inlined at deploy time by the release tooling)
END;

CREATE OR REPLACE TASK CORE_CUSTOMER_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    AFTER CORE_CUSTOMER_IDENTITY_RESOLUTION
    COMMENT   = 'Beyond Entity proc_PASXcCWvuz. Full rebuild of the CUSTOMER dimension.'
AS
BEGIN
    TRUNCATE TABLE CUSTOMER;
    -- sql/core/customer/5_trans_MydYVq9TcJ_build_core_customer.sql
    -- binds :oracle_server_timezone from the session variable set above
END;

ALTER TASK CORE_CUSTOMER_BUILD RESUME;
ALTER TASK CORE_CUSTOMER_IDENTITY_RESOLUTION RESUME;
