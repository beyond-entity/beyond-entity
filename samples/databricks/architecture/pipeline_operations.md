# Pipeline Operations and Data Quality

All designed pipeline code and job mappings are implemented locally. The 10-job bundle is paused and has not been deployed. ADR-010–015 define the publication and scheduling rules; implementation_status.md maps every processor to code and tests.

## Actual job graph

| Bundle job | Trigger (UTC) | Work / prerequisites |
|---|---|---|
| customers | hourly :30 | PG customers → immutable landing → Bronze → normalized identity and pseudonyms → customer publication/cursor/audit |
| commerce_source | every 15 minutes | orders/items; products when hourly due; consistent PG transaction → landing/Bronze → commerce_source epoch |
| partner_delivery | explicit delivery | full authoritative CSV object and expected SHA-256 → immutable landing/Bronze → partner epoch |
| events_bronze | continuous, 30-second microbatches | Kafka → Bronze Delta; independent checkpoint; initial earliest retained offsets, failOnDataLoss=true |
| events_silver | continuous, 30-second microbatches | Bronze stream → two-hour watermark/dedup → pinned identity → serialized Silver MERGE and reference quarantine |
| daily_refresh | daily 03:00 | silver → reconcile_events → gold → ml → activation; report depends only on gold |
| live_activity | hourly :10 | latest accepted events + published customer identity → activity_live epoch |
| activation_refresh | hourly :40 | latest ML publication + current published consent → replace active handoff |
| model_release | explicit approved release | exact contract artifact from restricted object storage → immutable model version |
| outbox_relay | every minute | transactionally locked pending outbox → acknowledged Kafka delivery → published timestamp |

The daily Gold task explicitly depends on both silver and reconcile_events. Silver bundles the five commerce cleaning/enrichment processors and quality gates. Gold bundles its five products; ML bundles frozen features and scoring. Customer normalization/pseudonymization runs inside the customer job, not again in the daily DAG. Source, customer and partner epochs are prerequisites captured by version; DAG trigger success alone is not a publication.

Source cadence uses scheduled trigger time; extraction cutoff uses actual job start. Customer and commerce jobs independently catch up a missed daily 00:30 full baseline. Commerce orders/items/products share one transaction when jointly due; the separate customer job is not a cross-job PostgreSQL transaction. Five-minute overlap and full baselines preserve corrections and soft deletes. Sources must retain modeled history; hard-delete/archival changes need a prior architecture decision. A baseline older than 48 hours blocks incremental publication; partner snapshots must be fresh within 48 hours. Source extracts are bounded to 64 MiB serialized input per table for this sample.

## Publication and recovery
Every Delta write is atomic only for its own table. Customer consumers capture one cursor and read the raw/normalized/identity/Silver versions in customer_pipeline_publications. Other batch, Silver, Gold and ML readers use pipeline_table_versions and pipeline_epoch_dependencies in immutable epoch envelopes. Only a conditional cursor update releases an epoch; independent latest-table reads can see incomplete candidates. Version retention/VACUUM must preserve active referenced versions.

Persist request identity and source dependencies before work that must survive retry. Immutable landing data/checksums and manifests prevent source re-extraction after completed delivery. Failed candidates remain raw evidence but are excluded from the committed predecessor chain. A post-cursor failure is already committed and its success audit is repaired. Metrics use actual counts; unknown failed counts remain null.

Scoped storage locks serialize each writer family; quarantine, Silver events and the shared activity table have common locks. Lock objects have no automatic expiry. An operator may remove a stale lock only after verifying its owner has stopped; then repair the same run. All bundle jobs permit one concurrent run and three retries with at least 60 seconds between attempts. Alert delivery is an environment integration, not configured here.

## Quality, streaming and temporal boundaries
Latest source versions are selected before tombstones. Invalid latest versions, unorderable IDs/timestamps, conflicting ties, unresolved current parent joins, duplicate grains and invalid approved currencies block release. Historical/resolved rejects do not permanently block later good epochs. Quarantine contains source references rather than copied PII. ANSI decimal casts detect overflow. Gross merchandise totals reconcile per currency; order counts are distinct across line fanout. Taxes, refunds, discounts and FX conversion are outside this metric.

Live events require schema version 1 and event-specific identifiers; reject timestamps over five minutes beyond ingestion before watermark state. Nightly retained Bronze reconciliation recovers late/unresolved events and detects same-ID semantic conflicts, including conflicts within one replay horizon. First accepted event payload remains immutable. State-dropped duplicates are inspected by reconciliation. Runtime SQL binds uniquely namespaced global temporary views across parent/microbatch sessions, preserves literal provenance and cleans them after analysis. This is runtime binding, not access control; mutually untrusted workloads need separate compute.

Daily activity uses as_of_date midnight UTC; hourly activity uses activity_cutoff. Both serialize writes to customer_activity_summary, but activity_live and gold epochs pin different versions. Daily ML cannot read partial-day hourly output accidentally. Feature partitions, including empty partitions, are frozen by date/currency; changes require an explicit backfill decision. Approved finite model coefficients, matching currency and training cutoff before scoring date are mandatory. No approved real artifact has been supplied by this implementation task.

Activation rechecks consent on every invocation, including retry, and replaces the active JSONL handoff. Reports pin Gold dependencies before immutable bytes and use explicit date bounds. Export JSON numbers retain monetary numeric types; exports are capped at 64 MiB. Historical privacy deletion is a separate coordinated operational process, not solved by replacing the active handoff.

## Deployment bindings and bootstrap
Provide an existing restricted Unity Catalog cluster, schemas bronze/silver_restricted/silver/gold/ml, restricted S3 artifact/checkpoint roots, approved currencies, reporting currency, partner identity and workload credentials. Secret scope keys: postgres-dsn, identity-pepper, email-pepper, kafka-options-json (Spark consumer options), kafka-producer-options-json (Confluent producer options). No secrets belong in the repository or architecture.

Validate the bundle in the actual workspace before deployment. Bootstrap customers, commerce_source and an actual partner_delivery; initialize events_bronze before events_silver; register a real approved artifact before running ML. Configure model_version and actual partner object/checksum parameters. The application factory requires a deployment-supplied credential verifier, database factory and broker adapter; endpoint hosting is separate from job deployment. Operational tables and outbox DDL must match BE contracts before adapters run.

Raw/restricted data and Spark logs require restricted service principals. Curated hashes/customer keys/sessions/scores remain PII. Key rotation needs coordinated rekey/backfill; never change a pepper under the same key_version. Privacy deletion must purge source-linked raw, identity, Silver, Gold, features, scores and retained exports. Retention jobs, grants, encryption and monitoring integrations are not provisioned. Local tests do not certify cloud permissions or live services.
