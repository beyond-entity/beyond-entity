-- CAMPAIGN  (Beyond Entity: ent_SyaovSZC9B, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- Grain: one row per partner campaign. Full rebuild.
--
-- CAMPAIGN_KEY is composite because campaign identifiers are only unique WITHIN a partner.
-- Every join to this table must carry both halves; joining on CAMPAIGN_ID alone mixes two
-- partners' campaigns together, which is exactly the defect the build had.
--
-- TOTAL_SPEND_USD is the sum of daily costs each converted on its own COST_DATE (BR-2), so
-- there is no single applied rate to store. TOTAL_SPEND_SOURCE and COST_DAY_COUNT plus the
-- per-day rows in CAMPAIGN_DAILY_COST are what make the figure auditable instead.
--
-- TOTAL_SPEND_USD stays nullable: a campaign with no delivered cost rows has no spend to
-- report, which is not the same as a failed conversion. COST_DAY_COUNT tells the two apart.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.CAMPAIGN (
    CAMPAIGN_KEY          VARCHAR(64)   NOT NULL PRIMARY KEY,
    PARTNER_ID            VARCHAR(64)   NOT NULL,
    CAMPAIGN_ID           VARCHAR(64)   NOT NULL,
    CAMPAIGN_NAME         VARCHAR(200),
    CHANNEL               VARCHAR(40),
    START_DATE            DATE,
    END_DATE              DATE,
    SOURCE_CURRENCY_CODE  VARCHAR(3),
    TOTAL_SPEND_SOURCE    NUMERIC(18,2),
    TOTAL_SPEND_USD       NUMERIC(18,2),
    COST_DAY_COUNT        INT,
    ATTRIBUTED_SIGNUPS    INT,
    TARGET_SEGMENT        VARCHAR(80)
);
