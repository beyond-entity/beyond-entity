-- Beyond Entity trans_dqJ9ocHpzo  |  proc_EMd95vDcg4 "PostgreSQL Subscription Ingestion"  |  order 2
-- target: RAW_SUBSCRIPTION_EVENTS. Generated from the model.
INSERT INTO RAW_SUBSCRIPTION_EVENTS (EVENT_ID, SUBSCRIPTION_ID, EVENT_TYPE, STATUS, EVENT_AT, SOURCE_CHANNEL, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT e.event_id, e.subscription_id, e.event_type, e.status, e.event_at, e.source_channel,
'POSTGRES_SUBSCRIPTION', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM subscription_events e
WHERE e.event_id > :last_event_id
