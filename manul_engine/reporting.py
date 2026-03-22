# manul_engine/reporting.py
"""
Data models for ManulEngine execution reporting.

Provides structured result objects that capture per-step and per-mission
execution data (timing, status, screenshots, errors).  The top-level
``RunSummary`` is consumed by the HTML report generator (reporter.py) and
can also be serialised to JSON for CI integrations.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class StepResult:
    """Outcome of a single numbered step within a mission."""
    index:         int                     # 1-based step number
    text:          str                     # step text after variable substitution
    status:        str = "pass"            # "pass" | "fail" | "skip" | "warning"
    duration_ms:   float = 0.0
    error:         str | None = None       # traceback / message on failure
    screenshot:    str | None = None       # base64-encoded PNG, or None
    logical_step:  str | None = None       # active STEP label when this step ran
    healed:        bool = False            # True when a stale cache entry was re-resolved via heuristics


@dataclass
class BlockResult:
    """Outcome of a logical STEP block within a mission."""

    name:        str
    status:      str = "pass"            # "pass" | "fail" | "warning"
    duration_ms: float = 0.0
    error:       str | None = None
    actions:     list[StepResult] = field(default_factory=list)


@dataclass
class MissionResult:
    """Outcome of executing a single ``.hunt`` file (possibly with retries)."""
    file:        str                     # absolute path to the .hunt file
    name:        str                     # basename, e.g. "saucedemo.hunt"
    status:      str = "pass"            # "pass" | "fail" | "flaky" | "warning"
    attempts:    int = 1                 # total attempts (1 = no retries used)
    duration_ms: float = 0.0            # wall clock ms (total, including retries)
    error:       str | None = None       # last error message when status == "fail"
    steps:       list[StepResult] = field(default_factory=list)
    blocks:      list[BlockResult] = field(default_factory=list)
    tags:        list[str] = field(default_factory=list)   # @tags from .hunt file
    soft_errors: list[str] = field(default_factory=list)   # collected VERIFY SOFTLY failures

    def __bool__(self) -> bool:         # truthy ⇔ not failed
        return self.status != "fail"


@dataclass
class RunSummary:
    """Aggregated outcome of an entire ``manul`` CLI invocation."""
    started_at:  str = ""               # ISO-8601 timestamp
    ended_at:    str = ""
    total:       int = 0
    passed:      int = 0
    failed:      int = 0
    flaky:       int = 0
    warning:     int = 0
    duration_ms: float = 0.0
    missions:    list[MissionResult] = field(default_factory=list)


# ── Run history persistence ──────────────────────────────────────────────────

_HISTORY_FILE = "run_history.json"
_REPORT_STATE_FILE = "manul_report_state.json"


def _step_from_dict(data: dict) -> StepResult:
    return StepResult(
        index=int(data.get("index", 0) or 0),
        text=str(data.get("text", "") or ""),
        status=str(data.get("status", "pass") or "pass"),
        duration_ms=float(data.get("duration_ms", 0.0) or 0.0),
        error=data.get("error"),
        screenshot=data.get("screenshot"),
        logical_step=data.get("logical_step"),
        healed=bool(data.get("healed", False)),
    )


def _block_from_dict(data: dict) -> BlockResult:
    return BlockResult(
        name=str(data.get("name", "") or ""),
        status=str(data.get("status", "pass") or "pass"),
        duration_ms=float(data.get("duration_ms", 0.0) or 0.0),
        error=data.get("error"),
        actions=[_step_from_dict(s) for s in data.get("actions", []) if isinstance(s, dict)],
    )


def _mission_from_dict(data: dict) -> MissionResult:
    return MissionResult(
        file=str(data.get("file", "") or ""),
        name=str(data.get("name", "") or ""),
        status=str(data.get("status", "pass") or "pass"),
        attempts=int(data.get("attempts", 1) or 1),
        duration_ms=float(data.get("duration_ms", 0.0) or 0.0),
        error=data.get("error"),
        steps=[_step_from_dict(s) for s in data.get("steps", []) if isinstance(s, dict)],
        blocks=[_block_from_dict(b) for b in data.get("blocks", []) if isinstance(b, dict)],
        tags=[str(t) for t in data.get("tags", []) if str(t).strip()],
        soft_errors=[str(e) for e in data.get("soft_errors", []) if str(e).strip()],
    )


def _summary_from_dict(data: dict) -> RunSummary:
    return RunSummary(
        started_at=str(data.get("started_at", "") or ""),
        ended_at=str(data.get("ended_at", "") or ""),
        total=int(data.get("total", 0) or 0),
        passed=int(data.get("passed", 0) or 0),
        failed=int(data.get("failed", 0) or 0),
        flaky=int(data.get("flaky", 0) or 0),
        warning=int(data.get("warning", 0) or 0),
        duration_ms=float(data.get("duration_ms", 0.0) or 0.0),
        missions=[_mission_from_dict(m) for m in data.get("missions", []) if isinstance(m, dict)],
    )


def recompute_summary(summary: RunSummary) -> RunSummary:
    """Normalize aggregate counters from the mission list."""
    missions = list(summary.missions)
    summary.total = len(missions)
    summary.passed = sum(1 for m in missions if m.status == "pass")
    summary.failed = sum(1 for m in missions if m.status == "fail")
    summary.flaky = sum(1 for m in missions if m.status == "flaky")
    summary.warning = sum(1 for m in missions if m.status == "warning")
    summary.duration_ms = sum(float(m.duration_ms or 0.0) for m in missions)
    return summary


def load_report_state(max_age_seconds: int | None = None) -> RunSummary | None:
    """Load recent persisted HTML-report state, or return None when stale/missing."""
    reports_dir = os.path.join(os.getcwd(), "reports")
    state_path = os.path.join(reports_dir, _REPORT_STATE_FILE)
    if max_age_seconds is None:
        try:
            max_age_seconds = int(os.getenv("MANUL_REPORT_SESSION_TTL_SEC", "1800"))
        except ValueError:
            max_age_seconds = 1800
    try:
        stat = os.stat(state_path)
    except OSError:
        return None
    now = datetime.now(timezone.utc).timestamp()
    if max_age_seconds > 0 and (now - stat.st_mtime) > max_age_seconds:
        return None
    try:
        raw = json.loads(open(state_path, encoding="utf-8").read())
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    return recompute_summary(_summary_from_dict(raw))


def save_report_state(summary: RunSummary) -> str:
    """Persist HTML-report state so multiple CLI invocations can share one report."""
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    state_path = os.path.join(reports_dir, _REPORT_STATE_FILE)
    normalized = recompute_summary(summary)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(asdict(normalized), fh, ensure_ascii=False, indent=2)
    return state_path


def merge_report_summaries(existing: RunSummary | None, current: RunSummary) -> RunSummary:
    """Merge recent report state with the current run, replacing duplicate files."""
    if existing is None or not existing.missions:
        return recompute_summary(current)

    merged = RunSummary(
        started_at=existing.started_at or current.started_at,
        ended_at=current.ended_at or existing.ended_at,
    )
    by_file: dict[str, MissionResult] = {}
    ordered_files: list[str] = []

    for mission in existing.missions + current.missions:
        file_key = str(mission.file or mission.name)
        if file_key not in by_file:
            ordered_files.append(file_key)
        by_file[file_key] = mission

    merged.missions = [by_file[file_key] for file_key in ordered_files if file_key in by_file]
    return recompute_summary(merged)


def append_run_history(mission: MissionResult) -> None:
    """Append a single run record to ``reports/run_history.json`` (JSON Lines).

    Each line is a self-contained JSON object with keys:
    ``file``, ``name``, ``timestamp``, ``status``, ``duration_ms``.
    """
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    history_path = os.path.join(reports_dir, _HISTORY_FILE)

    record = {
        "file": mission.file,
        "name": mission.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": mission.status,
        "duration_ms": round(mission.duration_ms, 1),
    }

    try:
        # Single low-level append write avoids interleaved/corrupted lines
        # when multiple worker subprocesses write concurrently.
        line = json.dumps(record, ensure_ascii=False).encode("utf-8") + b"\n"
        fd = os.open(history_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
    except OSError:
        pass  # best-effort — do not crash the run
