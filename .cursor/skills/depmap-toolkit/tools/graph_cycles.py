#!/usr/bin/env python3
"""Find circular dependencies via strongly connected components (Tarjan).
Ported from Cue's depmap-toolkit for Cuebert.

Accepts JSON on stdin from either python_ast_map or module_dep_scan.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from typing import Any


def edges_to_adj(edges: list[dict[str, Any]]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        f = e.get("from")
        t = e.get("to")
        if f and t:
            adj[f].add(t)
    return dict(adj)


def tarjan_scc(adj: dict[str, set[str]]) -> list[list[str]]:
    """Nontrivial SCCs: size > 1, or singleton with self-edge."""
    idx = [0]
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    sccs: list[list[str]] = []

    def visit(v: str) -> None:
        indices[v] = idx[0]
        lowlink[v] = idx[0]
        idx[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj.get(v, ()):
            if w not in indices:
                visit(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                sccs.append(comp)
            elif len(comp) == 1 and v in adj.get(v, ()):
                sccs.append(comp)

    vertices = set(adj.keys()) | {t for vs in adj.values() for t in vs}
    for v in sorted(vertices):
        if v not in indices:
            visit(v)
    return sccs


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps({"circular": [], "count": 0}))
        return
    data = json.loads(raw)
    if isinstance(data, dict) and "edges" in data:
        adj = edges_to_adj(data["edges"])
    else:
        adj = edges_to_adj([])
    sccs = tarjan_scc(adj)
    out = {"circular": sccs, "count": len(sccs)}
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
