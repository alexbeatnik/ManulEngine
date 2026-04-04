# manul_engine/imports.py
"""
Hunt file import resolver and package manager.

Resolves @import: directives, manages hunt_libs/ packages,
and handles huntlib.json manifests.

Resolution order for import source paths:
  1. Relative to the importing .hunt file's directory
  2. Relative to CWD
  3. hunt_libs/<name>/  (looks for main.hunt or huntlib.json entry)
  4. ~/.manul/hunt_libs/<name>/  (installed scoped packages)
"""

from __future__ import annotations

import json
import os
import re
from typing import NamedTuple


class HuntImportError(Exception):
    """Raised when an @import: directive cannot be resolved."""


class ImportDirective(NamedTuple):
    """Parsed @import: header directive."""

    block_names: list[str]    # ["Login", "Logout"] or ["*"]
    source: str               # "lib/auth_flows.hunt" or "@manul/saucedemo-flows"
    aliases: dict[str, str]   # {"Login": "AuthLogin"} when 'as' syntax used


class ResolvedImport(NamedTuple):
    """A single resolved imported block ready for USE expansion."""

    block_name: str
    actions: list[str]
    source_file: str
    original_vars: dict[str, str]


# ── @import: header regex ────────────────────────────────────────────────────
# Matches:
#   @import: Login from lib/auth.hunt
#   @import: Login, Logout from lib/auth.hunt
#   @import: Login as AuthLogin from lib/auth.hunt
#   @import: * from lib/auth.hunt
_RE_IMPORT = re.compile(
    r"^@import:\s+(.+?)\s+from\s+(\S+)\s*$",
    re.IGNORECASE,
)


def parse_import_directive(line: str) -> ImportDirective | None:
    """Parse a single @import: line into an ImportDirective, or None."""
    m = _RE_IMPORT.match(line.strip())
    if m is None:
        return None

    names_part = m.group(1).strip()
    source = m.group(2).strip()

    if names_part == "*":
        return ImportDirective(block_names=["*"], source=source, aliases={})

    # Parse comma-separated block names with optional 'as Alias'
    block_names: list[str] = []
    aliases: dict[str, str] = {}

    for token in names_part.split(","):
        token = token.strip()
        if not token:
            continue
        # Check for 'as' alias: "Login as AuthLogin"
        as_match = re.match(r"^(.+?)\s+as\s+(\S+)$", token, re.IGNORECASE)
        if as_match:
            original = as_match.group(1).strip()
            alias = as_match.group(2).strip()
            block_names.append(original)
            aliases[original] = alias
        else:
            block_names.append(token)

    return ImportDirective(block_names=block_names, source=source, aliases=aliases)


