# manul_engine/test/test_39_open_app.py
"""
Unit-test suite for the OPEN APP command (v0.0.9.2):
  A. classify_step() returns "open_app" for all syntactic variants.
  B. RE_SYSTEM_STEP detects OPEN APP in unnumbered format.
  C. OPEN APP inside quoted text is NOT classified as open_app.
  D. _handle_open_app() attaches to the first context page.
  E. _handle_open_app() waits for a page event when no pages exist.
  F. Integration: OPEN APP in a multi-step hunt file is parsed correctly.

No network, no live browser, no Ollama required.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.helpers import classify_step, RE_SYSTEM_STEP
from manul_engine.cli import parse_hunt_file

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


# ═══════════════════════════════════════════════════════════════════════════════
# Section A: classify_step() — OPEN APP detection
# ═══════════════════════════════════════════════════════════════════════════════

def _test_classify_open_app() -> None:
    print("\n  ── classify_step(): OPEN APP detection ───────────────────────")

    # Basic forms
    _assert(classify_step("OPEN APP") == "open_app",
            "OPEN APP — bare")
    _assert(classify_step("Open App") == "open_app",
            "Open App — mixed case")
    _assert(classify_step("open app") == "open_app",
            "open app — lowercase")
    _assert(classify_step("OPEN  APP") == "open_app",
            "OPEN  APP — extra space")

    # With leading step number (legacy format)
    _assert(classify_step("1. OPEN APP") == "open_app",
            "1. OPEN APP — numbered prefix")

    # With leading whitespace (indented under STEP)
    _assert(classify_step("    OPEN APP") == "open_app",
            "    OPEN APP — indented")

    # Should NOT match inside quotes
    _assert(classify_step("Click 'Open App Settings'") != "open_app",
            "Click 'Open App Settings' — quoted, NOT open_app")
    _assert(classify_step("VERIFY that 'Open App' is present") != "open_app",
            "VERIFY that 'Open App' is present — quoted, NOT open_app")


# ═══════════════════════════════════════════════════════════════════════════════
# Section B: RE_SYSTEM_STEP detects OPEN APP
# ═══════════════════════════════════════════════════════════════════════════════

def _test_re_system_step() -> None:
    print("\n  ── RE_SYSTEM_STEP: OPEN APP detection ────────────────────────")

    _assert(bool(RE_SYSTEM_STEP.search("OPEN APP")),
            "RE_SYSTEM_STEP matches OPEN APP")
    _assert(bool(RE_SYSTEM_STEP.search("open app")),
            "RE_SYSTEM_STEP matches lowercase open app (case-insensitive)")
    _assert(bool(RE_SYSTEM_STEP.search("1. OPEN APP")),
            "RE_SYSTEM_STEP matches 1. OPEN APP")


# ═══════════════════════════════════════════════════════════════════════════════
# Section C: Other step kinds still work correctly
# ═══════════════════════════════════════════════════════════════════════════════

def _test_no_interference() -> None:
    print("\n  ── No interference with other step kinds ─────────────────────")

    _assert(classify_step("NAVIGATE to https://example.com") == "navigate",
            "NAVIGATE still works")
    _assert(classify_step("Click the 'Submit' button") == "action",
            "Click still classified as action")
    _assert(classify_step("VERIFY that 'Hello' is present") == "verify",
            "VERIFY still works")
    _assert(classify_step("SET {foo} = bar") == "set_var",
            "SET still works")
    _assert(classify_step("DONE.") == "done",
            "DONE still works")


# ═══════════════════════════════════════════════════════════════════════════════
# Section D: _handle_open_app() with existing pages
# ═══════════════════════════════════════════════════════════════════════════════

async def _test_handle_open_app_existing_page() -> None:
    print("\n  ── _handle_open_app(): existing page in context ──────────────")

    from manul_engine.actions import _ActionsMixin

    class FakeEngine(_ActionsMixin):
        def __init__(self):
            self.last_xpath = "some/xpath"
            self.nav_timeout = 30000
            self.timeout = 5000

    engine = FakeEngine()

    # Mock a page that is already open
    mock_page = AsyncMock()
    mock_page.url = "app://main-window"
    mock_page.wait_for_load_state = AsyncMock()

    # Mock context with one page already available
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]

    success, returned_page = await engine._handle_open_app(MagicMock(), mock_ctx)

    _assert(success is True,
            "Returns success=True when page exists")
    _assert(returned_page is mock_page,
            "Returns the non-blank context page")
    _assert(engine.last_xpath is None,
            "Resets last_xpath to None")
    mock_page.wait_for_load_state.assert_awaited_once_with(
        "domcontentloaded", timeout=30000
    )
    _assert(mock_page.wait_for_load_state.await_count == 1,
            "Calls wait_for_load_state('domcontentloaded')")


# ═══════════════════════════════════════════════════════════════════════════════
# Section E: _handle_open_app() waits for page event when no pages
# ═══════════════════════════════════════════════════════════════════════════════

async def _test_handle_open_app_wait_for_page() -> None:
    print("\n  ── _handle_open_app(): wait_for_event('page') ────────────────")

    from manul_engine.actions import _ActionsMixin

    class FakeEngine(_ActionsMixin):
        def __init__(self):
            self.last_xpath = "stale"
            self.nav_timeout = 30000
            self.timeout = 5000

    engine = FakeEngine()

    mock_page = AsyncMock()
    mock_page.url = "file:///app/index.html"
    mock_page.wait_for_load_state = AsyncMock()

    # Context with NO pages yet — engine must wait for the "page" event
    mock_ctx = MagicMock()
    mock_ctx.pages = []  # empty
    mock_ctx.wait_for_event = AsyncMock(return_value=mock_page)

    success, returned_page = await engine._handle_open_app(MagicMock(), mock_ctx)

    _assert(success is True,
            "Returns success=True after waiting for page event")
    _assert(returned_page is mock_page,
            "Returns the page from wait_for_event")
    mock_ctx.wait_for_event.assert_awaited_once()
    _assert("page" in str(mock_ctx.wait_for_event.call_args),
            "Waited for 'page' event")


# ═══════════════════════════════════════════════════════════════════════════════
# Section F: _handle_open_app() failure path
# ═══════════════════════════════════════════════════════════════════════════════

async def _test_handle_open_app_failure() -> None:
    print("\n  ── _handle_open_app(): failure scenario ──────────────────────")

    from manul_engine.actions import _ActionsMixin

    class FakeEngine(_ActionsMixin):
        def __init__(self):
            self.last_xpath = None
            self.nav_timeout = 30000
            self.timeout = 5000

    engine = FakeEngine()

    mock_ctx = MagicMock()
    mock_ctx.pages = []
    mock_ctx.wait_for_event = AsyncMock(side_effect=TimeoutError("No window opened"))

    mock_original_page = MagicMock()
    success, returned_page = await engine._handle_open_app(mock_original_page, mock_ctx)

    _assert(success is False,
            "Returns success=False on timeout")
    _assert(returned_page is mock_original_page,
            "Returns the original page on failure")


# ═══════════════════════════════════════════════════════════════════════════════
# Section F2: _handle_open_app() skips about:blank pages
# ═══════════════════════════════════════════════════════════════════════════════

async def _test_handle_open_app_skips_blank() -> None:
    print("\n  ── _handle_open_app(): skips about:blank page ────────────────")

    from manul_engine.actions import _ActionsMixin

    class FakeEngine(_ActionsMixin):
        def __init__(self):
            self.last_xpath = None
            self.nav_timeout = 30000
            self.timeout = 5000

    engine = FakeEngine()

    blank_page = AsyncMock()
    blank_page.url = "about:blank"

    real_page = AsyncMock()
    real_page.url = "app://electron-window"
    real_page.wait_for_load_state = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.pages = [blank_page, real_page]

    success, returned_page = await engine._handle_open_app(MagicMock(), mock_ctx)

    _assert(success is True,
            "Returns success when non-blank page found")
    _assert(returned_page is real_page,
            "Returns the real app page, not about:blank")
    real_page.wait_for_load_state.assert_awaited_once()
    _assert(blank_page.wait_for_load_state.await_count == 0,
            "Does not wait on the blank page")


# ═══════════════════════════════════════════════════════════════════════════════
# Section F3: INSIDE container uses DOM descendant membership for id-xpaths
# ═══════════════════════════════════════════════════════════════════════════════

async def _test_inside_container_uses_dom_contains() -> None:
    print("\n  ── INSIDE container uses DOM.contains() for id-xpaths ─────────")

    from manul_engine.actions import _ActionsMixin

    class FakeLocator:
        @property
        def first(self):
            return self

        async def scroll_into_view_if_needed(self, timeout=2000):
            return None

    class FakeFrame:
        def __init__(self):
            self.membership_payload = None

        async def evaluate(self, script, arg):
            if isinstance(arg, str):
                return "/html/body/table[1]/tbody[1]/tr[1]"
            self.membership_payload = arg
            return ['//*[@id="delete-inside"]']

        def locator(self, selector):
            return FakeLocator()

    class FakeEngine(_ActionsMixin):
        def __init__(self, frame):
            self.last_xpath = None
            self._frame = frame
            self.captured_container_elements = None

        async def _resolve_element(self, page, step, mode, search_texts, target_field, strategic_context, **kwargs):
            if mode == "locate" and search_texts == ["john doe"]:
                return {
                    "id": 1,
                    "name": "John Doe",
                    "xpath": "//*[@id=\"row-label\"]",
                    "frame_index": 0,
                    "tag_name": "td",
                    "input_type": "",
                    "is_shadow": False,
                }
            if kwargs.get("contextual_hint") is not None:
                self.captured_container_elements = kwargs.get("container_elements")
                return {
                    "id": 2,
                    "name": "Delete",
                    "xpath": '//*[@id="delete-inside"]',
                    "frame_index": 0,
                    "tag_name": "button",
                    "input_type": "",
                    "is_shadow": False,
                }
            return None

        async def _snapshot(self, page, mode, search_texts):
            return [
                {
                    "id": 2,
                    "name": "Delete",
                    "xpath": '//*[@id="delete-inside"]',
                    "frame_index": 0,
                },
                {
                    "id": 3,
                    "name": "Delete",
                    "xpath": "/html/body/div[5]/button[1]",
                    "frame_index": 0,
                },
                {
                    "id": 4,
                    "name": "Delete",
                    "xpath": '//*[@id="delete-other-frame"]',
                    "frame_index": 1,
                },
            ]

        def _frame_for(self, page, el):
            return self._frame

        async def _highlight(self, page, locator_or_id, by_js_id=False, frame=None):
            return None

        def _fmt_el_name(self, name):
            return name

    frame = FakeFrame()
    engine = FakeEngine(frame)
    page = MagicMock()

    ok = await engine._execute_step(
        page,
        "Locate 'Delete' INSIDE 'Actions' row with 'John Doe'",
    )

    _assert(ok is True,
            "Locate step succeeds with DOM membership filtering")
    _assert(engine.captured_container_elements is not None,
            "Final resolve receives container_elements")
    _assert(len(engine.captured_container_elements) == 1,
            "Only contained descendant is kept")
    _assert(engine.captured_container_elements[0]["xpath"] == '//*[@id="delete-inside"]',
            "Id-based descendant xpath survives INSIDE scoping")
    _assert(frame.membership_payload is not None,
            "Frame membership eval payload captured")
    _assert(frame.membership_payload["candidateXPaths"] == [
        '//*[@id="delete-inside"]',
        "/html/body/div[5]/button[1]",
    ], "Membership check only evaluates same-frame candidate xpaths")


# ═══════════════════════════════════════════════════════════════════════════════
# Section G: parse_hunt_file integration — OPEN APP in a hunt file
# ═══════════════════════════════════════════════════════════════════════════════

def _test_parse_hunt_file_open_app() -> None:
    print("\n  ── parse_hunt_file: OPEN APP in hunt file ────────────────────")

    import tempfile, os

    hunt_content = """\
