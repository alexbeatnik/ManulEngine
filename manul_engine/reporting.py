# manul_engine/reporting.py
"""
Data models for ManulEngine execution reporting.

Provides structured result objects that capture per-step and per-mission
execution data (timing, status, screenshots, errors).  The top-level
``RunSummary`` is consumed by the HTML report generator (reporter.py) and
can also be serialised to JSON for CI integrations.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StepResult:
    """Outcome of a single numbered step within a mission."""
    index:         int                     # 1-based step number
    text:          str                     # step text after variable substitution
    status:        str = "pass"            # "pass" | "fail" | "skip"
    duration_ms:   float = 0.0
    error:         str | None = None       # traceback / message on failure
    screenshot:    str | None = None       # base64-encoded PNG, or None
    logical_step:  str | None = None       # active STEP label when this step ran


@dataclass
class MissionResult:
    """Outcome of executing a single ``.hunt`` file (possibly with retries)."""
    file:        str                     # absolute path to the .hunt file
    name:        str                     # basename, e.g. "saucedemo.hunt"
    status:      str = "pass"            # "pass" | "fail" | "flaky"
    attempts:    int = 1                 # total attempts (1 = no retries used)
    duration_ms: float = 0.0            # wall clock ms (total, including retries)
    error:       str | None = None       # last error message when status == "fail"
    tags:        list[str] = field(default_factory=list)   # @tags from .hunt file
    steps:       list[StepResult] = field(default_factory=list)

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
    duration_ms: float = 0.0
    missions:    list[MissionResult] = field(default_factory=list)
