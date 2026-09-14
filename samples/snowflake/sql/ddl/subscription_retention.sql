-- SUBSCRIPTION_RETENTION  (Beyond Entity: ent_G096OamO6a, model mdl_rxXc2eUD4f)
--
-- Grain: one row per (cohort month, plan). Full rebuild. No PII.
--
-- RETENTION_STATUS was removed from this entity: at cohort grain there is no single status,
-- and grouping by it was what made every measure in the mart degenerate.
--
-- RETAINED_COUNT and CHURNED_COUNT do not add up to COHORT_SIZE, deliberately. A TRIAL or
-- PAUSED subscription is neither: not paying, so not retained; not cancelled, so not
-- churned. See BR-5.
--
-- The mart reports each cohort's state AS OF NOW, not retention at month 1, 3 or 6. A real
-- horizon needs a history of subscription state over time; SUBSCRIPTION_FACT keeps only the
-- current state, so adding it is a modelling change rather than a query change.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.ANALYTICS.SUBSCRIPTION_RETENTION (
    COHORT_MONTH      DATE          NOT NULL,
    PLAN_ID           VARCHAR(40),
    COHORT_SIZE       INT,
    RETAINED_COUNT    INT,
    CHURNED_COUNT     INT,
    RETENTION_RATE    NUMERIC(5,4),
    RETAINED_MRR_USD  NUMERIC(18,2)
);
