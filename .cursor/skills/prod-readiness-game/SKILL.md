---
name: prod-readiness-game
description: Scan Unreal Engine project configuration files (DefaultEngine.ini, DefaultGame.ini, Build.cs, .uproject) for production-readiness defects. Returns structured findings with INFO/REJECT severity duality.
version: 0.1.0
status: alpha
---

## Purpose

Rule engine for `agent-prod-readiness-game`: static config scans only (no subprocesses). Exposes MCP tools on the `cuebert-qa` server.

## Tools

| Module | Function |
| --- | --- |
| `prod_readiness_scan` | `prod_readiness_scan(project_path, target_platform?, target_store?, build_config?, config_path?, caller?)` |
| `prod_readiness_status` | `prod_readiness_status()` |

## Config

Hub defaults: `.cuebert/config/prod-readiness-game.yaml`. Rule IDs use the `readiness.*` namespace; catalogue keys such as `metadata.game_name_set` are accepted as YAML aliases for severities and `status`.

## Environment

- `CUEBERT_PROD_READINESS_MODE=dry_run` — synthetic findings only.
- Vault placeholder: `prod_readiness.mode`.

## Cross-references

- `docs/_ai_system/standards/prod-readiness-game-rules.md`
- `docs/_ai_system/agents/agent-prod-readiness-game.md`
