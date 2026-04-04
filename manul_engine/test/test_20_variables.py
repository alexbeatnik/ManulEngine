# manul_engine/test/test_20_variables.py
"""
Unit-test suite for Static Variable Declaration (@var:) and initial_vars.

No network or live browser is required.  All tests run against synthetic
state only.

Tests:
  1. Parser correctness  -- parse_hunt_file extracts @var: lines into
     parsed_vars (7th element of the return tuple).
  2. Engine interpolation -- run_mission pre-populates self.memory when
     initial_vars is provided; substitution happens before step execution.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

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


# ── Section 1: Parser correctness ────────────────────────────────────────────

def _test_parser() -> None:
    print("\n  ── Parser (@var: extraction) ────────────────────────────────")

    hunt_content = """\
@context: Variables test
@title: vars

@var: {user_email} = admin@test.com
@var: {password} = secret123
@var: bare_key = no_braces_value

1. NAVIGATE to https://example.com
2. Fill 'Email' with '{user_email}'
3. Fill 'Password' with '{password}'
4. Fill 'Key' with '{bare_key}'
5. DONE.
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".hunt", encoding="utf-8", delete=False
    ) as tf:
        tf.write(hunt_content)
        tmp_path = tf.name

    try:
        result = parse_hunt_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    # 1a. Return value is a 12-tuple.
    _assert(
        len(result) == 12,
        "parse_hunt_file returns 12-tuple",
        f"len={len(result)}",
    )

    mission, context, title, step_file_lines, setup_lines, teardown_lines, parsed_vars, *_ = result

    # 1b. Standard metadata still parsed correctly.
    _assert(context == "Variables test", "context parsed correctly", f"got={context!r}")
    _assert(title == "vars", "title parsed correctly", f"got={title!r}")

    # 1c. @var: lines with braces are parsed into parsed_vars without braces.
    _assert(
        parsed_vars.get("user_email") == "admin@test.com",
        "@var: {user_email} extracted correctly",
        f"got={parsed_vars.get('user_email')!r}",
    )
    _assert(
        parsed_vars.get("password") == "secret123",
        "@var: {password} extracted correctly",
        f"got={parsed_vars.get('password')!r}",
    )

    # 1d. @var: without braces is parsed the same way.
    _assert(
        parsed_vars.get("bare_key") == "no_braces_value",
        "@var: bare_key (no braces) extracted correctly",
        f"got={parsed_vars.get('bare_key')!r}",
    )

    # 1e. @var: lines must NOT appear in the mission body.
    _assert(
        "@var:" not in mission,
        "@var: lines are not included in the mission body",
        f"mission={mission[:80]!r}",
    )

    # 1f. Numbered steps are collected into the mission body.
    _assert(
        "Fill 'Email' with '{user_email}'" in mission,
        "numbered steps with variable placeholders appear in the mission body",
    )

    # 1g. step_file_lines contains one entry per numbered step.
    _assert(
        len(step_file_lines) == 5,
        "step_file_lines has 5 entries (one per numbered step)",
        f"got={len(step_file_lines)}",
    )

    # 1h. Empty @var: line (malformed — no '=') is silently skipped.
    hunt_malformed = "@var: {broken}\n1. DONE.\n"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".hunt", encoding="utf-8", delete=False
    ) as tf:
        tf.write(hunt_malformed)
        tmp_path2 = tf.name
    try:
        _, _, _, _, _, _, bad_vars, *_ = parse_hunt_file(tmp_path2)
    finally:
        os.unlink(tmp_path2)
    _assert(
        "broken" not in bad_vars,
        "malformed @var: line (no '=') is silently skipped",
        f"parsed_vars={bad_vars}",
    )


