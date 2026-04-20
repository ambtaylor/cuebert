"""MCP tool: submit a ComfyUI workflow, poll for completion, and persist outputs."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from _comfyui_client import (
    _get_mode,
    _list_local_workflows,
    _resolve_timeout,
    fetch_asset,
    find_cuebert_root,
    poll_status,
    sanitize_prompt_text,
    submit_workflow,
)

logger = logging.getLogger(__name__)


def _slug_from_prompt(prompt: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", prompt.strip())[:80].strip("-")
    return slug or "asset"


def _destination_must_be_under_traces(dest: Path, traces_root: Path) -> bool:
    try:
        dest.relative_to(traces_root)
        return True
    except ValueError:
        return False


def register(mcp: FastMCP) -> None:
    """Register ``comfyui_generate_asset`` on the MCP server."""

    @mcp.tool()
    def comfyui_generate_asset(
        workflow_name: str,
        prompt: str,
        seed: int | None = None,
        destination: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a named workflow, wait for completion, and write image output under traces.

        Workflow graphs must exist as ``workflows/<name>.json`` in this skill (allow-listed).
        Generated assets and sidecar envelopes live under
        ``.cuebert/traces/asset/<timestamp>/<workflow_name>/`` per control-plane path
        conventions.

        Args:
            workflow_name: Workflow stem (filename without ``.json``).
            prompt: Positive prompt text (non-empty, max 4096 after sanitization).
            seed: Optional KSampler seed override.
            destination: Optional output path; must resolve under ``.cuebert/traces/asset/``.
            params: Optional shallow input overrides (deferred template layer in M4-P4).

        Returns:
            Envelope with ``status``, ``prompt_id``, ``assets``, ``envelope_path``,
            ``duration_ms``, ``dry_run``, and optional ``error_code``.
        """
        t0 = time.monotonic()
        try:
            available = _list_local_workflows()
            if not workflow_name or workflow_name not in available:
                return {
                    "status": "error",
                    "prompt_id": None,
                    "assets": [],
                    "envelope_path": None,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "dry_run": _get_mode() == "dry_run",
                    "error": (
                        f"Unknown workflow {workflow_name!r}. "
                        f"Available: {available!r}"
                    ),
                    "error_code": "unknown_workflow",
                }

            raw_prompt = str(prompt) if prompt is not None else ""
            cleaned = sanitize_prompt_text(raw_prompt)
            if not cleaned.strip():
                return {
                    "status": "error",
                    "prompt_id": None,
                    "assets": [],
                    "envelope_path": None,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "dry_run": _get_mode() == "dry_run",
                    "error": "prompt is required and must be non-empty after sanitization.",
                    "error_code": "prompt_empty",
                }
            if len(raw_prompt) > 4096:
                return {
                    "status": "error",
                    "prompt_id": None,
                    "assets": [],
                    "envelope_path": None,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "dry_run": _get_mode() == "dry_run",
                    "error": "prompt exceeds 4096 characters.",
                    "error_code": "prompt_empty",
                }

            hub = find_cuebert_root(Path(__file__).resolve())
            traces_root = (hub / ".cuebert" / "traces" / "asset").resolve()
            traces_root.mkdir(parents=True, exist_ok=True)

            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            if destination:
                dest_path = Path(destination)
                if dest_path.is_absolute():
                    final_dest = dest_path.resolve()
                else:
                    final_dest = (hub / dest_path).resolve()
            else:
                slug = _slug_from_prompt(cleaned)
                final_dest = (
                    traces_root / ts / workflow_name / f"{slug}.png"
                ).resolve()

            if not _destination_must_be_under_traces(final_dest, traces_root):
                return {
                    "status": "error",
                    "prompt_id": None,
                    "assets": [],
                    "envelope_path": None,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "dry_run": _get_mode() == "dry_run",
                    "error": (
                        "destination must resolve under "
                        f"{traces_root} (path traversal rejected)."
                    ),
                    "error_code": "workflow_validation_error",
                }

            final_dest.parent.mkdir(parents=True, exist_ok=True)

            submitted = submit_workflow(
                workflow_name, cleaned, seed, params
            )
            if submitted.get("status") == "failed" or not submitted.get("prompt_id"):
                return {
                    "status": "error",
                    "prompt_id": submitted.get("prompt_id"),
                    "assets": [],
                    "envelope_path": None,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "dry_run": bool(submitted.get("dry_run")),
                    "error": submitted.get("error"),
                    "error_code": submitted.get("error_code") or "workflow_validation_error",
                }

            prompt_id = str(submitted["prompt_id"])
            polled = poll_status(prompt_id, max_wait_s=_resolve_timeout())
            assets: list[str] = []
            dry = bool(submitted.get("dry_run") or polled.get("dry_run"))

            if polled.get("status") != "completed":
                envelope_path = Path(f"{final_dest}.json")
                env_body = {
                    "workflow_name": workflow_name,
                    "prompt": cleaned,
                    "seed": seed,
                    "params": params,
                    "prompt_id": prompt_id,
                    "status": polled.get("status"),
                    "dry_run": dry,
                    "error": polled.get("error"),
                    "error_code": polled.get("error_code"),
                }
                envelope_path.write_text(
                    json.dumps(env_body, indent=2), encoding="utf-8"
                )
                return {
                    "status": polled.get("status", "error"),
                    "prompt_id": prompt_id,
                    "assets": [],
                    "envelope_path": str(envelope_path),
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "dry_run": dry,
                    "error": polled.get("error"),
                    "error_code": polled.get("error_code"),
                }

            refs = polled.get("image_refs") or []
            if dry or _get_mode() == "dry_run":
                meta = {"type": "dry_placeholder"}
                got = fetch_asset(meta, str(final_dest))
                if got.get("saved"):
                    assets.append(str(got["saved"]))
            elif refs and isinstance(refs[0], dict):
                got = fetch_asset(refs[0], str(final_dest))
                if got.get("error_code"):
                    envelope_path = Path(f"{final_dest}.json")
                    envelope_path.write_text(
                        json.dumps(
                            {
                                "workflow_name": workflow_name,
                                "prompt": cleaned,
                                "prompt_id": prompt_id,
                                "status": "failed",
                                "fetch": got,
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    return {
                        "status": "error",
                        "prompt_id": prompt_id,
                        "assets": [],
                        "envelope_path": str(envelope_path),
                        "duration_ms": int((time.monotonic() - t0) * 1000),
                        "dry_run": False,
                        "error": got.get("error"),
                        "error_code": got.get("error_code"),
                    }
                if got.get("saved"):
                    assets.append(str(got["saved"]))
            else:
                envelope_path = Path(f"{final_dest}.json")
                envelope_path.write_text(
                    json.dumps(
                        {
                            "workflow_name": workflow_name,
                            "prompt": cleaned,
                            "prompt_id": prompt_id,
                            "status": "failed",
                            "error": "No image outputs in ComfyUI history entry.",
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return {
                    "status": "error",
                    "prompt_id": prompt_id,
                    "assets": [],
                    "envelope_path": str(envelope_path),
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "dry_run": False,
                    "error": "No image outputs returned from ComfyUI for this prompt.",
                    "error_code": "workflow_validation_error",
                }

            envelope_path = Path(f"{final_dest}.json")
            env_body = {
                "workflow_name": workflow_name,
                "prompt": cleaned,
                "seed": seed,
                "params": params,
                "prompt_id": prompt_id,
                "status": "completed",
                "dry_run": dry,
                "assets": assets,
            }
            envelope_path.write_text(
                json.dumps(env_body, indent=2), encoding="utf-8"
            )

            return {
                "status": "completed",
                "prompt_id": prompt_id,
                "assets": assets,
                "envelope_path": str(envelope_path),
                "duration_ms": int((time.monotonic() - t0) * 1000),
                "dry_run": dry,
                "error": None,
            }
        except Exception as exc:
            logger.error("comfyui_generate_asset failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "prompt_id": None,
                "assets": [],
                "envelope_path": None,
                "duration_ms": int((time.monotonic() - t0) * 1000),
                "dry_run": _get_mode() == "dry_run",
                "error": str(exc),
                "error_code": "network_error",
            }
