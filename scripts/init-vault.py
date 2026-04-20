#!/usr/bin/env python3
"""Cuebert Vault interactive setup and management.

Thin entry point that delegates to the ``vault_installer`` package.

Usage:
    python scripts/init-vault.py --interactive      # Full guided setup (new default)
    python scripts/init-vault.py --verify            # Re-run health checks
    python scripts/init-vault.py --sync              # Re-sync vault to .env
    python scripts/init-vault.py --check             # Local health (backward compat)
    python scripts/init-vault.py --add-service KEY   # Add a service
    python scripts/init-vault.py --list-services     # List available services

Options:
    --vault-dir DIR      Override project vault directory
    --registry PATH      Override master services.yaml path
    --no-color           Disable ANSI color output
    --yes                Skip confirmation prompts
    --no-health          Skip health checks during setup
    --verbose            Show debug output
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vault_installer.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
