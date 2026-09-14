# Pipeline Implementation Status

Beyond Entity is the source of truth. All 37 modeled processors have local runtime implementations, including the three scheduler mappings. Status is DRAFT_IMPLEMENTED, not deployed or production certified. Runtime SQL and entity contracts are exported in src/lakehouse/contracts.json; it is a delivery snapshot, not an alternative authoring source. Update architecture, decisions and lineage through MCP before changing the snapshot or code. Never edit the .bemdl file directly.

Code paths below are relative to src/lakehouse unless prefixed jobs/ or databricks.yml. Test paths are relative to tests/. Shared processor rows cover all designed branches.

| Modeled processor | ID | Implementation | Verification |
|---|---|---|---|
| `sync_customers` | `proc_tLb4Vvc4IN` | source.py; pipeline.py | test_customer.py; test_adapters.py |
| `normalize_customers` | `proc_iV9fZ5QRIe` | transforms.py; pipeline.py | test_customer.py |
| `pseudonymize_customers` | `proc_VOPDc38HLm` | transforms.py; pipeline.py | test_customer.py |
| `sync_orders` | `proc_l6hhYLa792` | batch.py | test_batch.py |
| `sync_order_items` | `proc_O4QuAZheX5` | batch.py | test_batch.py |
| `sync_products` | `proc_myHDLtCBL3` | batch.py | test_batch.py |
| `receive_partner_products` | `proc_cIt9it4kMm` | batch.py | test_batch.py |
| `ingest_landing_to_bronze` | `proc_fM15NUfRm4` | pipeline.py; batch.py | test_customer.py; test_batch.py |
| `stream_kafka_to_bronze` | `proc_OiRRHIXDqQ` | streaming.py | test_streaming.py |
| `clean_streaming_events` | `proc_eIaNup3Rc6` | streaming.py | test_streaming.py |
| `clean_orders` | `proc_5gh3GHrz95` | silver.py; modeled.py | test_batch.py |
| `clean_products` | `proc_Bw43kNAJLO` | silver.py; modeled.py | test_batch.py |
| `clean_items` | `proc_Yqr7ZuRs9W` | silver.py; modeled.py | test_batch.py |
| `clean_partner_products` | `proc_4bl6mv4kjN` | silver.py; modeled.py | test_batch.py |
| `enrich_product_catalog` | `proc_GVyXMdEKUc` | silver.py; modeled.py | test_batch.py |
| `quarantine_invalid_records` | `proc_xPJZ3R43Lt` | transforms.py; silver.py; streaming.py | test_customer.py; test_batch.py; test_streaming.py |
| `aggregate_daily_sales` | `proc_Q6qfSVR5f4` | gold.py; modeled.py | test_gold.py; test_end_to_end.py |
| `aggregate_product_performance` | `proc_qbIcHBzelH` | gold.py; modeled.py | test_gold.py; test_end_to_end.py |
| `aggregate_customer_value` | `proc_5PKFGwJldj` | gold.py; modeled.py | test_gold.py; test_end_to_end.py |
| `aggregate_customer_activity` | `proc_hOx6AKkHBB` | gold.py; modeled.py | test_gold.py; test_end_to_end.py |
| `build_customer_360` | `proc_GFPKimY22l` | gold.py; modeled.py | test_gold.py; test_end_to_end.py |
| `build_churn_features` | `proc_2jj713mipX` | ml.py; modeled.py | test_ml.py |
| `score_customer_churn` | `proc_dsDpnPvrBJ` | ml.py; modeled.py | test_ml.py |
| `register_approved_churn_model` | `proc_RNg283PYQO` | ml.py; modeled.py | test_ml.py |
| `export_consent_filtered_scores` | `proc_THr6W7ng5J` | exports.py; modeled.py | test_ml.py; test_end_to_end.py |
| `serve_sales_reporting` | `proc_uwAuQ4IwoG` | exports.py; modeled.py | test_ml.py; test_end_to_end.py |
| `updateCustomerProfile` | `proc_JdSrpuLm7H` | application.py; jobs/outbox.py | test_application.py |
| `captureBehaviorEvent` | `proc_hVkJwN3rKM` | application.py; jobs/outbox.py | test_application.py |
| `commit_order_lifecycle` | `proc_0YuGq2K03Y` | application.py; jobs/outbox.py | test_application.py |
| `relay_order_events` | `proc_rJlLx1AwTo` | application.py; jobs/outbox.py | test_application.py |
| `record_pipeline_run` | `proc_BTuhhECFqG` | pipeline.py; epochs.py; storage.py | test_customer.py; test_adapters.py; test_end_to_end.py |
| `commit_ingestion_cursor` | `proc_GQhF914SlZ` | pipeline.py; epochs.py; storage.py | test_customer.py; test_adapters.py; test_end_to_end.py |
| `commit_customer_publication` | `proc_ayX5zANz9O` | pipeline.py; epochs.py; storage.py | test_customer.py; test_adapters.py; test_end_to_end.py |
| `publish_pipeline_epoch` | `proc_udU4f93bLK` | pipeline.py; epochs.py; storage.py | test_customer.py; test_adapters.py; test_end_to_end.py |
| `daily_refresh` | `proc_MxtH5pMC0K` | databricks.yml; jobs/; cadence.py | test_orchestration.py; test_end_to_end.py |
| `source_refresh` | `proc_Opa4pYbUjY` | databricks.yml; jobs/; cadence.py | test_orchestration.py; test_end_to_end.py |
| `continuous_refresh` | `proc_OHIQNdX1t9` | databricks.yml; jobs/; cadence.py | test_orchestration.py; test_end_to_end.py |

## Execution and evidence
Tests use real local Spark/Delta and a real file-based Structured Streaming query with restart, plus simulated PostgreSQL/Kafka/HTTP/AWS boundaries. The end-to-end test covers customer identity, commerce and partner ingestion, streaming behavior, Silver, all Gold products, live activity isolation, feature freezing, scoring and exports. Final test results and source hashes are in architecture/implementation_test_evidence.json. Earlier milestone evidence remains historical and must not be interpreted as the final file hashes.

Databricks bundle tasks are configured and statically checked; the bundle has not been validated against a live workspace or deployed. All schedules and continuous triggers are PAUSED. Real database/broker/bucket, credential verifier, restricted compute, grants, approved model release, currencies and partner delivery are deployment bindings. No production model accuracy claim is made; synthetic coefficients exist only in tests. Model training is outside the designed inference pipelines.

## Architectural completion
ADR-010 through ADR-015 and implementation_verification_findings.md record publication atomicity, source epochs, event reconciliation, immutable ML grains, consent refresh, API/outbox behavior, scheduling and runtime session corrections. Architecture checkpoints preserve each milestone and findings as they occur. Physical privacy purge/retention, grants, monitoring integrations and infrastructure provisioning remain operational deployment work, not implemented modeled data processors.

Final local verification: **30 passed, 2 third-party deprecation warnings in 230.23 seconds**. Seven representative live MCP lineage paths connected; zero unresolved attribute references, external private-port projections or missing checked PII tags.
