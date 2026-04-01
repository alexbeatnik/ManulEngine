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
2. Configured helper directories under the ``.hunt`` file directory
3. Current working directory        — project root
4. Configured helper directories under the project root
5. ``sys.path``                     — installed packages / PYTHONPATH

To keep global interpreter state clean, file-based modules (resolved via steps
1 and 2) are **not** inserted into ``sys.modules``.  They are loaded into an
internal, process-level cache on first use and the same ``ModuleType`` instance
is reused for subsequent ``CALL PYTHON`` invocations in that process.  Installed
packages (step 3) are loaded via the standard ``importlib.import_module`` and
follow normal ``sys.modules`` caching behaviour.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

# ── JIT module cache ──────────────────────────────────────────────────────────
# Caches dynamically imported modules by (module_path, resolved_file) so that
# repeated CALL PYTHON invocations within a run reuse the same module object
# instead of re-executing the file every time.
_module_cache: dict[str, ModuleType] = {}

# ── Block-marker patterns (also imported by cli.parse_hunt_file) ──────────────
RE_SETUP        = re.compile(r"^\[SETUP\]$",          re.IGNORECASE)
RE_END_SETUP    = re.compile(r"^\[END\s+SETUP\]$",    re.IGNORECASE)
RE_TEARDOWN     = re.compile(r"^\[TEARDOWN\]$",       re.IGNORECASE)
RE_END_TEARDOWN = re.compile(r"^\[END\s+TEARDOWN\]$", re.IGNORECASE)

_RE_CALL_PYTHON = re.compile(
    r"^CALL\s+PYTHON\s+([{}\w.]+)(.*?)$",
    re.IGNORECASE,
)
_RE_PRINT = re.compile(r'^PRINT\s+(.+)$', re.IGNORECASE)

_RE_INTO_VAR = re.compile(r"(?:^|\s+)(?:into|to)\s+\{(\w+)\}\s*$", re.IGNORECASE)
_RE_WITH_ARGS = re.compile(r"^with\s+args\s*:\s*(.*)$", re.IGNORECASE)

_RE_VAR_PLACEHOLDER = re.compile(r"\{(\w+)\}")


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
    #: Top-level dict keys returned by Python helpers are flattened into shared
    #: variables so they can be referenced directly as ``{key}``.
    return_mapping: dict[str, str] = field(default_factory=dict)


def _lookup_variable(variables: dict[str, str] | None, name: str) -> str | None:
    if variables is None:
        return None
    getter = getattr(variables, "get", None)
    if callable(getter):
        return getter(name)
    try:
        return variables[name]  # type: ignore[index]
    except Exception:
        return None


def _substitute_hook_variables(text: str, variables: dict[str, str] | None) -> str:
    return _RE_VAR_PLACEHOLDER.sub(
        lambda m: _lookup_variable(variables, m.group(1)) or m.group(0),
        text,
    )


def bind_hook_result(result: HookResult, variables: dict[str, str] | None) -> None:
    """Apply any returned variables from a hook result into a shared context."""
    if variables is None or not result.success:
        return
    if result.return_mapping:
        updater = getattr(variables, "update", None)
        if callable(updater):
            updater(result.return_mapping)
        else:
            for key, value in result.return_mapping.items():
                variables[key] = value  # type: ignore[index]
    if result.var_name and result.return_value is not None:
        variables[result.var_name] = result.return_value  # type: ignore[index]


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

