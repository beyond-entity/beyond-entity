-- Beyond Entity trans_dzGW5MkIYi  |  proc_AR6brQlFmY "Build Customer Lifetime Value"  | order 1
--   source : CUSTOMER, ORDER_FACT, SUBSCRIPTION_FACT, CAMPAIGN (all CORE)
--   target : ent_qU3hMNl6lx  ENTERPRISE_DW.ANALYTICS.CUSTOMER_LIFETIME_VALUE
--
-- Terminal step of the revenue lineage chain that starts at Oracle ORDERS.TOTAL_AMOUNT.
--
-- D21 FIXED. The previous statement LEFT JOINed ORDER_FACT and SUBSCRIPTION_FACT to one
-- CUSTOMER row and then aggregated, so a customer with 4 orders and 2 subscriptions
-- reported 8 orders and twice its revenue. Each fact is aggregated on its own now.
--
-- D22 FIXED. The campaign is reached through ACQUISITION_CAMPAIGN_KEY. Campaign identifiers
-- are unique only within a partner, so the id alone would pull another partner's spend.
-- CAMPAIGN is one row per key, so that join cannot fan out.
--
-- BR-4. ACQUISITION_COST_USD is the campaign's COST PER ACQUISITION -- its spend divided by
-- the customers it acquired -- not the whole campaign spend. The old expression charged a
-- campaign's entire spend to every customer it acquired, so a campaign with a hundred
-- customers subtracted its full spend a hundred times and almost everyone came out
-- negative. NET_LIFETIME_VALUE_USD now also includes CURRENT_MRR_USD, which the old
-- statement computed and then ignored.
--
-- The COALESCEs in the net are deliberate, and BR-4 states why. Absent revenue nets as zero
-- because that is what it is. Unknown acquisition cost nets as zero because propagating the
-- NULL would empty the column for every customer not acquired through a partner, which is
-- most of them; the ACQUISITION_COST_USD column beside it stays NULL, and that is where the
-- distinction between "no cost" and "cost unknown" lives.
--
-- Read the net as: revenue booked to date, plus the current monthly recurring run rate,
-- less acquisition cost. It is not a projection, and the two revenue terms are not the same
-- time dimension.

INSERT INTO CUSTOMER_LIFETIME_VALUE (ENTERPRISE_CUSTOMER_KEY, TOTAL_REVENUE, CURRENT_MRR_USD, ORDER_COUNT, AVG_ORDER_VALUE_USD, TENURE_DAYS, ACQUISITION_COST_USD, NET_LIFETIME_VALUE_USD)
SELECT c.ENTERPRISE_CUSTOMER_KEY,
(SELECT SUM(o.ORDER_AMOUNT_USD) FROM ORDER_FACT o WHERE o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
(SELECT SUM(s.MRR_USD) FROM SUBSCRIPTION_FACT s WHERE s.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY AND s.LIFECYCLE_STATE IN ('ACTIVE', 'AT_RISK')),
(SELECT COUNT(o.ORDER_KEY) FROM ORDER_FACT o WHERE o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
(SELECT AVG(o.ORDER_AMOUNT_USD) FROM ORDER_FACT o WHERE o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
DATEDIFF('day', c.FIRST_SEEN_AT_UTC, CURRENT_TIMESTAMP()),
cp.TOTAL_SPEND_USD / NULLIF((SELECT COUNT(c2.ENTERPRISE_CUSTOMER_KEY) FROM CUSTOMER c2 WHERE c2.ACQUISITION_CAMPAIGN_KEY = c.ACQUISITION_CAMPAIGN_KEY), 0),
COALESCE((SELECT SUM(o.ORDER_AMOUNT_USD) FROM ORDER_FACT o WHERE o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY), 0)
+ COALESCE((SELECT SUM(s.MRR_USD) FROM SUBSCRIPTION_FACT s WHERE s.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY AND s.LIFECYCLE_STATE IN ('ACTIVE', 'AT_RISK')), 0)
- COALESCE(cp.TOTAL_SPEND_USD / NULLIF((SELECT COUNT(c2.ENTERPRISE_CUSTOMER_KEY) FROM CUSTOMER c2 WHERE c2.ACQUISITION_CAMPAIGN_KEY = c.ACQUISITION_CAMPAIGN_KEY), 0), 0)
FROM CUSTOMER c
LEFT JOIN CAMPAIGN cp ON cp.CAMPAIGN_KEY = c.ACQUISITION_CAMPAIGN_KEY
