# Compare the Databricks and Snowflake examples

Read these examples as two ways of using Beyond Entity to preserve intent, implement from transformations, and bring discovered problems back into the design. They have different requirements, agents, code structures, and test environments. This is not a controlled AI benchmark or a platform performance/cost comparison.

| Aspect | Databricks | Snowflake |
| --- | --- | --- |
| Project | [Lakehouse sample](databricks/README.md) | [Enterprise ELT sample](snowflake/README.md) |
| Viewer | [Open architecture](https://canvas.beyondentity.com/viewsample?sample_project_file_id=hPSEeEVPjzo11eR5gmTF) | [Open architecture](https://canvas.beyondentity.com/viewsample?sample_project_file_id=ULbLp9iGQNLXCF4U1Vt8) |
| Recorded agent | Codex | Claude Code |
| Data flow | Operational/partner sources and Kafka → Bronze → Silver → Gold → ML and activation | Operational/partner sources → RAW → CORE → ANALYTICS → modeled dashboards |
| Included implementation | [src/lakehouse](databricks/src/lakehouse/), [jobs](databricks/jobs/), [bundle](databricks/databricks.yml) | [pipelines](snowflake/pipelines/), [sql](snowflake/sql/), [dags](snowflake/dags/), [tests](snowflake/tests/) |
| Design-to-code connection | Exported contracts/SQL and processor-to-code map | Transformation-ID SQL files, parsed ingestion contracts, SQL runners |
| Useful review concerns | Pinned versions, publication epochs, streaming replay, consent, daily/hourly separation | Extraction versus loading, deduplication, join grain, FX coverage, revenue date semantics |
| Historical checks | 30 tests recorded using local Spark/Delta, with external boundaries mocked or stubbed | 252 tests reported using SQLite fixtures and SQL translation |
| Deployment boundary | Paused bundle; no live workspace deployment or real model-accuracy claim | No live Snowflake execution established; four dashboards outside pipeline implementation |
| Conversation notes | [Codex session](databricks/CONVERSATION.md) | [Claude Code session](snowflake/CONVERSATION.md) |

Both source snapshots are included with their original directory structure and original READMEs preserved as [Databricks implementation notes](databricks/IMPLEMENTATION.md) and [Snowflake implementation notes](snowflake/IMPLEMENTATION.md). Raw conversation HTML is not bundled; selected notes are linked above. Test counts are not comparable quality scores, and the suites were not rerun for this documentation.

## 1. Compare the implementation request

Databricks turn 8 and Snowflake turn 7 both ask the agent to preserve modeled contracts, transformation groups, and attribute lineage. When implementation needs a new architectural decision, it should record that decision before implementing it.

Look for the resulting link between design and code: Databricks develops runtime/publication protocols around lakehouse contracts; Snowflake derives executable extraction and loading from modeled SQL while respecting system boundaries.

## 2. Trace one attribute

Open each viewer and select a customer-identity or email attribute. Adjust Max Lineage Depth and expand relevant objects as described in the [user guide](../docs/USER_GUIDE.md#5-review-the-design-visually).

Databricks turns 16–17 ask about email origin, downstream uses, and removal impact. Ask the same style of question of Snowflake, without assuming identical identity rules or consumers.

> Trace this attribute from its source to downstream consumers. Identify transformation rules, privacy or identity boundaries, and what would be affected if its contract changed. Distinguish modeled facts from missing information.

## 3. Review a correction

For Databricks, examine the [architecture decisions](databricks/architecture/architecture_decisions.md) and [implementation findings](databricks/architecture/implementation_verification_findings.md) about daily/hourly publication and pinned versions. For Snowflake, follow turns 8–10 and the missing-FX policy: block only the affected revenue chain and record the policy in BE before aligning code and tests.

Inspect [Databricks contracts](databricks/src/lakehouse/contracts.json) and its [processor-to-code map](databricks/architecture/implementation_status.md). Compare these with [Snowflake contract parsing](snowflake/pipelines/contract.py), [FX coverage](snowflake/pipelines/fx_coverage.py), and [modeled FX checks](snowflake/sql/core/fx_coverage/).

For either example, ask: where is the decision stored, which transformation changed, and which check detects a regression?

## 4. Ask a business question

Later turns move beyond coding to revenue, campaign, identity, and subscription questions. Evaluate whether the answer explains its data sources, distinguishes business definitions, and admits missing information. A question about a capability is not proof that the project implements it.

Snowflake's landing_file_manifest question is particularly useful: a diagram can contain an unresolved physical storage decision even when individual transformations look detailed.

## 5. Separate a snapshot from current status

A checkpoint is a dated record; screenshots and conversations may show earlier states than the uploaded sample or source. The [Snowflake implementation notes](snowflake/IMPLEMENTATION.md) also mix some earlier open questions with later corrections. Read current project state through MCP before deciding whether a problem remains.

Use local verification evidence for the guarantees it actually exercises. Spark/Delta tests and SQLite translation tests do not establish the same runtime behavior, and neither proves a complete production deployment.

## Continue with an agent

> Read both projects through MCP and compare one shared concern, such as customer identity or revenue lineage. For each, identify the modeled rule, implementation location in the included source, verification evidence, and unresolved deployment assumptions. Explain requirement differences before judging implementation choices. Do not modify either project.

[All samples](README.md) · [User guide](../docs/USER_GUIDE.md)
