# Databricks Lakehouse sample

A retail lakehouse example following operational data, partner files, and Kafka events through Bronze, Silver, and Gold to analytics, ML inference, and activation. The supplied Codex conversation shows design, implementation, correction, and business-facing exploration using Beyond Entity as architecture memory.

- **BE file:** `databricks_lakehouse_sample.bemdl`
- **Viewer:** [Explore the architecture](https://canvas.beyondentity.com/viewsample?sample_project_file_id=hPSEeEVPjzo11eR5gmTF)
- **Download:** [Download the BE project](https://control.beyondentity.com/api/sample_project/hPSEeEVPjzo11eR5gmTF/download)
- **Conversation:** [Selected reading notes](CONVERSATION.md)
- **Compare:** [Databricks and Snowflake](../COMPARISON.md)

<a href="../../assets/screenshots/databricks_review_in_satellite_view.png"><img src="../../assets/screenshots/databricks_review_in_satellite_view.png" alt="Databricks Satellite View with lakehouse layers and connected processors" width="960"></a>

*Explore system boundaries, expand relevant objects, and select an attribute to follow its lineage. Click the screenshot to open the original image.*

## Architecture and implementation

The original project organizes its implementation as a Python package. Its README describes operational and partner ingestion, streaming/replay, identity handling, Silver refinement, Gold products, ML features/inference, exports, service adapters, and publication controls.

The package uses exported BE contracts and SQL, with a processor-to-code map and recorded architecture decisions. Publication epochs and pinned Delta versions define what readers consume; multiple table writes are not treated as one multi-table transaction.

### Included source layout

The source snapshot, job configuration, tests, and architecture notes are included below. The original project README is preserved as [IMPLEMENTATION.md](IMPLEMENTATION.md). The BE design is available through the viewer and download links above; conversation summaries are in [CONVERSATION.md](CONVERSATION.md).

| Location | Purpose |
| --- | --- |
| [src/lakehouse/](src/lakehouse/) | Python ingestion, streaming, transformations, ML, exports, runtime, and service adapters |
| [src/lakehouse/contracts.json](src/lakehouse/contracts.json) | Exported model contracts and SQL snapshot |
| [jobs/](jobs/) | Job entry points |
| [databricks.yml](databricks.yml) | Bundle and job configuration |
| [pyproject.toml](pyproject.toml) | Python dependencies and package/test configuration |
| [tests/](tests/) | Local Spark/Delta and adapter tests |
| [architecture/](architecture/) | Decisions, implementation map, operations, and historical test evidence |

Keep these directories together: the jobs, package configuration, tests, and supporting evidence accompany `src/`. See the [processor-to-code map](architecture/implementation_status.md) and [operations guide](architecture/pipeline_operations.md) to navigate the implementation.

## Run the local checks

From `samples/databricks`, use Python 3.10 or later and Java 17. The initial Spark/Delta setup needs Maven access to resolve dependencies.

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,service]'
.venv/bin/python -m pytest -q
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,service]"
.\.venv\Scripts\python.exe -m pytest -q
```

The Windows commands use the corresponding virtual-environment paths; this snapshot has not been validated on Windows. For workspace configuration and deployment prerequisites, consult [IMPLEMENTATION.md](IMPLEMENTATION.md) and [operations](architecture/pipeline_operations.md). Running the local tests does not deploy the bundle.

## What the recorded verification establishes

The supplied [test evidence](architecture/implementation_test_evidence.json) records **30 passed, 2 warnings** on September 11, 2026, using Python 3.10, Java 17, Spark 3.5.6, and Delta 3.3.2. It describes real local Spark/Delta tests, a streaming restart, and an end-to-end pipeline, with external PostgreSQL/Kafka/API/cloud boundaries mocked or stubbed.

These are historical results supplied with the example; they were not rerun for this documentation. The original notes report 37 modeled processors implemented locally. Re-read BE through MCP for current implementation status rather than treating that count as live state.

The supplied bundle is paused. No live Databricks deployment, real model accuracy, or production integration is established by the local test results. Deployment configuration, access grants, retention/privacy operations, and live service verification remain separate work.

<a href="../../assets/screenshots/databricks_checkpoint.png"><img src="../../assets/screenshots/databricks_checkpoint.png" alt="Databricks checkpoint with design milestone and implementation status snapshot" width="960"></a>

*This earlier checkpoint distinguishes a design milestone from deployed or runtime-tested behavior. The permission prompt on the left belongs to the captured session and is not a required workflow step.*

## Explore with an agent

> Read the latest project checkpoint and relevant transformations through MCP. Trace a customer identifier from its operational source to analytics and activation consumers. Explain publication and retry boundaries. Separate modeled intent, verified local behavior, and deployment assumptions.

[User guide](../../docs/USER_GUIDE.md) · [All samples](../README.md)
