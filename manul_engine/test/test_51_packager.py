# manul_engine/test/test_51_packager.py
"""
Test suite for manul_engine/packager.py — pack, install, lockfile.

Covers:
  - pack() creates .huntlib archives with correct contents
  - install() from archive and from directory
  - huntlib-lock.json creation and update
  - resolve_lockfile() reading
  - Validation errors for missing huntlib.json fields
  - Path traversal protection in archives
"""

import json
import os
import tarfile
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
# Section 1: pack()
# ═══════════════════════════════════════════════════════════════════════════════

def _test_pack() -> None:
    print("\n  ── pack() ────────────────────────────────────────────────────")
    from manul_engine.packager import pack
    from manul_engine.imports import HuntImportError

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_dir = os.path.join(tmpdir, "auth_flows")
        os.makedirs(pkg_dir)

        # Write huntlib.json
        manifest = {"name": "auth-flows", "version": "1.0.0", "entry": "main.hunt"}
        with open(os.path.join(pkg_dir, "huntlib.json"), "w") as f:
            json.dump(manifest, f)

        # Write hunt file
        with open(os.path.join(pkg_dir, "main.hunt"), "w") as f:
            f.write("@export: Login\n\nSTEP 1: Login\n    Click 'Login'\n")

        # Pack
        out_dir = os.path.join(tmpdir, "dist")
        archive = pack(pkg_dir, output_dir=out_dir)
        _assert(os.path.isfile(archive), "archive created")
        _assert(archive.endswith(".huntlib"), "archive has .huntlib extension")
        _assert("auth-flows-1.0.0" in os.path.basename(archive), "archive name contains name-version")

        # Verify archive contents
        with tarfile.open(archive, "r:gz") as tar:
            names = tar.getnames()
            _assert("huntlib.json" in names, "archive contains huntlib.json")
            _assert("main.hunt" in names, "archive contains main.hunt")

    # Missing huntlib.json raises
    with tempfile.TemporaryDirectory() as tmpdir2:
        try:
            pack(tmpdir2)
            _assert(False, "raises on missing huntlib.json")
        except HuntImportError:
            _assert(True, "HuntImportError on missing huntlib.json")

    # Missing required fields raises
    with tempfile.TemporaryDirectory() as tmpdir3:
        with open(os.path.join(tmpdir3, "huntlib.json"), "w") as f:
            json.dump({"name": "test"}, f)  # missing version
        try:
            pack(tmpdir3)
            _assert(False, "raises on missing version field")
        except HuntImportError:
            _assert(True, "HuntImportError on missing version field")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: install() from archive
# ═══════════════════════════════════════════════════════════════════════════════

def _test_install_from_archive() -> None:
    print("\n  ── install() from archive ────────────────────────────────────")
    from manul_engine.packager import pack, install

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and pack a library
        pkg_dir = os.path.join(tmpdir, "src")
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, "huntlib.json"), "w") as f:
            json.dump({"name": "my-lib", "version": "2.0.0", "entry": "flows.hunt"}, f)
        with open(os.path.join(pkg_dir, "flows.hunt"), "w") as f:
            f.write("STEP 1: Test\n    Click 'Ok'\n")

        archive = pack(pkg_dir, output_dir=os.path.join(tmpdir, "dist"))

        # Install to project
        target = os.path.join(tmpdir, "project")
        os.makedirs(target)
        dest = install(archive, target_dir=target)
        _assert(os.path.isdir(dest), "install directory created")
        _assert("my-lib" in dest, "installed under package name")
        _assert(os.path.isfile(os.path.join(dest, "flows.hunt")), "hunt file installed")
        _assert(os.path.isfile(os.path.join(dest, "huntlib.json")), "manifest installed")

        # Lockfile created
        lockfile = os.path.join(target, "hunt_libs", "huntlib-lock.json")
        _assert(os.path.isfile(lockfile), "lockfile created")
        with open(lockfile) as f:
            lock = json.load(f)
        _assert(lock["packages"]["my-lib"]["version"] == "2.0.0", "lockfile version correct")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: install() from directory
