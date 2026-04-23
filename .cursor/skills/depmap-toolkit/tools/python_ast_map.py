#!/usr/bin/env python3
"""
Generate dependency-map.json from Python packages using AST analysis.
Ported from Cue's depmap-toolkit for Cuebert's hub Python layout.

Default src roots for Cuebert: .cursor/mcp-server/ and .cursor/skills/
"""
from __future__ import annotations

import ast
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _py_files(root: Path) -> Iterable[Path]:
    skip = {"venv", ".venv", "__pycache__", ".git", "node_modules", "dist", "build"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if name.endswith(".py"):
                yield Path(dirpath) / name


def _module_name_for_path(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else rel.stem


@dataclass
class ImportCollector(ast.NodeVisitor):
    root: Path
    current: Path
    module: str
    imports: list[dict[str, Any]] = field(default_factory=list)

    def _rel_target(self, level: int, module: str | None) -> str | None:
        if module is None:
            return None
        parts = self.module.split(".")
        if level and parts:
            base = parts[: max(0, len(parts) - level)]
            rest = module.split(".")
            resolved = ".".join(base + rest)
        else:
            resolved = module
        return resolved

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                {
                    "kind": "import",
                    "module": alias.name,
                    "resolved": alias.name.split(".")[0],
                    "line": node.lineno,
                }
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        resolved = self._rel_target(node.level or 0, node.module)
        self.imports.append(
            {
                "kind": "from",
                "module": node.module,
                "resolved": resolved or node.module,
                "line": node.lineno,
            }
        )


def build_graph(root: Path, src_roots: list[Path]) -> dict[str, Any]:
    modules: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()

    for base in src_roots:
        if not base.is_dir():
            continue
        for path in _py_files(base):
            try:
                src = path.read_text(encoding="utf-8")
                tree = ast.parse(src, filename=str(path))
            except (OSError, SyntaxError):
                continue
            mod = _module_name_for_path(root, path)
            col = ImportCollector(root=root, current=path, module=mod)
            col.visit(tree)
            modules.append(
                {
                    "path": str(path.relative_to(root)),
                    "module": mod,
                    "imports": col.imports,
                }
            )
            for imp in col.imports:
                tgt = imp.get("resolved")
                if not tgt:
                    continue
                key = (mod, tgt)
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges.append({"from": mod, "to": tgt, "line": imp.get("line", 0)})

    return {
        "generated_at": _iso_now(),
        "tool": "python-ast-map",
        "project": root.name,
        "summary": {
            "modules": len(modules),
            "edges": len(edges),
        },
        "modules": modules,
        "edges": edges,
    }


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage: python_ast_map.py <project_root> [src_dir ...]\n"
            "  Cuebert defaults: .cursor/mcp-server .cursor/skills\n"
            "  Output: dependency-map.json on stdout.",
            file=sys.stderr,
        )
        sys.exit(2 if not args else 0)

    root = Path(args[0]).resolve()
    if len(args) > 1:
        srcs = [root / p for p in args[1:]]
    else:
        cuebert_defaults = [root / ".cursor" / "mcp-server", root / ".cursor" / "skills"]
        srcs = [d for d in cuebert_defaults if d.is_dir()]
        if not srcs:
            default_src = root / "src"
            srcs = [default_src] if default_src.is_dir() else [root]

    data = build_graph(root, srcs)
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
