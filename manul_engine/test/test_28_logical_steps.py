# manul_engine/test/test_28_logical_steps.py
"""
Unit-test suite for the STEP logical-grouping feature.

Tests:
  1. Parser — classify_step() correctly identifies "logical_step" kind.
  2. Parser — parse_logical_step() extracts number and description.
  3. Parser — STEP marker does not shadow regular keywords inside quoted labels.
  4. Reporting — StepResult carries the logical_step field.
  5. Reporter — _group_steps() partitions correctly with/without STEP markers.
  6. Reporter — _render_lstep_group() produces expected HTML structure.
  7. Reporter — generate_report() renders grouped sections when STEP markers exist.
  8. Reporter — flat rendering preserved when no STEP markers used.

No network or live browser required.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.helpers import classify_step, parse_logical_step, parse_hunt_blocks
from manul_engine.reporting import StepResult, MissionResult, RunSummary
from manul_engine.reporter import generate_report, _group_steps, _render_lstep_group

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


# ── Section 1: classify_step ──────────────────────────────────────────────────


def _test_classify_step() -> None:
    print("\n  ── classify_step — STEP recognition ──────────────────────")

    _assert(
        classify_step("1. STEP 1: Navigate to the login page") == "logical_step",
        "classify_step: numbered STEP with number",
    )
    _assert(
        classify_step("2. STEP: Fill in credentials") == "logical_step", "classify_step: numbered STEP without number"
    )
    _assert(classify_step("STEP 3: Verify checkout") == "logical_step", "classify_step: STEP without leading index")
    _assert(classify_step("step: lowercase accepted") == "logical_step", "classify_step: lowercase 'step:' accepted")
    _assert(
        classify_step("STEP  42 :  Trailing spaces") == "logical_step",
        "classify_step: extra whitespace around number and colon",
    )

    # Must NOT be classified as logical_step
    _assert(
        classify_step("1. NAVIGATE to https://example.com") == "navigate", "classify_step: NAVIGATE is not logical_step"
    )
    _assert(
        classify_step("1. Click 'Next Step' button") == "action",
        "classify_step: 'Next Step' inside a label is not logical_step",
    )
    _assert(
        classify_step("1. VERIFY that 'STEP completed' is present") == "verify",
        "classify_step: STEP inside a quoted verify target is not logical_step",
    )


# ── Section 2: parse_logical_step ────────────────────────────────────────────


def _test_parse_logical_step() -> None:
    print("\n  ── parse_logical_step — description extraction ────────────")

    num, desc = parse_logical_step("1. STEP 2: Navigate to the login page")
    _assert(num == "2", "parse_logical_step: number extracted from 'STEP 2:'")
    _assert(desc == "Navigate to the login page", "parse_logical_step: description extracted")

    num2, desc2 = parse_logical_step("3. STEP: Fill in valid credentials")
    _assert(num2 is None, "parse_logical_step: number is None when absent")
    _assert(desc2 == "Fill in valid credentials", "parse_logical_step: description without number")

    num3, desc3 = parse_logical_step("STEP 10:   Whitespace trimmed   ")
    _assert(num3 == "10", "parse_logical_step: leading/trailing whitespace trimmed")
    _assert(desc3 == "Whitespace trimmed", "parse_logical_step: description trimmed")

    num4, desc4 = parse_logical_step("1. Click the 'Login' button")
    _assert(num4 is None and desc4 is None, "parse_logical_step: returns (None, None) for non-STEP steps")


# ── Section 3: quoted-label isolation ────────────────────────────────────────


def _test_quoted_isolation() -> None:
    print("\n  ── STEP keyword inside quoted label is ignored ────────────")

    # 'STEP' appearing inside a quoted value should NOT trigger logical_step.
    # classify_step strips quotes before pattern matching.
    _assert(
        classify_step("1. VERIFY that 'STEP 1: done' is present") == "verify",
        "STEP inside quoted VERIFY target stays 'verify'",
    )
    _assert(classify_step("1. Click 'STEP button'") == "action", "STEP inside a quoted click target stays 'action'")


# ── Section 4: parse_hunt_blocks ─────────────────────────────────────────────


def _test_parse_hunt_blocks() -> None:
    print("\n  ── parse_hunt_blocks — hierarchy extraction ───────────────")

    blocks = parse_hunt_blocks(
        "STEP 1: Login\n"
        "    NAVIGATE to https://example.com\n"
        "    Fill 'Username' with 'admin'\n"
        "STEP 2: Verify\n"
        "    VERIFY that 'Dashboard' is present\n"
        "    DONE.\n",
        [10, 11, 12, 20, 21, 22],
    )

    _assert(len(blocks) == 2, "parse_hunt_blocks: two STEP blocks parsed")
    _assert(blocks[0].block_name == "STEP 1: Login", "parse_hunt_blocks: first block name canonicalized")
    _assert(
        blocks[0].actions
        == [
            "NAVIGATE to https://example.com",
            "Fill 'Username' with 'admin'",
        ],
        "parse_hunt_blocks: first block actions preserved",
    )
    _assert(blocks[0].block_line == 10, "parse_hunt_blocks: first block line recorded")
    _assert(blocks[0].action_lines == [11, 12], "parse_hunt_blocks: first block action lines recorded")
    _assert(blocks[1].block_name == "STEP 2: Verify", "parse_hunt_blocks: second block name canonicalized")
    _assert(blocks[1].action_lines == [21, 22], "parse_hunt_blocks: second block action lines recorded")

    default_blocks = parse_hunt_blocks(
        "NAVIGATE to https://example.com\nDONE.",
        [1, 2],
    )
    _assert(len(default_blocks) == 1, "parse_hunt_blocks: legacy mission grouped into one synthetic block")
    _assert(default_blocks[0].block_name == "STEP: Default", "parse_hunt_blocks: synthetic block gets default label")
    _assert(default_blocks[0].synthetic is True, "parse_hunt_blocks: synthetic flag set")


# ── Section 5: StepResult.logical_step field ─────────────────────────────────


def _test_step_result_field() -> None:
    print("\n  ── StepResult carries logical_step field ─────────────────")

    sr_default = StepResult(index=1, text="NAVIGATE to https://example.com")
    _assert(sr_default.logical_step is None, "StepResult.logical_step defaults to None")

    sr_tagged = StepResult(index=2, text="Click 'Login'", logical_step="Login Flow")
    _assert(sr_tagged.logical_step == "Login Flow", "StepResult.logical_step stores the label")

    sr_fail = StepResult(
        index=3, text="VERIFY that 'Dashboard' is present", status="fail", logical_step="Post-Login Check"
    )
    _assert(sr_fail.logical_step == "Post-Login Check", "StepResult.logical_step preserved on failure")


# ── Section 5: _group_steps partitioning ─────────────────────────────────────


def _test_group_steps() -> None:
    print("\n  ── _group_steps — partitioning logic ─────────────────────")

    # No STEP markers → single group with label None
    flat_steps = [
        StepResult(index=1, text="NAVIGATE to https://example.com"),
        StepResult(index=2, text="Click 'Login'"),
    ]
    groups = _group_steps(flat_steps)
    _assert(len(groups) == 1, "_group_steps: single group when no STEP markers")
    _assert(groups[0][0] is None, "_group_steps: flat group label is None")
    _assert(len(groups[0][1]) == 2, "_group_steps: flat group contains all steps")

    # Two STEP markers
    grouped_steps = [
        StepResult(index=1, text="NAVIGATE to https://example.com", logical_step="Navigate"),
        StepResult(index=2, text="VERIFY that page is loaded", logical_step="Navigate"),
        StepResult(index=3, text="Fill 'Username'", logical_step="Login"),
        StepResult(index=4, text="Click 'Submit'", logical_step="Login"),
    ]
    groups2 = _group_steps(grouped_steps)
    _assert(len(groups2) == 2, "_group_steps: two distinct STEP groups")
    _assert(groups2[0][0] == "Navigate", "_group_steps: first group label is 'Navigate'")
    _assert(len(groups2[0][1]) == 2, "_group_steps: first group has 2 steps")
    _assert(groups2[1][0] == "Login", "_group_steps: second group label is 'Login'")
    _assert(len(groups2[1][1]) == 2, "_group_steps: second group has 2 steps")

    # Steps before first STEP marker fall into None group
    mixed_steps = [
        StepResult(index=1, text="NAVIGATE to https://example.com", logical_step=None),
        StepResult(index=2, text="Fill 'User'", logical_step="Login"),
    ]
    groups3 = _group_steps(mixed_steps)
    _assert(len(groups3) == 2, "_group_steps: None group + Login group")
    _assert(groups3[0][0] is None, "_group_steps: first group is None (pre-STEP)")
    _assert(groups3[1][0] == "Login", "_group_steps: second group is Login")


# ── Section 6: _render_lstep_group HTML ──────────────────────────────────────


def _test_render_lstep_group() -> None:
    print("\n  ── _render_lstep_group — HTML output ─────────────────────")

    steps = [
        StepResult(index=1, text="Click 'Login'", logical_step="Authenticate"),
        StepResult(index=2, text="VERIFY that 'Dashboard' is present", logical_step="Authenticate"),
    ]
    html = _render_lstep_group("Authenticate", steps, 0)

    _assert("lstep-header" in html, "_render_lstep_group: has lstep-header class")
    _assert("Authenticate" in html, "_render_lstep_group: label text present")
    _assert("lstep-body" in html, "_render_lstep_group: has lstep-body wrapper")
    _assert("steps-list" in html, "_render_lstep_group: inner steps list present")
    _assert("2 actions" in html, "_render_lstep_group: action count shown")
    _assert("PASS" in html, "_render_lstep_group: PASS status when all steps pass")

    # Singular "action" for one step
    html_single = _render_lstep_group("Solo", [StepResult(index=1, text="DONE.")], 0)
    _assert(
        "1 action" in html_single and "1 actions" not in html_single,
        "_render_lstep_group: 'action' singular for 1 step",
    )

    # FAIL status when any step fails
    fail_steps = [
        StepResult(index=1, text="Click 'Login'", logical_step="Auth", status="fail"),
    ]
    html_fail = _render_lstep_group("Auth", fail_steps, 0)
    _assert("FAIL" in html_fail, "_render_lstep_group: FAIL status propagates from step")

    # Default label when None passed
    html_default = _render_lstep_group(None, steps, 0)
    _assert("Default" in html_default, "_render_lstep_group: label None renders as 'Default'")

    # HTML-escapes description
    html_xss = _render_lstep_group("<script>alert(1)</script>", steps, 0)
    _assert("<script>" not in html_xss, "_render_lstep_group: label is HTML-escaped")


# ── Section 7 & 8: generate_report integration ───────────────────────────────


def _test_generate_report() -> None:
    print("\n  ── generate_report — STEP grouping in HTML output ─────────")

    # Build a mission with STEP-tagged steps
    steps_grouped = [
        StepResult(index=1, text="NAVIGATE to https://example.com", logical_step="Setup", duration_ms=200),
        StepResult(index=2, text="Fill 'Username' with 'admin'", logical_step="Login", duration_ms=50),
        StepResult(index=3, text="Click 'Submit'", logical_step="Login", duration_ms=80),
        StepResult(
            index=4,
            text="VERIFY that 'Dashboard' is present",
            logical_step="Verification",
            status="fail",
            duration_ms=5000,
            error="Element not found",
        ),
    ]
    mr = MissionResult(file="/tmp/login.hunt", name="login.hunt", status="fail", duration_ms=6000, steps=steps_grouped)
    summary = RunSummary(
        started_at="2026-03-12T10:00:00",
        ended_at="2026-03-12T10:00:06",
        total=1,
        passed=0,
        failed=1,
        flaky=0,
        duration_ms=6000,
        missions=[mr],
    )

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        out_path = f.name

    try:
        generate_report(summary, out_path)
        content = open(out_path, encoding="utf-8").read()
    finally:
        os.unlink(out_path)

    _assert("lstep-header" in content, "generate_report: lstep-header present when STEP markers used")
    _assert("Setup" in content, "generate_report: 'Setup' group label present")
    _assert("Login" in content, "generate_report: 'Login' group label present")
    _assert("Verification" in content, "generate_report: 'Verification' group label present")
    _assert('<details class="lstep-block"' in content, "generate_report: accordion details element present")

    # Flat rendering: no STEP markers → no lstep-header
    steps_flat = [
        StepResult(index=1, text="NAVIGATE to https://example.com", duration_ms=100),
        StepResult(index=2, text="DONE.", duration_ms=1),
    ]
    mr_flat = MissionResult(file="/tmp/flat.hunt", name="flat.hunt", status="pass", duration_ms=200, steps=steps_flat)
    summary_flat = RunSummary(
        started_at="2026-03-12T10:00:00",
        ended_at="2026-03-12T10:00:00",
        total=1,
        passed=1,
        failed=0,
        flaky=0,
        duration_ms=200,
        missions=[mr_flat],
    )

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        out_path_flat = f.name

    try:
        generate_report(summary_flat, out_path_flat)
        content_flat = open(out_path_flat, encoding="utf-8").read()
    finally:
        os.unlink(out_path_flat)

    _assert(
        'class="lstep-header"' not in content_flat,
        "generate_report: no lstep-header when no STEP markers (flat rendering)",
    )
    _assert("steps-list" in content_flat, "generate_report: flat steps-list still present")


# ── Entry point ───────────────────────────────────────────────────────────────


async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n📋  test_28_logical_steps — STEP DSL grouping\n")

    _test_classify_step()
    _test_parse_logical_step()
    _test_quoted_isolation()
    _test_parse_hunt_blocks()
    _test_step_result_field()
    _test_group_steps()
    _test_render_lstep_group()
    _test_generate_report()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    print(f"  {'✅' if _FAIL == 0 else '❌'}  {_PASS} passed, {_FAIL} failed\n")
    return _FAIL == 0
