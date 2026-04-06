# manul_engine/packager.py
"""
Hunt library packager — pack, publish, install .huntlib archives.

A .huntlib file is a gzip-compressed tarball containing:
  - huntlib.json   (manifest: name, version, entry, description, exports)
  - *.hunt files
  - optional helper modules referenced by CALL PYTHON

Layout after install:
  hunt_libs/<name>/       (local project install)
  ~/.manul/hunt_libs/<name>/  (global install with --global)
"""

from __future__ import annotations

import json
import os
import shutil
import tarfile
import tempfile

from .imports import HuntImportError, parse_huntlib_json


def _validate_manifest(manifest: dict, manifest_path: str) -> None:
    """Ensure required fields exist in huntlib.json."""
    required = ("name", "version")
    for key in required:
        if key not in manifest:
            raise HuntImportError(
                f"huntlib.json is missing required field '{key}': {manifest_path}"
            )


def pack(source_dir: str, output_dir: str | None = None) -> str:
    """Create a .huntlib archive from a directory containing huntlib.json.

    Returns the absolute path to the created archive.
    """
    source_dir = os.path.abspath(source_dir)
    manifest_path = os.path.join(source_dir, "huntlib.json")
    if not os.path.isfile(manifest_path):
        raise HuntImportError(
            f"No huntlib.json found in '{source_dir}'. "
            f"Run `manul pack` from a directory containing huntlib.json."
        )

    manifest = parse_huntlib_json(manifest_path)
    _validate_manifest(manifest, manifest_path)

    name = manifest["name"]
    version = manifest["version"]
    archive_name = f"{name}-{version}.huntlib"

    out = output_dir or source_dir
    os.makedirs(out, exist_ok=True)
    archive_path = os.path.join(out, archive_name)

    with tarfile.open(archive_path, "w:gz") as tar:
        for root, _dirs, files in os.walk(source_dir):
            for fname in files:
                full = os.path.join(root, fname)
                arcname = os.path.relpath(full, source_dir)
                # Skip the output archive itself and hidden files
                if full == archive_path or fname.startswith("."):
                    continue
                tar.add(full, arcname=arcname)

    return os.path.abspath(archive_path)


def install(
    source: str,
    target_dir: str | None = None,
    global_install: bool = False,
) -> str:
    """Install a .huntlib archive into hunt_libs/.

    *source* can be a path to a .huntlib file or a directory with huntlib.json.

    Returns the installation directory path.
    """
    if global_install:
        base = os.path.join(os.path.expanduser("~"), ".manul", "hunt_libs")
    else:
        base = os.path.join(target_dir or os.getcwd(), "hunt_libs")

    if os.path.isdir(source):
        # Install from directory — copy directly
        manifest_path = os.path.join(source, "huntlib.json")
        if not os.path.isfile(manifest_path):
            raise HuntImportError(f"No huntlib.json in '{source}'")
        manifest = parse_huntlib_json(manifest_path)
        _validate_manifest(manifest, manifest_path)

        dest = os.path.join(base, manifest["name"])
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(source, dest)

        _update_lockfile(base, manifest)
        return os.path.abspath(dest)

    # Install from .huntlib archive
    if not os.path.isfile(source):
        raise HuntImportError(f"Source not found: '{source}'")

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(source, "r:gz") as tar:
            # Security: prevent path traversal
            for member in tar.getmembers():
                if (
                    member.name.startswith("/")
                    or ".." in member.name
                    or member.issym()
                    or member.islnk()
                ):
                    raise HuntImportError(
                        f"Unsafe path in archive: '{member.name}'"
                    )
                # Verify resolved path stays within destination
                dest_path = os.path.realpath(os.path.join(tmp, member.name))
                if not dest_path.startswith(os.path.realpath(tmp) + os.sep) and dest_path != os.path.realpath(tmp):
                    raise HuntImportError(
                        f"Path traversal in archive: '{member.name}'"
                    )
            tar.extractall(tmp)

        manifest_path = os.path.join(tmp, "huntlib.json")
        if not os.path.isfile(manifest_path):
            raise HuntImportError(
                f"Archive does not contain huntlib.json: '{source}'"
            )

        manifest = parse_huntlib_json(manifest_path)
        _validate_manifest(manifest, manifest_path)

        dest = os.path.join(base, manifest["name"])
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(tmp, dest)

    _update_lockfile(base, manifest)
    return os.path.abspath(dest)


def _update_lockfile(hunt_libs_dir: str, manifest: dict) -> None:
    """Update huntlib-lock.json with the installed package info."""
    lockfile_path = os.path.join(hunt_libs_dir, "huntlib-lock.json")
    lock: dict = {}
    if os.path.isfile(lockfile_path):
        with open(lockfile_path, "r", encoding="utf-8") as f:
            try:
                lock = json.load(f)
            except json.JSONDecodeError:
                lock = {}

    if "packages" not in lock:
        lock["packages"] = {}

    name = manifest["name"]
    lock["packages"][name] = {
        "version": manifest["version"],
        "entry": manifest.get("entry", "main.hunt"),
    }

    os.makedirs(hunt_libs_dir, exist_ok=True)
    with open(lockfile_path, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2, ensure_ascii=False)
        f.write("\n")


def resolve_lockfile(hunt_libs_dir: str) -> dict:
    """Read the lockfile and return installed packages info."""
    lockfile_path = os.path.join(hunt_libs_dir, "huntlib-lock.json")
    if not os.path.isfile(lockfile_path):
        return {}
    with open(lockfile_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    return data.get("packages", {})
