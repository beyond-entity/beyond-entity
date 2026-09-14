-- CUSTOMER_IDENTITY_MAP  (Beyond Entity: ent_rEdtkncihw, model mdl_uI9JmSHuG3 "Snowflake CORE Layer")
--
-- The crosswalk between the four independent customer identifier spaces.
-- Grain: one row per (SOURCE_SYSTEM, SOURCE_CUSTOMER_REF) -- never one per source row.
-- Rebuilt in full on every run; it is a current-state crosswalk, not a history.
--
-- No primary key is declared: the enterprise key repeats across source systems by
-- design, which is the entire point of the table.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.CUSTOMER_IDENTITY_MAP (
    ENTERPRISE_CUSTOMER_KEY  VARCHAR(64)   NOT NULL,   -- MD5(LOWER(TRIM(email)))
    SOURCE_SYSTEM            VARCHAR(30)   NOT NULL,
    SOURCE_CUSTOMER_REF      VARCHAR(64)   NOT NULL,   -- pii_level 1
    EMAIL_NORMALIZED         VARCHAR(320),             -- pii_level 3, stops at CORE
    EMAIL_HASH               VARCHAR(64),              -- pii_level 1, SHA-256; crosses into ANALYTICS
    MATCH_METHOD             VARCHAR(30)   NOT NULL,
    MATCH_CONFIDENCE         NUMERIC(5,4),
    RESOLVED_AT              TIMESTAMP_NTZ NOT NULL,
    IS_ACTIVE                BOOLEAN
);
