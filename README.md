# agent-security-skills

**Claude Code security plugin and agent skills for securing LLM agents: threat modelling, configuration audits, prompt injection review, tool approval gate audits, MCP server review, incident lookup and agent session log review.**

agent-security-skills is a Claude Code plugin marketplace and an [agentskills.io](https://agentskills.io)-compatible skill pack for people who build or run LLM agents against real APIs, MCP servers and codebases: security engineers reviewing an agent before it ships, and developers who want that review inside the tool they already use. Each skill is a procedure with a tested script or a fixed checklist, so two reviewers reach the same verdict and the evidence is a file, a line or a command output.

## Quick start

```bash
claude plugin marketplace add basitalisandhu/agent-security-skills
claude plugin install agent-security@agent-security-skills
# then, in Claude Code: "what did the agent actually do in this session?" or /agent-security:audit
```

Real output of `agent-session-log-review` on the session log bundled with the skill (`references/example-session.jsonl`, a run where a fetched issue page steered the agent), with `--root /work/widgets --allow-host github.com --flagged-only`:

```text
**Summary:** 14 events (6 tool calls), 4 flags: 1 critical, 3 high.

| # | Event | Severity | Flag              | Tool | Evidence                                              |
|---|-------|----------|-------------------|------|-------------------------------------------------------|
| 1 | 6     | high     | TOOL-DENIED-RETRY | Read | Bash was denied; Read then targeted /work/widgets/.env |
| 2 | 7     | high     | EGRESS-SECRET     | Read | in a tool result: AWS_ACCESS_KEY_ID=[masked secret]    |
| 3 | 8     | critical | INJ-PROVENANCE    | Bash | collector.example.net (from event 3)                  |
| 4 | 8     | high     | EGRESS-NETWORK    | Bash | collector.example.net                                 |
```

The script exits 1 because a flag reached `--fail-on high`, so the same command can gate an unattended agent pipeline. Time and finding columns are left out here; the full report also has a timeline of every event.

Ten skills (each with a tested script or a checklist), three slash commands, a subagent, two guard hooks for `Bash`, and an optional MCP server over the [ai-agent-incidents](https://github.com/basitalisandhu/ai-agent-incidents) dataset (80 documented events mapped to OWASP Agentic, OWASP LLM and MITRE ATLAS). No telemetry, no network calls except the documented, opt-in dataset refresh.

Typical questions it answers: "is this MCP server safe to install?", "does this agent have the lethal trifecta?", "could a malicious skill or plugin in this repository take over my agent?" and "which of my agent's tools run without approval?" and "what did the agent actually do in this session?".

Find this when you search for: human-in-the-loop approval for agent tools, needs_approval audit, LangGraph interrupt check, AI agent session log review, Claude Code transcript audit, agent observability for actions outside policy, detecting prompt injection in agent logs, agent data exfiltration check.

## When to use this

- How do I review an MCP server for security from inside Claude Code? `mcp-server-review`
- How do I threat-model an AI agent with a coding assistant? `/agent-security:threat-model`
- Is this agent vulnerable to prompt injection, and where do approvals and provenance checks belong? `prompt-injection-review`
- Which Claude Code hooks block dangerous tool calls, such as printing secrets or piping `curl` into a shell? The two bundled `PreToolUse` hooks
- Is the `.claude/` or `.mcp.json` in a repository I just cloned safe to open with an agent? `agent-config-audit`
- Is this MCP server safe to install? `mcp-server-review` on its source, then `agent-config-audit` on the config that launches it
- Does this agent have the lethal trifecta (private data, untrusted content and a way to send data out)? `prompt-injection-review`
- Skill supply chain: does a skill, plugin or hook I am about to install carry a malicious instruction, a secret or an unpinned server? `agent-config-audit`
- Which tools can my agent call without a person approving first, and can the approval fail open? `tool-approval-gate-audit`
- What did the agent actually do in a session: did a fetched page steer a tool call, was a denied action retried another way, did data or a secret leave, did it loop? `agent-session-log-review`

## Install

In a Claude Code session:

```text
/plugin marketplace add basitalisandhu/agent-security-skills
/plugin install agent-security@agent-security-skills
```

From a shell (for scripts and CI machines):

```bash
claude plugin marketplace add basitalisandhu/agent-security-skills
claude plugin install agent-security@agent-security-skills --scope user
```

To try it without installing, clone the repository and start Claude Code with `claude --plugin-dir ./plugins/agent-security`.

Requirements: Python 3.11 or newer on `PATH` as `python3` (hooks and skill scripts, standard library only). Optional: [Semgrep](https://semgrep.dev/docs/getting-started/) for `semgrep-agentic`; `uvx` or `pipx` for `agent-threat-model` (while its PyPI publication is pending, install from git: `pipx install git+https://github.com/basitalisandhu/agent-threat-model`); Node 20 or newer to build the incidents MCP server.

After installing, skills appear as `/agent-security:<skill>`, commands as `/agent-security:audit`, `/agent-security:threat-model` and `/agent-security:incidents`, and the agent as `@agent-agent-security:agent-security-reviewer`.

This pack is also part of [claude-skills](https://github.com/basitalisandhu/claude-skills), which holds every skill I maintain as one marketplace: `/plugin marketplace add basitalisandhu/claude-skills`.

## What is inside

```text
plugins/agent-security/
├── .claude-plugin/plugin.json      plugin manifest
├── skills/<name>/SKILL.md          ten skills, each with references/ or scripts/ (and tests)
├── commands/                       audit.md, threat-model.md, incidents.md
├── agents/                         agent-security-reviewer.md
├── hooks/hooks.json                two PreToolUse hooks on Bash, scripts in hooks/scripts/
├── .mcp.json                       declares the agent-incidents stdio server
├── mcp/incidents-server/           TypeScript MCP server (@modelcontextprotocol/sdk, zod)
└── data/incidents.json             bundled copy of site/incidents.json from ai-agent-incidents
```

## Skills

| Skill | Triggers on | What it produces |
|---|---|---|
| `agent-threat-model` | "threat model this agent", attack surface, architecture review | Draft system description in the agent-threat-model schema (`scan_agent_stack.py`, passes `atm validate`), `atm analyse` run with residual risk score, summarised threats with precedents |
| `agent-config-audit` | review or harden `.claude/`, `CLAUDE.md`, `.cursor/`, `.mcp.json`, `claude_desktop_config.json`, hooks, skills, plugins | JSON or Markdown findings with severity from `audit_agent_config.py`: permissions, hooks, MCP pinning and secrets, injection patterns in instruction files |
| `mcp-server-review` | review, harden or publish an MCP server; enable a third-party one | Checklist verdicts (auth, transport binding, input validation, description poisoning, SSRF, limits, logging) plus a Semgrep pass |
| `prompt-injection-review` | "is this agent injectable", review tool-calling code, where to put approvals | Tool inventory (`tool_inventory.py`), traced flows judged with the provenance and approval rules, findings table |
| `incident-lookup` | "has this happened before", examples, citations for a review | Filtered incidents (vector, authority, vendor, framework, OWASP Agentic, OWASP LLM, ATLAS, tags), stats, ranked precedents with the controls that would have helped (`incidents.py`, offline fallback) |
| `secure-agent-checklist` | "is this safe to ship", release gate, go/no-go | Markdown report with pass, fail or n.a. across identity, least privilege, approvals, sandboxing, audit, kill switch, supply chain, evals |
| `agent-eval-harness` | measure prompt-injection resistance, build a security eval, ASR numbers | AgentDojo-style runner template (`eval_runner.py`) with policies, demo suite, tests, and the path to the real benchmark |
| `agent-session-log-review` | "what did the agent actually do in this session?", after a suspicious run, spot checks of unattended agents | Timeline of one session (Claude Code transcript, chat messages or event lines) with structural flags for injection taking effect, denied-then-retried actions, destructive commands, writes outside the root, egress, secrets and loops (`review_session_log.py`, Markdown or JSON, secrets masked) |
| `tool-approval-gate-audit` | "which of my agent's tools run without approval?", `needs_approval`, LangGraph `interrupt`, crewAI `human_input`, MCP tool hints | Every tool in OpenAI Agents SDK, LangChain/LangGraph, crewAI and FastMCP Python code with its side effects and gate, and per-tool findings at file:line: ungated consequential tools, `needs_approval` values that are not bools, approvals whose answer is ignored, MCP hints that contradict the code, gates that differ from a policy file (`approval_gates.py`, Markdown or JSON) |
| `semgrep-agentic` | scan agent code, add rules to CI, the code step of an audit | Runs the 36-rule [agentic-semgrep-rules](https://github.com/basitalisandhu/agentic-semgrep-rules) pack, 16 bundled rules as the offline fallback (with the upstream id mapping), config rules, triage guide, CI snippet |

## Tool approval gate audit: sample run

`tool-approval-gate-audit` parses Python agent code (never runs it) and checks every tool the model can call for a deterministic human approval gate. On the bundled synthetic LangGraph fixture:

```bash
python3 plugins/agent-security/skills/tool-approval-gate-audit/scripts/approval_gates.py plugins/agent-security/skills/tool-approval-gate-audit/scripts/fixtures/langgraph
```

Output (exit code 1, the Fix column trimmed):

```text
# Tool approval gate audit: `plugins/agent-security/skills/tool-approval-gate-audit/scripts/fixtures/langgraph`

Files scanned: 1. Tools: 6 (5 consequential). Findings: 2 high, 1 medium.

## Tools

| Tool | Framework | Location | Side effects | Gate |
|---|---|---|---|---|
| `search_docs` | langchain | `graph.py:13` | read-only | none |
| `write_report` | langchain | `graph.py:19` | file-write: `Path(path).write_text(text, encoding='utf-8')` L21 | `interrupt_before=['actions']` L63 |
| `remove_workspace` | langchain | `graph.py:26` | file-delete: `shutil.rmtree(path)` L31 | `interrupt({'action': 'remove_workspace', 'path': path})` L28 |
| `deploy_service` | langchain | `graph.py:36` | name verb: deploy | none |
| `move_files` | langchain | `graph.py:50` | file-move: `shutil.move(src, dst) via _really_move()` L42 | none |
| `post_update` | langchain | `graph.py:58` | network-write: `requests.post('https://status.example.org/updates', json={'text': text})` L55 | `confirm_with_human(text)` (answer ignored) L54 |

## Findings

| # | Severity | Id | Tool | Location | Finding |
|---|---|---|---|---|---|
| 1 | high | NO-GATE | `deploy_service` | `graph.py:36` | consequential (name verb 'deploy') and no approval gate |
| 2 | high | NO-GATE | `move_files` | `graph.py:50` | consequential (shutil.move(src, dst) via _really_move()) and no approval gate |
| 3 | medium | GATE-RESULT-IGNORED | `post_update` | `graph.py:58` | confirm_with_human(text) at line 54 discards its result: confirm it raises when the human refuses |

Findings are leads from static rules. Read each gate in the code before signing off.
```

Add `--policy policy.json` to record which tools must always, never or conditionally ask, and `--fail-on medium` to gate CI on more than the high findings.

## Commands

| Command | Does |
|---|---|
| `/agent-security:audit [path]` | Config audit, Semgrep scan, tool inventory and checklist; writes `AGENT-SECURITY-REPORT.md` |
| `/agent-security:threat-model [path]` | Drafts `system.yaml`, runs `atm analyse` when available, writes `threat-model.md` |
| `/agent-security:incidents <query>` | Answers from the incident dataset: list, show, stats or precedents |

## Agents

| Agent | Tools | Purpose |
|---|---|---|
| `agent-security-reviewer` | Read, Grep, Glob, Bash (read-only use; Write, Edit and web tools disallowed) | Independent review with evidence; never changes files |

## Hooks

Both hooks are `PreToolUse` on `Bash`, written in Python with the standard library, and tested by piping real hook payloads through them.

| Hook | Behaviour |
|---|---|
| `block-secret-exposure` | Exits 2 (blocks, reason shown to the model) for commands that print or export likely secrets: `env`, `printenv`, bare `export` or `set`, `echo $OPENAI_API_KEY`, `cat .env`, `less ~/.aws/credentials`, `base64 ~/.ssh/id_ed25519`, `scp .env host:`, `gh auth token`, `gcloud auth print-access-token`, `kubectl get secret -o yaml`, `print(os.environ)`, and the same inside `sh -c`, `eval`, `sudo`, `$(...)` or backticks (quoted or not). Allows `env FOO=bar cmd`, `printenv HOME`, `[ -n "$TOKEN" ]`, `echo ${TOKEN:+set}`, `cat .env.example`, `source .env`, and using a secret in a header. |
| `warn-insecure-fetch` | Returns `permissionDecision: "ask"` with the reason when `curl` or `wget` targets a plain-HTTP URL, a raw IP (the cloud metadata address is named), a bare host with no scheme, disables certificate checks, or pipes the download into a shell or interpreter. Loopback targets are exempt unless `AGENT_SECURITY_WARN_LOOPBACK=1`. |

A hook that cannot read its input exits 1 (non-blocking) so a broken hook never silently blocks or silently passes. Disable both by disabling the plugin; there is no environment-variable bypass. Literal interpreter reads such as `python3 -I -c "print(open('.env').read())"` are checked without executing the source, and rejection names the path rather than printing its contents. Computed paths, aliases and obfuscated code remain out of scope; see [docs/good-first-issues.md](docs/good-first-issues.md).

## MCP server: agent-incidents

Optional, stdio only, read-only. Build it once after installing:

```bash
cd <plugin directory>/mcp/incidents-server    # `claude plugin details agent-security` prints the directory
npm install && npm run build && npm test
```

Then `/mcp` lists `plugin:agent-security:agent-incidents` with the tools `search_incidents`, `get_incident` and `stats` (`mcp__plugin_agent-security_agent-incidents__<tool>` in permission rules). It reads `data/incidents.json`, a copy of the published `site/incidents.json`; point `AGENT_INCIDENTS_DATA` at a freshly downloaded copy to use newer records.

### Install the server on its own (GitHub Packages)

The same server is published on every release tag, for use outside the plugin, by `publish-github-packages.yml`. Both carry the bundled dataset snapshot; `AGENT_INCIDENTS_DATA` still overrides it.

| Registry | Package | Run |
|---|---|---|
| npm (GitHub Packages) | `@basitalisandhu/agent-incidents-mcp` | `npx -y @basitalisandhu/agent-incidents-mcp@0.5.0` |
| Container (GHCR) | `ghcr.io/basitalisandhu/agent-incidents-mcp` | `docker run --rm -i ghcr.io/basitalisandhu/agent-incidents-mcp:0.5.0` |

GitHub's npm registry asks for a token even for public packages. Point the scope at it in `~/.npmrc`, with a personal access token (classic) that has the `read:packages` scope exported as `GITHUB_TOKEN`:

```
@basitalisandhu:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

Then add it to Claude Code with either:

```bash
claude mcp add agent-incidents -- npx -y @basitalisandhu/agent-incidents-mcp@0.5.0
claude mcp add agent-incidents -- docker run --rm -i ghcr.io/basitalisandhu/agent-incidents-mcp:0.5.0
```

The image (linux/amd64 and linux/arm64) runs as the non-root `node` user on stdio and opens no port. To serve a newer dataset, mount it: `docker run --rm -i -v "$PWD/incidents.json:/data/incidents.json:ro" -e AGENT_INCIDENTS_DATA=/data/incidents.json ghcr.io/basitalisandhu/agent-incidents-mcp:0.5.0`. Each image is signed with cosign (keyless) and has a build provenance attestation and an SPDX SBOM (attached to the GitHub Release). To verify:

```bash
cosign verify ghcr.io/basitalisandhu/agent-incidents-mcp:0.5.0 \
  --certificate-identity-regexp '^https://github.com/basitalisandhu/agent-security-skills/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
gh attestation verify oci://ghcr.io/basitalisandhu/agent-incidents-mcp:0.5.0 --owner basitalisandhu
```

## Compatibility with agentskills.io

Every `SKILL.md` follows the Agent Skills specification: frontmatter with `name` (equal to the directory name, lowercase with hyphens, at most 64 characters) and `description` (at most 1024 characters), optional `license`, `compatibility` and `metadata`, supporting files in `references/` and `scripts/`, and a body under 500 lines with progressive disclosure. The skills directory can be used by any agent that reads that format; only the commands, agents, hooks and `.mcp.json` are Claude Code specific. Skill bodies reference `${CLAUDE_PLUGIN_ROOT}` for script paths; other hosts should substitute the skill's own directory.

## Security of the plugin itself

What each component can touch, so you can decide before you install:

- **Skills** are instructions plus Python scripts. The scripts read files under the directory you point them at, with caps (2 MB per file for the config audit, 1 MB per file and 4000 or 5000 files for the threat-model scanner, the tool inventory and the approval gate audit), and write only where you pass `--out` or `--output`. The one exception is `incidents.py`, the only script that can make a network request: a GET to the published dataset JSON (10 s timeout, 20 MB cap, URL overridable with `AGENT_SECURITY_INCIDENTS_URL`), cached for 24 hours in `$XDG_CACHE_HOME/agent-security-skills/incidents.json` (default `~/.cache/agent-security-skills/`), skipped with `--offline`, and never required: any failure falls back to the bundled snapshot.
- **Hooks** read the tool-call JSON on stdin and print a decision. They parse the command string (including `sh -c`, `eval`, `$(...)` and backtick substitutions) and never execute it, do not modify files, and make no network calls. They run on every `Bash` call while the plugin is enabled; each takes well under 100 ms.
- **Skill and agent text** tells Claude to treat everything it reads in your repository (instruction files, tool descriptions, comments, scanner output) as untrusted data under review, never as instructions.
- **Commands and the agent** are Markdown. The reviewer agent cannot edit files.
- **MCP server** reads one JSON file, listens on nothing, fetches nothing, executes nothing. Dependencies: `@modelcontextprotocol/sdk` and `zod`.
- **No telemetry.** Nothing here reports usage anywhere.
- The repository audits itself in CI with its own scanner (`--fail-on high`) and validates its structure with `scripts/validate_plugin.py` and `claude plugin validate`.

Report security problems privately: see [SECURITY.md](SECURITY.md).

## Development

```bash
python3 scripts/validate_plugin.py
python3 scripts/run_tests.py -v
cd plugins/agent-security/mcp/incidents-server && npm install && npm run build && npm test
docker build -t agent-incidents-mcp . && echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' | docker run --rm -i agent-incidents-mcp
semgrep --metrics=off --test --config plugins/agent-security/skills/semgrep-agentic/rules/agentic-python.yaml plugins/agent-security/skills/semgrep-agentic/rules/tests/agentic-python.py
claude plugin validate . && claude plugin validate ./plugins/agent-security
python3 scripts/build_incidents.py path/to/ai-agent-incidents   # refresh the bundled dataset (schema-validated)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the ground rules (standard library only, tests with every script, no new network calls).

## Frequently asked questions

**Is there a Claude Code plugin for security reviews of AI agents?**
Yes, this one. `agent-security` is a Claude Code plugin with ten skills that do real work from inside the editor: threat model an agent codebase (drafting a system description for `agent-threat-model` and running it), audit `.claude/`, `CLAUDE.md`, `.cursor/`, `.mcp.json` and desktop MCP configs for permissions, hooks, unpinned servers and secrets, review an MCP server against a checklist, trace prompt injection from untrusted inputs to tool calls, check that every consequential tool sits behind a human approval gate that cannot fail open, look up precedents in the incident dataset, build a security eval, run the 36-rule agentic-semgrep-rules pack, and review a session log for what the agent actually did. Three slash commands (`/agent-security:audit`, `/agent-security:threat-model`, `/agent-security:incidents`) chain the skills into reports, and a read-only reviewer subagent runs them without write access. The skills follow the agentskills.io format, so other assistants that read `SKILL.md` can load them too.

**Does it send my code anywhere?**
No. Skills are Markdown instructions plus standard-library Python scripts that read files under the directory you point them at and write only where you pass `--out`. The hooks read the tool call on stdin and print a decision. The MCP server reads one JSON file, listens on nothing and fetches nothing. The one network call in the whole plugin is optional: `incidents.py` may GET the published dataset JSON to refresh its cache (10 second timeout, 20 MB cap, skipped with `--offline`, and never required because the bundled snapshot is the fallback). There is no telemetry, and the repository audits itself in CI with its own scanner.

**Can it block commands that print secrets?**
Yes. The `block-secret-exposure` hook runs before every `Bash` call and exits 2, which blocks the command and shows the reason to the model, when the command would print or export likely secrets: `env`, `printenv`, bare `export` or `set`, `echo $OPENAI_API_KEY`, `cat .env`, `less ~/.aws/credentials`, `base64 ~/.ssh/id_ed25519`, `scp .env host:`, `gh auth token`, `gcloud auth print-access-token`, `kubectl get secret -o yaml`, `print(os.environ)`, including inside `sh -c`, `eval`, `sudo`, `$(...)` and backticks. It allows `env FOO=bar cmd`, `printenv HOME`, `[ -n "$TOKEN" ]`, `cat .env.example`, `source .env` and using a secret in a header. A second hook, `warn-insecure-fetch`, asks before `curl` or `wget` to plain HTTP, raw IPs, the cloud metadata address, or a download piped into a shell. Known pattern gaps are listed in [docs/good-first-issues.md](docs/good-first-issues.md); there is no environment-variable bypass.

**Does it work with MCP servers?**
In three ways. The `mcp-server-review` skill reviews an MCP server you are writing or about to enable (authentication, transport binding, input validation, description poisoning, SSRF, limits, logging) and runs the Semgrep rules for FastMCP and MCP SDK tool handlers. The `agent-config-audit` skill checks `.mcp.json` and desktop MCP configs for unpinned servers and secrets in environment blocks. And the plugin ships its own MCP server, `agent-incidents`, a read-only stdio server over the incident dataset with `search_incidents`, `get_incident` and `stats`, built from `mcp/incidents-server` with `npm install && npm run build && npm test`.

**How do I install it?**
In a Claude Code session: `/plugin marketplace add basitalisandhu/agent-security-skills` then `/plugin install agent-security@agent-security-skills`. From a shell: `claude plugin marketplace add basitalisandhu/agent-security-skills` then `claude plugin install agent-security@agent-security-skills --scope user`. To try it without installing, clone the repository and start Claude Code with `claude --plugin-dir ./plugins/agent-security`. Requirements: Python 3.11 or newer on `PATH` as `python3`; optionally Semgrep, `uvx` or `pipx` for `agent-threat-model`, and Node 20 or newer to build the incidents MCP server. After installing, skills appear as `/agent-security:<skill>`.

## Roadmap

- `0.2`: `agent-threat-model` runs `atm diff` before and after proposed controls automatically.
- `0.3`: `mcp-server-review` gains a runtime probe (connect, list tools, diff descriptions across calls).
- `0.4`: eval suites for common agent shapes (support bot, coding agent, browsing agent) runnable in CI without a model.
- Ongoing: more Semgrep rules upstream in `agentic-semgrep-rules`, each with an incident as its justification.

## Sibling projects

More tools by the same author: https://github.com/basitalisandhu

| Project | What it is |
|---|---|
| [ai-agent-incidents](https://github.com/basitalisandhu/ai-agent-incidents) | Open, structured dataset of publicly documented AI-agent security incidents: JSON + schema, mapped to OWASP and MITRE ATLAS, with a [browsable site](https://basitalisandhu.github.io/ai-agent-incidents/). |
| [agentic-semgrep-rules](https://github.com/basitalisandhu/agentic-semgrep-rules) | Semgrep rule pack for insecure agent code: unbounded tool permissions, eval of model output, SSRF through tool URLs, prompt interpolation, MCP servers without auth. |
| [agent-threat-model](https://github.com/basitalisandhu/agent-threat-model) | CLI that turns a YAML description of an agent system into a STRIDE + OWASP Agentic threat model, control checklist and Mermaid diagram. |
| [All packs in one repository: claude-skills](https://github.com/basitalisandhu/claude-skills) | All packs in one repository; this plugin's pages are at https://basitalisandhu.github.io/claude-skills/plugins/agent-security/ |

## Licence

MIT. The bundled incident dataset is CC BY 4.0 (attribution: Muhammad Basit Ali, ai-agent-incidents).
