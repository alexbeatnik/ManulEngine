# manul_engine/controls.py
"""
Custom Controls registry for ManulEngine.

Allows mapping specific (page_name, target_element) pairs to custom Python
functions, bypassing the standard heuristic/AI DOM resolution pipeline.
The page name is the human-readable name returned by ``lookup_page_name()``
(i.e. whatever is mapped in your ``pages.json``).

Usage — create a file in ``controls/`` under your project root:

.. code-block:: python

    # controls/my_datepicker.py
    from manul_engine.controls import custom_control

    @custom_control(page="Booking Page", target="Check-in Date")
    async def handle_checkin(page, action_type: str, value: str | None):
        await page.locator("#custom-calendar-input").fill(value or "")

The function receives:
  - ``page``        — the live Playwright ``Page`` object.
  - ``action_type`` — the detected mode string: ``"input"``, ``"clickable"``,
    ``"select"``, ``"hover"``, ``"drag"``, or ``"locate"``.
  - ``value``       — for ``input`` steps, the text to type (last quoted arg);
    ``None`` for all other modes.

Both sync and async handlers are supported.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

# ── Global registry ───────────────────────────────────────────────────────────
# key: (page_name_lower, target_name_lower) → handler callable
_CUSTOM_CONTROLS: dict[tuple[str, str], Callable] = {}

# Tracks which workspace dirs have already been loaded to prevent re-execution
# of control module top-level code when multiple ManulEngine instances are
# created in the same process (e.g. synthetic test suite).
_LOADED_DIRS: set[str] = set()


def custom_control(page: str, target: str) -> Callable:
    """Decorator that registers a function as a custom control handler.

    Both sync and async handlers are accepted; the engine awaits async ones.

    Args:
        page:   The page name as returned by ``lookup_page_name()`` (case-insensitive).
        target: The quoted target element name from the ``.hunt`` step (case-insensitive).

    Example::

        @custom_control(page="Login Page", target="Username")
        async def handle_username(page, action_type, value):
            await page.locator("#user").fill(value or "")
    """
    def decorator(func: Callable) -> Callable:
        key = (page.strip().lower(), target.strip().lower())
        _CUSTOM_CONTROLS[key] = func
        return func
    return decorator


def get_custom_control(page_name: str, target_name: str) -> Callable | None:
    """Return the registered handler for (page_name, target_name), or ``None``."""
    key = (page_name.strip().lower(), target_name.strip().lower())
    return _CUSTOM_CONTROLS.get(key)


def load_custom_controls(workspace_dir: str) -> None:
    """Dynamically import all ``.py`` files in ``<workspace_dir>/controls/``.

    Idempotent: if *workspace_dir* has already been loaded in this process,
    the call is a no-op.  This prevents repeated execution of module-level code
    (e.g. print statements, expensive imports) when multiple ``ManulEngine``
    instances are created in the same process.

    Each file is executed in an isolated module so that ``@custom_control``
    decorators register into the global ``_CUSTOM_CONTROLS`` dict.
    Files whose names start with ``_`` (e.g. ``__init__.py``) are skipped.
    Errors in individual files are printed but do not abort engine startup.

    Args:
        workspace_dir: Absolute path to the user's project root (typically CWD).
    """
    resolved = str(Path(workspace_dir).resolve())
    if resolved in _LOADED_DIRS:
        return
    _LOADED_DIRS.add(resolved)

    controls_dir = Path(resolved) / "controls"
    if not controls_dir.is_dir():
        return

    for py_file in sorted(controls_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            mod_name = f"_manul_custom_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(mod_name, py_file)
            if spec is None or spec.loader is None:
                continue
            fresh_module = importlib.util.module_from_spec(spec)
            fresh_module.__file__ = str(py_file)
            spec.loader.exec_module(fresh_module)  # type: ignore[union-attr]
            print(f"    🎛️  Custom controls loaded: {py_file.name}")
        except Exception as exc:
            print(f"    ⚠️  Custom controls: failed to load '{py_file.name}': {exc}")
