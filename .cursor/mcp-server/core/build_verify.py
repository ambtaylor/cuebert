"""MCP tool: build verification.

Runs the four-check build verification gate (typecheck, lint, test, build)
for recognized **web/server** stacks (React/Node, Python, Go).

**Gaming** stacks (M6-P4): Unreal runs a bounded check chain via shipped
skill tools; Unity and Godot return ``skip_with_reason`` until M7. Non-game
repos with no markers return a structured ``not_applicable`` envelope when
no web/server stack applies.
"""

from __future__ import annotations

import concurrent.futures
import contextlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

# M6-P4: gaming check chain versioning. Bump when check set changes.
GAMING_BUILD_VERIFY_VERSION = "1.0.0"

_HUB_ROOT = Path(__file__).resolve().parents[3]  # .cursor/mcp-server/core/build_verify.py -> repo root
_SKILLS_ROOT = _HUB_ROOT / ".cursor" / "skills"


def _import_skill_tool(skill: str, tool: str):
    """Import a skill tool module by file path. Returns module or raises ImportError."""
    tools_dir = _SKILLS_ROOT / skill / "tools"
    tool_path = tools_dir / f"{tool}.py"
    if not tool_path.is_file():
        raise ImportError(f"Skill tool not found: {tool_path}")
    mod_name = f"cuebert_skills.{skill.replace('-', '_')}.{tool}"
    spec = importlib.util.spec_from_file_location(mod_name, tool_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for {tool_path}")
    insert_path = str(tools_dir)
    pushed = False
    if insert_path not in sys.path:
        sys.path.insert(0, insert_path)
        pushed = True
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if pushed:
            with contextlib.suppress(ValueError):
                sys.path.remove(insert_path)
    return module


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


def _scan_bases(project_path: Path) -> list[Path]:
    """Repo root and immediate child directories only (no deep crawl)."""
    bases = [project_path]
    try:
        for child in sorted(project_path.iterdir()):
            if child.is_dir():
                bases.append(child)
    except OSError:
        pass
    return bases


def _detect_gaming_stacks(project_path: Path) -> dict[str, Any]:
    """Detect Unreal / Unity / Godot markers (parity with agent-ops-onboard depth rules).

    Returns dict with keys: stacks (set of str), unreal_projects, unity_roots,
    godot_projects (lists of resolved Paths).
    """
    unreal_projects: list[Path] = []
    unity_roots: list[Path] = []
    godot_projects: list[Path] = []
    for base in _scan_bases(project_path):
        try:
            for entry in base.iterdir():
                if entry.is_file() and entry.suffix == ".uproject":
                    unreal_projects.append(entry.resolve(strict=False))
        except OSError:
            pass
        ver = base / "ProjectSettings" / "ProjectVersion.txt"
        if ver.is_file():
            unity_roots.append(base.resolve(strict=False))
        godot_file = base / "project.godot"
        if godot_file.is_file():
            godot_projects.append(godot_file.resolve(strict=False))
    stacks: set[str] = set()
    if unreal_projects:
        stacks.add("unreal")
    if unity_roots:
        stacks.add("unity")
    if godot_projects:
        stacks.add("godot")
    return {
        "stacks": stacks,
        "unreal_projects": sorted(set(unreal_projects), key=lambda p: str(p)),
        "unity_roots": sorted(set(unity_roots), key=lambda p: str(p)),
        "godot_projects": sorted(set(godot_projects), key=lambda p: str(p)),
    }


def _pick_unreal_project(paths: list[Path]) -> Path:
    return paths[0]


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
    """Classify web/server stack: explicit/lang/manifest/file, or not_applicable."""
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


def _run_with_timeout_s(seconds: float, fn: Callable[[], Any]) -> Any:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn)
        return fut.result(timeout=seconds)


def _gaming_envelope(
    *,
    status: str,
    mode: str,
    stack: str | None,
    project_path: str | None,
    checks: list[dict[str, Any]],
    reason: str | None,
    warnings: list[str],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "mode": mode,
        "stack": stack,
        "project_path": project_path,
        "checks": checks,
        "reason": reason,
        "warnings": warnings,
        "errors": errors,
        "version": GAMING_BUILD_VERIFY_VERSION,
    }


def _check_record(
    name: str,
    status: str,
    duration_s: float,
    detail: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "duration_s": duration_s,
        "detail": detail,
    }


