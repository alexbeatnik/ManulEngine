# manul_engine/test/test_52_exports.py
"""
Test suite for @export: validation, wildcard exports, and edge cases.

Covers:
  - @export: * (wildcard — all blocks exported)
  - File with no @export: and wildcard import
  - Empty blocks
  - Multiple files importing from the same library
  - HuntImportError re-exported from manul_engine
"""

import os
import tempfile

_PASS = 0
_FAIL = 0


def _assert(cond: bool, label: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"    ✅  {label}")
    else:
        _FAIL += 1
        msg = f"    ❌  {label}"
        if detail:
            msg += f" ({detail})"
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1: Wildcard @export: *
# ═══════════════════════════════════════════════════════════════════════════════

def _test_wildcard_export() -> None:
    print("\n  ── wildcard @export: * ───────────────────────────────────────")
    from manul_engine.imports import (
        ImportDirective, resolve_imports, _extract_exported_blocks,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        lib_path = os.path.join(tmpdir, "lib.hunt")
        with open(lib_path, "w") as f:
            f.write(
                "@export: *\n"
                "\n"
                "STEP 1: Login\n"
                "    Click 'Login'\n"
                "\n"
                "STEP 2: Logout\n"
                "    Click 'Logout'\n"
                "\n"
                "STEP 3: Reset\n"
                "    Click 'Reset'\n"
            )

        exports, blocks, _ = _extract_exported_blocks(lib_path)
        _assert(exports == ["*"], "wildcard export parsed")
        _assert(len(blocks) == 3, "all 3 blocks extracted")

        consumer = os.path.join(tmpdir, "c.hunt")
        with open(consumer, "w") as f:
            f.write("")

        # Wildcard import from wildcard export → all blocks
        directives = [ImportDirective(block_names=["*"], source="lib.hunt", aliases={})]
        result, _ = resolve_imports(directives, tmpdir, consumer)
        _assert("Login" in result, "wildcard→wildcard: Login available")
        _assert("Logout" in result, "wildcard→wildcard: Logout available")
        _assert("Reset" in result, "wildcard→wildcard: Reset available")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: No @export: with wildcard import
# ═══════════════════════════════════════════════════════════════════════════════

def _test_no_export_wildcard_import() -> None:
    print("\n  ── no @export: + wildcard @import ────────────────────────────")
    from manul_engine.imports import ImportDirective, resolve_imports

    with tempfile.TemporaryDirectory() as tmpdir:
        # Library with no @export: headers
        lib_path = os.path.join(tmpdir, "plain.hunt")
        with open(lib_path, "w") as f:
            f.write(
                "STEP 1: Setup\n"
                "    Click 'Setup'\n"
                "\n"
                "STEP 2: Verify\n"
                "    VERIFY that 'Done' is present\n"
            )

        consumer = os.path.join(tmpdir, "c.hunt")
        with open(consumer, "w") as f:
            f.write("")

        # Wildcard import from file with no exports → all blocks
        directives = [ImportDirective(block_names=["*"], source="plain.hunt", aliases={})]
        result, _ = resolve_imports(directives, tmpdir, consumer)
        _assert("Setup" in result, "no-export wildcard: Setup available")
        _assert("Verify" in result, "no-export wildcard: Verify available")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: Empty blocks
# ═══════════════════════════════════════════════════════════════════════════════

def _test_empty_blocks() -> None:
    print("\n  ── empty STEP blocks ─────────────────────────────────────────")
    from manul_engine.imports import _extract_exported_blocks

    with tempfile.TemporaryDirectory() as tmpdir:
        hunt_path = os.path.join(tmpdir, "empty.hunt")
        with open(hunt_path, "w") as f:
            f.write(
                "@export: EmptyStep\n"
                "\n"
                "STEP 1: EmptyStep\n"
                "\n"
                "STEP 2: HasAction\n"
                "    Click 'Go'\n"
            )

        exports, blocks, _ = _extract_exported_blocks(hunt_path)
        _assert("EmptyStep" in blocks, "empty block still extracted")
        _assert(len(blocks["EmptyStep"]) == 0, "empty block has no actions")
        _assert(len(blocks["HasAction"]) == 1, "non-empty block preserved")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4: Multiple files importing same library
# ═══════════════════════════════════════════════════════════════════════════════

def _test_multiple_consumers() -> None:
    print("\n  ── multiple consumers of same library ────────────────────────")
    from manul_engine.imports import ImportDirective, resolve_imports

    with tempfile.TemporaryDirectory() as tmpdir:
        lib_path = os.path.join(tmpdir, "shared.hunt")
        with open(lib_path, "w") as f:
            f.write(
                "@export: Login\n"
                "@var: {shared_url} = https://shared.com\n"
                "\n"
                "STEP 1: Login\n"
                "    Fill 'User' with 'admin'\n"
            )

        c1 = os.path.join(tmpdir, "c1.hunt")
        c2 = os.path.join(tmpdir, "c2.hunt")
        for p in (c1, c2):
            with open(p, "w") as f:
                f.write("")

        d = [ImportDirective(block_names=["Login"], source="shared.hunt", aliases={})]
        r1, v1 = resolve_imports(d, tmpdir, c1)
        r2, v2 = resolve_imports(d, tmpdir, c2)

        _assert("Login" in r1, "consumer 1 gets Login")
        _assert("Login" in r2, "consumer 2 gets Login")
        _assert(v1.get("shared_url") == "https://shared.com", "consumer 1 gets shared vars")
        _assert(v2.get("shared_url") == "https://shared.com", "consumer 2 gets shared vars")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: HuntImportError re-export
# ═══════════════════════════════════════════════════════════════════════════════

def _test_hunt_import_error_reexport() -> None:
    print("\n  ── HuntImportError re-export ─────────────────────────────────")
    from manul_engine import HuntImportError
    from manul_engine.imports import HuntImportError as DirectImport

    _assert(HuntImportError is DirectImport, "HuntImportError re-exported from manul_engine")
    _assert(issubclass(HuntImportError, Exception), "HuntImportError is an Exception subclass")

    try:
        raise HuntImportError("test error")
    except HuntImportError as e:
        _assert(str(e) == "test error", "HuntImportError carries message")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6: Named import with explicit @export access control
# ═══════════════════════════════════════════════════════════════════════════════

def _test_export_access_control() -> None:
    print("\n  ── @export access control ────────────────────────────────────")
    from manul_engine.imports import ImportDirective, resolve_imports, HuntImportError

    with tempfile.TemporaryDirectory() as tmpdir:
        lib_path = os.path.join(tmpdir, "restricted.hunt")
        with open(lib_path, "w") as f:
            f.write(
                "@export: Public\n"
                "\n"
                "STEP 1: Public\n"
                "    Click 'Public'\n"
                "\n"
                "STEP 2: Private\n"
                "    Click 'Private'\n"
            )

        consumer = os.path.join(tmpdir, "c.hunt")
        with open(consumer, "w") as f:
            f.write("")

        # Can import Public
        d1 = [ImportDirective(block_names=["Public"], source="restricted.hunt", aliases={})]
        r1, _ = resolve_imports(d1, tmpdir, consumer)
        _assert("Public" in r1, "exported block importable")

        # Cannot import Private (exists but not exported)
        d2 = [ImportDirective(block_names=["Private"], source="restricted.hunt", aliases={})]
        try:
            resolve_imports(d2, tmpdir, consumer)
            _assert(False, "raises on non-exported Private block")
        except HuntImportError as e:
            _assert("not exported" in str(e).lower(), "error mentions not exported", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n" + "=" * 60)
    print("  TEST 52 — @export validation & edge cases")
    print("=" * 60)

    _test_wildcard_export()
    _test_no_export_wildcard_import()
    _test_empty_blocks()
    _test_multiple_consumers()
    _test_hunt_import_error_reexport()
    _test_export_access_control()

    total = _PASS + _FAIL
    print(f"\n    SCORE: {_PASS}/{total}")
    if _FAIL:
        print(f"    \u26a0\ufe0f  {_FAIL} assertion(s) failed!")
    return _PASS, _FAIL
