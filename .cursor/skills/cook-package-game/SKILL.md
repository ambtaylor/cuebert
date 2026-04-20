---
name: cook-package-game
description: Orchestrate Unreal cook+package pipeline via UAT. Chains cook, stage, and package phases using unreal-build MCP tools. Returns structured phase envelope.
---

# cook-package-game

Python MCP skill tools under `tools/` orchestrate **BuildCookRun** phases (cook, stage, package) using configuration from `.cuebert/config/cook-package-game.yaml` and delegation into the **unreal-build** skill (`_build_runner`, optional UBT/commandlet entry points).

See `docs/_ai_system/agents/agent-cook-package-game.md` and `docs/_ai_system/standards/cook-package-commands.md`.
