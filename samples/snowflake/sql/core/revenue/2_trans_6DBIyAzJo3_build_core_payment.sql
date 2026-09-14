-- Beyond Entity trans_6DBIyAzJo3 | proc_3Ddf5VeRop "Build Core Payment" | order 1
-- RAW_PAYMENTS + ORDER_FACT + FX_RATE_DAILY -> PAYMENT. Full rebuild.
--
-- Inherits the enterprise customer key from the already-conformed order rather than
-- re-resolving identity, so orders and payments can never disagree about who the customer is.
-- The FX rate is looked up on the payment's OWN settlement date: a payment can settle days
-- after its order, at a different rate, in a different currency.
-- Dedups on PAYMENT_ID alone because RAW_PAYMENTS carries no source UPDATED_AT.
INSERT INTO PAYMENT (PAYMENT_KEY, ORDER_KEY, ENTERPRISE_CUSTOMER_KEY, PAYMENT_STATUS, PAYMENT_METHOD, PAID_AT_UTC, SOURCE_CURRENCY_CODE, PAYMENT_AMOUNT_USD)
SELECT TO_VARCHAR(rp.PAYMENT_ID), TO_VARCHAR(rp.ORDER_ID), o.ENTERPRISE_CUSTOMER_KEY,
CASE WHEN rp.PAYMENT_STATUS = 'CAPTURED' THEN 'SETTLED' WHEN rp.PAYMENT_STATUS = 'AUTHORIZED' THEN 'AUTHORIZED' WHEN rp.PAYMENT_STATUS = 'FAILED' THEN 'FAILED' ELSE 'REFUNDED' END,
rp.PAYMENT_METHOD,
CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', rp.PAID_AT),
rp.CURRENCY_CODE,
rp.PAYMENT_AMOUNT * CASE WHEN rp.CURRENCY_CODE = 'USD' THEN 1 ELSE fx.FX_RATE END
FROM RAW_PAYMENTS rp
JOIN ORDER_FACT o ON o.ORDER_KEY = TO_VARCHAR(rp.ORDER_ID)
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = rp.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', rp.PAID_AT))
QUALIFY ROW_NUMBER() OVER (PARTITION BY rp.PAYMENT_ID ORDER BY rp._INGESTED_AT DESC) = 1
