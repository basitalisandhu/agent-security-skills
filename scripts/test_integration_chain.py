#!/usr/bin/env python3
"""End-to-end chain across four skills on one fixture agent (run by scripts/run_tests.py).

The chain is the one agent-threat-model's SKILL.md describes for a design review:

  1. agent-threat-model: scan_agent_stack.py finds the untrusted inputs and the authorities of a crewAI agent;
  2. incident-lookup: those become a design file for `incidents.py precedents --design`, which must return real
     precedents that share the agent's input channel or authority;
  3. prompt-injection-review: tool_inventory.py lists the agent's tools with a consequential or regular tier;
  4. tool-approval-gate-audit: approval_gates.py must agree with that tiering tool by tool and report the gaps.

Everything runs offline on the bundled snapshot and the bundled fixture.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "agent-security" / "skills"
FIXTURE = SKILLS / "tool-approval-gate-audit" / "scripts" / "fixtures" / "crewai"


def run_json(*argv) -> dict:
    proc = subprocess.run([sys.executable, *map(str, argv)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    if proc.returncode not in (0, 1):
        raise AssertionError(f"{argv[0]} exited {proc.returncode}: {proc.stderr}")
    return json.loads(proc.stdout)


class DesignReviewChainTest(unittest.TestCase):
    def test_scan_to_precedents_to_tool_gates(self):
        # 1. stack scan: inputs and authorities in the incident vocabulary
        scan = run_json(SKILLS / "agent-threat-model" / "scripts" / "scan_agent_stack.py", FIXTURE, "--json")
        hits = scan["detections"]["hits"]
        inputs, authorities = sorted(hits.get("inputs", {})), sorted(hits.get("authorities", {}))
        self.assertIn("email", inputs)
        self.assertIn("send-message", authorities)

        # 2. precedents for that design, from the bundled snapshot: first the scan output passed as it is, then a
        #    hand-written design that adds a vector, as SKILL.md step 5 describes
        incidents = SKILLS / "incident-lookup" / "scripts" / "incidents.py"
        with tempfile.TemporaryDirectory() as tmp:
            scan_file = Path(tmp) / "scan.json"
            scan_file.write_text(json.dumps(scan), encoding="utf-8")
            from_scan = run_json(incidents, "--offline", "--format", "json", "precedents", "--design", scan_file)
            design = Path(tmp) / "design.json"
            design.write_text(json.dumps({"name": "newsletter crew", "channel_in": inputs, "authority": authorities,
                                          "vector": ["indirect-injection"]}), encoding="utf-8")
            prec = run_json(incidents, "--offline", "--format", "json", "precedents", "--design", design, "--limit", "5")
        self.assertEqual(from_scan["design"], "crewai")
        self.assertEqual(from_scan["inputs"]["channel_in"], inputs)
        self.assertEqual(from_scan["inputs"]["authority"], authorities)
        self.assertGreater(from_scan["matched"], 0)
        self.assertEqual(prec["design"], "newsletter crew")
        self.assertGreaterEqual(prec["matched"], from_scan["matched"])
        self.assertEqual(len(prec["precedents"]), 5)
        for p in prec["precedents"]:
            shared = p["channel_in"] in inputs or p["authority"] in authorities or p["vector"] == "indirect-injection"
            self.assertTrue(shared, f"precedent {p['id']} shares nothing with the design: {p['why']}")
            self.assertTrue(p["url"].startswith("http"), p["id"])

        # 3 and 4. tool inventory and approval gates agree on which tools are consequential
        inventory = run_json(SKILLS / "prompt-injection-review" / "scripts" / "tool_inventory.py", FIXTURE, "--format", "json")
        gates = run_json(SKILLS / "tool-approval-gate-audit" / "scripts" / "approval_gates.py", FIXTURE, "--format", "json")
        tiers = {t["name"]: t["tier"] == "consequential" for t in inventory["tools"]}
        judged = {t["name"]: t["consequential"] for t in gates["tools"]}
        self.assertEqual(tiers, judged)
        mail_tools = {t["name"] for t in gates["tools"] if any(s["kind"] == "mail" for s in t["side_effects"])}
        self.assertTrue(mail_tools, "the send-message authority from the scan should show up as a mail side effect")
        self.assertTrue(mail_tools <= {n for n, c in judged.items() if c})
        flagged = {f["tool"] for f in gates["findings"]}
        self.assertTrue(flagged, "the fixture has a gate whose answer is ignored; the audit must report it")
        self.assertTrue(flagged <= set(judged))


if __name__ == "__main__":
    unittest.main()
