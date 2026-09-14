-- RAW_ORDER_ITEMS  (Beyond Entity: ent_DYMdvmGE3b, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Faithful copy of Oracle SALES.ORDER_ITEMS. Append-only. ORDER_ITEMS has no
-- timestamp of its own, so ingestion windows it through the parent order: a run lands
-- exactly the lines belonging to the orders it landed.
--
-- Generated from the modeled entity. No primary key: the same business key appears
-- once per ingestion window in which it changed. Deduplication is CORE's job.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_ORDER_ITEMS (
    ORDER_ITEM_ID      NUMERIC(18) NOT NULL,
    ORDER_ID           NUMERIC(18) NOT NULL,
    PRODUCT_CODE       VARCHAR(50),
    QUANTITY           NUMERIC(10),
    UNIT_PRICE         NUMERIC(18,2),
    LINE_AMOUNT        NUMERIC(18,2),
    CURRENCY_CODE      VARCHAR(3),
    _SOURCE_SYSTEM     VARCHAR(30) NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60) NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
