# manul_engine/test/test_38_set_and_indent.py
"""
Unit-test suite for v0.0.9.2 features:
  A. Indentation robustness — indented .hunt lines parse identically to flush ones.
  B. SET {var} = value — inline variable assignment during execution.
  C. SET + substitute_memory — variables set via SET are available in later steps.
  D. @var: + SET coexistence — static and inline variables work together.

No network, no live browser, no Ollama required.
All tests run against in-memory state, parsers and classify_step().

Entry point ``run_suite()`` is picked up by the dev test runner
(``python run_tests.py``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.helpers import classify_step, detect_mode, substitute_memory, extract_quoted
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
# Section A: Indentation robustness
# ═══════════════════════════════════════════════════════════════════════════════


def _test_indentation_stripping() -> None:
    """Prove that indented lines (as produced by the VS Code formatter) parse
    identically to flush lines after the master strip in run_mission()."""
    print("\n  ── Indentation robustness ────────────────────────────────────")

    # Simulate what run_mission() does at the master split point (line 871):
    # plan = [line.strip() for line in task.splitlines() if line.strip()]
    indented_hunt = """\
STEP 1: Login
    NAVIGATE to https://example.com/login
    Fill 'Username' with 'admin'
    Fill 'Password' with 'secret'
    Click the 'Login' button
    VERIFY that 'Welcome' is present

STEP 2: Extract data
    EXTRACT the 'Price' into {price}
    SET {discount} = '10%'
    WAIT 2
    SCROLL DOWN
    PRESS ENTER
    CALL PYTHON helpers.api.get_otp into {otp}
    DONE.
"""
    plan = [line.strip() for line in indented_hunt.splitlines() if line.strip()]

    _assert(classify_step(plan[0]) == "logical_step", "indented: STEP 1 recognised as logical_step")
    _assert(classify_step(plan[1]) == "navigate", "indented: NAVIGATE recognised after stripping")
    _assert(classify_step(plan[2]) == "action", "indented: Fill recognised as action after stripping")
    _assert(classify_step(plan[3]) == "action", "indented: Fill (password) recognised as action")
    _assert(classify_step(plan[4]) == "action", "indented: Click recognised as action")
    _assert(classify_step(plan[5]) == "verify", "indented: VERIFY recognised after stripping")
    _assert(classify_step(plan[6]) == "logical_step", "indented: STEP 2 recognised as logical_step")
    _assert(classify_step(plan[7]) == "extract", "indented: EXTRACT recognised after stripping")
    _assert(classify_step(plan[8]) == "set_var", "indented: SET recognised after stripping")
    _assert(classify_step(plan[9]) == "wait", "indented: WAIT recognised after stripping")
    _assert(classify_step(plan[10]) == "scroll", "indented: SCROLL recognised after stripping")
    _assert(classify_step(plan[11]) == "press_enter", "indented: PRESS ENTER recognised after stripping")
    _assert(classify_step(plan[12]) == "call_python", "indented: CALL PYTHON recognised after stripping")
    _assert(classify_step(plan[13]) == "done", "indented: DONE recognised after stripping")

    # Also verify detect_mode works on stripped indented lines
    _assert(detect_mode(plan[2]) == "input", "indented: detect_mode Fill = input")
    _assert(detect_mode(plan[4]) == "clickable", "indented: detect_mode Click = clickable")


def _test_indented_hunt_file_parse() -> None:
    """Prove parse_hunt_file handles indented action lines correctly."""
    print("\n  ── Indented hunt file parsing ─────────────────────────────────")

    hunt_content = """\
@context: Indentation test
@title: indent-test
@var: {email} = admin@test.com

STEP 1: Login
    NAVIGATE to https://example.com
    Fill 'Email' with '{email}'
    Click the 'Submit' button
    VERIFY that 'Success' is present
    DONE.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False) as f:
        f.write(hunt_content)
        path = f.name

    try:
        parsed = parse_hunt_file(path)
        mission = parsed.mission

        # The mission text should contain the lines (with or without
        # leading whitespace — run_mission strips anyway).
        _assert("NAVIGATE" in mission, "indented file: NAVIGATE present in mission")
        _assert("Fill" in mission, "indented file: Fill present in mission")
        _assert("VERIFY" in mission, "indented file: VERIFY present in mission")
        _assert(parsed.context == "Indentation test", "indented file: @context parsed correctly")
        _assert(parsed.title == "indent-test", "indented file: @title parsed correctly")
        _assert(parsed.parsed_vars.get("email") == "admin@test.com", "indented file: @var parsed correctly")
    finally:
        os.unlink(path)


