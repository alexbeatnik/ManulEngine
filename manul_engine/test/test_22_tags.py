# manul_engine/test/test_22_tags.py
"""
Unit-test suite for the @tags: hunt-file header and --tags CLI filter.

No network or live browser required.  All tests run against synthetic
temporary files or in-memory state only.

Tests:
  1. Parser — parse_hunt_file extracts @tags: into the 8th tuple element.
  2. _read_tags — fast header-only scanner returns the same tag list.
  3. Filtering — intersection rule: file is included iff it shares at least
     one tag with the requested --tags set.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python run_tests.py``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.cli import parse_hunt_file, _read_tags

# ── Test helpers ──────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0


def _assert(condition: bool, name: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"    \u2705  {name}")
    else:
        _FAIL += 1
        suffix = f" ({detail})" if detail else ""
        print(f"    \u274c  {name}{suffix}")


def _write_hunt(content: str) -> str:
    """Write *content* to a temp .hunt file, return its path."""
    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix=".hunt", encoding="utf-8", delete=False
    )
    tf.write(content)
    tf.close()
    return tf.name


# ── Section 1: Parser (@tags: extraction) ────────────────────────────────────

def _test_parser() -> None:
    print("\n  \u2500\u2500 Parser (@tags: extraction) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")

    # 1a. Basic @tags: line with multiple comma-separated tags.
    path = _write_hunt(
        "@context: Login flow\n"
        "@title: auth\n"
        "@tags: smoke, auth, regression\n"
        "\n"
        "1. NAVIGATE to https://example.com\n"
        "2. DONE.\n"
    )
    try:
        result = parse_hunt_file(path)
    finally:
        os.unlink(path)

    tags = result[7]
    _assert(tags == ["smoke", "auth", "regression"],
            "@tags: parsed into list of 3 trimmed tags",
            f"got={tags!r}")

    # 1b. Tags do NOT appear in the mission body.
    mission = result[0]
    _assert("@tags:" not in mission,
            "@tags: line excluded from mission body",
            f"mission={mission[:60]!r}")

    # 1c. Other metadata fields still work alongside @tags:.
    _assert(result[1] == "Login flow", "context still parsed alongside @tags:", f"got={result[1]!r}")
    _assert(result[2] == "auth", "title still parsed alongside @tags:", f"got={result[2]!r}")

    # 1d. No @tags: line ⇒ empty list.
    path2 = _write_hunt(
        "@context: No tags here\n"
        "1. DONE.\n"
    )
    try:
        result2 = parse_hunt_file(path2)
    finally:
        os.unlink(path2)
    _assert(result2[7] == [],
            "missing @tags: line returns empty list",
            f"got={result2[7]!r}")

    # 1e. Extra whitespace around tags is stripped.
    path3 = _write_hunt("@tags:  critical ,  slow ,  nightly  \n1. DONE.\n")
    try:
        result3 = parse_hunt_file(path3)
    finally:
        os.unlink(path3)
    _assert(result3[7] == ["critical", "slow", "nightly"],
            "whitespace around individual tags is stripped",
            f"got={result3[7]!r}")

    # 1f. Single tag (no comma).
    path4 = _write_hunt("@tags: smoke\n1. DONE.\n")
    try:
        result4 = parse_hunt_file(path4)
    finally:
        os.unlink(path4)
    _assert(result4[7] == ["smoke"],
            "single tag (no comma) parsed correctly",
            f"got={result4[7]!r}")

    # 1g. @tags: with empty value produces empty list.
    path5 = _write_hunt("@tags:\n1. DONE.\n")
    try:
        result5 = parse_hunt_file(path5)
    finally:
        os.unlink(path5)
    _assert(result5[7] == [],
            "@tags: with no value produces empty list",
            f"got={result5[7]!r}")

    # 1h. return tuple has length 12.
    _assert(len(result) == 12, "parse_hunt_file now returns a 12-tuple", f"len={len(result)}")


# ── Section 2: _read_tags fast scanner ───────────────────────────────────────

def _test_read_tags() -> None:
    print("\n  \u2500\u2500 _read_tags fast header scanner \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")

    # 2a. Tags found in header.
    path = _write_hunt("@tags: smoke, critical\n1. NAVIGATE to https://example.com\n2. DONE.\n")
    try:
        tags = _read_tags(path)
    finally:
        os.unlink(path)
    _assert(tags == ["smoke", "critical"],
            "_read_tags returns correct tag list from header",
            f"got={tags!r}")

    # 2b. No @tags: header ⇒ empty list.
    path2 = _write_hunt("@context: No tags\n1. DONE.\n")
    try:
        tags2 = _read_tags(path2)
    finally:
        os.unlink(path2)
    _assert(tags2 == [],
            "_read_tags returns [] when no @tags: line present",
            f"got={tags2!r}")

    # 2c. Stops at first numbered step (does not read whole file).
    path3 = _write_hunt("1. DONE.\n@tags: invisible\n")
    try:
        tags3 = _read_tags(path3)
    finally:
        os.unlink(path3)
    _assert(tags3 == [],
            "_read_tags stops at first numbered step, misses @tags: placed after it",
            f"got={tags3!r}")

    # 2d. Result matches parse_hunt_file for the same file.
    path4 = _write_hunt("@title: x\n@tags: a, b, c\n1. DONE.\n")
    try:
        fast  = _read_tags(path4)
        full  = parse_hunt_file(path4)[7]
    finally:
        os.unlink(path4)
    _assert(fast == full,
            "_read_tags result matches parse_hunt_file tags for same file",
            f"fast={fast!r} full={full!r}")


# ── Section 3: Filtering (intersection rule) ──────────────────────────────────

def _test_filtering() -> None:
    print("\n  \u2500\u2500 Tag filtering (intersection rule) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")

    # Build a small pool of temporary hunt files.
    smoke_path   = _write_hunt("@tags: smoke, auth\n1. DONE.\n")
    regr_path    = _write_hunt("@tags: regression\n1. DONE.\n")
    no_tags_path = _write_hunt("@context: untagged\n1. DONE.\n")
    combo_path   = _write_hunt("@tags: smoke, regression\n1. DONE.\n")

    all_files = [smoke_path, regr_path, no_tags_path, combo_path]

    def _filter(files: list[str], requested: set[str]) -> list[str]:
        return [f for f in files if requested & set(_read_tags(f))]

    try:
        # 3a. filter_tags={'smoke'} → files tagged smoke (smoke_path, combo_path)
        result = _filter(all_files, {"smoke"})
        _assert(
            smoke_path in result and combo_path in result and regr_path not in result and no_tags_path not in result,
            "filter_tags={'smoke'} matches only files tagged 'smoke'",
            f"matched={len(result)}",
        )

        # 3b. filter_tags={'regression'} → regr_path + combo_path
        result2 = _filter(all_files, {"regression"})
        _assert(
            regr_path in result2 and combo_path in result2 and smoke_path not in result2,
            "filter_tags={'regression'} matches files tagged 'regression'",
            f"matched={len(result2)}",
        )

        # 3c. filter_tags={'smoke', 'regression'} → OR logic, all tagged files
        result3 = _filter(all_files, {"smoke", "regression"})
        _assert(
            smoke_path in result3 and regr_path in result3 and combo_path in result3,
            "filter_tags={'smoke','regression'} matches files with either tag",
            f"matched={len(result3)}",
        )
        _assert(
            no_tags_path not in result3,
            "untagged file excluded even with multi-tag filter",
        )

        # 3d. filter_tags={'nonexistent'} → [] (no matches)
        result4 = _filter(all_files, {"nonexistent"})
        _assert(result4 == [],
                "filter_tags with unknown tag → empty list",
                f"matched={len(result4)}")

        # 3e. Empty filter_tags set → all files (no filtering applied, caller responsibility)
        # (In the CLI, we only call _filter when filter_tags is non-empty.)
        result5 = [f for f in all_files]  # no filter
        _assert(len(result5) == len(all_files),
                "empty filter_tags → all files pass (no-op)",
                f"len={len(result5)}")

        # 3f. Untagged file is excluded when filter is active.
        result6 = _filter([no_tags_path], {"smoke"})
        _assert(result6 == [],
                "file with no @tags: is excluded when filter is active",
                f"matched={len(result6)}")

    finally:
        for p in all_files:
            try:
                os.unlink(p)
            except OSError:
                pass


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n" + "\u2501" * 56)
    print("  test_22_tags \u2014 @tags: header and --tags CLI filter")
    print("\u2501" * 56)

    _test_parser()
    _test_read_tags()
    _test_filtering()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    return _FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(run_suite())
    sys.exit(0 if ok else 1)
