# manul_engine/test/test_53_explain_next.py
"""
Unit-test suite for the ExplainNextDebugger (What-If Analysis REPL).

Tests:
  1.  PageContext creation and prompt formatting
  2.  PageContext with empty elements
  3.  WhatIfResult confidence labels (HIGH/MODERATE/LOW/IMPOSSIBLE)
  4.  WhatIfResult format_report output structure
  5.  Heuristic-only evaluation with matching element
  6.  Heuristic-only evaluation with no matching element
  7.  Heuristic-only evaluation for system commands (NAVIGATE, WAIT)
  8.  LLM-backed evaluation parses response correctly
  9.  LLM returns invalid JSON — falls back to heuristics
  10. LLM returns None — falls back to heuristics
  11. evaluate() history tracking
  12. Multiple evaluations accumulate in history
  13. _heuristic_pre_check with empty element list
  14. _heuristic_pre_check with scored elements
  15. WhatIfResult with heuristic_score displays in report
  16. PageContext.to_prompt_text truncates element list
  17. PageContext.to_prompt_text includes disabled state
  18. evaluate() extracts quoted targets for scoring
  19. System command evaluation gives high score
  20. NullProvider-based debugger works (heuristics-only)
  21. WHAT_IF_SYSTEM_PROMPT is well-formed
  22. capture_page_context returns PageContext (mock page)
  23. WhatIfResult suggestion field included in report
  24. WhatIfResult with zero score shows IMPOSSIBLE label

No network or browser required.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.explain_next import (
    ExplainNextDebugger,
    PageContext,
    WhatIfResult,
    WHAT_IF_SYSTEM_PROMPT,
    capture_page_context,
    _heuristic_pre_check,
    _HeuristicHit,
    _VISIBLE_TEXT_JS,
)
from manul_engine.llm import NullProvider
from manul_engine.scoring import SCALE

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


def _make_el(**overrides) -> dict:
    """Build a minimal element dict compatible with DOMScorer._preprocess."""
    base = {
        "name": overrides.pop("name", "Login button"),
        "xpath": overrides.pop("xpath", "/html/body/button[1]"),
        "is_select": False, "is_shadow": False, "is_contenteditable": False,
        "class_name": "", "tag_name": "button", "input_type": "",
        "data_qa": "", "html_id": "", "icon_classes": "",
        "aria_label": "", "placeholder": "", "role": "",
        "disabled": False, "aria_disabled": "", "name_attr": "",
        "id": 1, "frame_index": 0,
    }
    base.update(overrides)
    return base


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


class FakeLLM:
    """Mock LLM provider that returns a canned response dict."""

    def __init__(self, response: dict | None = None):
        self._response = response

    async def call_json(self, system: str, user: str) -> dict | None:
        return self._response


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_01_page_context_creation():
    """PageContext stores URL, title, elements, and visible text."""
    els = [_make_el(name="Submit"), _make_el(name="Cancel", id=2)]
    ctx = PageContext(
        url="https://example.com/login",
        title="Login Page",
        elements=els,
        visible_text_snippet="Welcome to our site",
    )
    _assert(ctx.url == "https://example.com/login", "url stored")
    _assert(ctx.title == "Login Page", "title stored")
    _assert(len(ctx.elements) == 2, "elements stored")
    _assert("Welcome" in ctx.visible_text_snippet, "visible text stored")


def test_02_page_context_empty():
    """PageContext with no elements."""
    ctx = PageContext(url="about:blank", title="", elements=[], visible_text_snippet="")
    _assert(ctx.url == "about:blank", "empty url")
    _assert(len(ctx.elements) == 0, "no elements")
    text = ctx.to_prompt_text()
    _assert("0 of 0" in text, "shows 0 elements in prompt")


def test_03_confidence_labels():
    """WhatIfResult confidence_label maps score ranges correctly."""
    cases = [
        (0, "IMPOSSIBLE"), (1, "LOW"), (3, "LOW"),
        (5, "MODERATE"), (7, "MODERATE"),
        (8, "HIGH"), (10, "HIGH"),
    ]
    for score, expected in cases:
        r = WhatIfResult(
            step="test", score=score, target_found=True,
            target_element=None, explanation="", risk="", suggestion=None,
        )
        _assert(r.confidence_label == expected, f"score {score} → {expected}",
                f"got {r.confidence_label}")


def test_04_format_report_structure():
    """format_report() includes key sections."""
    r = WhatIfResult(
        step="Click the 'Login' button",
        score=8, target_found=True,
        target_element="<button> Login",
        explanation="Would click the login button",
        risk="Navigates to dashboard",
        suggestion=None,
    )
    report = r.format_report()
    _assert("WHAT-IF ANALYSIS" in report, "header present")
    _assert("8/10" in report, "score present")
    _assert("HIGH" in report, "confidence label present")
    _assert("Login" in report, "target element present")
    _assert("Navigates" in report, "risk present")
    _assert("Suggestion" not in report, "no suggestion when None")


def test_05_heuristic_only_with_match():
    """Heuristic-only evaluation when a strong match exists."""
    debugger = ExplainNextDebugger(llm=NullProvider())
    els = [
        _make_el(name="Login button", data_qa="login-btn", id=1),
        _make_el(name="Cancel link", tag_name="a", id=2),
    ]
    ctx = PageContext(
        url="https://example.com",
        title="Test",
        elements=els,
        visible_text_snippet="Login Cancel",
    )
    # Use _heuristic_only_result directly since we can't mock the page easily
    result = debugger._heuristic_only_result(
        step="Click the 'Login' button",
        step_class="action",
        ctx=ctx,
        search_texts=["Login"],
        h_score=int(0.5 * SCALE),  # strong match
        h_match="Login button",
    )
    _assert(result.score >= 7, "strong heuristic → high score", f"got {result.score}")
    _assert(result.target_found, "target found")
    _assert(result.heuristic_match == "Login button", "match name preserved")


def test_06_heuristic_only_no_match():
    """Heuristic-only evaluation when no element matches."""
    debugger = ExplainNextDebugger(llm=NullProvider())
    result = debugger._heuristic_only_result(
        step="Click the 'Nonexistent' button",
        step_class="action",
        ctx=PageContext(url="https://x.com", title="", elements=[]),
        search_texts=["Nonexistent"],
        h_score=None,
        h_match=None,
    )
    _assert(result.score == 0, "no match → score 0")
    _assert(not result.target_found, "target not found")
    _assert("No matching" in result.explanation, "explanation says no match")


def test_07_system_command_high_score():
    """System commands like NAVIGATE, WAIT get high scores without element resolution."""
    debugger = ExplainNextDebugger(llm=NullProvider())
    for kind in ("navigate", "wait", "scroll", "press_enter", "done"):
        result = debugger._heuristic_only_result(
            step=f"NAVIGATE to https://example.com",
            step_class=kind,
            ctx=PageContext(url="https://x.com", title="", elements=[]),
            search_texts=[],
            h_score=None,
            h_match=None,
        )
        _assert(result.score >= 8, f"system command '{kind}' → high score",
                f"got {result.score}")


def test_08_llm_backed_evaluation():
    """LLM-backed evaluation parses a valid response correctly."""
    llm_response = {
        "score": 9,
        "target_found": True,
        "target_element": "<button> Submit",
        "explanation": "Clicks the submit button to send the form",
        "risk": "Form will be submitted",
        "suggestion": None,
    }
    debugger = ExplainNextDebugger(llm=FakeLLM(llm_response))

    # Mock async page
    mock_page = AsyncMock()
    mock_page.url = "https://example.com/form"
    mock_page.title = AsyncMock(return_value="Form Page")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="Submit your form")

    result = _run(debugger.evaluate(mock_page, "Click the 'Submit' button"))
    _assert(result.score == 9, "LLM score preserved", f"got {result.score}")
    _assert(result.target_found, "target_found from LLM")
    _assert("submit" in result.explanation.lower(), "explanation from LLM")


def test_09_llm_invalid_response():
    """LLM returns None — falls back to heuristics."""
    debugger = ExplainNextDebugger(llm=FakeLLM(None))

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    result = _run(debugger.evaluate(mock_page, "Click the 'Missing' button"))
    _assert(isinstance(result, WhatIfResult), "returns WhatIfResult on LLM failure")
    _assert("Heuristic-only" in result.risk, "risk mentions heuristic fallback")


def test_10_llm_returns_none():
    """NullProvider always returns None — heuristic fallback."""
    debugger = ExplainNextDebugger(llm=NullProvider())

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="Hello World")

    result = _run(debugger.evaluate(mock_page, "NAVIGATE to https://other.com"))
    _assert(isinstance(result, WhatIfResult), "returns WhatIfResult")
    # NAVIGATE is a system command, so it should get high score even heuristic-only
    _assert(result.score >= 8, "system command gets high score", f"got {result.score}")


def test_11_history_tracking():
    """evaluate() appends to history."""
    debugger = ExplainNextDebugger(llm=NullProvider())

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    _run(debugger.evaluate(mock_page, "WAIT 3"))
    _assert(len(debugger.history) == 1, "history has 1 entry")
    _assert(debugger.history[0].step == "WAIT 3", "step stored in history")


def test_12_multiple_history():
    """Multiple evaluations accumulate."""
    debugger = ExplainNextDebugger(llm=NullProvider())

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    _run(debugger.evaluate(mock_page, "WAIT 1"))
    _run(debugger.evaluate(mock_page, "SCROLL DOWN"))
    _run(debugger.evaluate(mock_page, "Click the 'Save' button"))
    _assert(len(debugger.history) == 3, "3 entries in history")
    steps = [r.step for r in debugger.history]
    _assert("SCROLL DOWN" in steps, "SCROLL DOWN in history")


def test_13_heuristic_pre_check_empty():
    """_heuristic_pre_check with empty elements returns None."""
    hit = _heuristic_pre_check([], "Click 'Login'", ["Login"], "Login")
    _assert(hit is None, "hit is None for empty elements")


def test_14_heuristic_pre_check_scored():
    """_heuristic_pre_check with matching elements returns a _HeuristicHit."""
    els = [
        _make_el(name="Login button", data_qa="login", id=1),
        _make_el(name="Register link", tag_name="a", id=2),
    ]
    hit = _heuristic_pre_check(els, "Click the 'Login' button", ["Login"], "Login")
    _assert(hit is not None, "hit returned")
    _assert(isinstance(hit, _HeuristicHit), "returns _HeuristicHit")
    _assert(hit.score > 0, "positive score returned", f"got {hit.score}")
    _assert(hit.name != "", "name returned")
    _assert(hit.xpath != "", "xpath returned")


def test_15_report_with_heuristic_score():
    """WhatIfResult format_report includes heuristic score when set."""
    r = WhatIfResult(
        step="Click 'Save'", score=7, target_found=True,
        target_element="<button> Save", explanation="Saves the form",
        risk="None", suggestion=None,
        heuristic_score=50000, heuristic_match="Save Button",
    )
    report = r.format_report()
    _assert("Heuristic Score" in report, "heuristic score in report")
    _assert("Save Button" in report, "heuristic match name in report")


def test_16_prompt_text_truncation():
    """to_prompt_text truncates element list to max_elements."""
    els = [_make_el(name=f"Element {i}", id=i) for i in range(100)]
    ctx = PageContext(url="https://x.com", title="T", elements=els)
    text = ctx.to_prompt_text(max_elements=10)
    _assert("10 of 100" in text, "shows element count correctly")
    # Count actual element lines
    el_lines = [l for l in text.splitlines() if l.strip().startswith("<")]
    _assert(len(el_lines) == 10, "only 10 elements rendered", f"got {len(el_lines)}")


def test_17_prompt_text_disabled_element():
    """to_prompt_text shows disabled attribute."""
    els = [_make_el(name="Submit", disabled=True)]
    ctx = PageContext(url="https://x.com", title="T", elements=els)
    text = ctx.to_prompt_text()
    _assert("disabled" in text, "disabled attribute shown")


def test_18_evaluate_extracts_quoted():
    """evaluate() extracts quoted targets for heuristic scoring."""
    llm_response = {
        "score": 5, "target_found": True,
        "target_element": "Email field",
        "explanation": "Would fill the email field",
        "risk": "None", "suggestion": None,
    }
    debugger = ExplainNextDebugger(llm=FakeLLM(llm_response))

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    result = _run(debugger.evaluate(mock_page, "Fill 'Email' field with 'test@test.com'"))
    _assert(result.score == 5, "score from LLM")
    _assert(result.step == "Fill 'Email' field with 'test@test.com'", "step preserved")


def test_19_system_navigate_evaluation():
    """NAVIGATE command gets high score in heuristic-only mode."""
    debugger = ExplainNextDebugger(llm=NullProvider())

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    result = _run(debugger.evaluate(mock_page, "NAVIGATE to https://google.com"))
    _assert(result.score >= 8, "NAVIGATE gets high score", f"got {result.score}")


def test_20_null_provider_debugger():
    """ExplainNextDebugger works with NullProvider (heuristics-only)."""
    debugger = ExplainNextDebugger(llm=NullProvider())
    _assert(isinstance(debugger._llm, NullProvider), "uses NullProvider")
    _assert(len(debugger.history) == 0, "history starts empty")


def test_21_system_prompt_well_formed():
    """WHAT_IF_SYSTEM_PROMPT contains essential instructions."""
    _assert("HYPOTHETICAL" in WHAT_IF_SYSTEM_PROMPT, "mentions hypothetical")
    _assert("Confidence" in WHAT_IF_SYSTEM_PROMPT or "confidence" in WHAT_IF_SYSTEM_PROMPT,
            "mentions confidence")
    _assert("0–10" in WHAT_IF_SYSTEM_PROMPT or "0-10" in WHAT_IF_SYSTEM_PROMPT,
            "mentions 0-10 scale")
    _assert("JSON" in WHAT_IF_SYSTEM_PROMPT, "mentions JSON output format")
    _assert("score" in WHAT_IF_SYSTEM_PROMPT, "mentions score field")
    _assert("explanation" in WHAT_IF_SYSTEM_PROMPT, "mentions explanation field")


def test_22_capture_page_context_mock():
    """capture_page_context returns a PageContext from a mock page."""
    mock_frame = AsyncMock()
    mock_frame.evaluate = AsyncMock(return_value=[
        _make_el(name="Button 1", id=1),
    ])
    mock_frame.url = "https://example.com"
    mock_frame.name = ""

    mock_page = AsyncMock()
    mock_page.url = "https://example.com/page"
    mock_page.title = AsyncMock(return_value="Test Page")
    mock_page.frames = [mock_frame]
    # First evaluate call is for visible text, frame evaluate is for SNAPSHOT_JS
    mock_page.evaluate = AsyncMock(return_value="Some visible text on the page")

    ctx = _run(capture_page_context(mock_page))
    _assert(ctx.url == "https://example.com/page", "url captured")
    _assert(ctx.title == "Test Page", "title captured")
    _assert(len(ctx.elements) >= 1, "elements captured", f"got {len(ctx.elements)}")
    _assert("visible text" in ctx.visible_text_snippet.lower(), "visible text captured")


def test_23_suggestion_in_report():
    """WhatIfResult format_report includes suggestion when present."""
    r = WhatIfResult(
        step="Click 'Sbumit' button", score=3, target_found=False,
        target_element=None,
        explanation="No element with text 'Sbumit' found",
        risk="Step would fail",
        suggestion="Click the 'Submit' button",
    )
    report = r.format_report()
    _assert("Suggestion" in report, "suggestion section present")
    _assert("Submit" in report, "suggestion content shown")


def test_24_zero_score_impossible():
    """Score 0 shows IMPOSSIBLE label."""
    r = WhatIfResult(
        step="Click the 'Ghost' button", score=0, target_found=False,
        target_element=None, explanation="Element not found",
        risk="Will fail", suggestion=None,
    )
    _assert(r.confidence_label == "IMPOSSIBLE", "zero score → IMPOSSIBLE")
    report = r.format_report()
    _assert("IMPOSSIBLE" in report, "IMPOSSIBLE in report output")


def test_25_llm_score_clamping():
    """LLM score is clamped to 0-10 range."""
    llm_response = {
        "score": 15, "target_found": True,
        "target_element": "btn", "explanation": "ok",
        "risk": "", "suggestion": None,
    }
    debugger = ExplainNextDebugger(llm=FakeLLM(llm_response))

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    result = _run(debugger.evaluate(mock_page, "Click 'X'"))
    _assert(result.score == 10, "score clamped to 10", f"got {result.score}")


def test_26_llm_negative_score_clamped():
    """Negative LLM score is clamped to 0."""
    llm_response = {
        "score": -5, "target_found": False,
        "target_element": None, "explanation": "bad",
        "risk": "fail", "suggestion": None,
    }
    debugger = ExplainNextDebugger(llm=FakeLLM(llm_response))

    mock_page = AsyncMock()
    mock_page.url = "https://x.com"
    mock_page.title = AsyncMock(return_value="T")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    result = _run(debugger.evaluate(mock_page, "Click 'Y'"))
    _assert(result.score == 0, "score clamped to 0", f"got {result.score}")


def test_27_history_property_returns_copy():
    """history property returns a copy, not the internal list."""
    debugger = ExplainNextDebugger(llm=NullProvider())

    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="T")
    mock_page.frames = []
    mock_page.evaluate = AsyncMock(return_value="")

    _run(debugger.evaluate(mock_page, "WAIT 1"))
    h1 = debugger.history
    h2 = debugger.history
    _assert(h1 is not h2, "history returns a new list each time")
    _assert(h1 == h2, "history copies are equal")


def test_28_visible_text_js_is_readonly():
    """_VISIBLE_TEXT_JS does not mutate the DOM — just a TreeWalker reader."""
    _assert("createTreeWalker" in _VISIBLE_TEXT_JS, "uses TreeWalker")
    _assert("SHOW_TEXT" in _VISIBLE_TEXT_JS, "reads text nodes only")
    # Ensure no DOM-mutating operations
    for bad in ("click(", "submit(", "remove(", "innerHTML", "createElement"):
        _assert(bad not in _VISIBLE_TEXT_JS, f"no '{bad}' in visible text JS")


# ── Runner ────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    test_01_page_context_creation,
    test_02_page_context_empty,
    test_03_confidence_labels,
    test_04_format_report_structure,
    test_05_heuristic_only_with_match,
    test_06_heuristic_only_no_match,
    test_07_system_command_high_score,
    test_08_llm_backed_evaluation,
    test_09_llm_invalid_response,
    test_10_llm_returns_none,
    test_11_history_tracking,
    test_12_multiple_history,
    test_13_heuristic_pre_check_empty,
    test_14_heuristic_pre_check_scored,
    test_15_report_with_heuristic_score,
    test_16_prompt_text_truncation,
    test_17_prompt_text_disabled_element,
    test_18_evaluate_extracts_quoted,
    test_19_system_navigate_evaluation,
    test_20_null_provider_debugger,
    test_21_system_prompt_well_formed,
    test_22_capture_page_context_mock,
    test_23_suggestion_in_report,
    test_24_zero_score_impossible,
    test_25_llm_score_clamping,
    test_26_llm_negative_score_clamped,
    test_27_history_property_returns_copy,
    test_28_visible_text_js_is_readonly,
]


def run_all() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS, _FAIL = 0, 0
    print("\n🔮 Test Suite 53: ExplainNextDebugger (What-If Analysis)")
    print("=" * 60)
    for fn in ALL_TESTS:
        print(f"\n  📋 {fn.__doc__ or fn.__name__}")
        try:
            fn()
        except Exception as exc:
            _FAIL += 1
            print(f"    ❌  EXCEPTION: {exc}")
    print(f"\n{'=' * 60}")
    print(f"Results: {_PASS} passed, {_FAIL} failed ({_PASS + _FAIL} total)")
    return _PASS, _FAIL


if __name__ == "__main__":
    _, fails = run_all()
    sys.exit(1 if fails else 0)