def _test_script_alias_parser_rewrite() -> None:
    print("\n  ── Parser (@script: alias rewrite) ─────────────────────────")

    hunt_content = """\
@context: Script aliases
@title: script_aliases
@script: {printer} = scripts.print
@script: {seed_mega_fixture} = scripts.demo_helpers.seed_mega_fixture

[SETUP]
CALL PYTHON {printer}.bootstrap
CALL PYTHON {seed_mega_fixture} with args: "shadow" "table"
[END SETUP]

STEP 1: Use alias in mission
CALL PYTHON {printer}.emit into {message}
CALL PYTHON {seed_mega_fixture} into {fixture_id}
DONE.
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".hunt", encoding="utf-8", delete=False
    ) as tf:
        tf.write(hunt_content)
        tmp_path = tf.name

    try:
        result = parse_hunt_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    mission, _, _, _, setup_lines, _, _, *_ = result

    _assert(
        "@script:" not in mission,
        "@script: header is not included in mission body",
        f"mission={mission!r}",
    )
    _assert(
        setup_lines == [
            "CALL PYTHON scripts.print.bootstrap",
            'CALL PYTHON scripts.demo_helpers.seed_mega_fixture with args: "shadow" "table"',
        ],
        "@script aliases rewrite hook CALL PYTHON lines",
        f"setup_lines={setup_lines!r}",
    )
    _assert(
        "CALL PYTHON scripts.print.emit into {message}" in mission,
        "module-style @script alias rewrites mission CALL PYTHON line",
        f"mission={mission!r}",
    )
    _assert(
        "CALL PYTHON scripts.demo_helpers.seed_mega_fixture into {fixture_id}" in mission,
        "callable-style @script alias rewrites mission CALL PYTHON line",
        f"mission={mission!r}",
    )


def _test_script_alias_parser_preserves_step_line_breaks() -> None:
    print("\n  ── Parser (@script: preserve mission line breaks) ───────────")

    hunt_content = """\
@context: Preserve line breaks
@title: preserve_breaks
@script: {showcase} = scripts.call_python_showcase

STEP 1: Aliased calls stay separate
    CALL PYTHON {showcase}.print_setup_banner
    CALL PYTHON {showcase}.build_token with args: "module-alias" into {alias_token}

STEP 2: Next step header stays separate
    DONE.
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".hunt", encoding="utf-8", delete=False
    ) as tf:
        tf.write(hunt_content)
        tmp_path = tf.name

    try:
        result = parse_hunt_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    mission = result.mission
    mission_lines = [line.strip() for line in mission.splitlines()]

    _assert(
        "CALL PYTHON scripts.call_python_showcase.print_setup_banner" in mission_lines,
        "module alias rewrite preserves first action as its own line",
        f"mission_lines={mission_lines!r}",
    )
    _assert(
        'CALL PYTHON scripts.call_python_showcase.build_token with args: "module-alias" into {alias_token}' in mission_lines,
        "module alias rewrite preserves second action as its own line",
        f"mission_lines={mission_lines!r}",
    )
    _assert(
        "STEP 2: Next step header stays separate" in mission_lines,
        "module alias rewrite does not concatenate the next STEP header",
        f"mission_lines={mission_lines!r}",
    )


def _test_script_alias_requires_dotted_python_path() -> None:
    print("\n  ── Parser (@script: dotted Python path validation) ────────")

    bad_hunt = """\
@context: Invalid script alias
@title: invalid_script_alias
@script: {printer} = scripts/print.py

DONE.
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".hunt", encoding="utf-8", delete=False
    ) as tf:
        tf.write(bad_hunt)
        tmp_path = tf.name

    try:
        try:
            parse_hunt_file(tmp_path)
            _assert(False, "slash-style @script path is rejected")
        except ValueError as exc:
            msg = str(exc)
            _assert("Invalid @script target 'scripts/print.py'" in msg, "invalid @script path reports offending value", msg)
            _assert("no '/'" in msg and "no '.py' suffix" in msg, "invalid @script path explains dotted-path rule", msg)
    finally:
        os.unlink(tmp_path)


def _test_script_alias_requires_placeholder_identifier_name() -> None:
    print("\n  ── Parser (@script: alias name validation) ───────────────")

    bad_hunt = """\
@context: Invalid script alias name
@title: invalid_script_alias_name
@script: {my-alias} = scripts.print

