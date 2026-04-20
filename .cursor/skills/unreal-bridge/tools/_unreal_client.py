"""Shared Unreal Editor Remote Control HTTP client with dry-run support.

HTTP GET subset only (websocket deferred). Mirrors the structure of
``_comfyui_client.py`` for vault/env resolution, timeouts, and safety rails.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:30010"
_VAULT_BASE_URL_KEY = "unreal.base_url"
_VAULT_MODE_KEY = "unreal.mode"
_VAULT_TIMEOUT_KEY = "unreal.timeout_s"
_VAULT_FALLBACK_LOGGED = False
_MAX_BODY_BYTES = 10_000_000
_MAX_TIMEOUT_S = 30.0
_DEFAULT_TIMEOUT_S = 10.0

_DRY_RUN_VERSION = "5.4.0-dry_run"
_DRY_RUN_PLUGINS = [
    "RemoteControl",
    "RemoteControlAPI",
    "RemoteControlWebInterface",
]
_DRY_RUN_PRESETS: list[dict[str, Any]] = [
    {"name": "ExamplePreset", "path": "/Game/Presets/ExamplePreset", "exposed_count": 3},
    {"name": "PlayerControls", "path": "/Game/Presets/PlayerControls", "exposed_count": 5},
    {"name": "LightingRig", "path": "/Game/Presets/LightingRig", "exposed_count": 2},
]
_DRY_RUN_PRESET_DETAIL: dict[str, Any] = {
    "name": "ExamplePreset",
    "properties": [
        {"object_path": "/Game/Maps/Test.Test:PersistentLevel.PlayerStart", "property_name": "RelativeLocation", "type": "struct", "exposed_name": "PlayerStartLocation"},
        {"object_path": "/Game/Maps/Test.Test:PersistentLevel.DirectionalLight_0", "property_name": "Intensity", "type": "float", "exposed_name": "SunIntensity"},
    ],
    "functions": [
        {"object_path": "/Game/Blueprint/BP_Game.BP_Game_C", "function_name": "ResetRound", "arg_count": 0, "exposed_name": "reset_round"},
    ],
}

_PRESET_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_ACTOR_LABEL_RE = re.compile(r"^[A-Za-z0-9_. -]{1,256}$")


class _NoFollowRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow redirects; log the first Location once at WARNING."""

    _logged = False

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        if not _NoFollowRedirect._logged:
            logger.warning(
                "Unreal Remote Control redirect not followed (%s -> %s)",
                req.full_url,
                newurl,
            )
            _NoFollowRedirect._logged = True
        return None


def _build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoFollowRedirect())


def _is_unreal_configured_explicitly() -> bool:
    """True when base URL is set via env or hub shared vault (not implicit default)."""
    env_url = os.environ.get("CUEBERT_UNREAL_BASE_URL")
    if env_url is not None and str(env_url).strip():
        return True
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return False
        url = get_resolver().get_credential(_VAULT_BASE_URL_KEY)
        return bool(url and str(url).strip())
    except Exception:
        return False


def _get_mode_explicit() -> str | None:
    """Return ``live`` or ``dry_run`` from env or vault, else None."""
    raw = os.environ.get("CUEBERT_UNREAL_MODE")
    if raw is not None and str(raw).strip():
        m = str(raw).strip().lower()
        if m in ("live", "dry_run"):
            return m
        logger.warning("Unknown CUEBERT_UNREAL_MODE=%r; treating as live.", raw)
        return "live"
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_MODE_KEY)
        if v is None or not str(v).strip():
            return None
        m = str(v).strip().lower()
        if m in ("live", "dry_run"):
            return m
        logger.warning("Unknown vault unreal.mode=%r; ignoring.", v)
    except Exception:
        return None
    return None


def _get_mode() -> str:
    """Resolve ``live`` vs ``dry_run`` (env/vault explicit, else comfyui-style default).

    When mode is unset and Unreal is not explicitly configured (no env URL and no
    vault ``unreal.base_url``), default to ``dry_run`` so MCP loads without a
    running editor. When configured, default to ``live`` (callers still see
    ``unreachable`` from ``health_probe`` if the socket fails).
    """
    explicit = _get_mode_explicit()
    if explicit is not None:
        return explicit
    if not _is_unreal_configured_explicitly():
        return "dry_run"
    return "live"


