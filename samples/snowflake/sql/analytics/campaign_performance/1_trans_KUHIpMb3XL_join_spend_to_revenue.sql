-- Beyond Entity trans_KUHIpMb3XL  |  proc_EkjDDx59xe "Build Campaign Performance"  |  order 1
--   source : CAMPAIGN, CUSTOMER, ORDER_FACT (all CORE)
--   target : ent_UCNW4yYNvK  ENTERPRISE_DW.ANALYTICS.CAMPAIGN_PERFORMANCE
--
-- The cross-system attribution join. Partner campaign spend on one side, Oracle order
-- revenue on the other, connected through the customer. Without identity resolution the two
-- identifier spaces could never meet and this mart could not exist.
--
-- D22 FIXED. The join uses ACQUISITION_CAMPAIGN_KEY against CAMPAIGN_KEY. Joining on
-- CAMPAIGN_ID alone was not partner-scoped, so two partners reusing a campaign id would
-- each be credited with the other's acquired customers and all of their revenue -- the same
-- collision the acquisition cost join had, and just as invisible in the output.
--
-- DIVISION GUARDS. A campaign that acquired nobody divides spend by zero; a campaign with no
-- delivered cost divides revenue by zero or NULL. Snowflake raises on division by zero, so
-- without NULLIF one such campaign fails the whole build. NULL reads as "not computable",
-- which is what it is.
--
-- NO FAN-OUT HERE, and none should be introduced. The grain is the campaign; spend comes
-- from the campaign row itself; acquired customers are counted DISTINCT; and each order
-- reaches the row through exactly one customer. Adding a second one-to-many fact -- payments,
-- subscriptions -- would multiply ATTRIBUTED_REVENUE_USD, which is the D21 defect.

INSERT INTO CAMPAIGN_PERFORMANCE (CAMPAIGN_KEY, CAMPAIGN_NAME, CHANNEL, TOTAL_SPEND_USD, ACQUIRED_CUSTOMER_COUNT, ATTRIBUTED_REVENUE_USD, COST_PER_ACQUISITION_USD, RETURN_ON_AD_SPEND)
SELECT cp.CAMPAIGN_KEY, cp.CAMPAIGN_NAME, cp.CHANNEL,
MAX(cp.TOTAL_SPEND_USD),
COUNT(DISTINCT c.ENTERPRISE_CUSTOMER_KEY),
SUM(o.ORDER_AMOUNT_USD),
MAX(cp.TOTAL_SPEND_USD) / NULLIF(COUNT(DISTINCT c.ENTERPRISE_CUSTOMER_KEY), 0),
SUM(o.ORDER_AMOUNT_USD) / NULLIF(MAX(cp.TOTAL_SPEND_USD), 0)
FROM CAMPAIGN cp
LEFT JOIN CUSTOMER c ON c.ACQUISITION_CAMPAIGN_KEY = cp.CAMPAIGN_KEY
LEFT JOIN ORDER_FACT o ON o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY
GROUP BY cp.CAMPAIGN_KEY, cp.CAMPAIGN_NAME, cp.CHANNEL
