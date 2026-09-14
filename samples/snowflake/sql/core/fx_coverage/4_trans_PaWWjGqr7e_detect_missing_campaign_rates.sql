-- Beyond Entity trans_PaWWjGqr7e | proc_UK8fvT1Asw "Assert FX Rate Coverage" | order 4
-- Campaign spend, checked on the COST DATE -- the day the spend belongs to (BR-2).
--
-- This branch carries more weight than the others. Campaign spend is a SUM over days, and
-- SUM ignores NULLs, so one missing rate would quietly *reduce* a campaign total instead of
-- nulling it: the campaign would look cheaper and its ROI better. Silently understating
-- spend is the exact failure the FX policy exists to prevent, and this gate plus the NOT
-- NULL columns on CAMPAIGN_DAILY_COST are what make it impossible.
--
-- Rows whose cost failed to cast in RAW are excluded: they have no amount to convert, so
-- they require no rate. They drop at the CORE boundary, where the two-tier rule puts them.
--
-- Own SOURCE_TABLE, because the gate is per build: a campaign gap blocks only the campaign
-- build.
INSERT INTO FX_COVERAGE_GAP (REQUIRED_CURRENCY, REQUIRED_DATE, SOURCE_TABLE, AFFECTED_ROW_COUNT, DETECTED_AT)
SELECT ac.CURRENCY_CODE, ac.COST_DATE, 'RAW_PARTNER_ACQUISITION_COST', COUNT(*), CURRENT_TIMESTAMP()
FROM RAW_PARTNER_ACQUISITION_COST ac
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = ac.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = ac.COST_DATE
WHERE ac.CURRENCY_CODE <> 'USD' AND ac.ACQUISITION_COST IS NOT NULL AND fx.FX_RATE IS NULL
GROUP BY ac.CURRENCY_CODE, ac.COST_DATE
