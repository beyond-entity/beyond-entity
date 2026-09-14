-- SUBSCRIPTION_FACT  (Beyond Entity: ent_O6Qh9roA0S, CORE layer)
--
-- Grain: one row per subscription. Full rebuild.
--
-- MRR_USD is converted at the rate for CURRENT_PERIOD_START_UTC -- the billing period the
-- recurring revenue belongs to. All three of CURRENT_PERIOD_START_UTC, MRR_AMOUNT_SOURCE and
-- FX_RATE_APPLIED are carried so MRR_USD is reproducible and auditable from the row alone.
--
-- MRR_USD and FX_RATE_APPLIED are NOT NULL: the structural backstop for the FX quality
-- policy, should the coverage gate ever be bypassed.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.CORE.SUBSCRIPTION_FACT (
    SUBSCRIPTION_KEY          VARCHAR(64)   NOT NULL PRIMARY KEY,
    ENTERPRISE_CUSTOMER_KEY   VARCHAR(64)   NOT NULL,
    PLAN_ID                   VARCHAR(40),
    LIFECYCLE_STATE           VARCHAR(30),
    STARTED_AT_UTC            TIMESTAMP_NTZ,
    CANCELED_AT_UTC           TIMESTAMP_NTZ,
    CURRENT_PERIOD_START_UTC  TIMESTAMP_NTZ,
    CURRENT_PERIOD_END_UTC    TIMESTAMP_NTZ,
    SOURCE_CURRENCY_CODE      VARCHAR(3),
    MRR_AMOUNT_SOURCE         NUMERIC(18,2),
    FX_RATE_APPLIED           NUMERIC(18,8) NOT NULL,
    MRR_USD                   NUMERIC(18,2) NOT NULL
);
