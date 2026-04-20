---
name: cert-game
description: Advisory cert-checklist scanner for game builds. Evaluates platform certification requirements (Steam, Epic, GOG, itch.io). Returns INFO/WARN findings only — never blocks ship.
---

# cert-game

Python MCP tools under `tools/` scan Unreal project metadata and optional staged build paths against twelve advisory checklists. Findings are **info** or **warn** only (`advisory_always` contract).

See `docs/_ai_system/agents/agent-cert-game.md`, `docs/_ai_system/standards/cert-game-checklists.md`, and `.cuebert/config/cert-game.yaml`.
