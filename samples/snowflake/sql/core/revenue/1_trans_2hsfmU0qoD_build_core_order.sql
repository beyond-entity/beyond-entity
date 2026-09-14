-- Beyond Entity trans_2hsfmU0qoD | proc_3ASyTmTu51 "Build Core Order" | order 1
-- RAW_ORDERS + CUSTOMER_IDENTITY_MAP + FX_RATE_DAILY -> ORDER_FACT. Full rebuild.
--
-- GATED by Assert FX Rate Coverage. This statement must not run when FX_COVERAGE_GAP is
-- non-empty. Four things here are load-bearing:
--   * the FX join carries the WHOLE rate key (currency, TO_CURRENCY, the order's UTC date).
--     A join on currency alone matches every rate date and multiplies the order rather than
--     converting it -- a fan-out that silently inflates revenue;
--   * USD orders take a rate of 1 rather than needing a USD->USD row, so a currency that
--     cannot be wrong can never block revenue;
--   * the identity join is scoped to ORACLE_SALES because SOURCE_CUSTOMER_REF holds four
--     identifier spaces;
--   * the QUALIFY collapses append-only RAW versions to the latest per order.
INSERT INTO ORDER_FACT (ORDER_KEY, ENTERPRISE_CUSTOMER_KEY, ORDER_STATUS, ORDERED_AT_UTC, ORDER_DATE_UTC, SOURCE_CURRENCY_CODE, ORDER_AMOUNT_SOURCE, FX_RATE_APPLIED, ORDER_AMOUNT_USD, CHANNEL_CODE)
SELECT TO_VARCHAR(ro.ORDER_ID), im.ENTERPRISE_CUSTOMER_KEY,
CASE WHEN ro.ORDER_STATUS = 'PENDING' THEN 'PENDING' WHEN ro.ORDER_STATUS = 'PAID' THEN 'CONFIRMED' WHEN ro.ORDER_STATUS = 'SHIPPED' THEN 'CONFIRMED' WHEN ro.ORDER_STATUS = 'COMPLETED' THEN 'FULFILLED' WHEN ro.ORDER_STATUS = 'CANCELLED' THEN 'CANCELLED' ELSE 'REFUNDED' END,
CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', ro.ORDER_DATE),
TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', ro.ORDER_DATE)),
ro.CURRENCY_CODE, ro.TOTAL_AMOUNT,
CASE WHEN ro.CURRENCY_CODE = 'USD' THEN 1 ELSE fx.FX_RATE END,
ro.TOTAL_AMOUNT * CASE WHEN ro.CURRENCY_CODE = 'USD' THEN 1 ELSE fx.FX_RATE END,
ro.CHANNEL_CODE
FROM RAW_ORDERS ro
JOIN CUSTOMER_IDENTITY_MAP im ON im.SOURCE_SYSTEM = 'ORACLE_SALES' AND TO_VARCHAR(ro.CUSTOMER_ID) = im.SOURCE_CUSTOMER_REF
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = ro.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', ro.ORDER_DATE))
QUALIFY ROW_NUMBER() OVER (PARTITION BY ro.ORDER_ID ORDER BY ro.UPDATED_AT DESC, ro._INGESTED_AT DESC) = 1
