"""MCP tool: memory_eval — Benchmark milestone precision and troubleshooting recall."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from _memory_db import (
    _get_memory_mode,
    cosine_similarity,
    generate_embedding,
    get_db,
    hybrid_search,
)
from milestone_lookup import _build_bridge

logger = logging.getLogger(__name__)

EVAL_MILESTONES: list[dict[str, Any]] = [
    {
        "plan_slug": "__eval_test__plan_alpha",
        "milestone": "M1",
        "phase": "code",
        "status": "success",
        "files_touched": '["src/foo.ts", "src/bar.ts"]',
        "deferred_items": (
            '[{"item": "accessibility polish", "target_milestone": "M2", '
            '"severity": "WARN"}]'
        ),
        "decisions": (
            '[{"decision": "Used React context instead of Redux", '
            '"rationale": "Simpler for 2 components"}]'
        ),
        "summary": "Implemented core feature with 2 components",
        "project": "eval-project",
    },
    {
        "plan_slug": "__eval_test__plan_alpha",
        "milestone": "M2",
        "phase": "code",
        "status": "success",
        "files_touched": '["src/baz.ts"]',
        "deferred_items": "[]",
        "decisions": (
            '[{"decision": "Added aria labels", '
            '"rationale": "Picked up from M1 deferral"}]'
        ),
        "summary": "Accessibility polish from M1 deferral",
        "project": "eval-project",
    },
    {
        "plan_slug": "__eval_test__plan_beta",
        "milestone": "M1",
        "phase": "spec",
        "status": "success",
        "summary": "Spec for beta plan",
        "project": "eval-project",
    },
]

EVAL_TROUBLESHOOTING: list[dict[str, Any]] = [
    {
        "problem": (
            "vitest ESM resolution fails with 'Cannot find module' for .ts files"
        ),
        "what_tried": [
            {
                "approach": "Upgraded vitest to 3.x",
                "outcome": "Same error persists",
            },
            {
                "approach": "Added extensionsToTreatAsEsm in jest config",
                "outcome": "Wrong config file",
            },
            {
                "approach": "Mocked the ESM module with vi.mock",
                "outcome": "Tests pass but types break",
            },
        ],
        "why_tried": (
            "Error looked like ESM/CJS interop issue, tried version and config fixes first"
        ),
        "what_worked": (
            "Circular import in utils.ts caused resolution failure. "
            "Refactored to lazy import."
        ),
        "tags": "vitest,esm,circular-import,typescript,eval-test",
    },
    {
        "problem": (
            "FastAPI endpoint returns 422 Unprocessable Entity on valid JSON payload"
        ),
        "what_tried": [
            {
                "approach": "Checked Content-Type header",
                "outcome": "Already application/json",
            },
            {
                "approach": "Validated payload against Pydantic model manually",
                "outcome": "Model accepts it fine",
            },
            {
                "approach": "Added print debugging in endpoint",
                "outcome": "Request body is empty",
            },
        ],
        "why_tried": (
            "422 usually means validation failure, but payload was valid. "
            "Suspected middleware."
        ),
        "what_worked": (
            "CORS middleware was consuming the request body before FastAPI "
            "could parse it. Reordered middleware."
        ),
        "tags": "fastapi,422,cors,middleware,pydantic,eval-test",
    },
    {
        "problem": (
            "React component re-renders infinitely when using useEffect with object dependency"
        ),
        "what_tried": [
            {
                "approach": "Wrapped object in useMemo",
                "outcome": "Fixed the infinite loop",
            },
        ],
        "why_tried": (
            "Object reference changes on every render, triggering useEffect repeatedly"
        ),
        "what_worked": (
            "useMemo stabilized the object reference. Also considered useRef "
            "for truly static objects."
        ),
        "tags": "react,useEffect,infinite-loop,useMemo,performance,eval-test",
    },
]

EVAL_TROUBLESHOOTING_IDS = (
    "__eval_test__ts_vitest",
    "__eval_test__ts_fastapi",
    "__eval_test__ts_react",
)

EVAL_QUERIES: list[dict[str, Any]] = [
    {
        "query": "vitest cannot resolve typescript module",
        "expected_match_tag": "vitest",
    },
    {
        "query": "FastAPI 422 error even with correct JSON",
        "expected_match_tag": "fastapi",
    },
    {
        "query": "React component keeps re-rendering in a loop",
        "expected_match_tag": "react",
    },
    {
        "query": "Angular NgRx selector not updating",
        "expected_match_tag": None,
    },
]


def _cleanup_eval(conn: Any) -> None:
    conn.execute(
        "DELETE FROM milestones WHERE plan_slug LIKE ?",
        ("__eval_test__%",),
    )
    conn.execute(
        "DELETE FROM troubleshooting WHERE IFNULL(tags, '') LIKE ?",
        ("%eval-test%",),
    )
    conn.commit()


def _fetch_sessions(
    conn: Any,
    plan_slug: str,
    milestone: str | None = None,
) -> list[dict[str, Any]]:
    if milestone:
        cur = conn.execute(
            """
            SELECT * FROM milestones
            WHERE plan_slug = ? AND milestone = ?
            ORDER BY created_at
            """,
            (plan_slug, milestone),
        )
    else:
        cur = conn.execute(
            """
            SELECT * FROM milestones
            WHERE plan_slug = ?
            ORDER BY created_at
            """,
            (plan_slug,),
        )
    return [dict(r) for r in cur.fetchall()]


def _seed_milestones(conn: Any) -> None:
    for i, m in enumerate(EVAL_MILESTONES):
        created = f"2024-01-0{1 + i} 12:00:00"
        conn.execute(
            """
            INSERT OR REPLACE INTO milestones (
              id, plan_slug, milestone, project, language, agent, phase,
              status, files_touched, deferred_items, decisions, summary,
              errors_encountered, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                m["plan_slug"],
                m["milestone"],
                m.get("project"),
                None,
                None,
                m["phase"],
                m.get("status"),
                m.get("files_touched"),
                m.get("deferred_items"),
                m.get("decisions"),
                m.get("summary"),
                None,
                created,
            ),
        )
    conn.commit()


