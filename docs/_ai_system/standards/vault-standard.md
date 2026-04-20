# CUEBERT VAULT STANDARD

> **SYSTEM ROLE:** Defines how agents and projects use the shared config vault.
> **Last Updated:** 2026-03-03
> **Scope:** All Cuebert-managed projects (Python, TypeScript/React, Go)

---

## 1. Overview

The **Cuebert Vault** provides every Cuebert-managed project with reusable
credentials, service endpoint profiles, LLM model aliases, and MCP
configurations.

**Architecture:** The vault uses a **hub-centric (control plane)** model.
Resolution tiers are **on the hub** (plus environment variables and a
legacy global fallback):

1. **Hub project vault** (`<hub>/.cuebert/vault/{project}/`) — centrally
   managed credentials for a specific workspace project, maintained in the
   `cuebert` repo.
2. **Hub shared vault** (`<hub>/.cuebert/vault/shared/`) — shared
   credentials (npm tokens, common API keys) available to all projects.

A legacy **global vault** (`~/.cuebert/`) is supported as a lowest-priority
fallback for environments that predate the hub layout.

Cuebert does **not** treat a separate credential tree under application repo
roots as a resolution tier; app configuration uses `.env` and environment
variables first (see **Priority Order**).

**Key principle:** The vault is **additive and optional**. Projects
that don't use the vault continue to work via `.env` files. When the
vault is present, it provides a second layer of configuration that
agents and settings loaders can draw from.

### Priority Order (highest wins)

1. **Environment variables** (already set in shell / `.env`)
2. **Hub project vault** (`<hub>/.cuebert/vault/{project}/credentials.yaml`)
3. **Hub shared vault** (`<hub>/.cuebert/vault/shared/credentials.yaml`)
4. **Global vault** (`~/.cuebert/vault/credentials.yaml`) — legacy fallback
5. **Hard-coded defaults** (if any — avoid)

First match wins after env vars. Prefer **hub project** for secrets that
belong to one workspace project; use **hub shared** for cross-project keys.

### Hub Discovery

The resolver discovers the **hub** from **control-plane context**: current
working directory, explicit `hub_dir` / `project_key` when provided, and
hub metadata such as **`workspace-manifest.json`** on the hub. It does
**not** depend on marker files inside application repositories for tier
resolution.

The workspace project key (used for `vault/{project}/` lookup) is resolved
from `workspace-manifest.json`, agent handoffs, or the application repo
folder name when aligned with `docs/projects/{project}/`.

---

## 2. Directory Structure

### Hub (cuebert — Single Source of Truth)

```
cuebert/                               # Hub
├── .cuebert/
│   ├── vault/
│   │   ├── shared/                      # Shared credentials (npm tokens, API keys)
│   │   │   └── credentials.yaml         # (perms: 0600)
│   │   ├── <project-key>/               # Per-project credentials (created by tooling)
│   │   │   └── credentials.yaml
│   │   └── README.md
│   └── workspace-manifest.json          # Registry of all projects + versions
├── registry/
│   ├── services.yaml                    # Master service definitions
│   └── models.yaml                      # LLM model catalog with aliases
└── scripts/
    ├── init-vault.py                    # Vault management entry point
    └── vault_installer/                 # Interactive installer package
```

### Global Vault (Legacy Fallback)

```
~/.cuebert/
├── vault/
│   └── credentials.yaml                # Legacy shared tokens (perms: 0600)
├── registry/
│   ├── apis.yaml                        # Legacy service profiles
│   ├── models.yaml                      # LLM model catalog (if no hub)
│   └── mcps.yaml                        # MCP server configs
└── config.yaml                          # Global Cuebert preferences
```

**Security:**
- `credentials.yaml` MUST have `0600` permissions (owner read/write only).
- NEVER commit `credentials.yaml` to version control.
- Hub vault directories are gitignored (selective pattern: `vault/*/credentials.yaml`).
- Use `python scripts/init-vault.py --verify` to check permissions and health.

---

## 3. Vault Files Reference

### A. credentials.yaml (Per-Project)

Flat YAML keyed by service name. Each top-level key is a service
(e.g. `sfdc`, `cx_playground`, `jira`) containing its credential
fields. Created during `--interactive` setup.

