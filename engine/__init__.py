# engine/__init__.py
"""
ManulEngine — AI-powered browser automation engine.

Package structure:
    engine/
        __init__.py    — public API (re-exports ManulEngine)
        prompts.py     — configuration, thresholds, LLM prompts
        helpers.py     — pure utility functions and timing constants
        js_scripts.py  — JavaScript injected into the browser page
        scoring.py     — heuristic element-scoring algorithm
        cache.py       — persistent per-site controls cache mixin
        core.py        — ManulEngine class (LLM, resolution, mission runner)
        actions.py     — action execution mixin (click, type, select, hover, drag…)
        test/
            test_*.py  — synthetic DOM unit tests

Usage:
    from engine import ManulEngine

    manul = ManulEngine()
    await manul.run_mission("1. Navigate to ...")
"""

from .core import ManulEngine

__all__ = ["ManulEngine"]
