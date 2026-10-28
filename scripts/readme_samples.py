#!/usr/bin/env python3
"""The sample runs shown in each skill's README.md, and a way to refresh them.

Each skill README carries one sample between `<!-- sample:begin -->` and `<!-- sample:end -->`, produced by running
the command below from the repository root on a bundled fixture. `python3 scripts/readme_samples.py --write`
re-runs every command and rewrites the blocks; scripts/test_readme_samples.py fails when a block no longer matches
what the script prints, so the samples cannot drift into invented output.

Lines that change from run to run (absolute paths, timestamps) are rewritten by `VOLATILE` before comparison.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = "plugins/agent-security/skills"
CRW = f"{SK}/tool-approval-gate-audit/scripts/fixtures/crewai"

# skill -> (command shown in the README, argv after the Python interpreter, number of output lines kept, fence language)
SAMPLES: dict[str, tuple[str, list[str], int, str]] = {
    "agent-config-audit": (
        f"python3 {SK}/agent-config-audit/scripts/audit_agent_config.py --root {SK}/semgrep-agentic/rules/tests/config-bad --format markdown",
        [f"{SK}/agent-config-audit/scripts/audit_agent_config.py", "--root", f"{SK}/semgrep-agentic/rules/tests/config-bad", "--format", "markdown"],
        26, "markdown"),
    "agent-eval-harness": (
        f"python3 {SK}/agent-eval-harness/scripts/eval_runner.py --demo",
        [f"{SK}/agent-eval-harness/scripts/eval_runner.py", "--demo"], 0, "text"),
    "agent-session-log-review": (
        f"python3 {SK}/agent-session-log-review/scripts/review_session_log.py {SK}/agent-session-log-review/references/example-session.jsonl",
        [f"{SK}/agent-session-log-review/scripts/review_session_log.py", f"{SK}/agent-session-log-review/references/example-session.jsonl"],
        13, "markdown"),
    "agent-threat-model": (
        f"python3 {SK}/agent-threat-model/scripts/scan_agent_stack.py {CRW}",
        [f"{SK}/agent-threat-model/scripts/scan_agent_stack.py", CRW], 31, "yaml"),
    "incident-lookup": (
        f"python3 {SK}/incident-lookup/scripts/incidents.py --offline --format markdown precedents --channel-in email --authority send-message --limit 3",
        [f"{SK}/incident-lookup/scripts/incidents.py", "--offline", "--format", "markdown", "precedents", "--channel-in", "email",
         "--authority", "send-message", "--limit", "3"], 16, "markdown"),
    "prompt-injection-review": (
        f"python3 {SK}/prompt-injection-review/scripts/tool_inventory.py {CRW} --format markdown",
        [f"{SK}/prompt-injection-review/scripts/tool_inventory.py", CRW, "--format", "markdown"], 14, "markdown"),
    "tool-approval-gate-audit": (
        f"python3 {SK}/tool-approval-gate-audit/scripts/approval_gates.py {CRW}",
        [f"{SK}/tool-approval-gate-audit/scripts/approval_gates.py", CRW], 0, "markdown"),
}

VOLATILE = [
    (re.compile(r"^(Root: |# Tool inventory for )`[^`]*`"), lambda m: m.group(1) + "`<path>`"),
    (re.compile(r"^Generated: \S+"), lambda m: "Generated: <timestamp>"),
]
BLOCK = re.compile(r"(<!-- sample:begin -->\n)(.*?)(<!-- sample:end -->)", re.S)


def normalise(text: str) -> str:
    out = []
    for line in text.splitlines():
        for pattern, repl in VOLATILE:
            line = pattern.sub(repl, line)
        out.append(line.rstrip())
    return "\n".join(out).strip("\n")


def render(skill: str) -> str:
    shown, argv, keep, lang = SAMPLES[skill]
    proc = subprocess.run([sys.executable, *argv], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)
    lines = normalise(proc.stdout).splitlines()
    if keep and len(lines) > keep:
        lines = lines[:keep] + ["..."]
    return f"```bash\n{shown}\n```\n\n```{lang}\n" + "\n".join(lines) + "\n```\n"


def readme(skill: str) -> Path:
    return ROOT / SK / skill / "README.md"


def main() -> int:
    write = "--write" in sys.argv
    stale = []
    for skill in SAMPLES:
        path = readme(skill)
        text = path.read_text(encoding="utf-8")
        m = BLOCK.search(text)
        if not m:
            print(f"{path}: no sample block", file=sys.stderr)
            return 2
        new = render(skill)
        if m.group(2) != new:
            stale.append(skill)
            if write:
                path.write_text(text[: m.start(2)] + new + text[m.end(2):], encoding="utf-8")
    if stale and not write:
        print("stale samples: " + ", ".join(stale), file=sys.stderr)
        return 1
    print(("rewrote " if write else "up to date: ") + (", ".join(stale) if write else str(len(SAMPLES))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
