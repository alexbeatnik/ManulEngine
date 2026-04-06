# manul_engine/test/test_37_enterprise_dsl.py
"""
Unit-test suite for v0.0.9.1 Enterprise DSL features:
  A. Data-Driven Testing (@data:)
  B. Network Interception (MOCK / WAIT FOR RESPONSE)
  C. Visual Regression (VERIFY VISUAL)
  D. Soft Assertions (VERIFY SOFTLY)

No network, no live browser, no Ollama required.
All tests run against synthetic data, in-memory state, and parsed ``.hunt`` files (no Playwright).

Entry point ``run_suite()`` is picked up by the dev test runner
(``python run_tests.py``) and must remain async.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.helpers import classify_step, parse_verify_strict_assertion
from manul_engine.reporting import StepResult, MissionResult, RunSummary
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
# Section A: classify_step — new step kind detection
# ═══════════════════════════════════════════════════════════════════════════════

def _test_classify_new_step_kinds() -> None:
    print("\n  ── classify_step: new DSL keywords ───────────────────────")

    # MOCK variants
    _assert(classify_step('MOCK GET "/api/users" with \'mocks/users.json\'') == "mock",
            "MOCK GET classified as 'mock'")
    _assert(classify_step('MOCK POST "/api/login" with \'mocks/login.json\'') == "mock",
            "MOCK POST classified as 'mock'")
    _assert(classify_step('MOCK PUT "/api/data" with \'mocks/data.json\'') == "mock",
            "MOCK PUT classified as 'mock'")
    _assert(classify_step('MOCK PATCH "/api/data" with \'mocks/patch.json\'') == "mock",
            "MOCK PATCH classified as 'mock'")
    _assert(classify_step('MOCK DELETE "/api/items" with \'mocks/del.json\'') == "mock",
            "MOCK DELETE classified as 'mock'")
    _assert(classify_step('1. MOCK GET "/api/test" with \'data.json\'') == "mock",
            "Numbered MOCK classified as 'mock'")

    # WAIT FOR RESPONSE
    _assert(classify_step('WAIT FOR RESPONSE "/api/users"') == "wait_for_response",
            "WAIT FOR RESPONSE classified correctly")
    _assert(classify_step('1. WAIT FOR RESPONSE "/api/data"') == "wait_for_response",
            "Numbered WAIT FOR RESPONSE classified correctly")
    _assert(classify_step('Wait for "Welcome, User" to be visible') == "wait_for_element",
            "Explicit wait visible classified correctly")
    _assert(classify_step("Wait for 'Loading...' to disappear") == "wait_for_element",
            "Explicit wait disappear classified correctly")
    _assert(classify_step('Wait for "Submit" to be hidden') == "wait_for_element",
            "Explicit wait hidden classified correctly")
    # Plain WAIT should still work
    _assert(classify_step("WAIT 3") == "wait",
            "Plain WAIT still classified as 'wait'")

    # VERIFY VISUAL
    _assert(classify_step("VERIFY VISUAL 'Login Button'") == "verify_visual",
            "VERIFY VISUAL classified as 'verify_visual'")
    _assert(classify_step('1. VERIFY VISUAL "Header Logo"') == "verify_visual",
            "Numbered VERIFY VISUAL classified correctly")

    # VERIFY SOFTLY
    _assert(classify_step("VERIFY SOFTLY that 'Welcome' is present") == "verify_softly",
            "VERIFY SOFTLY classified as 'verify_softly'")
    _assert(classify_step("VERIFY SOFTLY that 'Error' is NOT present") == "verify_softly",
            "Negative VERIFY SOFTLY classified correctly")
    _assert(classify_step("1. VERIFY SOFTLY that 'OK' is present") == "verify_softly",
            "Numbered VERIFY SOFTLY classified correctly")

    # Regular VERIFY should still work
    _assert(classify_step("VERIFY that 'Welcome' is present") == "verify",
            "Plain VERIFY still classified as 'verify'")
    _assert(classify_step("Verify 'Save' button has text 'Save me'") == "verify",
            "Strict VERIFY text classified as 'verify'")
    _assert(classify_step('Verify "Login" field has placeholder "Login/Email"') == "verify",
            "Strict VERIFY placeholder classified as 'verify'")
    _assert(classify_step('Verify "Email" field has value "captain@manul.com"') == "verify",
            "Strict VERIFY value classified as 'verify'")

    # Keywords inside quotes should NOT trigger
    _assert(classify_step("Click 'MOCK Button'") == "action",
            "MOCK inside quotes classified as 'action'")
    _assert(classify_step("Click 'VERIFY VISUAL Now'") == "action",
            "VERIFY VISUAL inside quotes classified as 'action'")


def _test_parse_strict_verify_assertions() -> None:
    print("\n  ── parse_verify_strict_assertion: strict VERIFY forms ─────────")

    parsed_text = parse_verify_strict_assertion('Verify "save" button has text "Save me"')
    _assert(parsed_text is not None, "Strict text assertion parsed")
    _assert(parsed_text is not None and parsed_text.kind == "text", "Strict text kind detected")
    _assert(parsed_text is not None and parsed_text.target == "save", "Strict text target captured")
    _assert(parsed_text is not None and parsed_text.element_type == "button", "Strict text element type captured")
    _assert(parsed_text is not None and parsed_text.expected == "Save me", "Strict text expected value captured")

    parsed_placeholder = parse_verify_strict_assertion("Verify 'Login' field has placeholder \"Login/Email\"")
    _assert(parsed_placeholder is not None, "Strict placeholder assertion parsed")
    _assert(parsed_placeholder is not None and parsed_placeholder.kind == "placeholder", "Strict placeholder kind detected")
    _assert(parsed_placeholder is not None and parsed_placeholder.target == "Login", "Strict placeholder target captured")
    _assert(parsed_placeholder is not None and parsed_placeholder.element_type == "field", "Strict placeholder element type captured")
    _assert(parsed_placeholder is not None and parsed_placeholder.expected == "Login/Email", "Strict placeholder expected value captured")

    parsed_value = parse_verify_strict_assertion('Verify "Email" field has value "captain@manul.com"')
    _assert(parsed_value is not None, "Strict value assertion parsed")
    _assert(parsed_value is not None and parsed_value.kind == "value", "Strict value kind detected")
    _assert(parsed_value is not None and parsed_value.target == "Email", "Strict value target captured")
    _assert(parsed_value is not None and parsed_value.element_type == "field", "Strict value element type captured")
    _assert(parsed_value is not None and parsed_value.expected == "captain@manul.com", "Strict value expected value captured")

    _assert(parse_verify_strict_assertion("VERIFY that 'Welcome' is present") is None,
            "Legacy VERIFY does not parse as strict assertion")


# ═══════════════════════════════════════════════════════════════════════════════
# Section B: Data-Driven Testing — @data: parsing
# ═══════════════════════════════════════════════════════════════════════════════

def _test_data_driven_parsing() -> None:
    print("\n  ── @data: header parsing ─────────────────────────────────")

    # Test @data: in hunt file header
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False, encoding="utf-8") as f:
        f.write("@context: Test data-driven\n")
        f.write("@title: DDT Test\n")
        f.write("@data: test_data.json\n")
        f.write("@var: {base_url} = https://example.com\n")
        f.write("\n")
        f.write("STEP 1: Login\n")
        f.write("NAVIGATE to https://example.com\n")
        f.write("Fill 'Email' with '{email}'\n")
        f.write("DONE.\n")
        tmp_path = f.name

    try:
        hunt = parse_hunt_file(tmp_path)
        _assert(hunt.data_file == "test_data.json",
                "@data: parsed correctly", f"got '{hunt.data_file}'")
        _assert(hunt.context == "Test data-driven",
                "@context: still works with @data:")
        _assert(hunt.title == "DDT Test",
                "@title: still works with @data:")
        _assert("base_url" in hunt.parsed_vars,
                "@var: still works with @data:")
        _assert("NAVIGATE" in hunt.mission,
                "Mission content preserved with @data:")
        _assert("@data:" not in hunt.mission,
                "@data: header not included in mission text")
    finally:
        os.unlink(tmp_path)

    # Test without @data: — backward compatibility
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False, encoding="utf-8") as f:
        f.write("@context: No data\n")
        f.write("NAVIGATE to https://example.com\n")
        f.write("DONE.\n")
        tmp_path = f.name

    try:
        hunt = parse_hunt_file(tmp_path)
        _assert(hunt.data_file == "",
                "No @data: returns empty string", f"got '{hunt.data_file}'")
    finally:
        os.unlink(tmp_path)

    # Test @data: with CSV
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False, encoding="utf-8") as f:
        f.write("@data: users.csv\n")
        f.write("Fill 'Name' with '{name}'\n")
        tmp_path = f.name

    try:
        hunt = parse_hunt_file(tmp_path)
        _assert(hunt.data_file == "users.csv",
                "@data: CSV file parsed correctly")
    finally:
        os.unlink(tmp_path)


def _test_load_data_file() -> None:
    print("\n  ── _load_data_file: JSON and CSV loading ─────────────────")
    from manul_engine.cli import _load_data_file

    # Test JSON loading
    with tempfile.TemporaryDirectory() as tmpdir:
        data = [
            {"email": "user1@test.com", "password": "pass1"},
            {"email": "user2@test.com", "password": "pass2"},
            {"email": "user3@test.com", "password": "pass3"},
        ]
        json_path = os.path.join(tmpdir, "data.json")
        with open(json_path, "w") as f:
            json.dump(data, f)

        rows = _load_data_file("data.json", tmpdir)
        _assert(len(rows) == 3, "JSON: loaded 3 rows", f"got {len(rows)}")
        _assert(rows[0]["email"] == "user1@test.com", "JSON: first row email correct")
        _assert(rows[2]["password"] == "pass3", "JSON: third row password correct")

    # Test CSV loading
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "users.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "age", "city"])
            writer.writeheader()
            writer.writerow({"name": "Alice", "age": "30", "city": "NYC"})
            writer.writerow({"name": "Bob", "age": "25", "city": "LA"})

        rows = _load_data_file("users.csv", tmpdir)
        _assert(len(rows) == 2, "CSV: loaded 2 rows", f"got {len(rows)}")
        _assert(rows[0]["name"] == "Alice", "CSV: first row name correct")
        _assert(rows[1]["city"] == "LA", "CSV: second row city correct")

    # Test missing file
    rows = _load_data_file("nonexistent.json", tempfile.gettempdir())
    _assert(rows == [], "Missing file returns empty list")

    # Test unsupported extension
    with tempfile.TemporaryDirectory() as tmpdir:
        xml_path = os.path.join(tmpdir, "data.xml")
        with open(xml_path, "w") as f:
            f.write("<data/>")
        rows = _load_data_file("data.xml", tmpdir)
        _assert(rows == [], "Unsupported extension returns empty list")

    # Test empty JSON array
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "empty.json")
        with open(json_path, "w") as f:
            json.dump([], f)
        rows = _load_data_file("empty.json", tmpdir)
        _assert(rows == [], "Empty JSON array returns empty list")


# ═══════════════════════════════════════════════════════════════════════════════
# Section C: Reporting — warning status
# ═══════════════════════════════════════════════════════════════════════════════

def _test_reporting_warning() -> None:
    print("\n  ── Reporting: warning status & soft_errors ────────────────")

    # StepResult with warning status
    sr = StepResult(index=1, text="VERIFY SOFTLY that 'X' is present", status="warning",
                    error="Soft assertion failed")
    _assert(sr.status == "warning", "StepResult can have 'warning' status")
    _assert(sr.error == "Soft assertion failed", "StepResult.error set for warning")

    # MissionResult with warning status
    mr = MissionResult(file="/tmp/test.hunt", name="test.hunt", status="warning")
    _assert(mr.status == "warning", "MissionResult can have 'warning' status")
    _assert(bool(mr) is True, "MissionResult(status='warning') is truthy (not failed)")

    # MissionResult soft_errors list
    mr2 = MissionResult(file="/tmp/t.hunt", name="t.hunt", status="warning",
                        soft_errors=["Err 1", "Err 2"])
    _assert(len(mr2.soft_errors) == 2, "MissionResult.soft_errors stores list")
    _assert(mr2.soft_errors[0] == "Err 1", "MissionResult.soft_errors[0] correct")

    # MissionResult soft_errors default
    mr3 = MissionResult(file="/tmp/t2.hunt", name="t2.hunt")
    _assert(mr3.soft_errors == [], "MissionResult.soft_errors defaults to empty list")

    # soft_errors list independence (mutable default safety)
    mr_a = MissionResult(file="a", name="a")
    mr_b = MissionResult(file="b", name="b")
    mr_a.soft_errors.append("err")
    _assert(len(mr_b.soft_errors) == 0,
            "MissionResult soft_errors lists are independent")

    # RunSummary with warning count
    rs = RunSummary(total=5, passed=2, failed=1, flaky=1, warning=1)
    _assert(rs.warning == 1, "RunSummary.warning field works")
    _assert(rs.total == 5, "RunSummary.total still works with warning")

    # RunSummary warning default
    rs2 = RunSummary()
    _assert(rs2.warning == 0, "RunSummary.warning defaults to 0")


# ═══════════════════════════════════════════════════════════════════════════════
# Section D: Reporter — HTML output with warning
# ═══════════════════════════════════════════════════════════════════════════════

def _test_reporter_warning_html() -> None:
    print("\n  ── Reporter: warning/soft-errors in HTML output ──────────")
    from manul_engine.reporter import generate_report

    with tempfile.TemporaryDirectory() as tmpdir:
        summary = RunSummary(
            started_at="2026-03-14T10:00:00",
            ended_at="2026-03-14T10:01:00",
            total=3,
            passed=1,
            failed=1,
            flaky=0,
            warning=1,
            duration_ms=60000,
            missions=[
                MissionResult(
                    file="/tmp/pass.hunt", name="pass.hunt", status="pass",
                    duration_ms=10000,
                    steps=[StepResult(index=1, text="NAVIGATE to https://x.com", status="pass")],
                ),
                MissionResult(
                    file="/tmp/warn.hunt", name="warn.hunt", status="warning",
                    duration_ms=20000,
                    soft_errors=["Soft fail: 'X' not found", "Soft fail: 'Y' not found"],
                    tags=["smoke"],
                    steps=[
                        StepResult(index=1, text="NAVIGATE to https://y.com", status="pass"),
                        StepResult(index=2, text="VERIFY SOFTLY that 'X' is present",
                                   status="warning", error="Soft fail: 'X' not found"),
                        StepResult(index=3, text="Click 'Submit'", status="pass"),
                    ],
                ),
                MissionResult(
                    file="/tmp/fail.hunt", name="fail.hunt", status="fail",
                    duration_ms=30000, error="Element not found",
                    steps=[StepResult(index=1, text="Click 'Missing'", status="fail",
                                      error="Element not found")],
                ),
            ],
        )

        report_path = os.path.join(tmpdir, "test_report.html")
        abs_path = generate_report(summary, report_path)
        _assert(os.path.exists(abs_path), "Report file generated")

        with open(abs_path, "r", encoding="utf-8") as f:
            html = f.read()

        _assert("badge-warning" in html, "Warning badge class present in HTML")
        _assert('data-status="warning"' in html, "Warning data-status attribute present")
        _assert("soft-errors" in html, "Soft errors block present in HTML")
        _assert("Soft Assertion Warnings" in html, "Soft errors title present")
        _assert("Soft fail: &#x27;X&#x27; not found" in html or "Soft fail:" in html,
                "Soft error message rendered in HTML")
        _assert("status-warning" in html, "Warning status CSS class on step")
        _assert("step-warning" in html, "Warning step row CSS class present")
        _assert("filter-warnings" in html, "Show Warnings checkbox present")
        _assert("Warning" in html, "Warning stat card label present")


# ═══════════════════════════════════════════════════════════════════════════════
# Section E: MOCK step classification edge cases
# ═══════════════════════════════════════════════════════════════════════════════

def _test_mock_edge_cases() -> None:
    print("\n  ── MOCK/WAIT FOR RESPONSE edge cases ─────────────────────")

    # MOCK must have a valid HTTP method
    _assert(classify_step('MOCK "/api/test" with \'data.json\'') != "mock",
            "MOCK without method is NOT classified as 'mock'")

    # WAIT FOR RESPONSE vs WAIT
    _assert(classify_step("WAIT FOR RESPONSE '/api/data'") == "wait_for_response",
            "WAIT FOR RESPONSE with single quotes classified correctly")
    _assert(classify_step('WAIT 5') == "wait",
            "Plain WAIT 5 is NOT classified as wait_for_response")

    # VERIFY ordering: VERIFY VISUAL before VERIFY
    _assert(classify_step("VERIFY VISUAL 'Logo'") == "verify_visual",
            "VERIFY VISUAL wins over plain VERIFY")
    _assert(classify_step("VERIFY SOFTLY that 'X' is present") == "verify_softly",
            "VERIFY SOFTLY wins over plain VERIFY")

    # Combined: system step detection includes new keywords
    from manul_engine.helpers import RE_SYSTEM_STEP
    _assert(bool(RE_SYSTEM_STEP.search("MOCK GET '/api' with 'f.json'")),
            "RE_SYSTEM_STEP matches MOCK GET")
    _assert(bool(RE_SYSTEM_STEP.search("WAIT FOR RESPONSE '/api/data'")),
            "RE_SYSTEM_STEP matches WAIT FOR RESPONSE")
    _assert(bool(RE_SYSTEM_STEP.search('Wait for "Submit" to be hidden')),
            "RE_SYSTEM_STEP matches explicit wait")
    _assert(bool(RE_SYSTEM_STEP.search("VERIFY VISUAL 'Logo'")),
            "RE_SYSTEM_STEP matches VERIFY VISUAL (via VERIFY)")
    _assert(bool(RE_SYSTEM_STEP.search("VERIFY SOFTLY that 'X'")),
            "RE_SYSTEM_STEP matches VERIFY SOFTLY (via VERIFY)")


# ═══════════════════════════════════════════════════════════════════════════════
# Section F: ParsedHunt backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

def _test_parsed_hunt_compat() -> None:
    print("\n  ── ParsedHunt backward compatibility ─────────────────────")
    from manul_engine.cli import ParsedHunt

    # 12-field NamedTuple (exports/imports added in import feature)
    _assert(len(ParsedHunt._fields) == 12,
            "ParsedHunt has 12 fields", f"got {len(ParsedHunt._fields)}")
    _assert("data_file" in ParsedHunt._fields,
            "ParsedHunt has 'data_file' field")
    _assert("schedule" in ParsedHunt._fields,
            "ParsedHunt has 'schedule' field")
    _assert("exports" in ParsedHunt._fields,
            "ParsedHunt has 'exports' field")
    _assert("imports" in ParsedHunt._fields,
            "ParsedHunt has 'imports' field")

    # Can still be unpacked positionally
    h = ParsedHunt(
        mission="test", context="ctx", title="t",
        step_file_lines=[1], setup_lines=[], teardown_lines=[],
        parsed_vars={}, tags=[], data_file="data.json", schedule="",
        exports=[], imports=[],
    )
    _assert(h[8] == "data.json", "ParsedHunt[8] is data_file")
    _assert(h.data_file == "data.json", "ParsedHunt.data_file attribute access works")
    _assert(h[9] == "", "ParsedHunt[9] is schedule")
    _assert(h.schedule == "", "ParsedHunt.schedule attribute access works")
    _assert(h[10] == [], "ParsedHunt[10] is exports")
    _assert(h.exports == [], "ParsedHunt.exports attribute access works")
    _assert(h[11] == [], "ParsedHunt[11] is imports")
    _assert(h.imports == [], "ParsedHunt.imports attribute access works")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

async def run_suite() -> tuple[int, int]:
        """Run all test sections and return (passed, failed)."""
        global _PASS, _FAIL
        _PASS = _FAIL = 0

        print("\n" + "=" * 60)
        print("  TEST 37 — Enterprise DSL Features (v0.0.9.1)")
        print("=" * 60)

        # A: classify_step for new keywords
        _test_classify_new_step_kinds()
        _test_parse_strict_verify_assertions()

        # B: Data-Driven Testing
        _test_data_driven_parsing()
        _test_load_data_file()

        # C: Reporting with warning
        _test_reporting_warning()

        # D: Reporter HTML with warning
        _test_reporter_warning_html()

        # E: Edge cases
        _test_mock_edge_cases()

        # F: ParsedHunt compatibility
        _test_parsed_hunt_compat()

        total = _PASS + _FAIL
        print(f"\n  {'='*50}")
        print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
        print(f"  {'='*50}")
        print(f"  \U0001f4ca SCORE: {_PASS}/{total}")
        return _PASS, _FAIL
