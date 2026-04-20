"""Orchestrate per-service health checks during the install flow.

Inlines data-driven health checks (originally ``cue_vault.health`` on the Cue hub)
so the installer stays self-contained under ``scripts/vault_installer/``.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .renderer import health_result_line

logger = logging.getLogger(__name__)

HEALTH_TIMEOUT_SECONDS = 5


class HealthStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class HealthResult:
    service: str
    status: HealthStatus
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None


_TEMPLATE_RE = re.compile(r"\{([^}]+)\}")


def _interpolate(template: str, credentials: dict[str, Any]) -> str:
    """Replace ``{service.field}`` placeholders with credential values."""

    def _replacer(match: re.Match[str]) -> str:
        path = match.group(1)
        parts = path.split(".")
        current: Any = credentials
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return match.group(0)
        return str(current) if current is not None else match.group(0)

    return _TEMPLATE_RE.sub(_replacer, template)


def _resolve_field(field_path: str, credentials: dict[str, Any]) -> str | None:
    """Resolve a dotted path like ``duo.client_id`` from the credentials dict."""
    parts = field_path.split(".")
    current: Any = credentials
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return str(current) if current is not None else None


def _check_http(
    service_key: str,
    health_config: dict[str, Any],
    credentials: dict[str, Any],
) -> HealthResult:
    """HTTP strategy: make a request and assert status code."""
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        return HealthResult(service=service_key, status=HealthStatus.FAIL, error="urllib not available")

    method = str(health_config.get("method", "GET")).upper()
    url_template = health_config.get("url_template", "")
    url = _interpolate(url_template, credentials)
    expect_status = health_config.get("expect_status", [200])

    req = urllib.request.Request(url, method=method)

    auth_type = health_config.get("auth")
    if auth_type == "basic":
        import base64
        user = _resolve_field(health_config.get("auth_user_field", ""), credentials) or ""
        token = _resolve_field(health_config.get("auth_token_field", ""), credentials) or ""
        encoded = base64.b64encode(f"{user}:{token}".encode()).decode()
        req.add_header("Authorization", f"Basic {encoded}")
    elif auth_type == "duo_oauth":
        pass

    raw_headers = health_config.get("headers", {})
    for header_name, header_val in raw_headers.items():
        req.add_header(header_name, _interpolate(str(header_val), credentials))

    start = time.monotonic()
    try:
        resp = urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT_SECONDS)
        latency = int((time.monotonic() - start) * 1000)
        code = resp.status
        if code in expect_status:
            return HealthResult(service=service_key, status=HealthStatus.PASS, status_code=code, latency_ms=latency)
        return HealthResult(
            service=service_key, status=HealthStatus.FAIL, status_code=code,
            latency_ms=latency, error=f"Unexpected status {code}",
        )
    except urllib.error.HTTPError as exc:
        latency = int((time.monotonic() - start) * 1000)
        if exc.code in expect_status:
            return HealthResult(service=service_key, status=HealthStatus.PASS, status_code=exc.code, latency_ms=latency)
        return HealthResult(
            service=service_key, status=HealthStatus.FAIL, status_code=exc.code,
            latency_ms=latency, error=str(exc),
        )
    except Exception as exc:
        latency = int((time.monotonic() - start) * 1000)
        return HealthResult(service=service_key, status=HealthStatus.FAIL, latency_ms=latency, error=str(exc))


def _check_oauth_token(
    service_key: str,
    health_config: dict[str, Any],
    credentials: dict[str, Any],
) -> HealthResult:
    """OAuth token strategy: POST client_credentials and check for access_token."""
    try:
        import urllib.request
        import urllib.error
        import urllib.parse
        import json
    except ImportError:
        return HealthResult(service=service_key, status=HealthStatus.FAIL, error="urllib not available")

    token_url = _resolve_field(health_config.get("url_field", ""), credentials)
    client_id = _resolve_field(health_config.get("client_id_field", ""), credentials)
    client_secret = _resolve_field(health_config.get("client_secret_field", ""), credentials)

    if not all([token_url, client_id, client_secret]):
        return HealthResult(
            service=service_key, status=HealthStatus.FAIL,
            error="Missing token URL, client ID, or client secret",
        )

    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()

    req = urllib.request.Request(
        token_url,  # type: ignore[arg-type]
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    start = time.monotonic()
    try:
        resp = urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT_SECONDS)
        latency = int((time.monotonic() - start) * 1000)
        data = json.loads(resp.read())
        if "access_token" in data:
            return HealthResult(service=service_key, status=HealthStatus.PASS, status_code=resp.status, latency_ms=latency)
        return HealthResult(
            service=service_key, status=HealthStatus.FAIL, status_code=resp.status,
            latency_ms=latency, error="No access_token in response",
        )
    except Exception as exc:
        latency = int((time.monotonic() - start) * 1000)
        return HealthResult(service=service_key, status=HealthStatus.FAIL, latency_ms=latency, error=str(exc))


def _check_mongodb(
    service_key: str,
    health_config: dict[str, Any],
    credentials: dict[str, Any],
) -> HealthResult:
    """MongoDB strategy: pymongo admin ping, skip if driver absent."""
    try:
        import pymongo  # noqa: WPS433
    except ImportError:
        return HealthResult(service=service_key, status=HealthStatus.SKIP, error="pymongo not installed")

    uri = _resolve_field(health_config.get("uri_field", ""), credentials)
    if not uri:
        return HealthResult(service=service_key, status=HealthStatus.FAIL, error="MongoDB URI not configured")

    start = time.monotonic()
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=HEALTH_TIMEOUT_SECONDS * 1000)
        client.admin.command("ping")
        latency = int((time.monotonic() - start) * 1000)
        client.close()
        return HealthResult(service=service_key, status=HealthStatus.PASS, latency_ms=latency)
    except Exception as exc:
        latency = int((time.monotonic() - start) * 1000)
        return HealthResult(service=service_key, status=HealthStatus.FAIL, latency_ms=latency, error=str(exc))


def _check_neo4j(
    service_key: str,
    health_config: dict[str, Any],
    credentials: dict[str, Any],
) -> HealthResult:
    """Neo4j strategy: driver verify_connectivity, skip if driver absent."""
    try:
        import neo4j  # noqa: WPS433
    except ImportError:
        return HealthResult(service=service_key, status=HealthStatus.SKIP, error="neo4j driver not installed")

    uri = _resolve_field(health_config.get("uri_field", ""), credentials)
    username = _resolve_field(health_config.get("username_field", ""), credentials)
    password = _resolve_field(health_config.get("password_field", ""), credentials)

    if not all([uri, username, password]):
        return HealthResult(service=service_key, status=HealthStatus.FAIL, error="Neo4j URI/username/password not configured")

    start = time.monotonic()
    try:
        driver = neo4j.GraphDatabase.driver(
            uri,  # type: ignore[arg-type]
            auth=(username, password),
            connection_timeout=HEALTH_TIMEOUT_SECONDS,
        )
        driver.verify_connectivity()
        latency = int((time.monotonic() - start) * 1000)
        driver.close()
        return HealthResult(service=service_key, status=HealthStatus.PASS, latency_ms=latency)
    except Exception as exc:
        latency = int((time.monotonic() - start) * 1000)
        return HealthResult(service=service_key, status=HealthStatus.FAIL, latency_ms=latency, error=str(exc))


_STRATEGY_MAP: dict[str, Any] = {
    "http": _check_http,
    "oauth_token": _check_oauth_token,
    "mongodb": _check_mongodb,
    "neo4j": _check_neo4j,
}


def run_health_check(
    service_key: str,
    health_config: dict[str, Any],
    credentials: dict[str, Any],
) -> HealthResult:
    """Dispatch to the correct health check strategy.

    Args:
        service_key: Service identifier (e.g. ``"sfdc"``).
        health_config: The ``health_check`` block from services.yaml.
        credentials: Flat or nested dict of all resolved credential values.

    Returns:
        A :class:`HealthResult` — never raises.
    """
    strategy = health_config.get("strategy", "")
    checker = _STRATEGY_MAP.get(strategy)
    if checker is None:
        return HealthResult(
            service=service_key, status=HealthStatus.SKIP,
            error=f"Unknown health check strategy: {strategy}",
        )
    return checker(service_key, health_config, credentials)


def check_service(
    service_key: str,
    health_config: dict[str, Any],
    credentials: dict[str, Any],
) -> HealthResult:
    """Run a single service health check and print the result."""
    result = run_health_check(service_key, health_config, credentials)

    print(f"  Verifying {service_key}... ", end="", flush=True)
    if result.status == HealthStatus.PASS:
        suffix = ""
        if result.status_code is not None:
            suffix = f" ({result.status_code}"
            if result.latency_ms is not None:
                suffix += f", {result.latency_ms}ms)"
            else:
                suffix += ")"
        print(f"OK{suffix}")
    elif result.status == HealthStatus.SKIP:
        print(f"SKIPPED — {result.error or 'no checker'}")
    else:
        print(f"FAILED — {result.error or 'unknown error'}")

    return result


def print_summary(
    results: list[HealthResult],
    services: dict[str, dict[str, Any]],
) -> None:
    """Print the aggregate health check results table."""
    print("\n=== Results ===")
    for r in results:
        name = services.get(r.service, {}).get("name", r.service)
        print(health_result_line(
            name,
            r.status.value,
            status_code=r.status_code,
            latency_ms=r.latency_ms,
            error=r.error,
        ))
    print()
