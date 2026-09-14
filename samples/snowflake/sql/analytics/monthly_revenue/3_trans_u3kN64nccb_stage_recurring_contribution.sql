-- Beyond Entity trans_u3kN64nccb  |  proc_5WN7LCvuxV "Build Monthly Revenue"  |  order 3
--   target : ent_e8oHtB8iYo  MONTHLY_REVENUE_CONTRIBUTION (build staging)
--
-- Subscription MRR, reported in the BILLING PERIOD month (BR-3).
--
-- This is the contribution the old single GROUP BY could not express at all. Driven by
-- ORDER_FACT, recurring revenue appeared only in months where that customer also placed an
-- order, so a subscription-only customer contributed zero recurring revenue for ever. It
-- now reaches the mart on its own terms.
--
-- Only revenue-bearing states count (BR-1): a cancelled or paused subscription is not
-- current recurring revenue.
--
-- CHANNEL_CODE is NULL because a subscription has no sales channel. NULL here means "this
-- measure has no channel", not "unknown" -- inventing a placeholder would make subscription
-- revenue look like it was sold through one.

INSERT INTO MONTHLY_REVENUE_CONTRIBUTION (REVENUE_MONTH, BILLING_COUNTRY_CODE, CHANNEL_CODE, ENTERPRISE_CUSTOMER_KEY, RECURRING_REVENUE_USD)
SELECT DATE_TRUNC('month', s.CURRENT_PERIOD_START_UTC), c.BILLING_COUNTRY_CODE, NULL, s.ENTERPRISE_CUSTOMER_KEY,
SUM(s.MRR_USD)
FROM SUBSCRIPTION_FACT s
JOIN CUSTOMER c ON c.ENTERPRISE_CUSTOMER_KEY = s.ENTERPRISE_CUSTOMER_KEY
WHERE s.CURRENT_PERIOD_START_UTC IS NOT NULL AND s.LIFECYCLE_STATE IN ('ACTIVE', 'AT_RISK')
GROUP BY DATE_TRUNC('month', s.CURRENT_PERIOD_START_UTC), c.BILLING_COUNTRY_CODE, s.ENTERPRISE_CUSTOMER_KEY
