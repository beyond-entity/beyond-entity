-- Beyond Entity trans_0B0zceN1kv  |  proc_qi2OyAuAAl "Build Customer 360"  |  order 1
--   source : CUSTOMER, ORDER_FACT, SUBSCRIPTION_FACT, SUPPORT_INTERACTION_FACT (all CORE)
--   target : ent_AtG0ggoMmQ  ENTERPRISE_DW.ANALYTICS.CUSTOMER_360
--
-- One row per enterprise customer across four independent source systems. All four reach
-- this row through ENTERPRISE_CUSTOMER_KEY, which exists only because identity resolution
-- ran first.
--
-- PII MASKING BOUNDARY. EMAIL_HASH is selected as CUSTOMER_KEY_HASH; raw EMAIL,
-- CUSTOMER_NAME and PHONE_NUMBER stop at CORE. Do not widen this column list.
--
-- D21 FIXED -- the most damaging defect found in this project. The previous statement LEFT
-- JOINed all three facts to one CUSTOMER row and then aggregated. The joins multiplied: a
-- customer with 3 orders, 2 subscriptions and 4 tickets produced 24 rows, so TOTAL_ORDERS
-- read 24, TOTAL_ORDER_REVENUE_USD was eight times the truth, SUPPORT_TICKET_COUNT was 24
-- and CURRENT_MRR_USD was twelve times. Nothing about the output looked wrong; the numbers
-- were plausible, just several times too large. Each fact is now aggregated on its own, in
-- its own scalar subquery, so no fact can inflate another.
--
-- BR-1 APPLIED, in two places:
--   * CURRENT_MRR_USD sums MRR across ALL the customer's subscriptions in a revenue-bearing
--     state (ACTIVE, AT_RISK). Concurrent plans are all real revenue; a cancelled one is
--     not, and previously contributed for ever.
--   * SUBSCRIPTION_LIFECYCLE_STATE is the highest-precedence state the customer holds. The
--     CASE maps each state to an explicit rank that traces back to BR-1. The old MAX() of
--     the state string was the alphabet deciding: MAX of ACTIVE and CHURNED is CHURNED, and
--     MAX of ACTIVE and TRIAL is TRIAL. MIN of the rank is the highest precedence.
--
-- The precedence CASE has NO ELSE branch, and that is load-bearing. For a customer with no
-- subscription at all, MIN() over an empty set is NULL, and an ELSE would map that NULL onto
-- the last named state -- reporting someone who never subscribed as CHURNED. Without it the
-- CASE yields NULL, which is the truth: this customer has no subscription state.
--
-- CONTRIBUTING_SOURCE_SYSTEMS was declared with no producer at all. It now comes from
-- CUSTOMER.SOURCE_SYSTEM_COUNT, which Build Core Customer already populates.

INSERT INTO CUSTOMER_360 (ENTERPRISE_CUSTOMER_KEY, CUSTOMER_KEY_HASH, BILLING_COUNTRY_CODE, CUSTOMER_STATUS, FIRST_SEEN_AT_UTC, ACQUISITION_CAMPAIGN_ID, TOTAL_ORDERS, TOTAL_ORDER_REVENUE_USD, LAST_ORDER_AT_UTC, SUBSCRIPTION_LIFECYCLE_STATE, CURRENT_MRR_USD, SUPPORT_TICKET_COUNT, AVG_RESOLUTION_SECONDS, CONTRIBUTING_SOURCE_SYSTEMS)
SELECT c.ENTERPRISE_CUSTOMER_KEY, c.EMAIL_HASH, c.BILLING_COUNTRY_CODE, c.CUSTOMER_STATUS, c.FIRST_SEEN_AT_UTC, c.ACQUISITION_CAMPAIGN_ID,
(SELECT COUNT(o.ORDER_KEY) FROM ORDER_FACT o WHERE o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
(SELECT SUM(o.ORDER_AMOUNT_USD) FROM ORDER_FACT o WHERE o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
(SELECT MAX(o.ORDERED_AT_UTC) FROM ORDER_FACT o WHERE o.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
(SELECT CASE MIN(CASE s.LIFECYCLE_STATE WHEN 'ACTIVE' THEN 1 WHEN 'AT_RISK' THEN 2 WHEN 'TRIAL' THEN 3 WHEN 'PAUSED' THEN 4 ELSE 5 END) WHEN 1 THEN 'ACTIVE' WHEN 2 THEN 'AT_RISK' WHEN 3 THEN 'TRIAL' WHEN 4 THEN 'PAUSED' WHEN 5 THEN 'CHURNED' END FROM SUBSCRIPTION_FACT s WHERE s.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
(SELECT SUM(s.MRR_USD) FROM SUBSCRIPTION_FACT s WHERE s.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY AND s.LIFECYCLE_STATE IN ('ACTIVE', 'AT_RISK')),
(SELECT COUNT(t.TICKET_KEY) FROM SUPPORT_INTERACTION_FACT t WHERE t.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
(SELECT AVG(t.RESOLUTION_SECONDS) FROM SUPPORT_INTERACTION_FACT t WHERE t.ENTERPRISE_CUSTOMER_KEY = c.ENTERPRISE_CUSTOMER_KEY),
c.SOURCE_SYSTEM_COUNT
FROM CUSTOMER c
