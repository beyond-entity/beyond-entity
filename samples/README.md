# Sample architecture memory projects

These guides introduce Beyond Entity sample files and link to their online viewers and downloads.

- [Table Q by Codex](table-q/README.md): restaurant queue and table management. Includes the [Codex-generated source](table-q/src/) and the required database schema.
- [eCommerce data lake](ecommerce/README.md): an illustrative Oracle → Google Cloud Storage → BigQuery flow with SQL aggregations.

- [Databricks Lakehouse](databricks/README.md): lakehouse architecture, [Python source](databricks/src/), jobs, tests, and Codex conversation notes.
- [Snowflake Enterprise ELT](snowflake/README.md): ELT architecture, [Python pipelines](snowflake/pipelines/), [SQL](snowflake/sql/), DAGs, tests, and Claude Code conversation notes.

[Compare the two examples](COMPARISON.md) through design, implementation decisions, verification, and business questions.

Preview the architecture in a browser, or download a `.bemdl` file and open it in [Beyond Entity](https://beyondentity.com/en/download). To work with an AI agent, follow the [installation guide](../INSTALL.md) and ask it to inspect the selected project through MCP.

## Reading the diagrams

- **Default model view:** all attributes are expanded for detailed inspection.
- **Satellite View and user-created canvases:** entities and processors start as compact boxes showing their names. Use each box's expand control to reveal its attributes.

This keeps the overall canvas readable while letting you inspect selected details. A collapsed box does not indicate an empty entity or processor.

[More samples →](https://beyondentity.com/en/sample-projects)
