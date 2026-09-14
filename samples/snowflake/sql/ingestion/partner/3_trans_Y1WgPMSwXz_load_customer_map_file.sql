-- Beyond Entity trans_Y1WgPMSwXz  |  proc_a5OA9FY6dc "Partner File Ingestion"  |  order 3
--   source : ent_OQHbvJ5s88  partner_customer_map_file (landing zone stage)
--   target : ent_l35iqCJWzG  ENTERPRISE_DW.RAW.RAW_PARTNER_CUSTOMER_MAP
--
-- The fourth customer identifier space, and a required input to CORE identity resolution.
--
-- EMAIL is externally-sourced PII and is modeled as landing unmasked in RAW; it is hashed
-- at the CORE boundary and only EMAIL_HASH reaches ANALYTICS. It lands verbatim here
-- because RAW is the faithful record of what the partner delivered -- CORE owns the
-- LOWER(TRIM(...)) normalization used for matching. Only the five modeled file columns are
-- carried; do not widen this list.
--
-- Grain key is (partner_customer_id, partner_id): the partner identifier space is scoped by
-- partner, which is what RAW_PARTNER_CUSTOMER_MAP's dedup contract already states.
-- SIGNUP_AT is a measure, so TRY_TO_TIMESTAMP_NTZ -- a bad timestamp lands null rather than
-- aborting the load.

INSERT INTO RAW_PARTNER_CUSTOMER_MAP (PARTNER_CUSTOMER_ID, PARTNER_ID, EMAIL, SIGNUP_AT, FIRST_TOUCH_CAMPAIGN_ID, _SOURCE_FILE, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT TRIM(f.partner_customer_id), TRIM(f.partner_id), f.email, TRY_TO_TIMESTAMP_NTZ(f.signup_at), TRIM(f.first_touch_campaign_id),
:customer_map_source_file, 'PARTNER_LANDING', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM partner_customer_map_file f
WHERE NULLIF(TRIM(f.partner_customer_id), '') IS NOT NULL AND NULLIF(TRIM(f.partner_id), '') IS NOT NULL AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter)