def _resolve_module(module_path: str, hunt_dir: str | None) -> tuple[ModuleType, bool]:
    """Locate and load *module_path*, returning ``(module, from_cache)``.

    Uses a process-level cache (``_module_cache``) keyed by the resolved
    absolute file path so that repeated ``CALL PYTHON`` invocations within
    a run reuse the same module object.

    Search order:

    1. *hunt_dir* — the directory containing the ``.hunt`` file.
    2. Configured CALL PYTHON helper directories under *hunt_dir*.
    3. ``Path.cwd()`` — the project root.
    4. Configured CALL PYTHON helper directories under ``Path.cwd()``.
    5. Standard ``importlib.import_module`` — installed packages / PYTHONPATH.

    File-based modules (found in steps 1/2) are executed in a fresh
    ``ModuleType`` object the first time they are resolved in a given Python
    process and are **not** added to ``sys.modules``.  The resulting module
    object is stored in the process-level ``_module_cache`` and reused for
    subsequent resolutions of the same file path, so module-level state
    persists across hook blocks and ``.hunt`` files for the lifetime of the
    process.

    Returns:
        A tuple ``(module, from_cache)`` where *from_cache* is ``True`` when
        the module was served from ``_module_cache``.
    """
    # Convert dotted module path to a relative filesystem path.
    # "test_data_helpers"   → test_data_helpers.py
    # "utils.db.helpers"    → utils/db/helpers.py
    parts  = module_path.split(".")
    rel_py = Path(*parts).with_suffix(".py")
    from .prompts import CALL_PYTHON_DIRS

    search_roots: list[Path] = []
    if hunt_dir:
        search_roots.append(Path(hunt_dir).resolve())
    search_roots.append(Path.cwd())

    for root in search_roots:
        candidates = [root / rel_py]
        for helper_dir in CALL_PYTHON_DIRS:
            if parts and parts[0] == helper_dir:
                continue
            candidates.append(root / helper_dir / rel_py)
        for candidate in candidates:
            if not candidate.is_file():
                continue
            cache_key = str(candidate.resolve())
            cached = _module_cache.get(cache_key)
            if cached is not None:
                return cached, True
            spec = importlib.util.spec_from_file_location(module_path, candidate)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                # Execute in isolation — does NOT touch sys.modules.
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                _module_cache[cache_key] = mod
                return mod, False

    # Fallback: standard import (PYTHONPATH / installed packages).
    # Check cache for stdlib/installed modules too.
    cached = _module_cache.get(module_path)
    if cached is not None:
        return cached, True
    mod = importlib.import_module(module_path)
    _module_cache[module_path] = mod
    return mod, False


def clear_module_cache() -> None:
    """Reset the JIT module cache.  Used between test runs or by the
    synthetic test suite to ensure isolation."""
    _module_cache.clear()


# ── Single-line executor ──────────────────────────────────────────────────────

def _parse_call_args(raw_args: str | None, variables: dict[str, str] | None = None) -> list[str]:
    """Parse and resolve positional arguments from a CALL PYTHON instruction.

    Handles single/double-quoted strings and ``{var}`` placeholders.
    Placeholders are resolved against *variables*; unresolved ones are
    kept as-is (literal ``{name}``).
    """
    if not raw_args or not raw_args.strip():
        return []
    try:
        # On Windows, use posix=False so backslashes in paths are preserved.
        tokens = shlex.split(raw_args, posix=(os.name != "nt"))
    except ValueError:
        # Malformed quoting — fall back to simple whitespace split.
        tokens = raw_args.split()
    # posix=False preserves surrounding quotes — strip them.
    if os.name == "nt":
        stripped: list[str] = []
        for t in tokens:
            if len(t) >= 2 and t[0] == t[-1] and t[0] in ('"', "'"):
                t = t[1:-1]
            stripped.append(t)
        tokens = stripped
    if variables:
        resolved: list[str] = []
        for tok in tokens:
            resolved.append(
                _RE_VAR_PLACEHOLDER.sub(
                    lambda m: variables.get(m.group(1), m.group(0)), tok
                )
            )
        return resolved
    return tokens


