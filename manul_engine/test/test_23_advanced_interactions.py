# manul_engine/test/test_23_advanced_interactions.py
"""
Unit-test suite for advanced interaction DSL commands:
  • PRESS [Key]  /  PRESS [Key] on 'Target'
  • RIGHT CLICK 'Target'
  • UPLOAD 'file' to 'Target'

No live browser required — tests exercise:
  1. classify_step() for correct step kind detection
  2. detect_mode() returning expected modes for new step verbs
  3. Handler methods via mocked Playwright page objects

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine import prompts
from manul_engine.helpers import classify_step, detect_mode

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


# ── 1. classify_step tests ───────────────────────────────────────────────────

def _test_classify_step() -> None:
    print("\n  ── classify_step — new step kinds ──────────────────────")

    # PRESS ENTER must still map to press_enter (not the generic press)
    _assert(classify_step("1. PRESS ENTER") == "press_enter",
            "PRESS ENTER → press_enter")
    _assert(classify_step("PRESS ENTER") == "press_enter",
            "PRESS ENTER (no number) → press_enter")

    # Generic PRESS variants
    _assert(classify_step("1. PRESS Escape") == "press",
            "PRESS Escape → press")
    _assert(classify_step("2. PRESS Control+A") == "press",
            "PRESS Control+A → press")
    _assert(classify_step("3. PRESS ArrowDown on 'Search Input'") == "press",
            "PRESS ArrowDown on 'Target' → press")
    _assert(classify_step("PRESS Tab") == "press",
            "PRESS Tab (no number) → press")
    _assert(classify_step("4. PRESS Shift+Tab on 'Username'") == "press",
            "PRESS Shift+Tab on 'Target' → press")

    # RIGHT CLICK
    _assert(classify_step("1. RIGHT CLICK 'Image'") == "right_click",
            "RIGHT CLICK 'Image' → right_click")
    _assert(classify_step("RIGHT CLICK the 'Context Menu Area'") == "right_click",
            "RIGHT CLICK the 'Target' → right_click")
    _assert(classify_step("5. Right Click 'Menu'") == "right_click",
            "Right Click (mixed case) → right_click")

    # UPLOAD
    _assert(classify_step("1. UPLOAD 'avatar.png' to 'Profile Picture'") == "upload",
            "UPLOAD 'file' to 'Target' → upload")
    _assert(classify_step("UPLOAD 'file.pdf' to 'Dropzone'") == "upload",
            "UPLOAD (no number) → upload")
    _assert(classify_step("3. Upload 'data.csv' to 'Import'") == "upload",
            "Upload (mixed case) → upload")

    # Explicit waits
    _assert(classify_step('Wait for "Welcome, User" to be visible') == "wait_for_element",
            "Wait for text to be visible → wait_for_element")
    _assert(classify_step("Wait for 'Loading...' to disappear") == "wait_for_element",
            "Wait for text to disappear → wait_for_element")
    _assert(classify_step('1. Wait for "Submit" to be hidden') == "wait_for_element",
            "Numbered explicit wait → wait_for_element")

    # Ensure existing keywords still work correctly
    _assert(classify_step("1. NAVIGATE to https://x.com") == "navigate",
            "NAVIGATE still works")
    _assert(classify_step("Click 'Submit'") == "action",
            "Click still → action")
    _assert(classify_step("DONE.") == "done",
            "DONE. still works")

    # Keywords inside quoted labels must NOT misclassify
    _assert(classify_step("Click 'Press Here' button") == "action",
            "PRESS inside quotes → action (not press)")
    _assert(classify_step("Click the 'Upload Logo' button") == "action",
            "UPLOAD inside quotes → action (not upload)")
    _assert(classify_step("Click 'DONE' button") == "action",
            "DONE inside quotes → action (not done)")
    _assert(classify_step("Fill 'Navigate Away' field with 'test'") == "action",
            "NAVIGATE inside quotes → action (not navigate)")

# ── 2. RE_SYSTEM_STEP tests ─────────────────────────────────────────────────

def _test_re_system_step() -> None:
    from manul_engine.helpers import RE_SYSTEM_STEP
    print("\n  ── RE_SYSTEM_STEP — new keywords ──────────────────────")

    _assert(RE_SYSTEM_STEP.search("1. PRESS Escape") is not None,
            "RE_SYSTEM_STEP matches PRESS Escape")
    _assert(RE_SYSTEM_STEP.search("PRESS ENTER") is not None,
            "RE_SYSTEM_STEP matches PRESS ENTER")
    _assert(RE_SYSTEM_STEP.search("RIGHT CLICK 'Image'") is not None,
            "RE_SYSTEM_STEP matches RIGHT CLICK")
    _assert(RE_SYSTEM_STEP.search("UPLOAD 'file.pdf' to 'Target'") is not None,
            "RE_SYSTEM_STEP matches UPLOAD")
    _assert(RE_SYSTEM_STEP.search('Wait for "Loading..." to disappear') is not None,
            "RE_SYSTEM_STEP matches explicit wait")
    _assert(RE_SYSTEM_STEP.search("VERIFY that 'Welcome' is present") is not None,
            "RE_SYSTEM_STEP matches VERIFY")
    _assert(RE_SYSTEM_STEP.search("Click 'Submit'") is None,
            "RE_SYSTEM_STEP does NOT match Click (action)")


# ── 3. Handler tests (mocked Playwright) ────────────────────────────────────

def _make_engine():
    """Create a ManulEngine with model=None, disable_cache=True."""
    from manul_engine import ManulEngine
    return ManulEngine(model=None, headless=True, disable_cache=True)


def _mock_page():
        page = MagicMock()
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.evaluate = AsyncMock(return_value=[])
        page.url = "https://example.com"

        mock_loc = MagicMock()
        mock_loc.press = AsyncMock()
        mock_loc.click = AsyncMock()
        mock_loc.set_input_files = AsyncMock()
        mock_loc.scroll_into_view_if_needed = AsyncMock()
        mock_loc.wait_for = AsyncMock()
        mock_loc.first = mock_loc
        page.locator = MagicMock(return_value=mock_loc)
        page.get_by_text = MagicMock(return_value=mock_loc)
        page._mock_locator = mock_loc
        return page


def _mock_element(el_id=1, name="Test Element", xpath="//button[@id='test']"):
    """Return a dict matching the snapshot element shape."""
    return {
        "id": el_id,
        "name": name,
        "xpath": xpath,
        "is_select": False,
        "is_shadow": False,
        "is_contenteditable": False,
        "class_name": "",
        "tag_name": "button",
        "input_type": "",
        "data_qa": "",
        "html_id": "test",
        "icon_classes": "",
        "aria_label": "",
        "placeholder": "",
        "role": "",
        "disabled": False,
        "aria_disabled": "",
    }


async def _test_handle_press_global() -> None:
    print("\n  ── _handle_press — global ────────────────────────────")
    engine = _make_engine()
    page = _mock_page()

    ok = await engine._handle_press(page, "1. PRESS Escape")
    _assert(ok, "PRESS Escape returns True")
    page.keyboard.press.assert_awaited_once_with("Escape")
    _assert(True, "page.keyboard.press called with 'Escape'")


async def _test_handle_press_combo() -> None:
    print("\n  ── _handle_press — combo key ─────────────────────────")
    engine = _make_engine()
    page = _mock_page()

    ok = await engine._handle_press(page, "2. PRESS Control+A")
    _assert(ok, "PRESS Control+A returns True")
    page.keyboard.press.assert_awaited_once_with("Control+A")
    _assert(True, "page.keyboard.press called with 'Control+A'")


async def _test_handle_press_targeted() -> None:
    print("\n  ── _handle_press — targeted ──────────────────────────")
    engine = _make_engine()
    page = _mock_page()
    el = _mock_element(name="Search Input")

    with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=el)):
        ok = await engine._handle_press(page, "3. PRESS ArrowDown on 'Search Input'")
        _assert(ok, "PRESS ArrowDown on 'Target' returns True")
        page._mock_locator.press.assert_awaited_once_with("ArrowDown", timeout=prompts.TIMEOUT)
        _assert(True, "locator.press called with 'ArrowDown'")


async def _test_handle_press_targeted_not_found() -> None:
    print("\n  ── _handle_press — targeted not found ────────────────")
    engine = _make_engine()
    page = _mock_page()

    with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=None)):
        ok = await engine._handle_press(page, "4. PRESS Tab on 'Missing'")
        _assert(not ok, "PRESS on missing element returns False")


async def _test_handle_right_click() -> None:
    print("\n  ── _handle_right_click ───────────────────────────────")
    engine = _make_engine()
    page = _mock_page()
    el = _mock_element(name="Context Menu Area")

    with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=el)):
        ok = await engine._handle_right_click(page, "1. RIGHT CLICK 'Context Menu Area'")
        _assert(ok, "RIGHT CLICK returns True")
        page._mock_locator.click.assert_awaited_once()
        call_kwargs = page._mock_locator.click.call_args
        _assert(call_kwargs.kwargs.get("button") == "right",
                "click called with button='right'")


async def _test_handle_right_click_not_found() -> None:
    print("\n  ── _handle_right_click — not found ───────────────────")
    engine = _make_engine()
    page = _mock_page()

    with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=None)):
        ok = await engine._handle_right_click(page, "2. RIGHT CLICK 'Ghost'")
        _assert(not ok, "RIGHT CLICK on missing element returns False")


async def _test_handle_right_click_shadow() -> None:
    print("\n  ── _handle_right_click — shadow DOM ──────────────────")
    engine = _make_engine()
    page = _mock_page()
    el = _mock_element(name="Shadow Button")
    el["is_shadow"] = True

    with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=el)):
        ok = await engine._handle_right_click(page, "3. RIGHT CLICK 'Shadow Button'")
        _assert(ok, "RIGHT CLICK shadow element returns True")
        # Should dispatch contextmenu event via JS, not locator.click
        page.evaluate.assert_awaited()
        _assert(True, "JS contextmenu dispatched for shadow element")


async def _test_handle_upload() -> None:
    print("\n  ── _handle_upload ────────────────────────────────────")
    engine = _make_engine()
    page = _mock_page()
    el = _mock_element(name="Profile Picture")
    el["tag_name"] = "input"
    el["input_type"] = "file"

    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "avatar.png"
        test_file.write_bytes(b"\x89PNG")

        with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=el)):
            ok = await engine._handle_upload(
                page, "1. UPLOAD 'avatar.png' to 'Profile Picture'",
                hunt_dir=tmp,
            )
            _assert(ok, "UPLOAD returns True")
            page._mock_locator.set_input_files.assert_awaited_once()
            _assert(True, "set_input_files called")


async def _test_handle_upload_missing_args() -> None:
    print("\n  ── _handle_upload — missing args ─────────────────────")
    engine = _make_engine()
    page = _mock_page()

    ok = await engine._handle_upload(page, "1. UPLOAD to nothing")
    _assert(not ok, "UPLOAD with insufficient quoted args returns False")


async def _test_handle_upload_not_found() -> None:
    print("\n  ── _handle_upload — target not found ─────────────────")
    engine = _make_engine()
    page = _mock_page()

    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "file.pdf"
        test_file.write_bytes(b"%PDF")

        with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=None)):
            ok = await engine._handle_upload(
                page, "2. UPLOAD 'file.pdf' to 'Dropzone'",
                hunt_dir=tmp,
            )
            _assert(not ok, "UPLOAD on missing element returns False")


async def _test_handle_upload_hunt_dir_resolution() -> None:
    print("\n  ── _handle_upload — hunt_dir file resolution ─────────")
    engine = _make_engine()
    page = _mock_page()
    el = _mock_element(name="Import")
    el["tag_name"] = "input"
    el["input_type"] = "file"

    # Create a temporary file in a temp directory to verify resolution
    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "data.csv"
        test_file.write_text("a,b,c")

        with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=el)):
            ok = await engine._handle_upload(
                page, "1. UPLOAD 'data.csv' to 'Import'",
                hunt_dir=tmp,
            )
            _assert(ok, "UPLOAD with existing file in hunt_dir returns True")
            call_args = page._mock_locator.set_input_files.call_args
            resolved = call_args.args[0]
            _assert(str(test_file.resolve()) == resolved,
                    f"file resolved to hunt_dir path: {resolved}")


async def _test_handle_upload_file_not_found() -> None:
    print("\n  ── _handle_upload — file not found ───────────────────")
    engine = _make_engine()
    page = _mock_page()

    with tempfile.TemporaryDirectory() as tmp:
        ok = await engine._handle_upload(
            page, "1. UPLOAD 'nonexistent.pdf' to 'Target'",
            hunt_dir=tmp,
        )
        _assert(not ok, "UPLOAD with missing file returns False")


async def _test_handle_upload_wrong_element_type() -> None:
    print("\n  ── _handle_upload — wrong element type ───────────────")
    engine = _make_engine()
    page = _mock_page()
    el = _mock_element(name="Submit Button")
    # default tag_name is 'button', not 'input type=file'

    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "doc.txt"
        test_file.write_text("hello")

        with patch.object(engine, "_resolve_element", new=AsyncMock(return_value=el)):
            ok = await engine._handle_upload(
                page, "1. UPLOAD 'doc.txt' to 'Submit Button'",
                hunt_dir=tmp,
            )
            _assert(not ok, "UPLOAD on non-file-input element returns False")


async def _test_handle_press_empty_key() -> None:
    print("\n  ── _handle_press — empty key ─────────────────────────")
    engine = _make_engine()
    page = _mock_page()

    ok = await engine._handle_press(page, "1. PRESS ")
    _assert(not ok, "PRESS with no key returns False")
    page.keyboard.press.assert_not_awaited()
    _assert(True, "page.keyboard.press not called")


async def _test_handle_wait_for_element_visible() -> None:
        print("\n  ── _handle_wait_for_element — visible ─────────────────")
        engine = _make_engine()
        page = _mock_page()

        ok, message = await engine._handle_wait_for_element(page, 'Wait for "Welcome, User" to be visible')
        _assert(ok, "Explicit wait visible returns True")
        _assert(message == "Element is now visible", "Visible wait success message", message)
        page.get_by_text.assert_called_once_with("Welcome, User", exact=False)
        page._mock_locator.wait_for.assert_awaited_once_with(state="visible", timeout=15_000)


async def _test_handle_wait_for_element_disappear() -> None:
        print("\n  ── _handle_wait_for_element — disappear ───────────────")
        engine = _make_engine()
        page = _mock_page()

        ok, message = await engine._handle_wait_for_element(page, "Wait for 'Loading...' to disappear")
        _assert(ok, "Explicit wait disappear returns True")
        _assert(message == "Element is now hidden", "Disappear maps to hidden", message)
        page._mock_locator.wait_for.assert_awaited_once_with(state="hidden", timeout=15_000)


async def _test_handle_wait_for_element_timeout() -> None:
        print("\n  ── _handle_wait_for_element — timeout ─────────────────")
        engine = _make_engine()
        page = _mock_page()
        page._mock_locator.wait_for = AsyncMock(side_effect=PlaywrightTimeoutError("boom"))

        ok, message = await engine._handle_wait_for_element(page, 'Wait for "Submit" to be hidden')
        _assert(not ok, "Explicit wait timeout returns False")
        _assert(message == "Timeout waiting 15s for element to be hidden",
                        "Timeout message includes mapped state", message)


# ── Suite runner ──────────────────────────────────────────────────────────────

async def run_suite() -> bool:
        global _PASS, _FAIL
        _PASS = 0
        _FAIL = 0

        print("\n═══ test_23_advanced_interactions ═══════════════════════")

        # Synchronous parser tests
        _test_classify_step()
        _test_re_system_step()

        # Async handler tests
        await _test_handle_press_global()
        await _test_handle_press_combo()
        await _test_handle_press_targeted()
        await _test_handle_press_targeted_not_found()
        await _test_handle_right_click()
        await _test_handle_right_click_not_found()
        await _test_handle_right_click_shadow()
        await _test_handle_upload()
        await _test_handle_upload_missing_args()
        await _test_handle_upload_not_found()
        await _test_handle_upload_hunt_dir_resolution()
        await _test_handle_upload_file_not_found()
        await _test_handle_upload_wrong_element_type()
        await _test_handle_press_empty_key()
        await _test_handle_wait_for_element_visible()
        await _test_handle_wait_for_element_disappear()
        await _test_handle_wait_for_element_timeout()

        print(f"\n  ── RESULT: {_PASS} passed, {_FAIL} failed ──")
        total = _PASS + _FAIL
        print(f"\n📊 SCORE: {_PASS}/{total} passed")
        return _FAIL == 0
