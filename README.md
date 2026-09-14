# Beyond Entity — Architecture Memory for AI Coding Agents

[English](README.md) · [한국어](README_ko.md) · [日本語](README_ja.md)

Beyond Entity gives AI agents and engineers a persistent, shared architecture memory: system intent, design decisions, models, data contracts, processor transformations, and implementation context that can be carried from one work session to the next.

The **beyond-entity-mcp** plugin connects this architecture memory to an AI coding workflow through the local Beyond Entity MCP server. Its skill guides an agent to recover context, check the design before changing code, keep architecture aligned with verified implementation changes, and leave a checkpoint for the next agent or human.

Use Beyond Entity for **software architecture modeling**, **architecture diagrams**, **data lineage**, and **design-to-code workflows** with Claude Code or Codex through MCP (Model Context Protocol).

[Download Beyond Entity](https://beyondentity.com/en/download) · [Installation guide](INSTALL.md) · [User guide](docs/USER_GUIDE.md) ([한국어](docs/USER_GUIDE_ko.md) · [日本語](docs/USER_GUIDE_ja.md)) · [Sample projects](samples/README.md) · [Website](https://beyondentity.com) · [GitHub](https://github.com/beyond-entity/beyond-entity)

[![Table Q web, API, and database attribute lineage](assets/screenshots/table-q-workflow.png)](https://canvas.beyondentity.com/viewsample?sample_project_file_id=rXxLCaaJ1nEVN9CKbneL)

*Trace a workflow from web interactions through API transformations to database attributes. Click the image to explore Table Q in the viewer.*

## Start from a design or from existing code

You can build architecture memory from either direction:

- **Start with design.** Ask your AI agent to turn your requirements into a design in Beyond Entity through MCP, including system boundaries, entities, data contracts, processors, and transformations. You can also design web and app architectures, ERDs, APIs, ETL/ELT pipelines, and schedulers directly in the Beyond Entity app, or combine hands-on modeling with AI assistance. Review and refine the design together, then ask the agent to implement it.
- **Start with existing code.** Ask your agent to inspect a codebase, extract its architecture and data flows, and record the corresponding models and design documentation in Beyond Entity through MCP. Review the extracted design and distinguish code-backed facts from inferred intent or unresolved questions.

Both approaches lead to the same workflow: use the architecture as a shared reference while coding, and keep it aligned with verified implementation changes. You can start with one feature or service and expand the architecture memory as needed.

## Ask AI to reference the design while coding

Ask your coding agent to consult Beyond Entity before implementing a feature, fixing a bug, or refactoring. The agent can read the relevant processor transformations, input/output contracts, and dependencies through MCP, then use that context to guide its changes.

When the requested behavior changes the architecture, ask the agent to update the corresponding BE design and record why it changed. This makes the design useful throughout development and preserves context for the next agent or engineer. Design reference is an agent workflow, not an automatic guarantee that generated code conforms; verify the implementation against the design.

## How it works

1. **Recover context.** Read the latest checkpoint and relevant project documents; inspect changes made by other agents or humans.
2. **Check the design.** Locate the affected processor and read its current transformations, input/output entities, and attributes before modifying code.
3. **Implement and synchronize.** Make the requested change and update the affected architecture when modeled behavior changes. Investigate discrepancies rather than assuming every code difference is intentional.
4. **Verify and hand off.** Check that implementation and design agree, then record completed changes, rationale, verification, and remaining work in a checkpoint.

Project reads and writes go through MCP. The skill directs agents to re-read current state rather than rely on old chat context or edit BE project database files directly. A review-only request remains read-only.

## Explore architecture at different levels of detail

The default model view shows all attributes expanded for detailed inspection. Satellite View and user-created canvases initially show compact boxes with entity or processor names, keeping larger diagrams readable. Use the expand control on a box to reveal its attributes when you need more detail.

Collapsing a box changes its presentation; it does not mean the entity or processor has no attributes. You can review the overall structure first, then expand the parts relevant to the current task.

[![Satellite View with compact processors and selectively expanded attributes](assets/screenshots/table-q-satellite-view.png)](https://canvas.beyondentity.com/viewsample?sample_project_file_id=rXxLCaaJ1nEVN9CKbneL)

*Keep the overall canvas compact and expand selected entities or processors to inspect their attributes and mappings. Click the image to open the viewer.*

## Comparing Beyond Entity and Archify

Exploring AI architecture diagram tools such as [Archify](https://github.com/tt-a1i/archify)? Archify generates interactive HTML/SVG diagrams from code or system descriptions, with snapshot comparisons and authored route tracing.

Beyond Entity focuses on persistent **architecture memory for AI coding agents**: editable entities, attributes, processor transformations, ERDs, and data lineage, with checkpoints that preserve design and implementation context across sessions. Humans review the model in the app; agents read and update it through MCP.

When comparing tools, consider whether your next task is to present an interactive system diagram or maintain a shared design that agents consult and update while coding. Explore the [Table Q design and implementation](samples/table-q/README.md) to see the BE workflow. These are independent projects; this repository does not provide an Archify integration or automatic import.

## Get started

- Install Beyond Entity for **macOS or Windows** from the [official download page](https://beyondentity.com/en/download).
- Follow [INSTALL.md](INSTALL.md) to connect the bundled `beyond-entity-mcp` server and the architecture-memory skill to **Claude Code** (via the plugin marketplace) or **Codex**.
- Open a project in Beyond Entity, or explore a sample below.

The desktop app supplies the MCP executable. This repository supplies its plugin configuration and architecture-memory skill; downloading this repository alone does not install the desktop app.

## Example requests

**Design to code**

> Design this feature in Beyond Entity first, including its entities, processors, and transformations. Then implement it using that design as the reference and verify that the behavior matches.

**Code to design**

> Inspect this existing codebase and extract its architecture into Beyond Entity through MCP. Map the data structures, processing responsibilities, and data flows, and identify any design intent that needs confirmation.

**Code with architecture context**

> Use the current Beyond Entity design as your reference while implementing this feature. Read the relevant processor transformations before editing, preserve existing contracts, and synchronize any intentional design changes afterward.

**Continue shared work**

> Use Beyond Entity as architecture memory for this project. Read the latest checkpoint and summarize relevant changes since the previous handoff.

> Before changing this endpoint, find its processor and inspect the transformation design. Compare it with the current implementation.

> Update the implementation and corresponding BE architecture for this change, verify their agreement, and leave a checkpoint for the next developer.

## Samples

| Sample | What to explore | Resources |
| --- | --- | --- |
| **Table Q by Codex** | Restaurant and café queue management, table status, and visibility across stores, with a Codex-generated implementation. | [Project guide](samples/table-q/README.md) · [Codex viewer](https://canvas.beyondentity.com/viewsample?sample_project_file_id=rXxLCaaJ1nEVN9CKbneL) |
| **eCommerce data lake** | Data lineage from Oracle through Google Cloud Storage to BigQuery, with SQL aggregations for sales, product performance, and customer sessions. | [Project guide](samples/ecommerce/README.md) · [Viewer](https://canvas.beyondentity.com/viewsample?sample_project_file_id=BWBDcESJ4tJcGkZqvRwL) |
| **Databricks Lakehouse** | Lakehouse architecture, Python source, jobs, tests, and Codex conversation notes. | [Project guide](samples/databricks/README.md) |
| **Snowflake Enterprise ELT** | ELT architecture, SQL, Python pipelines, DAGs, tests, and Claude Code conversation notes. | [Project guide](samples/snowflake/README.md) |

[Compare Databricks and Snowflake](samples/COMPARISON.md): architecture, implementation structure, corrections, and business questions.

The guides include `.bemdl` download links. Table Q includes the [Codex-generated implementation](samples/table-q/src/) and its companion database schema. See the [Table Q setup notes](samples/table-q/README.md) before running it.

[More samples →](https://beyondentity.com/en/sample-projects)

## Repository layout

```text
.
├── README.md
├── README_ko.md
├── README_ja.md
├── docs/                              # User guides in English, Korean, and Japanese
├── INSTALL.md
├── assets/screenshots/                 # README screenshots
├── .claude-plugin/marketplace.json      # Claude Code plugin marketplace
├── plugins/
│   └── beyond-entity-mcp/
│       ├── .claude-plugin/plugin.json   # Claude Code plugin manifest
│       ├── .codex-plugin/plugin.json    # Codex plugin manifest
│       ├── .mcp.json                    # MCP server (command: beyond-entity-mcp)
│       └── skills/architecture-memory/
│           ├── SKILL.md
│           └── references/modeling-principles.md
└── samples/
    ├── README.md
    ├── table-q/
    │   ├── README.md
    │   ├── src/                         # Codex-generated implementation
    │   └── db/                          # Initial schema and schema verification
    ├── ecommerce/README.md
    ├── databricks/                      # Python package, jobs, tests, architecture notes
    ├── snowflake/                       # SQL, Python pipelines, Airflow DAGs, tests
    └── COMPARISON.md
```

This repository is a self-hosted **Claude Code plugin marketplace** (`.claude-plugin/marketplace.json`) that also ships the equivalent Codex plugin. Publish it by pushing the repository to a public Git host — no central review is required, and users can add it immediately (see [INSTALL.md](INSTALL.md)). Listing in Anthropic's community plugin directory is a separate, optional submission.

## License

The MIT License applies to the plugin configuration, skills, documentation, and sample code in this repository. The Beyond Entity desktop application and separately distributed MCP executable are governed by their own license terms. Third-party components retain their respective licenses.
