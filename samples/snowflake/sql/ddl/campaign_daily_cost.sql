-- CAMPAIGN_DAILY_COST  (Beyond Entity: ent_kbvl0ZWGX3, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- Grain: one row per campaign per cost date. Full rebuild.
--
-- Exists because BR-2 defines campaign spend as the sum of daily costs, each converted on
-- its own COST_DATE. No single FX_RATE_APPLIED can reproduce a campaign total, so the
-- per-day conversion is stored where it can be audited. CAMPAIGN aggregates this table.
--
-- FX_RATE_APPLIED and COST_AMOUNT_USD are NOT NULL, and here that backstop does more work
-- than elsewhere: campaign spend is a SUM, and SUM ignores NULLs, so an unresolved
-- conversion would quietly *reduce* a campaign total rather than null it. Assert FX Rate
-- Coverage is meant to stop the build first; this constraint is what makes the silent
-- undercount impossible if it ever does not.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.CAMPAIGN_DAILY_COST (
    CAMPAIGN_KEY          VARCHAR(64)   NOT NULL,
    PARTNER_ID            VARCHAR(64)   NOT NULL,
    CAMPAIGN_ID           VARCHAR(64)   NOT NULL,
    COST_DATE             DATE          NOT NULL,
    SOURCE_CURRENCY_CODE  VARCHAR(3),
    COST_AMOUNT_SOURCE    NUMERIC(18,2),
    FX_RATE_APPLIED       NUMERIC(18,8) NOT NULL,
    COST_AMOUNT_USD       NUMERIC(18,2) NOT NULL,
    ATTRIBUTED_SIGNUPS    INT
);
