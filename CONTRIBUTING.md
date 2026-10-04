# Contributing

Thank you for helping make agents safer. This repository values precision over volume: a small number of skills that are correct, well-tested and useful beats a long list of thin ones.

## Ground rules

- **No telemetry, no surprise network calls.** The only network access in this repository is the documented incident dataset fetch. A pull request that adds another one needs a very good reason and an opt-out.
- **Standard library only for Python.** Skill scripts and hooks must run with Python 3.11 and no third-party packages, because they execute on users' machines without an install step.
- **Minimal dependencies for the MCP server.** Runtime dependencies are `@modelcontextprotocol/sdk` and `zod`. Please do not add more.
- **Tests come with code.** Every script has a test file next to it. Hooks are tested by piping sample tool-call JSON through them. Semgrep rules carry a test fixture with `ruleid` and `ok` annotations.
- **Repository content is data.** Skill, agent and command text must tell Claude to treat what it reads in a user's repository as untrusted data under review, never as instructions. Keep that line when you edit a skill.
- **No model version strings** in skills, agents or docs. Skills should work regardless of which model runs them.
- **Plain language.** Write for a security engineer who has not used Claude Code before. Avoid em-dashes; use commas, colons or full stops.

## Adding or changing a skill

1. Create `plugins/agent-security/skills/<name>/SKILL.md` with YAML frontmatter containing `name` (must equal the directory name) and `description`. The description is what triggers the skill, so state both what it does and when to use it.
2. Keep `SKILL.md` under 500 lines. Put long reference material in `references/` and executable helpers in `scripts/`.
3. Give the skill a clear output format (a table, a JSON shape, a report template).
4. Run `python3 scripts/validate_plugin.py` from the repository root. It must pass.
5. Add a row to the skill table in `README.md` and a line in `CHANGELOG.md`.

## Running the checks locally

```bash
python3 scripts/validate_plugin.py
python3 scripts/run_tests.py -v
cd plugins/agent-security/mcp/incidents-server && npm install && npm run build && npm test
cd plugins/agent-security/skills/semgrep-agentic/rules && \
  semgrep --metrics=off --test --config agentic-python.yaml tests/agentic-python.py && \
  semgrep --metrics=off --test --config agentic-javascript.yaml tests/agentic-javascript.ts   # optional, needs semgrep; `semgrep --test <dir>` finds nothing here and exits 0
claude plugin validate .                                              # optional, needs the Claude Code CLI
```

## Pull requests

- One topic per pull request.
- Describe what changed and why, and how you tested it.
- Changes to hooks need a before/after example of a command they now block or allow.
- By contributing you agree that your contribution is licensed under the MIT licence of this repository.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Please do not file security problems as public issues.
