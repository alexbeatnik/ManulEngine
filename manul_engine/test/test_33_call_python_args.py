# manul_engine/test/test_33_call_python_args.py
"""
Unit-test suite for CALL PYTHON with positional arguments.

No network or live browser is required.  All tests run against synthetic
state only.

Tests:
  1. Parser — regex correctly splits dotted name, arguments, and into clause.
  2. Arg parsing — shlex tokenisation, single/double quotes, {var} placeholders.
  3. Variable resolution — {var} placeholders resolved from variables dict.
  4. Execution — function called with positional args, return value captured.
  5. Backward compat — parameterless calls still work unchanged.
  6. Engine integration — run_mission passes self.memory as variables.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python run_tests.py``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import textwrap
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.hooks import HookResult, execute_hook_line, _parse_call_args

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


def _make_module(attrs: dict) -> types.ModuleType:
    """Create a throw-away module object with the given attributes."""
    mod = types.ModuleType("_test_args_mod")
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _make_helper(tmp_dir: str, filename: str, source: str) -> None:
    """Write *source* to *filename* inside *tmp_dir*."""
    Path(tmp_dir, filename).write_text(textwrap.dedent(source), encoding="utf-8")


# ── Section 1: Arg parser unit tests ─────────────────────────────────────────


def _test_parse_call_args() -> None:
    print("\n  ── _parse_call_args ─────────────────────────────────────────")

    # 1a. Empty string → empty list
    _assert(_parse_call_args("") == [], "empty string → []")
    _assert(_parse_call_args("   ") == [], "whitespace-only → []")
    _assert(_parse_call_args(None) == [], "None → []")

    # 1b. Simple unquoted tokens
    _assert(
        _parse_call_args("hello world") == ["hello", "world"],
        "simple unquoted tokens",
    )

    # 1c. Double-quoted strings
    _assert(
        _parse_call_args('"hello world" "foo"') == ["hello world", "foo"],
        "double-quoted strings",
    )

    # 1d. Single-quoted strings
    _assert(
        _parse_call_args("'hello world' 'bar'") == ["hello world", "bar"],
        "single-quoted strings",
    )

    # 1e. Mixed quotes
    _assert(
        _parse_call_args(""""arg 1" 'arg 2' plain""") == ["arg 1", "arg 2", "plain"],
        "mixed quotes and plain token",
    )

    # 1f. Variable placeholder without resolution
    _assert(
        _parse_call_args("{email}") == ["{email}"],
        "{var} placeholder without variables dict → kept literal",
    )

    # 1g. Variable placeholder with resolution
    _assert(
        _parse_call_args("{email}", {"email": "a@b.com"}) == ["a@b.com"],
        "{var} resolved from variables dict",
    )

    # 1h. Mixed args with variable resolution
    result = _parse_call_args('"static" {name} 42', {"name": "Manul"})
    _assert(
        result == ["static", "Manul", "42"],
        "mixed static + {var} + plain resolved correctly",
        f"got={result!r}",
    )

    # 1i. Unresolved variable kept as-is
    result = _parse_call_args("{unknown}", {"other": "val"})
    _assert(
        result == ["{unknown}"],
        "unresolved {var} kept as literal",
        f"got={result!r}",
    )


# ── Section 2: Parser regex + execute_hook_line parsing ──────────────────────


def _test_parser_regex() -> None:
    print("\n  ── Parser regex (splitting dotted, args, into) ──────────────")

    def _noop():
        pass

    def _echo(*args):
        return " ".join(args)

    mod = _make_module({"noop": _noop, "echo": _echo})

    with patch("manul_engine.hooks._resolve_module", return_value=(mod, False)):
        # 2a. No args, no into — backward compat
        r = execute_hook_line("CALL PYTHON mock_mod.noop")
        _assert(r.success, "no args, no into → success")
        _assert(r.var_name is None, "no args, no into → var_name is None")
        _assert(r.return_value is None, "no args, no into → return_value is None")

        # 2b. No args, with into
        def _get_val():
            return "hello"

        mod2 = _make_module({"get_val": _get_val})
        with patch("manul_engine.hooks._resolve_module", return_value=(mod2, False)):
            r = execute_hook_line("CALL PYTHON mock_mod.get_val into {greeting}")
        _assert(r.success, "no args, with into → success")
        _assert(r.var_name == "greeting", "no args, with into → var_name='greeting'", f"got={r.var_name!r}")
        _assert(r.return_value == "hello", "no args, with into → return_value='hello'", f"got={r.return_value!r}")

        # 2c. With args, no into
        r = execute_hook_line('CALL PYTHON mock_mod.echo "world" "peace"')
        _assert(r.success, "with args, no into → success")
        _assert(r.var_name is None, "with args, no into → var_name is None")

        # 2d. With args and into
        r = execute_hook_line('CALL PYTHON mock_mod.echo "hello" "world" into {msg}')
        _assert(r.success, "with args and into → success", r.message)
        _assert(r.var_name == "msg", "with args and into → var_name='msg'", f"got={r.var_name!r}")
        _assert(
            r.return_value == "hello world",
            "with args and into → return_value='hello world'",
            f"got={r.return_value!r}",
        )

        # 2e. With 'to' alias
        r = execute_hook_line('CALL PYTHON mock_mod.echo "a" "b" to {out}')
        _assert(r.success, "'to' alias with args → success")
        _assert(r.var_name == "out", "'to' alias with args → var_name='out'", f"got={r.var_name!r}")
        _assert(r.return_value == "a b", "'to' alias with args → return_value='a b'", f"got={r.return_value!r}")


def _test_unresolved_script_alias_error() -> None:
    print("\n  ── CALL PYTHON unresolved @script alias ───────────────────")

    r = execute_hook_line("CALL PYTHON {printer}.emit into {msg}")
    _assert(not r.success, "unresolved @script alias → failure")
    _assert("Unresolved @script alias" in r.message, "unresolved alias → helpful message")
    _assert("@script: {printer}" in r.message, "unresolved alias → declaration hint included")

    r2 = execute_hook_line('CALL PYTHON {seed_mega_fixture} with args: "shadow"')
    _assert(not r2.success, "unresolved callable @script alias → failure")
    _assert("@script: {seed_mega_fixture}" in r2.message, "unresolved callable alias → declaration hint included")
    _assert("alias a callable directly" in r2.message, "unresolved callable alias → callable hint included")


# ── Section 3: Variable resolution in args ───────────────────────────────────


def _test_variable_resolution() -> None:
    print("\n  ── Variable resolution in args ─────────────────────────────")

    def _multiply(a, b):
        return int(a) * int(b)

    mod = _make_module({"multiply": _multiply})
    variables = {"factor": "7"}

    with patch("manul_engine.hooks._resolve_module", return_value=(mod, False)):
        # 3a. Static args only
        r = execute_hook_line(
            'CALL PYTHON mock_mod.multiply "3" "5" into {product}',
            variables=variables,
        )
        _assert(r.success, "static args → success")
        _assert(r.return_value == "15", "3 × 5 = 15", f"got={r.return_value!r}")

        # 3b. {var} placeholder resolved from variables
        r = execute_hook_line(
            'CALL PYTHON mock_mod.multiply "6" {factor} into {product}',
            variables=variables,
        )
        _assert(r.success, "{var} resolved → success")
        _assert(r.return_value == "42", "6 × 7 = 42", f"got={r.return_value!r}")

        # 3c. Multiple {var} placeholders
        variables2 = {"a": "10", "b": "20"}
        r = execute_hook_line(
            "CALL PYTHON mock_mod.multiply {a} {b} into {product}",
            variables=variables2,
        )
        _assert(r.success, "multiple {var} resolved → success")
        _assert(r.return_value == "200", "10 × 20 = 200", f"got={r.return_value!r}")


# ── Section 4: File-based execution with args ────────────────────────────────


def _test_file_based_execution(tmp_dir: str) -> None:
    print("\n  ── File-based helper execution with args ───────────────────")

    _make_helper(
        tmp_dir,
        "math_helper.py",
        """\
        def add(a, b):
            return int(a) + int(b)

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        def concat(*args):
            return "-".join(args)

        def no_args():
            return "ok"
    """,
    )

    # 4a. Two args, file-based module
    r = execute_hook_line(
        'CALL PYTHON math_helper.add "10" "32" into {sum}',
        hunt_dir=tmp_dir,
    )
    _assert(r.success, "file-based add(10, 32) → success", r.message)
    _assert(r.return_value == "42", "10 + 32 = 42", f"got={r.return_value!r}")

    # 4b. Backward compat — no args
    r = execute_hook_line(
        "CALL PYTHON math_helper.no_args into {val}",
        hunt_dir=tmp_dir,
    )
    _assert(r.success, "file-based no_args() → success", r.message)
    _assert(r.return_value == "ok", "no_args returns 'ok'", f"got={r.return_value!r}")

    # 4c. Variadic args
    r = execute_hook_line(
        'CALL PYTHON math_helper.concat "a" "b" "c" into {joined}',
        hunt_dir=tmp_dir,
    )
    _assert(r.success, "variadic concat → success", r.message)
    _assert(r.return_value == "a-b-c", "concat(a,b,c) = 'a-b-c'", f"got={r.return_value!r}")

    # 4d. Args with variable resolution
    r = execute_hook_line(
        "CALL PYTHON math_helper.greet {user} into {msg}",
        hunt_dir=tmp_dir,
        variables={"user": "Manul"},
    )
    _assert(r.success, "greet with {var} → success", r.message)
    _assert(r.return_value == "Hello, Manul!", "greet(Manul) correct", f"got={r.return_value!r}")


# ── Section 5: Engine integration ────────────────────────────────────────────


async def _test_engine_integration() -> None:
    print("\n  ── Engine integration (args + memory) ──────────────────────")

    with patch("manul_engine.core.load_custom_controls"):
        from manul_engine.core import ManulEngine

        engine = ManulEngine(model=None, disable_cache=True)

    captured_steps: list[str] = []

    async def _fake_execute_step(page, step: str, strategic_context: str = "", step_idx: int = 0) -> bool:
        captured_steps.append(step)
        return True

    fake_page = MagicMock()
    fake_page.url = "https://example.com/calc"
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

    # Module with a multiply function
    def _multiply(a, b):
        return int(a) * int(b)

    calc_mod = _make_module({"multiply": _multiply})

    # 5a. CALL PYTHON with static args + into — value bound to memory
    mission = "1. CALL PYTHON calc.multiply \"6\" \"7\" into {product}\n2. Fill 'Result' with '{product}'\n"

    with (
        patch("manul_engine.core.async_playwright", return_value=mock_playwright),
        patch.object(engine, "_execute_step", side_effect=_fake_execute_step),
        patch("manul_engine.hooks._resolve_module", return_value=(calc_mod, False)),
        patch("manul_engine.core.load_custom_controls"),
    ):
        await engine.run_mission(mission)

    _assert(
        engine.memory.get("product") == "42",
        "engine.memory['product'] == '42' after multiply(6, 7)",
        f"memory={engine.memory}",
    )

    fill_step = captured_steps[0] if captured_steps else ""
    _assert(
        "42" in fill_step,
        "Fill step received '42' after {product} substitution",
        f"step={fill_step!r}",
    )

    # 5b. CALL PYTHON with {var} arg resolved from memory
    captured_steps.clear()
    with patch("manul_engine.core.load_custom_controls"):
        engine2 = ManulEngine(model=None, disable_cache=True)
    engine2.memory["base"] = "10"

    mission2 = "1. CALL PYTHON calc.multiply {base} \"5\" into {result}\n2. Fill 'Total' with '{result}'\n"

    with (
        patch("manul_engine.core.async_playwright", return_value=mock_playwright),
        patch.object(engine2, "_execute_step", side_effect=_fake_execute_step),
        patch("manul_engine.hooks._resolve_module", return_value=(calc_mod, False)),
        patch("manul_engine.core.load_custom_controls"),
    ):
        await engine2.run_mission(mission2)

    _assert(
        engine2.memory.get("result") == "50",
        "engine2.memory['result'] == '50' after multiply({base}=10, 5)",
        f"memory={engine2.memory}",
    )

    fill_step2 = captured_steps[0] if captured_steps else ""
    _assert(
        "50" in fill_step2,
        "Fill step received '50' after {result} substitution",
        f"step={fill_step2!r}",
    )

    # 5c. Backward compat — parameterless CALL PYTHON still works
    captured_steps.clear()
    with patch("manul_engine.core.load_custom_controls"):
        engine3 = ManulEngine(model=None, disable_cache=True)

    def _get_token():
        return "abc123"

    token_mod = _make_module({"get_token": _get_token})
    mission3 = "1. CALL PYTHON auth.get_token into {token}\n2. Fill 'Token' with '{token}'\n"
    with (
        patch("manul_engine.core.async_playwright", return_value=mock_playwright),
        patch.object(engine3, "_execute_step", side_effect=_fake_execute_step),
        patch("manul_engine.hooks._resolve_module", return_value=(token_mod, False)),
        patch("manul_engine.core.load_custom_controls"),
    ):
        await engine3.run_mission(mission3)

    _assert(
        engine3.memory.get("token") == "abc123",
        "backward compat: parameterless call → memory['token']='abc123'",
        f"memory={engine3.memory}",
    )


# ── Entry point ───────────────────────────────────────────────────────────────


async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  test_33_call_python_args — CALL PYTHON with arguments")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    _test_parse_call_args()
    _test_parser_regex()
    _test_unresolved_script_alias_error()
    _test_variable_resolution()

    with tempfile.TemporaryDirectory(prefix="manul_args_test_") as tmp_dir:
        _test_file_based_execution(tmp_dir)

    await _test_engine_integration()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    return _FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(run_suite())
    sys.exit(0 if ok else 1)
