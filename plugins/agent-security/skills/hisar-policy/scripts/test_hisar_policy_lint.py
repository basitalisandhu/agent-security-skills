"""Tests for hisar_policy_lint.py."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hisar_policy_lint as lint  # noqa: E402

GOOD = {
    "connectors": [
        {"name": "crm-read", "base_url": "https://api.example.com", "auth_header": "Authorization", "auth_prefix": "Bearer ", "secret": "${CRM_TOKEN}"},
        {"name": "crm-write", "base_url": "https://api.example.com", "secret": "${CRM_TOKEN}"},
    ],
    "agents": [{
        "name": "mailbot", "owner": "basit", "description": "weekly digest",
        "policies": [
            {"scope_pattern": "crm-read:GET:/contacts/*", "max_ttl": 120},
            {"scope_pattern": "crm-read:GET:/contacts", "max_ttl": 120},
            {"scope_pattern": "crm-write:POST:/contacts", "max_ttl": 60, "requires_approval": True, "single_use": True},
        ],
    }],
}


def codes(bundle: dict, level: str | None = None) -> set[str]:
    return {f["code"] for f in lint.lint_bundle(bundle).findings if level is None or f["level"] == level}


class GoodBundleTests(unittest.TestCase):
    def test_clean_bundle_has_no_errors_or_warnings(self):
        result = lint.lint_bundle(GOOD)
        self.assertEqual(result.summary()["error"], 0, result.findings)
        self.assertEqual(result.summary()["warning"], 0, result.findings)


class ConnectorTests(unittest.TestCase):
    def test_connector_checks(self):
        bundle = {"connectors": [
            {"name": "CRM", "base_url": "https://api.example.com", "secret": "${X}"},
            {"name": "ok", "base_url": "http://user:pw@10.0.0.5/x?y=1", "secret": "literal-secret-value-123"},
            {"name": "ok", "base_url": "https://api.example.com", "secret": "${Y}", "auth_prefix": "x" * 41},
            {"name": "nosecret", "base_url": "https://api.example.com"},
        ], "agents": []}
        found = codes(bundle)
        for c in ["connector_name", "base_url", "base_url_plain_http", "base_url_private", "secret_literal", "connector_duplicate", "auth_prefix", "secret_missing"]:
            self.assertIn(c, found, c)


class PolicyTests(unittest.TestCase):
    def test_scope_grammar_and_ttl(self):
        bundle = {"connectors": [{"name": "crm", "base_url": "https://a.example", "secret": "${T}"}], "agents": [{"name": "a", "owner": "o", "policies": [
            {"scope_pattern": "crm:get:/x", "max_ttl": 5},
            {"scope_pattern": "crm GET /x"},
            {"scope_pattern": "*"},
            {"scope_pattern": "crm:*"},
            {"scope_pattern": "crm:DELETE:/x", "max_ttl": 3600},
            {"scope_pattern": "lease:crm", "requires_approval": True, "max_ttl": 3600},
            {"scope_pattern": "lease:*"},
            {"scope_pattern": "mcp:*"},
            {"scope_pattern": "mcp:github:*"},
            {"scope_pattern": "billing:GET:/x"},
            {"scope_pattern": "crm:GET:/contacts*"},
            {"scope_pattern": "crm:GET:/contacts*"},
        ]}]}
        found = codes(bundle)
        for c in ["method_case", "max_ttl", "scope_chars", "wildcard_policy", "write_without_approval", "write_ttl", "lease_gated", "lease_ttl", "lease_wildcard", "unknown_connector", "prefix_match", "duplicate_pattern"]:
            self.assertIn(c, found, c)
        errors = codes(bundle, "error")
        self.assertEqual(errors, {"method_case", "max_ttl", "scope_chars", "lease_gated"})

    def test_overlap_and_ties(self):
        bundle = {"connectors": [{"name": "crm", "base_url": "https://a.example", "secret": "${T}"}], "agents": [{"name": "a", "owner": "o", "policies": [
            {"scope_pattern": "crm:*"},
            {"scope_pattern": "crm:POST:/contacts", "requires_approval": True, "single_use": True},
            {"scope_pattern": "crm:GET:/a*"},
            {"scope_pattern": "crm:GET:/*a"},
        ]}]}
        found = codes(bundle)
        self.assertIn("gated_scope_overlapped", found)
        self.assertIn("specificity_tie", found)
        self.assertTrue(lint.overlaps("crm:*", "crm:POST:/contacts"))
        self.assertFalse(lint.overlaps("crm:GET:/*", "crm:POST:/contacts"))

    def test_agent_checks(self):
        bundle = {"connectors": [], "agents": [{"name": "", "policies": []}, {"name": "x" * 121, "owner": "o" * 121, "description": "d" * 1001, "policies": [{"scope_pattern": "a:GET:/x"}] * 51}]}
        found = codes(bundle)
        for c in ["agent_name", "agent_without_owner", "no_policies", "owner_length", "description_length", "too_many_policies"]:
            self.assertIn(c, found, c)


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = lint.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_json_text_and_curl(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "b.json"
            f.write_text(json.dumps(GOOD))
            rc, out, _ = self.run_cli([str(f)])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out)["summary"]["error"], 0)
            rc, out, _ = self.run_cli([str(f), "--format", "text"])
            self.assertIn("0 error(s)", out)
            rc, out, _ = self.run_cli([str(f), "--emit-curl"])
            self.assertEqual(rc, 0)
            self.assertIn("/admin/api/connectors", out)
            self.assertIn("/admin/api/agents", out)
            self.assertIn("${CRM_TOKEN:?}", out)
            self.assertNotIn("literal", out)
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps({"connectors": [{"name": "c", "base_url": "https://a.example", "secret": "plain-text-secret-1"}], "agents": []}))
            rc, out, err = self.run_cli([str(bad), "--emit-curl"])
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")
            self.assertIn("secret_literal", err)
            bad.write_text("{nope")
            rc, _, err = self.run_cli([str(bad)])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
