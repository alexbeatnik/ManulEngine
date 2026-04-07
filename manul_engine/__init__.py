# manul_engine/__init__.py
"""
ManulEngine — deterministic, DSL-first Web & Desktop Automation Runtime.

Package structure:
    manul_engine/
        __init__.py    — public API (re-exports ManulEngine, ManulSession)
        api.py         — ManulSession: high-level async context manager for Python scripts
        prompts.py     — configuration, thresholds, LLM prompts
        helpers.py     — pure utility functions and timing constants
        js_scripts.py  — JavaScript injected into the browser page
        scoring.py     — heuristic element-scoring algorithm
        cache.py       — persistent per-site controls cache mixin
        core.py        — ManulEngine class (LLM, resolution, mission runner)
        actions.py     — action execution mixin (click, type, select, hover, drag…)
        test/
            test_*.py  — synthetic DOM unit tests

Usage (Public Python API — no .hunt files needed):
    from manul_engine import ManulSession

    async with ManulSession(headless=True) as session:
        await session.navigate("https://example.com")
        await session.click("Log in button")
        await session.fill("Username field", "admin")
        await session.verify("Welcome")

Usage (DSL runner — .hunt files):
    from manul_engine import ManulEngine

    manul = ManulEngine()
    await manul.run_mission("1. Navigate to ...")

Custom controls:
    from manul_engine import ManulEngine, custom_control

    @custom_control(page="Login Page", target="Username")
    async def handle_username(page, action_type, value):
        await page.locator("#user").fill(value or "")
"""

from .api import ManulSession
from .config import EngineConfig
from .controls import custom_control
from .core import ManulEngine
from .exceptions import (
    ConfigurationError,
    ElementResolutionError,
    HookExecutionError,
    HuntImportError,
    ManulEngineError,
    ScheduleError,
    SessionError,
    VerificationError,
)
from .explain_next import ExplainNextDebugger, WhatIfResult
from .lifecycle import (
    GlobalContext,
    after_all,
    after_group,
    before_all,
    before_group,
)
from .variables import ScopedVariables

__all__ = [
    "ConfigurationError",
    "ElementResolutionError",
    "EngineConfig",
    "ExplainNextDebugger",
    "GlobalContext",
    "HookExecutionError",
    "HuntImportError",
    "ManulEngine",
    "ManulEngineError",
    "ManulSession",
    "ScheduleError",
    "ScopedVariables",
    "SessionError",
    "VerificationError",
    "WhatIfResult",
    "after_all",
    "after_group",
    "before_all",
    "before_group",
    "custom_control",
]
