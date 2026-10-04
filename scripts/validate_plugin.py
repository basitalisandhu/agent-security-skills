#!/usr/bin/env python3
"""Validate this marketplace repository without the Claude Code CLI.

Checks:
  * every JSON file parses (marketplace, plugin manifest, .mcp.json, hooks.json, package.json, data)
  * marketplace.json has name, owner.name and plugins[]; every plugin source directory exists and has a plugin.json
    whose name matches the entry name
  * every skills/<name>/SKILL.md has YAML frontmatter with name (equal to the directory name, lowercase, hyphens,
    at most 64 chars) and description (at most 1024 chars); referenced relative links resolve
  * every commands/*.md has frontmatter with a description; every agents/*.md has name and description
  * hooks/hooks.json uses the {"hooks": {...}} wrapper, every command hook names an existing script, and exec-form
    args reference files that exist under ${CLAUDE_PLUGIN_ROOT}
  * .mcp.json server args reference files that exist after build (dist/index.js) or warn if not built yet
  * README.md lists every skill
  * no em-dashes in Markdown, skills, commands or agents (house style)
  * the bundled incidents dataset is consistent

Exit 1 on any error. Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def frontmatter(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+)\s*:\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


SCALAR_LINE_RE = re.compile(r"^(\s*)(?:- )?([A-Za-z_][\w.-]*):(?:[ \t]+(.*))?$")
QUOTED_RE = {'"': re.compile(r'"(?:[^"\\]|\\.)*"(?:\s+#.*)?'), "'": re.compile(r"'(?:[^']|'')*'(?:\s+#.*)?")}


def scalar_problems(text: str) -> list[str]:
    """Frontmatter scalars that a strict YAML reader rejects: a plain value containing ': ' or ' #', starting with
    an indicator character or ending with ':', and a quoted value that is not closed. Returns one message per line."""
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---", 4)
    if end < 0:
        return []
    problems: list[str] = []
    block_indent: int | None = None
    for number, line in enumerate(text[4:end].splitlines(), start=2):
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if not line.strip() or indent > block_indent:
                continue
            block_indent = None
        m = SCALAR_LINE_RE.match(line)
        if not m:
            continue
        key, value = m.group(2), (m.group(3) or "").strip()
        if not value or value[0] in "[{":
            continue
        if value[0] in "|>":
            block_indent = len(m.group(1))
            continue
        if value[0] in QUOTED_RE:
            if not QUOTED_RE[value[0]].fullmatch(value):
                problems.append(f"line {number}: quoted scalar for '{key}' is not closed")
        elif value[0] in "&*!%@`,]}?#" or value[:2] in ("- ", ": ") or value == "-":
            problems.append(f"line {number}: plain scalar for '{key}' starts with a YAML indicator; wrap it in double quotes")
        elif ": " in value or " #" in value or value.endswith(":"):
            problems.append(f"line {number}: plain scalar for '{key}' contains ': ' or ' #'; wrap it in double quotes")
    return problems


def check_json_files() -> dict[Path, object]:
    parsed: dict[Path, object] = {}
    for p in sorted(ROOT.rglob("*.json")):
        if "node_modules" in p.parts or "dist" in p.parts or ".venv" in p.parts:
            continue
        try:
            parsed[p] = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            err(f"{p.relative_to(ROOT)}: invalid JSON: {exc}")
    return parsed


def check_marketplace(parsed: dict[Path, object]) -> list[Path]:
    mp = ROOT / ".claude-plugin" / "marketplace.json"
    data = parsed.get(mp)
    if not isinstance(data, dict):
        err("missing or invalid .claude-plugin/marketplace.json")
        return []
    for key in ("name", "owner", "plugins"):
        if key not in data:
            err(f"marketplace.json: missing {key}")
    if not isinstance(data.get("owner"), dict) or not data["owner"].get("name"):
        err("marketplace.json: owner.name is required")
    name = data.get("name", "")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", name) or ".." in name:
        err(f"marketplace.json: invalid name {name!r}")
    roots: list[Path] = []
    for i, entry in enumerate(data.get("plugins") or []):
        if not isinstance(entry, dict) or "name" not in entry or "source" not in entry:
            err(f"marketplace.json: plugins[{i}] needs name and source")
            continue
        src = entry["source"]
        if isinstance(src, str):
            if not src.startswith("./") or ".." in src:
                err(f"marketplace.json: plugins[{i}].source must be a ./relative path without ..: {src}")
                continue
            root = ROOT / src[2:]
            if not root.is_dir():
                err(f"marketplace.json: plugins[{i}] source directory does not exist: {src}")
                continue
            manifest = root / ".claude-plugin" / "plugin.json"
            if manifest.exists():
                m = parsed.get(manifest)
                if isinstance(m, dict) and m.get("name") != entry["name"]:
                    err(f"{manifest.relative_to(ROOT)}: name {m.get('name')!r} differs from marketplace entry {entry['name']!r}")
            else:
                warn(f"{src}: no .claude-plugin/plugin.json (allowed, but metadata comes from the entry)")
            roots.append(root)
    return roots


def check_skills(plugin: Path) -> list[str]:
    names: list[str] = []
    skills_dir = plugin / "skills"
    if not skills_dir.is_dir():
        return names
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir():
            continue
        skill = d / "SKILL.md"
        if not skill.exists():
            err(f"{d.relative_to(ROOT)}: no SKILL.md")
            continue
        for problem in scalar_problems(skill.read_text(encoding="utf-8")):
            err(f"{skill.relative_to(ROOT)}: {problem}")
        fm = frontmatter(skill)
        if fm is None:
            err(f"{skill.relative_to(ROOT)}: no YAML frontmatter")
            continue
        name = fm.get("name", "")
        desc = fm.get("description", "")
        if not name:
            err(f"{skill.relative_to(ROOT)}: frontmatter has no name")
        elif name != d.name:
            err(f"{skill.relative_to(ROOT)}: name {name!r} must equal directory name {d.name!r}")
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name or "x") or len(name) > 64:
            err(f"{skill.relative_to(ROOT)}: name must be lowercase letters, digits and single hyphens, at most 64 chars")
        if not desc:
            err(f"{skill.relative_to(ROOT)}: frontmatter has no description")
        elif len(desc) > 1024:
            err(f"{skill.relative_to(ROOT)}: description is {len(desc)} chars (max 1024)")
        if "compatibility" in fm and len(fm["compatibility"]) > 500:
            err(f"{skill.relative_to(ROOT)}: compatibility over 500 chars")
        body = skill.read_text(encoding="utf-8")
        if body.count("\n") > 500:
            warn(f"{skill.relative_to(ROOT)}: over 500 lines; move detail into references/")
        for link in re.findall(r"\]\(([^)#]+)\)", body):
            if link.startswith(("http://", "https://", "mailto:")) or "${" in link:
                continue
            if not (d / link).exists():
                err(f"{skill.relative_to(ROOT)}: link target does not exist: {link}")
        names.append(name)
    return names


def check_commands_and_agents(plugin: Path) -> list[str]:
    commands: list[str] = []
    cdir = plugin / "commands"
    if cdir.is_dir():
        for f in sorted(cdir.rglob("*.md")):
            fm = frontmatter(f)
            if fm is None or not fm.get("description"):
                err(f"{f.relative_to(ROOT)}: command needs frontmatter with a description")
            commands.append(f.stem)
    adir = plugin / "agents"
    if adir.is_dir():
        for f in sorted(adir.rglob("*.md")):
            fm = frontmatter(f)
            if fm is None or not fm.get("name") or not fm.get("description"):
                err(f"{f.relative_to(ROOT)}: agent needs frontmatter with name and description")
                continue
            if ":" in fm["name"] or fm["name"].startswith("-"):
                err(f"{f.relative_to(ROOT)}: invalid agent name {fm['name']!r}")
            for ignored in ("permissionMode", "mcpServers", "initialPrompt"):
                if ignored in fm:
                    warn(f"{f.relative_to(ROOT)}: {ignored} is ignored in plugin agents")
    return commands


def resolve_plugin_path(raw: str, plugin: Path) -> Path | None:
    if "${CLAUDE_PLUGIN_ROOT}" not in raw:
        return None
    rest = raw.replace("${CLAUDE_PLUGIN_ROOT}", "").strip('"').lstrip("/")
    return plugin / rest


def check_hooks(plugin: Path, parsed: dict[Path, object]) -> None:
    hooks_file = plugin / "hooks" / "hooks.json"
    if not hooks_file.exists():
        return
    data = parsed.get(hooks_file)
    if not isinstance(data, dict) or "hooks" not in data or not isinstance(data["hooks"], dict):
        err(f"{hooks_file.relative_to(ROOT)}: must be an object with a top-level \"hooks\" key")
        return
    for event, matchers in data["hooks"].items():
        if not isinstance(matchers, list):
            err(f"{hooks_file.relative_to(ROOT)}: {event} must be a list")
            continue
        for matcher in matchers:
            for h in matcher.get("hooks", []):
                if h.get("type") != "command":
                    continue
                command = h.get("command", "")
                args = h.get("args") or []
                candidates = [command] + list(args)
                found_script = False
                for c in candidates:
                    p = resolve_plugin_path(str(c), plugin)
                    if p is None:
                        continue
                    found_script = True
                    if not p.exists():
                        err(f"{hooks_file.relative_to(ROOT)}: {event} hook references missing file {p.relative_to(ROOT)}")
                if not found_script and not args:
                    warn(f"{hooks_file.relative_to(ROOT)}: {event} hook does not reference ${{CLAUDE_PLUGIN_ROOT}}: {command}")
                if not args and "${CLAUDE_PLUGIN_ROOT}" in command and not re.search(r"\"\$\{CLAUDE_PLUGIN_ROOT\}[^\"]*\"", command):
                    warn(f"{hooks_file.relative_to(ROOT)}: shell-form hook should quote ${{CLAUDE_PLUGIN_ROOT}}")


def check_mcp(plugin: Path, parsed: dict[Path, object]) -> None:
    mcp = plugin / ".mcp.json"
    if not mcp.exists():
        return
    data = parsed.get(mcp)
    if not isinstance(data, dict):
        return
    servers = data.get("mcpServers", data)
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            err(f".mcp.json: server {name} must be an object")
            continue
        if "url" in cfg:
            err(f".mcp.json: server {name} is remote; this plugin declares stdio servers only")
        for a in [cfg.get("command", "")] + list(cfg.get("args") or []) + list((cfg.get("env") or {}).values()):
            p = resolve_plugin_path(str(a), plugin)
            if p is None:
                continue
            if not p.exists():
                if "dist" in p.parts:
                    warn(f".mcp.json: server {name} references {p.relative_to(ROOT)} which does not exist yet (run npm install && npm run build in mcp/incidents-server)")
                else:
                    err(f".mcp.json: server {name} references missing file {p.relative_to(ROOT)}")


def check_readme(skills: list[str]) -> None:
    readme = ROOT / "README.md"
    if not readme.exists():
        err("README.md missing")
        return
    text = readme.read_text(encoding="utf-8")
    for s in skills:
        if f"`{s}`" not in text:
            err(f"README.md does not mention skill `{s}`")
    for needle in ("/plugin marketplace add basitalisandhu/agent-security-skills", "/plugin install agent-security@agent-security-skills"):
        if needle not in text:
            err(f"README.md is missing the install command {needle!r}")


def check_style() -> None:
    for p in sorted(ROOT.rglob("*.md")):
        if "node_modules" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        em_dash = chr(0x2014)
        if em_dash in text:
            line = text[: text.index(em_dash)].count("\n") + 1
            err(f"{p.relative_to(ROOT)}:{line}: em-dash found (house style forbids it)")


def check_dataset() -> None:
    data_file = ROOT / "plugins" / "agent-security" / "data" / "incidents.json"
    if not data_file.exists():
        err("bundled dataset missing: plugins/agent-security/data/incidents.json")
        return
    data = json.loads(data_file.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        err("incidents.json: must be a non-empty JSON array (a copy of site/incidents.json from ai-agent-incidents)")
        return
    required = {"id", "date", "name", "type", "lens", "vector", "channel_in", "authority", "channel_out", "adversarial",
                "outcome", "cve", "sources", "summary", "mappings", "affected", "tags", "status"}
    for rec in data:
        missing = required - set(rec)
        if missing:
            err(f"incidents.json: record {rec.get('id')} is missing {sorted(missing)}")
        if not isinstance(rec.get("cve"), list) or not isinstance(rec.get("sources"), list) or not rec.get("sources"):
            err(f"incidents.json: record {rec.get('id')} has the wrong shape for cve or sources")
        if set(rec.get("mappings", {})) != {"owasp_agentic", "owasp_llm", "mitre_atlas"}:
            err(f"incidents.json: record {rec.get('id')} mappings must have owasp_agentic, owasp_llm, mitre_atlas")
    ids = [i.get("id") for i in data]
    if len(ids) != len(set(ids)):
        err("incidents.json: duplicate ids")
    if ids != sorted(ids):
        warn("incidents.json: records are not sorted by id")


def main() -> int:
    parsed = check_json_files()
    plugin_roots = check_marketplace(parsed)
    all_skills: list[str] = []
    for plugin in plugin_roots:
        skills = check_skills(plugin)
        all_skills += skills
        commands = check_commands_and_agents(plugin)
        check_hooks(plugin, parsed)
        check_mcp(plugin, parsed)
        print(f"{plugin.relative_to(ROOT)}: {len(skills)} skills, {len(commands)} commands")
    check_readme(all_skills)
    check_style()
    check_dataset()
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
