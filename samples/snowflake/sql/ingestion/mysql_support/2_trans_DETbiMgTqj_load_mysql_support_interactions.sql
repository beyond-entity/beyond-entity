-- Beyond Entity trans_DETbiMgTqj  |  proc_a9NaJ21I2p "MySQL Support Ingestion"  |  order 2
-- target: RAW_SUPPORT_INTERACTIONS. Generated from the model.
INSERT INTO RAW_SUPPORT_INTERACTIONS (INTERACTION_ID, TICKET_ID, INTERACTION_TYPE, AGENT_ID, INTERACTION_AT, DURATION_SECONDS, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT n.interaction_id, n.ticket_id, n.interaction_type, n.agent_id, n.interaction_at, n.duration_seconds,
'MYSQL_SUPPORT', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM support_interactions n
WHERE n.interaction_at >= :window_start AND n.interaction_at < :window_end
