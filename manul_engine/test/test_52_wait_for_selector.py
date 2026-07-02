# manul_engine/test/test_52_wait_for_selector.py
"""
Unit-test suite for WAIT FOR SELECTOR and CSS-selector detection in
WAIT FOR '...' TO BE VISIBLE.

Tests:
  Section 1: classify_step() — WAIT FOR SELECTOR recognised as new kind
  Section 2: classify_step() — existing kinds not disrupted
  Section 3: CSS-selector heuristic (_is_css_target) — true positives
  Section 4: CSS-selector heuristic — true negatives (plain text)
  Section 5: parse_explicit_wait() — WAIT FOR SELECTOR is NOT swallowed
  Section 6: Integration — WAIT FOR SELECTOR in parse_hunt_blocks()
  Section 7: _handle_wait_for_selector happy path (synthetic DOM)
  Section 8: _handle_wait_for_selector timeout path (element absent)
  Section 9: _handle_wait_for_element CSS branch — routes to wait_for_selector
  Section 10: _handle_wait_for_element text branch — unchanged behaviour

No external network required.
Sections 1–6 are pure-Python (no Playwright).
Sections 7–10 use a synthetic DOM served via Playwright.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile
from typing import ClassVar

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.helpers import classify_step, parse_explicit_wait, parse_hunt_blocks

# ── Test counters ─────────────────────────────────────────────────────────────

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


# ── CSS-selector heuristic (mirrors actions.py) ───────────────────────────────


def _is_css_target(target: str) -> bool:
    return bool(
        re.match(r"^[#.\[a-z]", target, re.IGNORECASE)
        and (target.startswith(("#", ".", "[")) or re.search(r"[\[>:]", target) or "-" in target)
    )


# ── Section 1: classify_step — WAIT FOR SELECTOR ─────────────────────────────


def test_classify_wait_for_selector():
    print("\n── Section 1: classify_step — WAIT FOR SELECTOR ──")

    _assert(
        classify_step("WAIT FOR SELECTOR 'ytd-video-renderer'") == "wait_for_selector",
        "WAIT FOR SELECTOR single-quoted custom element",
    )
    _assert(
        classify_step('WAIT FOR SELECTOR "#main > div"') == "wait_for_selector",
        "WAIT FOR SELECTOR double-quoted id child combinator",
    )
    _assert(
        classify_step("WAIT FOR SELECTOR '.search-results'") == "wait_for_selector",
        "WAIT FOR SELECTOR class selector",
    )
    _assert(
        classify_step("wait for selector '[data-testid=\"card\"]'") == "wait_for_selector",
        "wait for selector lowercase attribute selector",
    )
    _assert(
        classify_step("1. WAIT FOR SELECTOR 'input[type=text]'") == "wait_for_selector",
        "WAIT FOR SELECTOR with leading step number",
    )


# ── Section 2: classify_step — existing kinds unaffected ─────────────────────


def test_classify_existing_wait_kinds():
    print("\n── Section 2: classify_step — existing kinds not disrupted ──")

    _assert(
        classify_step("WAIT FOR 'Submit' TO BE VISIBLE") == "wait_for_element",
        "WAIT FOR text TO BE VISIBLE → wait_for_element",
    )
    _assert(
        classify_step("WAIT FOR 'ytd-video-renderer' TO BE VISIBLE") == "wait_for_element",
        "WAIT FOR css-like text TO BE VISIBLE → wait_for_element (not selector)",
    )
    _assert(
        classify_step("WAIT FOR 'Loading' TO DISAPPEAR") == "wait_for_element",
        "WAIT FOR text TO DISAPPEAR → wait_for_element",
    )
    _assert(
        classify_step("WAIT FOR RESPONSE '/api/data'") == "wait_for_response",
        "WAIT FOR RESPONSE unchanged",
    )
    _assert(
        classify_step("WAIT 3") == "wait",
        "WAIT N seconds unchanged",
    )
    _assert(
        classify_step("WAIT 10") == "wait",
        "WAIT 10 seconds unchanged",
    )


# ── Section 3: CSS heuristic — true positives ─────────────────────────────────


def test_css_heuristic_positives():
    print("\n── Section 3: CSS-selector heuristic — true positives ──")

    cases = [
        ("ytd-video-renderer", "custom element with hyphen"),
        ("#main", "id selector"),
        (".container", "class selector"),
        ("[data-id]", "attribute selector"),
        ("div > span", "child combinator"),
        ("input[type=text]", "element with attribute"),
        ("a:nth-child(2)", "pseudo-class"),
        (".search-results li", "class + descendant"),
        ("ytd-rich-item-renderer", "long custom element"),
        ("#header > nav", "id child combinator"),
    ]
    for selector, label in cases:
        _assert(_is_css_target(selector), f"CSS positive: {label} ({selector!r})")


# ── Section 4: CSS heuristic — true negatives ────────────────────────────────


def test_css_heuristic_negatives():
    print("\n── Section 4: CSS-selector heuristic — true negatives ──")

    cases = [
        ("Submit Button", "plain words"),
        ("Login", "single word"),
        ("Search results", "two plain words"),
        ("Loading indicator", "loading text"),
        ("Error message", "error text"),
        ("Continue to next page", "sentence"),
    ]
    for text, label in cases:
        _assert(not _is_css_target(text), f"CSS negative: {label} ({text!r})")


# ── Section 5: parse_explicit_wait does not eat WAIT FOR SELECTOR ─────────────


def test_parse_explicit_wait_does_not_match_selector():
    print("\n── Section 5: parse_explicit_wait ignores WAIT FOR SELECTOR ──")

    target, state = parse_explicit_wait("WAIT FOR SELECTOR 'ytd-video-renderer'")
    _assert(target is None, "target is None for WAIT FOR SELECTOR", f"got {target!r}")
    _assert(state is None, "state is None for WAIT FOR SELECTOR", f"got {state!r}")

    target2, state2 = parse_explicit_wait('WAIT FOR SELECTOR "#main"')
    _assert(target2 is None, "target is None for double-quoted selector", f"got {target2!r}")


# ── Section 6: parse_hunt_blocks integration ──────────────────────────────────


def test_parse_hunt_blocks_wait_for_selector():
    print("\n── Section 6: parse_hunt_blocks — WAIT FOR SELECTOR in DSL ──")

    task = """STEP 1: Search and wait
    NAVIGATE https://example.com
    FILL 'Search' 'cats'
    PRESS Enter
    WAIT FOR SELECTOR 'ytd-video-renderer'
    SCAN PAGE"""

    blocks = parse_hunt_blocks(task)
    _assert(len(blocks) == 1, "One STEP block", f"got {len(blocks)}")

    actions = blocks[0].actions
    _assert(len(actions) == 5, "Five actions parsed", f"got {len(actions)}")
    _assert(
        actions[3] == "WAIT FOR SELECTOR 'ytd-video-renderer'",
        "WAIT FOR SELECTOR preserved verbatim",
        f"got {actions[3]!r}",
    )

    # Confirm all classify correctly
    kinds = [classify_step(a) for a in actions if isinstance(a, str)]
    _assert(kinds[3] == "wait_for_selector", "Fourth action classifies as wait_for_selector")


# ── Synthetic DOM helpers ─────────────────────────────────────────────────────

_HTML_WITH_SELECTOR = """\
<!DOCTYPE html>
<html>
<body>
  <div class="search-results">
    <div class="result-item">Result One</div>
    <div class="result-item">Result Two</div>
  </div>
  <ytd-video-renderer>Video title here</ytd-video-renderer>
