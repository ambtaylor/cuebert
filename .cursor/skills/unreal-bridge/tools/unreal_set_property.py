"""MCP tool: set a scalar property on a preset-exposed object (Remote Control PUT)."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from _unreal_client import (
    FINDING_READBACK_FAILED,
    FINDING_PUT_REJECTED,
    _DRY_RUN_VERSION,
    _get_mode,
    _resolve_base_url,
    _resolve_timeout,
    get_exposed_property,
    health_probe,
    set_exposed_property,
)
from _unreal_mutate_common import (
    append_mutation_line,
    find_hub_root,
    mutation_trace_timestamp,
    troubleshoot_commit_safe,
    validate_mutation_value,
)

logger = logging.getLogger(__name__)

_PRESET_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_SET_PROPERTY_WHITELIST = frozenset(
    {
        "agent-play-author",
        "user-direct-debug",
    },
)


def register(mcp: FastMCP) -> None:
    """Register ``unreal_set_property`` on the MCP server."""

    @mcp.tool()
    def unreal_set_property(
        preset_name: str,
        object_path: str,
        property_name: str,
        value: Any,
        caller: str = "user-direct-debug",
    ) -> dict[str, Any]:
        """Set a property on a preset-exposed object (scope whitelist enforced).

        Args:
            preset_name: Remote Control preset name.
            object_path: Full UE object path for the exposed property owner.
            property_name: UPROPERTY name to set.
            value: JSON-serializable scalar (int, float, bool, str, dict, list).
            caller: Harness identity (see ``agent-unreal.md`` §6).

        Returns:
            Mutate envelope with ``status``, ``mutation_audit``, ``error``, etc.
        """
        t0 = time.monotonic()
        trace_ts = mutation_trace_timestamp()
        base_url = _resolve_base_url()
        mode = _get_mode()
        elapsed = lambda: int((time.monotonic() - t0) * 1000)

        def _envelope(
            *,
            status: str,
            value_from: Any,
            value_to: Any,
            editor_version: str | None,
            mutation_audit: dict[str, Any] | None,
            err: dict[str, str] | None,
        ) -> dict[str, Any]:
            return {
                "status": status,
                "operation": "mutate",
                "op_kind": "set_property",
                "caller": caller,
                "preset_name": preset_name,
                "object_path": object_path,
                "property_name": property_name,
                "value_from": value_from,
                "value_to": value_to,
                "base_url": base_url,
                "mode": mode,
                "editor_version": editor_version,
                "mutation_audit": mutation_audit,
                "error": err,
                "elapsed_ms": elapsed(),
            }

        if caller not in _SET_PROPERTY_WHITELIST:
            troubleshoot_commit_safe(
                "unreal.scope_rejected: set_property",
                [{"caller": caller, "op_kind": "set_property", "preset": preset_name}],
                tags="unreal-bridge,scope",
                agent="unreal_set_property",
            )
            return _envelope(
                status="blocked",
                value_from=None,
                value_to=None,
                editor_version=None,
                mutation_audit=None,
                err={
                    "code": "unreal.scope_rejected",
                    "message": f"caller {caller!r} is not allowed for set_property",
                },
            )

        if not preset_name or not _PRESET_NAME_RE.match(preset_name):
            return _envelope(
                status="error",
                value_from=None,
                value_to=None,
                editor_version=None,
                mutation_audit=None,
                err={"code": "unreal.validation_failed", "message": "invalid preset_name"},
            )

        if not object_path or not _OBJECT_PATH_RE.match(object_path):
            return _envelope(
                status="error",
                value_from=None,
                value_to=None,
                editor_version=None,
                mutation_audit=None,
                err={"code": "unreal.validation_failed", "message": "invalid object_path"},
            )
        if not property_name or not _PROPERTY_NAME_RE.match(property_name):
            return _envelope(
                status="error",
                value_from=None,
                value_to=None,
                editor_version=None,
                mutation_audit=None,
                err={"code": "unreal.validation_failed", "message": "invalid property_name"},
            )

        verr = validate_mutation_value(value)
        if verr:
            return _envelope(
                status="error",
                value_from=None,
                value_to=None,
                editor_version=None,
                mutation_audit=None,
                err={"code": "unreal.validation_failed", "message": verr},
            )

        timeout = _resolve_timeout()
        iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if mode == "dry_run":
            audit = {
                "timestamp": iso_now,
                "caller": caller,
                "op_kind": "set_property",
                "preset": preset_name,
                "object_path": object_path,
                "property": property_name,
                "from": None,
                "to": value,
                "mode": "dry_run",
                "editor_version": _DRY_RUN_VERSION,
                "reversal_hint": f"best-effort: set {property_name} back to prior value on {object_path}",
                "audit_status": "ok",
            }
            try:
                hub = find_hub_root()
                append_mutation_line(hub, trace_ts, audit)
            except Exception as exc:
                logger.warning("mutations.jsonl append failed: %s", exc)
            troubleshoot_commit_safe(
                "unreal_set_property dry_run accepted",
                [audit],
                tags="unreal-bridge,set_property,dry_run",
                agent="unreal_set_property",
            )
            return _envelope(
                status="dry_run",
                value_from=None,
                value_to=value,
                editor_version=_DRY_RUN_VERSION,
                mutation_audit=audit,
                err=None,
            )

        hp = health_probe(base_url, timeout)
        editor_version = hp.get("version") or "unknown"
        if not hp.get("reachable"):
            return _envelope(
                status="error",
                value_from=None,
                value_to=None,
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
                value_from=None,
                value_to=None,
                editor_version=editor_version,
                mutation_audit=None,
                err={
                    "code": "unreal.plugin_missing",
                    "message": "Remote Control plugins not reported by /remote/info",
                },
            )

        pre = get_exposed_property(base_url, object_path, property_name, timeout)
        if not pre.get("ok"):
            return _envelope(
                status="error",
                value_from=None,
                value_to=None,
                editor_version=editor_version,
                mutation_audit=None,
                err={
                    "code": "unreal.property_not_found",
                    "message": str(pre.get("error") or "pre-read failed"),
                },
            )
        value_from = pre.get("value")

        put = set_exposed_property(
            base_url,
            preset_name,
            object_path,
            property_name,
            value,
            timeout,
        )
        if not put.get("ok"):
            return _envelope(
                status="error",
                value_from=value_from,
                value_to=None,
                editor_version=editor_version,
                mutation_audit=None,
                err={
                    "code": FINDING_PUT_REJECTED,
                    "message": str(put.get("error") or "PUT /remote/object/property failed"),
                },
            )

        post = get_exposed_property(base_url, object_path, property_name, timeout)
        if not post.get("ok"):
            audit = {
                "timestamp": iso_now,
                "caller": caller,
                "op_kind": "set_property",
                "preset": preset_name,
                "object_path": object_path,
                "property": property_name,
                "from": value_from,
                "to": None,
                "mode": "live",
                "editor_version": editor_version,
                "reversal_hint": f"best-effort: set {property_name} back to {json.dumps(value_from)} on {object_path}",
                "audit_status": "partial_success",
            }
            try:
                hub = find_hub_root()
                append_mutation_line(hub, trace_ts, audit)
            except Exception as exc:
                logger.warning("mutations.jsonl append failed: %s", exc)
            troubleshoot_commit_safe(
                "unreal_set_property partial_success (post-read failed)",
                [audit],
                tags="unreal-bridge,set_property,partial",
                agent="unreal_set_property",
            )
            return _envelope(
                status="error",
                value_from=value_from,
                value_to=None,
                editor_version=editor_version,
                mutation_audit=audit,
                err={
                    "code": FINDING_READBACK_FAILED,
                    "message": str(post.get("error") or "post-read failed after successful PUT"),
                },
            )

        value_to = post.get("value")
        audit = {
            "timestamp": iso_now,
            "caller": caller,
            "op_kind": "set_property",
            "preset": preset_name,
            "object_path": object_path,
            "property": property_name,
            "from": value_from,
            "to": value_to,
            "mode": "live",
            "editor_version": editor_version,
            "reversal_hint": f"best-effort: set {property_name} back to {json.dumps(value_from)} on {object_path}",
            "audit_status": "ok",
        }
        try:
            hub = find_hub_root()
            append_mutation_line(hub, trace_ts, audit)
        except Exception as exc:
            logger.warning("mutations.jsonl append failed: %s", exc)
        troubleshoot_commit_safe(
            "unreal_set_property live success",
            [audit],
            tags="unreal-bridge,set_property,live",
            agent="unreal_set_property",
        )
        return _envelope(
            status="pass",
            value_from=value_from,
            value_to=value_to,
            editor_version=editor_version,
            mutation_audit=audit,
            err=None,
        )
