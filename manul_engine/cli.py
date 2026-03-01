#!/usr/bin/env python3
# manul_engine/cli.py
"""
🐾 Manul CLI — Browser Automation Runner

Usage:
  manul .                            run all *.hunt files in the current directory
  manul path/to/folder/              run all *.hunt files in that folder
  manul path/to/script.hunt          run a specific hunt file
  manul --headless .                 any of the above in headless mode

Hunt file format: plain text, numbered steps, optional @context / @blueprint headers.
"""

import asyncio
import os
import sys
import time

# ─────────────────────────────────────────────────────────────────────────────
_USAGE = """
Usage:
  manul .                    — run all *.hunt files in the current directory
  manul path/to/folder/      — run all *.hunt files in that folder
  manul path/to/file.hunt    — run a single hunt file

Flags:
  --headless                 — run browser in headless mode

Examples:
  manul .
  manul tests/
  manul tests/hunt_example.hunt
  manul tests/my_script.hunt
  manul --headless tests/

Notes:
  Any file with the .hunt extension is accepted.
  The "hunt_" filename prefix is a convention only — not required.
"""

# ── Tee stdout → log file ─────────────────────────────────────────────────────
class _Tee:
    def __init__(self, path: str) -> None:
        self._term = sys.stdout
        self._file = open(path, "w", encoding="utf-8")

    def write(self, msg: str) -> None:
        self._term.write(msg)
        self._file.write(msg)

    def flush(self) -> None:
        self._term.flush()
        self._file.flush()

    def isatty(self) -> bool:
        return False

    def close(self) -> None:
        self._file.close()


# ── Parse .hunt file ─────────────────────────────────────────────────────────
def parse_hunt_file(filepath: str) -> tuple[str, str, str]:
    """Return (mission_body, context, blueprint) from a .hunt file."""
    context = ""
    blueprint = ""
    mission_lines: list[str] = []

    with open(filepath, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("@context:"):
                context = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("@blueprint:"):
                blueprint = stripped.split(":", 1)[1].strip()
            elif not stripped.startswith("#") and stripped:
                mission_lines.append(line)

    return "".join(mission_lines).strip(), context, blueprint


# ── Execute a single .hunt file ───────────────────────────────────────────────
async def _run_hunt_file(path: str, headless: bool) -> bool:
    filename = os.path.basename(path)
    print(f"\n{'='*60}")
    print(f"📜 EXECUTING MANUL HUNT: {filename}")
    print(f"{'='*60}")

    mission, context, blueprint = parse_hunt_file(path)

    if not mission:
        print(f"⚠️  Skipping {filename}: empty or comments-only.")
        return True

    if not context:
        context = filename.replace(".hunt", "").replace("_", " ").title()
    if blueprint:
        print(f"🧩 Blueprint: {blueprint}")
        context = f"[{blueprint}] {context}"

    from manul_engine import ManulEngine
    manul = ManulEngine(headless=headless)
    try:
        result = await manul.run_mission(mission, strategic_context=context)
        return bool(result)
    except Exception as exc:
        print(f"\n💥 CRASH: {exc}")
        import traceback
        traceback.print_exc(file=sys.stdout)
        return False


# ── Collect .hunt files from a path ──────────────────────────────────────────
def _collect(path: str) -> list[str]:
    """
    Resolve *path* to a list of absolute .hunt file paths.

    Accepted inputs:
      - path to a single .hunt file
      - path to a directory (collects all *.hunt inside it)
      - "." for the current working directory
    """
    abs_path = os.path.abspath(path)

    if os.path.isfile(abs_path):
        if not abs_path.endswith(".hunt"):
            print(f"❌ Not a .hunt file: {path}")
            sys.exit(1)
        return [abs_path]

    if os.path.isdir(abs_path):
        files = sorted(
            os.path.join(abs_path, f)
            for f in os.listdir(abs_path)
            if f.endswith(".hunt")
        )
        return files

    print(f"❌ Path not found: {path}")
    sys.exit(1)


# ── Main entry point ──────────────────────────────────────────────────────────
async def main() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = sys.argv[1:]

    if not args or any(a in args for a in ("--help", "-h")):
        print(_USAGE)
        sys.exit(0)

    headless = "--headless" in args
    args = [a for a in args if a != "--headless"]
    if not args:
        print(_USAGE)
        sys.exit(0)
    target = args[0]

    # ── Hunt files ────────────────────────────────────────────────────────
    log_file = os.path.join(os.getcwd(), "last_run.log")
    tee = _Tee(log_file)
    sys.stdout = tee

    try:
        files = _collect(target)

        if not files:
            print(f"📭 No .hunt files found in: {target}")
            return

        print(f"😼 Manul: found {len(files)} hunt file(s) in {os.path.abspath(target)}")

        results: list[tuple[str, str, float]] = []
        total_start = time.perf_counter()

        for path in files:
            t0 = time.perf_counter()
            success = await _run_hunt_file(path, headless)
            elapsed = time.perf_counter() - t0
            results.append((os.path.basename(path), "PASS" if success else "FAIL", elapsed))

        total = time.perf_counter() - total_start
        passed = sum(1 for _, s, _ in results if s == "PASS")

        print(f"\n\n{'='*20} HUNT SUMMARY {'='*20}")
        for name, status, secs in results:
            icon = "✅" if status == "PASS" else "❌"
            print(f"{icon} {name.ljust(34)} {status}  {secs:5.1f}s")
        print("=" * 60)
        print(f"   {passed}/{len(results)} passed  •  total {total:.1f}s")
        print("=" * 60)
        print(f"\n📄 Full log saved to: {log_file}")

        return len(results) - passed  # number of failures

    finally:
        sys.stdout = tee._term
        tee.close()


def sync_main() -> None:
    """Synchronous entry point registered as the `manul` console_scripts command."""
    try:
        failures = asyncio.run(main())
        if failures:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🐾 Manul returned to the den.")
