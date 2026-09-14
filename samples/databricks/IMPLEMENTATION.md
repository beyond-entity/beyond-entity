# Databricks Lakehouse Sample

The **Databricks Lakehouse Sample Project** in Beyond Entity (`PqcaRKCiWKiVB`) is the architecture source of truth. All 37 modeled processors are implemented locally: customer and commerce ingestion, partner files, Kafka streaming/replay, Silver refinement, five Gold products, churn features/inference, exports, source APIs/outbox, publication controls and orchestration.

The implementation is not deployed. All configured schedules and continuous triggers remain **PAUSED**. No real model accuracy or live integration certification is claimed.

## Design and implementation

- [Processor-to-code map](architecture/implementation_status.md) covers every processor and its tests.
- [Operations](architecture/pipeline_operations.md) describes the actual 10-job graph, bootstrap, quality gates and recovery.
- [Test evidence](architecture/implementation_test_evidence.json) records final local results, source hashes and limitations.
- `src/lakehouse/contracts.json` is the live MCP contract/SQL delivery snapshot. Re-read Beyond Entity and record decisions/checkpoints there before changing contracts or implementation. Never directly edit the `.bemdl` file.

The core flow is PostgreSQL/partner landing and Kafka → Bronze → restricted customer identity and curated Silver → Gold → frozen ML features/approved inference → consent-filtered activation and sales reporting. Immutable epoch manifests and cursor CAS publish pinned Delta versions; a sequence of table writes is not a multi-table transaction. Readers must use the publication protocols in `pipeline.py`, `runtime.py` and `epochs.py`.

## Local verification

Use Python 3.10+ and Java 17; initial Delta dependencies require Maven access:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[test,service]'
.venv/bin/python -m pytest -q
```

Tests execute real local Spark 3.5.6/Delta 3.3.2, including an actual Structured Streaming checkpoint restart and an end-to-end pipeline. PostgreSQL/Kafka/AWS/API boundaries use mocks, botocore Stubber and TestClient. Test coefficients are synthetic and never register a production model. See evidence for the exact tested environment.

## Databricks execution

`databricks.yml` defines customers, commerce_source, partner_delivery, events_bronze, events_silver, daily_refresh, live_activity, activation_refresh, model_release and outbox_relay. The daily graph is Silver → event reconciliation → Gold → ML → activation, with reports branching from Gold. Customer and commerce baselines run independently and catch up after missed schedules.

Provide the required bundle variables: restricted existing cluster ID, catalog, S3 artifact root, separate checkpoint root, secret scope, key version, approved currency JSON array, reporting currency, partner identity, Kafka topic and an actual approved model version. Use DBR 14.3 LTS or later with the required connectors and Unity Catalog schemas. Configure workload identity/network access and secret keys listed in Operations. No credentials are included.

Validate the bundle with the Databricks CLI against the actual workspace before deploying. Bootstrap customer/source and real partner snapshots, initialize Bronze before Silver streaming, and register a valid approved artifact before ML. The model release job takes an object key containing exactly the modeled churn_model_versions fields; coefficients must be finite and version content immutable. Authorization to approve artifacts must be enforced by restricted release-job and artifact-storage access.

The FastAPI factory `lakehouse.application.create_app(connect, authenticate, publisher)` supplies `/customers/{customer_id}` and `/behavior-events`. It requires a real credential verifier returning a verified Principal; no permissive default exists. Operational order lifecycle/outbox functions are transaction adapters for existing modeled PostgreSQL tables. Provision those schemas and service hosting separately.

## Recovery and boundaries

Source extracts use repeatable-read UTC snapshots, five-minute overlap, soft-delete ordering and committed baseline chains. A sample extract is capped at 64 MiB per table; larger workloads require a modeled partitioned extractor. Current unresolved quality failures block publication. Reference-only quarantine avoids copying PII. No automatic lock expiry is used; verify a crashed owner is stopped before removing its lock and repairing the same run.

Live event dedup uses a two-hour watermark; nightly Bronze reconciliation recovers late/unresolved rows and quarantines conflicting event payloads. Daily and hourly activity pin separate epochs. Feature partitions are frozen even when empty. Activation rechecks current published consent, including retries, and replaces only the active handoff. Retained historical copies need coordinated privacy operations.

Direct PII stays restricted; pseudonymous keys and hashes are still PII. Preserve pinned Delta versions during retention/VACUUM. Grants, physical retention/purge, monitoring integrations, infrastructure provisioning, real identity-provider wiring and live service validation remain deployment work. Architectural checkpoints are distinct from Spark checkpoint directories.
