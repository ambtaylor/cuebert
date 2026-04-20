"""MCP tool: call an exposed UFunction on a preset-exposed object (Remote Control PUT)."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from _unreal_client import (
    FINDING_PUT_REJECTED,
    _DRY_RUN_VERSION,
    _get_mode,
    _resolve_base_url,
    _resolve_timeout,
    call_exposed_function,
    health_probe,
)
from _unreal_mutate_common import (
    append_mutation_line,
    find_hub_root,
    mutation_trace_timestamp,
    troubleshoot_commit_safe,
    validate_parameters_dict,
)

logger = logging.getLogger(__name__)

_PRESET_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_CALL_FUNCTION_WHITELIST = frozenset(
    {
        "agent-play-preview",
        "agent-asset-place",
        "user-direct-debug",
    },
)


def _extract_return_value(body: Any) -> Any:
    if not isinstance(body, dict):
        return None
    for key in ("ReturnValue", "returnValue", "value", "Value"):
        if key in body:
            return body.get(key)
    return None


def register(mcp: FastMCP) -> None:
    """Register ``unreal_call_function`` on the MCP server."""

    @mcp.tool()
    def unreal_call_function(
        preset_name: str,
        object_path: str,
        function_name: str,
        args: dict[str, Any] | None = None,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Call an exposed UFunction (scope whitelist enforced).

        Args:
            preset_name: Remote Control preset name.
            object_path: Full UE object path owning the exposed function.
            function_name: UFunction name to invoke.
            args: Named parameters for Remote Control (empty dict if none).
            caller: Harness identity (see ``agent-unreal.md`` §6).

        Returns:
            Mutate envelope including ``return_value`` when available.
        """
        t0 = time.monotonic()
        trace_ts = mutation_trace_timestamp()
        base_url = _resolve_base_url()
        mode = _get_mode()
        elapsed = lambda: int((time.monotonic() - t0) * 1000)
        params = dict(args) if args is not None else {}

        def _envelope(
            *,
            status: str,
            return_value: Any,
            editor_version: str | None,
            mutation_audit: dict[str, Any] | None,
            err: dict[str, str] | None,
        ) -> dict[str, Any]:
            return {
                "status": status,
                "operation": "mutate",
                "op_kind": "call_function",
                "caller": caller,
                "preset_name": preset_name,
                "object_path": object_path,
                "function_name": function_name,
                "args": params,
                "return_value": return_value,
                "base_url": base_url,
                "mode": mode,
                "editor_version": editor_version,
                "mutation_audit": mutation_audit,
                "error": err,
                "elapsed_ms": elapsed(),
            }

        if caller not in _CALL_FUNCTION_WHITELIST:
            troubleshoot_commit_safe(
                "unreal.scope_rejected: call_function",
                [{"caller": caller, "op_kind": "call_function", "preset": preset_name}],
                tags="unreal-bridge,scope",
                agent="unreal_call_function",
            )
            return _envelope(
                status="blocked",
                return_value=None,
                editor_version=None,
                mutation_audit=None,
                err={
                    "code": "unreal.scope_rejected",
                    "message": f"caller {caller!r} is not allowed for call_function",
                },
            )

        if not preset_name or not _PRESET_NAME_RE.match(preset_name):
            return _envelope(
                status="error",
                return_value=None,
                editor_version=None,
                mutation_audit=None,
                err={"code": "unreal.validation_failed", "message": "invalid preset_name"},
            )

        perr = validate_parameters_dict(params)
        if perr:
            return _envelope(
                status="error",
                return_value=None,
                editor_version=None,
                mutation_audit=None,
                err={"code": "unreal.validation_failed", "message": perr},
            )

        timeout = _resolve_timeout()
        iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if mode == "dry_run":
            audit = {
                "timestamp": iso_now,
                "caller": caller,
                "op_kind": "call_function",
                "preset": preset_name,
                "object_path": object_path,
                "function": function_name,
                "from": None,
                "to": True,
                "mode": "dry_run",
                "editor_version": _DRY_RUN_VERSION,
                "reversal_hint": None,
                "audit_status": "ok",
            }
            try:
                hub = find_hub_root()
                append_mutation_line(hub, trace_ts, audit)
            except Exception as exc:
                logger.warning("mutations.jsonl append failed: %s", exc)
            troubleshoot_commit_safe(
                "unreal_call_function dry_run accepted",
                [audit],
                tags="unreal-bridge,call_function,dry_run",
                agent="unreal_call_function",
            )
            return _envelope(
                status="dry_run",
                return_value=True,
                editor_version=_DRY_RUN_VERSION,
                mutation_audit=audit,
                err=None,
            )

        hp = health_probe(base_url, timeout)
        editor_version = hp.get("version") or "unknown"
        if not hp.get("reachable"):
            return _envelope(
                status="error",
                return_value=None,
                editor_version=editor_version,
                mutation_audit=None,
                err={
                    "code": "unreal.unreachable",
                    "message": str(hp.get("error") or "editor not reachable"),
                },
            )
        plugs = hp.get("plugins") or []
        if (
            isinstance(plugs, list)
            and len(plugs) > 0
            and not any("RemoteControl" in str(p) for p in plugs)
        ):
            return _envelope(
                status="error",
                return_value=None,
                editor_version=editor_version,
                mutation_audit=None,
                err={
                    "code": "unreal.plugin_missing",
                    "message": "Remote Control plugins not reported by /remote/info",
                },
            )

        put = call_exposed_function(
            base_url,
            preset_name,
            object_path,
            function_name,
            params,
            timeout,
        )
        body = put.get("response_body")
        if not put.get("ok"):
            return _envelope(
                status="error",
                return_value=None,
                editor_version=editor_version,
                mutation_audit=None,
                err={
                    "code": FINDING_PUT_REJECTED,
                    "message": str(put.get("error") or "PUT /remote/object/call failed"),
                },
            )

        ret = _extract_return_value(body)
        audit = {
            "timestamp": iso_now,
            "caller": caller,
            "op_kind": "call_function",
            "preset": preset_name,
            "object_path": object_path,
            "function": function_name,
            "from": None,
            "to": ret,
            "mode": "live",
            "editor_version": editor_version,
            "reversal_hint": None,
            "audit_status": "ok",
        }
        try:
            hub = find_hub_root()
            append_mutation_line(hub, trace_ts, audit)
        except Exception as exc:
            logger.warning("mutations.jsonl append failed: %s", exc)
        troubleshoot_commit_safe(
            "unreal_call_function live success",
            [audit],
            tags="unreal-bridge,call_function,live",
            agent="unreal_call_function",
        )
        return _envelope(
            status="pass",
            return_value=ret,
            editor_version=editor_version,
            mutation_audit=audit,
            err=None,
        )
