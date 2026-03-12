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

Hunt file format: plain text, numbered steps, optional @context / @title headers.
"""

import asyncio
import os
import re
import sys
import time
from typing import NamedTuple

from .reporting import StepResult, MissionResult, RunSummary

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
  --tags <tag1,tag2,...>     — only run hunt files whose @tags: header contains at least one matching tag
  --debug                    — interactive step-by-step mode with visual element highlighting
  --break-lines <n,n,...>    — pause before steps whose line numbers match (set by clicking the editor gutter)
  --retries <n>              — retry failed hunt files up to n times (pass on retry = flaky)
  --screenshot <mode>        — screenshot capture: on-fail (default), always, none
  --html-report              — generate a self-contained manul_report.html after the run

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
  manul --tags smoke tests/
  manul --tags smoke,regression tests/
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


# ── Structured return type for parse_hunt_file ───────────────────────────────
class ParsedHunt(NamedTuple):
    """Structured result of parsing a ``.hunt`` file.

    Behaves exactly like an 8-tuple for backward compatibility
    (positional indexing and unpacking both work), but also
    supports named attribute access.
    """
    mission: str
    context: str
    title: str
    step_file_lines: list[int]
    setup_lines: list[str]
    teardown_lines: list[str]
    parsed_vars: dict[str, str]
    tags: list[str]


# ── Parse .hunt file ─────────────────────────────────────────────────────────
def parse_hunt_file(filepath: str) -> ParsedHunt:
    """Return a :class:`ParsedHunt` with all parsed fields.

    *step_file_lines[i]* is the 1-based file line number of the *(i+1)*-th
    numbered step, in order of appearance.  Used to map editor gutter
    breakpoints to step indices that ManulEngine should pause before.
    Line numbers always refer to the **original** file, even when hook blocks
    are present — hook block lines are skipped transparently.

    *setup_lines* / *teardown_lines* contain the instruction strings extracted
    from ``[SETUP]`` / ``[TEARDOWN]`` blocks respectively, ready for
    execution by :func:`manul_engine.hooks.run_hooks`.

    *parsed_vars* contains key/value pairs declared with ``@var: {key} = value``
    at the top of the file.  Keys are stored without the surrounding ``{}``
    braces and are pre-populated into the engine's runtime memory before any
    step runs, enabling interpolation like ``Fill 'Email' with '{email}'``.

    *tags* contains the list of tag strings declared with ``@tags: tag1, tag2``
    at the top of the file.  If no ``@tags:`` line is present, returns ``[]``.
    Used by the CLI ``--tags`` flag to filter which hunt files are executed.
    """
    from .hooks import RE_SETUP, RE_END_SETUP, RE_TEARDOWN, RE_END_TEARDOWN

    context = ""
    title = ""
    parsed_vars: dict[str, str] = {}
    tags: list[str] = []
    mission_lines:  list[str] = []
    step_file_lines: list[int] = []
    setup_lines:    list[str] = []
    teardown_lines: list[str] = []
    in_setup    = False
    in_teardown = False

    with open(filepath, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            stripped = line.strip()

            # ── Hook block markers ─────────────────────────────────────────────
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
                continue
            if in_teardown:
                if stripped and not stripped.startswith("#"):
                    teardown_lines.append(stripped)
                continue

            # ── Normal mission line ────────────────────────────────────────────
            if stripped.startswith("@context:"):
                context = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("@title:") or stripped.startswith("@blueprint:"):
                title = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("@tags:"):
                raw_tags = stripped.split(":", 1)[1]
                tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            elif stripped.startswith("@var:"):
                var_part = stripped[5:].strip()
                m = re.match(r"\{?([^}=\s]+)\}?\s*=\s*(.*)", var_part)
                if m:
                    parsed_vars[m.group(1).strip()] = m.group(2).strip()
            elif not stripped.startswith("#") and stripped:
                mission_lines.append(line)
                if re.match(r'^\d+\.', stripped):
                    step_file_lines.append(lineno)

    return ParsedHunt(
        mission="".join(mission_lines).strip(),
        context=context,
        title=title,
        step_file_lines=step_file_lines,
        setup_lines=setup_lines,
        teardown_lines=teardown_lines,
        parsed_vars=parsed_vars,
        tags=tags,
    )


# ── Fast tag reader (header-only scan, no full parse) ────────────────────────
def _read_tags(path: str) -> list[str]:
    """Scan only the header lines of a .hunt file and return its @tags: values.

    Stops at the first numbered step line to avoid reading the whole file.
    Returns an empty list when no ``@tags:`` header is found.
    """
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("@tags:"):
                raw = stripped.split(":", 1)[1]
                return [t.strip() for t in raw.split(",") if t.strip()]
            if re.match(r'^\d+\.', stripped):
                break
    return []


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
    screenshot_mode: str = "none",
    global_vars: "dict[str, str] | None" = None,
) -> MissionResult:
    filename = os.path.basename(path)
    print(f"\n{'='*60}")
    print(f"📜 EXECUTING MANUL HUNT: {filename}")
    print(f"{'='*60}")

    hunt = parse_hunt_file(path)

    # Map file line numbers (from editor gutter breakpoints) to step indices.
    _break_lines = break_lines or set()
    break_steps: set[int] = {
        step_idx
        for step_idx, file_line in enumerate(hunt.step_file_lines, 1)
        if file_line in _break_lines
    }

    if not hunt.mission:
        print(f"⚠️  Skipping {filename}: empty or comments-only.")
        return MissionResult(file=path, name=filename, status="pass")

    context = hunt.context or filename.replace(".hunt", "").replace("_", " ").title()
    if hunt.title:
        print(f"🧩 Title: {hunt.title}")
        context = f"[{hunt.title}] {context}"

    from manul_engine import ManulEngine
    from manul_engine.hooks import run_hooks

    hunt_dir = os.path.dirname(os.path.abspath(path))

    # ── [SETUP] ───────────────────────────────────────────────────────────────
    # If setup fails, we skip the mission and teardown entirely — there is
    # nothing to clean up because setup never completed.
    if not run_hooks(hunt.setup_lines, label="SETUP", hunt_dir=hunt_dir):
        print(f"\n❌ SETUP failed — skipping mission and teardown for {filename}")
        return MissionResult(file=path, name=filename, status="fail", error="SETUP failed")

    manul = ManulEngine(headless=headless, browser=browser, debug_mode=debug, break_steps=break_steps)
    mission_result = MissionResult(file=path, name=filename, status="fail")
    # Merge global lifecycle vars (lower priority) with per-file @var: declarations
    # so that @var: can always override a global default.
    merged_vars: dict[str, str] = {**(global_vars or {}), **hunt.parsed_vars}
    try:
        mission_result = await manul.run_mission(
            hunt.mission,
            strategic_context=context,
            hunt_dir=hunt_dir,
            hunt_file=path,
            step_file_lines=hunt.step_file_lines,
            initial_vars=merged_vars,
            screenshot_mode=screenshot_mode,
        )
        mission_result.file = path
        mission_result.name = filename
        return mission_result
    except Exception as exc:
        print(f"\n💥 CRASH: {exc}")
        import traceback
        traceback.print_exc(file=sys.stdout)
        mission_result.error = str(exc)
        return mission_result
    finally:
        # ── [TEARDOWN] ────────────────────────────────────────────────────────
        # Always runs after setup succeeds, regardless of mission outcome.
        # Teardown failures are logged but do not override the mission result.
        run_hooks(hunt.teardown_lines, label="TEARDOWN", hunt_dir=hunt_dir)


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
        if a not in ("--headless", "--debug", "--html-report")
        and not (i > 0 and args[i - 1] in ("--browser", "--workers", "--output", "--break-lines", "--tags", "--retries", "--screenshot"))
        and a not in ("--browser", "--workers", "--output", "--break-lines", "--tags", "--retries", "--screenshot")
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
    html_report = "--html-report" in args
    args = [a for a in args if a not in ("--headless", "--debug", "--html-report")]

    # Extract --break-lines <n,n,...> flag (gutter breakpoints from VS Code).
    break_lines: set[int] = set()
    if "--break-lines" in args:
        idx = args.index("--break-lines")
        if idx + 1 >= len(args):
            print("Error: --break-lines requires a value (comma-separated line numbers).", file=sys.stderr)
            sys.exit(1)
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
    # --debug and --break-lines require interactive stdio and must run sequentially.
    # Passing them to parallel subprocess workers would cause stdin hangs; enforce
    # workers=1 automatically and warn the user if they requested more.
    if (debug or break_lines) and workers > 1:
        print(
            f"⚠️  --debug / --break-lines require sequential execution; forcing --workers 1"
            f" (was {workers}).",
            file=sys.stderr,
        )
        workers = 1

    # Extract --tags <tag1,tag2,...> filter
    filter_tags: set[str] = set()
    if "--tags" in args:
        idx = args.index("--tags")
        if idx + 1 >= len(args):
            print("Error: --tags requires a value (comma-separated tag names).", file=sys.stderr)
            sys.exit(1)
        filter_tags = {t.strip() for t in args[idx + 1].split(",") if t.strip()}
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    # Extract --retries <N> flag
    # Priority: CLI flag > MANUL_RETRIES env var > JSON config > 0
    from . import prompts as _prompts_cli
    retries: int = _prompts_cli.RETRIES
    if "--retries" in args:
        idx = args.index("--retries")
        if idx + 1 >= len(args):
            print("Error: --retries requires a number.", file=sys.stderr)
            sys.exit(1)
        try:
            retries = max(0, int(args[idx + 1]))
        except ValueError:
            print(f"Error: --retries value must be an integer, got '{args[idx + 1]}'.", file=sys.stderr)
            sys.exit(1)
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    # Extract --screenshot <mode> flag (on-fail | always | none)
    screenshot_mode: str = _prompts_cli.SCREENSHOT
    if "--screenshot" in args:
        idx = args.index("--screenshot")
        if idx + 1 >= len(args):
            print("Error: --screenshot requires a mode (on-fail, always, none).", file=sys.stderr)
            sys.exit(1)
        _ss_candidate = args[idx + 1].strip().lower()
        if _ss_candidate not in ("on-fail", "always", "none"):
            print(f"Error: --screenshot mode must be on-fail, always, or none; got '{args[idx + 1]}'.", file=sys.stderr)
            sys.exit(1)
        screenshot_mode = _ss_candidate
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    # Merge --html-report with config/env
    if not html_report:
        html_report = _prompts_cli.HTML_REPORT

    if not args:
        print(_USAGE)
        sys.exit(0)
    target = args[0]

    # ── Hunt files ────────────────────────────────────────────────────────
    import datetime as _dt
    _reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(_reports_dir, exist_ok=True)
    log_file = os.path.join(_reports_dir, "last_run.log")
    tee = _Tee(log_file)
    sys.stdout = tee

    run_summary: RunSummary | None = None
    results: list[tuple[str, str, float]] = []

    try:
        files = _collect(target)

        if not files:
            print(f"📭 No .hunt files found in: {target}")
            return

        # ── Tag filtering ─────────────────────────────────────────────────────
        if filter_tags:
            before = len(files)
            files = [f for f in files if filter_tags & set(_read_tags(f))]
            skipped = before - len(files)
            tag_str = ",".join(sorted(filter_tags))
            print(f"🏷️  --tags '{tag_str}': {skipped} file(s) skipped, {len(files)} matched.")
            if not files:
                print(f"📭 No .hunt files matched tags: {tag_str}")
                return

        print(f"😼 Manul: found {len(files)} hunt file(s) in {os.path.abspath(target)}")
        if retries:
            print(f"🔄 Retries enabled: up to {retries} retry(ies) per failed hunt")
        if screenshot_mode != "none":
            print(f"📸 Screenshot mode: {screenshot_mode}")
        if html_report:
            print(f"📊 HTML report: enabled")

        # ── Global lifecycle hooks ─────────────────────────────────────────────
        from .lifecycle import registry as _lc_registry, GlobalContext, load_hooks_file, serialize_global_vars, deserialize_global_vars
        _lc_registry.clear()          # reset any stale registrations from a previous run
        _lc_ctx = GlobalContext()
        # Inherit variables serialised by the orchestrator for parallel workers.
        _lc_ctx.variables.update(deserialize_global_vars())

        # Discover and load manul_hooks.py from the target directory.
        _target_dir = os.path.dirname(os.path.abspath(files[0])) if files else os.path.abspath(target)
        _hooks_loaded = load_hooks_file(_target_dir)
        if _hooks_loaded and not _lc_registry.is_empty:
            print(f"🪝  Lifecycle hooks loaded from: {os.path.join(_target_dir, 'manul_hooks.py')}")

        run_summary = RunSummary(started_at=_dt.datetime.now().isoformat())
        total_start = time.perf_counter()

        # ── @before_all ───────────────────────────────────────────────────────
        _before_all_ok = _lc_registry.run_before_all(_lc_ctx)
        if not _before_all_ok:
            print("\n❌ @before_all hook failed — aborting entire suite.")
            # Record all hunts as skipped and fall through to @after_all.
            for path in files:
                _mr = MissionResult(
                    file=path,
                    name=os.path.basename(path),
                    status="fail",
                    error="@before_all hook failed",
                )
                run_summary.missions.append(_mr)
                results.append((_mr.name, "FAIL", 0.0))
        elif workers == 1:
            # ── Sequential (default) ──────────────────────────────────────
            for path in files:
                file_tags = _read_tags(path)

                # ── @before_group ─────────────────────────────────────────
                _bg_ok = _lc_registry.run_before_group(file_tags, _lc_ctx)
                if not _bg_ok:
                    print(f"    ❌ @before_group hook failed — skipping {os.path.basename(path)}")
                    _lc_registry.run_after_group(file_tags, _lc_ctx)
                    _mr = MissionResult(
                        file=path,
                        name=os.path.basename(path),
                        status="fail",
                        error="@before_group hook failed",
                    )
                    run_summary.missions.append(_mr)
                    results.append((_mr.name, "FAIL", 0.0))
                    continue

                t0 = time.perf_counter()
                mission_result = await _run_hunt_file(
                    path, headless, browser, debug, break_lines,
                    screenshot_mode=screenshot_mode,
                    global_vars=_lc_ctx.variables,
                )
                # ── Retry loop ────────────────────────────────────────────
                if not mission_result and retries > 0:
                    for attempt in range(2, retries + 2):
                        print(f"\n🔄 RETRY {attempt - 1}/{retries} for {mission_result.name}")
                        mission_result = await _run_hunt_file(
                            path, headless, browser, debug, break_lines,
                            screenshot_mode=screenshot_mode,
                            global_vars=_lc_ctx.variables,
                        )
                        mission_result.attempts = attempt
                        if mission_result:
                            mission_result.status = "flaky"
                            print(f"    ⚠️  {mission_result.name} passed on retry {attempt - 1} — marked FLAKY")
                            break
                elapsed = time.perf_counter() - t0
                mission_result.duration_ms = elapsed * 1000
                run_summary.missions.append(mission_result)
                status_label = mission_result.status.upper()
                results.append((mission_result.name, status_label, elapsed))

                # ── @after_group ──────────────────────────────────────────
                _lc_registry.run_after_group(file_tags, _lc_ctx)
        else:
            # ── Parallel via subprocesses ─────────────────────────────────
            # Each hunt is spawned as a separate `manul <file>` subprocess so
            # that browsers run in truly separate processes (no shared Playwright
            # event loop) and stdout is captured cleanly without interleaving.
            print(f"\u2699\ufe0f  Running with up to {workers} parallel worker(s)\n")
            sem = asyncio.Semaphore(workers)
            manul_exe = _find_manul_exe()
            # Serialise ctx.variables so worker processes can inherit them.
            _global_vars_json = serialize_global_vars(_lc_ctx)

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
                # --debug and --break-lines require interactive stdio and must not
                # be forwarded to parallel subprocesses — workers is already forced
                # to 1 when either flag is set (see validation below).
                if browser:
                    flags += ["--browser", browser]
                if retries:
                    flags += ["--retries", str(retries)]
                if screenshot_mode is not None:
                    flags += ["--screenshot", screenshot_mode]
                # Do NOT forward --html-report: the parent process generates
                # the consolidated report; workers would overwrite each other.
                cmd = base + flags + [path]

                # Inject serialised global vars into the child's environment.
                child_env = {**os.environ, "MANUL_GLOBAL_VARS": _global_vars_json}

                async with sem:
                    t0 = time.perf_counter()
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        env=child_env,
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
                # Detect flaky status: child prints "marked FLAKY" when
                # a hunt passes on retry. Exit code is still 0 (pass).
                if status == "PASS" and "marked FLAKY" in output:
                    _child_status = "flaky"
                else:
                    _child_status = "pass" if status == "PASS" else "fail"
                _mr = MissionResult(
                    file="", name=name,
                    status=_child_status,
                    duration_ms=elapsed * 1000,
                )
                run_summary.missions.append(_mr)
                results.append((name, _child_status.upper(), elapsed))

        total = time.perf_counter() - total_start
        run_summary.ended_at = _dt.datetime.now().isoformat()
        run_summary.duration_ms = total * 1000
        run_summary.total = len(results)
        run_summary.passed = sum(1 for _, s, _ in results if s == "PASS")
        run_summary.failed = sum(1 for _, s, _ in results if s == "FAIL")
        run_summary.flaky  = sum(1 for _, s, _ in results if s == "FLAKY")
        passed = run_summary.passed + run_summary.flaky  # flaky counts as passed overall

        print(f"\n\n{'='*20} HUNT SUMMARY {'='*20}")
        for name, status, secs in results:
            if status == "PASS":
                icon = "✅"
            elif status == "FLAKY":
                icon = "⚠️ "
            else:
                icon = "❌"
            print(f"{icon} {name.ljust(34)} {status}  {secs:5.1f}s")
        print("=" * 60)
        _flaky_note = f"  ({run_summary.flaky} flaky)" if run_summary.flaky else ""
        print(f"   {passed}/{len(results)} passed{_flaky_note}  •  total {total:.1f}s")
        print("=" * 60)
        print(f"\n📄 Full log saved to: {log_file}")

        return run_summary.failed  # number of failures

    finally:
        # ── @after_all (always runs, even after exceptions) ────────────────
        try:
            _lc_registry.run_after_all(_lc_ctx)
        except Exception:
            pass  # _lc_registry / _lc_ctx may be unbound if setup failed early

        # ── HTML report generation (always runs, even after exceptions) ────
        if html_report and run_summary is not None and run_summary.missions:
            if not run_summary.ended_at:
                run_summary.ended_at = _dt.datetime.now().isoformat()
            if not run_summary.total:
                run_summary.total = len(results)
                run_summary.passed = sum(1 for _, s, _ in results if s == "PASS")
                run_summary.failed = sum(1 for _, s, _ in results if s == "FAIL")
                run_summary.flaky  = sum(1 for _, s, _ in results if s == "FLAKY")
            try:
                from .reporter import generate_report
                report_path = os.path.join(_reports_dir, "manul_report.html")
                generate_report(run_summary, report_path)
                print(f"\n✅ HTML Report saved to: {os.path.abspath(report_path)}")
            except Exception as _rpt_err:
                print(f"\n⚠️  HTML report generation failed: {_rpt_err}")

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
