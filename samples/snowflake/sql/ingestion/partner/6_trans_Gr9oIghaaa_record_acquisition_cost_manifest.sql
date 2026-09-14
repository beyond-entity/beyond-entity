-- Beyond Entity trans_Gr9oIghaaa | proc_a5OA9FY6dc "Partner File Ingestion" | order 6
--   target : ent_4vLGSfGlWM  landing_file_manifest
--
-- The cost file's manifest row. Its rejection test includes the cost date, because cost
-- date is part of this file's grain key -- the test must mirror the load's WHERE clause
-- exactly or the two counts stop adding up to the rows in scope.

INSERT INTO landing_file_manifest (file_name, storage_uri, file_format, partner_id, received_at, load_status, loaded_row_count, rejected_row_count)
SELECT :cost_source_file, :cost_storage_uri, 'PARQUET', :partner_id_filter, CURRENT_TIMESTAMP(), 'LOADED',
COUNT(CASE WHEN NULLIF(TRIM(f.campaign_id), '') IS NOT NULL AND NULLIF(TRIM(f.partner_id), '') IS NOT NULL AND TRY_TO_DATE(f.cost_date) IS NOT NULL AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter) THEN 1 END),
COUNT(CASE WHEN (NULLIF(TRIM(f.campaign_id), '') IS NULL OR NULLIF(TRIM(f.partner_id), '') IS NULL OR TRY_TO_DATE(f.cost_date) IS NULL) AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter) THEN 1 END)
FROM partner_acquisition_cost_file f
