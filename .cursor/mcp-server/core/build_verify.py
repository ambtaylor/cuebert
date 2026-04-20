"""MCP tool: build verification.

Runs the four-check build verification gate (typecheck, lint, test, build)
for recognized **web/server** stacks (React/Node, Python, Go).

**Gaming** stacks (Unreal, Unity, Godot) return ``status: skip`` — full
engine build verification is deferred to M6 (Issue I-2). Unknown or empty
trees return ``not_applicable``; there is **no** default to React.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

_CHECK_COMMANDS: dict[str, dict[str, list[str]]] = {
    "react": {
        "typecheck": ["npx", "tsc", "--noEmit"],
        "lint": ["npx", "eslint", "src/", "--max-warnings=0"],
        "test": ["npx", "vitest", "run", "--reporter=verbose"],
        "build": ["npm", "run", "build"],
    },
    "python": {
        "typecheck": ["python", "-m", "mypy", "src/", "--ignore-missing-imports"],
        "lint": ["python", "-m", "ruff", "check", "src/"],
        "test": ["python", "-m", "pytest", "-q"],
        "build": ["python", "-c", "import py_compile; print('build: ok')"],
    },
    "go": {
        "typecheck": ["go", "vet", "./..."],
        "lint": ["golangci-lint", "run"],
        "test": ["go", "test", "./...", "-count=1"],
        "build": ["go", "build", "./..."],
    },
}

_MAX_OUTPUT_CHARS = 2000


def _run_check(cmd: list[str], cwd: Path) -> dict:
    """Execute a shell command and return structured result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        if len(output) > _MAX_OUTPUT_CHARS:
            output = output[:_MAX_OUTPUT_CHARS] + "\n...(truncated)"

        return {
            "pass": result.returncode == 0,
            "exit_code": result.returncode,
            "output": output or "(no output)",
        }
    except FileNotFoundError:
        return {
            "pass": False,
            "exit_code": -1,
            "output": f"Command not found: {cmd[0]}",
        }
    except subprocess.TimeoutExpired:
        return {
            "pass": False,
            "exit_code": -1,
            "output": f"Timed out after 120s: {' '.join(cmd)}",
        }


def _detect_gaming_engine(project_path: Path) -> str | None:
    """Return a short engine name if a gaming stack is detected, else None."""
    if any(project_path.glob("*.uproject")):
        return "unreal"
    if (project_path / "ProjectSettings").is_dir():
        return "unity"
    if (project_path / "project.godot").is_file():
        return "godot"
    return None


def _read_workspace_manifest_language(project_path: Path) -> str | None:
    """Return normalized language from ``.cuebert/workspace-manifest.json`` if set."""
    manifest = project_path / ".cuebert" / "workspace-manifest.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get("language")
    if raw is None and isinstance(data.get("hub"), dict):
        raw = data["hub"].get("language")
    if not raw or not isinstance(raw, str):
        return None
    lang = raw.strip().lower()
    return lang if lang in _CHECK_COMMANDS else None


