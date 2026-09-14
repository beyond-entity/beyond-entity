# Beyond Entity modeling principles

Use this reference when creating or changing BE models, entities, processors, or transformations. It provides general design criteria for architecture memory; derive concrete requirements from the selected project's current documents, models, and implementation. Apply established project conventions where they differ from these defaults, and make material tradeoffs explicit.

For MCP access, current-state checks, code synchronization, and checkpoint handoffs, follow [the skill workflow](../SKILL.md).

## Model real system boundaries

A model should represent a meaningful system, runtime, storage, or ownership boundary. Consider separate models when responsibilities, deployment lifecycles, technologies, or integration contracts differ. Examples include a relational database, an API service, a client application, object storage, and an external provider.

Choose boundaries that make ownership and interactions understandable. Do not create a model solely to group shapes in a diagram, or split every component into a separate model without a useful boundary.

## Keep logical and physical names separate

Logical names express business meaning in the project's working language. Physical names match actual implementation identifiers and the project's naming conventions.

For example, an entity with logical name `Order Submission` might have physical name `order_submissions`; a processor named `Submit Order` should use the physical identifier of its actual implementation. These are examples, not identifiers to create automatically. Keep mappings explicit when code and model names differ.

## Start from workflow questions

Before adding structures, identify the questions and actions the system must support:

- Who initiates the work, and what are they acting on?
- What information enters the workflow, and what result is produced?
- Who may view, change, approve, or reject it?
- Which states, historical facts, and submitted snapshots must be retained?
- Which queries and downstream consumers depend on the result?

Use the answers to identify core workflow entities and contracts before extracting support tables. Review the main query and processing paths: opaque payloads, generic entities, or excessive joins may indicate that the domain is not represented clearly.

## Treat entities as data contracts

An entity should describe an identifiable persisted or exchanged structure, such as a storage record, request, response, message, or file metadata. Make its role and owning model clear; avoid assuming all entities are database tables.

Represent the attributes and constraints needed to understand the contract, including identifiers, types, required or optional values, relationships, and cardinality where applicable and supported. Distinguish a live reference from a historical snapshot when later edits must not change a submitted or audited result.

When stored and exchanged structures differ, model their relevant contracts and mappings explicitly. Do not assume that an API response is identical to its source table. Verify consumers before changing a shared contract.

## Make processor transformations explain behavior

A processor should have a clear responsibility. Its transformations should explain how modeled inputs become outputs: source and target entities and attributes, derivations, conditions, and dependencies to the extent supported by the current BE model.

Keep mappings precise enough to trace an output to its inputs and understand the intended behavior. Record relevant business rules in the appropriate transformation or associated design documentation. Do not invent MCP fields to express unsupported details, or reproduce incidental code syntax that adds no architectural meaning.

Check connected contracts when changing a transformation. Preserve field lineage and describe intentional omissions or unmapped values when they matter. Use the skill workflow to compare transformations with code before implementation changes and verify agreement afterward.

## Keep traceable domain data explicit

Prefer explicit attributes or child entities when individual values require lineage, filtering, validation, authorization, review, audit, or transformation mapping. Avoid hiding such values in JSON, unstructured blobs, or generic key-value payloads merely to defer modeling.

Aggregate storage can be appropriate for content whose internals are outside the modeled contract, such as an unprocessed provider payload retained for audit or arbitrary user metadata. The criterion is how the system uses the data, not the type name alone. If nested values become part of a workflow, query, or downstream mapping, model the relevant structure explicitly.

## Normalize according to domain needs

Do not split an entity merely because some fields are optional, multilingual, or potentially reusable. Keep fields together when they share lifecycle, ownership, access rules, and common read/write patterns.

Consider separate entities for repeated child collections, true many-to-many relationships, independent lifecycles, separately secured data, event history, and immutable submissions. Check whether a domain user could explain the separate object and whether the split improves the main workflow.

Balance traceability with understandable query paths. Neither opaque aggregates nor excessive fragmentation should obscure the business object.

## Model workflow state explicitly

For stateful workflows, represent the subject, initiating actor, current state, permitted transitions, responsible actors, and relevant history. Include review outcomes, assignments, generated artifacts, or access records when required by the project.

Distinguish current state from the evidence of how it was reached. Where the workflow requires auditability, a mutable status alone is insufficient; preserve the relevant events or snapshots. Avoid adding histories and audit structures without a concrete requirement.

## Review the architecture as a connected whole

Before considering a modeling change complete, trace the affected path from input through processor transformations to storage and outputs. Check that names, contracts, relationships, and mappings agree, and that the design still answers the workflow questions.

Resolve or explicitly record discrepancies between intended design and verified implementation. Preserve the reasoning behind material design choices in BE so the next human or agent can understand the architecture without reconstructing it from chat. Use the skill workflow to verify updates and leave a checkpoint handoff.