@context: Electron desktop app test
@title: desktop_smoke

STEP 1: Launch app
    OPEN APP
    VERIFY that 'Welcome' is present

STEP 2: Navigate inside app
    Click the 'Settings' button
    VERIFY that 'Preferences' is present
    DONE.
"""
    fd, path = tempfile.mkstemp(suffix=".hunt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(hunt_content)
        parsed = parse_hunt_file(path)
        mission = parsed.mission

        _assert("OPEN APP" in mission,
                "OPEN APP preserved in parsed mission text")
        _assert("NAVIGATE" not in mission,
                "No NAVIGATE in desktop app hunt")

        # Verify classify_step on each line
        lines = [l.strip() for l in mission.splitlines() if l.strip()]
        kinds = [classify_step(l) for l in lines]
        _assert("open_app" in kinds,
                "classify_step finds open_app in parsed mission")
        _assert("navigate" not in kinds,
                "No navigate kind in desktop app mission")
    finally:
        os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════════════
# Section H: OPEN APP ordering — must come before NAVIGATE in _STEP_PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

def _test_open_app_does_not_shadow_navigate() -> None:
    print("\n  ── OPEN APP does not shadow NAVIGATE ─────────────────────────")

    _assert(classify_step("NAVIGATE to https://example.com") == "navigate",
            "NAVIGATE to URL still classifies as navigate")
    _assert(classify_step("Navigate to https://example.com/page") == "navigate",
            "Navigate mixed case still classifies as navigate")
    _assert(classify_step("OPEN APP") == "open_app",
            "OPEN APP classifies as open_app (not navigate)")


# ═══════════════════════════════════════════════════════════════════════════════
# Suite runner
# ═══════════════════════════════════════════════════════════════════════════════

async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n═══ test_39_open_app ═══════════════════════════════════════════")

    # Sync tests
    _test_classify_open_app()
    _test_re_system_step()
    _test_no_interference()
    _test_parse_hunt_file_open_app()
    _test_open_app_does_not_shadow_navigate()

    # Async tests
    await _test_handle_open_app_existing_page()
    await _test_handle_open_app_wait_for_page()
    await _test_handle_open_app_failure()
    await _test_handle_open_app_skips_blank()
    await _test_inside_container_uses_dom_contains()

    print(f"\n  RESULTS: {_PASS} passed, {_FAIL} failed")
    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total} passed")
    return _PASS, _FAIL
