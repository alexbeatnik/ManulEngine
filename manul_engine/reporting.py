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
from dataclasses import dataclass, field
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
class MissionResult:
    """Outcome of executing a single ``.hunt`` file (possibly with retries)."""
    file:        str                     # absolute path to the .hunt file
    name:        str                     # basename, e.g. "saucedemo.hunt"
    status:      str = "pass"            # "pass" | "fail" | "flaky" | "warning"
    attempts:    int = 1                 # total attempts (1 = no retries used)
    duration_ms: float = 0.0            # wall clock ms (total, including retries)
    error:       str | None = None       # last error message when status == "fail"
    steps:       list[StepResult] = field(default_factory=list)
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