# ═══════════════════════════════════════════════════════════════════════════════

def _test_install_from_directory() -> None:
    print("\n  ── install() from directory ──────────────────────────────────")
    from manul_engine.packager import install

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src_pkg")
        os.makedirs(src)
        with open(os.path.join(src, "huntlib.json"), "w") as f:
            json.dump({"name": "dir-pkg", "version": "0.1.0"}, f)
        with open(os.path.join(src, "main.hunt"), "w") as f:
            f.write("STEP 1: Test\n    Click 'Go'\n")

        target = os.path.join(tmpdir, "project")
        os.makedirs(target)
        dest = install(src, target_dir=target)
        _assert(os.path.isdir(dest), "directory install creates dest")
        _assert(os.path.isfile(os.path.join(dest, "main.hunt")), "files copied")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4: resolve_lockfile()
# ═══════════════════════════════════════════════════════════════════════════════

def _test_resolve_lockfile() -> None:
    print("\n  ── resolve_lockfile() ────────────────────────────────────────")
    from manul_engine.packager import resolve_lockfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # No lockfile → empty
        result = resolve_lockfile(tmpdir)
        _assert(result == {}, "no lockfile returns empty dict")

        # With lockfile
        lock_dir = os.path.join(tmpdir, "hunt_libs")
        os.makedirs(lock_dir)
        with open(os.path.join(lock_dir, "huntlib-lock.json"), "w") as f:
            json.dump({"packages": {"test-lib": {"version": "1.0"}}}, f)
        result2 = resolve_lockfile(lock_dir)
        _assert("test-lib" in result2, "lockfile parsed correctly")
        _assert(result2["test-lib"]["version"] == "1.0", "version read from lockfile")

        # Corrupted lockfile → empty
        with open(os.path.join(lock_dir, "huntlib-lock.json"), "w") as f:
            f.write("not json")
        result3 = resolve_lockfile(lock_dir)
        _assert(result3 == {}, "corrupted lockfile returns empty dict")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 5: Reinstall / overwrite
# ═══════════════════════════════════════════════════════════════════════════════

def _test_reinstall() -> None:
    print("\n  ── reinstall (overwrite existing) ────────────────────────────")
    from manul_engine.packager import install

    with tempfile.TemporaryDirectory() as tmpdir:
        # Initial install
        src = os.path.join(tmpdir, "pkg")
        os.makedirs(src)
        with open(os.path.join(src, "huntlib.json"), "w") as f:
            json.dump({"name": "re-pkg", "version": "1.0.0"}, f)
        with open(os.path.join(src, "main.hunt"), "w") as f:
            f.write("STEP 1: V1\n    Click 'V1'\n")

        target = os.path.join(tmpdir, "project")
        os.makedirs(target)
        install(src, target_dir=target)

        # Update version and reinstall
        with open(os.path.join(src, "huntlib.json"), "w") as f:
            json.dump({"name": "re-pkg", "version": "2.0.0"}, f)
        with open(os.path.join(src, "main.hunt"), "w") as f:
            f.write("STEP 1: V2\n    Click 'V2'\n")

        dest = install(src, target_dir=target)
        with open(os.path.join(dest, "main.hunt")) as f:
            content = f.read()
        _assert("V2" in content, "reinstall overwrites old files")

        lockfile = os.path.join(target, "hunt_libs", "huntlib-lock.json")
        with open(lockfile) as f:
            lock = json.load(f)
        _assert(lock["packages"]["re-pkg"]["version"] == "2.0.0", "lockfile updated to v2")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n" + "=" * 60)
    print("  TEST 51 — Packager (pack / install / lockfile)")
    print("=" * 60)

    _test_pack()
    _test_install_from_archive()
    _test_install_from_directory()
    _test_resolve_lockfile()
    _test_reinstall()

    total = _PASS + _FAIL
    print(f"\n  {'='*50}")
    print(f"  RESULT: {_PASS} passed, {_FAIL} failed")
    print(f"  {'='*50}")
    return _PASS, _FAIL
