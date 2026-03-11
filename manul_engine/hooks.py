# manul_engine/hooks.py
"""[SETUP] / [TEARDOWN] hook parser and executor for .hunt files.

Block syntax in a .hunt file::

    [SETUP]
    CALL PYTHON <module_path>.<function_name>
    [END SETUP]

    [TEARDOWN]
    CALL PYTHON <module_path>.<function_name>
    [END TEARDOWN]

Module resolution order for each ``CALL PYTHON`` instruction:

1. Directory of the ``.hunt`` file  — local project helpers
2. Current working directory        — project root
3. ``sys.path``                     — installed packages / PYTHONPATH

To keep global interpreter state clean, file-based modules (resolved via steps
1 and 2) are **not** inserted into ``sys.modules``; each execution creates a
fresh, isolated module object.  Installed packages (step 3) are loaded via the
standard ``importlib.import_module`` and follow normal caching behaviour.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

# ── Block-marker patterns (also imported by cli.parse_hunt_file) ──────────────
RE_SETUP        = re.compile(r"^\[SETUP\]$",          re.IGNORECASE)
RE_END_SETUP    = re.compile(r"^\[END\s+SETUP\]$",    re.IGNORECASE)
RE_TEARDOWN     = re.compile(r"^\[TEARDOWN\]$",       re.IGNORECASE)
RE_END_TEARDOWN = re.compile(r"^\[END\s+TEARDOWN\]$", re.IGNORECASE)

_RE_CALL_PYTHON = re.compile(
    r"^CALL\s+PYTHON\s+([\w.]+)(?:\s+(?:into|to)\s+\{(\w+)\})?\s*$",
    re.IGNORECASE,
)


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HookResult:
    """Immutable result of executing a single hook instruction."""

    success: bool
    message: str = ""
    #: Populated when the step used ``CALL PYTHON ... into {var}`` syntax and
    #: the function returned a non-``None`` value.  ``None`` means no variable
    #: binding was requested (or the function returned ``None``).
    return_value: str | None = None
    #: The variable name extracted from the ``into {var}`` / ``to {var}`` clause.
    var_name: str | None = None


# ── Block extraction ──────────────────────────────────────────────────────────

def extract_hook_blocks(raw_text: str) -> tuple[list[str], list[str], str]:
    """Strip ``[SETUP]`` and ``[TEARDOWN]`` blocks from *raw_text*.

    Useful for standalone text-to-text processing when original file
    line-number tracking is not required (e.g. in-memory tests).

    Returns:
        ``(setup_lines, teardown_lines, mission_body)`` where *mission_body* is
        the original text with hook blocks removed.
    """
    setup_lines:    list[str] = []
    teardown_lines: list[str] = []
    mission_lines:  list[str] = []
    in_setup    = False
    in_teardown = False

    for raw_line in raw_text.splitlines(keepends=True):
        stripped = raw_line.strip()

        if RE_SETUP.match(stripped):
            in_setup = True
            continue
        if RE_END_SETUP.match(stripped):
            in_setup = False
            continue
        if RE_TEARDOWN.match(stripped):
            in_teardown = True
            continue
        if RE_END_TEARDOWN.match(stripped):
            in_teardown = False
            continue

        if in_setup:
            if stripped and not stripped.startswith("#"):
                setup_lines.append(stripped)
        elif in_teardown:
            if stripped and not stripped.startswith("#"):
                teardown_lines.append(stripped)
        else:
            mission_lines.append(raw_line)

    return setup_lines, teardown_lines, "".join(mission_lines)


# ── Module resolution ─────────────────────────────────────────────────────────

def _resolve_module(module_path: str, hunt_dir: str | None) -> ModuleType:
    """Locate and load *module_path* without permanently inserting it into
    ``sys.modules``.

    Search order:

    1. *hunt_dir* — the directory containing the ``.hunt`` file.
    2. ``Path.cwd()`` — the project root.
    3. Standard ``importlib.import_module`` — installed packages / PYTHONPATH.

    File-based modules (found in steps 1/2) are executed in a fresh
    ``ModuleType`` object that is **not** added to ``sys.modules``, preventing
    accidental global namespace pollution between test runs.
    """
    # Convert dotted module path to a relative filesystem path.
    # "test_data_helpers"   → test_data_helpers.py
    # "utils.db.helpers"    → utils/db/helpers.py
    parts  = module_path.split(".")
    rel_py = Path(*parts).with_suffix(".py")

    search_roots: list[Path] = []
    if hunt_dir:
        search_roots.append(Path(hunt_dir).resolve())
    search_roots.append(Path.cwd())

    for root in search_roots:
        candidate = root / rel_py
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location(module_path, candidate)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                # Execute in isolation — does NOT touch sys.modules.
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                return mod

    # Fallback: standard import (PYTHONPATH / installed packages).
    return importlib.import_module(module_path)


# ── Single-line executor ──────────────────────────────────────────────────────

def execute_hook_line(
    line: str,
    hunt_dir: str | None = None,
) -> HookResult:
    """Execute one hook instruction and return a :class:`HookResult`.

    Supported syntax::

        CALL PYTHON <module_path>.<function_name>

    The target function must be **synchronous**.  Async callables are detected
    and rejected with a descriptive error rather than silently producing a
    dangling coroutine object.

    Args:
        line:      A stripped instruction string from the hook block.
        hunt_dir:  Absolute path of the directory containing the ``.hunt``
                   file.  Used as the first search root for module resolution.
    """
    m = _RE_CALL_PYTHON.match(line)
    if not m:
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: Unrecognised hook instruction: '{line}'\n"
                f"  Supported syntax:  CALL PYTHON <module>.<function>\n"
                f"  With capture:      CALL PYTHON <module>.<function> into {{var_name}}"
            ),
        )

    dotted = m.group(1)
    var_name: str | None = m.group(2) or None  # None when no 'into {var}' clause
    if "." not in dotted:
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: 'CALL PYTHON' requires '<module>.<function>' "
                f"but received '{dotted}'.\n"
                f"  Example:  CALL PYTHON test_data_helpers.inject_admin_user"
            ),
        )

    module_path, _, func_name = dotted.rpartition(".")

    # ── Load the module ───────────────────────────────────────────────────────
    try:
        module = _resolve_module(module_path, hunt_dir=hunt_dir)
    except ModuleNotFoundError as exc:
        # Only treat as "module not found" when the missing name is the
        # requested module itself. If exc.name differs, the error comes from
        # inside an already-found helper (e.g. a missing dependency), so
        # surface the original exception details instead.
        if getattr(exc, "name", None) == module_path:
            hint = (
                f"'{module_path}.py'" if "." not in module_path
                else f"'{module_path}' package"
            )
            return HookResult(
                success=False,
                message=(
                    f"ManulEngine Error: Module '{module_path}' not found.\n"
                    f"  Searched in: hunt file directory, CWD, and sys.path.\n"
                    f"  Make sure {hint} exists or is installed and importable."
                ),
            )
        return HookResult(
            success=False,
            message=f"ManulEngine Error: Failed to import '{module_path}': {exc}",
        )
    except ImportError as exc:
        return HookResult(
            success=False,
            message=f"ManulEngine Error: Failed to import '{module_path}': {exc}",
        )
    except Exception as exc:
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: Unexpected error loading '{module_path}': "
                f"{type(exc).__name__}: {exc}"
            ),
        )

    # ── Resolve the callable ──────────────────────────────────────────────────
    func = getattr(module, func_name, None)
    if func is None:
        public_names = [n for n in dir(module) if not n.startswith("_")]
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: Could not find function '{func_name}' "
                f"in module '{module_path}.py'.\n"
                f"  Available public names: {public_names or ['(none)']}"
            ),
        )

    if not callable(func):
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: '{func_name}' in '{module_path}.py' is not "
                f"callable (found {type(func).__name__})."
            ),
        )

    import asyncio as _asyncio
    if _asyncio.iscoroutinefunction(func):
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: '{func_name}' in '{module_path}.py' is async. "
                f"Hook functions must be synchronous — wrap async code with "
                f"asyncio.run() inside the helper if needed."
            ),
        )

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        ret = func()
        ret_str: str | None = None
        if var_name is not None:
            # Always stringify — even None → "None" — so that a variable binding
            # is guaranteed when 'into {var}' / 'to {var}' was explicitly requested.
            ret_str = str(ret)
        suffix = f" → {{{var_name}}} = {ret_str!r}" if var_name and ret_str is not None else ""
        return HookResult(
            success=True,
            message=f"✔  {dotted}(){suffix}",
            return_value=ret_str,
            var_name=var_name,
        )
    except Exception as exc:
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: '{dotted}()' raised "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ── Block runner ──────────────────────────────────────────────────────────────

def run_hooks(
    lines: list[str],
    label: str = "HOOK",
    hunt_dir: str | None = None,
) -> bool:
    """Run all instruction lines in a hook block sequentially.

    Stops on the first failure and prints a clear, human-readable error
    message.  Successful steps are confirmed with a check-mark.

    Args:
        lines:    Non-empty instruction strings collected from the hook block.
        label:    Display label — ``"SETUP"`` or ``"TEARDOWN"``.
        hunt_dir: Absolute path to the ``.hunt`` file's directory, forwarded
                  to :func:`execute_hook_line` for module resolution.

    Returns:
        ``True`` if every instruction succeeded; ``False`` if any failed.
    """
    if not lines:
        return True

    bar = "─" * 54
    print(f"\n{bar}")
    print(f"  [{label}]")
    print(bar)

    for line in lines:
        print(f"  ▶  {line}")
        result = execute_hook_line(line, hunt_dir=hunt_dir)
        print(f"     {result.message}")
        if not result.success:
            print(bar)
            print(f"  [{label}]  ✖ FAILED — aborting hook block")
            print(f"{bar}\n")
            return False

    print(bar)
    print(f"  [{label}]  ✔ OK")
    print(f"{bar}\n")
    return True
