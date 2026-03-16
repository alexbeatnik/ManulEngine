# manul_engine/test/test_43_scoped_variables.py
"""
Unit-test suite for ScopedVariables — strict four-level variable scoping.

Tests:
  1. Precedence: row > step > mission > global
  2. resolve() and resolve_level() correctness
  3. as_flat_dict() merging respects precedence
  4. substitute() placeholder replacement
  5. set / set_many / clear_level / clear_runtime
  6. dict-like interface (__contains__, __getitem__, get, items, update)
  7. dump() output format (DEBUG VARS)
  8. classify_step recognises DEBUG VARS
  9. Integration with substitute_memory backward compatibility

No network or browser required.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.variables import ScopedVariables
from manul_engine.helpers import classify_step

# ── Test helpers ──────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0


def _assert(condition: bool, name: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"    ✅  {name}")
    else:
        _FAIL += 1
        suffix = f" ({detail})" if detail else ""
        print(f"    ❌  {name}{suffix}")


# ── Section 1: Precedence hierarchy ──────────────────────────────────────────

def _test_precedence() -> None:
    print("\n  ── Precedence hierarchy ─────────────────────────────────────")

    sv = ScopedVariables()
    sv.set("email", "global@test.com", ScopedVariables.LEVEL_GLOBAL)
    sv.set("email", "mission@test.com", ScopedVariables.LEVEL_MISSION)
    sv.set("email", "step@test.com", ScopedVariables.LEVEL_STEP)
    sv.set("email", "row@test.com", ScopedVariables.LEVEL_ROW)

    _assert(sv.resolve("email") == "row@test.com",
            "Row vars (L1) have highest precedence")

    sv.clear_level(ScopedVariables.LEVEL_ROW)
    _assert(sv.resolve("email") == "step@test.com",
            "Step vars (L2) shadow mission after row cleared")

    sv.clear_level(ScopedVariables.LEVEL_STEP)
    _assert(sv.resolve("email") == "mission@test.com",
            "Mission vars (L3) shadow global after step cleared")

    sv.clear_level(ScopedVariables.LEVEL_MISSION)
    _assert(sv.resolve("email") == "global@test.com",
            "Global vars (L4) used when all higher levels cleared")

    sv.clear_level(ScopedVariables.LEVEL_GLOBAL)
    _assert(sv.resolve("email") is None,
            "Returns None when variable not found at any level")


# ── Section 2: resolve_level ─────────────────────────────────────────────────

def _test_resolve_level() -> None:
    print("\n  ── resolve_level ────────────────────────────────────────────")

    sv = ScopedVariables()
    sv.set("x", "1", ScopedVariables.LEVEL_GLOBAL)
    sv.set("x", "2", ScopedVariables.LEVEL_STEP)

    val, level = sv.resolve_level("x")
    _assert(val == "2", "resolve_level returns highest-priority value")
    _assert(level == ScopedVariables.LEVEL_STEP, "resolve_level returns correct level name")

    val2, level2 = sv.resolve_level("nonexistent")
    _assert(val2 is None and level2 is None, "resolve_level returns (None, None) for missing")


# ── Section 3: as_flat_dict ──────────────────────────────────────────────────

def _test_flat_dict() -> None:
    print("\n  ── as_flat_dict ─────────────────────────────────────────────")

    sv = ScopedVariables()
    sv.set("a", "global_a", ScopedVariables.LEVEL_GLOBAL)
    sv.set("b", "mission_b", ScopedVariables.LEVEL_MISSION)
    sv.set("a", "step_a", ScopedVariables.LEVEL_STEP)
    sv.set("c", "row_c", ScopedVariables.LEVEL_ROW)

    flat = sv.as_flat_dict()
    _assert(flat["a"] == "step_a", "Flat dict: step overrides global for 'a'")
    _assert(flat["b"] == "mission_b", "Flat dict: mission-only var preserved")
    _assert(flat["c"] == "row_c", "Flat dict: row-only var preserved")
    _assert(len(flat) == 3, "Flat dict size correct (3 unique keys)")


# ── Section 4: substitute ────────────────────────────────────────────────────

def _test_substitute() -> None:
    print("\n  ── substitute ───────────────────────────────────────────────")

    sv = ScopedVariables()
    sv.set("name", "Alice", ScopedVariables.LEVEL_MISSION)
    sv.set("name", "Bob", ScopedVariables.LEVEL_ROW)
    sv.set("age", "30", ScopedVariables.LEVEL_STEP)

    result = sv.substitute("Hello {name}, age {age}")
    _assert(result == "Hello Bob, age 30",
            "substitute uses highest-priority values")

    result2 = sv.substitute("No placeholders here")
    _assert(result2 == "No placeholders here",
            "substitute returns unchanged text when no placeholders")

    result3 = sv.substitute("{missing} stays")
    _assert(result3 == "{missing} stays",
            "substitute leaves unresolved placeholders intact")


# ── Section 5: set_many / clear_runtime ──────────────────────────────────────

def _test_set_many_clear() -> None:
    print("\n  ── set_many / clear_runtime ──────────────────────────────────")

    sv = ScopedVariables()
    sv.set_many({"x": "1", "y": "2"}, ScopedVariables.LEVEL_GLOBAL)
    _assert(sv.resolve("x") == "1" and sv.resolve("y") == "2",
            "set_many populates multiple vars at once")

    sv.set("r", "row", ScopedVariables.LEVEL_ROW)
    sv.set("s", "step", ScopedVariables.LEVEL_STEP)
    sv.clear_runtime()
    _assert(sv.resolve("r") is None, "clear_runtime removes row vars")
    _assert(sv.resolve("s") is None, "clear_runtime removes step vars")
    _assert(sv.resolve("x") == "1", "clear_runtime preserves global vars")


# ── Section 6: dict-like interface ───────────────────────────────────────────

def _test_dict_interface() -> None:
    print("\n  ── dict-like interface ───────────────────────────────────────")

    sv = ScopedVariables()
    sv.set("k", "v", ScopedVariables.LEVEL_MISSION)

    _assert("k" in sv, "__contains__ returns True for existing key")
    _assert("z" not in sv, "__contains__ returns False for missing key")

    _assert(sv["k"] == "v", "__getitem__ returns value")

    try:
        _ = sv["nonexistent"]
        _assert(False, "__getitem__ raises KeyError for missing", "no exception raised")
    except KeyError:
        _assert(True, "__getitem__ raises KeyError for missing")

    _assert(sv.get("k") == "v", "get() returns value for existing key")
    _assert(sv.get("z", "default") == "default", "get() returns default for missing key")

    sv["new"] = "via_setitem"
    _assert(sv.resolve("new") == "via_setitem", "__setitem__ writes to step level")
    val, level = sv.resolve_level("new")
    _assert(level == ScopedVariables.LEVEL_STEP, "__setitem__ targets step level")

    sv.update({"u1": "a", "u2": "b"})
    _assert(sv.resolve("u1") == "a", "update() populates step level")


# ── Section 7: dump ──────────────────────────────────────────────────────────

def _test_dump() -> None:
    print("\n  ── dump (DEBUG VARS) ─────────────────────────────────────────")

    sv = ScopedVariables()
    sv.set("token", "abc123", ScopedVariables.LEVEL_GLOBAL)
    sv.set("email", "test@test.com", ScopedVariables.LEVEL_MISSION)
    sv.set("otp", "999888", ScopedVariables.LEVEL_STEP)

    output = sv.dump()
    _assert("Level 1" in output, "dump contains Level 1 header")
    _assert("Level 2" in output, "dump contains Level 2 header")
    _assert("Level 3" in output, "dump contains Level 3 header")
    _assert("Level 4" in output, "dump contains Level 4 header")
    _assert("{token} = abc123" in output, "dump shows global var")
    _assert("{email} = test@test.com" in output, "dump shows mission var")
    _assert("{otp} = 999888" in output, "dump shows step var")
    _assert("(empty)" in output, "dump shows (empty) for row level")


# ── Section 8: classify_step for DEBUG VARS ──────────────────────────────────

def _test_classify_debug_vars() -> None:
    print("\n  ── classify_step: DEBUG VARS ─────────────────────────────────")

    _assert(classify_step("DEBUG VARS") == "debug_vars",
            "classify_step('DEBUG VARS') returns 'debug_vars'")
    _assert(classify_step("4. DEBUG VARS") == "debug_vars",
            "classify_step('4. DEBUG VARS') returns 'debug_vars'")
    _assert(classify_step("DEBUG") == "debug",
            "classify_step('DEBUG') still returns 'debug'")
    _assert(classify_step("PAUSE") == "debug",
            "classify_step('PAUSE') still returns 'debug'")


# ── Section 9: clear_all ─────────────────────────────────────────────────────

def _test_clear_all() -> None:
    print("\n  ── clear_all ─────────────────────────────────────────────────")

    sv = ScopedVariables()
    sv.set("a", "1", ScopedVariables.LEVEL_GLOBAL)
    sv.set("b", "2", ScopedVariables.LEVEL_MISSION)
    sv.set("c", "3", ScopedVariables.LEVEL_STEP)
    sv.set("d", "4", ScopedVariables.LEVEL_ROW)
    sv.clear_all()
    _assert(len(sv.as_flat_dict()) == 0, "clear_all removes all vars")


# ── Section 10: invalid level raises ValueError ─────────────────────────────

def _test_invalid_level() -> None:
    print("\n  ── invalid level error ───────────────────────────────────────")

    sv = ScopedVariables()
    try:
        sv.set("x", "1", "bogus")
        _assert(False, "set with invalid level raises ValueError", "no exception")
    except ValueError:
        _assert(True, "set with invalid level raises ValueError")

    try:
        sv.set_many({"x": "1"}, "bogus")
        _assert(False, "set_many with invalid level raises ValueError", "no exception")
    except ValueError:
        _assert(True, "set_many with invalid level raises ValueError")


# ── Run ───────────────────────────────────────────────────────────────────────

async def run_suite() -> None:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n📦 TEST SUITE: Scoped Variables (v0.0.9.4)")

    _test_precedence()
    _test_resolve_level()
    _test_flat_dict()
    _test_substitute()
    _test_set_many_clear()
    _test_dict_interface()
    _test_dump()
    _test_classify_debug_vars()
    _test_clear_all()
    _test_invalid_level()

    total = _PASS + _FAIL
    print(f"\n    SCORE: {_PASS}/{total}")
    if _FAIL:
        print(f"    ⚠️  {_FAIL} assertion(s) failed!")
