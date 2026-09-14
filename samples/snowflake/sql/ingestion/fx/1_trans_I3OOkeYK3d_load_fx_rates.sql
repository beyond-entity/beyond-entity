-- Beyond Entity trans_I3OOkeYK3d  |  proc_PzWyOakCVL "FX Rate File Ingestion"  |  order 1
--   source : ent_btP1jORE1Z  fx_rate_file (landing zone stage)
--   target : ent_X6Bespl2VW  ENTERPRISE_DW.RAW.RAW_FX_RATES
--
-- Executes ENTIRELY IN SNOWFLAKE: the file is read from an external stage, so unlike the
-- database-sourced ingestions there is no extract/load split. Append-only.
--
-- Currency codes are normalized here because a currency code is an identifier, not a
-- business fact: 'usd' and 'USD ' are the same code, and letting both reach CORE would
-- silently split the join every revenue build depends on.
--
-- TRY_ casts are load-bearing. Plain TO_DATE / TO_NUMBER RAISE on unparseable input, so one
-- malformed row would abort the entire daily load and rejected_row_count could never be
-- anything but zero.
--
-- Two-tier rejection, applied across every file ingestion in the platform:
--   * a row whose GRAIN KEY will not parse is rejected here (the WHERE) and counted in
--     landing_file_manifest.rejected_row_count -- it cannot be stored at this grain at all;
--   * a row whose MEASURE will not parse still lands, with a null, and is dropped at the
--     CORE boundary where it remains countable.

INSERT INTO RAW_FX_RATES (RATE_DATE, FROM_CURRENCY, TO_CURRENCY, FX_RATE, _SOURCE_FILE, _SOURCE_SYSTEM, _INGESTED_AT, _INGESTION_JOB_ID, _BATCH_ID)
SELECT TRY_TO_DATE(f.rate_date), UPPER(TRIM(f.from_currency)), UPPER(TRIM(f.to_currency)), TRY_TO_NUMBER(f.fx_rate),
:source_file, 'FX_PROVIDER', CURRENT_TIMESTAMP(), :ingestion_job_id, :batch_id
FROM fx_rate_file f
WHERE TRY_TO_DATE(f.rate_date) IS NOT NULL AND NULLIF(TRIM(f.from_currency), '') IS NOT NULL AND NULLIF(TRIM(f.to_currency), '') IS NOT NULL
