# Cuebert Hub Vault

Centralized credential store for all Cuebert-managed projects.

## Structure

After cloning the hub, the vault directory only contains **shared** scaffolding.
Per-project vault folders (for example `my-app/`) and their `credentials.yaml`
files are created when you run:

```bash
python scripts/init-vault.py --interactive
```

Typical layout once projects are initialized:

```
vault/
├── shared/              # Shared credentials (npm tokens, common API keys)
├── <project-key>/       # Per-project credentials (created by init-vault / tooling)
└── README.md            # This file
```

## Resolution Order

When an agent or MCP tool needs credentials, the vault resolution chain is:

1. **Project `.cuebert/vault/`** — project-local overrides (highest priority)
2. **Hub `.cuebert/vault/{project}/`** — centrally-managed project credentials
3. **Hub `.cuebert/vault/shared/`** — shared credentials (npm tokens, common API keys)

First match wins. This means a project can override a shared credential by placing
its own version in its local vault.

## Security

- All credential files should have permissions `0600` (owner read/write only)
- Never commit credential files to version control
- The `.cuebert/` directory is gitignored by default
- Use `python scripts/init-vault.py --interactive` to populate credentials

## Registry note

`init-vault.py --interactive` reads service definitions from `registry/services.yaml`
(and optional `services-local.yaml` in the vault). If the registry has no `services`
entries yet, the installer will report an empty registry and exit — add definitions
before running interactive setup.
