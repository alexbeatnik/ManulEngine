# manul_engine/test/test_19_custom_controls.py
"""
Unit-test suite for the Custom Controls registry and engine interception.

No browser is required.  All tests run against synthetic state only.

Tests:
  1. Registry correctness  — decorator stores the handler keyed by
     (page_lower, target_lower); lookup is case-insensitive.
  2. Engine interception   — when a step targets a registered control the
     custom handler is called with a ControlContext and standard DOM
     resolution (_execute_step) is bypassed entirely.
  3. Pre-flight extraction & lazy loading — extract_required_controls only
     loads files whose declared targets appear in the mission text.
  4. Signature enforcement & miss-diagnostics & list_custom_controls — the
     0.0.9.30 surface: legacy 3-arg handlers are rejected, sibling-page
     misses produce a hint, and list_custom_controls() returns the registry.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python run_tests.py``) and must remain async.
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
    _REGISTRY_META,
    ControlContext,
    custom_control,
    diagnose_custom_control_miss,
    extract_required_controls,
    get_custom_control,
    list_custom_controls,
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


def _isolate_registry():
    """Return a (saved_controls, saved_meta, saved_files) tuple for restoration."""
    saved = (dict(_CUSTOM_CONTROLS), dict(_REGISTRY_META), set(_LOADED_FILES))
    _CUSTOM_CONTROLS.clear()
    _REGISTRY_META.clear()
    _LOADED_FILES.clear()
    return saved


def _restore_registry(saved) -> None:
    s_controls, s_meta, s_files = saved
    _CUSTOM_CONTROLS.clear()
    _CUSTOM_CONTROLS.update(s_controls)
    _REGISTRY_META.clear()
    _REGISTRY_META.update(s_meta)
    _LOADED_FILES.clear()
    _LOADED_FILES.update(s_files)


# ── Section 1: Registry correctness ──────────────────────────────────────────


def _test_registry() -> None:
    print("\n  ── Registry (decorator + lookup) ────────────────────────────")

    saved = _isolate_registry()
    try:
        # 1a. Registration adds the handler under the normalised key.
        @custom_control(page="Login Page", target="Username")
        def _handle_username(ctx: ControlContext) -> None:
            pass

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
        def _handle_password(ctx: ControlContext) -> None:
            pass

        @custom_control(page="Checkout Page", target="React Datepicker")
        def _handle_datepicker(ctx: ControlContext) -> None:
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
        async def _async_handler(ctx: ControlContext) -> None:
            pass

        _assert(
            asyncio.iscoroutinefunction(get_custom_control("Search Page", "Date Range")),
            "async handler stored and detectable via iscoroutinefunction",
        )
    finally:
        _restore_registry(saved)


# ── Section 2: Engine interception ───────────────────────────────────────────


async def _test_interception() -> None:
    print("\n  ── Engine interception (core.py else-branch) ────────────────")

    saved = _isolate_registry()
    handler_calls: list[ControlContext] = []

    async def _datepicker_handler(ctx: ControlContext) -> None:
        handler_calls.append(ctx)

    _CUSTOM_CONTROLS[("checkout page", "react datepicker")] = _datepicker_handler
    _REGISTRY_META[("checkout page", "react datepicker")] = {
        "page": "Checkout Page",
        "target": "React Datepicker",
        "handler": "_datepicker_handler",
        "source": "<test>",
    }

    try:
        from manul_engine.core import ManulEngine

        engine = ManulEngine(model=None, disable_cache=True)
        execute_step_mock = AsyncMock(return_value=True)

        fake_page = MagicMock()
        fake_page.url = "https://example-shop.com/checkout"
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

        step_text = "2. Fill 'React Datepicker' with '2026-12-25'"

        with (
            patch.object(type(engine), "_launch_browser", AsyncMock(return_value=(fake_browser, fake_ctx, fake_page))),
            patch("manul_engine.core.prompts.lookup_page_name", return_value="Checkout Page"),
            patch.object(engine, "_execute_step", execute_step_mock),
            patch("manul_engine.core.load_custom_controls"),
        ):
            await engine.run_mission(step_text)

        # 2a. Custom handler was called exactly once.
        _assert(
            len(handler_calls) == 1,
            "custom handler called exactly once",
            f"calls={len(handler_calls)}",
        )

        # 2b. Single arg is a ControlContext (not the legacy 3-tuple).
        ctx = handler_calls[0] if handler_calls else None
        _assert(
            isinstance(ctx, ControlContext),
            "handler received ControlContext instance",
            f"got={type(ctx).__name__ if ctx else None}",
        )

        if isinstance(ctx, ControlContext):
            # 2c. ctx.action is "input" (mode detected from "Fill").
            _assert(ctx.action == "input", "ctx.action == 'input'", f"got={ctx.action!r}")
            # 2d. ctx.value is the last quoted token.
            _assert(ctx.value == "2026-12-25", "ctx.value == '2026-12-25'", f"got={ctx.value!r}")
            # 2e. ctx.target / ctx.page_name / ctx.page populated.
            _assert(ctx.target == "React Datepicker", "ctx.target propagated", f"got={ctx.target!r}")
            _assert(ctx.page_name == "Checkout Page", "ctx.page_name resolved", f"got={ctx.page_name!r}")
            _assert(ctx.page is fake_page, "ctx.page is the live Playwright Page")

        # 2f. Standard DOM resolution was NOT called.
        _assert(
            execute_step_mock.call_count == 0,
            "_execute_step bypassed when custom control matches",
            f"call_count={execute_step_mock.call_count}",
        )

        # 2g. A step for a non-registered (page, target) falls through to DOM.
        handler_calls.clear()
        execute_step_mock.reset_mock()

        step_text_normal = "2. Click the 'Submit' button"

        with (
            patch.object(type(engine), "_launch_browser", AsyncMock(return_value=(fake_browser, fake_ctx, fake_page))),
            patch("manul_engine.core.prompts.lookup_page_name", return_value="Checkout Page"),
            patch.object(engine, "_execute_step", execute_step_mock),
            patch("manul_engine.core.load_custom_controls"),
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
        _restore_registry(saved)


# ── Section 3: Pre-flight extraction & lazy loading ──────────────────────────


def _test_extraction_and_lazy_loading() -> None:
    import shutil
    import tempfile

    print("\n  ── Pre-flight extraction & lazy loading ─────────────────────")

    tmpdir = tempfile.mkdtemp(prefix="manul_ctrl_test_")
    controls_dir = os.path.join(tmpdir, "controls")
    os.makedirs(controls_dir)

    try:
        # New 1-arg signature is mandatory.
        with open(os.path.join(controls_dir, "booking.py"), "w", encoding="utf-8") as f:
            f.write(
                "from manul_engine.controls import custom_control\n"
                "@custom_control(page='Booking Page', target='React Datepicker')\n"
                "async def handle(ctx): pass\n"
            )
        with open(os.path.join(controls_dir, "admin.py"), "w", encoding="utf-8") as f:
            f.write(
                "from manul_engine.controls import custom_control\n"
                "@custom_control(page='Admin Page', target='User Table')\n"
                "async def handle(ctx): pass\n"
            )
        with open(os.path.join(controls_dir, "positional.py"), "w", encoding="utf-8") as f:
            f.write(
                "from manul_engine import custom_control\n"
                "@custom_control('Some Page', 'Some Target')\n"
                "async def handle(ctx): pass\n"
            )
        with open(os.path.join(controls_dir, "_internal.py"), "w", encoding="utf-8") as f:
            f.write("# internal helper — should never be imported\n")

        # 3a. extract_required_controls finds only the matching file.
        mission = "Fill 'React Datepicker' with '2026-12-25'"
        needed = extract_required_controls(mission, tmpdir)
        _assert(
            needed == {"controls/booking.py"},
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
            needed_both == {"controls/booking.py", "controls/admin.py"},
            "extract finds multiple matching files",
            f"got={needed_both}",
        )

        # 3d. Positional decorator args are also discovered.
        mission_positional = "Click 'Some Target'"
        needed_positional = extract_required_controls(mission_positional, tmpdir)
        _assert(
            needed_positional == {"controls/positional.py"},
            "extract finds file using positional @custom_control args",
            f"got={needed_positional}",
        )

        # 3e. extract with no controls/ directory returns empty set.
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

        # 3f. Lazy load only the targeted file — registry gets only that handler.
        saved = _isolate_registry()
        try:
            load_custom_controls(tmpdir, required_modules={"controls/booking.py"})
            _assert(
                get_custom_control("Booking Page", "React Datepicker") is not None,
                "lazy-loaded booking.py registered its handler",
            )
            _assert(
                get_custom_control("Admin Page", "User Table") is None,
                "admin.py was NOT loaded (lazy mode skipped it)",
            )

            # 3g. Per-file idempotency: calling again does not re-import.
            sentinel = lambda ctx: None  # noqa: E731
            _CUSTOM_CONTROLS[("booking page", "react datepicker")] = sentinel
            load_custom_controls(tmpdir, required_modules={"controls/booking.py"})
            _assert(
                get_custom_control("Booking Page", "React Datepicker") is sentinel,
                "per-file idempotency: second lazy call did not re-import",
            )
        finally:
            _restore_registry(saved)

        # 3h. Positional-arg decorator usage is still lazy-loaded correctly.
        saved = _isolate_registry()
        try:
            load_custom_controls(tmpdir, required_modules=needed_positional)
            _assert(
                get_custom_control("Some Page", "Some Target") is not None,
                "lazy-loaded positional.py registered its handler",
            )
        finally:
            _restore_registry(saved)
    finally:
        shutil.rmtree(tmpdir)


# ── Section 4: 0.0.9.30 surface — signature, diagnostics, listing ────────────


def _test_new_surface() -> None:
    print("\n  ── 0.0.9.30 surface (sig / miss-hint / listing) ─────────────")

    saved = _isolate_registry()
    try:
        # 4a. Legacy 3-arg signature is rejected with a helpful TypeError.
        rejected = False
        try:

            @custom_control(page="Old Page", target="Old Target")
            def _legacy(page, action_type, value):
                pass
        except TypeError as exc:
            rejected = "ControlContext" in str(exc) and "0.0.9.30" in str(exc)

        _assert(
            rejected,
            "legacy (page, action_type, value) signature rejected with migration hint",
            "expected TypeError mentioning ControlContext + 0.0.9.30",
        )
        _assert(
            ("old page", "old target") not in _CUSTOM_CONTROLS,
            "rejected handler is NOT added to the registry",
        )

        # 4b. diagnose_custom_control_miss surfaces sibling-page mismatches.
        @custom_control(page="Booking Page", target="Date Picker")
        async def _h(ctx: ControlContext) -> None:
            pass

        hint = diagnose_custom_control_miss("Checkout Page", "Date Picker")
        _assert(
            hint is not None and "Booking Page" in hint and "Checkout Page" in hint,
            "miss-hint mentions both registered page and current page",
            f"hint={hint!r}",
        )
        _assert(
            diagnose_custom_control_miss("Checkout Page", "Some Random Field") is None,
            "miss-hint returns None when no sibling registration exists",
        )
        _assert(
            diagnose_custom_control_miss("Booking Page", "Date Picker") is None,
            "miss-hint returns None when target IS registered for the current page",
        )

        # 4c. list_custom_controls returns sorted rows with full metadata.
        @custom_control(page="Admin Page", target="User Table")
        async def _h2(ctx: ControlContext) -> None:
            pass

        rows = list_custom_controls()
        _assert(
            len(rows) == 2,
            "list_custom_controls returns one row per registration",
            f"len={len(rows)}",
        )
        pages = [r["page"] for r in rows]
        _assert(
            pages == sorted(pages, key=str.lower),
            "list_custom_controls is sorted by page (case-insensitive)",
            f"pages={pages}",
        )
        for r in rows:
            _assert(
                set(r.keys()) >= {"page", "target", "handler", "source"},
                f"row has full metadata for {r.get('page')!r}",
            )
    finally:
        _restore_registry(saved)


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
    _test_new_surface()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total} passed")
    if _PASS == total:
        print(f"👑 {total}/{total} PERFECT! CUSTOM CONTROLS ARE ROCK SOLID! 👑")
    return _PASS == total


if __name__ == "__main__":
    asyncio.run(run_suite())
