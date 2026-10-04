#!/usr/bin/env python3
"""Refresh the bundled incident dataset (plugins/agent-security/data/incidents.json).

The bundle is a copy of `site/incidents.json` from https://github.com/basitalisandhu/ai-agent-incidents:
a JSON array of records in the shape of schema/incident.schema.json (id, date, name, type, lens, vector,
channel_in, authority, channel_out, adversarial, outcome, cve[], sources[{url,...}], summary,
mappings{owasp_agentic[], owasp_llm[], mitre_atlas[]}, affected{vendors[], products[], frameworks[]}, tags[], status).
Because the bundle and the published file have the same shape, the online fetch in incidents.py and the offline
fallback are interchangeable.

Usage:
    python3 scripts/build_incidents.py /path/to/ai-agent-incidents            # checkout: uses site/incidents.json and schema/
    python3 scripts/build_incidents.py /path/to/incidents.json [--schema incident.schema.json]
    python3 scripts/build_incidents.py --url                                   # fetch the published file (network)

Every record is validated against the schema with a small built-in validator (type, enum, pattern, required,
additionalProperties, items, minItems, minLength, maxLength, uniqueItems). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

PUBLISHED_URL = "https://raw.githubusercontent.com/basitalisandhu/ai-agent-incidents/main/site/incidents.json"
SCHEMA_URL = "https://raw.githubusercontent.com/basitalisandhu/ai-agent-incidents/main/schema/incident.schema.json"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "plugins/agent-security/data/incidents.json"


class SchemaError(ValueError):
    pass


def validate(value, schema: dict, path: str = "$") -> list[str]:
    """Validate against the subset of JSON Schema the incident schema uses. Returns a list of problems."""
    problems: list[str] = []
    t = schema.get("type")
    if t:
        ok = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "number": (int, float)}[t]
        if not isinstance(value, ok) or (t in {"integer", "number"} and isinstance(value, bool)):
            return [f"{path}: expected {t}"]
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            problems.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            problems.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            problems.append(f"{path}: longer than {schema['maxLength']}")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                problems.append(f"{path}: missing {req}")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                problems += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                problems.append(f"{path}: unexpected property {k}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            problems.append(f"{path}: fewer than {schema['minItems']} items")
        if schema.get("uniqueItems") and len({json.dumps(i, sort_keys=True) for i in value}) != len(value):
            problems.append(f"{path}: duplicate items")
        if "items" in schema:
            for i, item in enumerate(value):
                problems += validate(item, schema["items"], f"{path}[{i}]")
    return problems


def load_source(src: str | None, schema_arg: str | None, use_url: bool) -> tuple[list, dict | None]:
    schema = None
    if use_url:
        with urllib.request.urlopen(PUBLISHED_URL, timeout=30) as resp:
            records = json.loads(resp.read().decode("utf-8"))
        try:
            with urllib.request.urlopen(SCHEMA_URL, timeout=30) as resp:
                schema = json.loads(resp.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            schema = None
    else:
        p = Path(src)
        if p.is_dir():
            data_file = p / "site" / "incidents.json"
            if not data_file.exists():
                files = sorted((p / "incidents").glob("*.json"))
                records = [json.loads(f.read_text(encoding="utf-8")) for f in files]
            else:
                records = json.loads(data_file.read_text(encoding="utf-8"))
            sp = p / "schema" / "incident.schema.json"
            schema = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
        else:
            records = json.loads(p.read_text(encoding="utf-8"))
    if schema_arg:
        schema = json.loads(Path(schema_arg).read_text(encoding="utf-8"))
    if isinstance(records, dict) and isinstance(records.get("incidents"), list):
        records = records["incidents"]
    if not isinstance(records, list):
        raise SchemaError("source must be a JSON array of incident records")
    return records, schema


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", help="ai-agent-incidents checkout, or an incidents.json file")
    ap.add_argument("--schema", help="incident.schema.json to validate against (default: the checkout's)")
    ap.add_argument("--url", action="store_true", help="fetch the published dataset instead of reading a local source")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    if not args.source and not args.url:
        ap.error("give a source path or --url")
    records, schema = load_source(args.source, args.schema, args.url)
    problems: list[str] = []
    if schema:
        for r in records:
            problems += validate(r, schema, f"incident {r.get('id', '?')}")
    else:
        print("warning: no schema found; only checking required keys", file=sys.stderr)
        required = ["id", "date", "name", "type", "lens", "vector", "channel_in", "authority", "channel_out", "adversarial", "outcome", "cve", "sources", "summary", "mappings", "affected", "tags", "status"]
        for r in records:
            problems += [f"incident {r.get('id', '?')}: missing {k}" for k in required if k not in r]
    ids = [r.get("id") for r in records]
    if len(ids) != len(set(ids)):
        problems.append("duplicate ids")
    if problems:
        for p in problems[:50]:
            print(f"error: {p}", file=sys.stderr)
        print(f"{len(problems)} problem(s); bundle not written", file=sys.stderr)
        return 1
    records.sort(key=lambda r: r["id"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    dates = sorted(r["date"] for r in records)
    print(f"wrote {args.out} ({len(records)} incidents, {dates[0]} to {dates[-1]}, schema-validated: {'yes' if schema else 'no'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
