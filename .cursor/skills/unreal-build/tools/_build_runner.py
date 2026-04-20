"""Shared Unreal CLI build subprocess runner (UBT, UAT, editor-cmd).

Stdlib only: engine path resolution, vault hooks, dry-run vs live mode,
minimal env subprocess execution, path sanitization, and log tail helpers.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_VAULT_ENGINE_PATH_KEY = "unreal.engine_path"
_VAULT_BUILD_MODE_KEY = "unreal.build_mode"
_VAULT_BUILD_TIMEOUT_KEY = "unreal.build_timeout_s"
_MAX_OUTPUT_BYTES = 50 * 1024 * 1024
_MAX_HARD_TIMEOUT_S = 3600.0
_MAX_GAUNTLET_TIMEOUT_S = 1800.0
_TRUNC_MARKER = b"\n<truncated>\n"

_DRY_RUN_VERSION = "5.4.0-dry_run"
_DRY_RUN_PLATFORMS = ["Mac", "Win64", "Linux", "IOS", "Android"]
_DRY_RUN_BUILD_LOG: list[str] = [
    "LogInit: Display: Running engine for game: DryRunGame",
    "LogTargetPlatformManager: Display: Loaded TargetPlatform 'Mac'",
    "LogTargetPlatformManager: Display: Loaded TargetPlatform 'Win64'",
    "LogShaderCompilers: Display: Using Local Shader Compiler",
    "LogDerivedDataCache: Display: Memory: Max Cache Size: -1 MB",
    "LogUObjectArray: CloseDisregardForGC: 0/0 objects in disregard for GC pool",
    "LogBlueprint: Warning: [AssetLog] DryRunAsset: [Compiler] test warning",
    "LogTemp: Display: UBT target DryRunEditor Mac Development",
    "LogLinker: Warning: Package dry stub",
    "LogCook: Display: Cook by the book from dry run fixture",
    "LogCook: Display: Sandbox cleanup took 0.000s",
    "LogCookCommandlet: Display: Misc Cook Stats",
    "LogCook: Display: Cooked packages 42 Packages Remain 0 Total 42",
    "LogCook: Display: Cook Diagnostics: OpenFileHandles=128, VirtualMemory=8192MiB",
    "LogInit: Display: Engine is initialized. Leaving FEngineLoop::Init()",
    "LogDerivedDataCache: Display: ../../../Engine/DerivedDataCache/Compressed.ddp",
    "LogCook: Display: Discovering localized assets for cultures: en",
    "LogPackageLocalizationCache: Processed 0 localized package path(s) in 0.000s",
    "LogCook: Display: Cooked 42/42 packages (100.00%)",
    "LogCook: Display: Cook Platform Mac, Cook Time: 1.23s",
    "LogCook: Display: Cool stuff: Cook time:",
    "LogInit: Display: Warning/Error Summary: Warnings: 2 Errors: 0",
    "LogOutputDevice: Display: Packaging succeeded",
    "LogExit: Display: Exiting.",
]
_DRY_RUN_COMMANDLET_RESULT: dict[str, Any] = {
    "exit_code": 0,
    "duration_s": 12.3,
    "warnings": 2,
    "errors": 0,
}

_TARGET_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_PLATFORM_ALLOW = {"Win64", "Mac", "Linux", "IOS", "Android"}
_CONFIG_ALLOW = {"Debug", "DebugGame", "Development", "Shipping", "Test"}
_COMMANDLET_ARG_RE = re.compile(r"^[A-Za-z0-9=_.\-/+]{1,256}$")


def find_hub_root(start: Path | None = None) -> Path:
    """Locate repo root (directory containing ``.cuebert``)."""
    p = (start or Path(__file__).resolve()).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".cuebert").is_dir():
            return parent
    raise FileNotFoundError("Could not locate Cuebert hub root (.cuebert).")


def build_trace_timestamp() -> str:
    """Filesystem-safe UTC stamp for ``.cuebert/traces/build/<stamp>/``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _detect_platform() -> str:
    plat = sys.platform
    if plat == "darwin":
        return "mac"
    if plat == "win32":
        return "win"
    return "linux"


