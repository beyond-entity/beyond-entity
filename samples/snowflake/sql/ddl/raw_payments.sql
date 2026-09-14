-- RAW_PAYMENTS  (Beyond Entity: ent_BvTcyQqVGO, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Faithful copy of Oracle SALES.PAYMENTS. Append-only, windowed on PAID_AT.
-- CARD_LAST_FOUR is deliberately NOT ingested -- the exclusion is enforced by the
-- ingestion column list, so do not widen it.
--
-- Generated from the modeled entity. No primary key: the same business key appears
-- once per ingestion window in which it changed. Deduplication is CORE's job.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_PAYMENTS (
    PAYMENT_ID         NUMERIC(18) NOT NULL,
    ORDER_ID           NUMERIC(18) NOT NULL,
    PAYMENT_METHOD     VARCHAR(30),
    PAYMENT_STATUS     VARCHAR(20),
    PAYMENT_AMOUNT     NUMERIC(18,2),
    CURRENCY_CODE      VARCHAR(3),
    PAID_AT            TIMESTAMP_NTZ,
    _SOURCE_SYSTEM     VARCHAR(30) NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60) NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