</body>
</html>
"""

_HTML_EMPTY = """\
<!DOCTYPE html>
<html><body><p>Nothing here</p></body></html>
"""


async def _serve_html(html: str) -> str:
    """Write HTML to a temp file and return a file:// URL."""
    fd, path = tempfile.mkstemp(suffix=".html", prefix="manul_test_")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"file://{path}", path


# ── Minimal stub engine for actions-only testing ──────────────────────────────


class _StubEngine:
    """Minimal engine stub — just enough for _ActionsMixin methods under test."""

    _EXPLICIT_WAIT_TIMEOUT_MS = 5_000  # short for tests
    _semantic_cache_enabled = False
    learned_elements: ClassVar[dict] = {}
    memory: ClassVar[dict] = {}
    last_xpath = None
    nav_timeout = 10_000
    timeout = 5_000
    debug_mode = False
    break_steps: ClassVar[set] = set()
    _verify_max_retries = 2

    def _frame_for(self, page, el):
        return page

    def _fmt_el_name(self, name):
        return str(name)


def _make_engine():
    from manul_engine.actions import _ActionsMixin

    class _Engine(_StubEngine, _ActionsMixin):
        pass

    return _Engine()


# ── Section 7: _handle_wait_for_selector happy path ──────────────────────────


async def test_wait_for_selector_happy():
    print("\n── Section 7: _handle_wait_for_selector — happy path ──")
    from manul_engine.cdp import CDPBrowser

    url, path = await _serve_html(_HTML_WITH_SELECTOR)
    try:
        async with CDPBrowser(headless=True) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            engine = _make_engine()

            ok, msg = await engine._handle_wait_for_selector(page, "WAIT FOR SELECTOR '.result-item'")
            _assert(ok, "wait_for_selector succeeds for existing class", msg)
            _assert("result-item" in msg, "success message contains selector", msg)

            ok2, msg2 = await engine._handle_wait_for_selector(page, "WAIT FOR SELECTOR 'ytd-video-renderer'")
            _assert(ok2, "wait_for_selector succeeds for custom element", msg2)

            await browser.close()
    finally:
        os.unlink(path)


