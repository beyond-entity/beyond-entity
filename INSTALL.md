# Install Beyond Entity for AI architecture memory

This guide covers the Beyond Entity desktop app, its local MCP server, and the architecture-memory skill, for use with **Claude Code** (via the plugin marketplace) or **Codex**. Steps 1–2 are shared; then follow the section for your tool.

## 1. Install the desktop app

Use the [official Beyond Entity download page](https://beyondentity.com/en/download) and select your operating system.

| Platform | Download |
| --- | --- |
| macOS | [Get the current macOS installer](https://beyondentity.com/en/download) |
| Windows | [Get the current Windows installer](https://beyondentity.com/en/download) |

Download the macOS or Windows installer directly from the Beyond Entity website. The download page provides the current release for each platform, so this guide does not pin versioned installer URLs.

Complete the installation, open Beyond Entity, and follow its MCP setup guide. If your installation requires MCP access configuration, complete the setup shown by the app. Open the BE project you intend to work with.

## 2. Check the MCP executable

Beyond Entity provides `beyond-entity-mcp`. It must be discoverable in the environment that launches Claude Code or Codex.

macOS terminal:

```sh
command -v beyond-entity-mcp
```

Windows PowerShell:

```powershell
Get-Command beyond-entity-mcp
```

If no executable is found, consult the desktop app's MCP setup guide and confirm its installation and PATH configuration. Restart the terminal and your coding agent after PATH changes. A command working in a terminal does not always mean an already-running GUI app has received the updated PATH.

## 3. Connect to Claude Code

### Option A — Plugin marketplace (recommended)

This installs the MCP server connection **and** the architecture-memory skill together. In Claude Code:

```text
/plugin marketplace add beyond-entity/beyond-entity
/plugin install beyond-entity-mcp@beyond-entity
```

The marketplace is hosted in [beyond-entity/beyond-entity](https://github.com/beyond-entity/beyond-entity), with `.claude-plugin/marketplace.json` at its root. As an alternative to the command above, use the full Git URL or a local checkout path:

```text
/plugin marketplace add https://github.com/beyond-entity/beyond-entity.git
/plugin marketplace add ./beyond-entity
```

The plugin's MCP server runs `beyond-entity-mcp` (verified in step 2). After installing,
start a new Claude Code session so the plugin's skill and MCP server load.

### Use MCP through the plugin

With `beyond-entity-mcp` installed and enabled, Claude Code loads the MCP connection from the plugin's [`.mcp.json`](plugins/beyond-entity-mcp/.mcp.json) and starts the local executable. The plugin supplies the connection configuration and skill; install the Beyond Entity desktop app first to provide the executable. See [Claude Code's plugin MCP documentation](https://code.claude.com/docs/en/plugins-reference#mcp-servers).

You do not need to run `claude mcp add` or copy the skill separately when using this plugin. Choose either the plugin setup or the manual setup below to avoid duplicate connections.

In Claude Code, use `/mcp` to inspect the connection, then ask in chat:

```text
Use the Beyond Entity MCP tools provided by the beyond-entity-mcp plugin to list
my accessible projects. Report the project names and IDs without modifying anything.
```

Once you identify the project, you can request a specific MCP operation in natural language:

```text
Use Beyond Entity MCP to read the latest checkpoint for project <project name or ID>
and summarize it without making changes.
```

The agent selects and calls the available MCP tools. You do not need to type their internal tool names. For the full architecture-memory workflow, invoke the bundled skill as well:

```text
/beyond-entity-mcp:architecture-memory Use project <project name or ID> as architecture
memory. Read its latest checkpoint and the processor design for this endpoint before
proposing code changes.
```

MCP tools can be used without explicitly invoking the skill. Use the skill for the design review, coding, synchronization, and handoff workflow described in step 6. If the plugin is installed but no MCP tools are available, check that it is enabled, confirm the executable is on PATH, and inspect the connection in `/mcp`.

### Option B — Manual (without the marketplace)

Register the MCP server and skill separately.

```sh
claude mcp add beyond-entity-mcp -- beyond-entity-mcp
claude mcp list
```

Then copy the skill directory:

```text
plugins/beyond-entity-mcp/skills/architecture-memory/
```

into your Claude Code skill directory — `~/.claude/skills/architecture-memory/`
(personal), or `.claude/skills/architecture-memory/` inside a project. Keep
`SKILL.md` and `references/modeling-principles.md` together.

## 4. Connect to Codex

For a local setup without marketplace installation, use the Codex CLI:

```sh
codex mcp add beyond-entity-mcp -- beyond-entity-mcp
codex mcp list
```

If Beyond Entity is already configured under another server name or through an installed plugin, reuse that connection rather than registering a duplicate.

Alternatively, merge this entry into your Codex `config.toml` without replacing unrelated settings:

```toml
[mcp_servers.beyond-entity-mcp]
command = "beyond-entity-mcp"
```

For the default Codex home, the configuration is `~/.codex/config.toml` on macOS and `%USERPROFILE%\.codex\config.toml` on Windows. Respect a custom `CODEX_HOME` if you use one.

The packaged plugin has the equivalent connection in `plugins/beyond-entity-mcp/.mcp.json`. Merely cloning the repository does not activate that plugin. These manual instructions configure the MCP server and skill separately; they do not register a marketplace plugin.

See the [official Codex MCP documentation](https://developers.openai.com/codex/mcp) for client configuration details.

## 5. Add the architecture-memory skill (Codex)

Copy the entire directory:

```text
plugins/beyond-entity-mcp/skills/architecture-memory/
```

into your user skill directory:

| Platform | Destination |
| --- | --- |
| macOS | `~/.agents/skills/architecture-memory/` |
| Windows | `%USERPROFILE%\.agents\skills\architecture-memory\` |

Keep `SKILL.md` and `references/modeling-principles.md` together. If a skill already exists at the destination, review and update that copy rather than creating nested or duplicate copies. For project-specific use, you can instead place it in the code project's `.agents/skills/architecture-memory/` directory.

Start a new Codex task after configuring the connection. If the skill does not appear, restart Codex. For supported discovery locations, see the [official skill documentation](https://developers.openai.com/codex/skills).

## 6. Use the architecture-memory skill

The MCP server gives your agent access to Beyond Entity. The `architecture-memory` skill guides how it uses that access: recover the latest project context, review design before coding, and keep architecture and checkpoints aligned with completed work.

After installing the skill, explicitly invoke it when starting or resuming architecture-related work. Enter the following in your agent's chat, followed by your request:

| Client and installation | Skill invocation |
| --- | --- |
| Codex (manual skill installation above) | `$architecture-memory` |
| Claude Code (marketplace plugin) | `/beyond-entity-mcp:architecture-memory` |
| Claude Code (manual skill installation) | `/architecture-memory` |

These are chat inputs, not terminal commands. See [Codex skill invocation](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md#skills) and [Claude Code skills](https://code.claude.com/docs/en/skills) for client details. The plugin and MCP server are named `beyond-entity-mcp`; the skill is named `architecture-memory`.

For example, in Codex:

```text
$architecture-memory Use Beyond Entity project <project name> as architecture memory
for this code repository. Read the latest checkpoint and relevant design, check for
changes by other agents or people, and summarize the current context without
modifying anything.
```

In Claude Code, replace `$architecture-memory` with the invocation for your installation. Replace `<project name>` with your actual project name; include a project ID if names are ambiguous.

Use the same invocation with requests such as:

- **Design from requirements:** “Create a design in Beyond Entity for these requirements, including entities, processors, and transformations. Summarize it for my review before implementing code.”
- **Implement a reviewed design:** “Before changing this endpoint, read its current processor and transformations in Beyond Entity. Implement the reviewed behavior and verify it.”
- **Bring architecture up to date:** “Compare these code changes with the current Beyond Entity design. Update the affected architecture to reflect the intended behavior, and record what was verified and what remains pending in a checkpoint.”

The agent may also select the skill when a request matches its description. Explicit invocation makes your intent clear. The skill guides work during the task; it does not continuously monitor your repository or synchronize changes in the background.

## 7. Verify the connection and workflow

Invoke the skill as shown above, then ask your agent (Claude Code or Codex):

> Use Beyond Entity as architecture memory. Identify my Beyond Entity project, read its latest checkpoint and relevant architecture documents, and summarize the current context without modifying anything.

Check that the agent can access the intended project through MCP and reports actual project context. A missing checkpoint is valid for a new project; a connection failure is not evidence that the project has no history.

Also ask the agent to confirm which `architecture-memory` skill file it loaded. A successful MCP connection alone does not confirm that the skill is installed or being used. If the skill is unavailable, check its installation directory and start a new session.

Then try a focused design review:

> Find the processor for this endpoint and explain its input/output transformations before proposing code changes.

If connection fails, check PATH, the app's MCP setup requirements, and the MCP status shown by Claude Code or Codex. Avoid placing private access keys in this repository or in shared example configuration.

Continue with the [user guide](docs/USER_GUIDE.md) ([한국어](docs/USER_GUIDE_ko.md) · [日本語](docs/USER_GUIDE_ja.md)) to create a project, review its architecture, implement the design, and keep it aligned with code changes.

## Keeping download links current

For human installation, use the stable [download page](https://beyondentity.com/en/download). No new `/latest` API is required for that link.

For tooling that needs the current macOS artifact URL, the existing public release metadata endpoint is:

```text
https://control.beyondentity.com/api/ota/current?app_name=desktop&platform=macos&release_channel=stable
```

Its JSON response includes `download_url`, `version`, and `build_number`. This endpoint returns metadata, not an HTTP redirect or the installer bytes. A future stable direct-download redirect could use this same release record; a separate latest-version lookup is unnecessary.
