# Security Policy

## Reporting a vulnerability

Please do **not** open a public issue for security problems in be-code-parser itself.

Report them privately through GitHub's **"Report a vulnerability"** button (Security → Advisories) on this repository. Include:

- the affected version or commit (the `extractor_version` recorded in `architecture-facts.json`),
- steps to reproduce, ideally with a minimal input repository,
- the impact you observed.

## Scope

In scope:

- Vulnerabilities in the analyzer when it processes untrusted source trees: XML external entities, path traversal, resource exhaustion and similar.
- Unintended writes by `send`, such as writing to a project listed in `protected.projects`.

Out of scope:

- Security findings the analyzer reports, or fails to report, **in the code it analyzes**. Those are false positives or negatives of the rule catalog. Please open a regular issue with a minimal code sample.

## Handling analysis output

`architecture-facts.json`, `be-plan.json` and the generated reports describe the analyzed application's endpoints, data model, PII columns and security weaknesses. Treat them as confidential as the source code itself, and do not publish them for code you do not own.
