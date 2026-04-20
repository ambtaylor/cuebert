"""Shared ComfyUI HTTP client with dry-run support and workflow allow-listing.

Workflow graphs are deferred to M4-P4; this module wires HTTP semantics,
vault/env resolution, and safety rails for MCP tools.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import random
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://127.0.0.1:8188"
_VAULT_CREDENTIAL_PATH = "comfyui.base_url"
_VAULT_FALLBACK_LOGGED = False
_MAX_RESPONSE_LOG_TAIL = 500
_MAX_RETRIES_5XX = 3
_RETRY_BACKOFF_S = 0.5


def find_cuebert_root(start: Path | None = None) -> Path:
    """Walk parents from *start* until a directory containing ``.cuebert`` is found."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError(
        "Could not locate Cuebert hub root (no .cuebert directory in parent chain).",
    )


def workflows_dir() -> Path:
    """Directory containing allow-listed workflow JSON files."""
    return Path(__file__).resolve().parent.parent / "workflows"


def _is_comfyui_configured() -> bool:
    """True when base URL is explicitly set via env or hub shared vault."""
    env_url = os.environ.get("CUEBERT_COMFYUI_BASE_URL")
    if env_url is not None and str(env_url).strip():
        return True
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return False
        url = get_resolver().get_credential(_VAULT_CREDENTIAL_PATH)
        return bool(url and str(url).strip())
    except Exception:
        return False


def _get_mode_explicit() -> str | None:
    """Return ``live`` or ``dry_run`` if ``CUEBERT_COMFYUI_MODE`` is set, else None."""
    raw = os.environ.get("CUEBERT_COMFYUI_MODE")
    if raw is None or not str(raw).strip():
        return None
    m = str(raw).strip().lower()
    if m in ("live", "dry_run"):
        return m
    logger.warning("Unknown CUEBERT_COMFYUI_MODE=%r; treating as live.", raw)
    return "live"


def _get_mode() -> str:
    """Resolve effective toolkit mode.

    When ``CUEBERT_COMFYUI_MODE`` is unset and ComfyUI is not configured
    (no ``CUEBERT_COMFYUI_BASE_URL`` and no vault ``comfyui.base_url``),
    defaults to ``dry_run`` so MCP loads without a local server.

    Returns:
        ``live`` or ``dry_run``.
    """
    explicit = _get_mode_explicit()
    if explicit is not None:
        return explicit
    if not _is_comfyui_configured():
        return "dry_run"
    return "live"


def _resolve_base_url() -> str:
    """Resolve ComfyUI base URL: env, then vault, then localhost default."""
    global _VAULT_FALLBACK_LOGGED
    env_url = os.environ.get("CUEBERT_COMFYUI_BASE_URL")
    if env_url is not None and str(env_url).strip():
        return str(env_url).strip().rstrip("/")
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if CUEBERT_VAULT_AVAILABLE:
            v = get_resolver().get_credential(_VAULT_CREDENTIAL_PATH)
            if v and str(v).strip():
                return str(v).strip().rstrip("/")
    except Exception as exc:
        if not _VAULT_FALLBACK_LOGGED:
            logger.info(
                "ComfyUI vault URL unavailable (%s); using default %s",
                exc,
                _DEFAULT_BASE_URL,
            )
            _VAULT_FALLBACK_LOGGED = True
    if not _VAULT_FALLBACK_LOGGED and not _is_comfyui_configured():
        logger.info(
            "ComfyUI base URL not configured; using default %s (see vault-standard.md).",
            _DEFAULT_BASE_URL,
        )
        _VAULT_FALLBACK_LOGGED = True
    return _DEFAULT_BASE_URL.rstrip("/")


def _resolve_timeout() -> float:
    raw = os.environ.get("CUEBERT_COMFYUI_TIMEOUT_S", "120")
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 120.0


def _resolve_poll_interval() -> float:
    raw = os.environ.get("CUEBERT_COMFYUI_POLL_INTERVAL_S", "2")
    try:
        return max(0.2, float(raw))
    except ValueError:
        return 2.0


def _list_local_workflows() -> list[str]:
    """Return workflow names (JSON filename stems) from the skill ``workflows/`` dir."""
    d = workflows_dir()
    if not d.is_dir():
        return []
    names: list[str] = []
    for p in sorted(d.glob("*.json")):
        if p.is_file():
            names.append(p.stem)
    return names


