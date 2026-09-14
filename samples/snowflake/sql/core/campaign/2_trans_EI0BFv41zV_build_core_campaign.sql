-- Beyond Entity trans_EI0BFv41zV  |  proc_7x7b2hFPxu "Build Core Campaign"  |  order 2
--   source : ent_gm1X0Mnte1  RAW_CAMPAIGN_DATA (append-only), ent_kbvl0ZWGX3 CAMPAIGN_DAILY_COST
--   target : ent_SyaovSZC9B  ENTERPRISE_DW.CORE.CAMPAIGN
--
-- One row per campaign: attributes from the latest delivery, spend and signups summed from
-- the per-day cost table per BR-2.
--
-- Three defects corrected from the original statement, each of which produced a wrong
-- number rather than an error:
--
--   1. The FX join carried neither a date nor TO_CURRENCY, so it matched every rate date in
--      FX_RATE_DAILY and multiplied the campaign row instead of converting it. Conversion
--      now happens once per day, upstream.
--   2. RAW_CAMPAIGN_DATA is append-only and was read with no dedup, so a redelivered
--      campaign produced several CAMPAIGN rows. QUALIFY takes the latest delivery.
--   3. The acquisition cost join omitted PARTNER_ID, even though campaign identifiers are
--      only unique within a partner -- which is precisely why CAMPAIGN_KEY is composite. Two
--      partners reusing a campaign id had each other's spend added to their totals.
--
-- The cost aggregates are scalar subqueries, not joins. Summing several cost days through a
-- join would multiply the campaign row back out -- the same D21 fan-out the marts had.

INSERT INTO CAMPAIGN (CAMPAIGN_KEY, PARTNER_ID, CAMPAIGN_ID, CAMPAIGN_NAME, CHANNEL, START_DATE, END_DATE, SOURCE_CURRENCY_CODE, TOTAL_SPEND_SOURCE, TOTAL_SPEND_USD, COST_DAY_COUNT, ATTRIBUTED_SIGNUPS, TARGET_SEGMENT)
SELECT CONCAT(rc.PARTNER_ID, ':', rc.CAMPAIGN_ID), rc.PARTNER_ID, rc.CAMPAIGN_ID, rc.CAMPAIGN_NAME, rc.CHANNEL, rc.START_DATE, rc.END_DATE, rc.CURRENCY_CODE,
(SELECT SUM(d.COST_AMOUNT_SOURCE) FROM CAMPAIGN_DAILY_COST d WHERE d.PARTNER_ID = rc.PARTNER_ID AND d.CAMPAIGN_ID = rc.CAMPAIGN_ID),
(SELECT SUM(d.COST_AMOUNT_USD) FROM CAMPAIGN_DAILY_COST d WHERE d.PARTNER_ID = rc.PARTNER_ID AND d.CAMPAIGN_ID = rc.CAMPAIGN_ID),
(SELECT COUNT(d.COST_DATE) FROM CAMPAIGN_DAILY_COST d WHERE d.PARTNER_ID = rc.PARTNER_ID AND d.CAMPAIGN_ID = rc.CAMPAIGN_ID),
(SELECT SUM(d.ATTRIBUTED_SIGNUPS) FROM CAMPAIGN_DAILY_COST d WHERE d.PARTNER_ID = rc.PARTNER_ID AND d.CAMPAIGN_ID = rc.CAMPAIGN_ID),
rc.TARGET_SEGMENT
FROM RAW_CAMPAIGN_DATA rc
QUALIFY ROW_NUMBER() OVER (PARTITION BY rc.PARTNER_ID, rc.CAMPAIGN_ID ORDER BY rc._INGESTED_AT DESC, rc._BATCH_ID DESC) = 1
