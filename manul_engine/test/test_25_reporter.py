# manul_engine/test/test_25_reporter.py
"""
Unit-test suite for the HTML report generator (reporter.py).

Tests:
  1. generate_report creates a file and returns an absolute path.
  2. HTML structure — contains expected sections, dashboard stats,
     mission names, step text, CSS, JS.
  3. Screenshot embedding — base64 data URI present when screenshot exists.
  4. Error rendering — error messages appear in output.
  5. Status badges — pass/fail/flaky badges rendered correctly.
  6. Edge cases — zero missions, all pass, all fail, special HTML chars escaped.
  7. Duration formatting — ms, seconds, minutes.

No network or live browser required.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.reporting import StepResult, MissionResult, RunSummary
from manul_engine.reporter import generate_report, _fmt_duration, _esc

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


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_summary() -> RunSummary:
    """Build a realistic RunSummary for testing."""
    step_pass = StepResult(index=1, text="NAVIGATE to https://example.com", duration_ms=320)
    step_fail = StepResult(index=2, text="Click 'Login' button", status="fail",
                           duration_ms=5001, error="Timeout waiting for selector",
                           screenshot="iVBORw0KGgoAAAANSUhEUg==")
    step_skip = StepResult(index=3, text="DONE.", status="skip", duration_ms=1)

    m_pass = MissionResult(
        file="/tmp/smoke.hunt", name="smoke.hunt", status="pass",
        duration_ms=1200, steps=[step_pass, StepResult(index=2, text="DONE.")],
        tags=["smoke", "fast"],
    )
    m_fail = MissionResult(
        file="/tmp/login.hunt", name="login.hunt", status="fail",
        duration_ms=8500, error="Step 2 failed",
        steps=[step_pass, step_fail, step_skip],
        tags=["smoke", "login"],
    )
    m_flaky = MissionResult(
        file="/tmp/flaky.hunt", name="flaky.hunt", status="flaky",
        duration_ms=3200, attempts=3,
        steps=[step_pass, StepResult(index=2, text="DONE.")],
        tags=["regression"],
    )

    rs = RunSummary()
    rs.session_id = "session-20250115T103000Z-4242"
    rs.invocation_count = 3
    rs.started_at = "2025-01-15 10:30:00"
    rs.ended_at = "2025-01-15 10:30:13"
    rs.total = 3
    rs.passed = 1
    rs.failed = 1
    rs.flaky = 1
    rs.duration_ms = 12900
    rs.missions = [m_pass, m_fail, m_flaky]
    return rs


# ── Section 1: generate_report file output ────────────────────────────────────

def _test_generate_report_creates_file() -> None:
    print("\n  ── generate_report file output ───────────────────────────")

    summary = _make_summary()
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "sub", "report.html")
        result = generate_report(summary, out_path)

        _assert(os.path.isfile(result), "generate_report creates the file")
        _assert(os.path.isabs(result), "returns absolute path")
        _assert(result.endswith("report.html"), "path ends with report.html")
        _assert(os.path.isdir(os.path.join(tmpdir, "sub")),
                "creates intermediate directories")

        content = open(result, encoding="utf-8").read()
        _assert(content.startswith("<!DOCTYPE html>"), "file starts with DOCTYPE")
        _assert(len(content) > 500, "file has substantial content",
                f"len={len(content)}")


# ── Section 2: HTML structure ─────────────────────────────────────────────────

def _test_html_structure() -> None:
    print("\n  ── HTML structure ────────────────────────────────────────")

    summary = _make_summary()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        generate_report(summary, out)
        html_content = open(out, encoding="utf-8").read()

    _assert("<title>ManulEngine Test Report</title>" in html_content,
            "contains <title>")
    _assert("<style>" in html_content, "contains inline <style>")
    _assert("<script>" in html_content, "contains inline <script>")
    _assert("ManulEngine Test Report" in html_content, "heading present")
    _assert("Run Session" in html_content, "run session banner present")
    _assert("session-20250115T103000Z-4242" in html_content, "session id rendered")
    _assert("Merged invocations: 3" in html_content, "invocation count rendered")

    # Dashboard stats
    _assert(">3</div>" in html_content or ">3<" in html_content,
            "dashboard shows total=3")
    _assert("33%" in html_content or "33" in html_content,
            "pass rate shown")

    # Mission names
    _assert("smoke.hunt" in html_content, "smoke.hunt mission name present")
    _assert("login.hunt" in html_content, "login.hunt mission name present")
    _assert("flaky.hunt" in html_content, "flaky.hunt mission name present")

    # Step text
    _assert("NAVIGATE to https://example.com" in html_content,
            "step text preserved in output")
    _assert("Click &#x27;Login&#x27; button" in html_content
            or "Click 'Login' button" in html_content,
            "step with quotes present (may be escaped)")


# ── Section 3: Screenshot embedding ──────────────────────────────────────────

def _test_screenshot_embedding() -> None:
    print("\n  ── Screenshot embedding ──────────────────────────────────")

    summary = _make_summary()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        generate_report(summary, out)
        html_content = open(out, encoding="utf-8").read()

    _assert("data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==" in html_content,
            "base64 screenshot embedded as data URI")
    _assert('alt="Screenshot step 2"' in html_content,
            "screenshot has alt text with step index")
    _assert("step-screenshot" in html_content,
            "screenshot wrapper class present")


# ── Section 4: Error rendering ────────────────────────────────────────────────

def _test_error_rendering() -> None:
    print("\n  ── Error rendering ───────────────────────────────────────")

    summary = _make_summary()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        generate_report(summary, out)
        html_content = open(out, encoding="utf-8").read()

    _assert("Timeout waiting for selector" in html_content,
            "step-level error message rendered")
    _assert("step-error" in html_content,
            "step-error CSS class used")


# ── Section 5: Status badges ─────────────────────────────────────────────────

def _test_status_badges() -> None:
    print("\n  ── Status badges ─────────────────────────────────────────")

    summary = _make_summary()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        generate_report(summary, out)
        html_content = open(out, encoding="utf-8").read()

    _assert("badge-pass" in html_content, "pass badge class present")
    _assert("badge-fail" in html_content, "fail badge class present")
    _assert("badge-flaky" in html_content, "flaky badge class present")
    _assert("3 attempts" in html_content, "flaky mission shows attempt count")
    _assert("passed on retry" in html_content,
            "flaky mission shows retry note")


# ── Section 6: Edge cases ────────────────────────────────────────────────────

def _test_edge_cases() -> None:
    print("\n  ── Edge cases ────────────────────────────────────────────")

    # Empty summary (zero missions)
    rs_empty = RunSummary()
    rs_empty.started_at = "2025-01-01 00:00:00"
    rs_empty.ended_at = "2025-01-01 00:00:00"
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "empty.html")
        result = generate_report(rs_empty, out)
        content = open(result, encoding="utf-8").read()
        _assert("<!DOCTYPE html>" in content, "empty summary still produces valid HTML")
        _assert("0%" in content or ">0</div>" in content,
                "empty summary shows zero stats")

    # Special HTML characters in mission name and step text
    m_xss = MissionResult(
        file="test.hunt", name='<script>alert("xss")</script>.hunt',
        status="pass", steps=[
            StepResult(index=1, text='Fill "Name & <Address>" field')
        ]
    )
    rs_xss = RunSummary()
    rs_xss.total = 1
    rs_xss.passed = 1
    rs_xss.missions = [m_xss]
    rs_xss.started_at = "2025-01-01"
    rs_xss.ended_at = "2025-01-01"
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "xss.html")
        generate_report(rs_xss, out)
        content = open(out, encoding="utf-8").read()
        _assert('<script>alert("xss")</script>' not in content,
                "script tag is escaped (XSS protection)")
        _assert("&lt;script&gt;" in content,
                "script tag rendered as escaped entity")
        _assert("&amp;" in content,
                "ampersand is escaped")


# ── Section 7: Duration formatting ───────────────────────────────────────────

def _test_duration_formatting() -> None:
    print("\n  ── Duration formatting ───────────────────────────────────")

    _assert(_fmt_duration(50) == "50ms", "50ms formatted",
            f"got={_fmt_duration(50)!r}")
    _assert(_fmt_duration(999) == "999ms", "999ms formatted",
            f"got={_fmt_duration(999)!r}")
    _assert(_fmt_duration(1000) == "1.0s", "1000ms → 1.0s",
            f"got={_fmt_duration(1000)!r}")
    _assert(_fmt_duration(5500) == "5.5s", "5500ms → 5.5s",
            f"got={_fmt_duration(5500)!r}")
    _assert(_fmt_duration(65000) == "1m 5s", "65000ms → 1m 5s",
            f"got={_fmt_duration(65000)!r}")
    _assert(_fmt_duration(0) == "0ms", "0ms edge case",
            f"got={_fmt_duration(0)!r}")


# ── Section 8: _esc helper ───────────────────────────────────────────────────

def _test_esc_helper() -> None:
    print("\n  ── _esc helper ───────────────────────────────────────────")

    _assert(_esc(None) == "", "_esc(None) returns empty string")
    _assert(_esc("") == "", "_esc('') returns empty string")
    _assert(_esc("hello") == "hello", "_esc plain text unchanged")
    _assert("&lt;" in _esc("<b>bold</b>"), "_esc escapes angle brackets")


# ── Section 9: Control panel — Show Only Failed toggle ────────────────────────

def _test_control_panel_failed_toggle() -> None:
    print("\n  ── Control panel: Show Only Failed toggle ────────────────")

    summary = _make_summary()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        generate_report(summary, out)
        content = open(out, encoding="utf-8").read()

    _assert("control-panel" in content, "control-panel class present")
    _assert('id="filter-failed"' in content, "filter-failed checkbox present")
    _assert("Show only failed" in content, "toggle label text present")
    _assert("applyFilters" in content, "JS applyFilters function present")
    _assert('data-status="pass"' in content, "mission has data-status=pass attr")
    _assert('data-status="fail"' in content, "mission has data-status=fail attr")
    _assert('data-status="flaky"' in content, "mission has data-status=flaky attr")


# ── Section 10: Control panel — Tag filtering ────────────────────────────────

def _test_control_panel_tag_filtering() -> None:
    print("\n  ── Control panel: Tag filtering ──────────────────────────")

    summary = _make_summary()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        generate_report(summary, out)
        content = open(out, encoding="utf-8").read()

    # Tags from fixture: smoke, fast, login, regression
    _assert("tag-chip" in content, "tag-chip class present in HTML")
    _assert('data-tag="smoke"' in content, "smoke tag chip rendered")
    _assert('data-tag="fast"' in content, "fast tag chip rendered")
    _assert('data-tag="login"' in content, "login tag chip rendered")
    _assert('data-tag="regression"' in content, "regression tag chip rendered")
    _assert("tag-divider" in content, "tag divider between checkbox and chips")

    # data-tags attribute on missions
    _assert('data-tags="smoke,fast"' in content, "smoke.hunt has correct data-tags")
    _assert('data-tags="smoke,login"' in content, "login.hunt has correct data-tags")
    _assert('data-tags="regression"' in content, "flaky.hunt has correct data-tags")

    # JS handles tag clicks
    _assert("activeTag" in content, "JS activeTag variable exists")
    _assert("tag-chip" in content, "JS references tag-chip class")


# ── Section 11: No tags — graceful fallback ──────────────────────────────────

def _test_no_tags_graceful() -> None:
    print("\n  ── No tags: graceful fallback ────────────────────────────")

    m = MissionResult(
        file="/tmp/bare.hunt", name="bare.hunt", status="pass",
        steps=[StepResult(index=1, text="DONE.")]
    )
    rs = RunSummary()
    rs.total = 1
    rs.passed = 1
    rs.started_at = "2025-01-01"
    rs.ended_at = "2025-01-01"
    rs.missions = [m]

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.html")
        generate_report(rs, out)
        content = open(out, encoding="utf-8").read()

    _assert("control-panel" in content, "control panel still rendered without tags")
    _assert('id="filter-failed"' in content, "failed toggle present without tags")
    _assert('data-tag=' not in content, "no tag chip elements when missions have no tags")
    _assert('<span class="tag-divider">' not in content,
            "no tag divider element when no tags exist")
    _assert('data-tags=""' in content, "data-tags is empty string when no tags")


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n" + "━" * 56)
    print("  test_25_reporter — HTML report generator")
    print("━" * 56)

    _test_generate_report_creates_file()
    _test_html_structure()
    _test_screenshot_embedding()
    _test_error_rendering()
    _test_status_badges()
    _test_edge_cases()
    _test_duration_formatting()
    _test_esc_helper()
    _test_control_panel_failed_toggle()
    _test_control_panel_tag_filtering()
    _test_no_tags_graceful()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    return _FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(run_suite())
    sys.exit(0 if ok else 1)
