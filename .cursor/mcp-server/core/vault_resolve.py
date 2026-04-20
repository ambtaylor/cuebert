"""MCP tool: vault credential resolution.

Resolves credentials from the Cuebert vault using the three-tier chain:
  project .cuebert/vault/ -> hub .cuebert/vault/{project}/ -> hub .cuebert/vault/shared/

Returns redacted values so agents never see raw secrets.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver, redact


def register(mcp: FastMCP) -> None:
    """Register vault tools on the given MCP server."""

    @mcp.tool()
    def vault_resolve(
        credential_path: str,
        project: str | None = None,
    ) -> dict:
        """Resolve a credential from the Cuebert vault chain.

        Args:
            credential_path: Dotted path like ``sfdc.api_token`` or
                ``duo.client_secret``.
            project: Optional project directory path.  When provided,
                that project's vault is checked first.  Defaults to
                the hub.

        Returns:
            A dict with ``found``, ``redacted_value``, and ``path``.
        """
        if not CUEBERT_VAULT_AVAILABLE:
            return {
                "found": False,
                "credential_path": credential_path,
                "redacted_value": None,
                "message": (
                    "cuebert_vault is not installed. Install hub lib/cuebert_vault "
                    "(see docs/_ai_system/standards/vault-standard.md)."
                ),
            }

        resolver = get_resolver(project_dir=project)
        value = resolver.get_credential(credential_path)

        if value is None:
            return {
                "found": False,
                "credential_path": credential_path,
                "redacted_value": None,
                "message": (
                    f"Credential '{credential_path}' not found in any vault tier. "
                    "Run 'python scripts/init-vault.py --interactive' to configure."
                ),
            }

        return {
            "found": True,
            "credential_path": credential_path,
            "redacted_value": redact(value),
        }

    @mcp.tool()
    def vault_list_services(
        project: str | None = None,
    ) -> dict:
        """List all services available in the vault's API registry.

        Args:
            project: Optional project directory path for project-scoped
                service discovery.

        Returns:
            A dict with the list of available service names.
        """
        if not CUEBERT_VAULT_AVAILABLE:
            return {
                "services": [],
                "count": 0,
                "error": "cuebert_vault is not installed.",
            }

        resolver = get_resolver(project_dir=project)
        services = resolver.list_services()
        return {"services": services, "count": len(services)}

    @mcp.tool()
    def vault_get_service_env(
        service: str,
        project: str | None = None,
    ) -> dict:
        """Get environment variable mappings for a named service.

        Resolves credentials from the vault and returns the env-var
        names with redacted values.  Useful for verifying a service
        is properly configured without exposing secrets.

        Args:
            service: Service name (e.g. ``sfdc``, ``langsmith``).
            project: Optional project directory path.

        Returns:
            A dict mapping env-var names to redacted credential values.
        """
        if not CUEBERT_VAULT_AVAILABLE:
            return {"error": "cuebert_vault is not installed.", "service": service}

        resolver = get_resolver(project_dir=project)
        try:
            env_map = resolver.get_service_env(service)
        except Exception as exc:
            return {"error": str(exc), "service": service}

        redacted = {k: redact(v) for k, v in env_map.items()}
        return {
            "service": service,
            "configured": bool(env_map),
            "env_vars": redacted,
            "count": len(env_map),
        }
