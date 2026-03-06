#!/usr/bin/env python3
# manul_engine/cli.py
"""
🐾 Manul CLI — Browser Automation Runner

Usage:
  manul .                            run all *.hunt files in the current directory
  manul path/to/folder/              run all *.hunt files in that folder
  manul path/to/script.hunt          run a specific hunt file
  manul --headless .                 any of the above in headless mode
  manul --workers 4 tests/           run up to 4 hunt files in parallel

Hunt file format: plain text, numbered steps, optional @context / @blueprint headers.
"""

import asyncio
import os
import re
import sys
import time

# ─────────────────────────────────────────────────────────────────────────────
_USAGE = """
Usage:
  manul .                    — run all *.hunt files in the current directory
  manul path/to/folder/      — run all *.hunt files in that folder
  manul path/to/file.hunt    — run a single hunt file
  manul scan <URL>           — scan a URL and generate a draft .hunt file

Flags:
  --headless                 — run browser in headless mode
  --browser <name>           — browser to use: chromium (default), firefox, webkit
  --workers <n>              — max hunt files to run in parallel (default: 1)
  --debug                    — interactive step-by-step mode with visual element highlighting
  --break-lines <n,n,...>    — pause before steps whose line numbers match (set by clicking the editor gutter)

Scan-specific flags (only with `manul scan`):
  --output <file>            — output file for the draft (default: draft.hunt)

Examples:
  manul .
  manul tests/
  manul tests/hunt_example.hunt
  manul tests/my_script.hunt
  manul --headless tests/
  manul --browser firefox tests/
  manul --headless --browser webkit tests/hunt_example.hunt
  manul --workers 4 tests/
  manul scan https://example.com
  manul scan https://example.com --output tests/example.hunt --headless

Notes:
  Any file with the .hunt extension is accepted.
  The "hunt_" filename prefix is a convention only — not required.
  Browser can also be set via "browser" key in manul_engine_configuration.json
  or the MANUL_BROWSER environment variable.
  --workers can also be set via "workers" in manul_engine_configuration.json
  or the MANUL_WORKERS environment variable.
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
def parse_hunt_file(filepath: str) -> tuple[str, str, str, list[int]]:
    """Return (mission_body, context, blueprint, step_file_lines) from a .hunt file.

    step_file_lines[i] is the 1-based file line number of the (i+1)-th numbered
    step, in order of appearance.  Used to map editor gutter breakpoints to step
    indices that ManulEngine should pause before.
    """
    context = ""
    blueprint = ""
    mission_lines: list[str] = []
    step_file_lines: list[int] = []

    with open(filepath, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            stripped = line.strip()
            if stripped.startswith("@context:"):
                context = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("@blueprint:"):
                blueprint = stripped.split(":", 1)[1].strip()
            elif not stripped.startswith("#") and stripped:
                mission_lines.append(line)
                if re.match(r'^\d+\.', stripped):
                    step_file_lines.append(lineno)

    return "".join(mission_lines).strip(), context, blueprint, step_file_lines


# ── Find the current manul executable ───────────────────────────────────────
def _find_manul_exe() -> str:
    """Return the path used to invoke the current process (for subprocess workers)."""
    # If invoked as the installed `manul` console script, sys.argv[0] is the right path.
    candidate = os.path.abspath(sys.argv[0])
    if candidate.endswith(("manul", "manul.exe", "__main__.py")) and os.path.exists(candidate):
        return candidate
    # Try shutil.which as a more reliable lookup when argv[0] is just "manul".
    import shutil
    which = shutil.which("manul")
    if which:
        return which
    # Final fallback: use __main__.py next to this file so create_subprocess_exec
    # can prepend sys.executable and call it correctly.
    return str(os.path.join(os.path.dirname(__file__), "__main__.py"))


# ── Execute a single .hunt file ───────────────────────────────────────────────
async def _run_hunt_file(
    path: str,
    headless: bool,
    browser: "str | None" = None,
    debug: bool = False,
    break_lines: "set[int] | None" = None,
) -> bool:
    filename = os.path.basename(path)
    print(f"\n{'='*60}")
    print(f"📜 EXECUTING MANUL HUNT: {filename}")
    print(f"{'='*60}")

    mission, context, blueprint, step_file_lines = parse_hunt_file(path)

    # Map file line numbers (from editor gutter breakpoints) to step indices.
    _break_lines = break_lines or set()
    break_steps: set[int] = {
        step_idx
        for step_idx, file_line in enumerate(step_file_lines, 1)
        if file_line in _break_lines
    }

    if not mission:
        print(f"⚠️  Skipping {filename}: empty or comments-only.")
        return True

    if not context:
        context = filename.replace(".hunt", "").replace("_", " ").title()
    if blueprint:
        print(f"🧩 Blueprint: {blueprint}")
        context = f"[{blueprint}] {context}"

    from manul_engine import ManulEngine
    manul = ManulEngine(headless=headless, browser=browser, debug_mode=debug, break_steps=break_steps)
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

    # ── `manul scan <URL>` subcommand ─────────────────────────────────────────
    # Strip leading flags (--headless / --browser) before checking for "scan"
    # so that `manul --headless scan https://…` also works.
    _non_flag_args = [
        a for i, a in enumerate(args)
        if a not in ("--headless",)
        and not (i > 0 and args[i - 1] in ("--browser", "--workers", "--output", "--break-lines"))
        and a not in ("--browser", "--workers", "--output", "--break-lines")
    ]
    if _non_flag_args and _non_flag_args[0] == "scan":
        from manul_engine.scanner import scan_main
        # Pass everything before and after 'scan' (flags and their values).
        scan_idx = args.index("scan")
        scan_args = args[:scan_idx] + args[scan_idx + 1:]
        await scan_main(scan_args)
        return

    headless = "--headless" in args
    debug = "--debug" in args
    args = [a for a in args if a not in ("--headless", "--debug")]
    # Extract --break-lines <n,n,...> flag (gutter breakpoints from VS Code).
    break_lines: set[int] = set()
    if "--break-lines" in args:
        idx = args.index("--break-lines")
        if idx + 1 < len(args):
            try:
                break_lines = {int(x.strip()) for x in args[idx + 1].split(",") if x.strip()}
            except ValueError:
                print("Error: --break-lines values must be integers.", file=sys.stderr)
                sys.exit(1)
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
    # Extract --browser <name> flag
    _VALID_BROWSERS = {"chromium", "firefox", "webkit"}
    browser: str | None = None
    if "--browser" in args:
        idx = args.index("--browser")
        if idx + 1 >= len(args):
            print("Error: --browser requires a browser name (chromium, firefox, webkit).", file=sys.stderr)
            sys.exit(1)
        raw_candidate = args[idx + 1]
        candidate = raw_candidate.strip().lower()
        if candidate not in _VALID_BROWSERS:
            print(f"Error: unsupported browser '{raw_candidate}'. Allowed: chromium, firefox, webkit.", file=sys.stderr)
            sys.exit(1)
        browser = candidate
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
    # Extract --workers <n> flag
    # prompts.py (which maps JSON → env vars) hasn't been imported yet at this
    # point, so read 'workers' from the JSON config file directly.
    import json as _json, pathlib as _pathlib
    _cfg_path = _pathlib.Path.cwd() / "manul_engine_configuration.json"
    if not _cfg_path.exists():
        _cfg_path = _pathlib.Path(__file__).resolve().parents[1] / "manul_engine_configuration.json"
    _json_workers: int = 1
    if _cfg_path.exists():
        try:
            _json_workers = max(1, int(_json.loads(_cfg_path.read_text("utf-8")).get("workers", 1)))
        except Exception:
            pass
    # Priority: CLI flag (below) > MANUL_WORKERS env var > JSON config > 1
    workers = _json_workers
    _env_workers = os.getenv("MANUL_WORKERS")
    if _env_workers is not None:
        _env_workers_stripped = _env_workers.strip()
        if _env_workers_stripped:
            try:
                workers = max(1, int(_env_workers_stripped))
            except ValueError:
                pass  # fall back to JSON/default value
    if "--workers" in args:
        idx = args.index("--workers")
        if idx + 1 >= len(args):
            print("Error: --workers requires a number.", file=sys.stderr)
            sys.exit(1)
        try:
            workers = max(1, int(args[idx + 1]))
        except ValueError:
            print(f"Error: --workers value must be an integer, got '{args[idx + 1]}'.", file=sys.stderr)
            sys.exit(1)
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
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

        if workers == 1:
            # ── Sequential (default) ──────────────────────────────────────
            for path in files:
                t0 = time.perf_counter()
                success = await _run_hunt_file(path, headless, browser, debug, break_lines)
                elapsed = time.perf_counter() - t0
                results.append((os.path.basename(path), "PASS" if success else "FAIL", elapsed))
        else:
            # ── Parallel via subprocesses ─────────────────────────────────
            # Each hunt is spawned as a separate `manul <file>` subprocess so
            # that browsers run in truly separate processes (no shared Playwright
            # event loop) and stdout is captured cleanly without interleaving.
            print(f"\u2699\ufe0f  Running with up to {workers} parallel worker(s)\n")
            sem = asyncio.Semaphore(workers)
            manul_exe = _find_manul_exe()

            async def _run_subprocess(path: str) -> tuple[str, str, float, str]:
                # Build base command: executable + optional script path
                base: list[str]
                if manul_exe.endswith(".py"):
                    base = [sys.executable, manul_exe]
                else:
                    base = [manul_exe]
                # Flags first, then the hunt file path.
                # --workers 1 is mandatory: without it the child process would
                # read workers=N from JSON again and try to spawn grandchildren,
                # causing infinite subprocess recursion and a permanent hang.
                flags: list[str] = ["--workers", "1"]
                if headless:
                    flags.append("--headless")
                if debug:
                    flags.append("--debug")
                if break_lines:
                    flags += ["--break-lines", ",".join(str(l) for l in sorted(break_lines))]
                if browser:
                    flags += ["--browser", browser]
                cmd = base + flags + [path]

                async with sem:
                    t0 = time.perf_counter()
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                    )
                    raw, _ = await proc.communicate()
                    elapsed = time.perf_counter() - t0
                    output = raw.decode("utf-8", errors="replace")
                    status = "PASS" if proc.returncode == 0 else "FAIL"
                    return os.path.basename(path), status, elapsed, output

            tasks = [asyncio.create_task(_run_subprocess(p)) for p in files]
            subprocess_results = await asyncio.gather(*tasks)

            # Print each hunt's buffered output in original submission order
            for name, status, elapsed, output in subprocess_results:
                print(output, end="")
                results.append((name, status, elapsed))

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