def _ue_host_bin_subdir() -> str:
    """Engine/Binaries/<subdir> for host editor binaries."""
    p = _detect_platform()
    if p == "mac":
        return "Mac"
    if p == "win":
        return "Win64"
    return "Linux"


def _vault_engine_path_raw() -> str | None:
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_ENGINE_PATH_KEY)
        if v and str(v).strip():
            return str(v).strip()
    except Exception as exc:
        logger.debug("vault engine path unavailable: %s", exc)
    return None


def _vault_mode_raw() -> str | None:
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_BUILD_MODE_KEY)
        if v is None or not str(v).strip():
            return None
        m = str(v).strip().lower()
        if m in ("live", "dry_run"):
            return m
        logger.warning("Unknown vault unreal.build_mode=%r; ignoring.", v)
    except Exception as exc:
        logger.debug("vault build mode unavailable: %s", exc)
    return None


def _vault_timeout_raw() -> str | None:
    try:
        from _vault import CUEBERT_VAULT_AVAILABLE, get_resolver

        if not CUEBERT_VAULT_AVAILABLE:
            return None
        v = get_resolver().get_credential(_VAULT_BUILD_TIMEOUT_KEY)
        if v is not None and str(v).strip():
            return str(v).strip()
    except Exception as exc:
        logger.debug("vault build timeout unavailable: %s", exc)
    return None


def _resolve_engine_path() -> str | None:
    """Resolve absolute engine root or None."""
    env_p = os.environ.get("CUEBERT_UNREAL_ENGINE_PATH")
    if env_p is not None and str(env_p).strip():
        cand = str(env_p).strip()
        try:
            rp = Path(cand).expanduser().resolve(strict=True)
            if rp.is_dir():
                return str(rp)
        except (OSError, RuntimeError):
            return None
    vp = _vault_engine_path_raw()
    if vp:
        try:
            rp = Path(vp).expanduser().resolve(strict=True)
            if rp.is_dir():
                return str(rp)
        except (OSError, RuntimeError):
            pass
    host = _detect_platform()
    candidates: list[Path] = []
    bases: list[Path] = []
    if host == "mac":
        bases.append(Path("/Users/Shared/Epic Games"))
    elif host == "win":
        bases.append(Path("C:/Program Files/Epic Games"))
    else:
        bases.append(Path.home() / "Epic Games")
    for base in bases:
        try:
            if not base.is_dir():
                continue
            for child in sorted(base.iterdir(), key=lambda p: p.name):
                if child.is_dir() and child.name.startswith("UE_"):
                    candidates.append(child)
        except OSError:
            continue
    for child in candidates:
        try:
            eng = child.resolve(strict=True)
            if (eng / "Engine").is_dir():
                return str(eng)
        except (OSError, RuntimeError):
            continue
    return None


def _read_engine_version(engine_root: Path) -> str | None:
    ver_path = engine_root / "Engine" / "Build" / "Build.version"
    if not ver_path.is_file():
        return None
    try:
        data = json.loads(ver_path.read_text(encoding="utf-8"))
        major = int(data.get("MajorVersion", 0))
        minor = int(data.get("MinorVersion", 0))
        patch = int(data.get("PatchVersion", 0))
        cl = data.get("Changelist")
        base = f"{major}.{minor}.{patch}"
        if cl is not None:
            return f"{base}+{cl}"
        return base
    except Exception:
        return None


