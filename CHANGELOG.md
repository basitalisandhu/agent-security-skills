# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

Nothing yet.

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
