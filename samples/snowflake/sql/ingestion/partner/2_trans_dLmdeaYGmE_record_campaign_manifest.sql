-- Beyond Entity trans_dLmdeaYGmE | proc_a5OA9FY6dc "Partner File Ingestion" | order 2
--   target : ent_4vLGSfGlWM  landing_file_manifest
--
-- One manifest row per delivered file, so three per run. The counts are exactly the two
-- sides of the load's WHERE clause: grain keys that parsed and were loaded, grain keys that
-- did not and were rejected. A row whose only fault is an uncastable MEASURE counts as
-- loaded, because it did land; it drops later at the CORE boundary, where it stays
-- countable.
--
-- partner_id records the scope of the run: NULL for a full-day load, the partner for a
-- single-partner reload. Without it loaded_row_count from a scoped reload would look like a
-- collapse in volume rather than a deliberately narrower load. This is also the only
-- producer of landing_file_manifest.partner_id.
--
-- Runs after the load so the counts describe what actually happened.

INSERT INTO landing_file_manifest (file_name, storage_uri, file_format, partner_id, received_at, load_status, loaded_row_count, rejected_row_count)
SELECT :campaign_source_file, :campaign_storage_uri, 'CSV', :partner_id_filter, CURRENT_TIMESTAMP(), 'LOADED',
COUNT(CASE WHEN NULLIF(TRIM(f.campaign_id), '') IS NOT NULL AND NULLIF(TRIM(f.partner_id), '') IS NOT NULL AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter) THEN 1 END),
COUNT(CASE WHEN (NULLIF(TRIM(f.campaign_id), '') IS NULL OR NULLIF(TRIM(f.partner_id), '') IS NULL) AND (:partner_id_filter IS NULL OR TRIM(f.partner_id) = :partner_id_filter) THEN 1 END)
FROM partner_campaign_file f