# ── Section 8: _handle_wait_for_selector timeout path ────────────────────────


async def test_wait_for_selector_timeout():
    print("\n── Section 8: _handle_wait_for_selector — timeout ──")
    from manul_engine.cdp import CDPBrowser

    url, path = await _serve_html(_HTML_EMPTY)
    try:
        async with CDPBrowser(headless=True) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            engine = _make_engine()
            engine._EXPLICIT_WAIT_TIMEOUT_MS = 1_000  # fast timeout for test

            ok, msg = await engine._handle_wait_for_selector(page, "WAIT FOR SELECTOR '.nonexistent-element'")
            _assert(not ok, "wait_for_selector fails when selector absent", msg)
            _assert("Timeout" in msg or "timeout" in msg, "error message mentions timeout", msg)

            await browser.close()
    finally:
        os.unlink(path)


# ── Section 9: _handle_wait_for_element CSS branch ───────────────────────────


async def test_wait_for_element_css_branch():
    print("\n── Section 9: _handle_wait_for_element — CSS branch ──")
    from manul_engine.cdp import CDPBrowser

    url, path = await _serve_html(_HTML_WITH_SELECTOR)
    try:
        async with CDPBrowser(headless=True) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            engine = _make_engine()

            # Class selector — routes to wait_for_selector internally
            ok, msg = await engine._handle_wait_for_element(page, "WAIT FOR '.search-results' TO BE VISIBLE")
            _assert(ok, "CSS class selector branch succeeds", msg)

            # Custom element with hyphen
            ok2, msg2 = await engine._handle_wait_for_element(page, "WAIT FOR 'ytd-video-renderer' TO BE VISIBLE")
            _assert(ok2, "Custom element (hyphen) branch succeeds", msg2)

            # id selector
            ok3, msg3 = await engine._handle_wait_for_element(page, "WAIT FOR '.result-item' TO BE VISIBLE")
            _assert(ok3, "Class selector routes to CSS branch", msg3)

            await browser.close()
    finally:
        os.unlink(path)


# ── Section 10: _handle_wait_for_element text branch (unchanged) ──────────────


async def test_wait_for_element_text_branch():
    print("\n── Section 10: _handle_wait_for_element — text branch unchanged ──")
    from manul_engine.cdp import CDPBrowser

    url, path = await _serve_html(_HTML_WITH_SELECTOR)
    try:
        async with CDPBrowser(headless=True) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            engine = _make_engine()

            ok, msg = await engine._handle_wait_for_element(page, "WAIT FOR 'Result One' TO BE VISIBLE")
            _assert(ok, "Plain text wait succeeds via get_by_text branch", msg)

            ok2, msg2 = await engine._handle_wait_for_element(page, "WAIT FOR 'Video title here' TO BE VISIBLE")
            _assert(ok2, "Plain text wait inside custom element succeeds", msg2)

            # Absent text → timeout
            engine._EXPLICIT_WAIT_TIMEOUT_MS = 1_000
            ok3, msg3 = await engine._handle_wait_for_element(page, "WAIT FOR 'Totally Absent Text XYZ' TO BE VISIBLE")
            _assert(not ok3, "Plain text wait times out when absent", msg3)

            await browser.close()
    finally:
        os.unlink(path)


# ── run_suite ─────────────────────────────────────────────────────────────────


async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    # Pure-Python sections (no Playwright)
    test_classify_wait_for_selector()
    test_classify_existing_wait_kinds()
    test_css_heuristic_positives()
    test_css_heuristic_negatives()
    test_parse_explicit_wait_does_not_match_selector()
    test_parse_hunt_blocks_wait_for_selector()

    # Playwright sections
    await test_wait_for_selector_happy()
    await test_wait_for_selector_timeout()
    await test_wait_for_element_css_branch()
    await test_wait_for_element_text_branch()

    total = _PASS + _FAIL
    print(f"\n  Wait-for-selector suite: {_PASS} passed, {_FAIL} failed")
    print(f"SCORE: {_PASS}/{total}")
    return _PASS, _FAIL


if __name__ == "__main__":
    p, f = asyncio.run(run_suite())
    raise SystemExit(0 if f == 0 else 1)
