#!/usr/bin/env python3
"""
Bump the ManulEngine version across all files from a single source.

Usage:
    python bump_version.py 0.0.9.28          # update all files
    python bump_version.py 0.0.9.28 --dry-run  # preview changes only
    python bump_version.py --show              # print current version

The canonical source of truth is pyproject.toml → version = "X.Y.Z".
This script reads the current version from there and replaces it in
every file that embeds the version string.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── Files and the regex patterns to match the version in each ────────────────
# Each entry: (relative_path, compiled_regex_with_one_capture_group)
# The capture group wraps the version substring to be replaced.

_VER_RE = r"0\.\d+\.\d+(?:\.\d+)?"  # matches 0.0.9.27-style versions

TARGETS: list[tuple[str, re.Pattern]] = [
    # Python package — single source of truth
    ("pyproject.toml", re.compile(rf'(version\s*=\s*"){_VER_RE}(")')),
    # Docker
    ("Dockerfile", re.compile(rf"(ARG MANUL_VERSION=){_VER_RE}()")),
    ("docker-compose.yml", re.compile(rf'(MANUL_VERSION:\s*"){_VER_RE}(")')),
    ("docker-compose.yml", re.compile(rf"(manul-engine:){_VER_RE}()")),
    # CI workflows
    (".github/workflows/release.yml", re.compile(rf'(echo\s+"manul_version=){_VER_RE}(")')),
    (".github/workflows/manul-ci.yml", re.compile(rf"(manul-engine:){_VER_RE}()")),
    # Documentation
    ("README.md", re.compile(rf"(manul-engine==){_VER_RE}()")),
    ("README.md", re.compile(rf"(manul-engine\[ai\]==){_VER_RE}()")),
    ("README.md", re.compile(rf"(manul-engine:){_VER_RE}()")),
    ("README.md", re.compile(rf"(What's New in v){_VER_RE}()")),
    ("README.md", re.compile(rf"(\*\*Version:\*\*\s*){_VER_RE}()")),
    ("README_DEV.md", re.compile(rf"(ManulEngine\s+v){_VER_RE}()")),
    ("README_DEV.md", re.compile(rf"(manul-engine\s+){_VER_RE}()")),
    ("README_DEV.md", re.compile(rf"(manul-engine==){_VER_RE}()")),
    ("README_DEV.md", re.compile(rf"(manul-engine:){_VER_RE}()")),
    ("README_DEV.md", re.compile(rf"(Release Notes:\s*v){_VER_RE}()")),
    ("README_DEV.md", re.compile(rf"(\*\*Version:\*\*\s*){_VER_RE}()")),
    # AI instructions
    (".github/copilot-instructions.md", re.compile(rf"(version:\s*){_VER_RE}()")),
    (".github/copilot-instructions.md", re.compile(rf"(manul-engine:){_VER_RE}()")),
    ("custom-instructions/repo/.github/copilot-instructions.md", re.compile(rf"(version:\s*){_VER_RE}()")),
    ("custom-instructions/repo/.github/copilot-instructions.md", re.compile(rf"(manul-engine:){_VER_RE}()")),
    (".cursorrules", re.compile(rf'(manulEngineVersion":\s*"){_VER_RE}(")')),
    (".cursorrules", re.compile(rf"(manul-engine==){_VER_RE}()")),
    (".cursorrules", re.compile(rf"(manul-engine\[ai\]==){_VER_RE}()")),
    (".cursorrules", re.compile(rf"(Treat\s+`){_VER_RE}(`)")),
]

# Contracts — all have "version": "X.Y.Z" in a JSON block
CONTRACT_FILES = [
    "contracts/MANUL_API_CONTRACT.md",
    "contracts/MANUL_CLI_CONTRACT.md",
    "contracts/MANUL_CONFIG_CONTRACT.md",
    "contracts/MANUL_DEBUG_CONTRACT.md",
    "contracts/MANUL_DSL_CONTRACT.md",
    "contracts/MANUL_HOOKS_CONTRACT.md",
    "contracts/MANUL_REPORTING_CONTRACT.md",
    "contracts/MANUL_SCORING_CONTRACT.md",
]
_CONTRACT_RE = re.compile(rf'("version":\s*"){_VER_RE}(")')

for cf in CONTRACT_FILES:
    TARGETS.append((cf, _CONTRACT_RE))


def get_current_version() -> str:
    """Read the canonical version from pyproject.toml."""
    pyproject = ROOT / "pyproject.toml"
    m = re.search(r'version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
    if not m:
        print("ERROR: could not parse version from pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def bump(new_version: str, *, dry_run: bool = False) -> None:
    old_version = get_current_version()
    if old_version == new_version:
        print(f"Version is already {old_version} — nothing to do.")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}Bumping {old_version} → {new_version}\n")

    total_replacements = 0
    files_changed: list[str] = []

    for rel_path, pattern in TARGETS:
        fpath = ROOT / rel_path
        if not fpath.exists():
            print(f"  ⚠️  SKIP (not found): {rel_path}")
            continue

        text = fpath.read_text(encoding="utf-8")
        new_text, count = pattern.subn(rf"\g<1>{new_version}\2", text)

        if count == 0:
            # Pattern didn't match — warn (might be already updated or format changed)
            print(f"  ⚠️  NO MATCH in {rel_path}: {pattern.pattern}")
            continue

        total_replacements += count
        if rel_path not in files_changed:
            files_changed.append(rel_path)

        if dry_run:
            print(f"  📝  {rel_path}: {count} replacement(s)")
        else:
            fpath.write_text(new_text, encoding="utf-8")
            print(f"  ✅  {rel_path}: {count} replacement(s)")

    print(
        f"\n{'[DRY RUN] ' if dry_run else ''}Done: {total_replacements} replacements across {len(files_changed)} files"
    )

    if not dry_run and total_replacements > 0:
        print(f"\nNext steps:")
        print(f"  git add -A && git commit -m 'chore: bump version to {new_version}'")
        print(f"  git tag v{new_version}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump ManulEngine version across all files.")
    parser.add_argument("version", nargs="?", help="New version string (e.g. 0.0.9.28)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    parser.add_argument("--show", action="store_true", help="Print current version and exit")
    args = parser.parse_args()

    if args.show:
        print(get_current_version())
        return

    if not args.version:
        parser.error("version is required (or use --show)")

    # Basic sanity check on version format
    if not re.match(r"^\d+\.\d+\.\d+(\.\d+)?$", args.version):
        parser.error(f"Invalid version format: {args.version} (expected N.N.N or N.N.N.N)")

    bump(args.version, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