def _validate_engine_path(path: str) -> dict[str, Any]:
    """Probe engine layout for UBT, UAT, and headless editor binary."""
    plat = _detect_platform()
    out: dict[str, Any] = {
        "valid": False,
        "reason": "",
        "ubt_path": None,
        "uat_path": None,
        "editor_cmd_path": None,
        "version": None,
        "platform": plat,
    }
    try:
        root = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        out["reason"] = f"engine path not resolvable: {exc}"
        return out
    if not root.is_dir():
        out["reason"] = "engine path is not a directory"
        return out
    engine = root / "Engine"
    if not engine.is_dir():
        out["reason"] = "missing Engine/ under engine root"
        return out
    batch = engine / "Build" / "BatchFiles"
    ubt: Path | None = None
    uat: Path | None = None
    if plat == "win":
        ubt = batch / "RunUBT.bat"
        uat = batch / "RunUAT.bat"
    else:
        ubt = batch / "RunUBT.sh"
        uat = batch / "RunUAT.sh"
    bin_sub = _ue_host_bin_subdir()
    ed = engine / "Binaries" / bin_sub
    editor_cmd: Path | None = None
    if plat == "win":
        cand = ed / "UnrealEditor-Cmd.exe"
        if cand.is_file():
            editor_cmd = cand
    else:
        cand = ed / "UnrealEditor-Cmd"
        if cand.is_file():
            editor_cmd = cand
    out["version"] = _read_engine_version(root)
    out["ubt_path"] = str(ubt) if ubt and ubt.is_file() else None
    out["uat_path"] = str(uat) if uat and uat.is_file() else None
    out["editor_cmd_path"] = str(editor_cmd) if editor_cmd else None
    if not out["ubt_path"] or not out["uat_path"]:
        out["reason"] = "RunUBT or RunUAT script missing under Engine/Build/BatchFiles"
        return out
    if not out["editor_cmd_path"]:
        out["reason"] = f"UnrealEditor-Cmd not found under Engine/Binaries/{bin_sub}"
        return out
    out["valid"] = True
    out["reason"] = ""
    return out


def _engine_supports_live() -> bool:
    raw = _resolve_engine_path()
    if not raw:
        return False
    v = _validate_engine_path(raw)
    return bool(v.get("valid"))


def _get_mode_explicit() -> str | None:
    raw = os.environ.get("CUEBERT_UNREAL_BUILD_MODE")
    if raw is not None and str(raw).strip():
        m = str(raw).strip().lower()
        if m in ("live", "dry_run"):
            return m
        logger.warning("Unknown CUEBERT_UNREAL_BUILD_MODE=%r; treating as dry_run.", raw)
        return "dry_run"
    vm = _vault_mode_raw()
    if vm is not None:
        return vm
    return None


def _get_mode() -> str:
    """Resolve ``live`` vs ``dry_run`` (env > vault > engine-aware default).

    When unset, use ``live`` only if the engine path resolves and validation
    finds UBT, UAT, and editor-cmd; otherwise ``dry_run`` so MCP and harnesses
    work without a local UE install.
    """
    explicit = _get_mode_explicit()
    if explicit is not None:
        return explicit
    if _engine_supports_live():
        return "live"
    return "dry_run"


def _resolve_default_timeout_s() -> float:
    raw = os.environ.get("CUEBERT_UNREAL_BUILD_TIMEOUT_S")
    if raw is not None and str(raw).strip():
        try:
            return min(_MAX_HARD_TIMEOUT_S, max(1.0, float(raw)))
        except ValueError:
            pass
    vt = _vault_timeout_raw()
    if vt:
        try:
            return min(_MAX_HARD_TIMEOUT_S, max(1.0, float(vt)))
        except ValueError:
            pass
    return 600.0


def _cap_timeout(timeout_s: float | None) -> float:
    base = float(timeout_s) if timeout_s is not None else _resolve_default_timeout_s()
    return min(_MAX_HARD_TIMEOUT_S, max(1.0, base))


def _cap_gauntlet_timeout(timeout_s: float | None) -> float:
    """Clamp Gauntlet/UAT RunUnreal timeouts to **1800s** (30 minutes) max."""
    base = float(timeout_s) if timeout_s is not None else _resolve_default_timeout_s()
    return min(_MAX_GAUNTLET_TIMEOUT_S, max(1.0, base))


