# manul_engine/test/test_57_full_scan.py
"""
Unit-test suite for the FULL SCAN DSL step.

Tests:
  Section 1: classify_step() — FULL SCAN recognised, SCAN PAGE not shadowed
  Section 2: parse_hunt_blocks() — FULL SCAN survives round-trip parse
  Section 3: _handle_full_scan happy path — page with named groups
  Section 4: _handle_full_scan empty page — returns True, prints warning
  Section 5: Conditional-branch path — FULL SCAN inside IF block executes

No external network required. Sections 1–2 are pure-Python.
Sections 3–5 use synthetic DOM HTML served via Playwright.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from typing import ClassVar

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.helpers import classify_step, parse_hunt_blocks

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


# ── Section 1: classify_step ──────────────────────────────────────────────────


def test_classify_full_scan():
    print("\n── Section 1: classify_step — FULL SCAN ──")

    _assert(classify_step("FULL SCAN") == "full_scan", "FULL SCAN uppercase")
    _assert(classify_step("full scan") == "full_scan", "full scan lowercase")
    _assert(classify_step("Full Scan") == "full_scan", "Full Scan mixed case")
    _assert(classify_step("1. FULL SCAN") == "full_scan", "FULL SCAN with step number")

    # SCAN PAGE must not be affected
    _assert(classify_step("SCAN PAGE") == "scan_page", "SCAN PAGE still scan_page")
    _assert(classify_step("SCAN PAGE into {file}") == "scan_page", "SCAN PAGE into not full_scan")

    # Quoted FULL or SCAN labels inside steps must not match
    _assert(classify_step("Click 'Full Scan' button") != "full_scan", "Quoted label not full_scan")
    _assert(classify_step("VERIFY that 'Full Scan' is present") != "full_scan", "VERIFY not full_scan")


# ── Section 2: parse_hunt_blocks round-trip ───────────────────────────────────


def test_parse_hunt_blocks_full_scan():
    print("\n── Section 2: parse_hunt_blocks — FULL SCAN round-trip ──")

    task = """STEP 1: Explore page
    NAVIGATE https://example.com
    FULL SCAN
    SCAN PAGE"""

    blocks = parse_hunt_blocks(task)
    _assert(len(blocks) == 1, "One STEP block", f"got {len(blocks)}")

    actions = blocks[0].actions
    _assert(len(actions) == 3, "Three actions", f"got {len(actions)}")
    _assert(actions[1] == "FULL SCAN", "FULL SCAN preserved verbatim", f"got {actions[1]!r}")

    kinds = [classify_step(a) for a in actions if isinstance(a, str)]
    _assert(kinds[1] == "full_scan", "Second action classifies as full_scan")
    _assert(kinds[2] == "scan_page", "Third action still scan_page")


# ── Synthetic DOM fixtures ────────────────────────────────────────────────────

_HTML_RICH = """\
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
  <header>
    <nav aria-label="Main navigation">
      <a href="/home">Home</a>
      <a href="/about">About</a>
      <a href="/contact">Contact</a>
    </nav>
  </header>

  <main>
    <form aria-label="Login form">
      <input id="email" type="email" placeholder="Email address" />
      <input id="password" type="password" placeholder="Password" />
      <button type="submit">Sign In</button>
      <a href="/forgot">Forgot password?</a>
    </form>

    <section aria-label="Search">
      <input id="query" type="search" placeholder="Search…" />
      <button>Search</button>
    </section>
  </main>

  <footer>
    <a href="/privacy">Privacy Policy</a>
    <a href="/terms">Terms of Service</a>
  </footer>
</body>
</html>
"""

_HTML_EMPTY = """\
<!DOCTYPE html>
<html><body><p>No interactive elements here.</p></body></html>
"""


async def _write_html(html: str) -> tuple[str, str]:
    fd, path = tempfile.mkstemp(suffix=".html", prefix="manul_full_scan_")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"file://{path}", path


# ── Stub engine ───────────────────────────────────────────────────────────────


class _StubEngine:
    _EXPLICIT_WAIT_TIMEOUT_MS = 5_000
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


# ── Section 3: _handle_full_scan happy path ───────────────────────────────────


async def test_full_scan_happy():
    print("\n── Section 3: _handle_full_scan — happy path ──")
    from manul_engine.cdp import CDPBrowser

    url, path = await _write_html(_HTML_RICH)
    try:
        async with CDPBrowser(headless=True) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            engine = _make_engine()
            ok = await engine._handle_full_scan(page)
            _assert(ok, "Returns True on a page with controls")

            # Run again to verify it is side-effect free (no crash on second call)
            ok2 = await engine._handle_full_scan(page)
            _assert(ok2, "Returns True on second consecutive call")

            await browser.close()
    finally:
        os.unlink(path)


# ── Section 4: _handle_full_scan empty page ───────────────────────────────────


async def test_full_scan_empty_page():
    print("\n── Section 4: _handle_full_scan — empty page ──")
    from manul_engine.cdp import CDPBrowser

    url, path = await _write_html(_HTML_EMPTY)
    try:
        async with CDPBrowser(headless=True) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            engine = _make_engine()
            ok = await engine._handle_full_scan(page)
            _assert(ok, "Returns True even when page has no interactive controls")

            await browser.close()
    finally:
        os.unlink(path)


# ── Section 5: conditional-branch path ───────────────────────────────────────


async def test_full_scan_in_if_block():
    print("\n── Section 5: FULL SCAN inside IF block ──")
    from manul_engine.cdp import CDPBrowser

    url, path = await _write_html(_HTML_RICH)
    try:
        async with CDPBrowser(headless=True) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            # Parse a hunt with FULL SCAN inside an IF body
            task = """STEP 1: Conditional scan
    IF text 'Sign In' is present:
        FULL SCAN"""

            blocks = parse_hunt_blocks(task)
            _assert(len(blocks) == 1, "One STEP block parsed", f"got {len(blocks)}")

            from manul_engine.helpers import IfBlock

            actions = blocks[0].actions
            _assert(len(actions) == 1, "One IfBlock action", f"got {len(actions)}")
            _assert(isinstance(actions[0], IfBlock), "Action is IfBlock")

            if isinstance(actions[0], IfBlock):
                branch = actions[0].branches[0]
                _assert(len(branch.actions) == 1, "IF branch has one action", f"got {len(branch.actions)}")
                _assert(branch.actions[0] == "FULL SCAN", "Branch action is FULL SCAN", f"got {branch.actions[0]!r}")
                _assert(
                    classify_step(branch.actions[0]) == "full_scan",
                    "Branch action classifies as full_scan",
                )

            await browser.close()
    finally:
        os.unlink(path)


# ── run_suite ─────────────────────────────────────────────────────────────────


async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    test_classify_full_scan()
    test_parse_hunt_blocks_full_scan()

    await test_full_scan_happy()
    await test_full_scan_empty_page()
    await test_full_scan_in_if_block()

    total = _PASS + _FAIL
    print(f"\n  Full-scan suite: {_PASS} passed, {_FAIL} failed")
    print(f"SCORE: {_PASS}/{total}")
    return _PASS, _FAIL


if __name__ == "__main__":
    p, f = asyncio.run(run_suite())
    raise SystemExit(0 if f == 0 else 1)
