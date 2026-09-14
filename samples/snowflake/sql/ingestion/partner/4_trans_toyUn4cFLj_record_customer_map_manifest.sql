-- Beyond Entity trans_toyUn4cFLj | proc_a5OA9FY6dc "Partner File Ingestion" | order 4
--   target : ent_4vLGSfGlWM  landing_file_manifest
--
-- The mapping file's own manifest row, with its own storage URI, so a rejection here is not
-- read as a rejection in the campaign or cost file.

INSERT INTO landing_file_manifest (file_name, storage_uri, file_format, partner_id, received_at, load_status, loaded_row_count, rejected_row_count)
SELECT :customer_map_source_file, :customer_map_storage_uri, 'PARQUET', :partner_id_filter, CURRENT_TIMESTAMP(), 'LOADED',
COUNT(CASE WHEN NULLIF(TRIM(f.partner_customer_id), '') IS NOT NULL AND NULLIF(TRIM(f.partner_id), '') IS NOT NULL AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter) THEN 1 END),
COUNT(CASE WHEN (NULLIF(TRIM(f.partner_customer_id), '') IS NULL OR NULLIF(TRIM(f.partner_id), '') IS NULL) AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter) THEN 1 END)
FROM partner_customer_map_file f
