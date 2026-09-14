-- MONTHLY_REVENUE  (Beyond Entity: ent_0lc0oYg4N0, model mdl_rxXc2eUD4f)
-- MONTHLY_REVENUE_CONTRIBUTION  (Beyond Entity: ent_e8oHtB8iYo, same model)
--
-- Fully aggregated, so no customer identifier reaches the published mart at all.
--
-- Each measure is reported in the month it belongs to (BR-3): orders in the order month,
-- payments in the settlement month, subscription MRR in the billing period month. The three
-- are separate measures and are never summed together.
--
-- CHANNEL_CODE is NULL on recurring revenue: a subscription has no sales channel, and
-- naming one would make subscription revenue look like it was sold through a channel.
--
-- The contribution table is build staging, not a published dataset. It exists at customer
-- grain because DISTINCT_CUSTOMER_COUNT cannot be summed across three contributions, and
-- because joining the three facts instead of staging them multiplies every measure.

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.ANALYTICS.MONTHLY_REVENUE (
    REVENUE_MONTH            DATE          NOT NULL,
    BILLING_COUNTRY_CODE     VARCHAR(2),
    CHANNEL_CODE             VARCHAR(30),
    ORDER_COUNT              INT,
    ORDER_REVENUE_USD        NUMERIC(18,2),
    SETTLED_REVENUE_USD      NUMERIC(18,2),
    RECURRING_REVENUE_USD    NUMERIC(18,2),
    DISTINCT_CUSTOMER_COUNT  INT
);

CREATE TABLE IF NOT EXISTS ENTERPRISE_DW.ANALYTICS.MONTHLY_REVENUE_CONTRIBUTION (
    REVENUE_MONTH            DATE          NOT NULL,
    BILLING_COUNTRY_CODE     VARCHAR(2),
    CHANNEL_CODE             VARCHAR(30),
    ENTERPRISE_CUSTOMER_KEY  VARCHAR(64)   NOT NULL,
    ORDER_COUNT              INT,
    ORDER_REVENUE_USD        NUMERIC(18,2),
    SETTLED_REVENUE_USD      NUMERIC(18,2),
    RECURRING_REVENUE_USD    NUMERIC(18,2)
);
