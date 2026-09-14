-- Beyond Entity trans_ncSl7tiwTo  |  proc_u5kiETSFgV "Build Core Support Interaction"  |  order 1
-- RAW_SUPPORT_TICKETS + CUSTOMER_IDENTITY_MAP -> SUPPORT_INTERACTION_FACT. Full rebuild.
--
-- The QUALIFY is critical, not housekeeping. A ticket lands TWICE by design -- once when
-- created and again when resolved, which is what lets RESOLVED_AT ever be populated.
-- Without deduplication every resolved ticket produces two CORE rows, one with a null
-- RESOLUTION_SECONDS, re-breaking exactly the metric that the created-or-resolved
-- ingestion window was introduced to repair.
-- Latest landing wins: it reflects current source state, so a resolution supersedes the
-- creation and a later reopen supersedes the resolution.
--
-- :mysql_server_timezone is 'UTC' for this sample -- an explicit configuration assumption,
-- never the Snowflake session setting. VERIFY against the real MySQL system: if it stores
-- server-local time, RESOLUTION_SECONDS is wrong by the offset.
INSERT INTO SUPPORT_INTERACTION_FACT (TICKET_KEY, ENTERPRISE_CUSTOMER_KEY, TICKET_STATUS, PRIORITY, CATEGORY_CODE, CREATED_AT_UTC, RESOLVED_AT_UTC, RESOLUTION_SECONDS, IS_RESOLVED, CHANNEL)
SELECT TO_VARCHAR(rt.TICKET_ID), im.ENTERPRISE_CUSTOMER_KEY,
CASE WHEN rt.TICKET_STATUS = 'NEW' THEN 'OPEN' WHEN rt.TICKET_STATUS = 'OPEN' THEN 'OPEN' WHEN rt.TICKET_STATUS = 'PENDING_CUSTOMER' THEN 'WAITING' WHEN rt.TICKET_STATUS = 'ESCALATED' THEN 'ESCALATED' ELSE 'RESOLVED' END,
rt.PRIORITY, rt.CATEGORY_CODE,
CONVERT_TIMEZONE(:mysql_server_timezone, 'UTC', rt.CREATED_AT),
CONVERT_TIMEZONE(:mysql_server_timezone, 'UTC', rt.RESOLVED_AT),
DATEDIFF('second', CONVERT_TIMEZONE(:mysql_server_timezone, 'UTC', rt.CREATED_AT), CONVERT_TIMEZONE(:mysql_server_timezone, 'UTC', rt.RESOLVED_AT)),
CASE WHEN rt.RESOLVED_AT IS NULL THEN FALSE ELSE TRUE END,
rt.CHANNEL
FROM RAW_SUPPORT_TICKETS rt
JOIN CUSTOMER_IDENTITY_MAP im ON im.SOURCE_SYSTEM = 'MYSQL_SUPPORT' AND rt.SUPPORT_CUSTOMER_REF = im.SOURCE_CUSTOMER_REF
QUALIFY ROW_NUMBER() OVER (PARTITION BY rt.TICKET_ID ORDER BY rt._INGESTED_AT DESC, rt._BATCH_ID DESC) = 1
