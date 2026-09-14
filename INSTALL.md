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

## 6. Verify the connection and workflow

Ask your agent (Claude Code or Codex):

> Use Beyond Entity as architecture memory. Identify my Beyond Entity project, read its latest checkpoint and relevant architecture documents, and summarize the current context without modifying anything.

Check that the agent can access the intended project through MCP and reports actual project context. A missing checkpoint is valid for a new project; a connection failure is not evidence that the project has no history.

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