def _seed_troubleshooting(conn: Any) -> None:
    day = date.today().isoformat()
    for rid, row in zip(EVAL_TROUBLESHOOTING_IDS, EVAL_TROUBLESHOOTING):
        wt_json = json.dumps(row["what_tried"], ensure_ascii=False)
        embed_text = "\n\n".join(
            part
            for part in (
                row["problem"],
                wt_json,
                row.get("why_tried") or "",
                row.get("what_worked") or "",
            )
            if part
        )
        blob = generate_embedding(embed_text)
        if blob is None:
            raise ValueError("generate_embedding returned None in hybrid troubleshooting eval.")
        if cosine_similarity(blob, blob) < 0.99:
            raise ValueError("embedding self-similarity sanity check failed")
        conn.execute(
            """
            INSERT OR REPLACE INTO troubleshooting (
              id, date, project, agent, language, problem, what_tried,
              why_tried, what_worked, tags, errors, files_touched,
              plan_slug, milestone, transcript_id, source, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                day,
                "eval-project",
                None,
                None,
                row["problem"],
                wt_json,
                row.get("why_tried"),
                row.get("what_worked"),
                row["tags"],
                None,
                None,
                None,
                None,
                None,
                "agent",
                blob,
            ),
        )
    conn.commit()


def _run_milestone_eval(conn: Any) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    passed = 0
    total = 0

    def check(name: str, ok: bool) -> None:
        nonlocal passed, total
        total += 1
        if ok:
            passed += 1
        details.append({"assertion": name, "passed": ok})

    rows_m1 = _fetch_sessions(conn, "__eval_test__plan_alpha", "M1")
    r0 = rows_m1[0] if rows_m1 else {}
    check(
        "milestone_lookup(plan_alpha, M1) single row with expected phase/summary",
        len(rows_m1) == 1
        and r0.get("milestone") == "M1"
        and r0.get("phase") == "code"
        and r0.get("summary") == "Implemented core feature with 2 components",
    )

    alpha_all = _fetch_sessions(conn, "__eval_test__plan_alpha")
    ms_order = [r.get("milestone") for r in alpha_all]
    check(
        "milestone_lookup(plan_alpha) all milestones ordered by created_at",
        len(alpha_all) == 2 and ms_order == ["M1", "M2"],
    )

    bridge = _build_bridge(alpha_all) if alpha_all else {}
    deferred = bridge.get("deferred_items") or []
    has_defer = any(
        isinstance(d, dict) and d.get("item") == "accessibility polish"
        for d in deferred
    )
    check(
        "bridge aggregates deferred_items across milestones",
        has_defer,
    )

    ghost = _fetch_sessions(conn, "__eval_test__nonexistent_plan_xyz")
    check("non-existent plan_slug returns empty sessions", ghost == [])

    return {"passed": passed, "total": total, "details": details}


def register(mcp: FastMCP) -> None:
    """Register memory_eval on the MCP server."""

    @mcp.tool()
    def memory_eval(clean: bool = True) -> dict[str, Any]:
        """Benchmark recall quality for milestone (exact) and troubleshooting (fuzzy) tables."""
        note: str | None = None
        try:
            conn = get_db()
            try:
                if clean:
                    _cleanup_eval(conn)

                _seed_milestones(conn)
                ms_summary = _run_milestone_eval(conn)

                troubleshooting_recall: dict[str, Any] | None = None
                if _get_memory_mode() != "hybrid":
                    note = (
                        "Troubleshooting eval skipped: CUEBERT_MEMORY_MODE=text "
                        "(embedding-based semantic recall benchmark requires hybrid mode)."
                    )
                    troubleshooting_recall = None
                elif not os.environ.get("OPENAI_API_KEY"):
                    note = (
                        "Troubleshooting eval skipped: OPENAI_API_KEY is not set "
                        "(embeddings required)."
                    )
                    troubleshooting_recall = None
                else:
                    _seed_troubleshooting(conn)
                    query_results: list[dict[str, Any]] = []
                    positive_hits = 0
                    positive_total = 0
                    for spec in EVAL_QUERIES:
                        q = str(spec["query"]).strip()
                        exp = spec.get("expected_match_tag")
                        q_emb = generate_embedding(q)
                        rows = hybrid_search(conn, q, q_emb, {"tags": "eval-test"}, 3)
                        top3 = (rows + [{}, {}, {}])[:3]
                        top3_tags = [
                            str(x.get("tags") or "") for x in top3
                        ]
                        top1_score = float(rows[0]["hybrid_score"]) if rows else 0.0
                        if exp:
                            positive_total += 1
                            tag_lc = str(exp).lower()
                            found = any(
                                tag_lc in (t or "").lower() for t in top3_tags
                            )
                            if found:
                                positive_hits += 1
                            found_in_top3 = found
                        else:
                            found_in_top3 = False
                        query_results.append(
                            {
                                "query": q,
                                "expected_tag": exp,
                                "found_in_top3": found_in_top3,
                                "top3_tags": top3_tags,
                                "top1_score": top1_score,
                            },
                        )
                    recall = (
                        positive_hits / positive_total if positive_total else 0.0
                    )
                    troubleshooting_recall = {
                        "recall_at_3": recall,
                        "queries": query_results,
                    }

                if clean:
                    _cleanup_eval(conn)
            finally:
                conn.close()

            out: dict[str, Any] = {
                "status": "ok",
                "milestone_precision": {
                    "passed": ms_summary["passed"],
                    "total": ms_summary["total"],
                    "details": ms_summary["details"],
                },
                "troubleshooting_recall": troubleshooting_recall,
                "weights": {"vector": 0.6, "fts": 0.4},
                "clean": clean,
            }
            if note:
                out["note"] = note
            logger.info(
                "memory_eval: milestone %s/%s clean=%s",
                ms_summary["passed"],
                ms_summary["total"],
                clean,
            )
            return out
        except Exception as exc:
            logger.error("memory_eval failed: %s", exc, exc_info=True)
            return {"status": "error", "error": str(exc)}