def _minimal_subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Inherit only PATH, HOME, temp dirs, and Windows program roots."""
    keys = [
        "PATH",
        "HOME",
        "USERPROFILE",
        "TMPDIR",
        "TEMP",
        "TMP",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
    ]
    env: dict[str, str] = {}
    for k in keys:
        v = os.environ.get(k)
        if v:
            env[k] = v
    if extra:
        env.update(extra)
    return env


def _truncate_bytes(data: bytes, max_bytes: int) -> bytes:
    if len(data) <= max_bytes:
        return data
    keep = max_bytes - len(_TRUNC_MARKER)
    if keep < 0:
        keep = 0
    return data[:keep] + _TRUNC_MARKER


def _run_subprocess(
    cmd: list[str],
    cwd: str,
    timeout: float,
    env_extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run *cmd* with ``shell=False`` and capped captured stdout/stderr."""
    start = time.monotonic()
    env = _minimal_subprocess_env(env_extra)
    out: dict[str, Any] = {
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "duration_s": 0.0,
        "timed_out": False,
        "error": None,
    }
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            shell=False,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
        out["exit_code"] = int(proc.returncode)
        raw_out = proc.stdout or b""
        raw_err = proc.stderr or b""
        raw_out = _truncate_bytes(raw_out, _MAX_OUTPUT_BYTES)
        raw_err = _truncate_bytes(raw_err, _MAX_OUTPUT_BYTES)
        out["stdout"] = raw_out.decode("utf-8", errors="replace")
        out["stderr"] = raw_err.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        out["timed_out"] = True
        out["error"] = str(exc)
        if exc.stdout:
            b = _truncate_bytes(exc.stdout, _MAX_OUTPUT_BYTES)
            out["stdout"] = b.decode("utf-8", errors="replace")
        if exc.stderr:
            b = _truncate_bytes(exc.stderr, _MAX_OUTPUT_BYTES)
            out["stderr"] = b.decode("utf-8", errors="replace")
    except Exception as exc:
        out["error"] = str(exc)
    out["duration_s"] = round(time.monotonic() - start, 4)
    return out


def _sanitize_target_name(name: str) -> str | None:
    if not name or not _TARGET_NAME_RE.fullmatch(name):
        return None
    return name


def _sanitize_platform(p: str) -> str | None:
    if p in _PLATFORM_ALLOW:
        return p
    return None


def _sanitize_config(c: str) -> str | None:
    if c in _CONFIG_ALLOW:
        return c
    return None


def _sanitize_project_path(p: str) -> str | None:
    try:
        path = Path(p).expanduser()
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    s = str(resolved)
    if not s.endswith(".uproject"):
        return None
    if not resolved.is_file():
        return None
    return s


def _uproject_dir(project_path: str) -> Path:
    return Path(project_path).resolve().parent


def _find_latest_log(project_path: str) -> str | None:
    logs = _uproject_dir(project_path) / "Saved" / "Logs"
    if not logs.is_dir():
        return None
    best: tuple[float, str] | None = None
    try:
        with os.scandir(logs) as it:
            for ent in it:
                if not ent.is_file(follow_symlinks=False):
                    continue
                if not ent.name.endswith(".log"):
                    continue
                try:
                    st = ent.stat(follow_symlinks=False)
                except OSError:
                    continue
                mtime = st.st_mtime
                if best is None or mtime > best[0]:
                    best = (mtime, ent.path)
    except OSError:
        return None
    return best[1] if best else None


def _tail_file(path: str, n_lines: int, max_bytes: int = 10_000_000) -> list[str]:
    """Return the last *n_lines* non-empty-oriented lines (memory-bounded)."""
    n_lines = max(1, min(100_000, n_lines))
    try:
        size = os.path.getsize(path)
    except OSError:
        return []
    read_size = min(max_bytes, size)
    try:
        with open(path, "rb") as fh:
            if size > read_size:
                fh.seek(size - read_size)
            chunk = fh.read()
    except OSError:
        return []
    text = chunk.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > n_lines:
        lines = lines[-n_lines:]
    return lines


def commandlets_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "commandlets"


def load_allowlisted_commandlets() -> set[str]:
    """Load commandlet ``name`` fields from JSON files under ``commandlets/``."""
    d = commandlets_dir()
    names: set[str] = set()
    if not d.is_dir():
        return names
    for p in sorted(d.glob("*.json")):
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            n = data.get("name")
            if isinstance(n, str) and n.strip():
                names.add(n.strip())
        except Exception as exc:
            logger.warning("skip malformed commandlet json %s: %s", p, exc)
    return names


