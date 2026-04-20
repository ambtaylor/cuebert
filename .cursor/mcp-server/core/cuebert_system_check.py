"""MCP tool: Cuebert system integrity check.

Validates the Cuebert hub workspace across 5 categories:
  1. Hub Structure — required directories and files exist
  2. MCP Connectivity — server.py parseable, tools discoverable, mcp.json valid
  3. Vault Resolution — services.yaml valid, credential tiers exist, resolver works
  4. Registry Consistency — skills on disk match registry; optional rule registry
  5. Cross-References — no stale paths in agents, standards, or rules

All checks are read-only. No files are modified.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

from _vault import CUEBERT_VAULT_AVAILABLE, find_cuebert_root

_HUB_ROOT = find_cuebert_root(Path(__file__).resolve().parent)

_STATUS_PASS = "pass"
_STATUS_WARN = "warn"
_STATUS_FAIL = "fail"

_STALE_PATH_PATTERNS = [
    (re.compile(r"scripts/tools/"), "scripts/tools/ → .cursor/skills/*/tools/"),
]

_HUB_REQUIRED_DIRS = [
    ".cuebert",
    ".cuebert/registry",
    "registry",
    ".cursor/mcp-server",
    ".cursor/mcp-server/core",
    ".cursor/mcp-server/lib",
]

_HUB_REQUIRED_FILES = [
    ".cuebert/workspace-manifest.json",
    ".cuebert/registry/skills.yaml",
    "registry/services.yaml",
    ".cursor/mcp-server/server.py",
    ".cursor/mcp-server/lib/_vault.py",
]

# Hub ``.cursor/mcp.json``: split Cuebert MCP processes (one per ``--group``).
_EXPECTED_CUEBERT_MCP_SERVERS: dict[str, str] = {
    "cuebert-core": "core",
    "cuebert-asset": "asset",
    "cuebert-engine": "engine",
    "cuebert-qa": "qa",
}


def _mcp_server_py_group(args: list[Any]) -> str | None:
    """Return the ``--group`` value when ``server.py`` appears in args, else ``None``."""
    args_str = [str(a) for a in args]
    if not any("server.py" in a for a in args_str):
        return None
    try:
        i = args_str.index("--group")
    except ValueError:
        return None
    if i + 1 < len(args_str):
        return args_str[i + 1]
    return None


def _check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "status": _STATUS_PASS if passed else _STATUS_FAIL,
        "detail": detail,
    }


def _warn(name: str, detail: str) -> dict[str, Any]:
    return {"name": name, "status": _STATUS_WARN, "detail": detail}


def _worst(checks: list[dict]) -> str:
    statuses = {c["status"] for c in checks}
    if _STATUS_FAIL in statuses:
        return _STATUS_FAIL
    if _STATUS_WARN in statuses:
        return _STATUS_WARN
    return _STATUS_PASS


def _load_hub_manifest() -> dict[str, Any] | None:
    path = _HUB_ROOT / ".cuebert" / "workspace-manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _check_manifest_projects() -> dict:
    """Validate ``projects`` entries from workspace-manifest.json (paths on disk)."""
    checks: list[dict] = []
    data = _load_hub_manifest()
    if data is None:
        checks.append(_warn(
            "manifest:workspace-manifest.json",
            ".cuebert/workspace-manifest.json missing or invalid JSON",
        ))
        return {"status": _worst(checks), "checks": checks}

    projects = data.get("projects")
    if projects is None:
        checks.append(_check("manifest:projects-key", False, "Missing 'projects' key"))
        return {"status": _worst(checks), "checks": checks}

    if not isinstance(projects, dict):
        checks.append(_check("manifest:projects-type", False, "'projects' must be an object"))
        return {"status": _worst(checks), "checks": checks}

    if not projects:
        checks.append(_check(
            "manifest:projects-empty",
            True,
            "No onboarded projects (empty map is valid).",
        ))
        return {"status": _worst(checks), "checks": checks}

    for key, spec in projects.items():
        path_str: str | None = None
        if isinstance(spec, str):
            path_str = spec
        elif isinstance(spec, dict):
            raw = spec.get("path") or spec.get("root") or spec.get("directory")
            if isinstance(raw, str):
                path_str = raw
        if not path_str:
            checks.append(_warn(
                f"manifest:project:{key}",
                "Entry has no resolvable path field (expected string or object.path).",
            ))
            continue
        p = Path(path_str)
        if not p.is_absolute():
            p = (_HUB_ROOT / path_str).resolve()
        checks.append(_check(
            f"manifest:project:{key}:path",
            p.exists(),
            "" if p.exists() else f"Project path does not exist: {p}",
        ))

    return {"status": _worst(checks), "checks": checks}


def _check_hub_structure() -> dict:
    checks: list[dict] = []

    for rel in _HUB_REQUIRED_DIRS:
        p = _HUB_ROOT / rel
        checks.append(_check(f"dir:{rel}", p.is_dir(), "" if p.is_dir() else f"Missing directory: {rel}"))

    for rel in _HUB_REQUIRED_FILES:
        p = _HUB_ROOT / rel
        checks.append(_check(f"file:{rel}", p.is_file(), "" if p.is_file() else f"Missing file: {rel}"))

    mp = _check_manifest_projects()
    checks.extend(mp.get("checks", []))

    return {"status": _worst(checks), "checks": checks}


def _check_mcp_connectivity() -> dict:
    checks: list[dict] = []

    server_py = _HUB_ROOT / ".cursor" / "mcp-server" / "server.py"
    if server_py.is_file():
        try:
            ast.parse(server_py.read_text(encoding="utf-8"))
            checks.append(_check("server.py:syntax", True))
        except SyntaxError as exc:
            checks.append(_check("server.py:syntax", False, f"Syntax error: {exc}"))
    else:
        checks.append(_check("server.py:exists", False, "server.py not found"))

    core_dir = _HUB_ROOT / ".cursor" / "mcp-server" / "core"
    if core_dir.is_dir():
        core_tools = [f for f in core_dir.glob("*.py") if not f.name.startswith("_")]
        for tool_file in core_tools:
            try:
                tree = ast.parse(tool_file.read_text(encoding="utf-8"))
                has_register = any(
                    isinstance(node, ast.FunctionDef) and node.name == "register"
                    for node in ast.walk(tree)
                )
                checks.append(_check(
                    f"core/{tool_file.name}:register",
                    has_register,
                    "" if has_register else f"{tool_file.name} missing register() function",
                ))
            except SyntaxError as exc:
                checks.append(_check(f"core/{tool_file.name}:syntax", False, str(exc)))

    skills_dir = _HUB_ROOT / ".cursor" / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.name.startswith("_") or not skill_dir.is_dir():
                continue
            tools_dir = skill_dir / "tools"
            if not tools_dir.is_dir():
                continue
            for tool_file in tools_dir.glob("*.py"):
                if tool_file.name.startswith("_"):
                    continue
                try:
                    tree = ast.parse(tool_file.read_text(encoding="utf-8"))
                    has_register = any(
                        isinstance(node, ast.FunctionDef) and node.name == "register"
                        for node in ast.walk(tree)
                    )
                    checks.append(_check(
                        f"skills/{skill_dir.name}/{tool_file.name}:register",
                        has_register,
                        "" if has_register else f"{tool_file.name} missing register()",
                    ))
                except SyntaxError as exc:
                    checks.append(_check(
                        f"skills/{skill_dir.name}/{tool_file.name}:syntax",
                        False, str(exc),
                    ))

    mcp_json = _HUB_ROOT / ".cursor" / "mcp.json"
    if mcp_json.is_file():
        try:
            data = json.loads(mcp_json.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            split_ok = True
            for srv_name, expected_group in _EXPECTED_CUEBERT_MCP_SERVERS.items():
                cfg = servers.get(srv_name) if isinstance(servers, dict) else None
                if not isinstance(cfg, dict):
                    checks.append(_check(
                        f"mcp.json:{srv_name}:present",
                        False,
                        f"missing mcpServers entry for {srv_name}",
                    ))
                    split_ok = False
                    continue
                args = cfg.get("args", [])
                if not any("server.py" in str(a) for a in args):
                    checks.append(_check(
                        f"mcp.json:{srv_name}:server.py",
                        False,
                        f"{srv_name} args must invoke .cursor/mcp-server/server.py",
                    ))
                    split_ok = False
                    continue
                got = _mcp_server_py_group(args)
                group_match = got == expected_group
                checks.append(_check(
                    f"mcp.json:{srv_name}:--group",
                    group_match,
                    "" if group_match else (
                        f"expected --group {expected_group}, got {got!r}"
                    ),
                ))
                if not group_match:
                    split_ok = False
            checks.append(_check(
                "mcp.json:split-cuebert-mcp-servers",
                split_ok,
                "" if split_ok else (
                    "cuebert-core / cuebert-asset / cuebert-engine / cuebert-qa must each "
                    "call server.py with matching --group"
                ),
            ))
            for name, cfg in servers.items():
                if "server.py" not in str(cfg.get("args", [])):
                    continue
                args = cfg.get("args", [])
                cmd = cfg.get("command", "")
                has_abs_args = all(
                    str(a).startswith("/") for a in args if "server.py" in str(a)
                )
                checks.append(_check(
                    f"mcp.json:{name}:absolute-args",
                    has_abs_args,
                    "" if has_abs_args else (
                        "args contains relative path — Cursor ignores cwd; "
                        "use absolute paths to prevent connection failures"
                    ),
                ))
                has_abs_cmd = str(cmd).startswith("/")
                checks.append(_check(
                    f"mcp.json:{name}:absolute-command",
                    has_abs_cmd,
                    "" if has_abs_cmd else (
                        f"command '{cmd}' is not an absolute path — "
                        "may fail if not on Cursor's PATH"
                    ),
                ))
                has_cwd = "cwd" in cfg
                checks.append(_check(
                    f"mcp.json:{name}:no-unsupported-cwd",
                    not has_cwd,
                    "" if not has_cwd else (
                        "cwd field is not supported by Cursor MCP — "
                        "remove it and use absolute paths instead"
                    ),
                ))
        except (json.JSONDecodeError, OSError) as exc:
            checks.append(_check("mcp.json:parse", False, str(exc)))
    else:
        checks.append(_warn("mcp.json:exists", ".cursor/mcp.json not found (optional until configured)"))

    return {"status": _worst(checks), "checks": checks}


def _check_vault_resolution() -> dict:
    checks: list[dict] = []

    services_yaml = _HUB_ROOT / "registry" / "services.yaml"
    if services_yaml.is_file():
        try:
            data = yaml.safe_load(services_yaml.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "services" in data:
                svc_count = len(data["services"])
                checks.append(_check("services.yaml:valid", True, f"{svc_count} services defined"))
            else:
                checks.append(_check("services.yaml:schema", False, "Missing 'services' key"))
        except yaml.YAMLError as exc:
            checks.append(_check("services.yaml:parse", False, str(exc)))
    else:
        checks.append(_check("services.yaml:exists", False, "registry/services.yaml not found"))

    hub_vault = _HUB_ROOT / ".cuebert" / "vault"
    if hub_vault.is_dir():
        shared = hub_vault / "shared"
        if shared.is_dir():
            cred_files = list(shared.glob("*.yaml")) + list(shared.glob("*.yml"))
            checks.append(_check(
                "vault:shared-tier",
                len(cred_files) > 0,
                f"{len(cred_files)} credential file(s)" if cred_files else "No credential files in shared/",
            ))
        else:
            checks.append(_warn("vault:shared-tier", ".cuebert/vault/shared/ does not exist"))
    else:
        checks.append(_warn("vault:hub-dir", ".cuebert/vault/ does not exist"))

    if CUEBERT_VAULT_AVAILABLE:
        try:
            lib_dir = _HUB_ROOT / "lib"
            if str(lib_dir) not in sys.path:
                sys.path.insert(0, str(lib_dir))
            import cuebert_vault  # noqa: F401

            checks.append(_check("vault:resolver-import", True))
        except ImportError as exc:
            checks.append(_check("vault:resolver-import", False, f"Cannot import cuebert_vault: {exc}"))
    else:
        checks.append(_warn(
            "vault:resolver-import",
            "cuebert_vault not installed under hub lib/ (deferred per M1 plan).",
        ))

    return {"status": _worst(checks), "checks": checks}


def _resolve_skill_md(skill_path: str) -> Path:
    """Resolve a skill_path from skills.yaml to an on-disk path."""
    p = Path(skill_path)
    if p.is_absolute():
        return p
    return (_HUB_ROOT / skill_path).resolve()


def _check_registry_consistency() -> dict:
    checks: list[dict] = []

    registry_path = _HUB_ROOT / "docs" / "_ai_system" / "rule_registry.md"
    if registry_path.is_file():
        content = registry_path.read_text(encoding="utf-8", errors="replace")

        agent_pattern = re.compile(
            r"`(docs/_ai_system/agents/[a-zA-Z0-9_-]+\.md)`"
            r"|`(agent-[a-zA-Z0-9_-]+\.md)`"
        )
        agents_dir = _HUB_ROOT / "docs" / "_ai_system" / "agents"

        for match in agent_pattern.finditer(content):
            ref = match.group(1) or match.group(2)
            if ref.startswith("docs/"):
                agent_file = _HUB_ROOT / ref
            else:
                agent_file = agents_dir / ref

            checks.append(_check(
                f"registry-agent:{agent_file.name}",
                agent_file.is_file(),
                "" if agent_file.is_file() else f"Registered agent not found on disk: {ref}",
            ))
    else:
        checks.append(_warn(
            "rule_registry.md:exists",
            "docs/_ai_system/rule_registry.md not found (optional for early bootstrap)",
        ))

    skills_yaml = _HUB_ROOT / ".cuebert" / "registry" / "skills.yaml"
    if skills_yaml.is_file():
        try:
            data = yaml.safe_load(skills_yaml.read_text(encoding="utf-8"))
            skills = data.get("skills", []) if isinstance(data, dict) else []
            for skill in skills:
                name = skill.get("name", "unknown")
                skill_path = skill.get("skill_path", "")

                if skill_path:
                    resolved = _resolve_skill_md(str(skill_path))
                    checks.append(_check(
                        f"skill:{name}:SKILL.md",
                        resolved.is_file(),
                        "" if resolved.is_file() else f"SKILL.md not found: {skill_path}",
                    ))

                status = skill.get("status", "unknown")
                if status != "active":
                    checks.append(_warn(f"skill:{name}:status", f"Status is '{status}', expected 'active'"))

        except yaml.YAMLError as exc:
            checks.append(_check("skills.yaml:parse", False, str(exc)))
    else:
        checks.append(_warn("skills.yaml:exists", "skills.yaml not found"))

    rules_dir = _HUB_ROOT / ".cursor" / "rules"
    if rules_dir.is_dir():
        for mdc in rules_dir.glob("*.mdc"):
            content = mdc.read_text(encoding="utf-8", errors="replace")
            if "---" in content:
                checks.append(_check(f"rule:{mdc.name}:frontmatter", True))
            else:
                checks.append(_warn(f"rule:{mdc.name}:frontmatter", "Missing YAML frontmatter"))

    return {"status": _worst(checks), "checks": checks}


def _check_cross_references() -> dict:
    checks: list[dict] = []

    scan_dirs = [
        _HUB_ROOT / "docs" / "_ai_system" / "agents",
        _HUB_ROOT / "docs" / "_ai_system" / "standards",
        _HUB_ROOT / ".cursor" / "rules",
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for f in scan_dir.iterdir():
            if not f.is_file() or f.suffix not in (".md", ".mdc"):
                continue

            content = f.read_text(encoding="utf-8", errors="replace")
            rel_name = f.name

            for pattern, suggestion in _STALE_PATH_PATTERNS:
                if pattern.search(content):
                    deprecated_keyword = "DEPRECATED" in content.upper()
                    if deprecated_keyword:
                        continue
                    checks.append(_warn(
                        f"stale-ref:{rel_name}",
                        f"Contains stale path pattern ({pattern.pattern}). {suggestion}",
                    ))

    standards_dir = _HUB_ROOT / "docs" / "_ai_system" / "standards"
    agents_dir = _HUB_ROOT / "docs" / "_ai_system" / "agents"

    std_ref_pattern = re.compile(r"`([a-z_-]+\.md)`")

    if agents_dir.is_dir():
        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text(encoding="utf-8", errors="replace")
            for match in std_ref_pattern.finditer(content):
                ref = match.group(1)
                if ref.startswith("agent-"):
                    target = agents_dir / ref
                elif ref.startswith("project-profile") or ref.endswith("-principles.md") or ref.endswith("-workflow.md") or ref.endswith("-behavior.md") or ref.endswith("-architecture.md") or ref.endswith("-standard.md") or ref.endswith("-protocol.md") or ref.endswith("-toolkit.md"):
                    target = standards_dir / ref
                else:
                    continue

                if not target.is_file():
                    checks.append(_warn(
                        f"xref:{agent_file.name}->{ref}",
                        f"{agent_file.name} references {ref} which does not exist",
                    ))

    if not checks:
        checks.append(_check("cross-refs:clean", True, "No stale references detected"))

    return {"status": _worst(checks), "checks": checks}


def _run_all_checks(
    scope: str,
    verbose: bool,
) -> dict:
    """Execute requested check categories and build the report."""

    categories_map = {
        "hub": ("Hub Structure", _check_hub_structure),
        "mcp": ("MCP Connectivity", _check_mcp_connectivity),
        "vault": ("Vault Resolution", _check_vault_resolution),
        "registry": ("Registry Consistency", _check_registry_consistency),
        "cross-refs": ("Cross-References", _check_cross_references),
    }

    if scope == "all":
        selected = list(categories_map.keys())
    elif scope in categories_map:
        selected = [scope]
    else:
        return {"error": f"Unknown scope: {scope}. Valid: all, {', '.join(categories_map.keys())}"}

    categories: dict[str, dict] = {}
    total_checks = 0
    total_pass = 0
    total_warn = 0
    total_fail = 0

    for key in selected:
        label, fn = categories_map[key]
        result = fn()
        cat_checks = result.get("checks", [])

        if not verbose:
            cat_checks = [c for c in cat_checks if c["status"] != _STATUS_PASS]

        for c in result.get("checks", []):
            total_checks += 1
            if c["status"] == _STATUS_PASS:
                total_pass += 1
            elif c["status"] == _STATUS_WARN:
                total_warn += 1
            else:
                total_fail += 1

        categories[key] = {
            "label": label,
            "status": result["status"],
            "checks": cat_checks,
        }

    overall = _STATUS_FAIL if total_fail > 0 else (_STATUS_WARN if total_warn > 0 else _STATUS_PASS)

    return {
        "status": overall,
        "summary": f"{total_checks} checks: {total_pass} passed, {total_warn} warnings, {total_fail} failures",
        "hub_root": str(_HUB_ROOT),
        "categories": categories,
    }


def register(mcp: FastMCP) -> None:
    """Register system check tools on the given MCP server."""

    @mcp.tool()
    def cuebert_system_check(
        scope: str = "all",
        verbose: bool = False,
    ) -> dict:
        """Run Cuebert system integrity checks.

        Validates the Cuebert hub workspace across 5 categories. All checks
        are read-only — no files are modified. Onboarded application paths
        listed under ``.cuebert/workspace-manifest.json`` ``projects`` are
        validated when present.

        Args:
            scope: Check category to run. One of ``all``, ``hub``,
                ``mcp``, ``vault``, ``registry``, ``cross-refs``.
            verbose: Include passing checks in output. Default is
                failures and warnings only.

        Returns:
            A dict with overall status, summary counts, and per-category
            check results.
        """
        return _run_all_checks(scope, verbose)
