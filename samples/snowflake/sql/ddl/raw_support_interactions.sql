-- RAW_SUPPORT_INTERACTIONS  (Beyond Entity: ent_azYdnbOJ5J, model mdl_pcE5TphblS "Snowflake RAW Layer")
--
-- Faithful copy of MySQL support_interactions, windowed on interaction_at.
-- note_text is deliberately NOT ingested -- incidental free-text PII stops at the boundary.
--
-- Generated from the modeled entity. No primary key by design.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.RAW.RAW_SUPPORT_INTERACTIONS (
    INTERACTION_ID     BIGINT NOT NULL,
    TICKET_ID          BIGINT NOT NULL,
    INTERACTION_TYPE   VARCHAR(30),
    AGENT_ID           VARCHAR(40),
    INTERACTION_AT     TIMESTAMP_NTZ,
    DURATION_SECONDS   INT,
    _SOURCE_SYSTEM     VARCHAR(30) NOT NULL,
    _INGESTED_AT       TIMESTAMP_NTZ NOT NULL,
    _INGESTION_JOB_ID  VARCHAR(60) NOT NULL,
    _BATCH_ID          VARCHAR(60)
);
