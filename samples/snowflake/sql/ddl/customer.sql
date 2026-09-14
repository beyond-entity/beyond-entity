-- CUSTOMER  (Beyond Entity: ent_INwxIrXZq1, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- The conformed customer dimension. Grain: one row per enterprise customer.
-- Rebuilt in full on every run.
--
-- Attribution source is Oracle: name, phone and country come from RAW_CUSTOMERS, so
-- the build is scoped to SOURCE_SYSTEM = 'ORACLE_SALES'. A customer present only in
-- PostgreSQL, MySQL or the partner feed is resolved in CUSTOMER_IDENTITY_MAP but has
-- no row here -- see the known_limitation on proc_PASXcCWvuz.
--
-- PII boundary: EMAIL stops at this table. EMAIL_HASH is the only customer identifier
-- permitted to cross into ANALYTICS.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.CUSTOMER (
    ENTERPRISE_CUSTOMER_KEY  VARCHAR(64)   NOT NULL PRIMARY KEY,
    CUSTOMER_NAME            VARCHAR(200),             -- pii_level 3
    EMAIL                    VARCHAR(320),             -- pii_level 3, stops here
    EMAIL_HASH               VARCHAR(64),              -- pii_level 1
    PHONE_NUMBER             VARCHAR(50),              -- pii_level 3
    BILLING_COUNTRY_CODE     VARCHAR(2),               -- address reduced to country only
    CUSTOMER_STATUS          VARCHAR(20),              -- enterprise vocabulary
    FIRST_SEEN_AT_UTC        TIMESTAMP_NTZ,
    ACQUISITION_CAMPAIGN_ID  VARCHAR(64),
    ACQUISITION_CAMPAIGN_KEY VARCHAR(64),
    SOURCE_SYSTEM_COUNT      INT                       -- how many of the four systems resolved here
);
