-- RAW_SUPPORT_TICKETS  (Beyond Entity: ent_enbOBmA4lI, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Faithful copy of MySQL support_tickets. Append-only, windowed on created_at OR
-- resolved_at -- so a ticket lands TWICE in its life and CORE dedups to the latest landing.
-- Windowing on creation alone would leave RESOLVED_AT permanently null.
--
-- Generated from the modeled entity. No primary key by design.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_SUPPORT_TICKETS (
    TICKET_ID             BIGINT NOT NULL,
    SUPPORT_CUSTOMER_REF  VARCHAR(64) NOT NULL,
    CONTACT_EMAIL         VARCHAR(320),
    TICKET_STATUS         VARCHAR(30),
    PRIORITY              VARCHAR(20),
    CATEGORY_CODE         VARCHAR(40),
    CREATED_AT            TIMESTAMP_NTZ,
    RESOLVED_AT           TIMESTAMP_NTZ,
    CHANNEL               VARCHAR(30),
    _SOURCE_SYSTEM        VARCHAR(30) NOT NULL,
    _INGESTED_AT          TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID     VARCHAR(60) NOT NULL,
    _BATCH_ID             VARCHAR(60)
);
