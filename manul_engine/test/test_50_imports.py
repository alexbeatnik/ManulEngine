# manul_engine/test/test_50_imports.py
"""
Test suite for the @import: / @export: / USE system.

Covers:
  - parse_import_directive() parsing
  - resolve_source_path() resolution order
  - _extract_exported_blocks() block extraction + export validation
  - resolve_imports() full resolution with cycle detection
  - expand_use_directives() USE command expansion
  - ParsedHunt integration (@import/@export round-trip via parse_hunt_file)
  - Variable precedence: import-level vars are lowest priority
  - classify_step for USE keyword
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
# Section 1: parse_import_directive
# ═══════════════════════════════════════════════════════════════════════════════

def _test_parse_import_directive() -> None:
    print("\n  ── parse_import_directive ────────────────────────────────────")
    from manul_engine.imports import parse_import_directive

    # Simple single block import
    d = parse_import_directive("@import: Login from lib/auth.hunt")
    _assert(d is not None, "parses simple import")
    _assert(d.block_names == ["Login"], "single block name", f"{d.block_names}")
    _assert(d.source == "lib/auth.hunt", "source path", f"{d.source}")
    _assert(d.aliases == {}, "no aliases", f"{d.aliases}")

    # Multiple blocks
    d2 = parse_import_directive("@import: Login, Logout from lib/auth.hunt")
    _assert(d2 is not None, "parses multi-block import")
    _assert(d2.block_names == ["Login", "Logout"], "two block names", f"{d2.block_names}")

    # With alias
    d3 = parse_import_directive("@import: Login as AuthLogin from lib/auth.hunt")
    _assert(d3 is not None, "parses aliased import")
    _assert(d3.block_names == ["Login"], "aliased block name", f"{d3.block_names}")
    _assert(d3.aliases == {"Login": "AuthLogin"}, "alias mapping", f"{d3.aliases}")

    # Wildcard
    d4 = parse_import_directive("@import: * from lib/auth.hunt")
    _assert(d4 is not None, "parses wildcard import")
    _assert(d4.block_names == ["*"], "wildcard marker", f"{d4.block_names}")

    # Non-import line returns None
    d5 = parse_import_directive("@var: {x} = hello")
    _assert(d5 is None, "non-import returns None")

    # Case insensitive
    d6 = parse_import_directive("@IMPORT: Login from lib/auth.hunt")
    _assert(d6 is not None, "case-insensitive @IMPORT")

    # Mixed aliases: "Login as AuthLogin, Logout"
    d7 = parse_import_directive("@import: Login as AuthLogin, Logout from lib/auth.hunt")
    _assert(d7 is not None, "parses mixed alias+plain import")
    _assert(d7.block_names == ["Login", "Logout"], "mixed block names", f"{d7.block_names}")
    _assert(d7.aliases == {"Login": "AuthLogin"}, "mixed alias mapping", f"{d7.aliases}")

    # Package-style source
    d8 = parse_import_directive("@import: Login from @manul/auth")
    _assert(d8 is not None, "parses package-style import")
    _assert(d8.source == "@manul/auth", "scoped package source", f"{d8.source}")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: resolve_source_path
# ═══════════════════════════════════════════════════════════════════════════════

def _test_resolve_source_path() -> None:
    print("\n  ── resolve_source_path ───────────────────────────────────────")
    from manul_engine.imports import resolve_source_path, HuntImportError

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create hunt_dir/lib/auth.hunt
        lib_dir = os.path.join(tmpdir, "lib")
        os.makedirs(lib_dir)
        auth_path = os.path.join(lib_dir, "auth.hunt")
        with open(auth_path, "w") as f:
            f.write("STEP 1: Login\n    Click 'Login'\n")

        # Resolve relative to hunt_dir
        result = resolve_source_path("lib/auth.hunt", hunt_dir=tmpdir)
        _assert(os.path.isfile(result), "resolves relative to hunt_dir")
        _assert(result == os.path.abspath(auth_path), "correct abspath", f"{result}")

        # Resolve relative to CWD
        result2 = resolve_source_path("lib/auth.hunt", hunt_dir=os.path.join(tmpdir, "other"), cwd=tmpdir)
        _assert(os.path.isfile(result2), "resolves relative to CWD when hunt_dir fails")

        # Non-existent file raises
        try:
            resolve_source_path("nonexistent.hunt", hunt_dir=tmpdir)
            _assert(False, "raises on missing file")
        except HuntImportError:
            _assert(True, "raises HuntImportError on missing file")

        # Package-style with hunt_libs/
        pkg_dir = os.path.join(tmpdir, "hunt_libs", "auth_flows")
        os.makedirs(pkg_dir)
        main_path = os.path.join(pkg_dir, "main.hunt")
        with open(main_path, "w") as f:
            f.write("STEP 1: Test\n    Click 'Ok'\n")
        result3 = resolve_source_path("auth_flows", hunt_dir=tmpdir, cwd=tmpdir)
        _assert(os.path.isfile(result3), "resolves package via hunt_libs/")

        # Package with huntlib.json entry field
        pkg2_dir = os.path.join(tmpdir, "hunt_libs", "custom_pkg")
        os.makedirs(pkg2_dir)
        with open(os.path.join(pkg2_dir, "huntlib.json"), "w") as f:
            import json
            json.dump({"name": "custom_pkg", "version": "1.0.0", "entry": "flows.hunt"}, f)
        flows_path = os.path.join(pkg2_dir, "flows.hunt")
        with open(flows_path, "w") as f:
            f.write("STEP 1: Flow\n    Click 'Go'\n")
        result4 = resolve_source_path("custom_pkg", hunt_dir=tmpdir, cwd=tmpdir)
        _assert(os.path.isfile(result4), "resolves package via huntlib.json entry")
        _assert(os.path.basename(result4) == "flows.hunt", "correct entry file", f"{result4}")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: _extract_exported_blocks
# ═══════════════════════════════════════════════════════════════════════════════

def _test_extract_exported_blocks() -> None:
    print("\n  ── _extract_exported_blocks ──────────────────────────────────")
    from manul_engine.imports import _extract_exported_blocks

    with tempfile.TemporaryDirectory() as tmpdir:
        hunt_path = os.path.join(tmpdir, "lib.hunt")
        with open(hunt_path, "w") as f:
            f.write(
                "@context: Auth library\n"
                "@export: Login\n"
                "@export: Logout\n"
                "@var: {base_url} = https://example.com\n"
                "\n"
                "STEP 1: Login\n"
                "    NAVIGATE to {base_url}/login\n"
                "    Fill 'Username' with 'admin'\n"
                "\n"
                "STEP 2: Logout\n"
                "    Click 'Logout'\n"
                "\n"
                "STEP 3: Internal helpers\n"
                "    Click 'Debug'\n"
            )

        exports, blocks, parsed_vars = _extract_exported_blocks(hunt_path)
        _assert(exports == ["Login", "Logout"], "exports list", f"{exports}")
        _assert("Login" in blocks, "Login block extracted")
        _assert("Logout" in blocks, "Logout block extracted")
        _assert("Internal helpers" in blocks, "internal block also extracted")
        _assert(len(blocks["Login"]) == 2, "Login has 2 actions", f"{len(blocks['Login'])}")
        _assert(len(blocks["Logout"]) == 1, "Logout has 1 action", f"{len(blocks['Logout'])}")
        _assert(parsed_vars.get("base_url") == "https://example.com", "@var parsed", f"{parsed_vars}")

        # Hook blocks are skipped
        hunt2 = os.path.join(tmpdir, "with_hooks.hunt")
        with open(hunt2, "w") as f:
            f.write(
                "[SETUP]\n"
                "CALL PYTHON foo.bar\n"
                "[END SETUP]\n"
                "\n"
                "STEP 1: Act\n"
                "    Click 'Go'\n"
                "\n"
                "[TEARDOWN]\n"
                "CALL PYTHON foo.cleanup\n"
                "[END TEARDOWN]\n"
            )
        exports2, blocks2, _ = _extract_exported_blocks(hunt2)
        _assert(exports2 == [], "no exports declared")
        _assert("Act" in blocks2, "block extracted despite hooks")
        _assert(len(blocks2) == 1, "only 1 block (hooks excluded)", f"{len(blocks2)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4: resolve_imports full resolution
# ═══════════════════════════════════════════════════════════════════════════════

def _test_resolve_imports() -> None:
    print("\n  ── resolve_imports (full resolution) ─────────────────────────")
    from manul_engine.imports import (
        ImportDirective, resolve_imports, HuntImportError
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create lib file
        lib_path = os.path.join(tmpdir, "lib.hunt")
        with open(lib_path, "w") as f:
            f.write(
                "@export: Login\n"
                "@export: Logout\n"
                "@var: {base_url} = https://example.com\n"
                "\n"
                "STEP 1: Login\n"
                "    Fill 'User' with 'admin'\n"
                "    Click 'Submit'\n"
                "\n"
                "STEP 2: Logout\n"
                "    Click 'Logout'\n"
                "\n"
                "STEP 3: Secret\n"
                "    Click 'Debug'\n"
            )

        consumer_path = os.path.join(tmpdir, "consumer.hunt")
        with open(consumer_path, "w") as f:
            f.write("")  # dummy

        # Named import
        directives = [ImportDirective(block_names=["Login"], source="lib.hunt", aliases={})]
        blocks, vars_ = resolve_imports(directives, tmpdir, consumer_path)
        _assert("Login" in blocks, "named import resolves Login")
        _assert(len(blocks["Login"]) == 2, "Login has 2 actions", f"{len(blocks['Login'])}")
        _assert(vars_.get("base_url") == "https://example.com", "import vars populated")

        # Aliased import
        directives2 = [ImportDirective(block_names=["Login"], source="lib.hunt", aliases={"Login": "AuthLogin"})]
        blocks2, _ = resolve_imports(directives2, tmpdir, consumer_path)
        _assert("AuthLogin" in blocks2, "aliased import resolves AuthLogin")
        _assert("Login" not in blocks2, "original name not present when aliased")

        # Wildcard import (only exported blocks)
        directives3 = [ImportDirective(block_names=["*"], source="lib.hunt", aliases={})]
        blocks3, _ = resolve_imports(directives3, tmpdir, consumer_path)
        _assert("Login" in blocks3, "wildcard includes Login")
        _assert("Logout" in blocks3, "wildcard includes Logout")
        _assert("Secret" not in blocks3, "wildcard excludes non-exported Secret")

        # Non-exported block raises
        directives4 = [ImportDirective(block_names=["Secret"], source="lib.hunt", aliases={})]
        try:
            resolve_imports(directives4, tmpdir, consumer_path)
            _assert(False, "raises on non-exported block")
        except HuntImportError:
            _assert(True, "HuntImportError on non-exported block")

        # Non-existent block raises
        directives5 = [ImportDirective(block_names=["NonExistent"], source="lib.hunt", aliases={})]
        try:
            resolve_imports(directives5, tmpdir, consumer_path)
            _assert(False, "raises on missing block")
        except HuntImportError:
            _assert(True, "HuntImportError on missing block")

        # Circular import detection
        a_path = os.path.join(tmpdir, "a.hunt")
        b_path = os.path.join(tmpdir, "b.hunt")
        with open(a_path, "w") as f:
            f.write("@export: StepA\n\nSTEP 1: StepA\n    Click 'A'\n")
        with open(b_path, "w") as f:
            f.write("@export: StepB\n\nSTEP 1: StepB\n    Click 'B'\n")
        # a imports from b, b imports from a → cycle when a is already in seen_files
        directives_cycle = [ImportDirective(block_names=["StepA"], source="a.hunt", aliases={})]
        try:
            resolve_imports(directives_cycle, tmpdir, a_path, seen_files={os.path.abspath(a_path)})
            _assert(False, "raises on circular import")
        except HuntImportError as e:
            _assert("Circular" in str(e), "circular import error message", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: expand_use_directives
# ═══════════════════════════════════════════════════════════════════════════════

def _test_expand_use() -> None:
    print("\n  ── expand_use_directives ─────────────────────────────────────")
    from manul_engine.imports import expand_use_directives, HuntImportError

    imported_blocks = {
        "Login": ["Fill 'User' with 'admin'", "Click 'Submit'"],
        "Logout": ["Click 'Logout'"],
    }

    # Simple expansion
    mission_lines = [
        "STEP 1: Auth flow\n",
        "    USE Login\n",
        "    VERIFY that 'Dashboard' is present\n",
    ]
    file_lines = [5, 6, 7]
    expanded, expanded_fl = expand_use_directives(mission_lines, file_lines, imported_blocks)
    _assert(len(expanded) == 4, "USE Login expanded to 2 lines + others", f"len={len(expanded)}")
    _assert("Fill 'User' with 'admin'" in expanded[1], "first action inserted")
    _assert("Click 'Submit'" in expanded[2], "second action inserted")
    _assert(expanded_fl[1] == 0, "synthetic line number for expanded action")
    _assert(expanded_fl[0] == 5, "non-USE line retains original line number")

    # Multiple USE
    mission2 = [
        "STEP 1: Flow\n",
        "    USE Login\n",
        "    VERIFY that 'Welcome' is present\n",
        "    USE Logout\n",
    ]
    file_lines2 = [1, 2, 3, 4]
    expanded2, _ = expand_use_directives(mission2, file_lines2, imported_blocks)
    _assert(len(expanded2) == 5, "double USE expanded correctly", f"len={len(expanded2)}")

    # Unknown USE raises
    mission3 = ["    USE NonExistent\n"]
    try:
        expand_use_directives(mission3, [1], imported_blocks)
        _assert(False, "raises on unknown USE reference")
    except HuntImportError:
        _assert(True, "HuntImportError on unknown USE reference")

    # USE is case-insensitive
    mission4 = ["    use Login\n"]
    expanded4, _ = expand_use_directives(mission4, [1], imported_blocks)
    _assert(len(expanded4) == 2, "case-insensitive USE expansion", f"len={len(expanded4)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 6: classify_step recognizes USE
# ═══════════════════════════════════════════════════════════════════════════════

def _test_classify_use() -> None:
    print("\n  ── classify_step: USE keyword ────────────────────────────────")
    from manul_engine.helpers import classify_step, RE_SYSTEM_STEP

    _assert(classify_step("USE Login") == "use_import", "classify: USE Login")
    _assert(classify_step("    USE Login") == "use_import", "classify: indented USE")
    _assert(classify_step("1. USE AuthLogin") == "use_import", "classify: numbered USE")
    _assert(RE_SYSTEM_STEP.search("USE Login") is not None, "RE_SYSTEM_STEP matches USE")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 7: ParsedHunt @import/@export integration
# ═══════════════════════════════════════════════════════════════════════════════

def _test_parse_hunt_file_imports() -> None:
    print("\n  ── ParsedHunt @import/@export round-trip ─────────────────────")
    from manul_engine.cli import parse_hunt_file

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a library file
        lib_path = os.path.join(tmpdir, "lib.hunt")
        with open(lib_path, "w") as f:
            f.write(
                "@export: Login\n"
                "@var: {lib_base} = https://lib.example.com\n"
                "\n"
                "STEP 1: Login\n"
                "    Fill 'User' with 'admin'\n"
                "    Click 'Submit'\n"
            )

        # Create consumer file
        consumer_path = os.path.join(tmpdir, "consumer.hunt")
        with open(consumer_path, "w") as f:
            f.write(
                "@context: Consumer test\n"
                "@title: Import Test\n"
                "@import: Login from lib.hunt\n"
                "@var: {my_var} = 42\n"
                "\n"
                "STEP 1: Do login\n"
                "    USE Login\n"
                "    VERIFY that 'Dashboard' is present\n"
                "DONE.\n"
            )

        hunt = parse_hunt_file(consumer_path)
        _assert(hunt.context == "Consumer test", "context parsed")
        _assert(hunt.title == "Import Test", "title parsed")
        _assert(len(hunt.imports) == 1, "1 import directive", f"{len(hunt.imports)}")
        _assert(hunt.imports[0].block_names == ["Login"], "import block name")
        _assert(hunt.exports == [], "no exports in consumer")
        _assert(hunt.parsed_vars.get("my_var") == "42", "local @var parsed")
        # The USE should be expanded in the mission text
        _assert("Fill 'User' with 'admin'" in hunt.mission, "USE expanded in mission")
        _assert("Click 'Submit'" in hunt.mission, "USE expansion includes all actions")
        _assert("USE Login" not in hunt.mission, "USE directive itself removed from mission")

        # Export-only file
        export_path = os.path.join(tmpdir, "export_only.hunt")
        with open(export_path, "w") as f:
            f.write(
                "@export: Login\n"
                "@export: Logout\n"
                "\n"
                "STEP 1: Login\n"
                "    Click 'Login'\n"
                "\n"
                "STEP 2: Logout\n"
                "    Click 'Logout'\n"
            )
        hunt2 = parse_hunt_file(export_path)
        _assert(hunt2.exports == ["Login", "Logout"], "exports parsed", f"{hunt2.exports}")
        _assert(hunt2.imports == [], "no imports in lib file")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 8: Variable precedence — import vars are lowest
# ═══════════════════════════════════════════════════════════════════════════════

def _test_import_variable_precedence() -> None:
    print("\n  ── Import variable precedence ────────────────────────────────")
    from manul_engine.variables import ScopedVariables

    sv = ScopedVariables()
    sv.set("url", "https://import.com", ScopedVariables.LEVEL_IMPORT)
    sv.set("url", "https://mission.com", ScopedVariables.LEVEL_MISSION)

    _assert(sv.resolve("url") == "https://mission.com", "mission overrides import")

    sv2 = ScopedVariables()
    sv2.set("url", "https://import.com", ScopedVariables.LEVEL_IMPORT)
    _assert(sv2.resolve("url") == "https://import.com", "import var resolves when alone")

    # All levels override import
    sv3 = ScopedVariables()
    sv3.set("x", "import", ScopedVariables.LEVEL_IMPORT)
    _assert(sv3.resolve("x") == "import", "import level baseline")
    sv3.set("x", "global", ScopedVariables.LEVEL_GLOBAL)
    _assert(sv3.resolve("x") == "global", "global overrides import")
    sv3.set("x", "mission", ScopedVariables.LEVEL_MISSION)
    _assert(sv3.resolve("x") == "mission", "mission overrides global+import")
    sv3.set("x", "step", ScopedVariables.LEVEL_STEP)
    _assert(sv3.resolve("x") == "step", "step overrides mission+global+import")
    sv3.set("x", "row", ScopedVariables.LEVEL_ROW)
    _assert(sv3.resolve("x") == "row", "row overrides all including import")

    # as_flat_dict includes import vars (lowest priority)
    sv4 = ScopedVariables()
    sv4.set("a", "import_a", ScopedVariables.LEVEL_IMPORT)
    sv4.set("b", "step_b", ScopedVariables.LEVEL_STEP)
    flat = sv4.as_flat_dict()
    _assert(flat.get("a") == "import_a", "import var in flat dict")
    _assert(flat.get("b") == "step_b", "step var in flat dict")

    # dump includes Level 5
    sv5 = ScopedVariables()
    sv5.set("imported_url", "https://lib.com", ScopedVariables.LEVEL_IMPORT)
    dump = sv5.dump()
    _assert("Level 5" in dump, "dump shows Level 5")
    _assert("Import" in dump, "dump shows Import label")
    _assert("{imported_url}" in dump, "dump shows import var")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 9: validate_exports
# ═══════════════════════════════════════════════════════════════════════════════

def _test_validate_exports() -> None:
    print("\n  ── validate_exports ──────────────────────────────────────────")
    from manul_engine.imports import validate_exports

    with tempfile.TemporaryDirectory() as tmpdir:
        # Valid exports
        good_path = os.path.join(tmpdir, "good.hunt")
        with open(good_path, "w") as f:
            f.write(
                "@export: Login\n"
                "\n"
                "STEP 1: Login\n"
                "    Click 'Login'\n"
            )
        warnings = validate_exports(good_path)
        _assert(len(warnings) == 0, "no warnings for valid exports")

        # Export with no matching block
        bad_path = os.path.join(tmpdir, "bad.hunt")
        with open(bad_path, "w") as f:
            f.write(
                "@export: NonExistent\n"
                "\n"
                "STEP 1: Login\n"
                "    Click 'Login'\n"
            )
        warnings2 = validate_exports(bad_path)
        _assert(len(warnings2) == 1, "warning for missing export block", f"{len(warnings2)}")
        _assert("NonExistent" in warnings2[0], "warning mentions block name")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n" + "=" * 60)
    print("  TEST 50 — @import / @export / USE System")
    print("=" * 60)

    _test_parse_import_directive()
    _test_resolve_source_path()
    _test_extract_exported_blocks()
    _test_resolve_imports()
    _test_expand_use()
    _test_classify_use()
    _test_parse_hunt_file_imports()
    _test_import_variable_precedence()
    _test_validate_exports()

    total = _PASS + _FAIL
    print(f"\n    SCORE: {_PASS}/{total}")
    if _FAIL:
        print(f"    \u26a0\ufe0f  {_FAIL} assertion(s) failed!")
    return _PASS, _FAIL
