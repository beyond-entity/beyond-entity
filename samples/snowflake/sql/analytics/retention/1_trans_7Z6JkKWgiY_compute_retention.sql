-- Beyond Entity trans_7Z6JkKWgiY  |  proc_F3jEWvf4lM "Build Subscription Retention"  | order 1
--   source : ent_O6Qh9roA0S  SUBSCRIPTION_FACT (CORE)
--   target : ent_G096OamO6a  ENTERPRISE_DW.ANALYTICS.SUBSCRIPTION_RETENTION
--
-- Terminal step of the retention lineage chain from the PostgreSQL status mapping.
-- One row per (cohort month, plan), where the cohort month is the month the subscription
-- started.
--
-- D23 FIXED, and it is worth being precise about what was wrong. The previous statement
-- grouped by LIFECYCLE_STATE *and* derived retention FROM lifecycle state. Every group
-- therefore held exactly one state, so:
--   * RETENTION_RATE could only ever be exactly 1.0 or 0.0, never a rate;
--   * RETAINED_COUNT equalled COHORT_SIZE in every non-churned row, and CHURNED_COUNT
--     equalled it in the churned row;
--   * COHORT_SIZE was one state's slice of the cohort, not the cohort;
--   * RETAINED_MRR_USD in the churned group was the MRR of churned subscriptions, reported
--     under a column named retained.
-- Removing the state from the GROUP BY is what turns all of those into real numbers.
-- RETENTION_STATUS is gone from the entity: at cohort grain there is no single status.
--
-- BR-5. Retained means REVENUE-BEARING (ACTIVE, AT_RISK), per BR-1 -- not merely 'not
-- churned', which counted trialling and paused subscriptions as retained and put the
-- retention rate out of step with recurring revenue.
--
-- RETAINED_COUNT and CHURNED_COUNT deliberately do not add up to COHORT_SIZE. A TRIAL or
-- PAUSED subscription is in neither: not paying, so not retained; not cancelled, so not
-- churned. Forcing it into a bucket would make the arithmetic tidy and the meaning wrong.
--
-- No retention horizon: this reports each cohort AS OF NOW. A real month-1 / month-3 curve
-- needs a history of subscription state over time, which SUBSCRIPTION_FACT does not keep.

INSERT INTO SUBSCRIPTION_RETENTION (COHORT_MONTH, PLAN_ID, COHORT_SIZE, RETAINED_COUNT, CHURNED_COUNT, RETENTION_RATE, RETAINED_MRR_USD)
SELECT DATE_TRUNC('month', s.STARTED_AT_UTC), s.PLAN_ID,
COUNT(s.SUBSCRIPTION_KEY),
SUM(CASE WHEN s.LIFECYCLE_STATE IN ('ACTIVE', 'AT_RISK') THEN 1 ELSE 0 END),
SUM(CASE WHEN s.LIFECYCLE_STATE = 'CHURNED' THEN 1 ELSE 0 END),
AVG(CASE WHEN s.LIFECYCLE_STATE IN ('ACTIVE', 'AT_RISK') THEN 1 ELSE 0 END),
SUM(CASE WHEN s.LIFECYCLE_STATE IN ('ACTIVE', 'AT_RISK') THEN s.MRR_USD ELSE 0 END)
FROM SUBSCRIPTION_FACT s
WHERE s.STARTED_AT_UTC IS NOT NULL
GROUP BY DATE_TRUNC('month', s.STARTED_AT_UTC), s.PLAN_ID
