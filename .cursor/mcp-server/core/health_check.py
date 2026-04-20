"""MCP tool: service health checks.

Runs data-driven health checks defined in ``registry/services.yaml``
against configured services.  Uses the vault resolver to obtain
credentials for authenticated checks.

Requires ``lib/cuebert_vault`` (install with ``pip install -e`` from that
directory). Until the resolver ships, this tool returns a clear error payload
instead of failing import-time.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from _vault import (
    CUEBERT_VAULT_AVAILABLE,
    find_cuebert_root,
    get_resolver,
    health_result_to_dict,
    run_health_check,
)

_HUB_ROOT = find_cuebert_root(Path(__file__).resolve().parent)


def _load_services_yaml() -> dict:
    """Load the master services registry from the hub."""
    import yaml

    path = _HUB_ROOT / "registry" / "services.yaml"
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def register(mcp: FastMCP) -> None:
    """Register health-check tools on the given MCP server."""

    @mcp.tool()
    def health_check(
        services: list[str] | None = None,
        project: str | None = None,
    ) -> dict:
        """Check connectivity for one or more registered services.

        Runs the health-check strategy defined in each service's
        ``registry/services.yaml`` entry (http, oauth_token, mongodb,
        neo4j).  Credentials are resolved from the vault automatically.

        Args:
            services: List of service names to check.  If omitted,
                checks all services that have a ``health_check`` block.
            project: Optional project directory for vault resolution.

        Returns:
            A dict with per-service results (status, latency, errors).
        """
        if not CUEBERT_VAULT_AVAILABLE or run_health_check is None:
            return {
                "results": [],
                "checked": 0,
                "passed": 0,
                "failed": 0,
                "missing": None,
                "error": (
                    "cuebert_vault is not installed; health checks need the resolver "
                    "and credential loader. See docs/_ai_system/standards/vault-standard.md."
                ),
            }

        registry = _load_services_yaml()
        all_services = registry.get("services", {})

        if services:
            targets = {k: v for k, v in all_services.items() if k in services}
            missing = set(services) - set(targets.keys())
        else:
            targets = {
                k: v for k, v in all_services.items()
                if "health_check" in v
            }
            missing = set()

        resolver = get_resolver(project_dir=project)
        creds = resolver._creds  # noqa: SLF001 — internal but needed for health checks

        results = []
        for svc_key, svc_def in targets.items():
            hc_config = svc_def.get("health_check")
            if not hc_config:
                results.append({
                    "service": svc_key,
                    "status": "skip",
                    "error": "No health_check config defined",
                })
                continue
            result = run_health_check(svc_key, hc_config, creds)
            results.append(health_result_to_dict(result))

        return {
            "results": results,
            "checked": len(results),
            "passed": sum(1 for r in results if r.get("status") == "pass"),
            "failed": sum(1 for r in results if r.get("status") == "fail"),
            "missing": list(missing) if missing else None,
        }
