-- Beyond Entity trans_IkCCZ85WpW  |  proc_EMd95vDcg4 "PostgreSQL Subscription Ingestion"  |  order 1
-- target: RAW_SUBSCRIPTIONS. Generated from the model.
INSERT INTO RAW_SUBSCRIPTIONS (SUBSCRIPTION_ID, CRM_CUSTOMER_REF, BILLING_EMAIL, PLAN_ID, SUBSCRIPTION_STATUS, STARTED_AT, CURRENT_PERIOD_START, CURRENT_PERIOD_END, CANCELED_AT, MRR_AMOUNT, CURRENCY_CODE, UPDATED_AT, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT s.subscription_id, s.crm_customer_ref, s.billing_email, s.plan_id, s.subscription_status, s.started_at, s.current_period_start, s.current_period_end, s.canceled_at, s.mrr_amount, s.currency_code, s.updated_at,
'POSTGRES_SUBSCRIPTION', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM subscriptions s
WHERE s.updated_at >= :window_start AND s.updated_at < :window_end
