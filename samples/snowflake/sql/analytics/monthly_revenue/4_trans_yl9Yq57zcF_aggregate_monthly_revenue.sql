-- Beyond Entity trans_yl9Yq57zcF  |  proc_5WN7LCvuxV "Build Monthly Revenue"  |  order 4
--   target : ent_0lc0oYg4N0  ENTERPRISE_DW.ANALYTICS.MONTHLY_REVENUE
--
-- Collapses the three staged contributions to the published mart grain.
--
-- Booked, settled and recurring revenue stay separate measures and are never summed
-- together: they answer different questions.
--
-- DISTINCT_CUSTOMER_COUNT counts customers contributing any of the three. This is the whole
-- reason the contributions are staged at customer grain -- a distinct count cannot be summed
-- across three separately aggregated inputs.
--
-- Aggregation removes every customer identifier, so the published mart carries no PII.

INSERT INTO MONTHLY_REVENUE (REVENUE_MONTH, BILLING_COUNTRY_CODE, CHANNEL_CODE, ORDER_COUNT, ORDER_REVENUE_USD, SETTLED_REVENUE_USD, RECURRING_REVENUE_USD, DISTINCT_CUSTOMER_COUNT)
SELECT k.REVENUE_MONTH, k.BILLING_COUNTRY_CODE, k.CHANNEL_CODE,
SUM(k.ORDER_COUNT), SUM(k.ORDER_REVENUE_USD), SUM(k.SETTLED_REVENUE_USD), SUM(k.RECURRING_REVENUE_USD),
COUNT(DISTINCT k.ENTERPRISE_CUSTOMER_KEY)
FROM MONTHLY_REVENUE_CONTRIBUTION k
GROUP BY k.REVENUE_MONTH, k.BILLING_COUNTRY_CODE, k.CHANNEL_CODE
