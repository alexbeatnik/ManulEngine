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
  - ``value``       — for ``"input"`` steps, the text to type (last quoted
    arg); for ``"select"`` steps, the option being selected (first quoted
    arg); for ``"drag"`` steps, the drop destination label (last quoted arg);
    ``None`` for ``"clickable"``, ``"hover"``, and ``"locate"`` modes.

Both sync and async handlers are supported.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Callable

# ── Global registry ───────────────────────────────────────────────────────────
# key: (page_name_lower, target_name_lower) → handler callable
_CUSTOM_CONTROLS: dict[tuple[str, str], Callable] = {}

# Tracks which workspace dirs have been fully (eagerly) loaded to prevent
# re-execution when multiple ManulEngine instances are created in the same
# process (e.g. synthetic test suite).
_LOADED_DIRS: set[str] = set()

# Per-file idempotency: tracks individual files that have been imported
# (by resolved absolute path).  Shared between eager and lazy modes so a
# file that was already lazily loaded is never re-imported by a later eager
# call, and vice versa.
_LOADED_FILES: set[str] = set()


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


# ── Pre-compiled regex for source-level target extraction ─────────────────────
# Matches @custom_control(page="...", target="...") with single or double quotes.
_RE_DECORATOR_TARGET = re.compile(
    r'@custom_control\s*\([^)]*target\s*=\s*["\']([^"\']+)["\']',
)


def extract_required_controls(
    mission_text: str,
    workspace_dir: str,
) -> set[str]:
    """Pre-flight scan: identify which ``controls/*.py`` files are needed.

    Parses the mission text for quoted target strings, then scans each
    ``.py`` file in ``<workspace_dir>/controls/`` at the **source level**
    (no import) for ``@custom_control(... target="...")`` decorators whose
    target matches any quoted token from the hunt steps.

    Returns a set of **filenames** (e.g. ``{"booking.py", "checkout.py"}``).
    Returns an empty set when no controls directory exists or no matches
    are found.
    """
    controls_dir = Path(workspace_dir).resolve() / "controls"
    if not controls_dir.is_dir():
        return set()

    # Collect all quoted target strings from the mission steps (lowered).
    step_targets: set[str] = set()
    for match in re.finditer(r'"([^"]+)"|'  r"'([^']+)'", mission_text):
        token = (match.group(1) or match.group(2)).strip().lower()
        if token:
            step_targets.add(token)

    if not step_targets:
        return set()

    needed: set[str] = set()
    for py_file in sorted(controls_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _RE_DECORATOR_TARGET.finditer(source):
            declared_target = m.group(1).strip().lower()
            if declared_target in step_targets:
                needed.add(py_file.name)
                break  # one match is enough to mark this file
    return needed


def load_custom_controls(
    workspace_dir: str,
    required_modules: "set[str] | None" = None,
) -> None:
    """Import custom control modules from ``<workspace_dir>/controls/``.

    **Lazy mode (recommended):** pass *required_modules* — a set of filenames
    (e.g. ``{"checkout.py"}``) obtained from :func:`extract_required_controls`.
    Only those files are imported, skipping the rest of the directory.

    **Eager mode (backward compat):** omit *required_modules*. All ``.py``
    files (excluding ``_``-prefixed) are imported — the legacy behaviour.

    Idempotent per file: each source file is imported at most once per
    process, regardless of how many ``ManulEngine`` instances are created.

    Each file is executed in an isolated module so that ``@custom_control``
    decorators register into the global ``_CUSTOM_CONTROLS`` dict.
    Errors in individual files are printed but do not abort engine startup.

    Args:
        workspace_dir: Absolute path to the user's project root (typically CWD).
        required_modules: Optional set of filenames to load.  When ``None``,
            every non-underscore ``.py`` file in ``controls/`` is loaded
            (eager mode).
    """
    resolved = str(Path(workspace_dir).resolve())
    controls_dir = Path(resolved) / "controls"
    if not controls_dir.is_dir():
        return

    if required_modules is not None:
        # Targeted (lazy) loading — only import specifically requested files.
        candidates = [controls_dir / name for name in sorted(required_modules)]
    else:
        # Eager loading (legacy) — skip entirely if this dir was already loaded.
        if resolved in _LOADED_DIRS:
            return
        candidates = sorted(controls_dir.glob("*.py"))
        # Mark directory as fully loaded so repeated eager calls are no-ops.
        _LOADED_DIRS.add(resolved)

    for py_file in candidates:
        if not py_file.is_file() or py_file.name.startswith("_"):
            continue
        # Per-file idempotency: skip files already imported in this process.
        file_key = str(py_file.resolve())
        if file_key in _LOADED_FILES:
            continue
        try:
            mod_name = f"_manul_custom_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(mod_name, py_file)
            if spec is None or spec.loader is None:
                continue
            fresh_module = importlib.util.module_from_spec(spec)
            fresh_module.__file__ = str(py_file)
            spec.loader.exec_module(fresh_module)  # type: ignore[union-attr]
            _LOADED_FILES.add(file_key)
            _label = "Lazy" if required_modules is not None else "Eager"
            print(f"    🎛️  Custom controls loaded: {py_file.name} ({_label} loaded)")
        except Exception as exc:
            print(f"    ⚠️  Custom controls: failed to load '{py_file.name}': {exc}")
