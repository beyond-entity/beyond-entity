-- Beyond Entity transformation trans_4THOjFhbA6
--   processor : proc_4osn63QZFi  "Oracle Customer Ingestion"  (module dag_ingest_oracle_customers)
--   source    : ent_vSVcwq36Qc   Oracle SALES.CUSTOMERS
--   target    : ent_K0JacNbYrd   ENTERPRISE_DW.RAW.RAW_CUSTOMERS
--
-- This file is the canonical statement. The Python pipeline derives its extract
-- and load halves from this text rather than restating them, so the code cannot
-- drift from the modeled lineage. Change the model first, then regenerate here.
--
-- Parameters
--   :window_start, :window_end   inclusive/exclusive UPDATED_AT window (orchestrator data interval)
--   :ingestion_job_id            the modeled job identity, constant per DAG
--   :batch_id                    the orchestrator run instance, for replay and reconciliation

INSERT INTO RAW_CUSTOMERS (CUSTOMER_ID, CUSTOMER_NAME, EMAIL, PHONE_NUMBER, BILLING_ADDRESS, COUNTRY_CODE, CUSTOMER_STATUS, CREATED_AT, UPDATED_AT, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT c.CUSTOMER_ID, c.CUSTOMER_NAME, c.EMAIL, c.PHONE_NUMBER, c.BILLING_ADDRESS, c.COUNTRY_CODE, c.CUSTOMER_STATUS, c.CREATED_AT, c.UPDATED_AT,
'ORACLE_SALES', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM CUSTOMERS c
WHERE c.UPDATED_AT >= :window_start AND c.UPDATED_AT < :window_end
