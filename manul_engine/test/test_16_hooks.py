# manul_engine/test/test_16_hooks.py
"""
Unit-test suite for manul_engine.hooks — no browser required.

Validates:
  • extract_hook_blocks  — block detection, comment skipping, line preservation
  • execute_hook_line    — CALL PYTHON dispatch, module resolution, error paths
  • run_hooks            — sequential execution, stop-on-failure, early-exit

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async even though no Playwright
page is created.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import textwrap
from pathlib import Path

# Ensure the repo root is on sys.path when run standalone.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.hooks import (
    execute_hook_line,
    extract_hook_blocks,
    run_hooks,
)

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
        msg = f" ({detail})" if detail else ""
        print(f"    ❌  {name}{msg}")


def _make_helper(tmp_dir: str, filename: str, source: str) -> None:
    """Write *source* to *filename* inside *tmp_dir*."""
    Path(tmp_dir, filename).write_text(textwrap.dedent(source), encoding="utf-8")


# ── Suite sections ────────────────────────────────────────────────────────────

def _test_extract_hook_blocks() -> None:
    print("\n  ── extract_hook_blocks ──────────────────────────────────")

    # ── 1. Both blocks present, mission body preserved ────────────────────────
    raw = textwrap.dedent("""\
        @context: Login flow

        [SETUP]
        CALL PYTHON db_helpers.seed_admin
        [END SETUP]

        1. Navigate to https://example.com
        2. Click 'Login'

        [TEARDOWN]
        CALL PYTHON db_helpers.clean_all
        [END TEARDOWN]

        3. DONE.
    """)
    setup, teardown, body = extract_hook_blocks(raw)
    _assert(setup == ["CALL PYTHON db_helpers.seed_admin"],
            "setup line extracted correctly")
    _assert(teardown == ["CALL PYTHON db_helpers.clean_all"],
            "teardown line extracted correctly")
    _assert("Navigate" in body and "DONE" in body,
            "mission body contains main steps")
    _assert("[SETUP]" not in body and "[TEARDOWN]" not in body,
            "hook markers absent from mission body")
    _assert("@context" in body,
            "metadata header preserved in mission body")

    # ── 2. No hooks — body returned unchanged ─────────────────────────────────
    plain = "1. Navigate to https://example.com\n2. DONE.\n"
    s2, t2, b2 = extract_hook_blocks(plain)
    _assert(s2 == [] and t2 == [],
            "no-hook file produces empty setup/teardown lists")
    _assert(b2 == plain,
            "no-hook file body is unchanged")

    # ── 3. Case-insensitive markers ───────────────────────────────────────────
    mixed = "[setup]\nCALL PYTHON x.y\n[end setup]\n1. Step\n"
    s3, _, b3 = extract_hook_blocks(mixed)
    _assert(s3 == ["CALL PYTHON x.y"],
            "case-insensitive [setup] marker")
    _assert("1. Step" in b3,
            "mission body intact after case-insensitive block")

    # ── 4. Comments inside blocks are skipped ─────────────────────────────────
    with_comments = textwrap.dedent("""\
        [SETUP]
        # This is a comment
        CALL PYTHON helpers.setup_db
        # Another comment
        [END SETUP]
        1. Step
    """)
    s4, _, _ = extract_hook_blocks(with_comments)
    _assert(s4 == ["CALL PYTHON helpers.setup_db"],
            "comments inside setup block skipped")

    # ── 5. Multiple instructions per block ────────────────────────────────────
    multi = textwrap.dedent("""\
        [TEARDOWN]
        CALL PYTHON helpers.clean_users
        CALL PYTHON helpers.clean_orders
        CALL PYTHON helpers.reset_flags
        [END TEARDOWN]
        1. Step
    """)
    _, t5, _ = extract_hook_blocks(multi)
    _assert(len(t5) == 3,
            "multiple teardown instructions all collected")

    # ── 6. Empty blocks produce empty lists ───────────────────────────────────
    empty = "[SETUP]\n# comment only\n[END SETUP]\n1. Step\n"
    s6, _, _ = extract_hook_blocks(empty)
    _assert(s6 == [],
            "empty (comment-only) setup block yields empty list")


def _test_execute_hook_line__syntax() -> None:
    print("\n  ── execute_hook_line — syntax errors ────────────────────")

    # ── Unrecognised instruction ───────────────────────────────────────────────
    r1 = execute_hook_line("RUN SHELL echo hello")
    _assert(not r1.success, "unrecognised instruction → failure")
    _assert("Unrecognised hook instruction" in r1.message,
            "unrecognised instruction → helpful message")

    # ── Missing function name (no dot) ────────────────────────────────────────
    r2 = execute_hook_line("CALL PYTHON just_a_module")
    _assert(not r2.success, "missing function name → failure")
    _assert("module>.<function>" in r2.message,
            "missing function name → format hint in message")

    # ── Empty instruction ─────────────────────────────────────────────────────
    r3 = execute_hook_line("")
    _assert(not r3.success, "empty instruction → failure")


def _test_execute_hook_line__module_not_found() -> None:
    print("\n  ── execute_hook_line — module not found ─────────────────")

    r = execute_hook_line("CALL PYTHON nonexistent_xyz_module_abc.some_func")
    _assert(not r.success, "missing module → failure")
    _assert("not found" in r.message.lower(),
            "missing module → 'not found' in message")
    _assert("nonexistent_xyz_module_abc" in r.message,
            "missing module → module name echoed in message")
    _assert("CWD" in r.message or "sys.path" in r.message,
            "missing module → search locations mentioned")


def _test_execute_hook_line__success(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — successful execution ─────────────")

    _make_helper(tmp_dir, "good_helper.py", """\
        _called: list[str] = []

        def inject_admin_user() -> None:
            _called.append("inject_admin_user")

        def clean_database() -> None:
            _called.append("clean_database")
    """)

    r1 = execute_hook_line(
        "CALL PYTHON good_helper.inject_admin_user",
        hunt_dir=tmp_dir,
    )
    _assert(r1.success, "valid CALL PYTHON → success")
    _assert("inject_admin_user" in r1.message,
            "success result message includes function name")

    r2 = execute_hook_line(
        "CALL PYTHON good_helper.clean_database",
        hunt_dir=tmp_dir,
    )
    _assert(r2.success, "second valid call → success")


def _test_execute_hook_line__print_and_dict_context(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — PRINT and dict context ───────────")

    _make_helper(tmp_dir, "context_helper.py", """\
        def get_context():
            return {"random_id": "4242", "username": "manul_tester_4242"}
    """)

    ctx: dict[str, str] = {}
    r1 = execute_hook_line(
        "CALL PYTHON context_helper.get_context",
        hunt_dir=tmp_dir,
        variables=ctx,
    )
    from manul_engine.hooks import bind_hook_result
    bind_hook_result(r1, ctx)
    _assert(r1.success, "dict-returning helper succeeds")
    _assert(ctx.get("random_id") == "4242", "dict key random_id exposed as shared variable")
    _assert(ctx.get("username") == "manul_tester_4242", "dict key username exposed as shared variable")

    r2 = execute_hook_line('PRINT "Cleanup complete for {random_id}"', variables=ctx)
    _assert(r2.success, "PRINT instruction succeeds")
    _assert(r2.message == "Cleanup complete for 4242", "PRINT substitutes shared variables")


def _test_execute_hook_line__scripts_folder_and_with_args(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — /scripts lookup + with args ───────")

    scripts_dir = Path(tmp_dir, "scripts")
    scripts_dir.mkdir(parents=True, exist_ok=True)
    _make_helper(str(scripts_dir), "auth.py", """\
        def get_admin_token():
            return "adm_tok_123"
    """)
    _make_helper(str(scripts_dir), "db_cleanup.py", """\
        def delete_user(username):
            return f"deleted:{username}"
    """)

    r1 = execute_hook_line(
        "CALL PYTHON auth.get_admin_token into {auth_token}",
        hunt_dir=tmp_dir,
        variables={},
    )
    _assert(r1.success, "helper loaded from /scripts folder in project root")
    _assert(r1.return_value == "adm_tok_123", "scripts helper return captured into variable")

    r2 = execute_hook_line(
        "CALL PYTHON db_cleanup.delete_user with args: 'manul_tester_77' into {cleanup_status}",
        hunt_dir=tmp_dir,
        variables={},
    )
    _assert(r2.success, "with args: syntax succeeds")
    _assert(r2.return_value == "deleted:manul_tester_77", "with args: forwards positional argument")


def _test_execute_hook_line__function_not_found(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — function not found ───────────────")

    _make_helper(tmp_dir, "partial_helper.py", """\
        def existing_func() -> None:
            pass
    """)

    r = execute_hook_line(
        "CALL PYTHON partial_helper.missing_func",
        hunt_dir=tmp_dir,
    )
    _assert(not r.success, "missing function → failure")
    _assert("missing_func" in r.message,
            "missing function → function name echoed")
    _assert("partial_helper" in r.message,
            "missing function → module name in message")
    _assert("existing_func" in r.message,
            "missing function → available names listed (helpful hint)")


def _test_execute_hook_line__not_callable(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — attribute not callable ───────────")

    _make_helper(tmp_dir, "const_helper.py", """\
        DB_URL = "postgresql://localhost/test"
    """)

    r = execute_hook_line(
        "CALL PYTHON const_helper.DB_URL",
        hunt_dir=tmp_dir,
    )
    _assert(not r.success, "non-callable attribute → failure")
    _assert("not callable" in r.message.lower(),
            "non-callable → 'not callable' in message")
    _assert("str" in r.message,
            "non-callable → actual type named in message")


def _test_execute_hook_line__runtime_error(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — function raises an exception ─────")

    _make_helper(tmp_dir, "failing_helper.py", """\
        def inject_broken() -> None:
            raise RuntimeError("DB connection refused on port 5432")
    """)

    r = execute_hook_line(
        "CALL PYTHON failing_helper.inject_broken",
        hunt_dir=tmp_dir,
    )
    _assert(not r.success, "function that raises → failure")
    _assert("RuntimeError" in r.message,
            "exception type surfaced in error message")
    _assert("DB connection refused" in r.message,
            "exception text surfaced in error message")


def _test_execute_hook_line__async_rejected(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — async function rejected ──────────")

    _make_helper(tmp_dir, "async_helper.py", """\
        import asyncio

        async def async_setup() -> None:
            await asyncio.sleep(0)
    """)

    r = execute_hook_line(
        "CALL PYTHON async_helper.async_setup",
        hunt_dir=tmp_dir,
    )
    _assert(not r.success, "async callable → failure (not silently awaited)")
    _assert("async" in r.message.lower(),
            "async rejection → 'async' mentioned in message")
    _assert("asyncio.run" in r.message,
            "async rejection → actionable workaround suggested")


def _test_execute_hook_line__state_isolation(tmp_dir: str) -> None:
    print("\n  ── execute_hook_line — module state isolation ───────────")

    _make_helper(tmp_dir, "stateful_helper.py", """\
        _counter = 0

        def increment() -> None:
            global _counter
            _counter += 1

        def get_counter() -> int:
            return _counter
    """)

    # JIT cache: first call imports the module; second reuses from cache.
    # Module state persists across calls (counter accumulates).
    from manul_engine.hooks import clear_module_cache
    clear_module_cache()  # ensure clean state for this test

    r1 = execute_hook_line("CALL PYTHON stateful_helper.increment", hunt_dir=tmp_dir)
    _assert(r1.success, "first increment() succeeds")

    r2 = execute_hook_line("CALL PYTHON stateful_helper.increment", hunt_dir=tmp_dir)
    _assert(r2.success, "second increment() succeeds (from cache)")

    # The module must NOT be cached in sys.modules under its plain name.
    _assert(
        "stateful_helper" not in sys.modules,
        "locally resolved module not inserted into sys.modules",
    )

    clear_module_cache()  # cleanup


def _test_run_hooks(tmp_dir: str) -> None:
    print("\n  ── run_hooks ─────────────────────────────────────────────")

    _make_helper(tmp_dir, "multi_helper.py", """\
        log: list[str] = []

        def step_a() -> None:
            log.append("a")

        def step_b() -> None:
            log.append("b")

        def step_fail() -> None:
            raise ValueError("intentional failure")
    """)

    # ── All succeed ───────────────────────────────────────────────────────────
    ok = run_hooks(
        ["CALL PYTHON multi_helper.step_a", "CALL PYTHON multi_helper.step_b"],
        label="SETUP",
        hunt_dir=tmp_dir,
    )
    _assert(ok, "run_hooks returns True when all lines succeed")

    # ── Empty list is a no-op ─────────────────────────────────────────────────
    ok2 = run_hooks([], label="SETUP", hunt_dir=tmp_dir)
    _assert(ok2, "run_hooks([]) returns True (no-op)")

    # ── Stops on first failure ────────────────────────────────────────────────
    steps = [
        "CALL PYTHON multi_helper.step_a",
        "CALL PYTHON multi_helper.step_fail",
        "CALL PYTHON multi_helper.step_b",  # must NOT be reached
    ]
    ok3 = run_hooks(steps, label="TEARDOWN", hunt_dir=tmp_dir)
    _assert(not ok3, "run_hooks returns False when a line fails")


def _test_run_hooks__shared_variables(tmp_dir: str) -> None:
    print("\n  ── run_hooks — shared variables across lifecycle lines ───")

    scripts_dir = Path(tmp_dir, "scripts")
    scripts_dir.mkdir(parents=True, exist_ok=True)
    _make_helper(str(scripts_dir), "auth.py", """\
        def get_admin_token():
            return "token-xyz"
    """)
    _make_helper(str(scripts_dir), "seed.py", """\
        def create_user():
            return {"random_id": "9001", "username": "manul_tester_9001"}
    """)

    variables: dict[str, str] = {}
    ok = run_hooks(
        [
            "CALL PYTHON auth.get_admin_token into {auth_token}",
            'PRINT "Authenticated with token: {auth_token}"',
            "CALL PYTHON seed.create_user",
            'PRINT "Cleanup complete for {random_id}"',
        ],
        label="SETUP",
        hunt_dir=tmp_dir,
        variables=variables,
    )
    _assert(ok, "run_hooks succeeds with shared variables across lines")
    _assert(variables.get("auth_token") == "token-xyz", "scalar into binding persisted in shared variables")
    _assert(variables.get("random_id") == "9001", "dict return key persisted in shared variables")
    _assert(variables.get("username") == "manul_tester_9001", "dict return username persisted in shared variables")


# ── Suite entry point ─────────────────────────────────────────────────────────

async def run_suite() -> bool:
    """Run all hooks unit tests.  No browser or network required."""
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n🧪 HOOKS — Unit tests (no browser)")

    with tempfile.TemporaryDirectory(prefix="manul_hooks_test_") as tmp_dir:
        _test_extract_hook_blocks()
        _test_execute_hook_line__syntax()
        _test_execute_hook_line__module_not_found()
        _test_execute_hook_line__success(tmp_dir)
        _test_execute_hook_line__print_and_dict_context(tmp_dir)
        _test_execute_hook_line__scripts_folder_and_with_args(tmp_dir)
        _test_execute_hook_line__function_not_found(tmp_dir)
        _test_execute_hook_line__not_callable(tmp_dir)
        _test_execute_hook_line__runtime_error(tmp_dir)
        _test_execute_hook_line__async_rejected(tmp_dir)
        _test_execute_hook_line__state_isolation(tmp_dir)
        _test_run_hooks(tmp_dir)
        _test_run_hooks__shared_variables(tmp_dir)

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total} passed")
    return _FAIL == 0


if __name__ == "__main__":
    asyncio.run(run_suite())
