-- RAW_SUBSCRIPTIONS  (Beyond Entity: ent_OSn60969iu, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Faithful copy of PostgreSQL subscriptions. Append-only, windowed on updated_at.
-- One customer can hold several subscriptions, which is why identity resolution partitions
-- on CRM_CUSTOMER_REF rather than SUBSCRIPTION_ID.
--
-- Generated from the modeled entity. No primary key by design.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_SUBSCRIPTIONS (
    SUBSCRIPTION_ID       VARCHAR(36) NOT NULL,
    CRM_CUSTOMER_REF      VARCHAR(64) NOT NULL,
    BILLING_EMAIL         VARCHAR(320),
    PLAN_ID               VARCHAR(40),
    SUBSCRIPTION_STATUS   VARCHAR(30),
    STARTED_AT            TIMESTAMP_TZ,
    CURRENT_PERIOD_START  TIMESTAMP_TZ,
    CURRENT_PERIOD_END    TIMESTAMP_TZ,
    CANCELED_AT           TIMESTAMP_TZ,
    MRR_AMOUNT            NUMERIC(18,2),
    CURRENCY_CODE         VARCHAR(3),
    UPDATED_AT            TIMESTAMP_TZ,
    _SOURCE_SYSTEM        VARCHAR(30) NOT NULL,
    _INGESTED_AT          TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID     VARCHAR(60) NOT NULL,
    _BATCH_ID             VARCHAR(60)
);
