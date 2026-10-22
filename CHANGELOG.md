# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

- Mirror `PERM-007` project MCP auto-approval and `HOOK-002` remote HTTP hooks in the bundled Semgrep configuration rules, with remote/loopback fixture checks in CI.

## [0.5.0] - 2026-10-18

### Added

- `prompt-injection-review`: `tool_inventory.py` recognises MCP tools in Go (`mcp.NewTool("name", mcp.WithString(...))` from mcp-go, `mcp.Tool{Name: ...}` from the official go-sdk), Ruby (`tool_name "name"`, `tool "name"`, `tool :name`, with `required(:x)` and `properties:` parameters) and C# (`[McpServerTool]` and `[McpServerTool(Name = "...")]` methods, leaving out `CancellationToken` and server plumbing), and the summary names the extensions that were read without tool patterns (Rust, Java, Kotlin) so an empty table is explained (closes #4). Python tools now take the name from `@tool("name")` or `name=` (also across lines), decorators with nested calls such as `annotations=ToolAnnotations(...)` are found, and crewAI `BaseTool` subclasses are listed with their `_run` parameters.
- `agent-eval-harness`: `--max-asr RATE` exits 1 when any attack success rate is above the rate, for a CI gate; the table and JSON count `errors`.
- `agent-session-log-review`: a bundled example session (`references/example-session.jsonl`) to run the review on before using a real log; the README shows its output.

### Fixed