```yaml
sfdc:
  api_token: "sf-xxxx"
  proxy_url: "https://..."

cx_playground:
  api_key: "your-jwt"
  endpoint: "https://cxai-playground.cisco.com"
```

### B. services.yaml (Master Service Registry)

The single source of truth for service definitions. Lives at
`cuebert/registry/services.yaml` (authoritative copy on the hub).

```yaml
version: 2
services:
  sfdc:
    name: "Salesforce"
    category: data
    depends_on: [duo]
    fields:
      - {name: api_token, prompt: "SFDC API Token", secret: true}
    env_mapping:
      SFDC_API_TOKEN: sfdc.api_token
      DUO_CLIENT_ID: duo.client_id
    health_check:
      strategy: http
      method: GET
      url_template: "{sfdc.proxy_url}"
      expect_status: [200]
```

### C. services-local.yaml (Project Overrides)

Optional project-specific service extensions that merge with the
shipped `services.yaml`. Useful for adding custom services.

### D. manifest.yaml

Records which services were installed, when, and the env sync state.

### E. models.yaml (Global — Model Catalog)

Human-friendly aliases for LLM model identifiers.

```yaml
models:
  claude-sonnet-4:
    id: "us.anthropic.claude-sonnet-4-20250514-v1:0"
    provider: anthropic
    aliases: ["claude-sonnet", "sonnet-4", "Claude Sonnet"]
    context_window: 200000
    capabilities: [chat, function_calling, vision]
```

### F. .env Synchronization

The vault installer writes managed sections into `.env` using marker
comments. User-managed lines are preserved.

```env
# [vault:sfdc] Managed by Cuebert vault. Do not edit manually.
SFDC_API_TOKEN=sf-xxxx
DUO_CLIENT_ID=duo-id
# [vault:end]

# Your custom vars (untouched by vault sync)
DEBUG=true
LOG_LEVEL=info
```

---

## 4. Python Resolver Library (`cuebert_vault`)

The resolver lives at `cuebert/lib/cuebert_vault/` and can be installed into
any Python project via `pip install -e <path-to-cuebert>/lib/cuebert_vault`.

### Core API

```python
from cuebert_vault import FileVaultResolver

# Resolves hub from cwd / manifest / explicit paths — see Hub Discovery
vault = FileVaultResolver()

# Single credential lookup (resolves through the full chain)
token = vault.get_credential("sfdc.api_token")

# Resolve model alias → provider ID
model_id = vault.resolve_model("Claude Sonnet")
# → "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Get all env vars for a service
env = vault.get_service_env("sfdc")
# → {"SFDC_API_TOKEN": "...", "DUO_CLIENT_ID": "...", ...}

# Merge env vars for multiple services
env = vault.hydrate_env(["sfdc", "cx_playground", "langsmith"])

# Discovery
vault.list_services()   # → ["sfdc", "cx_playground", ...]
vault.list_models()     # → {"gpt-5.2": "gpt-5.2", "claude-sonnet-4": "us.anthropic..."}
vault.hub_dir           # → Path("/Users/.../cuebert") or None
vault.project_key       # → "kaces-backend" or None
```

### Explicit Hub Configuration

For scripts running outside a project directory, or when auto-discovery
is not desired, provide the hub and project key explicitly:

```python
from pathlib import Path
from cuebert_vault import FileVaultResolver

vault = FileVaultResolver(
    project_dir=Path("/path/to/kaces-backend"),
    hub_dir=Path("/path/to/cuebert"),
    project_key="kaces-backend",
)
```

### Exception Hierarchy

| Exception | When |
|-----------|------|
| `VaultError` | Base class for all vault errors |
| `VaultNotFoundError` | Neither project nor global vault directory found |
| `VaultCredentialMissingError` | Dotted path not found in credentials |
| `ModelAliasNotFoundError` | Model alias not in catalog |
| `ServiceNotFoundError` | Service name not in API registry |
| `HealthCheckError` | Service health check failed critically |
| `EnvSyncError` | `.env` sync encountered an unrecoverable error |
| `ServiceRegistryError` | Master `services.yaml` is invalid or missing |

### Graceful Degradation

If `~/.cuebert/` is missing or `PyYAML` is not installed:
- `get_credential()` returns `None`
- `get_service_env()` / `hydrate_env()` return `{}`
- A warning is logged (not raised)