def _sanitize_url(url: str) -> str | None:
    """Return *url* if scheme is http(s), no embedded credentials, else None."""
    raw = str(url).strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return None
    if parsed.username or parsed.password:
        return None
    if not parsed.netloc:
        return None
    return raw.rstrip("/")


def _resolve_base_url() -> str:
    """Resolve Remote Control HTTP base: env, then vault, then localhost default."""
    global _VAULT_FALLBACK_LOGGED
    env_url = os.environ.get("CUEBERT_UNREAL_BASE_URL")
    if env_url is not None and str(env_url).strip():
        cleaned = _sanitize_url(str(env_url).strip())
        if cleaned:
            return cleaned
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if CUEBERT_VAULT_AVAILABLE:
            v = get_resolver().get_credential(_VAULT_BASE_URL_KEY)
            if v and str(v).strip():
                cleaned = _sanitize_url(str(v).strip())
                if cleaned:
                    return cleaned
    except Exception as exc:
        if not _VAULT_FALLBACK_LOGGED:
            logger.info(
                "Unreal vault URL unavailable (%s); using default %s",
                exc,
                _DEFAULT_BASE_URL,
            )
            _VAULT_FALLBACK_LOGGED = True
    if not _VAULT_FALLBACK_LOGGED and not _is_unreal_configured_explicitly():
        logger.info(
            "Unreal base URL not configured; using default %s (see vault-standard.md).",
            _DEFAULT_BASE_URL,
        )
        _VAULT_FALLBACK_LOGGED = True
    return _DEFAULT_BASE_URL.rstrip("/")


def _vault_timeout_raw() -> str | None:
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_TIMEOUT_KEY)
        if v is None or not str(v).strip():
            return None
        return str(v).strip()
    except Exception:
        return None


def _resolve_timeout() -> float:
    """Seconds for urllib ``open`` timeout (connect+read combined); hard-capped at 30s."""
    raw = os.environ.get("CUEBERT_UNREAL_TIMEOUT_S")
    if raw is None or not str(raw).strip():
        raw = _vault_timeout_raw()
    if raw is None or not str(raw).strip():
        t = _DEFAULT_TIMEOUT_S
    else:
        try:
            t = float(str(raw).strip())
        except ValueError:
            t = _DEFAULT_TIMEOUT_S
    return min(max(0.5, t), _MAX_TIMEOUT_S)