- `agent-eval-harness`: the documented `python3 eval/eval_runner.py --agent eval.agent:run` failed with "No module named 'eval'" because Python only put the script folder on the import path; the working directory is now added. An unknown tool name, a tool that raises on bad arguments, or an agent that raises no longer stops the whole run: the case is scored as failed and kept with its error. A bad `--agent` spec or an unwritable `--out` exits 2 with a message instead of a traceback.
- `agent-threat-model`: `scan_agent_stack.py` skipped every file when the checkout sat inside a folder named `build`, `dist`, `target`, `vendor` or `venv`, because skip folders were matched against the absolute path (`tool_inventory.py` had the same bug); one malformed server entry or an invalid `.mcp.json` dropped every server in that file silently, and now it is reported on stderr and the other servers are kept. A missing root or an unwritable `--out` exits 2, and a walk that stops at the file limit says so. The test no longer depends on a machine-specific path for the `atm` binary (from #16).
- `prompt-injection-review`: tool names that start with a read verb (`get_order`) are regular unless they take a recipient, URL or command; `purge`, `kill`, `reset`, `submit` and similar verbs count as consequential; camelCase names are split. A missing path exits 2. No more `DeprecationWarning` from `re.split` on Python 3.13.
- `agent-session-log-review`: a denied `cat .env` followed by a read of `/work/repo/.env` was not linked, because relative file names were not targets; they are now joined to `--root` (or matched by file name without a root).
- `incident-lookup`: `--format` after the subcommand (as SKILL.md writes it: `list ... --format markdown`) was rejected; both positions work now. `--framework MCP` returned nothing because the dataset spells out "Model Context Protocol"; the short name is an alias.
- `semgrep-agentic`, `mcp-server-review` and `/agent-security:audit`: the pinned clone named tag `v1.0.0` of agentic-semgrep-rules, which does not exist (the latest is `v0.2.0`), so the clone failed and the audit command fell back silently. The config-file scan passed paths that may not exist, and one missing path makes Semgrep report nothing for the others while `|| true` hid it; only existing files are passed now.
- Every skill that runs a bundled script says where the script is when the skill folder is copied without the plugin system (from #16).

### Changed

- `agent-threat-model` and `mcp-server-review` descriptions: trigger on "what could go wrong with this agent?" and trust boundaries; not for writing a new MCP server.
- Version 0.5.0 in the marketplace, plugin manifest, MCP server package, `server.json`, server and scanner version constants and README examples.

## [0.4.0] - 2026-10-16

### Added

- `tool-approval-gate-audit`: `approval_gates.py` parses Python agent code with the standard library `ast` module (never imports or runs it) and lists every tool the model can call in the OpenAI Agents SDK (`@function_tool`, `FunctionTool`), LangChain and LangGraph (`@tool`, `StructuredTool.from_function`, `Tool`, `BaseTool` subclasses), crewAI (`@tool`, `BaseTool` subclasses) and FastMCP (`@<server>.tool`), with the side effects found in its body and same-module helpers (processes, file deletes, moves and writes, network writes, mail, boto3-style cloud writes, SQL writes) or its name verb, and the gate in front of it (`needs_approval`, `interrupt()`, `interrupt_before`/`interrupt_after` including the ToolNode holding the tool, human-in-the-loop wrappers, crewAI `Task(human_input=True)`, approval-named calls, `input()`). Flags `NO-GATE` and `GATE-NOT-BOOL` (high), `GATE-RESULT-IGNORED` (high for a discarded `input()` or `interrupt()` answer, medium for other approval calls), `READONLY-HINT-BUT-WRITES` and `POLICY-MISMATCH` (medium), `DESTRUCTIVE-NO-HINT` (low, medium when the hint says `False`), `GATE-CONDITIONAL` and `GATE-ON-READ-ONLY` (info); `--policy` checks gates against a reviewed always, never or conditional decision per tool. Markdown or JSON, `--fail-on high|medium|low`, unparsable files listed as skipped (or exit 2 with `--strict`). Exit codes 0, 1 (findings at or above `--fail-on`) and 2 (bad input or usage). 14 tests over synthetic per-framework fixtures with golden JSON outputs.

### Changed

- Version 0.4.0 in the marketplace, plugin manifest, MCP server package, `server.json`, server and scanner version constants and README examples; the README lists the new skill and the searches it answers.

## [0.3.0] - 2026-10-09

### Added

- Warn when fetched content is executed through process or command substitution,
  while leaving non-executing diff and version-read substitutions alone.

## [0.2.0] - 2026-10-05

### Added

- `agent-session-log-review`: `review_session_log.py` reads one agent session (Claude Code transcript lines, a chat messages export or generic event lines), normalises it into prompts, tool calls, tool results and messages, and flags events with fixed structural rules: a host, URL or address that reached a consequential tool call only through untrusted tool results (`INJ-PROVENANCE`), role markers or hidden characters in untrusted results, a denied action retried with a different tool, destructive command shapes, writes outside `--root`, network calls to hosts not on `--allow-host` (higher when carrying data), secret-shaped strings anywhere in the session, Markdown images that carry a query string to an outside host, repeated calls and error streaks. Prints a flagged timeline as Markdown or JSON, masks secrets always and tokenises e-mail addresses and home folder names with `--redact`. Exit codes 0, 1 (flags to review) and 2 (bad input). 14 tests with synthetic logs and no attack text.

### Changed

- Version 0.2.0 in the marketplace, plugin manifest, MCP server package, `server.json`, server and scanner version constants and README examples; the README lists the new skill and the searches it answers.

## [0.1.2] - 2026-10-05

### Changed

- Rewrote all eight skill descriptions to under 500 characters: each starts with a verb, states the goal before the mechanism, carries one quoted phrase a user would type, a "Use when ..." sentence and a "Not for ..." boundary (the agent-security skills had none).
- Added a `## Limits` section to the seven skills that lacked one, and a Related section to `incident-lookup`.
- `agent-config-audit` names its boundary with `agent-context-writer` in repo-engineering-skills.
- Test scripts open text files with `encoding="utf-8"`, and CI runs the Python tests on `windows-latest` as well as Ubuntu and macOS.
- `audit_agent_config.py`, `scan_agent_stack.py` and `tool_inventory.py` report relative paths with forward slashes on every platform (Windows printed backslashes).
- The README lists three more questions the pack answers (MCP server safe to install, the lethal trifecta, skill supply chain).
- `scripts/validate_plugin.py` now fails when a description is over 600 characters, is not double-quoted, or lacks "Use " or "Not for", and when a SKILL.md has no `## Limits` section; tests cover each rule.
- Version 0.1.2 in the marketplace, plugin manifest, MCP server package, `server.json`, server and scanner version constants and README examples.

## [0.1.1] - 2026-10-04

### Fixed

- Quoted SKILL.md descriptions that contained a colon so the frontmatter parses under strict YAML readers such as the skills CLI; the validator now fails on unquoted scalars with ': ' or ' #'.

## [0.1.0] - 2026-10-04

First tagged release. The incidents MCP server is published to GitHub Packages, using only the workflow's `GITHUB_TOKEN`:

- npm (`https://npm.pkg.github.com`): `@basitalisandhu/agent-incidents-mcp`.
- GitHub Container Registry: `ghcr.io/basitalisandhu/agent-incidents-mcp`, tagged `0.1.0` and `latest`, for linux/amd64 and linux/arm64, with an SPDX SBOM, a build provenance attestation and a keyless cosign signature.

### Changed

- The incidents MCP server package is now `@basitalisandhu/agent-incidents-mcp` (no longer private), with `publishConfig`, `files` and `repository.directory`; `server.json` names the scoped package. The plugin still runs the server from source.
- The server prefers a `data/incidents.json` next to `dist/` (present in the npm package and the image) and falls back to the plugin's snapshot, and it now starts when run through a symlinked bin (`npx`, `npm i -g`).

### Added

- `publish-github-packages.yml`: on a `v*` tag, builds and tests the server, publishes the npm package (skipping a version that already exists), builds, pushes, attests and signs the image, and creates the GitHub release with the SBOM attached. Pull requests that touch packaging run it as a dry run.
- A root `Dockerfile` (digest-pinned `node:22-alpine`, runtime dependencies only, the dataset snapshot, non-root `node` user, stdio) and a CI job that builds it and initializes the server over stdio.
- A test that starts the server through a symlinked bin and checks what `npm pack` ships.

- Plugin marketplace `agent-security-skills` with one plugin, `agent-security`.
- Eight skills: `agent-threat-model`, `agent-config-audit`, `mcp-server-review`, `prompt-injection-review`, `incident-lookup`, `secure-agent-checklist`, `agent-eval-harness`, `semgrep-agentic`.
- `agent-threat-model`: `scan_agent_stack.py` emits the agent-threat-model schema (principals, agents, channels, tools, data stores, catalogue controls) and the draft passes `atm validate`; skill, references and command follow the released CLI (`validate`, `analyse --format markdown|json|sarif|html`, `--fail-on`, `catalogue`, `diff`).
- `incident-lookup`: the bundled dataset is a copy of `site/incidents.json` from ai-agent-incidents (schema-validated by `scripts/build_incidents.py`); `incidents.py` and the MCP server use that record shape (cve lists, sources, summary, OWASP Agentic, OWASP LLM and MITRE ATLAS mappings, affected vendors, products and frameworks, tags, status) with matching filters.
- `semgrep-agentic`: runs the upstream agentic-semgrep-rules pack first; the bundled rules are the offline fallback and carry `metadata.upstream` ids, with a mapping table in the skill.
- Commands `/agent-security:audit`, `/agent-security:threat-model`, `/agent-security:incidents`.
- Agent `agent-security-reviewer` (read-only reviewer).
- Two `PreToolUse` hooks on `Bash`, which parse the command (including `sh -c`, `eval`, `$(...)` and backtick substitutions) and never run it: `block-secret-exposure` (blocks commands that print or export likely secrets) and `warn-insecure-fetch` (asks before `curl` or `wget` to a raw IP, a plain-HTTP URL, a certificate-check bypass, or a pipe into a shell).
- Optional stdio MCP server `agent-incidents` with `search_incidents`, `get_incident` and `stats`, reading the bundled incident dataset.
- Bundled snapshot of the AI agent incident dataset (80 entries, 2023-02 to 2026-09) and a builder script to refresh it.
- Repository validator `scripts/validate_plugin.py` and a CI workflow that validates JSON, runs the Python tests, builds and tests the MCP server, and tests the Semgrep rules.
