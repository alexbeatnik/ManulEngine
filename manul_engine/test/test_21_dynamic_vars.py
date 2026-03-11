# manul_engine/test/test_21_dynamic_vars.py
"""
Unit-test suite for Dynamic Variables via ``CALL PYTHON ... into {var}``.

No network or live browser is required.  All tests run against synthetic
state only.

Tests:
  1. Hook parser  -- ``execute_hook_line`` parses the ``into {var}`` suffix and
     populates ``HookResult.var_name`` and ``HookResult.return_value``.
  2. ``to`` alias -- ``CALL PYTHON mod.func to {var}`` is accepted as an alias.
  3. No clause    -- plain ``CALL PYTHON mod.func`` still works; no return value.
  4. Failure path -- exceptions in the called function still fail the step.
  5. Engine integration -- ``run_mission`` binds the return value into
     ``self.memory`` so that subsequent ``{placeholder}`` substitution works.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import types
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.hooks import HookResult, execute_hook_line

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


def _make_module(func_name: str, func) -> types.ModuleType:
    """Create a throw-away module object exposing *func* as *func_name*."""
    mod = types.ModuleType("_test_dynamic_mod")
    setattr(mod, func_name, func)
    return mod


# ── Section 1: Hook parser (execute_hook_line) ────────────────────────────────

def _test_hook_parser() -> None:
    print("\n  ── Hook parser (CALL PYTHON ... into {var}) ─────────────────")

    # Build a tiny module with a known function.
    def _get_code() -> str:
        return "998877"

    mod = _make_module("get_magic_code", _get_code)

    with patch("manul_engine.hooks._resolve_module", return_value=mod):
        # 1a. 'into {var}' syntax — return value bound, var_name set.
        result = execute_hook_line("CALL PYTHON mock_module.get_magic_code into {magic_code}")
        _assert(result.success, "into {var}: step succeeds", result.message)
        _assert(
            result.return_value == "998877",
            "into {var}: return_value is '998877'",
            f"got={result.return_value!r}",
        )
        _assert(
            result.var_name == "magic_code",
            "into {var}: var_name is 'magic_code'",
            f"got={result.var_name!r}",
        )

        # 1b. 'to {var}' alias.
        result_to = execute_hook_line("CALL PYTHON mock_module.get_magic_code to {magic_code}")
        _assert(result_to.success, "to {var} alias: step succeeds", result_to.message)
        _assert(
            result_to.return_value == "998877",
            "to {var} alias: return_value is '998877'",
            f"got={result_to.return_value!r}",
        )
        _assert(
            result_to.var_name == "magic_code",
            "to {var} alias: var_name is 'magic_code'",
            f"got={result_to.var_name!r}",
        )

        # 1c. No 'into' clause — return_value and var_name are None.
        result_plain = execute_hook_line("CALL PYTHON mock_module.get_magic_code")
        _assert(result_plain.success, "plain (no into): step succeeds", result_plain.message)
        _assert(
            result_plain.return_value is None,
            "plain (no into): return_value is None",
            f"got={result_plain.return_value!r}",
        )
        _assert(
            result_plain.var_name is None,
            "plain (no into): var_name is None",
            f"got={result_plain.var_name!r}",
        )

        # 1d. Function returning an integer — stored as a string.
        def _get_int() -> int:
            return 42

        int_mod = _make_module("get_int", _get_int)
        with patch("manul_engine.hooks._resolve_module", return_value=int_mod):
            result_int = execute_hook_line("CALL PYTHON mock_module.get_int into {answer}")
        _assert(result_int.success, "integer return value: step succeeds", result_int.message)
        _assert(
            result_int.return_value == "42",
            "integer return value: stored as string '42'",
            f"got={result_int.return_value!r}",
        )

        # 1e. Function raises — step must fail, return_value is None.
        def _boom() -> str:
            raise RuntimeError("db is on fire")

        err_mod = _make_module("boom", _boom)
        with patch("manul_engine.hooks._resolve_module", return_value=err_mod):
            result_err = execute_hook_line("CALL PYTHON mock_module.boom into {should_fail}")
        _assert(not result_err.success, "raised exception: step fails", result_err.message)
        _assert(
            result_err.return_value is None,
            "raised exception: return_value is None",
            f"got={result_err.return_value!r}",
        )

    # 1f. HookResult is still frozen / immutable.
    hr = HookResult(success=True, message="ok", return_value="x", var_name="v")
    try:
        hr.return_value = "mutated"  # type: ignore[misc]
        _assert(False, "HookResult is immutable (should have raised)")
    except (AttributeError, TypeError):
        _assert(True, "HookResult is immutable (frozen dataclass)")


# ── Section 2: Engine integration ────────────────────────────────────────────

async def _test_engine_integration() -> None:
    print("\n  ── Engine integration (run_mission binds CALL PYTHON return) ─")

    with patch("manul_engine.core.load_custom_controls"):
        from manul_engine.core import ManulEngine
        engine = ManulEngine(model=None, disable_cache=True)

    # Capture which step strings reach _execute_step.
    captured_steps: list[str] = []

    async def _fake_execute_step(
        page, step: str, strategic_context: str = "", step_idx: int = 0
    ) -> bool:
        captured_steps.append(step)
        return True

    # Minimal Playwright fakes.
    fake_page = MagicMock()
    fake_page.url = "https://example.com/otp"
    fake_page.evaluate = AsyncMock(return_value=None)
    fake_page.goto = AsyncMock()
    fake_page.wait_for_load_state = AsyncMock()

    fake_ctx = MagicMock()
    fake_ctx.new_page = AsyncMock(return_value=fake_page)
    fake_browser = MagicMock()
    fake_browser.new_context = AsyncMock(return_value=fake_ctx)
    fake_browser.close = AsyncMock()

    mock_browser_type = MagicMock()
    mock_browser_type.launch = AsyncMock(return_value=fake_browser)

    mock_playwright = MagicMock()
    mock_playwright.chromium = mock_browser_type
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)

    # A tiny module exposing the dynamic-OTP helper.
    def _fetch_otp() -> str:
        return "998877"

    otp_mod = _make_module("fetch_otp", _fetch_otp)

    mission = (
        "1. CALL PYTHON api_helpers.fetch_otp into {magic_code}\n"
        "2. Fill 'Security Code' with '{magic_code}'\n"
    )

    with (
        patch("manul_engine.core.async_playwright", return_value=mock_playwright),
        patch.object(engine, "_execute_step", side_effect=_fake_execute_step),
        patch("manul_engine.hooks._resolve_module", return_value=otp_mod),
    ):
        await engine.run_mission(mission)

    # 2a. CALL PYTHON step must NOT reach _execute_step (handled before it).
    _assert(
        len(captured_steps) == 1,
        "_execute_step called once (CALL PYTHON step consumed by engine)",
        f"count={len(captured_steps)}, steps={captured_steps!r}",
    )

    # 2b. Return value bound into engine.memory.
    _assert(
        engine.memory.get("magic_code") == "998877",
        "engine.memory['magic_code'] == '998877' after CALL PYTHON ... into {var}",
        f"memory={engine.memory}",
    )

    # 2c. The Fill step received the substituted value, not the raw placeholder.
    fill_step = captured_steps[0] if captured_steps else ""
    _assert(
        "998877" in fill_step,
        "Fill step received '998877' after {magic_code} substitution",
        f"step={fill_step!r}",
    )
    _assert(
        "{magic_code}" not in fill_step,
        "Raw {magic_code} placeholder absent from Fill step",
        f"step={fill_step!r}",
    )

    # 2d. 'to' alias also works end-to-end.
    captured_steps.clear()
    engine2 = ManulEngine(model=None, disable_cache=True)
    mission2 = (
        "1. CALL PYTHON api_helpers.fetch_otp to {token}\n"
        "2. Fill 'Token' with '{token}'\n"
    )
    with (
        patch("manul_engine.core.async_playwright", return_value=mock_playwright),
        patch.object(engine2, "_execute_step", side_effect=_fake_execute_step),
        patch("manul_engine.hooks._resolve_module", return_value=otp_mod),
    ):
        await engine2.run_mission(mission2)

    _assert(
        engine2.memory.get("token") == "998877",
        "engine2.memory['token'] == '998877' with 'to {var}' alias",
        f"memory={engine2.memory}",
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  test_21_dynamic_vars — CALL PYTHON ... into {var}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    _test_hook_parser()
    await _test_engine_integration()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    return _FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(run_suite())
    sys.exit(0 if ok else 1)