DONE.
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".hunt", encoding="utf-8", delete=False
    ) as tf:
        tf.write(bad_hunt)
        tmp_path = tf.name

    try:
        try:
            parse_hunt_file(tmp_path)
            _assert(False, "invalid @script alias name is rejected")
        except ValueError as exc:
            msg = str(exc)
            _assert("Invalid @script alias '{my-alias}'" in msg, "invalid alias name reports offending value", msg)
            _assert("letters, digits, and underscores" in msg, "invalid alias name explains identifier rule", msg)
    finally:
        os.unlink(tmp_path)


# ── Section 2: Engine interpolation ──────────────────────────────────────────

async def _test_interpolation() -> None:
    print("\n  ── Engine interpolation (run_mission + initial_vars) ────────")

    with patch("manul_engine.core.load_custom_controls"):
        from manul_engine.core import ManulEngine
        engine = ManulEngine(model=None, disable_cache=True)

    # Capture the step string that _execute_step receives.
    captured_steps: list[str] = []

    async def _fake_execute_step(page, step: str, strategic_context: str = "", step_idx: int = 0) -> bool:
        captured_steps.append(step)
        return True

    # Minimal Playwright fakes.
    fake_page = MagicMock()
    fake_page.url = "https://example.com/login"
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

    task = "1. Fill 'Email' with '{user_email}'\n2. Fill 'Password' with '{password}'"

    with (
        patch("manul_engine.core.async_playwright", return_value=mock_playwright),
        patch.object(engine, "_execute_step", side_effect=_fake_execute_step),
        patch("manul_engine.core.load_custom_controls"),
    ):
        await engine.run_mission(
            task,
            initial_vars={"user_email": "test@manul.com", "password": "hunter2"},
        )

    # 2a. Both steps were passed to _execute_step.
    _assert(
        len(captured_steps) == 2,
        "_execute_step called twice (one per action step)",
        f"count={len(captured_steps)}",
    )

    # 2b. {user_email} placeholder is substituted before execution.
    email_step = captured_steps[0] if captured_steps else ""
    _assert(
        "test@manul.com" in email_step,
        "{user_email} substituted with 'test@manul.com' in step text",
        f"step={email_step!r}",
    )
    _assert(
        "{user_email}" not in email_step,
        "raw {user_email} placeholder absent from substituted step",
        f"step={email_step!r}",
    )

    # 2c. Second variable also substituted correctly.
    password_step = captured_steps[1] if len(captured_steps) > 1 else ""
    _assert(
        "hunter2" in password_step,
        "{password} substituted with 'hunter2' in step text",
        f"step={password_step!r}",
    )

    # 2d. Variables survive into self.memory after the run.
    _assert(
        engine.memory.get("user_email") == "test@manul.com",
        "initial_vars are available in engine.memory after run",
        f"memory={engine.memory}",
    )

    # 2e. No initial_vars → memory starts empty for that key.
    with patch("manul_engine.core.load_custom_controls"):
        engine2 = ManulEngine(model=None, disable_cache=True)
    _assert(
        engine2.memory.get("user_email") is None,
        "fresh engine has no pre-populated variables without initial_vars",
    )

    # 2f. initial_vars=None is accepted and treated as no-op.
    captured_steps.clear()
    with patch("manul_engine.core.load_custom_controls"):
        engine3 = ManulEngine(model=None, disable_cache=True)
    with (
        patch("manul_engine.core.async_playwright", return_value=mock_playwright),
        patch.object(engine3, "_execute_step", side_effect=_fake_execute_step),
        patch("manul_engine.core.load_custom_controls"),
    ):
        await engine3.run_mission("1. DONE.", initial_vars=None)
    _assert(
        engine3.memory == {},
        "initial_vars=None leaves memory empty",
        f"memory={engine3.memory}",
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    _test_parser()
    _test_script_alias_parser_rewrite()
    _test_script_alias_parser_preserves_step_line_breaks()
    _test_script_alias_requires_dotted_python_path()
    _test_script_alias_requires_placeholder_identifier_name()
    await _test_interpolation()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    return _FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(run_suite())
    sys.exit(0 if ok else 1)
