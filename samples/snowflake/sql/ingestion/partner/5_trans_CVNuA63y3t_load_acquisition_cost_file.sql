-- Beyond Entity trans_CVNuA63y3t  |  proc_a5OA9FY6dc "Partner File Ingestion"  |  order 5
--   source : ent_NmN647zEgK  partner_acquisition_cost_file (landing zone stage)
--   target : ent_S7007U3oD0  ENTERPRISE_DW.RAW.RAW_PARTNER_ACQUISITION_COST
--
-- This file's grain is one row per campaign per COST DATE, so COST_DATE is part of the
-- grain key and not a measure: a row whose cost date will not parse cannot be stored at
-- this grain at all, so it is rejected here and counted. ACQUISITION_COST and
-- ATTRIBUTED_SIGNUPS are measures and land null, staying countable until CORE drops them.

INSERT INTO RAW_PARTNER_ACQUISITION_COST (CAMPAIGN_ID, PARTNER_ID, COST_DATE, ACQUISITION_COST, CURRENCY_CODE, ATTRIBUTED_SIGNUPS, _SOURCE_FILE, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT TRIM(f.campaign_id), TRIM(f.partner_id), TRY_TO_DATE(f.cost_date), TRY_TO_NUMBER(f.acquisition_cost), UPPER(TRIM(f.currency_code)), TRY_TO_NUMBER(f.attributed_signups),
:cost_source_file, 'PARTNER_LANDING', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM partner_acquisition_cost_file f
WHERE NULLIF(TRIM(f.campaign_id), '') IS NOT NULL AND NULLIF(TRIM(f.partner_id), '') IS NOT NULL AND TRY_TO_DATE(f.cost_date) IS NOT NULL AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter)
