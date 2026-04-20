"""Parse Gauntlet TestReport.json and optional JUnit XML (stdlib + optional defusedxml)."""

from __future__ import annotations

import io
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import defusedxml.ElementTree as DefusedET  # type: ignore[import-not-found]

    _DEFUSEDXML_AVAILABLE = True
except ImportError:
    DefusedET = None  # type: ignore[assignment,misc]
    _DEFUSEDXML_AVAILABLE = False


def _strip_doctype_decl(data: bytes) -> bytes:
    """Remove the first ``<!DOCTYPE ...>`` declaration (internal subset aware, best-effort)."""
    lower = data.lower()
    start = lower.find(b"<!doctype")
    if start < 0:
        return data
    i = start + 9
    n = len(data)
    in_bracket = False
    while i < n:
        b = data[i]
        if b == ord("["):
            in_bracket = True
        elif b == ord("]") and in_bracket:
            in_bracket = False
        elif b == ord(">") and not in_bracket:
            return data[:start] + data[i + 1 :]
        i += 1
    return data[:start]


def _xml_parser_stdlib() -> ET.XMLParser:
    """Stdlib XMLParser with hardening flags when supported (Python 3.13+)."""
    try:
        return ET.XMLParser(resolve_entities=False)  # type: ignore[call-arg]
    except TypeError:
        return ET.XMLParser()


def _safe_read_json(path: str, max_bytes: int = 10_000_000) -> dict[str, Any] | None:
    """Read JSON with size cap and UTF-8 decode (``errors='replace'``)."""
    try:
        rp = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not rp.is_file():
        return None
    try:
        size = rp.stat().st_size
    except OSError:
        return None
    if size > max_bytes:
        logger.warning("gauntlet json exceeds max_bytes cap: %s", path)
        return None
    try:
        text = rp.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _artifact_lists(entry: dict[str, Any]) -> tuple[list[str], list[str]]:
    screenshots: list[str] = []
    logs: list[str] = []
    arts = entry.get("artifacts")
    if not isinstance(arts, list):
        return screenshots, logs
    for a in arts:
        if not isinstance(a, dict):
            continue
        typ = str(a.get("type") or "")
        files = a.get("files")
        if not isinstance(files, list):
            continue
        paths = [str(f) for f in files if isinstance(f, str) and f]
        if typ == "Screenshot":
            screenshots.extend(paths)
        elif typ == "Log":
            logs.extend(paths)
    return screenshots, logs


def _first_error_message(errors: Any) -> str:
    if not isinstance(errors, list) or not errors:
        return ""
    first = errors[0]
    if isinstance(first, dict):
        msg = first.get("message")
        if isinstance(msg, str):
            return msg[:1000]
        return str(first)[:1000]
    return str(first)[:1000]


def parse_gauntlet_report(report_path: str, max_bytes: int = 10_000_000) -> dict[str, Any] | None:
    """Parse Gauntlet ``TestReport.json`` into a normalized summary dict."""
    data = _safe_read_json(report_path, max_bytes=max_bytes)
    if not data:
        return None
    tests = data.get("tests")
    if not isinstance(tests, list):
        return None

    passed = 0
    failed = 0
    skipped = 0
    failures: list[dict[str, Any]] = []

    td = data.get("totalDuration")
    if isinstance(td, (int, float)):
        duration_s = float(td)
    else:
        duration_s = 0.0
        for t in tests:
            if not isinstance(t, dict):
                continue
            dur = t.get("duration")
            if isinstance(dur, (int, float)):
                duration_s += float(dur)

    for t in tests:
        if not isinstance(t, dict):
            continue
        state = str(t.get("state") or "")
        if state == "Success":
            passed += 1
        elif state == "Fail":
            failed += 1
            name = str(t.get("testDisplayName") or t.get("fullTestPath") or "unknown")
            errs = t.get("errors")
            err_count = len(errs) if isinstance(errs, list) else 0
            shots, log_paths = _artifact_lists(t)
            failures.append(
                {
                    "name": name,
                    "error_count": err_count,
                    "first_error": _first_error_message(errs),
                    "artifacts": {"screenshots": shots, "logs": log_paths},
                },
            )
        elif state in ("Skipped", "NotRun"):
            skipped += 1
        else:
            skipped += 1

    total = len(tests)
    if total == 0 and isinstance(data.get("succeeded"), int):
        succ = int(data.get("succeeded") or 0)
        fail = int(data.get("failed") or 0)
        nr = int(data.get("notRun") or 0)
        total = succ + fail + nr
        passed = succ
        failed = fail
        skipped = nr

    if total == 0:
        return None

    return {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_s": duration_s,
        "failures": failures,
    }


