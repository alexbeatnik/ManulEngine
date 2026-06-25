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
    from manul_engine import ControlContext, ManulEngine, custom_control

    @custom_control(page="Login Page", target="Username")
    async def handle_username(ctx: ControlContext) -> None:
        # ctx.page is a live Playwright Page.
        el = await ctx.page.query("#user")
        await el.fill(ctx.value or "")

    # ctx fields: page, action, value, target, page_name, url, step.

Page registry (since 0.0.9.30):
    Mappings live as one JSON fragment per site under <project>/pages/<safe_netloc>.json.
    Lean shape:    {"site": "https://example.com/", "Domain": "Example", ".*/login": "Login"}
    Wrapped shape: {"https://example.com/": {"Domain": "Example", ".*/login": "Login"}}
    Override the directory via MANUL_PAGES_DIR. Use `manul pages list` / `manul pages migrate`.
"""

from .api import ManulSession
from .config import EngineConfig
from .controls import ControlContext, custom_control, list_custom_controls
from .core import ManulEngine
from .exceptions import (
    ConditionalSyntaxError,
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
from .helpers import LoopBlock
from .lifecycle import (
    GlobalContext,
    after_all,
    after_group,
    before_all,
    before_group,
)
from .variables import ScopedVariables

__all__ = [
    "ConditionalSyntaxError",
    "ConfigurationError",
    "ControlContext",
    "ElementResolutionError",
    "EngineConfig",
    "ExplainNextDebugger",
    "GlobalContext",
    "HookExecutionError",
    "HuntImportError",
    "LoopBlock",
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
    "list_custom_controls",
]
