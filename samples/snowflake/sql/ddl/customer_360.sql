-- CUSTOMER_360  (Beyond Entity: ent_AtG0ggoMmQ, model mdl_rxXc2eUD4f "Snowflake ANALYTICS Layer")
--
-- Grain: one row per enterprise customer. Full rebuild.
--
-- The PII masking boundary. CUSTOMER_KEY_HASH is the SHA-256 of the normalized email and is
-- the only customer identifier permitted past this point; raw EMAIL, CUSTOMER_NAME and
-- PHONE_NUMBER stop at CORE and must never be added here.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.ANALYTICS.CUSTOMER_360 (
    ENTERPRISE_CUSTOMER_KEY       VARCHAR(64)   NOT NULL PRIMARY KEY,
    CUSTOMER_KEY_HASH             VARCHAR(64),
    BILLING_COUNTRY_CODE          VARCHAR(2),
    CUSTOMER_STATUS               VARCHAR(20),
    FIRST_SEEN_AT_UTC             TIMESTAMP_NTZ,
    ACQUISITION_CAMPAIGN_ID       VARCHAR(64),
    TOTAL_ORDERS                  INT,
    TOTAL_ORDER_REVENUE_USD       NUMERIC(18,2),
    LAST_ORDER_AT_UTC             TIMESTAMP_NTZ,
    SUBSCRIPTION_LIFECYCLE_STATE  VARCHAR(30),
    CURRENT_MRR_USD               NUMERIC(18,2),
    SUPPORT_TICKET_COUNT          INT,
    AVG_RESOLUTION_SECONDS        INT,
    CONTRIBUTING_SOURCE_SYSTEMS   INT
);
