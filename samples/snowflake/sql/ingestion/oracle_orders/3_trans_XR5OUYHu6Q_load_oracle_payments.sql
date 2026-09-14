-- Beyond Entity trans_XR5OUYHu6Q  |  proc_U9h1dVHj2j "Oracle Order Ingestion"  |  order 3
-- target: RAW_PAYMENTS. Written from the model, not by hand -- regenerate if the model changes.
INSERT INTO RAW_PAYMENTS (PAYMENT_ID, ORDER_ID, PAYMENT_METHOD, PAYMENT_STATUS, PAYMENT_AMOUNT, CURRENCY_CODE, PAID_AT, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT p.PAYMENT_ID, p.ORDER_ID, p.PAYMENT_METHOD, p.PAYMENT_STATUS, p.PAYMENT_AMOUNT, p.CURRENCY_CODE, p.PAID_AT,
'ORACLE_SALES', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM PAYMENTS p
WHERE p.PAID_AT >= :window_start AND p.PAID_AT < :window_end
