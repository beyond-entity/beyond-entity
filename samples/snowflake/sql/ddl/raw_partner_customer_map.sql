-- RAW_PARTNER_CUSTOMER_MAP  (Beyond Entity: ent_l35iqCJWzG, model mdl_pcE5TphblS)
--
-- Append-only. Grain: one row per partner customer mapping per delivered file, where a
-- mapping is identified by the (PARTNER_ID, PARTNER_CUSTOMER_ID) pair -- the partner
-- identifier space is scoped by partner.
--
-- SECURITY. EMAIL holds unmasked externally-sourced PII (pii_level 3). It is permitted at
-- RAW because CORE identity resolution matches on it; it is hashed at the CORE boundary and
-- only EMAIL_HASH reaches ANALYTICS. This table needs restricted RAW-layer grants.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_PARTNER_CUSTOMER_MAP (
    PARTNER_CUSTOMER_ID      VARCHAR(64)   NOT NULL,
    PARTNER_ID               VARCHAR(64)   NOT NULL,
    EMAIL                    VARCHAR(320),
    SIGNUP_AT                TIMESTAMP_NTZ,
    FIRST_TOUCH_CAMPAIGN_ID  VARCHAR(64),
    _SOURCE_FILE             VARCHAR(500),
    _SOURCE_SYSTEM           VARCHAR(30)   NOT NULL,
    _INGESTED_AT             TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID        VARCHAR(60)   NOT NULL,
    _BATCH_ID                VARCHAR(60)
);