Projects fall through to their `.env` / env vars as usual.

---

## 5. Integration Patterns

### A. Pydantic BaseSettings (Python — Recommended)

Use the vault as a **custom settings source** so that Pydantic loads
from `.env` first, then falls back to the vault.

```python
from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings

from cuebert_vault import FileVaultResolver


def _vault_source(settings: BaseSettings) -> dict[str, Any]:
    """Custom Pydantic settings source that reads from Cuebert vault."""
    vault = FileVaultResolver()
    return vault.hydrate_env(["sfdc", "cx_playground", "langsmith"])


class Settings(BaseSettings):
    """Application settings — env vars win, vault is fallback."""

    sfdc_api_token: str = Field(default="")
    openai_api_key: str = Field(default="")
    langchain_api_key: str = Field(default="")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        return (
            init_settings,       # 1. Constructor kwargs
            env_settings,        # 2. Environment variables
            dotenv_settings,     # 3. .env file
            _vault_source,       # 4. Cuebert vault (lowest priority)
            file_secret_settings,
        )
```

### B. Direct Vault Import (Python — Simple)

For scripts or services that don't use Pydantic settings:

```python
from cuebert_vault import FileVaultResolver

vault = FileVaultResolver()

# Resolve a model alias for LLM calls
model_id = vault.resolve_model("Claude Sonnet")

# Get a single credential
sfdc_token = vault.get_credential("sfdc.api_token")
```

### C. Model Config Integration (Python)

Replace hard-coded model ID strings with vault-resolved aliases:

```python
from cuebert_vault import FileVaultResolver

vault = FileVaultResolver()

MODEL_CONFIG = {
    "primary": vault.resolve_model("Claude Sonnet"),
    "fast": vault.resolve_model("gpt-4o-mini"),
    "summarizer": vault.resolve_model("gpt-5.2"),
}
```

### D. Environment Hydration (Node / TypeScript / React)

Node projects don't import the Python library directly.  Instead,
use one of these patterns:

**Option 1: Pre-hydrate `.env` via CLI**

```bash
# Future: cuebert inject will read vault and write .env
# For now, use init-vault.py --sync from the hub
python scripts/init-vault.py --sync
```

**Option 2: Read YAML with hub resolution (Node)**

```typescript
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { parse } from 'yaml';

/** Supply hub root from the multi-root workspace (e.g. env or known monorepo layout). */
function loadVaultCredential(
  dottedPath: string,
  hubRoot: string,
  projectKey: string,
): string | undefined {
  const home = process.env.HOME || '';

  // After env vars: hub/{project} → hub/shared → legacy global
  const candidates: string[] = [
    join(hubRoot, '.cuebert', 'vault', projectKey, 'credentials.yaml'),
    join(hubRoot, '.cuebert', 'vault', 'shared', 'credentials.yaml'),
    join(home, '.cuebert', 'vault', 'credentials.yaml'),
  ];

  for (const credsPath of candidates) {
    try {
      if (!existsSync(credsPath)) continue;
      const data = parse(readFileSync(credsPath, 'utf-8'));
      const value = dottedPath.split('.').reduce(
        (obj: any, key: string) => obj?.[key], data,
      );
      if (value !== undefined && value !== null) return String(value);
    } catch { continue; }
  }
  return undefined;
}
```

---

## 6. Agent Awareness

### For Coding Agents

When generating configuration or settings code for a Cuebert-managed
project:

1. **Check** if the project's `project-profile.md` mentions vault
   integration.
2. **If yes:** Generate settings code that uses `FileVaultResolver` as
   a fallback source (see Section 5A).
3. **If no:** Generate standard `.env`-based settings.  Mention vault
   as an optional enhancement.

### For Spec Agents

When designing a new service that needs credentials:

1. **List** which services from `~/.cuebert/registry/apis.yaml` are
   needed.
2. **Reference** the vault in the plan's "Configuration" section.
3. **Include** `cuebert_vault` as a project dependency.

### For Review Agents

During review, check:

- [ ] No hard-coded credentials in source code
- [ ] Settings use env vars (with vault as optional fallback)
- [ ] Model IDs use vault aliases where available
- [ ] `credentials.yaml` is NOT referenced in any commit

