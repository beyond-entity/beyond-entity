-- Snowflake task for the CORE support build.
--   proc_u5kiETSFgV  "Build Core Support Interaction"  schedule 20 5 * * *
--
-- No currency in this build, so the FX coverage gate does NOT apply and a missing
-- exchange rate cannot block support reporting. That narrow blast radius is deliberate.
--
-- DEPLOYMENT PREREQUISITE:
--     SET mysql_server_timezone = 'UTC';
-- 'UTC' is this sample's explicit configuration assumption. VERIFY against the real MySQL
-- system: if it stores server-local time, every RESOLUTION_SECONDS is wrong by the offset.
--
-- NOT EXECUTED. Warehouse, database and role are deployment concerns.

USE DATABASE ENTERPRISE_DW;
USE SCHEMA CORE;

CREATE OR REPLACE TASK CORE_SUPPORT_INTERACTION_BUILD
    WAREHOUSE = <WAREHOUSE_NAME>
    SCHEDULE  = 'USING CRON 20 5 * * * UTC'
    COMMENT   = 'Beyond Entity proc_u5kiETSFgV. Full rebuild of the support fact.'
AS
BEGIN
    TRUNCATE TABLE SUPPORT_INTERACTION_FACT;
    -- sql/core/support/1_trans_ncSl7tiwTo_build_core_support_interaction.sql
END;

ALTER TASK CORE_SUPPORT_INTERACTION_BUILD RESUME;
