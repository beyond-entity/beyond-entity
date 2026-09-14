-- SUPPORT_INTERACTION_FACT  (Beyond Entity: ent_iqu9zbXcfN, CORE layer)
--
-- Grain: one row per support ticket. Full rebuild.
-- RESOLUTION_SECONDS is null for unresolved tickets rather than zero, so they cannot
-- drag AVG_RESOLUTION_TIME down. No currency here, so the FX gate does not apply.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.SUPPORT_INTERACTION_FACT (
    TICKET_KEY               VARCHAR(64) NOT NULL PRIMARY KEY,
    ENTERPRISE_CUSTOMER_KEY  VARCHAR(64) NOT NULL,
    TICKET_STATUS            VARCHAR(30),
    PRIORITY                 VARCHAR(20),
    CATEGORY_CODE            VARCHAR(40),
    CREATED_AT_UTC           TIMESTAMP_NTZ NOT NULL,
    RESOLVED_AT_UTC          TIMESTAMP_NTZ,
    RESOLUTION_SECONDS       INT,
    IS_RESOLVED              BOOLEAN,
    CHANNEL                  VARCHAR(30)
);