def _workflow_path(name: str) -> Path | None:
    """Resolve *name* to a path under ``workflows/`` or None if invalid."""
    if not name or any(c in name for c in ("/", "\\", "..")):
        return None
    if name.strip() != name:
        return None
    path = (workflows_dir() / f"{name}.json").resolve()
    root = workflows_dir().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.is_file() else None


def sanitize_prompt_text(prompt_text: str) -> str:
    """Strip control characters and cap length (4096)."""
    cleaned = "".join(
        ch for ch in prompt_text if ord(ch) >= 32 or ch in "\n\r\t"
    )
    return cleaned[:4096]


class _SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that change host or scheme (same-netloc only)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        orig = urlparse(req.full_url)
        dest = urlparse(newurl)
        if dest.scheme and dest.scheme != orig.scheme:
            raise urllib.error.URLError("cross-scheme redirect rejected")
        if dest.netloc and dest.netloc != orig.netloc:
            raise urllib.error.URLError("cross-host redirect rejected")
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )


def _build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_SameHostRedirectHandler())


def _response_tail(body: bytes) -> str:
    if len(body) <= _MAX_RESPONSE_LOG_TAIL:
        return body.decode("utf-8", errors="replace")
    return body[-_MAX_RESPONSE_LOG_TAIL :].decode("utf-8", errors="replace")


def http_request_json(
    method: str,
    url: str,
    *,
    timeout: float,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any] | list[Any] | str | None, str | None]:
    """Perform HTTP request; return (status, json_or_none, error_message).

    On non-JSON success body, returns parsed None and no error (caller handles).
    Retries transient 5xx up to ``_MAX_RETRIES_5XX``.
    """
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")

    last_err: str | None = None
    opener = _build_opener()
    for attempt in range(_MAX_RETRIES_5XX):
        try:
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                status = resp.getcode() or 0
                if status >= 500 and attempt < _MAX_RETRIES_5XX - 1:
                    time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
                    continue
                if len(raw) > 500:
                    logger.debug(
                        "ComfyUI HTTP %s %s tail: %s",
                        method,
                        url,
                        _response_tail(raw),
                    )
                try:
                    parsed: Any = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    parsed = None
                return status, parsed if isinstance(parsed, (dict, list)) else None, None
        except urllib.error.HTTPError as exc:
            body = exc.read() if exc.fp else b""
            tail = _response_tail(body) if len(body) > 500 else body.decode(
                "utf-8", errors="replace"
            )
            if exc.code >= 500 and attempt < _MAX_RETRIES_5XX - 1:
                last_err = f"HTTP {exc.code}: {tail[:200]}"
                time.sleep(_RETRY_BACKOFF_S * (attempt + 1))
                continue
            return exc.code, None, f"HTTP {exc.code}: {tail[:500]}"
        except Exception as exc:
            return 0, None, str(exc)
    return 0, None, last_err or "request failed after retries"


def health_probe(base_url: str, timeout: float) -> dict[str, Any]:
    """HTTP GET ``/system_stats`` or dry-run synthetic result."""
    if _get_mode() == "dry_run":
        return {
            "reachable": True,
            "version": "dry_run",
            "queue_remaining": 0,
            "error": None,
            "dry_run": True,
        }
    url = f"{base_url.rstrip('/')}/system_stats"
    status, data, err = http_request_json("GET", url, timeout=timeout)
    if err or status != 200:
        return {
            "reachable": False,
            "version": None,
            "queue_remaining": None,
            "error": err or f"unexpected status {status}",
            "dry_run": False,
        }
    version = None
    queue_remaining = None
    if isinstance(data, dict):
        version = data.get("system", {}).get("comfyui_version") if isinstance(
            data.get("system"), dict
        ) else data.get("version")
        exec_info = data.get("exec_info")
        if isinstance(exec_info, dict) and "queue_remaining" in exec_info:
            try:
                queue_remaining = int(exec_info["queue_remaining"])
            except (TypeError, ValueError):
                queue_remaining = None
    return {
        "reachable": True,
        "version": str(version) if version is not None else None,
        "queue_remaining": queue_remaining,
        "error": None,
        "dry_run": False,
    }


def _inject_prompt_and_seed(
    workflow: dict[str, Any],
    prompt_text: str,
    seed: int | None,
    extra_params: dict[str, Any] | None,
) -> dict[str, Any]:
    """Apply prompt, seed, and shallow ``extra_params`` to a ComfyUI graph (M4-P1 stub)."""
    wf = copy.deepcopy(workflow)
    for _node_id, node in wf.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == "CLIPTextEncode":
            inputs = node.setdefault("inputs", {})
            if isinstance(inputs, dict):
                inputs["text"] = prompt_text
        if node.get("class_type") == "KSampler" and seed is not None:
            inputs = node.setdefault("inputs", {})
            if isinstance(inputs, dict):
                inputs["seed"] = seed
    if extra_params:
        for _node_id, node in wf.items():
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for k, v in extra_params.items():
                if k in inputs:
                    inputs[k] = v
    return wf