def _test_tab_indentation() -> None:
    """Tabs should also be stripped cleanly."""
    print("\n  ── Tab indentation ───────────────────────────────────────────")

    tab_lines = [
        "\tNAVIGATE to https://example.com",
        "\t\tClick the 'Button'",
        "\tVERIFY that 'Text' is present",
        "\tSET {x} = 'hello'",
    ]
    stripped = [line.strip() for line in tab_lines]
    _assert(classify_step(stripped[0]) == "navigate", "tab indent: NAVIGATE recognised")
    _assert(classify_step(stripped[1]) == "action", "tab indent: Click recognised as action")
    _assert(classify_step(stripped[2]) == "verify", "tab indent: VERIFY recognised")
    _assert(classify_step(stripped[3]) == "set_var", "tab indent: SET recognised")


# ═══════════════════════════════════════════════════════════════════════════════
# Section B: SET command — classify_step recognition
# ═══════════════════════════════════════════════════════════════════════════════


def _test_classify_set() -> None:
    """classify_step must return 'set_var' for SET commands."""
    print("\n  ── classify_step — SET recognition ───────────────────────────")

    _assert(classify_step("SET {user_email} = 'admin@test.com'") == "set_var", "SET with braces and quoted value")
    _assert(classify_step("SET user_email = admin@test.com") == "set_var", "SET with bare key and unquoted value")
    _assert(classify_step("SET {token} = abc123") == "set_var", "SET with braces and unquoted value")
    _assert(classify_step('SET {greeting} = "Hello World"') == "set_var", "SET with double-quoted value")
    _assert(classify_step("1. SET {x} = 42") == "set_var", "numbered SET command")

    # Must NOT match SET inside quoted labels
    _assert(classify_step("Click 'Settings' button") == "action", "SET inside quoted text is not set_var (Settings)")
    _assert(classify_step("Click the 'Reset' button") == "action", "Reset is not SET")


# ═══════════════════════════════════════════════════════════════════════════════
# Section C: SET command — regex parsing
# ═══════════════════════════════════════════════════════════════════════════════


def _test_set_regex_parsing() -> None:
    """Verify the SET regex from core.py correctly extracts var name and value."""
    print("\n  ── SET regex parsing ─────────────────────────────────────────")

    _RE_SET = re.compile(
        r"(?:\d+\.\s*)?SET\s+\{?(\w+)\}?\s*=\s*(.+)",
        re.IGNORECASE,
    )

    # Case 1: braces + quoted value
    m = _RE_SET.match("SET {user_email} = 'admin@test.com'")
    _assert(m is not None, "regex: SET {key} = 'value' matches")
    if m:
        _assert(m.group(1) == "user_email", "regex: var name extracted", f"got {m.group(1)!r}")
        raw = m.group(2).strip()
        if len(raw) >= 2 and raw[0] in ("'", '"') and raw[-1] == raw[0]:
            raw = raw[1:-1]
        _assert(raw == "admin@test.com", "regex: quoted value unquoted", f"got {raw!r}")

    # Case 2: bare key + unquoted value
    m = _RE_SET.match("SET token = abc123")
    _assert(m is not None, "regex: SET key = value matches (no braces)")
    if m:
        _assert(m.group(1) == "token", "regex: bare key extracted")

    # Case 3: numbered prefix
    m = _RE_SET.match("1. SET {x} = 42")
    _assert(m is not None, "regex: numbered SET matches")
    if m:
        _assert(m.group(1) == "x", "regex: var name from numbered SET")
        _assert(m.group(2).strip() == "42", "regex: numeric value extracted")

    # Case 4: double-quoted value
    m = _RE_SET.match('SET {msg} = "Hello World"')
    _assert(m is not None, "regex: double-quoted value matches")
    if m:
        raw = m.group(2).strip()
        if len(raw) >= 2 and raw[0] in ("'", '"') and raw[-1] == raw[0]:
            raw = raw[1:-1]
        _assert(raw == "Hello World", "regex: double-quoted value unquoted")

    # Case 5: value with spaces, no quotes
    m = _RE_SET.match("SET {desc} = a long description here")
    _assert(m is not None, "regex: unquoted multi-word value matches")
    if m:
        _assert(m.group(2).strip() == "a long description here", "regex: multi-word value preserved")


