-- Beyond Entity trans_Tg8Y7ew2EN  |  proc_a9NaJ21I2p "MySQL Support Ingestion"  |  order 1
-- target: RAW_SUPPORT_TICKETS. Generated from the model.
INSERT INTO RAW_SUPPORT_TICKETS (TICKET_ID, SUPPORT_CUSTOMER_REF, CONTACT_EMAIL, TICKET_STATUS, PRIORITY, CATEGORY_CODE, CREATED_AT, RESOLVED_AT, CHANNEL, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT t.ticket_id, t.support_customer_ref, t.contact_email, t.ticket_status, t.priority, t.category_code, t.created_at, t.resolved_at, t.channel,
'MYSQL_SUPPORT', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM support_tickets t
WHERE (t.created_at >= :window_start AND t.created_at < :window_end)
OR (t.resolved_at >= :window_start AND t.resolved_at < :window_end)
