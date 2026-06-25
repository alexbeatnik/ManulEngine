# manul_engine/controls.py
"""
Custom Controls registry for ManulEngine.

Maps ``(page_name, target_element)`` pairs to user Python handlers, bypassing
the heuristic / AI element resolver for that one target on that one page.
``page_name`` is the human-readable label returned by ``lookup_page_name()``
— i.e. whatever you mapped in the per-site fragments under ``<project>/pages/``.

Quickstart — drop a file under ``controls/`` in your project root::

    # controls/login.py
    from manul_engine import custom_control, ControlContext

    @custom_control(page="Login Page", target="Username")
    async def handle_username(ctx: ControlContext) -> None:
        # ctx.page is a live Playwright Page.
        el = await ctx.page.query("#user")
        await el.fill(ctx.value or "")

The handler receives a single :class:`ControlContext` argument with these
attributes:

  ``page``       — live Playwright ``Page`` (always present, never ``None``).
  ``action``     — detected DSL mode: ``"input"``, ``"clickable"``, ``"select"``,
                   ``"hover"``, ``"drag"``, ``"locate"``.
  ``value``      — type/select value (``None`` for click/hover/locate).
  ``target``     — the quoted target string from the DSL step (e.g. ``"Username"``).
  ``page_name``  — the resolved page label that matched the registration.
  ``url``        — ``page.url`` snapshot at dispatch time.
  ``step``       — the original step text (with variable substitution applied).

Both sync and async handlers are supported; the engine awaits async ones.

**Breaking change in 0.0.9.30:** the legacy 3-arg signature
``(page, action_type, value)`` is removed. All custom controls must now use
the single-``ControlContext`` form.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .cdp import CDPPage as Page


# ── Public context object passed to every handler ────────────────────────────
@dataclass(slots=True)
class ControlContext:
    """Single argument passed to every ``@custom_control`` handler.

    Attributes:
        page:      Live Playwright ``Page``. Use it like any Playwright page —
                   ``await page.query(...)``, ``page.evaluate(...)``, etc.
        action:    DSL mode — one of ``"input"``, ``"clickable"``, ``"select"``,
                   ``"hover"``, ``"drag"``, ``"locate"``.
        value:     Type/select value (``None`` for click/hover/locate).
        target:    The quoted target string from the step (e.g. ``"Username"``).
        page_name: The resolved page label — matches ``page=`` on the decorator.
        url:       ``page.url`` snapshot at dispatch.
        step:      Original step text (with ``{variables}`` substituted).
    """

    page: Page
    action: str
    value: str | None
    target: str
    page_name: str
    url: str
    step: str


# ── Global registry ──────────────────────────────────────────────────────────
# key: (page_name_lower, target_name_lower) → handler callable
_CUSTOM_CONTROLS: dict[tuple[str, str], Callable[[ControlContext], Any]] = {}
_REGISTRY_META: dict[tuple[str, str], dict[str, str]] = {}  # diagnostics
_REGISTRY_LOCK = threading.Lock()

# Eagerly-loaded directories (process-wide idempotency).
_LOADED_DIRS: set[str] = set()
# Per-file idempotency: tracks individual files that have been imported.
_LOADED_FILES: set[str] = set()


def custom_control(page: str, target: str) -> Callable:
    """Register a function as a custom control handler.

    Args:
        page:   The page name as returned by ``lookup_page_name()``
                (case-insensitive). Must match a label in your ``pages/`` fragments.
        target: The quoted target element name from the ``.hunt`` step
                (case-insensitive).

    The decorated function must accept a single :class:`ControlContext`
    argument. Both sync and async are supported. Example::

        @custom_control(page="Login Page", target="Username")
        async def handle_username(ctx: ControlContext) -> None:
            el = await ctx.page.query("#user")
        await el.fill(ctx.value or "")
    """
    page_key = page.strip().lower()
    target_key = target.strip().lower()

    def decorator(func: Callable[[ControlContext], Any]) -> Callable[[ControlContext], Any]:
        _validate_handler_signature(func, page=page, target=target)
        key = (page_key, target_key)
        with _REGISTRY_LOCK:
            _CUSTOM_CONTROLS[key] = func
            _REGISTRY_META[key] = {
                "page": page,
                "target": target,
                "handler": getattr(func, "__qualname__", func.__name__),
                "source": getattr(inspect.getmodule(func), "__file__", "<unknown>") or "<unknown>",
            }
        return func

    return decorator


def _validate_handler_signature(func: Callable, *, page: str, target: str) -> None:
    """Reject handlers using the legacy 3-arg signature with a clear error."""
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return  # builtins / C-extensions — give them the benefit of the doubt
    params = [
        p
        for p in sig.parameters.values()
        if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]
    if len(params) == 1:
        return
    raise TypeError(
        f"@custom_control(page={page!r}, target={target!r}): handler "
        f"{func.__qualname__!r} must accept exactly one ControlContext argument. "
        f"The legacy 3-arg signature (page, action_type, value) was removed in 0.0.9.30. "
        f"Migration: `async def fn(ctx): el = await ctx.page.query(...); await el.fill(ctx.value or '')`."
    )


def get_custom_control(page_name: str, target_name: str) -> Callable[[ControlContext], Any] | None:
    """Return the registered handler for ``(page_name, target_name)``, or ``None``."""
    key = (page_name.strip().lower(), target_name.strip().lower())
    with _REGISTRY_LOCK:
        return _CUSTOM_CONTROLS.get(key)


def diagnose_custom_control_miss(page_name: str, target_name: str) -> str | None:
    """Return a one-line hint when a target has a control on a *different* page.

    The most common authoring mistake is mismatched ``page=`` vs. the label
    in the ``pages/`` fragments. When a step's target has a registered handler
    under some *other* page name, surface that to the user instead of silently
    falling through to heuristic resolution.

    Returns ``None`` when there is no near-match (heuristic resolution is
    the right thing to do).
    """
    target_key = target_name.strip().lower()
    if not target_key:
        return None
    current = page_name.strip().lower()
    with _REGISTRY_LOCK:
        sibling_pages = sorted(
            {
                meta["page"]
                for (p_key, t_key), meta in _REGISTRY_META.items()
                if t_key == target_key and p_key != current
            }
        )
    if not sibling_pages:
        return None
    pretty = ", ".join(f"'{p}'" for p in sibling_pages)
    return (
        f"⚠️  CUSTOM CONTROL MISS — target '{target_name}' is registered for {pretty} "
        f"but the current page resolves to '{page_name}'. "
        f"Fix: align @custom_control(page=…) with the matching pages/*.json fragment, "
        f"or update that fragment."
    )


def list_custom_controls() -> list[dict[str, str]]:
    """Return all registered handlers as ``[{page, target, handler, source}, …]``.

    Sorted by page then target. Useful for ``manul controls list`` and for
    introspection in test setup. Empty list when nothing is registered.
    """
    with _REGISTRY_LOCK:
        rows = list(_REGISTRY_META.values())
    return sorted(rows, key=lambda r: (r["page"].lower(), r["target"].lower()))


def _iter_custom_control_targets(source: str) -> list[str]:
    """Return target names declared in @custom_control decorators.

    Supports both keyword form::

        @custom_control(page="Booking Page", target="React Datepicker")

    and positional form::

        @custom_control("Booking Page", "React Datepicker")
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    targets: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            is_custom_control = (isinstance(func, ast.Name) and func.id == "custom_control") or (
                isinstance(func, ast.Attribute) and func.attr == "custom_control"
            )
            if not is_custom_control:
                continue

            target_value: str | None = None
            for keyword in decorator.keywords:
                if keyword.arg == "target" and isinstance(keyword.value, ast.Constant):
                    if isinstance(keyword.value.value, str):
                        target_value = keyword.value.value
                        break

            if target_value is None and len(decorator.args) >= 2:
                positional_target = decorator.args[1]
                if isinstance(positional_target, ast.Constant) and isinstance(positional_target.value, str):
                    target_value = positional_target.value

            if target_value:
                targets.append(target_value)
    return targets


