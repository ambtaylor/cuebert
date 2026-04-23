#!/usr/bin/env python3
"""
Generate module-dependency-map.json from Unreal Engine project files.
Parses .Build.cs (PublicDependencyModuleNames, PrivateDependencyModuleNames)
and .uplugin (Plugins[].Name) to build an import graph.

Usage: module_dep_scan.py <source_root> [--project <name>]
Output: JSON on stdout with the same envelope pattern as python_ast_map.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_DEP_PATTERN = re.compile(
    r'(?:Public|Private)DependencyModuleNames'
    r'\s*\.(?:AddRange|Add)\s*\('
    r'(?:\s*new\s*string\s*\[\s*\]\s*\{)?'
    r'([^)};]+)',
    re.DOTALL,
)

_STRING_LITERAL = re.compile(r'"([^"]+)"')


def _module_name_from_build_cs(path: Path) -> str:
    """Unreal module id from e.g. MyModule.Build.cs — not Path.stem, which yields MyModule.Build."""
    if path.name.endswith(".Build.cs"):
        return path.name[: -len(".Build.cs")]
    return path.stem


def _find_files(root: Path, ext: str) -> Iterable[Path]:
    skip = {".git", "Intermediate", "Binaries", "Saved", "DerivedDataCache"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if name.endswith(ext):
                yield Path(dirpath) / name


def _parse_build_cs(path: Path) -> dict[str, Any]:
    """Extract module name and dependencies from a .Build.cs file."""
    module_name = _module_name_from_build_cs(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"module": module_name, "public_deps": [], "private_deps": [], "path": str(path)}

    public_deps: list[str] = []
    private_deps: list[str] = []

    for match in _DEP_PATTERN.finditer(text):
        block = match.group(0)
        deps = _STRING_LITERAL.findall(match.group(1))
        if "PublicDependencyModuleNames" in block:
            public_deps.extend(deps)
        else:
            private_deps.extend(deps)

    return {
        "module": module_name,
        "public_deps": sorted(set(public_deps)),
        "private_deps": sorted(set(private_deps)),
        "path": str(path),
    }


def _parse_uplugin(path: Path) -> list[dict[str, str]]:
    """Extract plugin dependencies from a .uplugin file."""
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return []

    plugins = data.get("Plugins", [])
    deps = []
    for p in plugins:
        if isinstance(p, dict):
            name = p.get("Name")
            if name:
                deps.append({"name": name, "enabled": p.get("Enabled", True)})
    return deps


def build_module_graph(root: Path, project_name: str) -> dict[str, Any]:
    modules: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    plugin_deps: list[dict[str, Any]] = []

    for build_cs in _find_files(root, ".Build.cs"):
        info = _parse_build_cs(build_cs)
        rel_path = str(build_cs.relative_to(root)) if build_cs.is_relative_to(root) else str(build_cs)
        modules.append({
            "path": rel_path,
            "module": info["module"],
            "public_deps": info["public_deps"],
            "private_deps": info["private_deps"],
        })
        for dep in info["public_deps"] + info["private_deps"]:
            key = (info["module"], dep)
            if key not in seen_edges:
                seen_edges.add(key)
                dep_type = "public" if dep in info["public_deps"] else "private"
                edges.append({"from": info["module"], "to": dep, "type": dep_type})

    for uplugin in _find_files(root, ".uplugin"):
        plugin_name = uplugin.stem
        deps = _parse_uplugin(uplugin)
        rel_path = str(uplugin.relative_to(root)) if uplugin.is_relative_to(root) else str(uplugin)
        plugin_deps.append({
            "path": rel_path,
            "plugin": plugin_name,
            "dependencies": deps,
        })
        for dep in deps:
            if dep.get("enabled", True):
                key = (plugin_name, dep["name"])
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"from": plugin_name, "to": dep["name"], "type": "plugin"})

    return {
        "generated_at": _iso_now(),
        "tool": "ue-module-dep-scan",
        "project": project_name,
        "summary": {
            "modules": len(modules),
            "plugins": len(plugin_deps),
            "edges": len(edges),
        },
        "modules": modules,
        "plugins": plugin_deps,
        "edges": edges,
    }


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage: module_dep_scan.py <source_root> [--project <name>]\n"
            "  Scans .Build.cs and .uplugin files under <source_root>.\n"
            "  Output: module-dependency-map.json on stdout.",
            file=sys.stderr,
        )
        sys.exit(2 if not args else 0)

    root = Path(args[0]).resolve()
    project_name = root.name

    i = 1
    while i < len(args):
        if args[i] == "--project" and i + 1 < len(args):
            project_name = args[i + 1]
            i += 2
        else:
            i += 1

    data = build_module_graph(root, project_name)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
