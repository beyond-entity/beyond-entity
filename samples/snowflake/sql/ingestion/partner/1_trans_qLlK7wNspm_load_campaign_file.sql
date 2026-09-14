-- Beyond Entity trans_qLlK7wNspm  |  proc_a5OA9FY6dc "Partner File Ingestion"  |  order 1
--   source : ent_xJRehU39lS  partner_campaign_file (landing zone stage)
--   target : ent_gm1X0Mnte1  ENTERPRISE_DW.RAW.RAW_CAMPAIGN_DATA
--
-- Executes ENTIRELY IN SNOWFLAKE: the file is read from an external stage, so like the FX
-- ingestion and unlike the database-sourced ones there is no extract/load split.
--
-- D18. This job loads THREE landing objects in one run, so it cannot have a single
-- :source_file parameter. It binds :campaign_source_file, and the other two loads bind
-- theirs. A shared parameter would stamp three different landing objects with the same
-- _SOURCE_FILE and destroy the row-to-manifest join that _SOURCE_FILE exists for.
--
-- Grain key is (campaign_id, partner_id), not campaign_id: the model states campaign_id is
-- only unique within a partner, which is also why CAMPAIGN_KEY is composite downstream.
--
-- Two-tier rejection, as everywhere else in the platform:
--   * a row whose GRAIN KEY will not parse is rejected here and counted in the manifest;
--   * a row whose MEASURE will not parse still lands, with a null, and drops at CORE.
-- START_DATE, END_DATE and ACQUISITION_COST are measures, so they use TRY_ casts. Plain
-- TO_DATE / TO_NUMBER RAISE, and one malformed row would abort the whole daily load.
--
-- CHANNEL and CURRENCY_CODE are normalized because they are codes, not free text: 'usd'
-- and 'USD ' are the same code and letting both through silently splits downstream joins.
-- CAMPAIGN_NAME and TARGET_SEGMENT are free text and land verbatim.
--
-- :partner_id_filter is the modeled single-partner reload. NULL means the whole day.

INSERT INTO RAW_CAMPAIGN_DATA (CAMPAIGN_ID, PARTNER_ID, CAMPAIGN_NAME, CHANNEL, START_DATE, END_DATE, ACQUISITION_COST, CURRENCY_CODE, TARGET_SEGMENT, _SOURCE_FILE, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT TRIM(f.campaign_id), TRIM(f.partner_id), f.campaign_name, UPPER(TRIM(f.channel)), TRY_TO_DATE(f.start_date), TRY_TO_DATE(f.end_date), TRY_TO_NUMBER(f.acquisition_cost), UPPER(TRIM(f.currency_code)), f.target_segment,
:campaign_source_file, 'PARTNER_LANDING', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM partner_campaign_file f
WHERE NULLIF(TRIM(f.campaign_id), '') IS NOT NULL AND NULLIF(TRIM(f.partner_id), '') IS NOT NULL AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter)
