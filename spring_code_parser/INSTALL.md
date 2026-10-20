# Installation

be-parser is ready to run: there is nothing to build. The only requirement is **Java 21 or newer** (`JAVA_HOME`, or `java` on the `PATH`).

The analyzer does **not** need the analyzed application's dependencies, a running database, or network access. The Beyond Entity desktop app (with its MCP server `beyond-entity-mcp`) is needed only to write results into a Beyond Entity project. Use desktop MCP 3.2.38 or newer: JMS/SQS queue entities need it, and `send` reads the model, processor and entity definitions the server serves.

## Get it

be-parser lives in the `spring_code_parser/` folder of the Beyond Entity repository. Clone it, or download it as a ZIP and unpack it:

```bash
git clone https://github.com/beyond-entity/beyond-entity.git
cd beyond-entity/spring_code_parser
```

```
bin/be-parser                     launcher (macOS, Linux)
bin/be-parser.cmd                 launcher (Windows)
lib/be-extractor.jar              the program
install.sh                        optional: put be-parser on your PATH
be-extractor.example.properties   every setting, as a settings-file example
```

## Run

```bash
bin/be-parser --version
bin/be-parser serve                                    # web interface: settings, runs and reports
bin/be-parser run /path/to/spring-app --no-send        # analysis and reports only
```

On Windows: `bin\be-parser.cmd serve`. The jar also runs on its own: `java -jar lib/be-extractor.jar <command>`.

If `bin/be-parser` is not executable after a ZIP download, run `chmod +x bin/be-parser install.sh`.

## Put it on your PATH (optional)

```bash
./install.sh               # copies to ~/.local/bin and ~/.local/lib
./install.sh /usr/local    # or another prefix
be-parser --version
```

If `~/.local/bin` is not on your `PATH`, the installer prints the line to add to your shell profile. Alternatively, add this folder's `bin` to your `PATH`. On Windows, add the `bin` folder to `PATH`.

To upgrade, pull (or download) the repository again and run `./install.sh` again if you used it. Your settings in `~/.be-parser/` are kept.

## Check the installation

```bash
be-parser --help                              # usage
be-parser security-catalog list               # bundled standards: CWE, CWE Top 25, OWASP Top 10, MOIS
be-parser run /path/to/spring-app --no-send   # writes ~/.be-parser/out/<repository>/
```

`run --no-send` prints fact counts per type and writes the analysis, security and personal-data reports.

## Memory

`be-parser` starts Java with a 3 GB heap, which covers ThingsBoard (a large multi-module repository). For larger code bases:

```bash
BE_PARSER_HEAP=6g be-parser run /path/to/large-repo --no-send     # or: be-parser config set java.heap 6g
```

## Writing into Beyond Entity

1. Install Beyond Entity desktop. Its MCP server is expected at `/usr/local/bin/beyond-entity-mcp`. If it is elsewhere, set `BE_MCP_COMMAND`, use `--mcp`, or run `be-parser config set mcp.command <path>`.
2. Pick the BE project the parser should write to (`be-parser projects` lists the IDs), or create one: `be-parser projects create ~/models/my-app.bemdl`. In `be-parser serve`, both are on the Run page.
3. Try a dry run first. It connects and reads, but writes nothing:

   ```bash
   be-parser run /path/to/spring-app --project PxxxxxxxxxxxX --dry-run
   ```

4. Run it for real by dropping `--dry-run`, or use `be-parser serve` and press Run.

Settings such as the report language or the MCP server path are kept in `~/.be-parser/config.properties`. Set them with `be-parser config set <key> <value>`, or in `be-parser serve` > Settings. Options of one source folder are remembered with `run --save` or on the Run page. To share settings with a team, put a `be-extractor.properties` (see `be-extractor.example.properties`) in the folder you run from.

If the project is open in the desktop app, it may be locked. The send waits and retries (`mcp.lock.retry_seconds`, `mcp.lock.max_retries`).

## Uninstall

Delete the `spring_code_parser` folder (or the whole clone). If you ran `install.sh`, also delete `~/.local/bin/be-parser` and `~/.local/lib/be-extractor.jar`. Settings and outputs are in `~/.be-parser/`.