def resolve_source_path(
    source: str,
    hunt_dir: str,
    cwd: str | None = None,
) -> str:
    """Resolve an import source path to an absolute file path.

    Resolution order:
      1. Relative to hunt_dir (the importing file's directory)
      2. Relative to CWD
      3. hunt_libs/<name>/main.hunt  (CWD-based)
      4. hunt_libs/<name>/  + huntlib.json entry field
      5. ~/.manul/hunt_libs/<name>/  (global install)

    Raises HuntImportError if no candidate exists.
    """
    cwd = cwd or os.getcwd()

    # If it looks like a file path (contains / or \ or ends with .hunt)
    if "/" in source or "\\" in source or source.endswith(".hunt"):
        candidates = [
            os.path.normpath(os.path.join(hunt_dir, source)),
            os.path.normpath(os.path.join(cwd, source)),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return os.path.abspath(c)
        tried = ", ".join(candidates)
        raise HuntImportError(
            f"Import source file not found: '{source}' "
            f"(tried: {tried})"
        )

    # Package-style import: "@manul/saucedemo-flows" or "auth_flows"
    # Normalize scoped names: @manul/foo → @manul/foo
    package_dirs = [
        os.path.join(cwd, "hunt_libs", source),
        os.path.join(os.path.expanduser("~"), ".manul", "hunt_libs", source),
    ]

    for pkg_dir in package_dirs:
        if not os.path.isdir(pkg_dir):
            continue
        # Check huntlib.json for entry field
        manifest_path = os.path.join(pkg_dir, "huntlib.json")
        if os.path.isfile(manifest_path):
            manifest = parse_huntlib_json(manifest_path)
            entry = manifest.get("entry", "main.hunt")
            entry_path = os.path.join(pkg_dir, entry)
            if os.path.isfile(entry_path):
                return os.path.abspath(entry_path)
        # Fallback: main.hunt
        main_path = os.path.join(pkg_dir, "main.hunt")
        if os.path.isfile(main_path):
            return os.path.abspath(main_path)

    tried = ", ".join(package_dirs)
    raise HuntImportError(
        f"Import package not found: '{source}' "
        f"(tried: {tried})"
    )


def parse_huntlib_json(path: str) -> dict:
    """Parse and validate a huntlib.json manifest file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise HuntImportError(f"huntlib.json must be a JSON object: {path}")
    return data


def _extract_exported_blocks(
    hunt_path: str,
    seen_files: set[str] | None = None,
) -> tuple[list[str], dict[str, list[str]], dict[str, str]]:
    """Parse a .hunt file and extract its exported STEP blocks.

    Returns (export_names, blocks_dict, parsed_vars) where:
      - export_names: list of @export: names (empty = nothing exported)
      - blocks_dict: {"BlockName": [action_lines...]} for all STEP blocks
      - parsed_vars: @var: declarations from the file

    Performs cycle detection via *seen_files*.
    """
    abs_path = os.path.abspath(hunt_path)
    if seen_files is not None and abs_path in seen_files:
        chain = " → ".join(sorted(seen_files)) + f" → {abs_path}"
        raise HuntImportError(f"Circular import detected: {chain}")

    exports: list[str] = []
    parsed_vars: dict[str, str] = {}
    blocks: dict[str, list[str]] = {}
    current_block_name: str | None = None
    current_actions: list[str] = []
    in_setup = False
    in_teardown = False

    _re_step = re.compile(r"^\s*(?:\d+\.\s*)?STEP\s*\d*\s*:\s*(.*)", re.IGNORECASE)
    _re_setup = re.compile(r"^\s*\[SETUP\]", re.IGNORECASE)
    _re_end_setup = re.compile(r"^\s*\[END\s+SETUP\]", re.IGNORECASE)
    _re_teardown = re.compile(r"^\s*\[TEARDOWN\]", re.IGNORECASE)
    _re_end_teardown = re.compile(r"^\s*\[END\s+TEARDOWN\]", re.IGNORECASE)

    with open(hunt_path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()

            # Skip hook blocks
            if _re_setup.match(stripped):
                in_setup = True
                continue
            if _re_end_setup.match(stripped):
                in_setup = False
                continue
            if _re_teardown.match(stripped):
                in_teardown = True
                continue
            if _re_end_teardown.match(stripped):
                in_teardown = False
                continue
            if in_setup or in_teardown:
                continue

            # Headers
            if stripped.startswith("@export:"):
                name = stripped.split(":", 1)[1].strip()
                if name:
                    exports.append(name)
                continue
            if stripped.startswith("@var:"):
                var_part = stripped[5:].strip()
                m = re.match(r"\{?([^}=\s]+)\}?\s*=\s*(.*)", var_part)
                if m:
                    parsed_vars[m.group(1).strip()] = m.group(2).strip()
                continue
            if stripped.startswith("@"):
                continue
            if stripped.startswith("#") or not stripped:
                continue
            if stripped.upper().startswith("DONE"):
                continue

            # STEP marker
            step_m = _re_step.match(stripped)
            if step_m:
                # Save previous block
                if current_block_name is not None:
                    blocks[current_block_name] = current_actions
                current_block_name = step_m.group(1).strip()
                current_actions = []
                continue

            # Action line inside a block
            if current_block_name is not None:
                current_actions.append(stripped)

    # Save last block
    if current_block_name is not None:
        blocks[current_block_name] = current_actions

    return exports, blocks, parsed_vars


def resolve_imports(
    directives: list[ImportDirective],
    hunt_dir: str,
    hunt_file: str,
    cwd: str | None = None,
    seen_files: set[str] | None = None,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Resolve all @import: directives and return importable blocks + vars.

    Returns (imported_blocks, import_vars) where:
      - imported_blocks: {"AliasOrName": [action_lines...]}
      - import_vars: merged @var: from all imported files (lowest priority)
    """
    if seen_files is None:
        seen_files = set()
    seen_files.add(os.path.abspath(hunt_file))
    cwd = cwd or os.getcwd()

    imported_blocks: dict[str, list[str]] = {}
    import_vars: dict[str, str] = {}

    for directive in directives:
        try:
            source_path = resolve_source_path(directive.source, hunt_dir, cwd)
        except HuntImportError as e:
            raise HuntImportError(
                f"Cannot resolve '@import: {', '.join(directive.block_names)} "
                f"from {directive.source}' in {hunt_file}: {e}"
            ) from e

        exports, blocks, lib_vars = _extract_exported_blocks(
            source_path, seen_files=set(seen_files),
        )

        # Merge library vars (import-level, will be lowest priority)
        import_vars.update(lib_vars)

        # Determine which blocks to import
        if directive.block_names == ["*"]:
            # Wildcard: import all exported blocks
            if exports and exports != ["*"]:
                requested = exports
            else:
                # If @export: * or no exports declared at all with wildcard import
                if exports == ["*"] or not exports:
                    requested = list(blocks.keys())
                else:
                    requested = exports
        else:
            requested = directive.block_names

        for name in requested:
            if name not in blocks:
                available = ", ".join(blocks.keys()) or "(none)"
                raise HuntImportError(
                    f"Block '{name}' not found in '{directive.source}' "
                    f"(resolved: {source_path}). "
                    f"Available blocks: {available}"
                )

            # Check export access (if the file has explicit exports)
            if exports and exports != ["*"] and name not in exports:
                raise HuntImportError(
                    f"Block '{name}' exists in '{directive.source}' but is not exported. "
                    f"Exported blocks: {', '.join(exports)}"
                )

            # Apply alias if specified
            alias = directive.aliases.get(name, name)
            imported_blocks[alias] = blocks[name]

    return imported_blocks, import_vars


def validate_exports(hunt_path: str) -> list[str]:
    """Validate that all @export: names reference existing STEP blocks.

    Returns a list of warning messages for exports that have no matching block.
    """
    exports, blocks, _ = _extract_exported_blocks(hunt_path)
    warnings: list[str] = []
    if exports == ["*"]:
        return warnings
    for name in exports:
        if name not in blocks:
            warnings.append(
                f"@export: '{name}' has no matching STEP block in {hunt_path}"
            )
    return warnings


def expand_use_directives(
    mission_lines: list[str],
    step_file_lines: list[int],
    imported_blocks: dict[str, list[str]],
) -> tuple[list[str], list[int]]:
    """Replace USE <BlockName> lines with imported block actions.

    Returns (expanded_lines, expanded_file_lines) where USE lines have been
    replaced by the corresponding imported actions.  File line numbers for
    expanded lines are set to 0 (synthetic/imported).
    """
    expanded: list[str] = []
    expanded_lines: list[int] = []

    _re_use = re.compile(r"^\s*(?:\d+\.\s*)?USE\s+(.+?)\s*$", re.IGNORECASE)

    for raw_line, file_line in zip(mission_lines, step_file_lines):
        m = _re_use.match(raw_line.strip())
        if m:
            block_name = m.group(1).strip()
            if block_name not in imported_blocks:
                raise HuntImportError(
                    f"USE '{block_name}' references an unknown import. "
                    f"Available imports: {', '.join(imported_blocks.keys()) or '(none)'}. "
                    f"Did you forget an @import: header?"
                )
            actions = imported_blocks[block_name]
            for action in actions:
                # Preserve 4-space indentation of expanded actions
                expanded.append(f"    {action}\n")
                expanded_lines.append(0)  # synthetic line
        else:
            expanded.append(raw_line)
            expanded_lines.append(file_line)

    return expanded, expanded_lines
