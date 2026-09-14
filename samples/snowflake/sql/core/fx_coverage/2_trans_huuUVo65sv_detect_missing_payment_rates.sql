-- Beyond Entity trans_huuUVo65sv | proc_UK8fvT1Asw "Assert FX Rate Coverage" | order 2
-- The same assertion for payments, on PAID_AT rather than the order date. Checked separately
-- rather than inherited from orders: a payment can settle days after its order, at a
-- different rate, in a different currency.
INSERT INTO FX_COVERAGE_GAP (REQUIRED_CURRENCY, REQUIRED_DATE, SOURCE_TABLE, AFFECTED_ROW_COUNT, DETECTED_AT)
SELECT rp.CURRENCY_CODE, TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', rp.PAID_AT)), 'RAW_PAYMENTS', COUNT(*), CURRENT_TIMESTAMP()
FROM RAW_PAYMENTS rp
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = rp.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', rp.PAID_AT))
WHERE rp.CURRENCY_CODE <> 'USD' AND fx.FX_RATE IS NULL
GROUP BY rp.CURRENCY_CODE, TO_DATE(CONVERT_TIMEZONE(:oracle_server_timezone, 'UTC', rp.PAID_AT))
