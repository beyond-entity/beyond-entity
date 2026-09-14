-- RAW_FX_RATES  (Beyond Entity: ent_X6Bespl2VW, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Append-only. Grain: one row per currency pair per rate date per delivered file.
-- A corrected file redelivers the same rate date; CORE takes the latest delivery.
--
-- FX_RATE is nullable here on purpose: a row whose rate fails to cast still lands so it can
-- be counted and reconciled against landing_file_manifest. CORE enforces NOT NULL.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_FX_RATES (
    RATE_DATE          DATE          NOT NULL,
    FROM_CURRENCY      VARCHAR(3)    NOT NULL,
    TO_CURRENCY        VARCHAR(3)    NOT NULL,
    FX_RATE            NUMERIC(18,8),
    _SOURCE_FILE       VARCHAR(500),
    _SOURCE_SYSTEM     VARCHAR(30)   NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60)   NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
