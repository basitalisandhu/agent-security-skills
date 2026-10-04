#!/usr/bin/env python3
"""Lint a Hisar Broker policy bundle before it is applied, and optionally emit the admin API calls.

Bundle shape (what the hisar-policy skill writes):

{
  "connectors": [{"name": "crm", "base_url": "https://api.example.com", "auth_header": "Authorization",
                  "auth_prefix": "Bearer ", "secret": "${CRM_TOKEN}"}],
  "agents": [{"name": "mailbot", "owner": "basit", "description": "weekly digest",
              "policies": [{"scope_pattern": "crm:GET:/contacts*", "max_ttl": 120,
                            "requires_approval": false, "single_use": false}]}]
}

Checks follow docs/api-reference.md and docs/concepts.md of https://basitalisandhu.github.io/hisar/hisar-broker.html:
field limits and character sets, scope grammar, TTL range, lease policies that cannot be approval-gated,
wildcard policies, write scopes without approval, ungated patterns that overlap gated ones, literal secrets.

Usage:
  hisar_policy_lint.py bundle.json                 JSON findings, exit 1 on any error
  hisar_policy_lint.py bundle.json --format text
  hisar_policy_lint.py bundle.json --emit-curl     print the curl sequence (connectors first, then agents)

Standard library only. No network.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

CONNECTOR_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
SCOPE_CHARS_RE = re.compile(r"^[A-Za-z0-9_.:/*@%~-]{1,200}$")
ENV_REF_RE = re.compile(r"^\$\{?[A-Za-z_][A-Za-z0-9_]*\}?$")
METHODS = {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PRIVATE_HOST_RE = re.compile(r"^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|0\.0\.0\.0|\[::1\]|.*\.local|.*\.internal)")


def glob_to_re(pattern: str) -> re.Pattern[str]:
    return re.compile("^" + ".*".join(re.escape(p) for p in pattern.split("*")) + "$")


@functools.lru_cache(maxsize=None)
def overlaps(a: str, b: str) -> bool:
    """True when some scope string matches both patterns (`*` matches any run of characters)."""
    if not a and not b:
        return True
    if a.startswith("*"):
        return overlaps(a[1:], b) or (bool(b) and overlaps(a, b[1:]))
    if b.startswith("*"):
        return overlaps(a, b[1:]) or (bool(a) and overlaps(a[1:], b))
    if not a or not b:
        return False
    return a[0] == b[0] and overlaps(a[1:], b[1:])


def literal_len(pattern: str) -> int:
    return len(pattern.replace("*", ""))


class Lint:
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def add(self, level: str, code: str, where: str, message: str, fix: str = "") -> None:
        self.findings.append({"level": level, "code": code, "where": where, "message": message, "fix": fix})

    # ------------------------------------------------------------------ connectors
    def connectors(self, items: list) -> set[str]:
        names: set[str] = set()
        for i, c in enumerate(items):
            where = f"connectors[{i}]"
            if not isinstance(c, dict):
                self.add("error", "shape", where, "connector must be an object")
                continue
            name = str(c.get("name", ""))
            where = f"connector {name or i}"
            if not CONNECTOR_NAME_RE.match(name):
                self.add("error", "connector_name", where, f"name {name!r} must match ^[a-z0-9][a-z0-9-]{{1,39}}$")
            elif name in names:
                self.add("error", "connector_duplicate", where, "duplicate connector name (broker returns 409 connector_exists)")
            names.add(name)
            url = str(c.get("base_url", ""))
            parts = urlsplit(url) if url else None
            if not parts or parts.scheme not in {"http", "https"} or not parts.netloc:
                self.add("error", "base_url", where, f"base_url {url!r} must be an http(s) URL")
            else:
                if parts.username or parts.password or parts.query or parts.fragment:
                    self.add("error", "base_url", where, "base_url must not carry credentials, a query or a fragment")
                if parts.scheme == "http":
                    self.add("warning", "base_url_plain_http", where, "base_url uses plain HTTP; the leased or proxied credential travels in clear text", "use https://")
                if PRIVATE_HOST_RE.match(parts.hostname or ""):
                    self.add("warning", "base_url_private", where, "private or local upstream; the broker refuses it unless HISAR_ALLOW_PRIVATE_UPSTREAMS=1")
            prefix = c.get("auth_prefix", "Bearer ")
            if prefix is not None and len(str(prefix)) > 40:
                self.add("error", "auth_prefix", where, "auth_prefix is longer than 40 characters")
            secret = c.get("secret")
            if secret is None or secret == "":
                self.add("error", "secret_missing", where, "secret is required (1 to 4000 characters)", "use an environment reference such as ${CRM_TOKEN}")
            elif not ENV_REF_RE.match(str(secret)):
                self.add("error", "secret_literal", where, "secret is a literal value; bundles are reviewed and committed, so keep secrets in the environment",
                         "replace with ${ENV_VAR} and export it where the curl runs")
            elif len(str(secret)) > 4000:
                self.add("error", "secret_length", where, "secret exceeds 4000 characters")
        return names

    # ------------------------------------------------------------------ agents
    def agents(self, items: list, connector_names: set[str]) -> None:
        seen: set[str] = set()
        for i, a in enumerate(items):
            where = f"agents[{i}]"
            if not isinstance(a, dict):
                self.add("error", "shape", where, "agent must be an object")
                continue
            name = str(a.get("name", ""))
            where = f"agent {name or i}"
            if not 1 <= len(name) <= 120:
                self.add("error", "agent_name", where, "name must be 1 to 120 characters")
            if name in seen:
                self.add("warning", "agent_duplicate", where, "two agents share a name; the broker allows it but audit trails get confusing")
            seen.add(name)
            owner = a.get("owner")
            if not owner:
                self.add("warning", "agent_without_owner", where, "no owner; evidence packs flag agent_without_owner", "set owner to the accountable person or team")
            elif len(str(owner)) > 120:
                self.add("error", "owner_length", where, "owner is longer than 120 characters")
            if a.get("description") and len(str(a["description"])) > 1000:
                self.add("error", "description_length", where, "description is longer than 1000 characters")
            policies = a.get("policies") or []
            if not isinstance(policies, list):
                self.add("error", "shape", where, "policies must be a list")
                continue
            if len(policies) > 50:
                self.add("error", "too_many_policies", where, "more than 50 policies in one create-agent call; add the rest with POST /agents/:id/policies")
            if not policies:
                self.add("info", "no_policies", where, "agent has no policies; every token request will be refused until some are added")
            self.policies(where, policies, connector_names)

    def policies(self, where: str, policies: list, connector_names: set[str]) -> None:
        patterns: list[tuple[str, bool, int]] = []
        for j, p in enumerate(policies):
            pw = f"{where} policy[{j}]"
            if not isinstance(p, dict):
                self.add("error", "shape", pw, "policy must be an object")
                continue
            sp = str(p.get("scope_pattern", ""))
            pw = f"{where} {sp or 'policy[' + str(j) + ']'}"
            gated = bool(p.get("requires_approval", False))
            single = bool(p.get("single_use", False))
            ttl = p.get("max_ttl", 300)
            if not SCOPE_CHARS_RE.match(sp):
                self.add("error", "scope_chars", pw, "scope_pattern must be 1 to 200 characters from A-Z a-z 0-9 _ . : / * @ % ~ -")
                continue
            if not isinstance(ttl, int) or isinstance(ttl, bool) or not 10 <= ttl <= 86400:
                self.add("error", "max_ttl", pw, "max_ttl must be an integer from 10 to 86400 seconds")
            if any(sp == q[0] for q in patterns):
                self.add("warning", "duplicate_pattern", pw, "the same scope_pattern appears twice; the broker picks one, avoid the tie")
            patterns.append((sp, gated, int(ttl) if isinstance(ttl, int) else 300))
            if sp == "*":
                self.add("warning", "wildcard_policy", pw, "`*` grants every scope the broker will ever see", "name the connector and method: crm:GET:/contacts*")
            parts = sp.split(":", 2)
            if parts[0] == "lease":
                if gated:
                    self.add("error", "lease_gated", pw, "a lease policy cannot require approval (403 lease_cannot_be_approval_gated)", "put the approval on the tool scopes instead")
                if len(parts) < 2 or "*" in parts[1]:
                    self.add("warning", "lease_wildcard", pw, "lease policy with a wildcard hands out every connector secret")
                elif parts[1] not in connector_names and connector_names:
                    self.add("warning", "unknown_connector", pw, f"no connector named {parts[1]!r} in this bundle")
                if isinstance(ttl, int) and ttl > 900:
                    self.add("warning", "lease_ttl", pw, "lease TTL above 15 minutes; the broker cannot recall a leased secret")
                continue
            if parts[0] == "mcp":
                if len(parts) < 3 or "*" in parts[1]:
                    self.add("warning", "wildcard_policy", pw, "mcp policy covers every server or tool", "use mcp:<server>:<tool>")
                elif parts[2] == "*" and not gated:
                    self.add("warning", "wildcard_policy", pw, f"every tool of MCP server {parts[1]} is ungated", "list read-only tools ungated; gate write tools")
                continue
            if len(parts) == 3 and parts[1] and parts[1] != "*":
                connector, method, path = parts
                if method.upper() in METHODS and method != method.upper():
                    self.add("error", "method_case", pw, f"METHOD must be upper case ({method.upper()}); {method!r} never matches")
                elif method not in METHODS and "*" not in method:
                    self.add("warning", "method_unknown", pw, f"{method!r} is not an HTTP method; proxy scopes are connector:METHOD:/path (custom scopes for your own services are fine)")
                if method in WRITE_METHODS and not gated:
                    self.add("warning", "write_without_approval", pw, f"{method} scope without requires_approval", "set requires_approval true (and single_use for one-off actions) or move writes to a *-write connector")
                if method in WRITE_METHODS and not single and gated:
                    self.add("info", "write_multi_use", pw, "approved write token can be reused until it expires", "set single_use true if one approval should cover one action")
                if path and not path.startswith("/") and "*" not in path:
                    self.add("warning", "path_shape", pw, "path should start with /")
                if path.endswith("*") and len(path) > 1 and not path.endswith("/*"):
                    self.add("info", "prefix_match", pw, f"trailing * is a prefix match: {path} also covers {path[:-1]}-archive; add {path[:-1]}/* for a segment boundary")
                if connector not in connector_names and connector_names and "*" not in connector:
                    self.add("warning", "unknown_connector", pw, f"no connector named {connector!r} in this bundle")
                if isinstance(ttl, int) and method in WRITE_METHODS and ttl > 600:
                    self.add("warning", "write_ttl", pw, "write scope with TTL above 10 minutes", "keep write tokens short, 60 to 300 seconds")
            elif len(parts) == 2 and parts[1] == "*" or (len(parts) == 3 and parts[1] == "*"):
                self.add("warning", "wildcard_policy", pw, f"covers every method and path of connector {parts[0]}", "grant GET paths ungated and gate writes separately")
            if isinstance(ttl, int) and ttl > 3600 and not gated:
                self.add("info", "long_ttl", pw, "ungated token lives over an hour; revocation is the only way to stop it early")
        # overlap: an ungated pattern that can match a gated one lets wildcard requests be tightened by the broker,
        # but the policy set is clearer when gated scopes live under their own connector.
        for sp, gated, _ in patterns:
            if gated:
                continue
            for other, og, _ in patterns:
                if og and other != sp and overlaps(sp, other):
                    self.add("warning", "gated_scope_overlapped", f"{where} {sp}", f"ungated pattern overlaps gated {other}; wildcard token requests under it will be gated, but reviewers can misread it",
                             "register the upstream twice (crm-read, crm-write) and put the gated scopes under crm-write")
                    break
        lengths: dict[int, list[str]] = {}
        for sp, _, _ in patterns:
            lengths.setdefault(literal_len(sp), []).append(sp)
        for ln, group in lengths.items():
            if len(group) > 1:
                pairs = [(a, b) for a in group for b in group if a < b and overlaps(a, b)]
                for a, b in pairs:
                    self.add("info", "specificity_tie", f"{where}", f"{a} and {b} have the same literal length ({ln}); the winner for a scope both match is not promised by the broker")

    def summary(self) -> dict:
        levels = {"error": 0, "warning": 0, "info": 0}
        for f in self.findings:
            levels[f["level"]] += 1
        return levels


def emit_curl(bundle: dict) -> str:
    lines = ["#!/usr/bin/env bash", "# Generated by hisar_policy_lint.py --emit-curl. Review before running.",
             "set -euo pipefail", ": \"${HISAR_URL:?set HISAR_URL, e.g. https://broker.example.com}\"",
             ": \"${HISAR_ADMIN:?set HISAR_ADMIN to an operator token with role admin}\"",
             "H=\"Authorization: Bearer $HISAR_ADMIN\"", "J='content-type: application/json'", ""]
    for c in bundle.get("connectors", []):
        body = {k: c[k] for k in ("name", "base_url", "auth_header", "auth_prefix") if k in c}
        secret = str(c.get("secret", ""))
        var = secret.strip("${}") if ENV_REF_RE.match(secret) else None
        payload = json.dumps(body)[:-1] + f', "secret": "\'"${{{var}:?}}"\'"}}' if var else json.dumps({**body, "secret": secret})
        lines.append(f"# connector {c.get('name')}")
        lines.append(f"curl -sS -X POST \"$HISAR_URL/admin/api/connectors\" -H \"$H\" -H \"$J\" -d '{payload}'")
        lines.append("echo")
    for a in bundle.get("agents", []):
        body = {k: a[k] for k in ("name", "owner", "description", "policies") if k in a}
        lines.append(f"# agent {a.get('name')} (the response carries agent_key once; store it in your secret manager)")
        lines.append(f"curl -sS -X POST \"$HISAR_URL/admin/api/agents\" -H \"$H\" -H \"$J\" -d '{json.dumps(body)}'")
        lines.append("echo")
    return "\n".join(lines) + "\n"


def lint_bundle(bundle: dict) -> Lint:
    lint = Lint()
    if not isinstance(bundle, dict):
        lint.add("error", "shape", "bundle", "bundle must be a JSON object with connectors and agents")
        return lint
    connectors = bundle.get("connectors") or []
    agents = bundle.get("agents") or []
    if not isinstance(connectors, list) or not isinstance(agents, list):
        lint.add("error", "shape", "bundle", "connectors and agents must be lists")
        return lint
    names = lint.connectors(connectors)
    lint.agents(agents, names)
    if not agents:
        lint.add("info", "no_agents", "bundle", "bundle defines no agents")
    return lint


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="policy bundle JSON file, or - for stdin")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    ap.add_argument("--emit-curl", action="store_true", help="print the admin API calls instead of findings (refused when there are errors)")
    args = ap.parse_args(argv)
    text = sys.stdin.read() if args.bundle == "-" else Path(args.bundle).read_text(encoding="utf-8")
    try:
        bundle = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"hisar_policy_lint: bundle is not valid JSON: {exc}", file=sys.stderr)
        return 2
    lint = lint_bundle(bundle)
    summary = lint.summary()
    if args.emit_curl:
        if summary["error"]:
            print(f"hisar_policy_lint: {summary['error']} error(s); fix them before emitting calls", file=sys.stderr)
            for f in lint.findings:
                if f["level"] == "error":
                    print(f"  [{f['code']}] {f['where']}: {f['message']}", file=sys.stderr)
            return 1
        sys.stdout.write(emit_curl(bundle))
        return 0
    if args.format == "json":
        print(json.dumps({"summary": summary, "findings": lint.findings}, indent=1))
    else:
        for f in lint.findings:
            fix = f" -> {f['fix']}" if f["fix"] else ""
            print(f"{f['level'].upper():8} [{f['code']}] {f['where']}: {f['message']}{fix}")
        print(f"\n{summary['error']} error(s), {summary['warning']} warning(s), {summary['info']} note(s)")
    return 1 if summary["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
