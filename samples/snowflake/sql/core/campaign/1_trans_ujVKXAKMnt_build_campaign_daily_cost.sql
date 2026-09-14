-- Beyond Entity trans_ujVKXAKMnt  |  proc_7x7b2hFPxu "Build Core Campaign"  |  order 1
--   source : ent_S7007U3oD0  RAW_PARTNER_ACQUISITION_COST (append-only)
--   target : ent_kbvl0ZWGX3  ENTERPRISE_DW.CORE.CAMPAIGN_DAILY_COST
--
-- BR-2: each day's spend converts at its OWN COST_DATE rate. Converting here, once per day,
-- is what makes a campaign total a sum of correctly-converted days rather than one rate
-- applied to everything.
--
-- Dedup partitions on (PARTNER_ID, CAMPAIGN_ID, COST_DATE): campaign identifiers are only
-- unique within a partner, and the row grain is the day. Latest delivery wins, the
-- append-only RAW rule used everywhere.
--
-- The FX join carries the WHOLE rate key -- FROM_CURRENCY, TO_CURRENCY and RATE_DATE. A
-- join on currency alone matches every rate date in the table and multiplies the row
-- instead of converting it. That was the original defect here.
--
-- Rows whose cost failed to cast in RAW drop at this CORE boundary, which is where the
-- two-tier rejection rule puts them: they landed and stayed countable against the manifest,
-- and they are removed before they can reach a published figure.

INSERT INTO CAMPAIGN_DAILY_COST (CAMPAIGN_KEY, PARTNER_ID, CAMPAIGN_ID, COST_DATE, SOURCE_CURRENCY_CODE, COST_AMOUNT_SOURCE, FX_RATE_APPLIED, COST_AMOUNT_USD, ATTRIBUTED_SIGNUPS)
SELECT CONCAT(ac.PARTNER_ID, ':', ac.CAMPAIGN_ID), ac.PARTNER_ID, ac.CAMPAIGN_ID, ac.COST_DATE, ac.CURRENCY_CODE, ac.ACQUISITION_COST,
CASE WHEN ac.CURRENCY_CODE = 'USD' THEN 1 ELSE fx.FX_RATE END,
ac.ACQUISITION_COST * CASE WHEN ac.CURRENCY_CODE = 'USD' THEN 1 ELSE fx.FX_RATE END,
ac.ATTRIBUTED_SIGNUPS
FROM RAW_PARTNER_ACQUISITION_COST ac
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = ac.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = ac.COST_DATE
WHERE ac.ACQUISITION_COST IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY ac.PARTNER_ID, ac.CAMPAIGN_ID, ac.COST_DATE ORDER BY ac._INGESTED_AT DESC, ac._BATCH_ID DESC) = 1
