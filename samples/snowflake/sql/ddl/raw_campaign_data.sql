-- RAW_CAMPAIGN_DATA  (Beyond Entity: ent_gm1X0Mnte1, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Append-only. Grain: one row per campaign per delivered file. A redelivered campaign
-- appears again under a new _SOURCE_FILE; Build Core Campaign takes the latest delivery.
--
-- CAMPAIGN_ID is unique only within PARTNER_ID, which is why the grain key is the pair and
-- why CAMPAIGN_KEY is composite in CORE.
--
-- START_DATE, END_DATE and ACQUISITION_COST are nullable on purpose: a row whose measure
-- fails to cast still lands so it can be counted and reconciled against
-- landing_file_manifest. CORE is where such a row drops.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_CAMPAIGN_DATA (
    CAMPAIGN_ID        VARCHAR(64)   NOT NULL,
    PARTNER_ID         VARCHAR(64)   NOT NULL,
    CAMPAIGN_NAME      VARCHAR(200),
    CHANNEL            VARCHAR(40),
    START_DATE         DATE,
    END_DATE           DATE,
    ACQUISITION_COST   NUMERIC(18,2),
    CURRENCY_CODE      VARCHAR(3),
    TARGET_SEGMENT     VARCHAR(80),
    _SOURCE_FILE       VARCHAR(500),
    _SOURCE_SYSTEM     VARCHAR(30)   NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60)   NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
