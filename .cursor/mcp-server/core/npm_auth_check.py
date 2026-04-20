"""MCP tool: npm registry authentication check.

Verifies that npm authentication is configured for private registries
by checking ``.npmrc`` files and vault credentials.  Solves the
recurring "I don't have npm credentials" failure mode where agents
can't find registry tokens.

Gaming-focused repos often have no npm private registry; this check stays
generic (Node/web) and is safe to omit when unused.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from _vault import CUEBERT_VAULT_AVAILABLE, find_cuebert_root, get_resolver, redact

_HUB_ROOT = find_cuebert_root(Path(__file__).resolve().parent)


def _find_npmrc_files(project_path: Path | None) -> list[dict]:
    """Locate all .npmrc files in the resolution chain."""
    locations = []

    if project_path:
        project_npmrc = project_path / ".npmrc"
        if project_npmrc.is_file():
            locations.append({
                "path": str(project_npmrc),
                "tier": "project",
                "exists": True,
            })

    hub_npmrc = _HUB_ROOT / ".npmrc"
    if hub_npmrc.is_file():
        locations.append({
            "path": str(hub_npmrc),
            "tier": "hub",
            "exists": True,
        })

    home_npmrc = Path.home() / ".npmrc"
    if home_npmrc.is_file():
        locations.append({
            "path": str(home_npmrc),
            "tier": "global",
            "exists": True,
        })

    return locations


def _check_npmrc_auth(npmrc_path: Path) -> dict:
    """Parse an .npmrc file for auth tokens and registry entries."""
    content = npmrc_path.read_text(encoding="utf-8", errors="replace")
    lines = content.strip().splitlines()

    registries = []
    has_auth_token = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        if "registry=" in stripped or "registry =" in stripped:
            registries.append(stripped.split("=", 1)[-1].strip())

        if "_authToken=" in stripped or "_auth=" in stripped:
            has_auth_token = True

        if ":_authToken=" in stripped:
            registry_scope = stripped.split(":_authToken=")[0]
            if registry_scope.startswith("//"):
                registries.append(registry_scope)

    return {
        "has_auth_token": has_auth_token,
        "registries": registries,
    }


def register(mcp: FastMCP) -> None:
    """Register npm auth tools on the given MCP server."""

    @mcp.tool()
    def npm_auth_check(
        project: str | None = None,
    ) -> dict:
        """Check if npm authentication is configured for private registries.

        Searches for ``.npmrc`` files in the project, hub, and user
        home directories.  Reports which registries have auth tokens
        and which don't.

        This solves the recurring problem where agents say "I don't
        have npm credentials" when the token exists in the hub vault.

        Args:
            project: Optional project directory path to check.

        Returns:
            A dict with discovered .npmrc files, their auth status,
            and vault npm credential availability.
        """
        project_path = Path(project) if project else None
        npmrc_files = _find_npmrc_files(project_path)

        file_results = []
        any_auth_found = False

        for npmrc_info in npmrc_files:
            info = _check_npmrc_auth(Path(npmrc_info["path"]))
            npmrc_info.update(info)
            file_results.append(npmrc_info)
            if info["has_auth_token"]:
                any_auth_found = True

        vault_npm = None
        if not CUEBERT_VAULT_AVAILABLE:
            vault_npm = {"found": False, "note": "cuebert_vault is not installed."}
        else:
            try:
                resolver = get_resolver(project_dir=project)
                npm_token = resolver.get_credential("npm.auth_token")
                if npm_token:
                    vault_npm = {
                        "found": True,
                        "redacted_value": redact(npm_token),
                    }
                else:
                    vault_npm = {"found": False}
            except Exception as exc:  # noqa: BLE001 — graceful fallback for vault unavailability
                vault_npm = {"found": False, "note": f"Vault not available: {exc}"}

        return {
            "authenticated": any_auth_found,
            "npmrc_files": file_results,
            "vault_npm_credential": vault_npm,
            "recommendation": (
                None if any_auth_found
                else "No npm auth token found. Check hub .cuebert/vault/shared/ "
                     "for npm credentials, or run 'npm login --registry=<url>'."
            ),
        }