def submit_workflow(
    workflow_name: str,
    prompt_text: str,
    seed: int | None,
    extra_params: dict[str, Any] | None,
) -> dict[str, Any]:
    """Queue a workflow on ComfyUI or return a dry-run envelope."""
    allowed = _list_local_workflows()
    if workflow_name not in allowed:
        return {
            "prompt_id": None,
            "status": "failed",
            "dry_run": False,
            "error_code": "unknown_workflow",
            "error": f"No workflow file for name {workflow_name!r}",
        }

    if _get_mode() == "dry_run":
        h = hashlib.sha256(
            f"{workflow_name}:{prompt_text}:{seed}".encode()
        ).hexdigest()[:12]
        return {
            "prompt_id": f"dryrun-{h}",
            "status": "queued",
            "dry_run": True,
            "error_code": None,
            "error": None,
        }

    path = _workflow_path(workflow_name)
    if path is None:
        return {
            "prompt_id": None,
            "status": "failed",
            "dry_run": False,
            "error_code": "unknown_workflow",
            "error": f"No workflow file for name {workflow_name!r}",
        }

    with path.open("r", encoding="utf-8") as f:
        workflow = json.load(f)
    if not isinstance(workflow, dict):
        return {
            "prompt_id": None,
            "status": "failed",
            "dry_run": False,
            "error_code": "workflow_validation_error",
            "error": "Workflow JSON must be an object graph.",
        }

    wf_graph = _inject_prompt_and_seed(workflow, prompt_text, seed, extra_params)
    base = _resolve_base_url()
    client_id = "".join(
        random.choices(string.ascii_lowercase + string.digits, k=12)
    )
    payload = json.dumps({"prompt": wf_graph, "client_id": client_id}).encode("utf-8")
    url = f"{base}/prompt"
    status, data, err = http_request_json(
        "POST", url, timeout=_resolve_timeout(), data=payload
    )
    if err or status != 200 or not isinstance(data, dict):
        return {
            "prompt_id": None,
            "status": "failed",
            "dry_run": False,
            "error_code": "network_error" if err else "workflow_validation_error",
            "error": err or f"unexpected response status {status}",
        }
    pid = data.get("prompt_id")
    if not pid:
        return {
            "prompt_id": None,
            "status": "failed",
            "dry_run": False,
            "error_code": "workflow_validation_error",
            "error": "Missing prompt_id in ComfyUI response",
        }
    return {
        "prompt_id": str(pid),
        "status": "queued",
        "dry_run": False,
        "error_code": None,
        "error": None,
    }