def extract_required_controls(
    mission_text: str,
    workspace_dir: str,
    custom_modules_dirs: list[str] | None = None,
) -> set[str]:
    """Pre-flight scan: identify which custom module ``.py`` files are needed.

    Parses the mission text for quoted target strings, then scans each
    ``.py`` file in every directory listed in *custom_modules_dirs* at the
    **source level** (no import) for ``@custom_control(...)`` decorators
    whose target matches any quoted token from the hunt steps.

    Returns a set of **relative paths** (e.g. ``{"controls/booking.py",
    "rest/api_client.py"}``) so the loader knows both directory and filename.
    Returns an empty set when no directories exist or no matches are found.

    Args:
        mission_text: Raw mission body from the ``.hunt`` file.
        workspace_dir: Absolute path to the user's project root (typically CWD).
        custom_modules_dirs: Directory names to scan.  Defaults to ``["controls"]``.
    """
    dirs = custom_modules_dirs or ["controls"]
    ws = Path(workspace_dir).resolve()

    # Collect all quoted target strings from the mission steps (lowered).
    step_targets: set[str] = set()
    for match in re.finditer(r'"([^"]+)"|' r"'([^']+)'", mission_text):
        token = (match.group(1) or match.group(2)).strip().lower()
        if token:
            step_targets.add(token)

    if not step_targets:
        return set()

    needed: set[str] = set()
    for dir_name in dirs:
        controls_dir = ws / dir_name
        if not controls_dir.is_dir():
            continue
        for py_file in sorted(controls_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for declared_target_raw in _iter_custom_control_targets(source):
                declared_target = declared_target_raw.strip().lower()
                if declared_target in step_targets:
                    needed.add(f"{dir_name}/{py_file.name}")
                    break  # one match is enough to mark this file
    return needed


def load_custom_controls(
    workspace_dir: str,
    required_modules: set[str] | None = None,
    custom_modules_dirs: list[str] | None = None,
) -> None:
    """Import custom control modules from workspace directories.

    Scans all directories listed in *custom_modules_dirs* (default:
    ``["controls"]``) for ``.py`` files and imports them so that
    ``@custom_control`` decorators register into the global registry.

    **Lazy mode (recommended):** pass *required_modules* — a set of
    relative paths (e.g. ``{"controls/checkout.py"}``) obtained from
    :func:`extract_required_controls`.  Only those files are imported.

    **Eager mode (backward compat):** omit *required_modules*. All ``.py``
    files (excluding ``_``-prefixed) in every directory are imported.

    Idempotent per file: each source file is imported at most once per
    process, regardless of how many ``ManulEngine`` instances are created.

    Directories that do not exist are silently skipped.

    Args:
        workspace_dir: Absolute path to the user's project root (typically CWD).
        required_modules: Optional set of relative paths to load.  When ``None``,
            every non-underscore ``.py`` file in each directory is loaded
            (eager mode).
        custom_modules_dirs: Directory names to scan.  Defaults to ``["controls"]``.
    """
    dirs = custom_modules_dirs or ["controls"]
    resolved = str(Path(workspace_dir).resolve())
    ws = Path(resolved)

    for dir_name in dirs:
        modules_dir = (ws / dir_name).resolve()
        if not modules_dir.is_dir():
            continue
        try:
            modules_dir.relative_to(ws)
        except ValueError:
            # Directory is outside the workspace; skip for safety.
            continue

        if required_modules is not None:
            # Targeted (lazy) loading — only import specifically requested files
            # that belong to this directory.
            candidates: list[Path] = []
            for rel in sorted(required_modules):
                rel_path = PurePosixPath(rel)
                try:
                    sub_path = rel_path.relative_to(dir_name)
                except ValueError:
                    continue
                candidates.append(modules_dir.joinpath(*sub_path.parts))
            # Backward compat: accept bare filenames for the "controls" directory.
            if dir_name == "controls":
                candidates += [modules_dir / rel for rel in sorted(required_modules) if "/" not in rel]
        else:
            # Eager loading (legacy) — skip entirely if this dir was already loaded.
            dir_key = f"{resolved}/{dir_name}"
            if dir_key in _LOADED_DIRS:
                continue
            candidates = sorted(modules_dir.glob("*.py"))
            # Mark directory as fully loaded so repeated eager calls are no-ops.
            _LOADED_DIRS.add(dir_key)

        for py_file in candidates:
            if not py_file.is_file() or py_file.name.startswith("_"):
                continue
            # Per-file idempotency: skip files already imported in this process.
            file_key = str(py_file.resolve())
            if file_key in _LOADED_FILES:
                continue
            try:
                safe_dir = re.sub(r"[^0-9A-Za-z_]", "_", str(dir_name))
                safe_stem = re.sub(r"[^0-9A-Za-z_]", "_", py_file.stem)
                mod_name = f"_manul_custom_{safe_dir}_{safe_stem}"
                spec = importlib.util.spec_from_file_location(mod_name, py_file)
                if spec is None or spec.loader is None:
                    continue
                fresh_module = importlib.util.module_from_spec(spec)
                fresh_module.__file__ = str(py_file)
                spec.loader.exec_module(fresh_module)  # type: ignore[union-attr]
                _LOADED_FILES.add(file_key)
                print(f"    [⚙️ JIT LOAD] @custom_control: {dir_name}/{py_file.name}")
            except Exception as exc:
                print(f"    ⚠️  Failed to load '{dir_name}/{py_file.name}': {exc}")