def _local_tag(elem: ET.Element) -> str:
    return elem.tag.split("}")[-1]


def parse_gauntlet_xml_fallback(xml_path: str, max_bytes: int = 10_000_000) -> dict[str, Any] | None:
    """Parse JUnit-style XML (e.g. ``-writetestreporttype=junit``) into the normalized summary."""
    try:
        rp = Path(xml_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not rp.is_file():
        return None
    try:
        size = rp.stat().st_size
    except OSError:
        return None
    if size > max_bytes:
        return None
    try:
        raw = rp.read_bytes()
    except OSError:
        return None
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]

    root: ET.Element | None = None
    if _DEFUSEDXML_AVAILABLE and DefusedET is not None:
        try:
            root = DefusedET.parse(io.BytesIO(raw)).getroot()
        except Exception as exc:
            logger.debug("defusedxml junit parse failed: %s", exc)
            root = None
    if root is None:
        cleaned = _strip_doctype_decl(raw)
        parser = _xml_parser_stdlib()
        try:
            root = ET.fromstring(cleaned, parser=parser)
        except ET.ParseError as exc:
            logger.debug("stdlib junit parse failed: %s", exc)
            return None

    cases = [e for e in root.iter() if _local_tag(e) == "testcase"]
    if not cases:
        return None

    duration_s = 0.0
    for e in root.iter():
        if _local_tag(e) == "testsuite":
            try:
                duration_s += float(e.attrib.get("time") or 0.0)
            except ValueError:
                pass

    failed = 0
    skipped = 0
    failures: list[dict[str, Any]] = []
    for case in cases:
        name = case.attrib.get("name") or case.attrib.get("classname") or "unknown"
        children = list(case)
        skip_nodes = [c for c in children if _local_tag(c) == "skipped"]
        if skip_nodes:
            skipped += 1
            continue
        fail_nodes = [c for c in children if _local_tag(c) in ("failure", "error")]
        if fail_nodes:
            failed += 1
            fn = fail_nodes[0]
            msg = (fn.attrib.get("message") or (fn.text or "")).strip()
            failures.append(
                {
                    "name": str(name),
                    "error_count": len(fail_nodes),
                    "first_error": msg[:1000],
                    "artifacts": {"screenshots": [], "logs": []},
                },
            )

    total_tests = len(cases)
    passed = max(0, total_tests - failed - skipped)
    return {
        "total_tests": total_tests,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_s": duration_s,
        "failures": failures,
    }


def find_junit_fallback_path(gauntlet_log_subdir: Path) -> str | None:
    """Return path to a JUnit XML file under the Gauntlet log subdir, if any."""
    if not gauntlet_log_subdir.is_dir():
        return None
    for n in ("junit.xml", "JUnit.xml", "TestReport.xml", "report.xml"):
        p = gauntlet_log_subdir / n
        try:
            if p.is_file():
                return str(p.resolve(strict=True))
        except (OSError, RuntimeError):
            continue
    try:
        for p in sorted(gauntlet_log_subdir.glob("*.xml")):
            if p.is_file():
                return str(p.resolve(strict=True))
    except OSError:
        return None
    return None
