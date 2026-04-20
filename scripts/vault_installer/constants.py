"""Shared paths and defaults for the vault installer."""

from __future__ import annotations

from pathlib import Path

PROJECT_VAULT_REL = Path(".cuebert") / "vault"
CREDENTIALS_FILENAME = "credentials.yaml"
MANIFEST_FILENAME = "manifest.yaml"
SERVICES_LOCAL_FILENAME = "services-local.yaml"
SERVICES_FILENAME = "services.yaml"

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "registry" / SERVICES_FILENAME

CREDS_FILE_PERMS = 0o600
