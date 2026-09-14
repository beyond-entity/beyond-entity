-- CAMPAIGN_PERFORMANCE  (Beyond Entity: ent_UCNW4yYNvK, model mdl_rxXc2eUD4f)
--
-- Grain: one row per campaign. Full rebuild. Fully aggregated, no PII.
--
-- The cross-system attribution dataset: partner campaign spend against the Oracle order
-- revenue of the customers that campaign acquired. The two sides only meet because identity
-- resolution mapped the partner customer identifier space onto the enterprise key.
--
-- COST_PER_ACQUISITION_USD and RETURN_ON_AD_SPEND are nullable on purpose. A campaign that
-- acquired nobody has no cost per acquisition, and one with no delivered cost has no return
-- on spend. NULL says "not computable"; a zero would read as free, and an infinity as a
-- triumph.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.ANALYTICS.CAMPAIGN_PERFORMANCE (
    CAMPAIGN_KEY              VARCHAR(64)   NOT NULL PRIMARY KEY,
    CAMPAIGN_NAME             VARCHAR(200),
    CHANNEL                   VARCHAR(40),
    TOTAL_SPEND_USD           NUMERIC(18,2),
    ACQUIRED_CUSTOMER_COUNT   INT,
    ATTRIBUTED_REVENUE_USD    NUMERIC(18,2),
    COST_PER_ACQUISITION_USD  NUMERIC(18,2),
    RETURN_ON_AD_SPEND        NUMERIC(10,4)
);
