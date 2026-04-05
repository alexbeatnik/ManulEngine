# manul_engine/lifecycle.py
"""
Global Lifecycle Hook Registry for ManulEngine.

Provides four decorator-based hooks that bracket the CLI execution lifecycle:

    @before_all          — runs once before the entire suite starts
    @after_all           — runs once after all missions finish (always)
    @before_group(tag=)  — runs before each mission whose @tags: includes tag
    @after_group(tag=)   — runs after  each mission whose @tags: includes tag

Quick-start
-----------
Create ``manul_hooks.py`` in the same directory as your ``.hunt`` files::

    from manul_engine import before_all, after_all, before_group, after_group, GlobalContext

    @before_all
    def global_setup(ctx: GlobalContext) -> None:
        ctx.variables["BASE_URL"] = "https://staging.example.com"
        ctx.variables["API_TOKEN"] = fetch_token_from_vault()

    @after_all
    def global_teardown(ctx: GlobalContext) -> None:
        db.rollback_all_test_data()

    @before_group(tag="smoke")
    def seed_smoke(ctx: GlobalContext) -> None:
        ctx.variables["ORDER_ID"] = db.create_temp_order()

    @after_group(tag="smoke")
    def clean_smoke(ctx: GlobalContext) -> None:
        db.delete_order(ctx.variables.get("ORDER_ID"))

Variable propagation
--------------------
Variables written to ``ctx.variables`` in any lifecycle hook are injected into
every matching hunt file as ``initial_vars``—the same mechanism used by
``@var:`` headers.  They are available for ``{placeholder}`` interpolation in
any step::

    # inside a .hunt file
    STEP Login:
        NAVIGATE to '{BASE_URL}/login'
        Fill 'API Token' with '{API_TOKEN}'

Failure semantics
-----------------
- ``@before_all`` failure  → entire run is aborted; ``@after_all`` still fires.
- ``@before_group`` failure → that mission is skipped; ``@after_group`` still fires.
- ``@after_all`` / ``@after_group`` failures are logged but never override
  the mission or suite result.

Parallel workers
----------------
When ``--workers N`` is used, ``before_all`` runs in the orchestrator process
and its ``ctx.variables`` are serialised as JSON into the ``MANUL_GLOBAL_VARS``
environment variable before worker subprocesses are spawned.  Each worker
deserialises them at startup so ``{placeholders}`` resolve correctly.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# ── Shared context object ─────────────────────────────────────────────────────

@dataclass
class GlobalContext:
    """Mutable state shared between all lifecycle hooks and every hunt mission.

    Attributes:
        variables:  String key/value pairs propagated into every hunt file as
                    ``initial_vars``, available for ``{placeholder}``
                    interpolation.  Values are always coerced to ``str``.
        metadata:   Arbitrary per-hook scratch space.  Not propagated to the
                    hunt engine; hook-to-hook communication only.
    """
    variables: dict[str, str] = field(default_factory=dict)
    metadata:  dict[str, object] = field(default_factory=dict)


# ── Internal registry helpers ─────────────────────────────────────────────────

@dataclass
class _HookEntry:
    fn:  Callable
    tag: str | None   # None  → before_all / after_all
                       # str   → before_group / after_group (lower-cased)


class _HookRegistry:
    """Singleton that collects all registered lifecycle hooks.

    Populated at import-time via decorators; consumed by the CLI runner.
    Thread-safety is not required: the CLI is single-process during
    registration, and hooks always execute sequentially in the main loop.
    """

    def __init__(self) -> None:
        self._before_all:   list[_HookEntry] = []
        self._after_all:    list[_HookEntry] = []
        self._before_group: list[_HookEntry] = []
        self._after_group:  list[_HookEntry] = []

    # ── Registration ──────────────────────────────────────────────────────────

    def register_before_all(self, fn: Callable) -> Callable:
        _reject_async(fn)
        self._before_all.append(_HookEntry(fn=fn, tag=None))
        return fn

    def register_after_all(self, fn: Callable) -> Callable:
        _reject_async(fn)
        self._after_all.append(_HookEntry(fn=fn, tag=None))
        return fn

    def register_before_group(self, tag: str) -> Callable[[Callable], Callable]:
        def _decorator(fn: Callable) -> Callable:
            _reject_async(fn)
            self._before_group.append(_HookEntry(fn=fn, tag=tag.lower()))
            return fn
        return _decorator

    def register_after_group(self, tag: str) -> Callable[[Callable], Callable]:
        def _decorator(fn: Callable) -> Callable:
            _reject_async(fn)
            self._after_group.append(_HookEntry(fn=fn, tag=tag.lower()))
            return fn
        return _decorator

    # ── Execution ─────────────────────────────────────────────────────────────

    def run_before_all(self, ctx: GlobalContext) -> bool:
        """Execute all @before_all hooks. Returns False on first failure."""
        return _run_entries(self._before_all, ctx, label="before_all")

    def run_after_all(self, ctx: GlobalContext) -> None:
        """Execute all @after_all hooks. Runs all entries regardless of errors."""
        _run_entries(self._after_all, ctx, label="after_all", is_cleanup=True)

    def run_before_group(self, tags: list[str], ctx: GlobalContext) -> bool:
        """Execute @before_group hooks whose tag matches any of *tags*."""
        return _run_entries(_matching(self._before_group, tags), ctx, label="before_group")

    def run_after_group(self, tags: list[str], ctx: GlobalContext) -> None:
        """Execute @after_group hooks whose tag matches any of *tags*."""
        _run_entries(_matching(self._after_group, tags), ctx, label="after_group", is_cleanup=True)

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def is_empty(self) -> bool:
        return not (self._before_all or self._after_all
                    or self._before_group or self._after_group)

    def clear(self) -> None:
        """Reset all registrations. Used between isolated test runs."""
        self._before_all.clear()
        self._after_all.clear()
        self._before_group.clear()
        self._after_group.clear()


# ── Module-level singleton ────────────────────────────────────────────────────

registry = _HookRegistry()


# ── Public decorators (re-exported via __init__.py) ───────────────────────────

def before_all(fn: Callable) -> Callable:
    """Decorator: register *fn(ctx)* to run once before the entire suite."""
    return registry.register_before_all(fn)


def after_all(fn: Callable) -> Callable:
    """Decorator: register *fn(ctx)* to run once after all missions finish."""
    return registry.register_after_all(fn)


def before_group(tag: str) -> Callable[[Callable], Callable]:
    """Decorator factory: register *fn(ctx)* to run before each mission
    whose ``@tags:`` header contains *tag*."""
    return registry.register_before_group(tag)


def after_group(tag: str) -> Callable[[Callable], Callable]:
    """Decorator factory: register *fn(ctx)* to run after each mission
    whose ``@tags:`` header contains *tag*."""
    return registry.register_after_group(tag)


# ── Auto-discovery ────────────────────────────────────────────────────────────

def load_hooks_file(directory: str) -> bool:
    """Silently attempt to import ``manul_hooks.py`` from *directory*.

    The file is executed in an isolated ``ModuleType`` (same sandboxing as
    ``[SETUP]``/``[TEARDOWN]`` hooks) so it does **not** pollute
    ``sys.modules``.  Decorators inside it mutate the module-level
    ``registry`` singleton, which persists for the process lifetime.

    Returns:
        ``True``  — file found and imported (may have registered 0 hooks).
        ``False`` — file not present (normal: no hooks configured).

    Raises:
        Any exception raised *inside* ``manul_hooks.py`` (import errors,
        bad decorator usage, etc.) is re-raised immediately so misconfigured
        hook files are always visible with a full traceback.
    """
    candidate = Path(directory) / "manul_hooks.py"
    if not candidate.is_file():
        return False

    spec = importlib.util.spec_from_file_location("manul_hooks", candidate)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return True


# ── ctx.variables  ↔  MANUL_GLOBAL_VARS env-var serialization ────────────────

_ENV_KEY = "MANUL_GLOBAL_VARS"


def serialize_global_vars(ctx: GlobalContext) -> str:
    """Serialise ``ctx.variables`` to a JSON string for ``MANUL_GLOBAL_VARS``."""
    return json.dumps({k: str(v) for k, v in ctx.variables.items()})


def deserialize_global_vars() -> dict[str, str]:
    """Read ``MANUL_GLOBAL_VARS`` from the environment and parse it.

    Returns an empty dict when the variable is absent or malformed.
    """
    raw = os.environ.get(_ENV_KEY, "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


# ── Internal utilities ────────────────────────────────────────────────────────

def _reject_async(fn: Callable) -> None:
    if asyncio.iscoroutinefunction(fn):
        raise TypeError(
            f"Lifecycle hook '{fn.__name__}' must be synchronous. "
            f"Async callables are not supported — wrap async code with "
            f"asyncio.run() inside your hook function if needed."
        )


def _matching(entries: list[_HookEntry], tags: list[str]) -> list[_HookEntry]:
    lower = {t.lower() for t in tags}
    return [e for e in entries if e.tag in lower]


def _run_entries(
    entries: list[_HookEntry],
    ctx: GlobalContext,
    label: str,
    is_cleanup: bool = False,
) -> bool:
    """Execute *entries* sequentially, passing *ctx* to each.

    Setup hooks (``is_cleanup=False``) abort on first failure and return
    ``False``.  Cleanup hooks (``is_cleanup=True``) always run all entries
    regardless of individual failures and return ``False`` only if at least
    one entry raised.
    """
    ok = True
    for entry in entries:
        try:
            entry.fn(ctx)
        except Exception:
            print(f"\n    ❌ [{label}] hook '{entry.fn.__name__}' raised an exception:")
            traceback.print_exc()
            ok = False
            if not is_cleanup:
                return False
    return ok
