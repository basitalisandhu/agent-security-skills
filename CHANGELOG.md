# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

### Changed

- Renamed the umbrella project from Hisar to Masoon; links, names and identifiers updated.

## [0.1.0] - 2026-10-03

### Added

- Plugin marketplace `agent-security-skills` with one plugin, `agent-security`.
- Nine skills: `agent-threat-model`, `agent-config-audit`, `mcp-server-review`, `prompt-injection-review`, `hisar-policy`, `incident-lookup`, `secure-agent-checklist`, `agent-eval-harness`, `semgrep-agentic`.
- `agent-threat-model`: `scan_agent_stack.py` emits the agent-threat-model schema (principals, agents, channels, tools, data stores, catalogue controls) and the draft passes `atm validate`; skill, references and command follow the released CLI (`validate`, `analyse --format markdown|json|sarif|html`, `--fail-on`, `catalogue`, `diff`).
- `incident-lookup`: the bundled dataset is a copy of `site/incidents.json` from ai-agent-incidents (schema-validated by `scripts/build_incidents.py`); `incidents.py` and the MCP server use that record shape (cve lists, sources, summary, OWASP Agentic, OWASP LLM and MITRE ATLAS mappings, affected vendors, products and frameworks, tags, status) with matching filters.
- `semgrep-agentic`: runs the upstream agentic-semgrep-rules pack first; the bundled rules are the offline fallback and carry `metadata.upstream` ids, with a mapping table in the skill.
- Commands `/agent-security:audit`, `/agent-security:threat-model`, `/agent-security:incidents`.
- Agents `agent-security-reviewer` (read-only reviewer) and `hisar-integrator`.
- Two `PreToolUse` hooks on `Bash`, which parse the command (including `sh -c`, `eval`, `$(...)` and backtick substitutions) and never run it: `block-secret-exposure` (blocks commands that print or export likely secrets) and `warn-insecure-fetch` (asks before `curl` or `wget` to a raw IP, a plain-HTTP URL, a certificate-check bypass, or a pipe into a shell).
- Optional stdio MCP server `agent-incidents` with `search_incidents`, `get_incident` and `stats`, reading the bundled incident dataset.
- Bundled snapshot of the AI agent incident dataset (80 entries, 2023-02 to 2026-09) and a builder script to refresh it.
- Repository validator `scripts/validate_plugin.py` and a CI workflow that validates JSON, runs the Python tests, builds and tests the MCP server, and tests the Semgrep rules.