def allow_unlisted_commandlets() -> bool:
    return os.environ.get("CUEBERT_UNREAL_BUILD_ALLOW_UNLISTED_COMMANDLETS", "").strip() == "1"


_COMMANDLET_NAME_BYPASS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,127}$")


def sanitize_commandlet_name_for_bypass(name: str) -> str | None:
    if not name or not _COMMANDLET_NAME_BYPASS_RE.fullmatch(name.strip()):
        return None
    return name.strip()


def sanitize_commandlet_extra_args(args: list[str] | None) -> tuple[list[str], str | None]:
    """Validate extra CLI args; return ``(cleaned, error_message)``."""
    if not args:
        return [], None
    out: list[str] = []
    for a in args:
        s = str(a)
        if not s or not _COMMANDLET_ARG_RE.fullmatch(s):
            return [], f"invalid commandlet arg (regex allowlist): {s!r}"
        out.append(s)
    return out, None


def _normalize_what_tried(what_tried: Any) -> str:
    if isinstance(what_tried, str):
        return what_tried
    return json.dumps(what_tried, ensure_ascii=False)


def troubleshoot_commit_safe(
    problem: str,
    what_tried: Any,
    *,
    why_tried: str | None = None,
    what_worked: str | None = None,
    tags: str | None = None,
    project: str | None = None,
    agent: str | None = None,
    plan_slug: str | None = None,
) -> dict[str, Any]:
    """Best-effort memory insert mirroring ``troubleshoot_commit``; never raises."""
    skills = Path(__file__).resolve().parents[2]
    mem_tools = skills / "memory-toolkit" / "tools"
    if not mem_tools.is_dir():
        sys.stderr.write(
            "unreal-build: memory-toolkit not found; skip troubleshoot_commit\n",
        )
        return {"status": "skipped", "error": "memory-toolkit not found"}

    inserted = False
    if str(mem_tools) not in sys.path:
        sys.path.insert(0, str(mem_tools))
        inserted = True
    try:
        from _memory_db import generate_embedding, get_db, _get_memory_mode

        wt_json = _normalize_what_tried(what_tried)
        rid = str(uuid.uuid4())
        day = date.today().isoformat()
        embed_text = "\n\n".join(
            part for part in (problem, wt_json, why_tried or "", what_worked or "") if part
        )
        embedding_blob = generate_embedding(embed_text)
        if embedding_blob is None and _get_memory_mode() == "text":
            logger.debug("memory_mode=text; skipping embedding for unreal-build")

        conn = get_db()
        conn.execute(
            """
                INSERT INTO troubleshooting (
                  id, date, project, agent, language, problem, what_tried,
                  why_tried, what_worked, tags, errors, files_touched,
                  plan_slug, milestone, transcript_id, source, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                rid,
                day,
                project,
                agent,
                None,
                problem,
                wt_json,
                why_tried,
                what_worked,
                tags,
                None,
                None,
                plan_slug,
                None,
                None,
                "agent",
                embedding_blob,
            ),
        )
        conn.commit()
        conn.close()
        logger.info("unreal-build troubleshoot_commit: id=%s", rid)
        return {"status": "ok", "id": rid}
    except Exception as exc:
        sys.stderr.write(f"unreal-build: troubleshoot_commit failed: {exc}\n")
        logger.warning("troubleshoot_commit_safe failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        if inserted:
            try:
                sys.path.remove(str(mem_tools))
            except ValueError:
                pass


def dry_run_build_log_excerpt(n: int = 20) -> list[str]:
    lines = list(_DRY_RUN_BUILD_LOG)
    return lines[-n:] if len(lines) > n else lines


def dry_run_constants() -> dict[str, Any]:
    return {
        "version": _DRY_RUN_VERSION,
        "platforms": list(_DRY_RUN_PLATFORMS),
        "commandlet": dict(_DRY_RUN_COMMANDLET_RESULT),
    }
