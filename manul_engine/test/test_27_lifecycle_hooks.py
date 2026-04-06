# manul_engine/test/test_27_lifecycle_hooks.py
"""
Unit-test suite for the Global Lifecycle Hook system.

No browser or network required.  All tests run against synthetic state.

Tests:
  1.  Decorator registration — all four hooks populate the registry correctly.
  2.  Async rejection — async callables are rejected at decoration time.
  3.  run_before_all — executes hooks; propagates ctx.variables; aborts on fail.
  4.  run_after_all  — runs all entries even when one raises.
  5.  run_before_group / run_after_group — tag-matching semantics.
  6.  Failure semantics — before_all fail aborts suite; before_group fail skips
                          mission; after hooks always run.
  7.  GlobalContext — variables / metadata defaults; variable mutation visible
                      across multiple hooks.
  8.  is_empty / clear — introspection and reset.
  9.  load_hooks_file — finds and executes manul_hooks.py in isolation (uses a
                         real temp file); absent file returns False.
  10. serialize / deserialize — round-trip through MANUL_GLOBAL_VARS env var.
  11. _run_hunt_file signature — accepts global_vars kwarg.
  12. __init__.py re-exports — public API accessible from manul_engine top level.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python run_tests.py``) and must remain async.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import tempfile
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.lifecycle import (
    GlobalContext,
    _HookRegistry,
    before_all,
    after_all,
    before_group,
    after_group,
    load_hooks_file,
    serialize_global_vars,
    deserialize_global_vars,
    registry,
    _ENV_KEY,
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
        suffix = f" ({detail})" if detail else ""
        print(f"    ❌  {name}{suffix}")


def _fresh_registry() -> _HookRegistry:
    """Return a brand-new, empty _HookRegistry (isolates each test section)."""
    return _HookRegistry()


# ── Section 1: Decorator registration ────────────────────────────────────────

def _test_registration() -> None:
    print("\n  ── Decorator registration ─────────────────────────────────")
    reg = _fresh_registry()

    calls: list[str] = []

    def ba(ctx: GlobalContext) -> None:
        calls.append("before_all")

    def aa(ctx: GlobalContext) -> None:
        calls.append("after_all")

    def bg(ctx: GlobalContext) -> None:
        calls.append("before_group:smoke")

    def ag(ctx: GlobalContext) -> None:
        calls.append("after_group:smoke")

    reg.register_before_all(ba)
    reg.register_after_all(aa)
    reg.register_before_group("smoke")(bg)
    reg.register_after_group("smoke")(ag)

    _assert(not reg.is_empty, "registry.is_empty is False after registration")
    _assert(len(reg._before_all) == 1, "one before_all entry registered")
    _assert(len(reg._after_all) == 1, "one after_all entry registered")
    _assert(len(reg._before_group) == 1, "one before_group entry registered")
    _assert(len(reg._after_group) == 1, "one after_group entry registered")
    _assert(reg._before_group[0].tag == "smoke", "before_group tag stored lowercase")
    _assert(reg._after_group[0].tag == "smoke", "after_group tag stored lowercase")

    # Decorators must return the original function unchanged.
    _assert(reg.register_before_all(ba) is ba, "register_before_all returns fn")
    _assert(reg.register_after_all(aa) is aa, "register_after_all returns fn")


# ── Section 2: Async rejection ────────────────────────────────────────────────

def _test_async_rejection() -> None:
    print("\n  ── Async rejection ────────────────────────────────────────")
    reg = _fresh_registry()

    async def async_fn(ctx: GlobalContext) -> None:
        pass

    rejected = [False, False, False, False]
    for i, call in enumerate([
        lambda: reg.register_before_all(async_fn),
        lambda: reg.register_after_all(async_fn),
        lambda: reg.register_before_group("smoke")(async_fn),
        lambda: reg.register_after_group("smoke")(async_fn),
    ]):
        try:
            call()
        except TypeError:
            rejected[i] = True

    _assert(rejected[0], "register_before_all rejects async fn")
    _assert(rejected[1], "register_after_all rejects async fn")
    _assert(rejected[2], "register_before_group rejects async fn")
    _assert(rejected[3], "register_after_group rejects async fn")


# ── Section 3: run_before_all ─────────────────────────────────────────────────

def _test_run_before_all() -> None:
    print("\n  ── run_before_all ─────────────────────────────────────────")
    reg = _fresh_registry()
    ctx = GlobalContext()

    order: list[str] = []

    def first(c: GlobalContext) -> None:
        c.variables["step"] = "first"
        order.append("first")

    def second(c: GlobalContext) -> None:
        c.variables["step"] = "second"
        order.append("second")

    reg.register_before_all(first)
    reg.register_before_all(second)

    result = reg.run_before_all(ctx)

    _assert(result is True, "run_before_all returns True on success")
    _assert(order == ["first", "second"], "hooks run in registration order")
    _assert(ctx.variables.get("step") == "second", "ctx.variables mutated by hook")

    # Failure: first hook raises; second must NOT run; returns False.
    reg2 = _fresh_registry()
    ran: list[str] = []

    def fail_hook(c: GlobalContext) -> None:
        raise RuntimeError("DB down")

    def should_not_run(c: GlobalContext) -> None:
        ran.append("second")

    reg2.register_before_all(fail_hook)
    reg2.register_before_all(should_not_run)
    ctx2 = GlobalContext()
    result2 = reg2.run_before_all(ctx2)

    _assert(result2 is False, "run_before_all returns False on failure")
    _assert(ran == [], "second before_all hook NOT called after failure (abort-on-first-fail)")


# ── Section 4: run_after_all ──────────────────────────────────────────────────

def _test_run_after_all() -> None:
    print("\n  ── run_after_all ──────────────────────────────────────────")
    reg = _fresh_registry()
    ran: list[str] = []

    def a1(ctx: GlobalContext) -> None:
        raise RuntimeError("cleanup fail")

    def a2(ctx: GlobalContext) -> None:
        ran.append("a2")

    reg.register_after_all(a1)
    reg.register_after_all(a2)

    # after_all must run all entries even if one fails.
    ctx = GlobalContext()
    reg.run_after_all(ctx)

    _assert("a2" in ran, "after_all continues past individual failures (is_cleanup=True)")


# ── Section 5: run_before_group / run_after_group tag matching ────────────────

def _test_group_tag_matching() -> None:
    print("\n  ── before_group / after_group tag matching ────────────────")
    reg = _fresh_registry()
    fired: list[str] = []

    def smoke_hook(ctx: GlobalContext) -> None:
        fired.append("smoke")

    def regression_hook(ctx: GlobalContext) -> None:
        fired.append("regression")

    reg.register_before_group("smoke")(smoke_hook)
    reg.register_before_group("regression")(regression_hook)

    ctx = GlobalContext()

    fired.clear()
    reg.run_before_group(["smoke"], ctx)
    _assert(fired == ["smoke"], "only smoke hook fires for ['smoke']")

    fired.clear()
    reg.run_before_group(["regression"], ctx)
    _assert(fired == ["regression"], "only regression hook fires for ['regression']")

    fired.clear()
    reg.run_before_group(["smoke", "regression"], ctx)
    _assert(set(fired) == {"smoke", "regression"}, "both hooks fire when both tags present")

    fired.clear()
    reg.run_before_group([], ctx)
    _assert(fired == [], "no hooks fire for empty tag list")

    fired.clear()
    reg.run_before_group(["unrelated"], ctx)
    _assert(fired == [], "no hooks fire for non-matching tags")

    # Tag matching must be case-insensitive.
    reg2 = _fresh_registry()
    ci_fired: list[str] = []

    def ci_hook(ctx: GlobalContext) -> None:
        ci_fired.append("ci")

    reg2.register_before_group("Smoke")(ci_hook)
    reg2.run_before_group(["SMOKE"], ctx)
    _assert(ci_fired == ["ci"], "tag matching is case-insensitive")


# ── Section 6: GlobalContext variable propagation ─────────────────────────────

def _test_global_context() -> None:
    print("\n  ── GlobalContext variable propagation ─────────────────────")
    ctx = GlobalContext()

    _assert(isinstance(ctx.variables, dict), "ctx.variables is a dict")
    _assert(isinstance(ctx.metadata, dict), "ctx.metadata is a dict")
    _assert(ctx.variables == {}, "ctx.variables starts empty")
    _assert(ctx.metadata == {}, "ctx.metadata starts empty")

    # Variables accumulate across multiple hooks.
    reg = _fresh_registry()

    def h1(c: GlobalContext) -> None:
        c.variables["base_url"] = "https://staging.manul.ai"

    def h2(c: GlobalContext) -> None:
        c.variables["api_key"] = "tok_abc123"

    reg.register_before_all(h1)
    reg.register_before_all(h2)
    reg.run_before_all(ctx)

    _assert(ctx.variables.get("base_url") == "https://staging.manul.ai", "variable set by first hook")
    _assert(ctx.variables.get("api_key") == "tok_abc123", "variable set by second hook")


# ── Section 7: is_empty / clear ───────────────────────────────────────────────

def _test_is_empty_and_clear() -> None:
    print("\n  ── is_empty / clear ───────────────────────────────────────")
    reg = _fresh_registry()
    _assert(reg.is_empty, "fresh registry is_empty == True")

    def noop(ctx: GlobalContext) -> None:
        pass

    reg.register_before_all(noop)
    _assert(not reg.is_empty, "is_empty == False after registration")

    reg.clear()
    _assert(reg.is_empty, "is_empty == True after clear()")
    _assert(reg._before_all == [], "before_all list empty after clear")
    _assert(reg._after_all == [], "after_all list empty after clear")
    _assert(reg._before_group == [], "before_group list empty after clear")
    _assert(reg._after_group == [], "after_group list empty after clear")


# ── Section 8: load_hooks_file ────────────────────────────────────────────────

def _test_load_hooks_file() -> None:
    print("\n  ── load_hooks_file ────────────────────────────────────────")

    # Absent manul_hooks.py → returns False without raising.
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_hooks_file(tmpdir)
        _assert(result is False, "load_hooks_file returns False when file absent")

    # Present manul_hooks.py → returns True; decorators register into the
    # module-level registry singleton (side effect of executing the file).
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_src = textwrap.dedent("""\
            from manul_engine.lifecycle import before_all, GlobalContext, registry

            @before_all
            def suite_setup(ctx: GlobalContext) -> None:
                ctx.variables["loaded"] = "yes"
        """)
        hooks_path = os.path.join(tmpdir, "manul_hooks.py")
        with open(hooks_path, "w") as fh:
            fh.write(hooks_src)

        # Use a clean registry so previous tests don't interfere.
        # load_hooks_file() mutates the module-level `registry` singleton.
        registry.clear()
        result = load_hooks_file(tmpdir)
        _assert(result is True, "load_hooks_file returns True when file found")
        _assert(not registry.is_empty, "decorators in manul_hooks.py populate registry")

        # Run the loaded hook to verify it works end-to-end.
        ctx = GlobalContext()
        registry.run_before_all(ctx)
        _assert(ctx.variables.get("loaded") == "yes", "hook loaded from file executes correctly")

    # Syntax error inside manul_hooks.py → exception propagates to caller.
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_src = "this is not valid python !!!"
        with open(os.path.join(tmpdir, "manul_hooks.py"), "w") as fh:
            fh.write(bad_src)
        raised = False
        try:
            load_hooks_file(tmpdir)
        except SyntaxError:
            raised = True
        _assert(raised, "load_hooks_file propagates SyntaxError from bad manul_hooks.py")

    # Clean up global registry after this section.
    registry.clear()


# ── Section 9: serialize / deserialize ───────────────────────────────────────

def _test_serialize_deserialize() -> None:
    print("\n  ── serialize / deserialize ────────────────────────────────")

    # Round-trip through the MANUL_GLOBAL_VARS env var.
    ctx = GlobalContext(variables={"TOKEN": "abc123", "ENV": "staging"})
    serialised = serialize_global_vars(ctx)
    _assert(isinstance(serialised, str), "serialize_global_vars returns str")

    # Inject into environment and deserialise.
    os.environ[_ENV_KEY] = serialised
    try:
        recovered = deserialize_global_vars()
        _assert(recovered == {"TOKEN": "abc123", "ENV": "staging"}, "round-trip preserves all vars")
    finally:
        del os.environ[_ENV_KEY]

    # Absent env var → empty dict.
    os.environ.pop(_ENV_KEY, None)
    _assert(deserialize_global_vars() == {}, "absent env var returns empty dict")

    # Malformed JSON → graceful empty dict (no exception).
    os.environ[_ENV_KEY] = "not-json-at-all"
    try:
        result = deserialize_global_vars()
        _assert(result == {}, "malformed env var returns empty dict without raising")
    finally:
        os.environ.pop(_ENV_KEY, None)

    # Non-dict JSON (e.g. a list) → empty dict.
    os.environ[_ENV_KEY] = json.dumps(["a", "b"])
    try:
        result = deserialize_global_vars()
        _assert(result == {}, "non-dict JSON returns empty dict")
    finally:
        os.environ.pop(_ENV_KEY, None)

    # Empty string env var → empty dict.
    os.environ[_ENV_KEY] = ""
    try:
        result = deserialize_global_vars()
        _assert(result == {}, "empty string env var returns empty dict")
    finally:
        os.environ.pop(_ENV_KEY, None)


# ── Section 10: _run_hunt_file accepts global_vars ────────────────────────────

def _test_run_hunt_file_signature() -> None:
    print("\n  ── _run_hunt_file signature accepts global_vars ───────────")
    from manul_engine.cli import _run_hunt_file
    sig = inspect.signature(_run_hunt_file)
    _assert("global_vars" in sig.parameters, "_run_hunt_file has global_vars parameter")
    param = sig.parameters["global_vars"]
    _assert(param.default is None, "global_vars defaults to None")


# ── Section 11: __init__.py public re-exports ─────────────────────────────────

def _test_public_exports() -> None:
    print("\n  ── manul_engine public re-exports ─────────────────────────")
    import manul_engine as me
    _assert(hasattr(me, "GlobalContext"), "GlobalContext in manul_engine namespace")
    _assert(hasattr(me, "before_all"), "before_all in manul_engine namespace")
    _assert(hasattr(me, "after_all"), "after_all in manul_engine namespace")
    _assert(hasattr(me, "before_group"), "before_group in manul_engine namespace")
    _assert(hasattr(me, "after_group"), "after_group in manul_engine namespace")
    _assert(me.GlobalContext is GlobalContext, "GlobalContext is the same class object")


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n🐾 test_27 — Global Lifecycle Hooks")

    # Ensure we start with a clean global registry before all tests.
    registry.clear()

    _test_registration()
    _test_async_rejection()
    _test_run_before_all()
    _test_run_after_all()
    _test_group_tag_matching()
    _test_global_context()
    _test_is_empty_and_clear()
    _test_load_hooks_file()
    _test_serialize_deserialize()
    _test_run_hunt_file_signature()
    _test_public_exports()

    # Final clean-up of module-level registry.
    registry.clear()

    total = _PASS + _FAIL
    print(f"\n  SCORE: {_PASS}/{total}")
    if _FAIL:
        print(f"  ❌  {_FAIL} assertion(s) failed")

    return _FAIL == 0


if __name__ == "__main__":
    asyncio.run(run_suite())
