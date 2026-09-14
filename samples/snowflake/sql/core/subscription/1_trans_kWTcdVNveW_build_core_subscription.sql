-- Beyond Entity trans_kWTcdVNveW | proc_VlepSlkKoH "Build Core Subscription" | order 1
-- RAW_SUBSCRIPTIONS + CUSTOMER_IDENTITY_MAP + FX_RATE_DAILY -> SUBSCRIPTION_FACT. Full rebuild.
--
-- MRR converts on the BILLING PERIOD START -- the period the recurring revenue belongs to,
-- rather than an operational timestamp such as creation or update time. That is why
-- CURRENT_PERIOD_START_UTC is carried on the fact: the conversion date is part of what the
-- USD figure means, and without it nobody can tell which rate applied. MRR_AMOUNT_SOURCE and
-- FX_RATE_APPLIED are retained for the same reason, mirroring ORDER_FACT.
--
-- GATED by Assert FX Rate Coverage on RAW_SUBSCRIPTIONS gaps ONLY.
-- The FX join carries the whole rate key; a join on currency alone matches every rate date.
-- The identity join is scoped to POSTGRES_SUBSCRIPTION; SOURCE_CUSTOMER_REF holds four spaces.
-- The QUALIFY collapses append-only RAW versions to the latest per subscription.
INSERT INTO SUBSCRIPTION_FACT (SUBSCRIPTION_KEY, ENTERPRISE_CUSTOMER_KEY, PLAN_ID, LIFECYCLE_STATE, STARTED_AT_UTC, CANCELED_AT_UTC, CURRENT_PERIOD_START_UTC, CURRENT_PERIOD_END_UTC, SOURCE_CURRENCY_CODE, MRR_AMOUNT_SOURCE, FX_RATE_APPLIED, MRR_USD)
SELECT rs.SUBSCRIPTION_ID, im.ENTERPRISE_CUSTOMER_KEY, rs.PLAN_ID,
CASE WHEN rs.SUBSCRIPTION_STATUS = 'TRIALING' THEN 'TRIAL' WHEN rs.SUBSCRIPTION_STATUS = 'ACTIVE' THEN 'ACTIVE' WHEN rs.SUBSCRIPTION_STATUS = 'PAST_DUE' THEN 'AT_RISK' WHEN rs.SUBSCRIPTION_STATUS = 'PAUSED' THEN 'PAUSED' ELSE 'CHURNED' END,
CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.STARTED_AT),
CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.CANCELED_AT),
CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.CURRENT_PERIOD_START),
CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.CURRENT_PERIOD_END),
rs.CURRENCY_CODE, rs.MRR_AMOUNT,
CASE WHEN rs.CURRENCY_CODE = 'USD' THEN 1 ELSE fx.FX_RATE END,
rs.MRR_AMOUNT * CASE WHEN rs.CURRENCY_CODE = 'USD' THEN 1 ELSE fx.FX_RATE END
FROM RAW_SUBSCRIPTIONS rs
JOIN CUSTOMER_IDENTITY_MAP im ON im.SOURCE_SYSTEM = 'POSTGRES_SUBSCRIPTION' AND rs.CRM_CUSTOMER_REF = im.SOURCE_CUSTOMER_REF
LEFT JOIN FX_RATE_DAILY fx ON fx.FROM_CURRENCY = rs.CURRENCY_CODE AND fx.TO_CURRENCY = 'USD' AND fx.RATE_DATE = TO_DATE(CONVERT_TIMEZONE(:postgres_server_timezone, 'UTC', rs.CURRENT_PERIOD_START))
QUALIFY ROW_NUMBER() OVER (PARTITION BY rs.SUBSCRIPTION_ID ORDER BY rs.UPDATED_AT DESC, rs._INGESTED_AT DESC) = 1