def _parse_history_for_outputs(history: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Derive status string and image metadata dicts from a ComfyUI history entry."""
    status_str = "unknown"
    st = history.get("status")
    if isinstance(st, dict):
        status_str = str(st.get("status_str", "unknown"))
    images: list[dict[str, Any]] = []
    outputs = history.get("outputs")
    if isinstance(outputs, dict):
        for _nid, out in outputs.items():
            if not isinstance(out, dict):
                continue
            imgs = out.get("images")
            if isinstance(imgs, list):
                for im in imgs:
                    if isinstance(im, dict) and "filename" in im:
                        images.append(im)
    return status_str, images


def poll_status(prompt_id: str, max_wait_s: float) -> dict[str, Any]:
    """Poll ``/history/{prompt_id}`` until completion or timeout."""
    if prompt_id.startswith("dryrun-"):
        time.sleep(0.05)
        return {
            "status": "completed",
            "image_paths": ["<dry-run placeholder>"],
            "image_refs": [],
            "dry_run": True,
            "error_code": None,
            "error": None,
        }

    base = _resolve_base_url()
    timeout = _resolve_timeout()
    interval = _resolve_poll_interval()
    deadline = time.monotonic() + max_wait_s
    last_err: str | None = None

    while time.monotonic() < deadline:
        url = f"{base}/history/{urllib.parse.quote(prompt_id)}"
        status, data, err = http_request_json("GET", url, timeout=timeout)
        if err:
            last_err = err
            time.sleep(interval)
            continue
        if status != 200 or not isinstance(data, dict):
            last_err = f"HTTP {status}"
            time.sleep(interval)
            continue
        entry = data.get(prompt_id)
        if not isinstance(entry, dict):
            time.sleep(interval)
            continue
        status_str, image_refs = _parse_history_for_outputs(entry)
        if status_str in ("success", "completed"):
            return {
                "status": "completed",
                "image_paths": [str(i.get("filename", "")) for i in image_refs],
                "image_refs": image_refs,
                "dry_run": False,
                "error_code": None,
                "error": None,
            }
        if status_str in ("error", "failed"):
            return {
                "status": "failed",
                "image_paths": [],
                "image_refs": image_refs,
                "dry_run": False,
                "error_code": "comfyui_execution_error",
                "error": str(entry.get("status", {})),
            }
        if status_str in ("pending", "running", "executing"):
            time.sleep(interval)
            continue
        time.sleep(interval)

    return {
        "status": "failed",
        "image_paths": [],
        "image_refs": [],
        "dry_run": False,
        "error_code": "network_error",
        "error": last_err or "poll timeout",
    }


def fetch_asset(image_metadata: dict[str, Any], dest_path: str) -> dict[str, Any]:
    """Download output image to *dest_path* or write a dry-run ``.png.txt`` placeholder."""
    if _get_mode() == "dry_run" or image_metadata.get("type") == "dry_placeholder":
        p = Path(dest_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        placeholder = p.with_name(p.name + ".txt")
        text = (
            "Cuebert ComfyUI dry-run placeholder (no image bytes).\n"
            "Deferred to M4-P4 for real workflow output.\n"
        )
        placeholder.write_text(text, encoding="utf-8")
        return {"saved": str(placeholder), "dry_run": True, "bytes": 0}

    base = _resolve_base_url()
    filename = image_metadata.get("filename")
    if not filename:
        return {
            "saved": None,
            "dry_run": False,
            "bytes": 0,
            "error_code": "workflow_validation_error",
            "error": "image_metadata missing filename",
        }
    subfolder = image_metadata.get("subfolder") or ""
    typ = image_metadata.get("type") or "output"
    q = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": typ}
    )
    url = f"{base}/view?{q}"
    opener = _build_opener()
    try:
        with opener.open(url, timeout=_resolve_timeout()) as resp:
            data = resp.read()
    except Exception as exc:
        return {
            "saved": None,
            "dry_run": False,
            "bytes": 0,
            "error_code": "network_error",
            "error": str(exc),
        }
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"saved": str(dest), "dry_run": False, "bytes": len(data)}


def lookup_history(prompt_id: str) -> dict[str, Any]:
    """Single-shot history lookup (no polling) for ``comfyui_asset_status``."""
    if prompt_id.startswith("dryrun-"):
        return {
            "status": "completed",
            "assets": ["<dry-run placeholder>"],
            "error": None,
            "dry_run": True,
            "error_code": None,
        }
    base = _resolve_base_url()
    url = f"{base}/history/{urllib.parse.quote(prompt_id)}"
    status, data, err = http_request_json("GET", url, timeout=_resolve_timeout())
    if err:
        return {
            "status": "unknown",
            "assets": [],
            "error": err,
            "dry_run": False,
            "error_code": "network_error",
        }
    if status != 200 or not isinstance(data, dict):
        return {
            "status": "unknown",
            "assets": [],
            "error": f"HTTP {status}",
            "dry_run": False,
            "error_code": "network_error",
        }
    entry = data.get(prompt_id)
    if not isinstance(entry, dict):
        return {
            "status": "unknown",
            "assets": [],
            "error": None,
            "dry_run": False,
            "error_code": None,
        }
    status_str, image_refs = _parse_history_for_outputs(entry)
    assets = [str(i.get("filename", "")) for i in image_refs if i.get("filename")]
    if status_str in ("success", "completed"):
        return {
            "status": "completed",
            "assets": assets,
            "error": None,
            "dry_run": False,
            "error_code": None,
        }
    if status_str in ("error", "failed"):
        return {
            "status": "failed",
            "assets": assets,
            "error": str(entry.get("status", {})),
            "dry_run": False,
            "error_code": "comfyui_execution_error",
        }
    if status_str in ("pending", "running", "executing"):
        return {
            "status": "running",
            "assets": assets,
            "error": None,
            "dry_run": False,
            "error_code": None,
        }
    return {
        "status": "pending",
        "assets": assets,
        "error": None,
        "dry_run": False,
        "error_code": None,
    }
