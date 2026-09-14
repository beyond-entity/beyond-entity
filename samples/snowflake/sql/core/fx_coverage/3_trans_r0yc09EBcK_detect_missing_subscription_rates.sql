-- Beyond Entity trans_r0yc09EBcK | proc_UK8fvT1Asw "Assert FX Rate Coverage" | order 3
-- Subscription MRR, checked on the BILLING PERIOD START -- the period the recurring revenue
-- belongs to, not an operational timestamp.
-- Recorded under its own SOURCE_TABLE because the gate is PER BUILD: a rate missing for
-- orders must not block subscription revenue, and a rate missing for subscriptions must not
-- block order revenue.
INSERT INTO FX_COVERAGE_GAP (REQUIRED_CURRENCY, REQUIRED_DATE, SOURCE_TABLE, AFFECTED_ROW_COUNT, DETECTED_AT)
SELECT rs.CURRENCY_CODE, TO_DATE(CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.CURRENT_PERIOD_START)), 'RAW_SUBSCRIPTIONS', COUNT(*), CURRENT_TIMESTAMP()
FROM RAW_SUBSCRIPTIONS rs
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = rs.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = TO_DATE(CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.CURRENT_PERIOD_START))
WHERE rs.CURRENCY_CODE <> 'USD' AND fx.FX_RATE IS NULL
GROUP BY rs.CURRENCY_CODE, TO_DATE(CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.CURRENT_PERIOD_START))
