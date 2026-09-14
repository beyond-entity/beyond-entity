# Snowflake conversation reading notes

These notes summarize the supplied Claude Code `session.html` export from September 11, 2026. Turn numbers refer to its navigation. The raw archive is not published here; these are paraphrases, not a verbatim transcript.

| Turns | What to examine |
| --- | --- |
| 4–6 | Open the project, reread updated requirements, and start designing. |
| 7 | Implement from the current architecture, recording newly required decisions in BE first. |
| 8–10 | Review ingestion defects, explicitly choose UTC source-timestamp semantics, and specify missing-FX behavior. |
| 11–13 | Continue ingestion/CORE implementation and clarify the FX conversion date for subscription MRR. |
| 14–19 | Explain revenue origins, investigate high revenue and low campaign ROI, reason about subscription state, and examine the physical location of landing_file_manifest. |

## A concrete design correction: missing FX rates

In turn 10, the user specifies that a required missing currency/date rate is a data-quality failure. The dependent revenue build should fail rather than silently omit rows or publish unresolved USD values, while unrelated pipelines may continue. The policy must first be represented in BE, then aligned with implementation and tests.

This is a useful comparison point: find the dependency and failure semantics in the architecture, not only an exception in code. The existing checkpoint screenshot records an added FX producer and file-ingestion corrections.

## Business definitions affect code

Turn 13 chooses billing-period start as the subscription MRR conversion date. The later revenue, campaign, and subscription questions show why business semantics must remain visible alongside transformation logic.

Turn 19 questions the physical placement and update mechanism of landing_file_manifest. A conflict between an object-storage file and SQL INSERT behavior should lead to an explicit design decision, not an invented storage implementation.

## Historical cautions

The original implementation README contains older open questions alongside later BR-4/BR-5 corrections. Read the conversation in sequence and consult the latest BE checkpoint before classifying an issue as unresolved. The local SQLite harness is not proof of live Snowflake behavior.

[Sample guide](README.md) · [Comparison](../COMPARISON.md)
