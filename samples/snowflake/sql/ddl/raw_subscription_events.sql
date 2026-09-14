-- RAW_SUBSCRIPTION_EVENTS  (Beyond Entity: ent_Ew4nDKg3yx, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Immutable lifecycle event stream. Append-only on an EVENT_ID high-water mark
-- rather than a time window: an id mark cannot miss a late-written event.
-- The ONLY RAW table needing no deduplication -- EVENT_ID is unique and events never change.
--
-- Generated from the modeled entity. No primary key by design.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_SUBSCRIPTION_EVENTS (
    EVENT_ID           BIGINT NOT NULL,
    SUBSCRIPTION_ID    VARCHAR(36) NOT NULL,
    EVENT_TYPE         VARCHAR(40),
    STATUS             VARCHAR(30),
    EVENT_AT           TIMESTAMP_TZ,
    SOURCE_CHANNEL     VARCHAR(30),
    _SOURCE_SYSTEM     VARCHAR(30) NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60) NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
