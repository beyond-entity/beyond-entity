-- CUSTOMER_LIFETIME_VALUE  (Beyond Entity: ent_qU3hMNl6lx, model mdl_rxXc2eUD4f)
--
-- Grain: one row per enterprise customer. Full rebuild.
--
-- CURRENT_MRR_USD was called TOTAL_SUBSCRIPTION_REVENUE, which promised a lifetime figure
-- the source cannot supply: MRR is a monthly run rate, and lifetime subscription revenue
-- needs a billing history this platform does not carry.
--
-- ACQUISITION_COST_USD is the acquisition campaign's cost per acquisition (BR-4), and is
-- NULL for a customer not acquired through a partner campaign. NET_LIFETIME_VALUE_USD nets
-- off KNOWN acquisition cost only -- see BR-4 for why the NULL is not propagated.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.ANALYTICS.CUSTOMER_LIFETIME_VALUE (
    ENTERPRISE_CUSTOMER_KEY  VARCHAR(64)   NOT NULL PRIMARY KEY,
    TOTAL_REVENUE            NUMERIC(18,2),
    CURRENT_MRR_USD          NUMERIC(18,2),
    ORDER_COUNT              INT,
    AVG_ORDER_VALUE_USD      NUMERIC(18,2),
    TENURE_DAYS              INT,
    ACQUISITION_COST_USD     NUMERIC(18,2),
    NET_LIFETIME_VALUE_USD   NUMERIC(18,2)
);