---

## 7. Setup & Maintenance

### First-Time Setup

```bash
# 1. Add the cuebert hub repo to the Cursor workspace (multi-root) alongside app repos.

# 2. Populate hub shared credentials
python scripts/init-vault.py --interactive

# 3. Verify vault health
python scripts/init-vault.py --check
```

### Adding Shared Credentials

Place credentials in the hub shared vault for all projects to access:

```bash
# Edit cuebert/.cuebert/vault/shared/credentials.yaml
# All workspace projects resolve these via the hub chain (after env vars)
```

### Adding Project-Specific Credentials

For credentials only one workspace project needs, use the **hub project**
vault:

- **Hub project:** `cuebert/.cuebert/vault/{project}/credentials.yaml`
  — centrally managed, visible in the hub, resolved when the project key
  matches `docs/projects/{project}/`.

### Adding a New Service

1. Add the service definition to `cuebert/registry/services.yaml`
2. Add credentials to the appropriate vault tier
3. Add the service schema to `scripts/init-vault.py` (`SERVICE_SCHEMA`)

### Adding a New Model

1. Add the model entry to `~/.cuebert/registry/models.yaml`
2. Include aliases for common short names

### Rotating Credentials

1. Update credentials in the hub vault (shared or per-project)
2. All projects using the vault pick up changes on next settings load
3. No per-project `.env` updates needed (unless using env sync)

---

## 8. Credential Intake Protocol (All Agents — Mandatory)

When a user provides a new credential during conversation (connection string,
API key, token, URI), the receiving agent MUST store it through the vault —
not only in `.env`.

### Trigger

Any of:
- User pastes a connection string, API key, or token
- User says "here is my [service] credential"
- A script or tool outputs a new credential that should persist

### Procedure

1. **IDENTIFY** the service (MongoDB, SFDC, TechZone, Jira, etc.)
2. **CHECK** if this service already exists in the vault chain
   (hub project vault → hub shared vault → legacy global)
3. **DETERMINE** the correct tier:

   | Condition | Tier | Location |
   |-----------|------|----------|
   | Used by multiple projects | Hub shared | `<hub>/.cuebert/vault/shared/credentials.yaml` |
   | Used by one workspace project | Hub project | `<hub>/.cuebert/vault/{project}/credentials.yaml` |
   | Legacy / non-hub environments only | Global (lowest) | `~/.cuebert/vault/credentials.yaml` |

4. **STORE** the credential in the correct `credentials.yaml` with the
   service name as the top-level key and field names matching the service
   definition in `registry/services.yaml`
5. **VERIFY** the service exists in `registry/services.yaml`. If not, add
   a service definition with `name`, `category`, `fields`, and `env_mapping`
6. **SYNC** the project's `.env` file if vault hydration is configured
   (write the managed block with `[vault:service]` markers)
7. **CONFIRM** to the user:
   ```
   Stored [service] credential in [tier] vault.
   Available to: [list of projects that can resolve it].
   ```

### Example

User provides a MongoDB URI:

```
Agent response:
  1. Service: mongodb (exists in registry/services.yaml)
  2. Tier: hub shared (used by kaces-backend and kaces-react)
  3. Stored in: cuebert/.cuebert/vault/shared/credentials.yaml
  4. Env mapping: MONGO_URI → mongodb.uri
  5. Available to: all workspace projects that resolve that hub tier
```

### What NOT to Do

- Do NOT only add the credential to `.env` and stop
- Do NOT hardcode credentials in source code or plan files
- Do NOT store credentials in the hub's `registry/services.yaml` (that file
  holds service *definitions*, not secrets)
- Do NOT skip the tier determination — putting everything in hub shared
  when a credential is single-project defeats the purpose of hub project
  vaults

---

## 9. Future Enhancements (Not In Scope)

| Enhancement | Description |
|-------------|-------------|
| Encryption at rest | Encrypt `credentials.yaml` with `age` or `sops` |
| `cuebert inject` CLI | Generate `.env` from vault for non-Python projects |
| MCP auto-config | Auto-configure Cursor's MCP settings from `mcps.yaml` |
| CI/CD integration | Vault-aware CI that reads from secrets manager |
