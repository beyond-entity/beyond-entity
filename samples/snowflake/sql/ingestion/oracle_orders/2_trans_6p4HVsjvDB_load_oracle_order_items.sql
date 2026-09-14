-- Beyond Entity trans_6p4HVsjvDB  |  proc_U9h1dVHj2j "Oracle Order Ingestion"  |  order 2
-- target: RAW_ORDER_ITEMS. Written from the model, not by hand -- regenerate if the model changes.
INSERT INTO RAW_ORDER_ITEMS (ORDER_ITEM_ID, ORDER_ID, PRODUCT_CODE, QUANTITY, UNIT_PRICE, LINE_AMOUNT, CURRENCY_CODE, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT i.ORDER_ITEM_ID, i.ORDER_ID, i.PRODUCT_CODE, i.QUANTITY, i.UNIT_PRICE, i.LINE_AMOUNT, i.CURRENCY_CODE,
'ORACLE_SALES', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM ORDER_ITEMS i
JOIN ORDERS o ON o.ORDER_ID = i.ORDER_ID
WHERE o.UPDATED_AT >= :window_start AND o.UPDATED_AT < :window_end
