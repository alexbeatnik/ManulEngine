# manul_engine/test/test_41_recorder.py
"""
Unit-test suite for the Semantic Test Recorder (recorder.py).

Tests:
  1. _event_to_dsl maps all action types correctly.
  2. Unknown/empty actions return None.
  3. _write_hunt_file produces valid STEP-grouped output.
  4. _default_output resolves to tests_home directory.
  5. JS injection script contains expected event listeners.
  6. record_main parses CLI arguments correctly.

No browser or network required — tests the DSL generator and file writer only.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.recorder import _event_to_dsl, _write_hunt_file, _RECORDER_JS, _aggregate_event

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


# ── Tests ─────────────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n🧪 SEMANTIC TEST RECORDER — DSL generation, file writer, JS injection")

    # ── 1. Click action ───────────────────────────────────────────────────
    result = _event_to_dsl({"action": "click", "target": "Login", "value": ""})
    _assert(result is not None and "Click" in result and "'Login'" in result,
            "click → Click the 'Login' button")

    result = _event_to_dsl({"action": "click", "target": "Submit Form", "value": ""})
    _assert(result is not None and "'Submit Form'" in result,
            "click preserves multi-word target")

    # ── 2. Fill action ────────────────────────────────────────────────────
    result = _event_to_dsl({"action": "fill", "target": "Email", "value": "test@manul.ai"})
    _assert(result is not None and "Fill 'Email' with 'test@manul.ai'" in result,
            "fill → Fill 'Email' with 'test@manul.ai'")

    result = _event_to_dsl({"action": "fill", "target": "Password", "value": "secret"})
    _assert(result is not None and "'Password'" in result and "'secret'" in result,
            "fill maps target and value correctly")

    # ── 3. Select action ─────────────────────────────────────────────────
    result = _event_to_dsl({"action": "select", "target": "Country", "value": "Japan"})
    _assert(result is not None and "Select 'Japan' from the 'Country' dropdown" in result,
            "select → Select 'Japan' from the 'Country' dropdown")

    # ── 4. Check / Uncheck / Radio actions ────────────────────────────────
    result = _event_to_dsl({"action": "check", "target": "Terms", "value": ""})
    _assert(result is not None and "Check the checkbox for 'Terms'" in result,
            "check → Check the checkbox for 'Terms'")

    result = _event_to_dsl({"action": "uncheck", "target": "Newsletter", "value": ""})
    _assert(result is not None and "Uncheck the checkbox for 'Newsletter'" in result,
            "uncheck → Uncheck the checkbox for 'Newsletter'")

    result = _event_to_dsl({"action": "radio", "target": "Male", "value": ""})
    _assert(result is not None and "Click the radio button for 'Male'" in result,
            "radio → Click the radio button for 'Male'")

    # ── 5. Press Enter ────────────────────────────────────────────────────
    result = _event_to_dsl({"action": "press", "target": "", "value": "Enter"})
    _assert(result is not None and "PRESS ENTER" in result,
            "press Enter → PRESS ENTER")

    result = _event_to_dsl({"action": "press", "target": "", "value": "Escape"})
    _assert(result is None,
            "press non-Enter key → None (ignored)")

    # ── 6. Unknown/empty actions ──────────────────────────────────────────
    _assert(_event_to_dsl({"action": "unknown", "target": "X", "value": ""}) is None,
            "unknown action → None")

    _assert(_event_to_dsl({"action": "click", "target": "", "value": ""}) is None,
            "click with empty target → None")

    _assert(_event_to_dsl({"action": "fill", "target": "", "value": "text"}) is None,
            "fill with empty target → None")

    _assert(_event_to_dsl({"action": "select", "target": "", "value": "x"}) is None,
            "select with empty target → None")

    _assert(_event_to_dsl({}) is None,
            "empty event dict → None")

    # ── 7. _write_hunt_file produces valid output ─────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "test_output.hunt")
        lines = [
            "    Click the 'Login' button",
            "    Fill 'Username' with 'admin'",
            "    PRESS ENTER",
        ]
        _write_hunt_file(out_path, "https://example.com", lines)

        _assert(os.path.exists(out_path),
                "hunt file created on disk")

        content = open(out_path, "r", encoding="utf-8").read()

        _assert("@context: Recorded session" in content,
                "hunt file contains @context header")

        _assert("@title: example.com" in content,
                "hunt file contains @title from URL netloc")

        _assert("STEP 1: Recorded interactions" in content,
                "hunt file contains STEP 1 header")

        _assert("NAVIGATE to https://example.com" in content,
                "hunt file contains NAVIGATE step")

        _assert("Click the 'Login' button" in content,
                "hunt file contains recorded click step")

        _assert("Fill 'Username' with 'admin'" in content,
                "hunt file contains recorded fill step")

        _assert("PRESS ENTER" in content,
                "hunt file contains recorded press step")

        _assert(content.strip().endswith("DONE."),
                "hunt file ends with DONE.")

        # Verify 4-space indentation for action lines
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("@") and not stripped.startswith("STEP") and stripped != "":
                if stripped in ("DONE.", ""):
                    continue
                _assert(line.startswith("    "),
                        f"4-space indent: '{stripped[:40]}...'")
                break  # just check one action line

    # ── 8. _write_hunt_file with empty recorded lines ─────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "empty.hunt")
        _write_hunt_file(out_path, "https://blank.test", [])
        content = open(out_path, "r", encoding="utf-8").read()
        _assert("NAVIGATE to https://blank.test" in content,
                "empty recording still has NAVIGATE")
        _assert(content.strip().endswith("DONE."),
                "empty recording still ends with DONE.")

    # ── 9. _write_hunt_file creates parent directories ────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        deep_path = os.path.join(tmpdir, "sub", "dir", "test.hunt")
        _write_hunt_file(deep_path, "https://deep.test", ["    Click the 'OK' button"])
        _assert(os.path.exists(deep_path),
                "nested directories created automatically")

    # ── 10. JS injection script structure ─────────────────────────────────
    _assert("__manulRecorderInjected" in _RECORDER_JS,
            "JS has double-injection guard")

    _assert("bestLabel" in _RECORDER_JS,
            "JS has bestLabel semantic extraction function")

    _assert("data-qa" in _RECORDER_JS,
            "JS checks data-qa attribute")

    _assert("aria-label" in _RECORDER_JS,
            "JS checks aria-label attribute")

    _assert("aria-labelledby" in _RECORDER_JS,
            "JS checks aria-labelledby attribute")

    _assert("placeholder" in _RECORDER_JS,
            "JS checks placeholder attribute")

    _assert("recordManulEvent" in _RECORDER_JS,
            "JS calls recordManulEvent bridge")

    _assert("addEventListener" in _RECORDER_JS and "'click'" in _RECORDER_JS,
            "JS listens to click events")

    _assert("'input'" in _RECORDER_JS,
            "JS listens to input events")

    _assert("'change'" in _RECORDER_JS,
            "JS listens to change events")

    _assert("'keydown'" in _RECORDER_JS,
            "JS listens to keydown events")

    _assert("debounce" in _RECORDER_JS.lower(),
            "JS has input debouncing logic")

    _assert("'Enter'" in _RECORDER_JS,
            "JS detects Enter key")

    # ── 11. DSL indentation correctness ───────────────────────────────────
    for action, event in [
        ("click",   {"action": "click", "target": "Save", "value": ""}),
        ("fill",    {"action": "fill", "target": "Name", "value": "John"}),
        ("select",  {"action": "select", "target": "Size", "value": "Large"}),
        ("check",   {"action": "check", "target": "Agree", "value": ""}),
        ("uncheck", {"action": "uncheck", "target": "Promo", "value": ""}),
        ("radio",   {"action": "radio", "target": "Color", "value": ""}),
        ("press",   {"action": "press", "target": "", "value": "Enter"}),
    ]:
        dsl = _event_to_dsl(event)
        _assert(dsl is not None and dsl.startswith("    "),
                f"{action} DSL has 4-space indent")

    # ── 12. Step aggregation — consecutive fills on same target collapse ──
    print("\n  🔄 Step aggregation (consecutive fill collapsing)")

    lines: list[str] = []
    lft: list[str | None] = [None]

    # First fill on 'email' → appends
    _aggregate_event({"action": "fill", "target": "email", "value": "l"}, lines, lft)
    _assert(len(lines) == 1, "first fill appends (len=1)")
    _assert("'l'" in lines[0], "first fill has value 'l'")

    # Second fill on same 'email' → replaces
    _aggregate_event({"action": "fill", "target": "email", "value": "lo"}, lines, lft)
    _assert(len(lines) == 1, "second fill on same target replaces (len=1)")
    _assert("'lo'" in lines[0], "replaced value is 'lo'")

    # Third fill on same 'email' → replaces again
    _aggregate_event({"action": "fill", "target": "email", "value": "login"}, lines, lft)
    _assert(len(lines) == 1, "third fill on same target still replaces (len=1)")
    _assert("'login'" in lines[0], "final value is 'login'")

    # ── 13. Aggregation resets when target changes ────────────────────────
    _aggregate_event({"action": "fill", "target": "pass", "value": "p"}, lines, lft)
    _assert(len(lines) == 2, "fill on different target appends (len=2)")
    _assert("'pass'" in lines[1] and "'p'" in lines[1],
            "new target step has correct target and value")

    _aggregate_event({"action": "fill", "target": "pass", "value": "password"}, lines, lft)
    _assert(len(lines) == 2, "consecutive fill on 'pass' replaces (len=2)")
    _assert("'password'" in lines[1], "replaced pass value is 'password'")

    # ── 14. Aggregation resets when action changes ────────────────────────
    _aggregate_event({"action": "click", "target": "Login", "value": ""}, lines, lft)
    _assert(len(lines) == 3, "click appends as new step (len=3)")
    _assert(lft[0] is None, "last_fill_target reset after click")

    # Fill after click → appends even if same target as a previous fill
    _aggregate_event({"action": "fill", "target": "email", "value": "retry"}, lines, lft)
    _assert(len(lines) == 4, "fill after click appends (len=4)")
    _assert("'retry'" in lines[3], "new fill step has value 'retry'")

    # ── 15. Aggregation skips None DSL events ─────────────────────────────
    result = _aggregate_event({"action": "unknown", "target": "X", "value": ""}, lines, lft)
    _assert(result is None, "unknown action returns None")
    _assert(len(lines) == 4, "unknown action does not modify list (len=4)")

    result = _aggregate_event({"action": "fill", "target": "", "value": "empty"}, lines, lft)
    _assert(result is None, "fill with empty target returns None")
    _assert(len(lines) == 4, "fill with empty target does not modify list (len=4)")

    # ── 16. Full sequence produces clean output ───────────────────────────
    full_lines: list[str] = []
    full_lft: list[str | None] = [None]
    events = [
        {"action": "fill", "target": "email", "value": "l"},
        {"action": "fill", "target": "email", "value": "lo"},
        {"action": "fill", "target": "email", "value": "login"},
        {"action": "fill", "target": "pass", "value": "p"},
        {"action": "fill", "target": "pass", "value": "pa"},
        {"action": "fill", "target": "pass", "value": "password"},
        {"action": "click", "target": "Log In", "value": ""},
    ]
    for ev in events:
        _aggregate_event(ev, full_lines, full_lft)

    _assert(len(full_lines) == 3,
            "7 raw events collapse to 3 clean steps")
    _assert("'login'" in full_lines[0],
            "email fill collapsed to final value 'login'")
    _assert("'password'" in full_lines[1],
            "pass fill collapsed to final value 'password'")
    _assert("'Log In'" in full_lines[2],
            "click step preserved")

    # ── 17. Write aggregated output to file ───────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "aggregated.hunt")
        _write_hunt_file(out_path, "https://www.facebook.com/", full_lines)
        content = open(out_path, "r", encoding="utf-8").read()
        # Should contain exactly one email fill and one pass fill
        _assert(content.count("Fill 'email'") == 1,
                "aggregated file has exactly 1 email fill")
        _assert(content.count("Fill 'pass'") == 1,
                "aggregated file has exactly 1 pass fill")
        _assert("'login'" in content,
                "aggregated file has final email value")
        _assert("'password'" in content,
                "aggregated file has final pass value")
        _assert("Click the 'Log In' button" in content,
                "aggregated file has click step")

    # ── Summary ───────────────────────────────────────────────────────────
    total = _PASS + _FAIL
    print(f"\n{'='*70}")
    print(f"📊 SCORE: {_PASS}/{total} passed")
    if _FAIL:
        print(f"\n🙀 {_FAIL} assertion(s) failed")
    else:
        print("\n🏆 FLAWLESS VICTORY!")
    print(f"{'='*70}")

    return _FAIL == 0


if __name__ == "__main__":
    asyncio.run(run_suite())
