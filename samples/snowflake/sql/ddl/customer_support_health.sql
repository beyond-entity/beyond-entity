-- CUSTOMER_SUPPORT_HEALTH  (Beyond Entity: ent_GUW45vloxQ, model mdl_rxXc2eUD4f)
--
-- Grain: one row per reporting month, category and priority. Full rebuild.
-- Fully aggregated, so no customer identifier reaches the published mart.
--
-- AVG_RESOLUTION_TIME is the terminal column of the support lineage chain that starts at
-- MySQL support_tickets.created_at and resolved_at.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.ANALYTICS.CUSTOMER_SUPPORT_HEALTH (
    REPORTING_MONTH          DATE          NOT NULL,
    CATEGORY_CODE            VARCHAR(40),
    PRIORITY                 VARCHAR(20),
    TICKET_COUNT             INT,
    RESOLVED_TICKET_COUNT    INT,
    AVG_RESOLUTION_TIME      NUMERIC(18,2),
    AFFECTED_CUSTOMER_COUNT  INT,
    ESCALATION_RATE          NUMERIC(5,4)
);
