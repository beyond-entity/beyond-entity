-- Beyond Entity trans_mXLYGBkIPS | proc_UK8fvT1Asw "Assert FX Rate Coverage" | order 1
-- Every currency/UTC-date that landed orders need converted and FX_RATE_DAILY lacks.
-- USD is excluded: a USD order needs no conversion, and requiring a USD rate would let a
-- currency that cannot be wrong block revenue.
-- The join carries the FULL rate key -- currency, TO_CURRENCY, date. A join on currency
-- alone matches every rate date in the table and multiplies the order instead of converting it.
INSERT INTO FX_COVERAGE_GAP (REQUIRED_CURRENCY, REQUIRED_DATE, SOURCE_TABLE, AFFECTED_ROW_COUNT, DETECTED_AT)
SELECT ro.CURRENCY_CODE, TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', ro.ORDER_DATE)), 'RAW_ORDERS', COUNT(*), CURRENT_TIMESTAMP()
FROM RAW_ORDERS ro
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = ro.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', ro.ORDER_DATE))
WHERE ro.CURRENCY_CODE <> 'USD' AND fx.FX_RATE IS NULL
GROUP BY ro.CURRENCY_CODE, TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', ro.ORDER_DATE))
