-- RAW_ORDERS  (Beyond Entity: ent_DmT1jmONAy, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Faithful copy of Oracle SALES.ORDERS. Append-only; one row per source
-- version of an order, not one row per order. TOTAL_AMOUNT is in the order's own
-- currency and is step 1 of the revenue lineage chain.
--
-- Generated from the modeled entity. No primary key: the same business key appears
-- once per ingestion window in which it changed. Deduplication is CORE's job.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_ORDERS (
    ORDER_ID           NUMERIC(18) NOT NULL,
    CUSTOMER_ID        NUMERIC(18) NOT NULL,
    ORDER_STATUS       VARCHAR(20),
    ORDER_DATE         TIMESTAMP_NTZ,
    CURRENCY_CODE      VARCHAR(3),
    TOTAL_AMOUNT       NUMERIC(18,2),
    CHANNEL_CODE       VARCHAR(30),
    UPDATED_AT         TIMESTAMP_NTZ,
    _SOURCE_SYSTEM     VARCHAR(30) NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60) NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
