# manul_engine/test/test_45_api.py
"""
Unit-test suite for ManulSession (Public Python API).

Validates:
  1. Constructor and configuration pass-through.
  2. Step-string generation for all public methods.
  3. Async context-manager lifecycle (start / close).
  4. Memory / ScopedVariables access.
  5. run_steps() DSL dispatch.

No network or live browser required — all Playwright calls are mocked.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.api import ManulSession
from manul_engine.variables import ScopedVariables

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


# ── Section 1: Constructor pass-through ──────────────────────────────────────

def _test_constructor() -> None:
    print("\n  ── Constructor & configuration ─────────────────────────────")

    s = ManulSession(headless=True, browser="firefox", disable_cache=True)

    _assert(s.engine is not None, "engine attribute exists")
    _assert(s.engine.headless is True, "headless passed through")
    _assert(s.engine.browser == "firefox", "browser passed through")
    _assert(s.engine._controls_cache_enabled is False, "disable_cache passed through")
    _assert(s._page is None, "page is None before start()")
    _assert(isinstance(s.memory, ScopedVariables), "memory is ScopedVariables")

    s2 = ManulSession()
    _assert(s2.engine is not None, "default constructor succeeds")

    s3 = ManulSession(model="qwen2.5:0.5b", ai_threshold=500)
    _assert(s3.engine.model == "qwen2.5:0.5b", "model passed through")
    _assert(s3.engine._threshold == 500, "ai_threshold passed through")


# ── Section 2: Page property guard ───────────────────────────────────────────

def _test_page_guard() -> None:
    print("\n  ── Page property guard ─────────────────────────────────────")

    s = ManulSession()
    raised = False
    try:
        _ = s.page
    except RuntimeError:
        raised = True
    _assert(raised, "page raises RuntimeError before start()")


# ── Section 3: Step string generation ────────────────────────────────────────

async def _test_step_generation() -> None:
    """Verify that each public method builds the correct DSL step string."""
    print("\n  ── Step string generation ──────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)
    s._page = MagicMock()  # mock page so property doesn't raise

    captured_steps: list[str] = []

    async def capture_execute(page, step, strategic_context="", step_idx=0):
        captured_steps.append(step)
        return True

    async def capture_handler(page, step, *args, **kwargs):
        captured_steps.append(step)
        return True

    s._engine._execute_step = capture_execute
    s._engine._handle_right_click = capture_handler
    s._engine._handle_press = capture_handler
    s._engine._handle_upload = capture_handler
    s._engine._handle_scroll = AsyncMock()
    s._engine._handle_verify = capture_handler
    s._engine._handle_extract = AsyncMock(return_value=True)

    captured_steps.clear()
    await s.click("Log in button")
    _assert("Click the 'Log in button'" == captured_steps[-1],
            "click() generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.click("Image", double=True)
    _assert("DOUBLE CLICK the 'Image'" == captured_steps[-1],
            "click(double=True) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.fill("Username field", "admin")
    _assert("Fill 'Username field' with 'admin'" == captured_steps[-1],
            "fill() generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.select("Express", "Shipping Method")
    _assert("Select 'Express' from the 'Shipping Method' dropdown" == captured_steps[-1],
            "select() generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.hover("Menu")
    _assert("HOVER over the 'Menu'" == captured_steps[-1],
            "hover() generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.drag("Item A", "Box B")
    _assert("Drag the 'Item A' and drop it into 'Box B'" == captured_steps[-1],
            "drag() generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.right_click("Context Area")
    _assert("RIGHT CLICK 'Context Area'" == captured_steps[-1],
            "right_click() generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.press("Escape")
    _assert("PRESS Escape" == captured_steps[-1],
            "press(key) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.press("ArrowDown", target="Search Input")
    _assert("PRESS ArrowDown on 'Search Input'" == captured_steps[-1],
            "press(key, target) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.upload("avatar.png", "Profile Picture")
    _assert("UPLOAD 'avatar.png' to 'Profile Picture'" == captured_steps[-1],
            "upload() generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.verify("Welcome")
    _assert("VERIFY that 'Welcome' is present" == captured_steps[-1],
            "verify(present) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.verify("Error", present=False)
    _assert("VERIFY that 'Error' is NOT present" == captured_steps[-1],
            "verify(absent) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.verify("Submit", enabled=True)
    _assert("VERIFY that 'Submit' is ENABLED" == captured_steps[-1],
            "verify(enabled) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.verify("Submit", enabled=False)
    _assert("VERIFY that 'Submit' is DISABLED" == captured_steps[-1],
            "verify(disabled) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.verify("Terms", checked=True)
    _assert("VERIFY that 'Terms' is checked" == captured_steps[-1],
            "verify(checked) generates correct step",
            f"got: {captured_steps[-1]}")

    captured_steps.clear()
    await s.verify("Promo", checked=False)
    _assert("VERIFY that 'Promo' is NOT checked" == captured_steps[-1],
            "verify(not checked) generates correct step",
            f"got: {captured_steps[-1]}")


# ── Section 4: Navigate ──────────────────────────────────────────────────────

async def _test_navigate() -> None:
    print("\n  ── navigate() ─────────────────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    s._page = mock_page

    await s.navigate("https://example.com")
    mock_page.goto.assert_called_once()
    call_args = mock_page.goto.call_args
    _assert(call_args[0][0] == "https://example.com",
            "navigate() calls page.goto with correct URL")
    _assert(call_args[1]["wait_until"] == "domcontentloaded",
            "navigate() waits for domcontentloaded")
    _assert(s._engine.last_xpath is None,
            "navigate() clears last_xpath")


# ── Section 5: Wait ──────────────────────────────────────────────────────────

async def _test_wait() -> None:
    print("\n  ── wait() ─────────────────────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)

    import time
    t0 = time.perf_counter()
    await s.wait(0.1)
    elapsed = time.perf_counter() - t0
    _assert(elapsed >= 0.09, "wait() sleeps for requested duration",
            f"elapsed={elapsed:.3f}s")


# ── Section 6: Scroll ────────────────────────────────────────────────────────

async def _test_scroll() -> None:
    print("\n  ── scroll() ───────────────────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)
    s._page = MagicMock()
    captured: list[str] = []

    async def mock_scroll(page, step):
        captured.append(step)

    s._engine._handle_scroll = mock_scroll

    await s.scroll()
    _assert(captured[-1] == "SCROLL DOWN", "scroll() default step",
            f"got: {captured[-1]}")

    await s.scroll("the dropdown list")
    _assert(captured[-1] == "SCROLL DOWN inside the dropdown list",
            "scroll(target) generates correct step",
            f"got: {captured[-1]}")


# ── Section 7: Extract ───────────────────────────────────────────────────────

async def _test_extract() -> None:
    print("\n  ── extract() ──────────────────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)
    s._page = MagicMock()

    async def mock_extract(page, step):
        import re
        m = re.search(r'\{(\w+)\}', step)
        if m:
            s._engine.memory[m.group(1)] = "$19.99"
        return True

    s._engine._handle_extract = mock_extract

    val = await s.extract("Product Price", variable="price")
    _assert(val == "$19.99", "extract() returns extracted value",
            f"got: {val!r}")
    _assert(s.memory.get("price") == "$19.99",
            "extract() stores value in memory")

    val2 = await s.extract("Description")
    _assert(val2 is not None, "extract() without variable uses internal name")


# ── Section 8: Memory access ─────────────────────────────────────────────────

def _test_memory() -> None:
    print("\n  ── memory access ──────────────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)
    s.memory["token"] = "abc123"
    _assert(s.memory["token"] == "abc123", "memory write/read works")
    _assert(s._engine.memory["token"] == "abc123",
            "memory is shared with engine")


# ── Section 9: Lifecycle (mocked Playwright) ─────────────────────────────────

async def _test_lifecycle() -> None:
    print("\n  ── lifecycle (start/close) ─────────────────────────────────")

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium

    with patch("manul_engine.api.async_playwright") as mock_ap:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_ap.return_value = mock_cm

        s = ManulSession(headless=True, disable_cache=True)
        await s.start()

        _assert(s._page is mock_page, "start() assigns page")
        _assert(s._browser is mock_browser, "start() assigns browser")

        await s.close()
        mock_browser.close.assert_called_once()
        _assert(s._page is None, "close() clears page")
        _assert(s._browser is None, "close() clears browser")


# ── Section 10: Context manager ──────────────────────────────────────────────

async def _test_context_manager() -> None:
    print("\n  ── async context manager ──────────────────────────────────")

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium

    with patch("manul_engine.api.async_playwright") as mock_ap:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_ap.return_value = mock_cm

        async with ManulSession(headless=True, disable_cache=True) as session:
            _assert(session._page is mock_page,
                    "__aenter__ assigns page")

        mock_browser.close.assert_called_once()
        _assert(session._page is None,
                "__aexit__ cleans up page")


# ── Section 11: run_steps() DSL dispatch ─────────────────────────────────────

async def _test_run_steps() -> None:
    print("\n  ── run_steps() ────────────────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.evaluate = AsyncMock(return_value="Welcome to Example")
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    s._page = mock_page

    captured_steps: list[str] = []

    async def mock_navigate(page, step):
        captured_steps.append(("navigate", step))
        return True

    async def mock_execute(page, step, strategic_context="", step_idx=0):
        captured_steps.append(("action", step))
        return True

    s._engine._handle_navigate = mock_navigate
    s._engine._execute_step = mock_execute
    s._engine._handle_verify = AsyncMock(return_value=True)

    dsl = """\