def _read_version_json_language(project_path: Path) -> str | None:
    """Return language from ``.cuebert/version.json`` if present and recognized."""
    version_json = project_path / ".cuebert" / "version.json"
    if not version_json.is_file():
        return None
    try:
        data = json.loads(version_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    lang = str(data.get("language", "")).strip().lower()
    return lang if lang in _CHECK_COMMANDS else None


def _web_markers(project_path: Path) -> dict[str, bool]:
    """File-indicator presence for supported web/server stacks."""
    return {
        "react": (project_path / "package.json").is_file(),
        "python": (
            (project_path / "pyproject.toml").is_file()
            or (project_path / "requirements.txt").is_file()
        ),
        "go": (project_path / "go.mod").is_file(),
    }


def _infer_web_language_from_files(project_path: Path) -> str | None:
    """Pick a single web/server language from markers; None if zero or ambiguous."""
    markers = _web_markers(project_path)
    active = [k for k, v in markers.items() if v]
    if len(active) == 1:
        return active[0]
    if len(active) == 0:
        return None
    return None


def _resolve_build_language(project_path: Path, language: str | None) -> dict[str, Any]:
    """Classify stack: gaming skip, explicit/lang/manifest/file, or not_applicable."""
    gaming = _detect_gaming_engine(project_path)
    if gaming:
        return {
            "status": "skip",
            "reason": (
                "Gaming stack detected — full build verification lands in M6 "
                "(see Issue I-2 in cuebert-gaming-system plan)."
            ),
            "detected_engine": gaming,
        }

    if language:
        lang = language.strip().lower()
        if lang in _CHECK_COMMANDS:
            return {"status": "run", "language": lang}
        return {
            "status": "not_applicable",
            "reason": f"Unsupported language override: {language!r}.",
        }

    for fn in (_read_workspace_manifest_language, _read_version_json_language):
        lang = fn(project_path)
        if lang:
            return {"status": "run", "language": lang}

    inferred = _infer_web_language_from_files(project_path)
    if inferred:
        return {"status": "run", "language": inferred}

    markers = _web_markers(project_path)
    if any(markers.values()):
        active = [k for k, v in markers.items() if v]
        return {
            "status": "not_applicable",
            "reason": f"Ambiguous build stack (multiple markers): {', '.join(sorted(active))}.",
        }

    return {
        "status": "not_applicable",
        "reason": "No recognized build stack detected.",
    }


def _run_web_checks(project_path: Path, lang: str, checks: list[str] | None) -> dict:
    """Execute the legacy four-check gate for a supported web/server language."""
    commands = _CHECK_COMMANDS[lang]
    requested = checks or list(commands.keys())
    unknown = set(requested) - set(commands.keys())
    if unknown:
        return {"status": "not_applicable", "reason": f"Unknown checks: {sorted(unknown)}"}

    results: dict[str, dict] = {}
    all_pass = True
    for check_name in requested:
        cmd = commands[check_name]
        result = _run_check(cmd, project_path)
        results[check_name] = result
        if not result["pass"]:
            all_pass = False

    return {
        "status": "pass" if all_pass else "fail",
        "project": str(project_path),
        "language": lang,
        "all_pass": all_pass,
        "checks": results,
    }


def register(mcp: FastMCP) -> None:
    """Register build verification tools on the given MCP server."""

    @mcp.tool()
    def build_verify(
        project: str,
        checks: list[str] | None = None,
        language: str | None = None,
    ) -> dict:
        """Run build verification checks for a project.

        Detects **gaming** stacks first (``.uproject``, Unity ``ProjectSettings/``,
        Godot ``project.godot``) and returns ``skip``. For **web/server** stacks
        (React/Node, Python, Go), runs typecheck / lint / test / build commands.
        Unknown or ambiguous trees return ``not_applicable`` — never defaults
        to React.

        Args:
            project: Absolute path to the project root directory.
            checks: List of checks to run.  Valid values are
                ``typecheck``, ``lint``, ``test``, ``build``.
                Defaults to all four.
            language: Override language detection (``react``, ``python``,
                ``go``).  Auto-detected from manifest and project files if omitted.

        Returns:
            For gaming: ``status``, ``reason``, ``detected_engine``.
            For unknown: ``status``, ``reason``.
            For executed runs: ``status`` (pass/fail), ``project``, ``language``,
            ``all_pass``, ``checks``.
        """
        project_path = Path(project)
        if not project_path.is_dir():
            return {"error": f"Project directory not found: {project}"}

        classified = _resolve_build_language(project_path, language)
        st = classified.get("status")
        if st in ("skip", "not_applicable"):
            return {k: v for k, v in classified.items() if k != "language"}

        if st == "run":
            lang = classified["language"]
            return _run_web_checks(project_path, lang, checks)

        return {
            "status": "not_applicable",
            "reason": f"Unexpected classification state: {classified!r}",
        }
