# manul_engine/test/test_19_custom_controls.py
"""
Unit-test suite for the Custom Controls registry and engine interception.

No browser is required.  All tests run against synthetic state only.

Tests:
  1. Registry correctness  — decorator stores the handler keyed by
     (page_lower, target_lower); lookup is case-insensitive.
  2. Engine interception   — when a step targets a registered control the
     custom handler is called with the correct (page, mode, value) arguments
     and standard DOM resolution (_execute_step) is bypassed entirely.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.controls import (
    _CUSTOM_CONTROLS,
    _LOADED_FILES,
    custom_control,
    extract_required_controls,
    get_custom_control,
    load_custom_controls,
)

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


# ── Section 1: Registry correctness ──────────────────────────────────────────

def _test_registry() -> None:
    print("\n  ── Registry (decorator + lookup) ────────────────────────────")

    # Isolate: save and restore the registry around this section.
    saved = dict(_CUSTOM_CONTROLS)
    _CUSTOM_CONTROLS.clear()

    try:
        # 1a. Registration adds the handler under the normalised key.
        call_log: list = []

        @custom_control(page="Login Page", target="Username")
        def _handle_username(page, action_type, value):
            call_log.append((action_type, value))

        expected_key = ("login page", "username")
        _assert(
            expected_key in _CUSTOM_CONTROLS,
            "decorator registers handler under (page_lower, target_lower)",
            f"keys={list(_CUSTOM_CONTROLS.keys())}",
        )
        _assert(
            _CUSTOM_CONTROLS[expected_key] is _handle_username,
            "registered value is the original function",
        )

        # 1b. Lookup is case-insensitive on both dimensions.
        _assert(
            get_custom_control("Login Page", "Username") is _handle_username,
            "lookup: exact case matches",
        )
        _assert(
            get_custom_control("login page", "username") is _handle_username,
            "lookup: all-lower case matches",
        )
        _assert(
            get_custom_control("LOGIN PAGE", "USERNAME") is _handle_username,
            "lookup: all-upper case matches",
        )

        # 1c. Non-matching lookups return None.
        _assert(
            get_custom_control("Dashboard", "Username") is None,
            "lookup: wrong page returns None",
        )
        _assert(
            get_custom_control("Login Page", "Password") is None,
            "lookup: wrong target returns None",
        )
        _assert(
            get_custom_control("", "") is None,
            "lookup: empty strings return None",
        )

        # 1d. Multiple handlers co-exist without collision.
        @custom_control(page="Login Page", target="Password")
        def _handle_password(page, action_type, value):
            pass

        @custom_control(page="Checkout Page", target="React Datepicker")
        def _handle_datepicker(page, action_type, value):
            pass

        _assert(
            get_custom_control("Login Page", "Password") is _handle_password,
            "multiple handlers: login/password resolves correctly",
        )
        _assert(
            get_custom_control("Checkout Page", "React Datepicker") is _handle_datepicker,
            "multiple handlers: checkout/datepicker resolves correctly",
        )
        _assert(
            get_custom_control("Login Page", "Username") is _handle_username,
            "multiple handlers: login/username still intact",
        )

        # 1e. Decorator is transparent — returns the original callable.
        _assert(
            callable(_handle_username),
            "decorated function remains callable",
        )

        # 1f. Async handlers are stored without modification.
        @custom_control(page="Search Page", target="Date Range")
        async def _async_handler(page, action_type, value):
            pass

        _assert(
            asyncio.iscoroutinefunction(
                get_custom_control("Search Page", "Date Range")
            ),
            "async handler stored and detectable via iscoroutinefunction",
        )

    finally:
        _CUSTOM_CONTROLS.clear()
        _CUSTOM_CONTROLS.update(saved)


# ── Section 2: Engine interception ───────────────────────────────────────────

async def _test_interception() -> None:
    print("\n  ── Engine interception (core.py else-branch) ────────────────")

    # Inject a fresh handler into the registry.
    saved = dict(_CUSTOM_CONTROLS)
    _CUSTOM_CONTROLS.clear()

    handler_calls: list[tuple] = []

    async def _datepicker_handler(page, action_type: str, value):
        handler_calls.append((action_type, value))

    _CUSTOM_CONTROLS[("checkout page", "react datepicker")] = _datepicker_handler

    try:
        # Build the minimal ManulEngine instance without touching Playwright.
        # We patch load_custom_controls so the constructor does not scan the
        # filesystem (which would overwrite our synthetic registry entry).
        with patch("manul_engine.core.load_custom_controls"):
            from manul_engine.core import ManulEngine
            engine = ManulEngine(model=None, disable_cache=True)

        # Patch out the parts of run_mission we do not want to exercise:
        # - async_playwright launch / close
        # - _execute_step (must NOT be called when a custom control matches)
        # - lookup_page_name (returns our synthetic page name)
        execute_step_mock = AsyncMock(return_value=True)

        # Minimal fake Playwright page.
        fake_page = MagicMock()
        fake_page.url = "https://example-shop.com/checkout"
        fake_page.evaluate = AsyncMock(return_value=None)
        fake_page.goto = AsyncMock()
        fake_page.wait_for_load_state = AsyncMock()

        # Fake browser / context.
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

        step_text = "2. Fill 'React Datepicker' with '2026-12-25'"

        with (
            patch("manul_engine.core.async_playwright", return_value=mock_playwright),
            patch("manul_engine.core.prompts.lookup_page_name", return_value="Checkout Page"),
            patch.object(engine, "_execute_step", execute_step_mock),
        ):
            await engine.run_mission(step_text)

        # 2a. Custom handler was called exactly once.
        _assert(
            len(handler_calls) == 1,
            "custom handler called exactly once",
            f"calls={handler_calls}",
        )

        # 2b. action_type is "input" (mode detected from "Fill").
        _assert(
            handler_calls[0][0] == "input",
            "handler received action_type='input'",
            f"got={handler_calls[0][0]!r}",
        )

        # 2c. value is the last quoted token.
        _assert(
            handler_calls[0][1] == "2026-12-25",
            "handler received value='2026-12-25'",
            f"got={handler_calls[0][1]!r}",
        )

        # 2d. Standard DOM resolution was NOT called.
        _assert(
            execute_step_mock.call_count == 0,
            "_execute_step bypassed when custom control matches",
            f"call_count={execute_step_mock.call_count}",
        )

        # 2e. A step for a non-registered (page, target) falls through to DOM.
        handler_calls.clear()
        execute_step_mock.reset_mock()

        step_text_normal = "2. Click the 'Submit' button"

        with (
            patch("manul_engine.core.async_playwright", return_value=mock_playwright),
            patch("manul_engine.core.prompts.lookup_page_name", return_value="Checkout Page"),
            patch.object(engine, "_execute_step", execute_step_mock),
        ):
            await engine.run_mission(step_text_normal)

        _assert(
            len(handler_calls) == 0,
            "non-registered target does not trigger custom handler",
        )
        _assert(
            execute_step_mock.call_count == 1,
            "_execute_step called for non-registered target",
            f"call_count={execute_step_mock.call_count}",
        )

    finally:
        _CUSTOM_CONTROLS.clear()
        _CUSTOM_CONTROLS.update(saved)


# ── Section 3: Pre-flight extraction & lazy loading ──────────────────────────

def _test_extraction_and_lazy_loading() -> None:
    import tempfile
    import shutil

    print("\n  ── Pre-flight extraction & lazy loading ─────────────────────")

    # Create a temporary workspace with a controls/ directory.
    tmpdir = tempfile.mkdtemp(prefix="manul_ctrl_test_")
    controls_dir = os.path.join(tmpdir, "controls")
    os.makedirs(controls_dir)

    try:
        # Write two control files — one matching and one not.
        with open(os.path.join(controls_dir, "booking.py"), "w") as f:
            f.write(
                "from manul_engine.controls import custom_control\n"
                "@custom_control(page='Booking Page', target='React Datepicker')\n"
                "async def handle(page, action_type, value): pass\n"
            )
        with open(os.path.join(controls_dir, "admin.py"), "w") as f:
            f.write(
                "from manul_engine.controls import custom_control\n"
                "@custom_control(page='Admin Page', target='User Table')\n"
                "async def handle(page, action_type, value): pass\n"
            )
        # Also a file that should be skipped (underscore prefix).
        with open(os.path.join(controls_dir, "_internal.py"), "w") as f:
            f.write("# internal helper — should never be imported\n")

        # 3a. extract_required_controls finds only the matching file.
        mission = "Fill 'React Datepicker' with '2026-12-25'"
        needed = extract_required_controls(mission, tmpdir)
        _assert(
            needed == {"booking.py"},
            "extract finds only the file with matching target",
            f"got={needed}",
        )

        # 3b. extract with no matching targets returns empty set.
        mission_no_match = "Click the 'Submit' button"
        needed_empty = extract_required_controls(mission_no_match, tmpdir)
        _assert(
            needed_empty == set(),
            "extract returns empty set when no control matches",
            f"got={needed_empty}",
        )

        # 3c. extract with multiple targets finds all matching files.
        mission_both = "Fill 'React Datepicker' with 'today'\nClick 'User Table'"
        needed_both = extract_required_controls(mission_both, tmpdir)
        _assert(
            needed_both == {"booking.py", "admin.py"},
            "extract finds multiple matching files",
            f"got={needed_both}",
        )

        # 3d. extract with no controls/ directory returns empty set.
        empty_dir = tempfile.mkdtemp(prefix="manul_no_ctrl_")
        try:
            needed_no_dir = extract_required_controls(mission, empty_dir)
            _assert(
                needed_no_dir == set(),
                "extract returns empty set when controls/ dir absent",
                f"got={needed_no_dir}",
            )
        finally:
            shutil.rmtree(empty_dir)

        # 3e. Lazy load only the targeted file — registry gets only that handler.
        saved = dict(_CUSTOM_CONTROLS)
        saved_files = set(_LOADED_FILES)
        _CUSTOM_CONTROLS.clear()
        _LOADED_FILES.clear()
        try:
            load_custom_controls(tmpdir, required_modules={"booking.py"})
            _assert(
                get_custom_control("Booking Page", "React Datepicker") is not None,
                "lazy-loaded booking.py registered its handler",
            )
            _assert(
                get_custom_control("Admin Page", "User Table") is None,
                "admin.py was NOT loaded (lazy mode skipped it)",
            )

            # 3f. Per-file idempotency: calling again does not re-import.
            # Replace the handler — if re-imported, it would be overwritten.
            sentinel = lambda p, a, v: None  # noqa: E731
            _CUSTOM_CONTROLS[("booking page", "react datepicker")] = sentinel
            load_custom_controls(tmpdir, required_modules={"booking.py"})
            _assert(
                get_custom_control("Booking Page", "React Datepicker") is sentinel,
                "per-file idempotency: second lazy call did not re-import",
            )
        finally:
            _CUSTOM_CONTROLS.clear()
            _CUSTOM_CONTROLS.update(saved)
            _LOADED_FILES.clear()
            _LOADED_FILES.update(saved_files)

    finally:
        shutil.rmtree(tmpdir)


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n" + "=" * 70)
    print("CUSTOM CONTROLS: Registry & Interception")
    print("=" * 70)

    _test_registry()
    await _test_interception()
    _test_extraction_and_lazy_loading()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total} passed")
    if _PASS == total:
        print(f"👑 {total}/{total} PERFECT! CUSTOM CONTROLS ARE ROCK SOLID! 👑")
    return _PASS == total


if __name__ == "__main__":
    asyncio.run(run_suite())