STEP 1: Open the site
    NAVIGATE to https://example.com
    WAIT 0

STEP 2: Log in
    Fill 'Username' with 'admin'
    Click the 'Login' button
    DONE.
"""
    result = await s.run_steps(dsl)
    _assert(result.status == "pass", "run_steps() returns pass on success",
            f"got: {result.status}")
    _assert(len(result.blocks) == 2, "run_steps() returns two block results",
            f"got: {len(result.blocks)}")
    _assert(result.blocks[0].name == "STEP 1: Open the site",
            "run_steps() preserves first block name",
            f"got: {result.blocks[0].name!r}")
    _assert(result.steps[0].logical_step == "STEP 1: Open the site",
            "run_steps() tags actions with parent block name",
            f"got: {result.steps[0].logical_step!r}")

    nav_steps = [st for kind, st in captured_steps if kind == "navigate"]
    _assert(len(nav_steps) >= 1, "run_steps() dispatched NAVIGATE",
            f"got: {len(nav_steps)}")

    action_steps = [st for kind, st in captured_steps if kind == "action"]
    _assert(len(action_steps) >= 2, "run_steps() dispatched action steps",
            f"got: {len(action_steps)}")


# ── Section 12: run_steps SET variable ───────────────────────────────────────

async def _test_run_steps_set_var() -> None:
    print("\n  ── run_steps SET variable ─────────────────────────────────")

    s = ManulSession(headless=True, disable_cache=True)
    s._page = MagicMock()

    dsl = "SET {username} = 'testuser'"
    result = await s.run_steps(dsl)
    _assert(s.memory.get("username") == "testuser",
            "run_steps SET stores variable",
            f"got: {s.memory.get('username')!r}")


# ── Entry point ──────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n📋  test_45_api — ManulSession Public Python API\n")

    _test_constructor()
    _test_page_guard()
    await _test_step_generation()
    await _test_navigate()
    await _test_wait()
    await _test_scroll()
    await _test_extract()
    _test_memory()
    await _test_lifecycle()
    await _test_context_manager()
    await _test_run_steps()
    await _test_run_steps_set_var()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    print(f"  {'✅' if _FAIL == 0 else '❌'}  {_PASS} passed, {_FAIL} failed\n")
    return _FAIL == 0