# ═══════════════════════════════════════════════════════════════════════════════
# Section D: SET + substitute_memory integration
# ═══════════════════════════════════════════════════════════════════════════════


def _test_set_substitute_memory() -> None:
    """Simulate the SET → substitute_memory flow that core.py executes."""
    print("\n  ── SET + substitute_memory integration ───────────────────────")

    memory: dict[str, str] = {}

    # Step 1: SET {base_url} = 'https://staging.example.com'
    memory["base_url"] = "https://staging.example.com"

    # Step 2: NAVIGATE to {base_url}/login
    step2 = "NAVIGATE to {base_url}/login"
    substituted = substitute_memory(step2, memory)
    _assert(
        substituted == "NAVIGATE to https://staging.example.com/login",
        "SET var substituted in NAVIGATE step",
        f"got {substituted!r}",
    )

    # Step 3: SET {user} = 'admin'
    memory["user"] = "admin"

    # Step 4: Fill 'Username' with '{user}'
    step4 = "Fill 'Username' with '{user}'"
    substituted4 = substitute_memory(step4, memory)
    _assert(substituted4 == "Fill 'Username' with 'admin'", "SET var substituted in Fill step", f"got {substituted4!r}")


def _test_var_and_set_coexistence() -> None:
    """@var: static variables and inline SET must coexist in the same mission."""
    print("\n  ── @var: + SET coexistence ────────────────────────────────────")

    hunt_content = """\
@context: Coexistence test
@title: coexist

@var: {static_email} = static@example.com
@var: {env} = staging

STEP 1: Setup
SET {dynamic_token} = 'tok_abc123'
Fill 'Email' with '{static_email}'
Fill 'Token' with '{dynamic_token}'
NAVIGATE to https://{env}.example.com
DONE.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False) as f:
        f.write(hunt_content)
        path = f.name

    try:
        parsed = parse_hunt_file(path)

        # Static vars parsed correctly
        _assert(parsed.parsed_vars.get("static_email") == "static@example.com", "coexistence: @var static_email parsed")
        _assert(parsed.parsed_vars.get("env") == "staging", "coexistence: @var env parsed")

        # Simulate engine memory state after @var loading + SET execution
        memory = dict(parsed.parsed_vars)
        memory["dynamic_token"] = "tok_abc123"  # simulates SET step

        step_fill = "Fill 'Email' with '{static_email}'"
        _assert(
            substitute_memory(step_fill, memory) == "Fill 'Email' with 'static@example.com'",
            "coexistence: @var substitution works",
        )

        step_token = "Fill 'Token' with '{dynamic_token}'"
        _assert(
            substitute_memory(step_token, memory) == "Fill 'Token' with 'tok_abc123'",
            "coexistence: SET substitution works",
        )

        step_nav = "NAVIGATE to https://{env}.example.com"
        _assert(
            substitute_memory(step_nav, memory) == "NAVIGATE to https://staging.example.com",
            "coexistence: @var in URL substitution works",
        )
    finally:
        os.unlink(path)


def _test_set_not_confused_with_labels() -> None:
    """SET inside quoted text must not trigger the set_var classification."""
    print("\n  ── SET inside quoted labels ───────────────────────────────────")

    # 'Settings' contains 'SET' as a substring but should stay action
    _assert(classify_step("Click the 'Settings' button") == "action", "'Settings' label not classified as set_var")
    _assert(
        classify_step("VERIFY that 'Set up your account' is present") == "verify",
        "'Set up' in quoted verify not classified as set_var",
    )
    _assert(classify_step("Fill 'Offset' field with '100'") == "action", "'Offset' label not classified as set_var")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════


async def run_suite() -> tuple[int, int]:
    """Run all test sections and return (passed, failed)."""
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n" + "=" * 60)
    print("  TEST 38 — SET Command & Indentation Robustness (v0.0.9.2)")
    print("=" * 60)

    # A: Indentation robustness
    _test_indentation_stripping()
    _test_indented_hunt_file_parse()
    _test_tab_indentation()

    # B: SET classify_step recognition
    _test_classify_set()

    # C: SET regex parsing
    _test_set_regex_parsing()

    # D: SET + memory integration
    _test_set_substitute_memory()
    _test_var_and_set_coexistence()
    _test_set_not_confused_with_labels()

    total = _PASS + _FAIL
    print(f"\n  {'=' * 50}")
    print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
    print(f"  {'=' * 50}")
    print(f"  \U0001f4ca SCORE: {_PASS}/{total}")
    return _PASS, _FAIL
