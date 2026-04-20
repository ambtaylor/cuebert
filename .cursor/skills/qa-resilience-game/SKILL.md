---
name: qa-resilience-game
description: Scan Unreal Engine runtime logs and Gauntlet artifacts for resilience defects (frame hitches, memory leaks, crashes, streaming stalls). Returns structured findings consumable by agent-play-qa and /ship gates.
version: 0.1.0
status: alpha
---

## Purpose

Rule engine for `agent-qa-resilience-game`: stdlib + YAML config, read-only log scans, `dry_run` / `live` modes. Tools register with `cuebert-qa` MCP (`python .cursor/mcp-server/server.py --group qa`).

## Tools

| Module | Function |
| --- | --- |
| `qa_resilience_scan` | `qa_resilience_scan(log_path, config_path?, caller?)` |
| `qa_resilience_status` | `qa_resilience_status()` |

## Config

Default: `.cuebert/config/qa-resilience-game.yaml`. Rule IDs use the `resilience.*` namespace; legacy keys from the M7 catalogue (e.g. `hitch.frame_time_exceeded`) are honored as fallbacks for `severity` / `status`.

## Environment

- `CUEBERT_QA_RESILIENCE_MODE=dry_run` — synthetic findings, no file reads.
- Optional vault key `qa_resilience.mode` (placeholder): `dry_run` / `live`.

## Cross-references

- `docs/_ai_system/standards/qa-resilience-game-rules.md`
- `docs/_ai_system/agents/agent-qa-resilience-game.md`
