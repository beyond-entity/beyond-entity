-- Beyond Entity trans_PAPFDfxzRI  |  proc_5WN7LCvuxV "Build Monthly Revenue"  |  order 2
--   target : ent_e8oHtB8iYo  MONTHLY_REVENUE_CONTRIBUTION (build staging)
--
-- Payment revenue, reported in the SETTLEMENT month (BR-3) rather than the month the order
-- was booked. Under the old ORDER_FACT-driven GROUP BY, a payment settling in month M
-- against an order from M-1 was reported in M-1, which made a column named "settled" a
-- booking figure.
--
-- The channel is inherited from the order the payment settles, because a channel is a
-- property of an order. Joining PAYMENT to ORDER_FACT here is safe where joining both into
-- one aggregate was not: this contribution aggregates payments only, and the order supplies
-- a dimension rather than a measure.

INSERT INTO MONTHLY_REVENUE_CONTRIBUTION (REVENUE_MONTH, BILLING_COUNTRY_CODE, CHANNEL_CODE, ENTERPRISE_CUSTOMER_KEY, SETTLED_REVENUE_USD)
SELECT DATE_TRUNC('month', p.PAID_AT_UTC), c.BILLING_COUNTRY_CODE, o.CHANNEL_CODE, p.ENTERPRISE_CUSTOMER_KEY,
SUM(p.PAYMENT_AMOUNT_USD)
FROM PAYMENT p
JOIN CUSTOMER c ON c.ENTERPRISE_CUSTOMER_KEY = p.ENTERPRISE_CUSTOMER_KEY
LEFT JOIN ORDER_FACT o ON o.ORDER_KEY = p.ORDER_KEY
WHERE p.PAID_AT_UTC IS NOT NULL
GROUP BY DATE_TRUNC('month', p.PAID_AT_UTC), c.BILLING_COUNTRY_CODE, o.CHANNEL_CODE, p.ENTERPRISE_CUSTOMER_KEY
