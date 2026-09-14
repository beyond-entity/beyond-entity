-- RAW_CUSTOMERS  (Beyond Entity: ent_K0JacNbYrd, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Generated from the Beyond Entity design. Column names, order, types and
-- nullability are the modeled contract -- do not edit here without updating
-- the model first.
--
-- Layer contract: source-shaped, APPEND-ONLY. One row per source *version* of a
-- customer, not one row per customer. There is deliberately no primary key and
-- no unique constraint: the same CUSTOMER_ID appears once per ingestion window
-- in which it changed. Deduplication to the current version is the CORE layer's
-- job (Build Core Customer, proc_PASXcCWvuz).
--
-- PII: CUSTOMER_NAME, EMAIL, PHONE_NUMBER and BILLING_ADDRESS are pii_level 3 /
-- confidentiality H. RAW is access-restricted for this reason; the CORE customer
-- build is the only permitted consumer.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_CUSTOMERS (
    CUSTOMER_ID        NUMERIC(18)   NOT NULL,
    CUSTOMER_NAME      VARCHAR(200),                 -- pii_level 3
    EMAIL              VARCHAR(320),                 -- pii_level 3, identity-resolution matching key
    PHONE_NUMBER       VARCHAR(50),                  -- pii_level 3
    BILLING_ADDRESS    VARCHAR(500),                 -- pii_level 3, reduced to country code in CORE
    COUNTRY_CODE       VARCHAR(2),
    CUSTOMER_STATUS    VARCHAR(20),                  -- Oracle vocabulary, mapped in CORE
    CREATED_AT         TIMESTAMP_NTZ,                -- Oracle server local time, normalized to UTC in CORE
    UPDATED_AT         TIMESTAMP_NTZ,                -- incremental watermark column
    _SOURCE_SYSTEM     VARCHAR(30)   NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60)   NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