def _host_ubt_platform() -> str:
    plat = sys.platform
    if plat == "darwin":
        return "Mac"
    if plat == "win32":
        return "Win64"
    return "Linux"


@contextlib.contextmanager
def _coerce_unreal_build_mode_dry_run():
    key = "CUEBERT_UNREAL_BUILD_MODE"
    if key in os.environ:
        previous = os.environ[key]
        had = True
    else:
        previous = None
        had = False
    os.environ[key] = "dry_run"
    try:
        yield
    finally:
        if had:
            os.environ[key] = previous
        else:
            del os.environ[key]


def _run_unreal_gaming_chain(project_root: Path, uproject: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    top_warnings: list[str] = []
    top_errors: list[str] = []
    proj_str = str(uproject.resolve(strict=False))
    top_mode = "live"
    chain_break = False

    # --- Check 1: unreal.status ---
    t0 = time.monotonic()
    detail1 = ""
    st1 = "error"
    raw1: dict[str, Any] | None = None
    try:
        mod = _import_skill_tool("unreal-build", "unreal_build_status")
    except ImportError as exc:
        duration = time.monotonic() - t0
        detail1 = f"code=build_verify.skill_not_found message={exc}"
        checks.append(_check_record("unreal.status", "error", duration, detail1))
        top_errors.append("build_verify.skill_not_found: unreal_build_status import failed")
        return _gaming_envelope(
            status="error",
            mode="live",
            stack="unreal",
            project_path=proj_str,
            checks=checks,
            reason="Skill import failed for unreal.status",
            warnings=top_warnings,
            errors=top_errors,
        )

    def _call_status() -> dict[str, Any]:
        return mod.unreal_build_status()

    try:
        raw1 = _run_with_timeout_s(30.0, _call_status)
    except TimeoutError:
        duration = time.monotonic() - t0
        detail1 = "unreal_build_status timed out after 30s"
        checks.append(_check_record("unreal.status", "error", duration, detail1))
        top_errors.append(detail1)
        return _gaming_envelope(
            status="error",
            mode="live",
            stack="unreal",
            project_path=proj_str,
            checks=checks,
            reason="unreal.status chain-breaking error",
            warnings=top_warnings,
            errors=top_errors,
        )
    except Exception as exc:
        duration = time.monotonic() - t0
        detail1 = f"unreal_build_status raised: {exc}"
        checks.append(_check_record("unreal.status", "error", duration, detail1))
        top_errors.append(detail1)
        return _gaming_envelope(
            status="error",
            mode="live",
            stack="unreal",
            project_path=proj_str,
            checks=checks,
            reason="unreal.status chain-breaking error",
            warnings=top_warnings,
            errors=top_errors,
        )

    duration = time.monotonic() - t0
    assert raw1 is not None
    rs = str(raw1.get("status", ""))
    top_mode = str(raw1.get("mode") or top_mode)
    if isinstance(raw1.get("warnings"), list):
        top_warnings.extend(str(w) for w in raw1["warnings"] if w is not None)

    if rs == "ok":
        st1 = "pass"
        detail1 = "engine resolution ok"
    elif rs == "dry_run":
        st1 = "dry_run"
        detail1 = "unreal_build_status dry_run"
    elif rs in ("not_configured", "invalid"):
        st1 = "fail"
        detail1 = str(raw1.get("reason") or rs)
    else:
        st1 = "error"
        detail1 = str(raw1.get("reason") or rs or "unexpected unreal_build_status status")
        chain_break = True

    checks.append(_check_record("unreal.status", st1, duration, detail1))

    if chain_break:
        top_errors.append(detail1)
        return _gaming_envelope(
            status="error",
            mode=top_mode,
            stack="unreal",
            project_path=proj_str,
            checks=checks,
            reason="unreal.status chain-breaking error",
            warnings=top_warnings,
            errors=top_errors,
        )

    # --- Check 2: unreal.build_dry_run ---
    if st1 not in ("pass", "dry_run"):
        checks.append(
            _check_record(
                "unreal.build_dry_run",
                "skip",
                0.0,
                "prerequisite: unreal.status != pass",
            )
        )
    else:
        t1 = time.monotonic()
        detail2 = ""
        st2 = "fail"
        target = os.environ.get("CUEBERT_BUILD_VERIFY_TARGET_NAME", "Editor")
        plat = _host_ubt_platform()
        try:
            mod_t = _import_skill_tool("unreal-build", "unreal_build_target")
        except ImportError as exc:
            duration = time.monotonic() - t1
            detail2 = f"code=build_verify.skill_not_found message={exc}"
            checks.append(_check_record("unreal.build_dry_run", "error", duration, detail2))
            top_errors.append("build_verify.skill_not_found: unreal_build_target import failed")
            return _gaming_envelope(
                status="error",
                mode=top_mode,
                stack="unreal",
                project_path=proj_str,
                checks=checks,
                reason="Skill import failed for unreal.build_dry_run",
                warnings=top_warnings,
                errors=top_errors,
            )

        def _call_target() -> dict[str, Any]:
            with _coerce_unreal_build_mode_dry_run():
                return mod_t.unreal_build_target(
                    project_path=proj_str,
                    target_name=target,
                    platform=plat,
                    config="Development",
                    caller="build-verify",
                )

        try:
            raw2 = _run_with_timeout_s(120.0, _call_target)
        except TimeoutError:
            duration = time.monotonic() - t1
            detail2 = "unreal_build_target timed out after 120s"
            st2 = "fail"
            checks.append(_check_record("unreal.build_dry_run", st2, duration, detail2))
        except Exception as exc:
            duration = time.monotonic() - t1
            detail2 = f"unreal_build_target raised: {exc}"
            st2 = "fail"
            checks.append(_check_record("unreal.build_dry_run", st2, duration, detail2))
        else:
            duration = time.monotonic() - t1
            r2 = str(raw2.get("status", ""))
            if r2 in ("dry_run", "pass"):
                st2 = "pass"
                detail2 = f"forced dry_run path; tool status={r2}"
            elif r2 in ("error", "timeout"):
                st2 = "fail"
                detail2 = str((raw2.get("error") or {}).get("message") or r2)
            else:
                st2 = "fail"
                detail2 = r2 or "unexpected unreal_build_target status"
            checks.append(_check_record("unreal.build_dry_run", st2, duration, detail2))

    # --- Check 3: vision.status (advisory) ---
    t2 = time.monotonic()
    detail3 = (
        "Advisory only: failure does not fail build_verify top-level status. "
        "vision-qa readiness probe."
    )
    try:
        mod_v = _import_skill_tool("vision-qa", "vision_qa_status")
    except ImportError as exc:
        duration = time.monotonic() - t2
        detail3 += f" ImportError: {exc}"
        checks.append(_check_record("vision.status", "fail", duration, detail3))
    else:

        def _call_vision() -> dict[str, Any]:
            return mod_v.vision_qa_status()

        try:
            raw3 = _run_with_timeout_s(10.0, _call_vision)
        except TimeoutError:
            duration = time.monotonic() - t2
            detail3 += " (timed out after 10s)"
            checks.append(_check_record("vision.status", "fail", duration, detail3))
        except Exception as exc:
            duration = time.monotonic() - t2
            detail3 += f" Exception: {exc}"
            checks.append(_check_record("vision.status", "fail", duration, detail3))
        else:
            duration = time.monotonic() - t2
            r3 = str(raw3.get("status", ""))
            if r3 in ("ok", "dry_run"):
                st3 = "pass"
                detail3 += f" status={r3}."
            else:
                st3 = "fail"
                detail3 += f" status={r3}."
            checks.append(_check_record("vision.status", st3, duration, detail3))

    # --- Top-level resolution (vision advisory) ---
    non_adv = [c for c in checks if c["name"] != "vision.status"]
    if any(c["status"] == "error" for c in non_adv):
        top_status = "error"
    elif any(c["status"] == "fail" for c in non_adv):
        top_status = "fail"
    elif all(c["status"] in ("pass", "dry_run", "skip") for c in non_adv):
        top_status = "pass"
    else:
        top_status = "fail"

    return _gaming_envelope(
        status=top_status,
        mode=top_mode,
        stack="unreal",
        project_path=proj_str,
        checks=checks,
        reason=None,
        warnings=top_warnings,
        errors=top_errors,
    )


def _not_applicable_envelope(reason: str) -> dict[str, Any]:
    return _gaming_envelope(
        status="not_applicable",
        mode="live",
        stack=None,
        project_path=None,
        checks=[],
        reason=reason,
        warnings=[],
        errors=[],
    )


def _multi_stack_error(paths_note: list[str]) -> dict[str, Any]:
    return _gaming_envelope(
        status="error",
        mode="live",
        stack=None,
        project_path=None,
        checks=[],
        reason="Multiple gaming stacks detected; ambiguous",
        warnings=paths_note,
        errors=["Multiple gaming stacks detected; ambiguous"],
    )


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


def build_verify(
    project: str | None = None,
    checks: list[str] | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Run build verification for *project* (defaults to current working directory).

    Gaming-aware envelope when a gaming stack is present or when no web/server
    stack applies after gaming detection. Web/server stacks keep the legacy
    dict shape on successful classification to ``run``.
    """
    project_path = Path(project).resolve(strict=False) if project else Path.cwd().resolve(strict=False)
    if not project_path.is_dir():
        return {"error": f"Project directory not found: {project}"}

    detected = _detect_gaming_stacks(project_path)
    stacks = detected["stacks"]
    if len(stacks) > 1:
        note: list[str] = []
        for p in detected["unreal_projects"]:
            note.append(f"unreal:{p}")
        for p in detected["unity_roots"]:
            note.append(f"unity:{p}")
        for p in detected["godot_projects"]:
            note.append(f"godot:{p}")
        return _multi_stack_error(note)

    if "unity" in stacks:
        root = detected["unity_roots"][0]
        return _gaming_envelope(
            status="skip_with_reason",
            mode="live",
            stack="unity",
            project_path=str(root.resolve(strict=False)),
            checks=[],
            reason="Unity build toolkit not yet ported (tracked for M7)",
            warnings=[],
            errors=[],
        )

    if "godot" in stacks:
        gpath = detected["godot_projects"][0]
        return _gaming_envelope(
            status="skip_with_reason",
            mode="live",
            stack="godot",
            project_path=str(gpath.resolve(strict=False)),
            checks=[],
            reason="Godot build toolkit not yet ported (tracked for M7)",
            warnings=[],
            errors=[],
        )

    if "unreal" in stacks:
        uproj = _pick_unreal_project(detected["unreal_projects"])
        return _run_unreal_gaming_chain(project_path, uproj)

    classified = _resolve_build_language(project_path, language)
    st = classified.get("status")
    if st == "not_applicable":
        raw = str(classified.get("reason") or "").strip()
        if raw.startswith("Unsupported language override"):
            reason_out = raw
        else:
            reason_out = (
                "No gaming stack detected (no .uproject, project.godot, or Unity "
                "ProjectSettings/ProjectVersion.txt)"
            )
        return _not_applicable_envelope(reason_out)

    if st == "run":
        lang = classified["language"]
        return _run_web_checks(project_path, lang, checks)

    return {
        "status": "not_applicable",
        "reason": f"Unexpected classification state: {classified!r}",
    }


_build_verify_fn = build_verify


def register(mcp: "FastMCP") -> None:
    """Register build verification tools on the given MCP server."""

    @mcp.tool()
    def build_verify(
        project: str,
        checks: list[str] | None = None,
        language: str | None = None,
    ) -> dict:
        """Run build verification checks for a project.

        **Gaming (M6-P4):** Detects Unreal (``.uproject``), Unity
        (``ProjectSettings/ProjectVersion.txt``), and Godot (``project.godot``)
        at the repo root or one directory deep. Unreal runs ``unreal_build_status``,
        a forced-dry-run ``unreal_build_target``, and an advisory ``vision_qa_status``.
        Unity/Godot return ``skip_with_reason`` until M7.

        **Web/server:** When no gaming markers match, runs typecheck / lint /
        test / build for React, Python, or Go when unambiguously detected.

        Args:
            project: Absolute path to the project root directory.
            checks: List of checks to run.  Valid values are
                ``typecheck``, ``lint``, ``test``, ``build``.
                Defaults to all four.
            language: Override language detection (``react``, ``python``,
                ``go``).  Auto-detected from manifest and project files if omitted.

        Returns:
            Gaming envelope (``status``, ``mode``, ``stack``, ``project_path``,
            ``checks``, ``reason``, ``warnings``, ``errors``, ``version``) or
            legacy web dict with ``project`` / ``language`` / ``checks`` map.
        """
        return _build_verify_fn(project=project, checks=checks, language=language)
