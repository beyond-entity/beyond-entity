-- Beyond Entity trans_Ja4BzpYdVa | proc_PzWyOakCVL "FX Rate File Ingestion" | order 2
--   target : ent_4vLGSfGlWM  landing_file_manifest
--
-- The producer of rejected_row_count. Until this existed the column was declared,
-- described as a data-quality signal, and written by nothing -- so the two-tier rejection
-- rule had no way to report its own rejections and the count could only ever be zero.
--
-- The two counts are exactly the two sides of the ingestion WHERE clause: rows whose grain
-- key parsed and were loaded, and rows whose grain key did not and were rejected. A row
-- whose only fault is an uncastable MEASURE counts as loaded here, because it did land --
-- it is dropped later, at the CORE boundary.
--
-- Runs after the load so the counts describe what actually happened.

INSERT INTO landing_file_manifest (file_name, storage_uri, file_format, received_at, load_status, loaded_row_count, rejected_row_count)
SELECT :source_file, :storage_uri, 'CSV', CURRENT_TIMESTAMP(), 'LOADED',
COUNT(CASE WHEN TRY_TO_DATE(f.rate_date) IS NOT NULL AND NULLIF(TRIM(f.from_currency), '') IS NOT NULL AND NULLIF(TRIM(f.to_currency), '') IS NOT NULL THEN 1 END),
COUNT(CASE WHEN TRY_TO_DATE(f.rate_date) IS NULL OR NULLIF(TRIM(f.from_currency), '') IS NULL OR NULLIF(TRIM(f.to_currency), '') IS NULL THEN 1 END)
FROM fx_rate_file f