def execute_hook_line(
    line: str,
    hunt_dir: str | None = None,
    variables: dict[str, str] | None = None,
) -> HookResult:
    """Execute one hook instruction and return a :class:`HookResult`.

    Supported syntax::

        CALL PYTHON <module_path>.<function_name>
        CALL PYTHON <module_path>.<function_name> "arg1" 'arg2' {var}
        CALL PYTHON <module_path>.<function_name> "arg1" into {result}

    The target function must be **synchronous**.  Async callables are detected
    and rejected with a descriptive error rather than silently producing a
    dangling coroutine object.

    Args:
        line:      A stripped instruction string from the hook block.
        hunt_dir:  Absolute path of the directory containing the ``.hunt``
                   file.  Used as the first search root for module resolution.
        variables: Optional dict of ``{name} → value`` used to resolve
                   placeholder arguments.
    """
    print_match = _RE_PRINT.match(line)
    if print_match:
        payload = print_match.group(1).strip()
        if len(payload) >= 2 and payload[0] == payload[-1] and payload[0] in ('"', "'"):
            payload = payload[1:-1]
        return HookResult(success=True, message=_substitute_hook_variables(payload, variables))

    m = _RE_CALL_PYTHON.match(line)
    if not m:
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: Unrecognised hook instruction: '{line}'\n"
                f"  Supported syntax:  CALL PYTHON <module>.<function>\n"
                f"                      PRINT \"message with {{vars}}\"\n"
                f"  With capture:      CALL PYTHON <module>.<function> into {{var_name}}"
            ),
        )

    dotted = m.group(1)
    remainder = m.group(2).strip()  # everything after dotted name

    if dotted.startswith("{") and "}" in dotted:
        alias_name = dotted[1:].split("}", 1)[0]
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: Unresolved @script alias '{{{alias_name}}}' in '{line}'.\n"
                f"  Declare it in the hunt header, for example: @script: {{{alias_name}}} = scripts.{alias_name}\n"
                f"  Or alias a callable directly: @script: {{{alias_name}}} = scripts.helpers.{alias_name}"
            ),
        )

    # Extract 'into {var}' / 'to {var}' clause from the end if present.
    var_name: str | None = None
    into_m = _RE_INTO_VAR.search(remainder)
    if into_m:
        var_name = into_m.group(1)
        remainder = remainder[:into_m.start()].strip()  # args without 'into {var}'
    with_args_m = _RE_WITH_ARGS.match(remainder)
    if with_args_m:
        remainder = with_args_m.group(1).strip()
    raw_args_str: str | None = remainder or None

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
        module, from_cache = _resolve_module(module_path, hunt_dir=hunt_dir)
        if from_cache:
            print(f"    [📦 CACHE HIT] Module '{module_path}' loaded from cache.")
        else:
            print(f"    [⚙️ JIT LOAD] Module '{module_path}' dynamically imported.")
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
            from .prompts import CALL_PYTHON_DIRS
            helper_dirs = ", ".join(f"'{d}'" for d in CALL_PYTHON_DIRS) or "<none>"
            return HookResult(
                success=False,
                message=(
                    f"ManulEngine Error: Module '{module_path}' not found.\n"
                    f"  Searched in: hunt file directory, helper dirs {helper_dirs}, CWD, matching helper dirs under CWD, and sys.path.\n"
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

    # ── Parse positional arguments ─────────────────────────────────────────────
    call_args = _parse_call_args(raw_args_str or "", variables)
    args_repr = ", ".join(repr(a) for a in call_args)

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        ret = func(*call_args)
        ret_str: str | None = None
        ret_mapping: dict[str, str] = {}
        if isinstance(ret, dict):
            ret_mapping = {
                str(key): str(value)
                for key, value in ret.items()
                if str(key).strip()
            }
        if var_name is not None:
            # Always stringify — even None → "None" — so that a variable binding
            # is guaranteed when 'into {var}' / 'to {var}' was explicitly requested.
            ret_str = str(ret)
        suffix = f" → {{{var_name}}} = {ret_str!r}" if var_name and ret_str is not None else ""
        if ret_mapping:
            suffix += f" → keys {sorted(ret_mapping)}"
        return HookResult(
            success=True,
            message=f"✔  {dotted}({args_repr}){suffix}",
            return_value=ret_str,
            var_name=var_name,
            return_mapping=ret_mapping,
        )
    except Exception as exc:
        return HookResult(
            success=False,
            message=(
                f"ManulEngine Error: '{dotted}({args_repr})' raised "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ── Block runner ──────────────────────────────────────────────────────────────

def run_hooks(
    lines: list[str],
    label: str = "HOOK",
    hunt_dir: str | None = None,
    variables: dict[str, str] | None = None,
) -> bool:
    """Run all instruction lines in a hook block sequentially.

    Stops on the first failure and prints a clear, human-readable error
    message.  Successful steps are confirmed with a check-mark.

    Args:
        lines:    Non-empty instruction strings collected from the hook block.
        label:    Display label — ``"SETUP"`` or ``"TEARDOWN"``.
        hunt_dir: Absolute path to the ``.hunt`` file's directory, forwarded
                  to :func:`execute_hook_line` for module resolution.
        variables: Optional ``{name → value}`` dict forwarded to
                   :func:`execute_hook_line` for placeholder resolution.

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
        result = execute_hook_line(line, hunt_dir=hunt_dir, variables=variables)
        bind_hook_result(result, variables)
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
