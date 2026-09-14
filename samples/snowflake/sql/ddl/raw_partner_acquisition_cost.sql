-- RAW_PARTNER_ACQUISITION_COST  (Beyond Entity: ent_S7007U3oD0, model mdl_pcE5TphblS)
--
-- Append-only. Grain: one row per campaign per cost date per delivered file. COST_DATE is
-- NOT NULL because it is part of the grain, so a row whose cost date will not parse is
-- rejected at ingestion rather than landed.
--
-- ACQUISITION_COST and ATTRIBUTED_SIGNUPS are measures and stay nullable so an uncastable
-- value lands and remains countable against landing_file_manifest.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_PARTNER_ACQUISITION_COST (
    CAMPAIGN_ID         VARCHAR(64)   NOT NULL,
    PARTNER_ID          VARCHAR(64)   NOT NULL,
    COST_DATE           DATE          NOT NULL,
    ACQUISITION_COST    NUMERIC(18,2),
    CURRENCY_CODE       VARCHAR(3),
    ATTRIBUTED_SIGNUPS  INT,
    _SOURCE_FILE        VARCHAR(500),
    _SOURCE_SYSTEM      VARCHAR(30)   NOT NULL,
    _INGESTED_AT        TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID   VARCHAR(60)   NOT NULL,
    _BATCH_ID           VARCHAR(60)
);
