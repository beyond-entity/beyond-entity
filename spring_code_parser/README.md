# be-parser

**English** | [한국어](README_ko.md) | [日本語](README_ja.md)

A static analyzer for Java/Spring code bases. It reads source code, without building or running it, and:

1. builds an **architecture model**: modules, processors (controllers, services, repositories, listeners, ...), endpoints, data stores, entities and attributes, plus the **data lineage** between them;
2. runs a **security pre-check** against a bundled rule catalog mapped to CWE, OWASP Top 10 and the Korean MOIS software-weakness guide;
3. optionally **sends both to a Beyond Entity (BE) project** over its local MCP server (see [Beyond Entity integration](#beyond-entity-integration)).

The model is written to these files:

- `architecture-facts.json`: library-neutral facts with source locations.
- `be-plan.json`: the model as BE would store it.
- Markdown reports.

Steps 1 and 2 run fully offline. A Beyond Entity installation is needed only for step 3.

> Status: `0.1.0-SNAPSHOT`, under active development. Output formats may still change.

---

## Contents

- [What it analyzes](#what-it-analyzes)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Output files](#output-files)
- [Beyond Entity integration](#beyond-entity-integration)
- [Settings](#settings)
- [Report language](#report-language)
- [Security rule catalog](#security-rule-catalog)
- [How it works](#how-it-works)
- [Limitations](#limitations)
- [Package contents](#package-contents)

This folder is the ready-to-run package: Java 21 or newer is all you need. See [INSTALL.md](INSTALL.md). License: MIT (see `LICENSE` at the root of this repository).

---

## What it analyzes

| Area | Covered |
|---|---|
| Build layout | Maven and Gradle multi-module projects; each module is analyzed with its own source roots. A reactor of separately deployed Boot services becomes one model per service; a library several services use becomes a model of its own that their calls reach |
| Web | Spring MVC / WebFlux controllers, request mappings, parameters and bodies; Spring Cloud Gateway routes |
| Components | `@Service`, `@Component`, `@Repository`, XML bean definitions (eGovFrame style), constructor/field/setter injection, interface → implementation resolution, profiles and conditional beans |
| Data access | JPA / Spring Data (incl. derived queries, `@Query`, R2DBC), MyBatis mapper XML (incl. dynamic SQL and XML reload), eGovFrame DAOs, Spring Data Redis / MongoDB / Elasticsearch repositories, Spring Session JDBC tables. Datasources from Spring Boot, Druid, Hikari and dynamic-datasource keys (also behind p6spy/log4jdbc); schema scripts, Flyway, Liquibase, or a DDL script anywhere in the repository |
| Messaging | Kafka (incl. Kafka Streams topologies), RabbitMQ (exchanges, queues, bindings, dead-letter routing), Spring Cloud Stream, JMS and Amazon SQS. JMS/SQS queues are entities of the application model that uses them, or of a shared "Message queues" model when several services use one |
| Libraries | Catalog-driven ports for Spring AI, LangChain4j, eGovFrame core, Spring Data |
| Lineage | Argument, result, handoff (a value from one call's result passed to another call), composed and store lineage, field by field into object ports (`creditCard.cardNumber`); messages, logs and session attributes; lookup keys are kept apart from looked-up data |
| Security | 35 rules (injection, crypto, secrets, authorization, CSRF, PII storage/logging, state-changing GET, unauthenticated writes, ...), PII column classification and protection level |

The analyzer works from source roots only. It does not need the target's third-party classpath, so it also works in closed networks where dependencies are not available.

---

## Quick start

```bash
# 1. put the be-parser command on your PATH (Java 21+); or run bin/be-parser from this folder
./install.sh                         # → ~/.local/bin/be-parser

# 2a. the web interface: settings, folder options, runs and reports
be-parser serve

# 2b. or one command: analyze, write the reports, send to a Beyond Entity project
be-parser projects                                   # find the project id
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX
be-parser run ~/src/spring-app --no-send             # analysis and reports only, no Beyond Entity
```

`run` writes everything to `~/.be-parser/out/<repository>/`: `architecture-facts.json`, `be-plan.json`, `analysis-report.md`, `security-report.md` and `pii-flow.md`. Options you set once (in the web page, with `be-parser config`, or with `run --save`) are reused, so later runs need only the folder: `be-parser run ~/src/spring-app`.

Example: [spring-petclinic](https://github.com/spring-projects/spring-petclinic) produces 16 security findings and its 7 tables in each of its 3 database profiles (MySQL, PostgreSQL, H2) in a few seconds.

---

## Commands

All commands are subcommands of `be-parser` (`bin/be-parser`, or `bin\be-parser.cmd` on Windows), which runs `lib/be-extractor.jar`. `java -jar lib/be-extractor.jar <command>` works the same.

### `run`: analyze + reports + send in one step

```
run <repo-root> [--project <id> | --no-send] [--lang en|ko|ja] [--exclude <glob>]... [--dry-run] [--save]
    [--out <dir>] [--config <file>] [--include-general-modules] [--allow-mass-resolve]
```

Options left out come from the [settings](#settings): the folder's remembered options, the config file and your defaults. A folder set up once runs with just `be-parser run <folder>`. `--save` remembers the options given on this command line for the folder. Without a target project the run stops after the local reports. Output goes to `output.dir/<repository>/` (default `~/.be-parser/out/<repository>/`).

### `config`: settings from the command line

```
config [list] [--source <repo>] [--json]          every setting, its value for a run and where it comes from
config set <key> <value> [--source <repo>]       user default, or with --source an option of that folder
config unset <key> [--source <repo>]
config path                                      the settings files
```

### `projects`

```
projects [--json]                                              the Beyond Entity projects: id, name, file
projects create <file.bemdl> [--name <name>] [--lang en|ko|ja]  a new local project file; prints its id
```

### `serve`: local web interface

```
serve [--port 8765] [--no-open] [--config <file>]
```

Opens a page with two tabs:

- **Run**: pick a source folder (folder browser, recent folders). Its options are shown and editable. The target project is picked from your Beyond Entity projects, or "+ New project…" creates one from a name and a `.bemdl` file name (by default `<folder>/<folder>.bemdl`). The other options are report language, excluded paths, general modules, repository key and findings branch. Empty fields show the default they inherit. "Remember these options for this folder" saves them (the same as `run --save`). Then choose analyze-only, dry run or allow mass resolve, and press Run. The log is shown live, followed by the analysis, security and personal-data reports.
- **Settings**: every setting, grouped, with its description and default, saved as your defaults. "Test Beyond Entity connection" checks the MCP server. A value that the config file overrides is marked.

The page edits the same files as `be-parser config`, and a run is `be-parser run` with those settings. The server listens on `127.0.0.1` only. Every API call needs a random token created at start, which is part of the URL it prints and opens. Requests with another Host header are refused. One run happens at a time. The port and token are written to `~/.be-parser/serve.json`, so another local tool (for example the Beyond Entity desktop app) can open the page for a project: `http://127.0.0.1:<port>/?token=<token>&project=<project id>`.

### `analyze`: source → facts

```
analyze <repo-root> [-o architecture-facts.json] [--commit <sha>] [--exclude <glob>]...
        [--report <base>] [--schema model_creation_schema.json] [--no-report] [--catalog <dir>] [--lang en|ko|ja]
```

| Option | Meaning |
|---|---|
| `-o` | Output facts file (default `architecture-facts.json`) |
| `--commit` | Source commit to record; by default read from the repository's git metadata, together with branch and dirty state |
| `--exclude` | Glob of paths to skip (repeatable), e.g. `--exclude '**/generated/**'` |
| `--report` | Base name of the analysis report (`<base>.md`, `<base>.json`); default `analysis-report` next to the facts |
| `--no-report` | Skip the analysis report |
| `--schema` | BE storage-type catalog used to validate data types in the report |
| `--catalog` | External security catalog directory (default: the bundled one) |
| `--lang` | Report language: `en` (default), `ko` or `ja` (see [Report language](#report-language)) |

### `plan`: facts → BE model (offline)

```
plan <architecture-facts.json> [-o be-plan.json] [--include-general-modules]
```

Maps facts to models, processors, entities and lineage the way `send` would write them, without connecting to BE. `--include-general-modules` also keeps modules with no Spring role (plain libraries).

### `report`, `security-report`, `pii-report`

```
report           <architecture-facts.json> [-o <base>] [--schema model_creation_schema.json] [--catalog <dir>] [--lang en|ko|ja]
security-report  <architecture-facts.json> [-o security-report.md] [--catalog <dir>] [--lang en|ko|ja]
pii-report       <architecture-facts.json> [-o pii-flow.md] [--lang en|ko|ja]
```

- `report` regenerates the analysis report from existing facts.
- `security-report` lists findings with rule, CWE and standard mappings, location and evidence.
- `pii-report` lists PII columns, their protection (hashing, encryption), and the endpoints that collect and expose them.

### `validate`

```
validate <architecture-facts.json> <model_creation_schema.json>
```

Checks that every data type the plan would write is allowed by the BE storage-type catalog.

### `security-catalog`

```
security-catalog list|validate [--catalog <dir>] [--lang en|ko|ja]
security-catalog import-csv <items.csv> --id <standard-id> --version <v> --title <title>
        [--published <date>] [--source <url>] --catalog <dir> [--activate]
```

Lists or validates the rule catalog, or imports a new standard version (for example a newer CWE list) into an external catalog directory.

### `send`: facts → Beyond Entity

```
send <architecture-facts.json> [--config be-extractor.properties] [--dry-run] [--include-general-modules]
     [--allow-mass-resolve]
```

`--dry-run` connects to BE and reads, but writes nothing. Writes the model, lineage and security findings to the BE project named in the config. See [Beyond Entity integration](#beyond-entity-integration).

---

## Output files

| File | Written by | Content |
|---|---|---|
| `architecture-facts.json` | `analyze` | Facts (`MODULE`, `PROCESSOR`, `ENDPOINT`, `CALL`, `DATA_ENTITY`, `DATA_ATTRIBUTE`, `STORE_ACCESS`, `SECURITY_FINDING`, `UNRESOLVED`, ...) with source file, line and evidence; source repository, branch, commit and extractor version |
| `analysis-report.md` / `.json` | `analyze`, `report` | Counts per fact type, data stores, unresolved items, validation results |
| `be-plan.json` | `plan` | Models → processors (inputs/outputs, endpoints, call dependencies) → entities/attributes, and lineage as SQL-like transformations |
| `security-report.md` | `security-report` | Findings by severity with CWE / OWASP / MOIS mappings |
| `pii-flow.md` | `pii-report` | PII columns, protection level, collecting and exposing endpoints |
| `be-sync-report.json` | `send` | Created/updated/deleted objects, failures, security scan outcome (`be-sync-dry-run.json` with `--dry-run`) |

Lineage is expressed as SQL over BE objects, for example:

```sql
-- parser: EgovSysHistoryServiceImpl.selectSysHistory → EgovFileMngServiceImpl.deleteAllFileInf (handoff)
INSERT INTO {{EgovFileMngServiceImpl}} (atchFileId) SELECT p.OUTPUT.atchFileId FROM {{EgovSysHistoryServiceImpl}} p
```

---

## Beyond Entity integration

Beyond Entity is a data/architecture modeling tool. `send` talks to its **local desktop MCP server** over stdio. The MCP server opens the target project itself, so no credentials are stored in this repository. JMS/SQS queue entities need desktop MCP 3.2.38 or newer; `send` checks the plan against the definitions the server serves.

What `send` does, in order:

1. reads the MCP usage guides and checks the plan against the live BE definitions (schema check);
2. starts a code-analysis run (project run + node runs);
3. creates, updates or deletes models, processors, entities, attributes and transformations, so that only differences are written;
4. records the security scan atomically with its analysis run, grouped by evidence basis (source facts, call reach, plan-derived); a rule with more than 200 findings is recorded as complete scans over exact source files;
5. finishes the run and adds a checkpoint carrying the source commit and extractor version.

Safety rails:

- **`protected.projects`** (development setting): project IDs the sender refuses to write to, even if `target.project` is set to one of them by mistake. It is meant for batch runs over many projects; a single run with a target you pick does not need it.
- **Project lock retry**: when the project is locked (the desktop app or a reviewer is working in it), `send` waits `mcp.lock.retry_seconds` and retries.
- **Mass-resolve guard**: if a send would resolve an unusually large share of open findings, it stops unless `--allow-mass-resolve` is given.
- Any failed write, or a security scan that could not be recorded, makes `send` exit non-zero.

No configuration file is needed: pick the target in `be-parser serve`, or pass `--project` to `run`. To keep settings in a repository, a `be-extractor.properties` there can hold any [setting](#settings), for example:

```properties
target.project=PxxxxxxxxxxxX
report.language=ko
analysis.exclude=**/generated/**
```

See [`be-extractor.example.properties`](be-extractor.example.properties) for all options.

```bash
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX --dry-run
be-parser run ~/src/spring-app --project PxxxxxxxxxxxX
be-parser send out/architecture-facts.json --config be-extractor.properties   # existing facts, settings from a file
```

---

## Settings

Every option of a run is a setting. Each value is taken from the following layers, where later layers win:

1. built-in defaults;
2. **your defaults**: `~/.be-parser/config.properties`, edited with `be-parser config set` or the Settings tab;
3. a **config file**: `--config <file>`, else `be-extractor.properties` in the working directory (optional; useful to share settings in a repository);
4. the **folder's options**: `~/.be-parser/sources.json`, remembered per analyzed folder (`run --save`, `config set --source`, or the Run tab);
5. **command-line options**.

Relative paths resolve against the folder of the file they come from, and `~` is your home folder. `be-parser config` shows each value and its layer. Set `BE_PARSER_HOME` to keep the settings somewhere other than `~/.be-parser`.

| Key | Default | Meaning |
|---|---|---|
| `target.project` * | – | Beyond Entity project the analysis is written into; empty: analyze only |
| `report.language` * | `en` | Language of the reports and of the finding texts written to BE: `en`, `ko` or `ja` |
| `analysis.exclude` * | – | Glob patterns of files and folders to skip (comma-separated; one per line in the web page) |
| `extract.include_general_modules` * | `false` | Also model modules with no Spring role (plain libraries) |
| `analysis.repository_key` * | folder name | Key that identifies the source repository across runs |
| `security.findings.branch` * | – | Branch recorded with the security findings |
| `output.dir` | `~/.be-parser/out` | Where `run` writes facts, plan and reports, in a sub-folder per repository |
| `java.heap` | `3g` | Maximum heap of the analysis (`BE_PARSER_HEAP` overrides it) |
| `security.catalog.dir` | bundled | External security catalog directory |
| `security.report.enabled` / `security.report.file` | `true` / `security-check-<repo>.md` | Upload the security report as a BE document |
| `pii.report.enabled` / `pii.report.file` | `true` / `pii-flow-<repo>.md` | Upload the PII flow report as a BE document |
| `checkpoint.actor` | `be-code-parser` | Actor name on checkpoints and analysis runs |
| `implementation.status.enabled` | `true` | Also write implementation status for created objects |
| `be.schema` | – | BE storage-type catalog (`model_creation_schema.json`) to check the plan against before writing |
| `security.findings.enabled` | `true` | Send security findings |
| `security.findings.refresh` | `true` | A finding detected again takes this run's location, snippet and message (statuses set by people are kept) |
| `security.findings.mass_resolve.min` / `.ratio` | `10` / `0.3` | Thresholds of the mass-resolve guard |
| `mcp.command` | `/usr/local/bin/beyond-entity-mcp` | Beyond Entity MCP server executable (`BE_MCP_COMMAND` overrides the default) |
| `mcp.timeout.seconds` | `120` | Timeout per MCP call |
| `mcp.batch_mode` | `true` | Keep the project database open across calls during a send |
| `mcp.lock.retry_seconds` / `mcp.lock.max_retries` | `30` / `20` | Wait and retry while the project is locked |
| `protected.projects` (development) | – | For batch runs over many projects while developing the parser: project IDs that must never be written, even if one is configured as the target by mistake. Not shown in the web page; not needed when you pick the target yourself |

\* also a per-folder option.

---

## Report language

The security report, the PII flow report, and the finding titles, descriptions and remediation written to BE can be produced in **English (default), Korean or Japanese**.

| Where | How |
|---|---|
| `send` | `report.language=ko` in the config file |
| `security-report`, `pii-report`, `report`, `analyze`, `security-catalog list` | `--lang ko` |
| Any command | `BE_REPORT_LANGUAGE=ko` environment variable (a default that `--lang` overrides) |

Accepted values: `en`, `ko`, `ja` (also `english`, `korean`/`kr`, `japanese`/`jp`).

What changes with the language:

- report headings, tables and explanations;
- rule titles, descriptions and remediation;
- standard titles, item names and categories (the MOIS guide in English or Japanese; OWASP and CWE keep their official English names).

Finding messages that quote code (class, method, path, SQL) and the developer-facing analysis report (`analysis-report.md`) stay in English. On an existing BE project, the next `send` rewrites the report documents in the new language, and new findings get titles in that language. Whether BE also rewrites the titles of findings it already has depends on its refresh behaviour (`security.findings.refresh`). Statuses and decisions made by people are kept either way.

---

## Security rule catalog

The catalog is bundled in `lib/be-extractor.jar` (`security-catalog/`):

- `rules.json`: 35 rules, each with detection kind, severity and confidence, CWE, and mappings to standards. Texts are in English with Korean and Japanese translations under `i18n`.
- `attribute-security.json`: PII data types and encryption levels.
- `standards/`: bundled standard versions, namely CWE 4.20, CWE Top 25 (2024, 2025), OWASP Top 10 (2021, 2025) and the MOIS software-weakness guide (2021, 49 items).

Standards are resolved when a report is produced, so a catalog update applies without re-analysis. To use a newer standard without rebuilding, point `--catalog` (or `security.catalog.dir`) to a directory created with `security-catalog import-csv`.

Findings are a **pre-check**, not a verdict. Each one carries its evidence and confidence, and rules that depend on call reach report when a path could not be followed instead of guessing.

---

## How it works

```
source tree ──► extractor-spring ──► architecture-facts.json ──► extractor-be ──► be-plan.json ──► send (MCP) ──► Beyond Entity
                (JavaParser AST,       (library-neutral facts,       (BeMapper, PortMapper,
                 XML, YAML, catalogs)   evidence, unresolved)          LineageComposer, SecuritySync)
```

- **Extraction**: module discovery, Java/XML/YAML analysis on JavaParser ASTs, type resolution without a classpath, call graph, guard analysis, security scanner.
- **Mapping**: facts to BE objects, ports and lineage, multi-hop lineage, differences synced over MCP.
- **Command line**: reports, analysis runs, send, settings and the local web interface.

Design notes:

- Anything the analyzer cannot resolve becomes an `UNRESOLVED` fact with a reason. It is not dropped silently.
- Call relationships that carry no caller data are kept as processor `call_dependencies` with a reason (`handoff`, `no_mapping`, `no_caller_value`), separate from data lineage.
- A value used only as a lookup key (`findById(id)`) is not lineage into the looked-up object. The looked-up object's properties become a **handoff** from the lookup's result.


---

## Limitations

- Reflection, dynamic bean registration and runtime-generated proxies are not followed.
- Types come from source only. Library types without a catalog entry are treated as opaque.
- Lineage goes one level into an object port (`creditCard.cardNumber`); a value read deeper (`request.getA().getB().getC()`) maps to the nearest port. A nested field named like a port of the same side is not nested (it would be ambiguous in BE).
- RabbitMQ topology is read from `@Bean` Exchange/Queue/Binding definitions; topology declared elsewhere (properties, the management UI) is not.
- Kotlin, Groovy and non-Spring frameworks are not analyzed.

---

## Package contents

```
bin/be-parser                     launcher (macOS, Linux)
bin/be-parser.cmd                 launcher (Windows)
lib/be-extractor.jar              the program
install.sh                        optional: put be-parser on your PATH (~/.local by default)
be-extractor.example.properties   every setting, as a settings-file example
README.md, README_ko.md, README_ja.md, INSTALL.md, SECURITY.md
```

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
