# Implementation Verification Findings

## Recorded during final verification — 2026-09-11

### Live contract export correction
A fresh beyond_load_schema read found that the runtime export omitted previous_batch_id from customer_pipeline_publications because its original cached creation specification predated that attribute addition. Beyond Entity itself and the implemented publication manifest already contained the field. The export was corrected from the live MCP schema. Other differences were equivalent explicit DECIMAL(18,2)/numeric(18,2) type spelling. Future exports must use live MCP entity attributes, not cached creation payloads. No business contract or lineage was changed by this correction.

### Runtime SQL isolation and lifecycle
ADR-011 requires isolated staged SQL. Review found that unprefixed temporary views could collide when runtime paths share a Spark session, and per-microbatch views could accumulate. ModeledSQL now assigns a unique identifier namespace per executor, rewrites only modeled identifiers outside quoted literals, and drops temporary views after returning analyzed DataFrames. Literal source_table provenance strings remain unchanged. This is an implementation correction to satisfy the existing boundary decision, not a rewrite of modeled SQL logic. Added targeted namespace/literal and streaming cleanup tests.

### Conflicting event IDs inside one replay horizon
Existing tests covered conflict with an already accepted Silver event. Review added detection for multiple semantic payloads sharing event_id within the same retained raw horizon. The earliest modeled candidate remains the accepted immutable event; conflicting broker references are quarantined. Live stateful dedup still relies on nightly Bronze reconciliation to inspect duplicates removed by its watermark state. Added a same-horizon conflict test. This implements ADR-011's first-accepted/immutable event policy without changing field lineage.

### Export recovery ordering
Report export source dependency metadata is now persisted before writing immutable JSONL. A retry after a partial handoff can recover the exact pinned Gold version, rather than writing bytes whose dependency record might be missing. Dependency metadata uses the explicit pipeline_epoch_dependencies fields. Activation continues to recheck current customer consent on every invocation, including retries; it replaces only the active handoff.

### Read-back evidence
Live inventory: 12 models, 43 entities, 37 processors, 84 transformations and 3 PostgreSQL relationships. Graph validation found zero unresolved attribute references, zero external private-port projections, and zero missing PII tags in checked fields. All seven representative paths remain connected: customer email→customer_360 identifier; quantity→customer revenue; item price→churn probability; event type→activity views; event type→churn probability; partner brand→product performance; model version→activation model version.

### Test evidence and limits
The prior combined suite passed 28 tests with two third-party TestClient deprecation warnings in 220.20 seconds. A final expanded suite is running after the corrections above; its result is not yet claimed. No live PostgreSQL, Kafka, S3, identity-provider or Databricks deployment is claimed. Architecture checkpoints are distinct from Spark runtime checkpoints.

### Expanded verification finding: microbatch session boundary
The expanded suite passed 28 tests before the actual Structured Streaming restart test failed: foreachBatch DataFrames own a microbatch Spark session, while the staged SQL executor and pinned identity DataFrame can belong to the parent session. Session-local temporary views are therefore not a valid cross-session binding. The runtime binding will use Spark application-scoped global temporary views with an unguessable unique executor prefix, explicit global_temp qualification, and guaranteed cleanup after analysis. This is an internal runtime binding only: Unity Catalog access boundaries and modeled attribute lineage remain unchanged. Global temporary views are not an authorization mechanism; mutually untrusted jobs require separate compute. The restart test must pass before completion is claimed.


### Final corrected verification result
After the Spark parent/microbatch binding correction, the complete suite passed: 30 tests, 2 third-party deprecation warnings, 230.23 seconds. This includes actual streaming checkpoint restart, global temporary-view cleanup, same-horizon payload conflict handling, live/daily activity version isolation and the full customer/commerce/partner/events→Silver→Gold→features/inference→exports path. All 37 processors now have DRAFT_IMPLEMENTED status and local TEST_PASSED_WITH_WARNING evidence. The 10-job bundle remains PAUSED and undeployed. Final source hashes and exact test environment are preserved in architecture/implementation_test_evidence.json and test-environment.txt. Earlier failed/prior test results in this document are historical findings, retained to explain the corrections.
