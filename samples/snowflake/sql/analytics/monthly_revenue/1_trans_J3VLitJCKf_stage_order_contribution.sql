-- Beyond Entity trans_J3VLitJCKf  |  proc_5WN7LCvuxV "Build Monthly Revenue"  |  order 1
--   target : ent_e8oHtB8iYo  MONTHLY_REVENUE_CONTRIBUTION (build staging)
--
-- Booked order revenue, reported in the ORDER month (BR-3), staged at customer grain.
-- Orders carry their own CHANNEL_CODE.
--
-- Only the order measures are written. The payment and subscription columns stay NULL and
-- are filled by their own contributions, which is what keeps the three facts from
-- multiplying each other.

INSERT INTO MONTHLY_REVENUE_CONTRIBUTION (REVENUE_MONTH, BILLING_COUNTRY_CODE, CHANNEL_CODE, ENTERPRISE_CUSTOMER_KEY, ORDER_COUNT, ORDER_REVENUE_USD)
SELECT DATE_TRUNC('month', o.ORDER_DATE_UTC), c.BILLING_COUNTRY_CODE, o.CHANNEL_CODE, o.ENTERPRISE_CUSTOMER_KEY,
COUNT(o.ORDER_KEY), SUM(o.ORDER_AMOUNT_USD)
FROM ORDER_FACT o
JOIN CUSTOMER c ON c.ENTERPRISE_CUSTOMER_KEY = o.ENTERPRISE_CUSTOMER_KEY
GROUP BY DATE_TRUNC('month', o.ORDER_DATE_UTC), c.BILLING_COUNTRY_CODE, o.CHANNEL_CODE, o.ENTERPRISE_CUSTOMER_KEY
