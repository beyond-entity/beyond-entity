-- Beyond Entity trans_LHiLIVlNkW  |  proc_tUDyM0IkCx "Build Customer Support Health"  |  order 1
--   source : ent_iqu9zbXcfN  SUPPORT_INTERACTION_FACT (CORE)
--   target : ent_GUW45vloxQ  ENTERPRISE_DW.ANALYTICS.CUSTOMER_SUPPORT_HEALTH
--
-- Terminal step of the support lineage chain that begins at MySQL support_tickets.
--
-- This is the one mart that needed no correction. It aggregates a SINGLE fact, so there is
-- no second one-to-many table to multiply against -- the D21 fan-out that damaged
-- CUSTOMER_360, MONTHLY_REVENUE and the campaign build simply cannot arise here. Keep it
-- that way: adding a join to another fact reintroduces the defect.
--
-- RESOLUTION_SECONDS is null for unresolved tickets rather than zero, and AVG ignores
-- nulls, so AVG_RESOLUTION_TIME reflects only tickets that actually closed. An unresolved
-- ticket must not read as one resolved instantly.
--
-- ESCALATION_RATE is the mean of a 0/1 indicator, which is the proportion of tickets in
-- this month, category and priority that reached ESCALATED. 'ESCALATED' is a value the
-- CORE status mapping really produces -- an indicator over a status the source never emits
-- would report a permanent zero and look like good news.
--
-- The month is the month the ticket was CREATED, not resolved: this mart measures the load
-- arriving, and a ticket that stays open must not vanish from it.

INSERT INTO CUSTOMER_SUPPORT_HEALTH (REPORTING_MONTH, CATEGORY_CODE, PRIORITY, TICKET_COUNT, RESOLVED_TICKET_COUNT, AVG_RESOLUTION_TIME, AFFECTED_CUSTOMER_COUNT, ESCALATION_RATE)
SELECT DATE_TRUNC('month', t.CREATED_AT_UTC), t.CATEGORY_CODE, t.PRIORITY,
COUNT(t.TICKET_KEY),
SUM(CASE WHEN t.IS_RESOLVED THEN 1 ELSE 0 END),
AVG(t.RESOLUTION_SECONDS),
COUNT(DISTINCT t.ENTERPRISE_CUSTOMER_KEY),
AVG(CASE WHEN t.TICKET_STATUS = 'ESCALATED' THEN 1 ELSE 0 END)
FROM SUPPORT_INTERACTION_FACT t
GROUP BY DATE_TRUNC('month', t.CREATED_AT_UTC), t.CATEGORY_CODE, t.PRIORITY
