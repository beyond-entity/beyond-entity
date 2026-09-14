-- Beyond Entity trans_W0R9eiHhld  |  proc_U9h1dVHj2j "Oracle Order Ingestion"  |  order 1
-- target: RAW_ORDERS. Written from the model, not by hand -- regenerate if the model changes.
INSERT INTO RAW_ORDERS (ORDER_ID, CUSTOMER_ID, ORDER_STATUS, ORDER_DATE, CURRENCY_CODE, TOTAL_AMOUNT, CHANNEL_CODE, UPDATED_AT, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT o.ORDER_ID, o.CUSTOMER_ID, o.ORDER_STATUS, o.ORDER_DATE, o.CURRENCY_CODE, o.TOTAL_AMOUNT, o.CHANNEL_CODE, o.UPDATED_AT,
'ORACLE_SALES', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM ORDERS o
WHERE o.UPDATED_AT >= :window_start AND o.UPDATED_AT < :window_end