def _http_request(
    method: str,
    url: str,
    *,
    timeout: float,
    data: bytes | None = None,
) -> tuple[int, dict[str, Any] | list[Any] | None, str | None]:
    """Perform HTTP request; return ``(status, json_or_none, error_message)``."""
    safe = _sanitize_url(url)
    if safe is None:
        return 0, None, "invalid or unsupported URL"
    capped = min(max(0.5, timeout), _MAX_TIMEOUT_S)
    req = urllib.request.Request(safe, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    opener = _build_opener()
    try:
        with opener.open(req, timeout=capped) as resp:
            chunk = resp.read(_MAX_BODY_BYTES + 1)
            if len(chunk) > _MAX_BODY_BYTES:
                return 0, None, "response body exceeds 10MB cap"
            status = resp.getcode() or 0
            try:
                parsed: Any = json.loads(chunk.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                return status, None, None
            if isinstance(parsed, (dict, list)):
                return status, parsed, None
            return status, None, None
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        tail = body[:500].decode("utf-8", errors="replace")
        if 300 <= exc.code < 400:
            return exc.code, None, f"HTTP redirect {exc.code} (not followed): {tail}"
        return exc.code, None, f"HTTP {exc.code}: {tail}"
    except Exception as exc:
        return 0, None, str(exc)


def _http_get(url: str, timeout: float) -> tuple[int, dict[str, Any] | list[Any] | None, str | None]:
    """GET helper; live branch uses stdlib urllib only (see also ``_http_put``)."""
    return _http_request("GET", url, timeout=timeout, data=None)


def _http_put(url: str, body: bytes | None, timeout: float) -> tuple[int, dict[str, Any] | list[Any] | None, str | None]:
    """PUT skeleton for M5-P4 ``/remote/object/property`` and ``/remote/object/call``.

    P1 tools do not call this; it mirrors ``_http_get`` so future writes share
    the same opener, caps, and JSON parsing rules.
    """
    return _http_request("PUT", url, timeout=timeout, data=body)


def _extract_version(data: dict[str, Any] | list[Any] | None) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in (
        "ApplicationVersion",
        "EngineVersion",
        "Version",
        "version",
        "ServerVersion",
    ):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _extract_plugins(data: dict[str, Any] | list[Any] | None) -> list[str] | None:
    if not isinstance(data, dict):
        return None
    raw = data.get("Plugins") or data.get("plugins")
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and "Name" in item:
                out.append(str(item["Name"]))
        return out or None
    return None


def health_probe(base_url: str, timeout: float) -> dict[str, Any]:
    """GET ``/remote/info`` or return a dry-run synthetic envelope."""
    # dry_run branch: no outbound HTTP (tool layer may still classify ``not_configured``).
    if _get_mode() == "dry_run":
        return {
            "reachable": True,
            "version": _DRY_RUN_VERSION,
            "plugins": list(_DRY_RUN_PLUGINS),
            "error": None,
            "dry_run": True,
        }
    base = base_url.rstrip("/")
    url = f"{base}/remote/info"
    status, data, err = _http_get(url, timeout)
    if err or status != 200:
        return {
            "reachable": False,
            "version": None,
            "plugins": None,
            "error": err or f"unexpected status {status}",
            "dry_run": False,
        }
    return {
        "reachable": True,
        "version": _extract_version(data),
        "plugins": _extract_plugins(data) or [],
        "error": None,
        "dry_run": False,
    }


def _normalize_preset_entry(item: Any) -> dict[str, Any] | None:
    if isinstance(item, str):
        name = item.strip()
        if not name:
            return None
        return {"name": name, "path": "", "exposed_count": 0}
    if not isinstance(item, dict):
        return None
    name = item.get("Name") or item.get("name") or item.get("Id")
    if not name:
        return None
    path = item.get("Path") or item.get("path") or ""
    exposed = item.get("ExposedEntitiesCount")
    if exposed is None:
        exposed = item.get("exposed_count") or item.get("ExposedCount") or 0
    try:
        exposed_count = int(exposed)
    except (TypeError, ValueError):
        exposed_count = 0
    return {
        "name": str(name),
        "path": str(path) if path is not None else "",
        "exposed_count": exposed_count,
    }


def list_presets(base_url: str, timeout: float) -> dict[str, Any]:
    """GET ``/remote/presets``; normalize to ``presets`` list."""
    if _get_mode() == "dry_run":
        return {
            "presets": [dict(p) for p in _DRY_RUN_PRESETS],
            "error": None,
            "dry_run": True,
        }
    base = base_url.rstrip("/")
    url = f"{base}/remote/presets"
    status, data, err = _http_get(url, timeout)
    if err or status != 200:
        return {"presets": [], "error": err or f"unexpected status {status}", "dry_run": False}
    rows: list[dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            row = _normalize_preset_entry(item)
            if row:
                rows.append(row)
    elif isinstance(data, dict):
        inner = data.get("Presets") or data.get("presets") or data.get("PresetNames")
        if isinstance(inner, list):
            for item in inner:
                row = _normalize_preset_entry(item)
                if row:
                    rows.append(row)
    return {"presets": rows, "error": None, "dry_run": False}


def _sanitize_preset_name(preset_name: str) -> str | None:
    if not preset_name or not _PRESET_NAME_RE.match(preset_name):
        return None
    return preset_name


def _sanitize_actor_label(actor_label: str) -> str | None:
    if not actor_label or not _ACTOR_LABEL_RE.match(actor_label):
        return None
    return actor_label


def _normalize_exposed_row(item: Any, *, kind: str) -> dict[str, Any] | None:
    """Normalize one exposed property (``kind='prop'``) or function row."""
    if not isinstance(item, dict):
        return None
    obj = item.get("ObjectPath") or item.get("object_path") or item.get("Owner")
    exposed = item.get("Label") or item.get("exposed_name") or item.get("DisplayName")
    exp_out = str(exposed) if exposed is not None else None
    if kind == "prop":
        prop = item.get("PropertyName") or item.get("property_name") or item.get("Name")
        if not obj or not prop:
            return None
        typ = item.get("Type") or item.get("type") or "unknown"
        return {"object_path": str(obj), "property_name": str(prop), "type": str(typ), "exposed_name": exp_out}
    fn = item.get("FunctionName") or item.get("function_name") or item.get("Name")
    if not obj or not fn:
        return None
    args = item.get("Arguments") or item.get("arguments") or []
    arg_count = len(args) if isinstance(args, list) else int(item.get("arg_count") or 0)
    return {"object_path": str(obj), "function_name": str(fn), "arg_count": int(arg_count), "exposed_name": exp_out}


def describe_preset(base_url: str, preset_name: str, timeout: float) -> dict[str, Any]:
    """GET ``/remote/preset/<name>``; return properties/functions lists."""
    safe_name = _sanitize_preset_name(preset_name)
    if safe_name is None:
        return {
            "name": preset_name,
            "properties": [],
            "functions": [],
            "error": "invalid preset_name",
            "dry_run": False,
            "missing": False,
        }
    if _get_mode() == "dry_run":
        return {
            "name": safe_name,
            "properties": [dict(p) for p in _DRY_RUN_PRESET_DETAIL["properties"]],
            "functions": [dict(f) for f in _DRY_RUN_PRESET_DETAIL["functions"]],
            "error": None,
            "dry_run": True,
            "missing": False,
        }
    base = base_url.rstrip("/")
    enc = urllib.parse.quote(safe_name, safe="")
    url = f"{base}/remote/preset/{enc}"
    status, data, err = _http_get(url, timeout)
    if status == 404 or (err and "404" in err):
        return {
            "name": safe_name,
            "properties": [],
            "functions": [],
            "error": None,
            "dry_run": False,
            "missing": True,
        }
    if err or status != 200:
        return {
            "name": safe_name,
            "properties": [],
            "functions": [],
            "error": err or f"unexpected status {status}",
            "dry_run": False,
            "missing": False,
        }
    props: list[dict[str, Any]] = []
    funcs: list[dict[str, Any]] = []
    if isinstance(data, dict):
        raw_props = (
            data.get("ExposedProperties")
            or data.get("exposed_properties")
            or data.get("Properties")
            or []
        )
        raw_funcs = (
            data.get("ExposedFunctions")
            or data.get("exposed_functions")
            or data.get("Functions")
            or []
        )
        if isinstance(raw_props, list):
            for item in raw_props:
                row = _normalize_exposed_row(item, kind="prop")
                if row:
                    props.append(row)
        if isinstance(raw_funcs, list):
            for item in raw_funcs:
                row = _normalize_exposed_row(item, kind="func")
                if row:
                    funcs.append(row)
    return {
        "name": safe_name,
        "properties": props,
        "functions": funcs,
        "error": None,
        "dry_run": False,
        "missing": False,
    }


def ping_actor(
    base_url: str,
    preset_name: str,
    actor_label: str,
    timeout: float,
) -> dict[str, Any]:
    """GET read-only expose path for an actor label under a preset."""
    ps = _sanitize_preset_name(preset_name)
    al = _sanitize_actor_label(actor_label)
    if ps is None:
        return {"found": False, "label": actor_label, "error": "invalid preset_name"}
    if al is None:
        return {"found": False, "label": actor_label, "error": "invalid actor_label"}
    if _get_mode() == "dry_run":
        return {"found": True, "label": al, "error": None, "dry_run": True}
    base = base_url.rstrip("/")
    enc_preset = urllib.parse.quote(ps, safe="")
    enc_label = urllib.parse.quote(al, safe="")
    url = f"{base}/remote/preset/{enc_preset}/expose/actor/{enc_label}"
    status, data, err = _http_get(url, timeout)
    if status == 404 or (err and "404" in (err or "")):
        return {"found": False, "label": al, "error": None, "dry_run": False}
    if err or status != 200:
        return {"found": False, "label": al, "error": err or f"unexpected status {status}", "dry_run": False}
    found = True
    if isinstance(data, dict):
        if "Found" in data:
            found = bool(data.get("Found"))
        elif "found" in data:
            found = bool(data.get("found"))
    return {"found": found, "label": al, "error": None, "dry_run": False}


def non_localhost_warning(base_url: str) -> str | None:
    """Return a warning string when the configured host is not loopback."""
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1", ""):
        return None
    if not host:
        return None
    return (
        f"base_url host {host!r} is not localhost; ensure Remote Control is not "
        "exposed to untrusted networks (Epic defaults to LAN-only)."
    )
