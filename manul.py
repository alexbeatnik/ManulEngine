#!/usr/bin/env python3
"""
🐾 Manul CLI — Browser Automation Runner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage:
  python manul.py                             run all *.hunt scripts in ./tests/
  python manul.py my_script.hunt              run a specific Manul script
  python manul.py custom_folder/              run all *.hunt scripts in a folder
  python manul.py --headless                  run scripts in headless mode
  python manul.py "1. Navigate to ..."        run an inline mission prompt
  python manul.py test                        run synthetic engine unit tests
"""

import asyncio
import os
import sys
import time

ROOT     = os.path.abspath(os.path.dirname(__file__))
TEST_DIR = os.path.join(ROOT, "tests")
LOG_FILE = os.path.join(ROOT, "last_run.log")

sys.path.insert(0, ROOT)


# ── Tee stdout → file ─────────────────────────────────────────────────────────
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


# ── Parse and Execute .hunt Script ────────────────────────────────────────────
def parse_hunt_file(filepath: str) -> tuple[str, str, str]:
    """Parse .hunt file to extract @context, @blueprint, and the mission body."""
    context = ""
    blueprint = ""
    mission_lines = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            # Parse meta tags
            if stripped.startswith('@context:'):
                context = stripped.split(':', 1)[1].strip()
            elif stripped.startswith('@blueprint:'):
                blueprint = stripped.split(':', 1)[1].strip()
            # Ignore comments, but keep mission lines
            elif not stripped.startswith('#') and stripped:
                mission_lines.append(line)

    mission = "".join(mission_lines).strip()
    return mission, context, blueprint


async def _run_hunt_script(path: str, headless: bool) -> bool:
    """Execute a .hunt text file mission."""
    filename = os.path.basename(path)
    print(f"\n{'='*60}")
    print(f"📜 EXECUTING MANUL HUNT: {filename}")
    print(f"{'='*60}")

    mission, context, blueprint = parse_hunt_file(path)

    if not mission:
        print(f"⚠️  Skipping {filename}: File is empty or only contains comments.")
        return True

    # Fallback context if not explicitly provided in the file
    if not context:
        context = filename.replace('.hunt', '').replace('_', ' ').title()

    if blueprint:
        print(f"🧩 Blueprint: {blueprint}")
        # Optionally merge blueprint into strategic context for the LLM
        context = f"[{blueprint}] {context}"

    from engine import ManulEngine
    manul = ManulEngine(headless=headless)
    
    try:
        result = await manul.run_mission(mission, strategic_context=context)
        return bool(result)
    except Exception as exc:
        print(f"\n💥 CRASH: {exc}")
        import traceback
        traceback.print_exc()
        return False


# ── Run inline mission prompt ─────────────────────────────────────────────────
async def _run_prompt(prompt: str, headless: bool) -> None:
    from engine import ManulEngine
    print(f"\n{'='*60}")
    print("🐾 EXECUTING DIRECT HUNT (INLINE)")
    print(f"{'='*60}")
    print(f"📜 Mission: {prompt[:120]}{'…' if len(prompt) > 120 else ''}")

    manul  = ManulEngine(headless=headless)
    result = await manul.run_mission(prompt, strategic_context="Inline CLI Mission")
    status = "✅ ACCOMPLISHED" if result else "🙀 FAILED"
    print(f"\n{status}")


# ── Collect test files ────────────────────────────────────────────────────────
def _collect(target: str | None) -> list[str]:
    """Resolve target to a list of absolute .hunt file paths."""
    files = []
    
    # 1. Default to TEST_DIR if nothing is provided
    if target is None:
        target_dir = TEST_DIR
    else:
        # 2. Check if target is a specific file
        if os.path.isfile(target) and target.endswith(".hunt"):
            return [os.path.abspath(target)]
        if os.path.isfile(os.path.join(TEST_DIR, target)) and target.endswith(".hunt"):
            return [os.path.abspath(os.path.join(TEST_DIR, target))]
            
        # 3. Check if target is a directory
        if os.path.isdir(target):
            target_dir = target
        elif os.path.isdir(os.path.join(TEST_DIR, target)):
            target_dir = os.path.join(TEST_DIR, target)
        else:
            # Not a valid .hunt file or directory.  Distinguish between a
            # likely filename/path and a free-form inline mission prompt.
            looks_like_path = (
                os.path.sep in target
                or target.endswith(".hunt")
                or os.path.exists(target)
                or os.path.exists(os.path.join(TEST_DIR, target))
            )
            if looks_like_path:
                print(f"\u274c Target is not a valid .hunt file or directory: {target}")
                sys.exit(1)
            return []  # Not a valid file/dir, probably an inline prompt

    if not os.path.isdir(target_dir):
        print(f"❌ Directory not found: {target_dir}")
        sys.exit(1)

    for f in os.listdir(target_dir):
        if f.endswith(".hunt"):
            files.append(os.path.abspath(os.path.join(target_dir, f)))

    return sorted(files)


# ── Entry point ───────────────────────────────────────────────────────────────
async def main() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args     = sys.argv[1:]
    headless = "--headless" in args
    args     = [a for a in args if a != "--headless"]

    target = args[0] if args else None

    # ── Engine unit tests (.py synthetic tests) ───────────────────────────
    if target == "test":
        import importlib
        import io
        import re as _re

        # Synthetic suites should be deterministic and side-effect free.
        # Disable persistent controls cache for the whole synthetic test run.
        os.environ["MANUL_DOTENV_OVERRIDE"] = "False"
        os.environ["MANUL_CONTROLS_CACHE_ENABLED"] = "False"
        try:
            from engine import prompts as _prompts
            _prompts.CONTROLS_CACHE_ENABLED = False
        except Exception:
            pass

        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(
                sys.stdout.detach(), encoding="utf-8", errors="replace", line_buffering=True
            )

        log_path = os.path.join(ROOT, "last_test_run.log")
        _real_stdout = sys.stdout
        _log_file    = open(log_path, "w", encoding="utf-8")
        _score_lines: list[str] = []

        class _TestTee:
            def write(self, msg):
                _real_stdout.write(msg)
                _log_file.write(msg)
                for line in msg.splitlines():
                    if "SCORE:" in line:
                        _score_lines.append(line.strip())
            def flush(self):
                _real_stdout.flush()
                _log_file.flush()
            def isatty(self):
                return False

        sys.stdout = _TestTee()

        test_dir = os.path.join(ROOT, "engine", "test")
        test_files = sorted(
            f[:-3] for f in os.listdir(test_dir)
            if f.startswith("test_") and f.endswith(".py")
        )
        all_ok = True
        suite_results: list[tuple[str, int, int]] = []

        for mod_name in test_files:
            full = f"engine.test.{mod_name}"
            mod  = importlib.import_module(full)
            runner = getattr(mod, "run_laboratory", None) or getattr(mod, "run_suite", None)
            if runner is None:
                continue
            before = len(_score_lines)
            ok = await runner()
            if not ok:
                all_ok = False
            for sl in _score_lines[before:]:
                m = _re.search(r"(\d+)/(\d+)", sl)
                if m:
                    suite_results.append((mod_name, int(m.group(1)), int(m.group(2))))

        total_passed = sum(p for _, p, _ in suite_results)
        total_tests  = sum(t for _, _, t in suite_results)

        print(f"\n\n{'=' * 70}")
        print("🐾 SYNTHETIC DOM LABORATORY SUMMARY")
        print(f"{'=' * 70}")
        for name, p, t in suite_results:
            icon = "✅" if p == t else "❌"
            label = name.replace("test_", "").replace("_", " ").upper()
            print(f"   {icon} {label:<30} {p:>4}/{t}")
        print(f"{'─' * 70}")
        print(f"   {'TOTAL':<30} {total_passed:>4}/{total_tests}")
        if total_passed == total_tests:
            print("\n🏆 ALL TESTS PASSED — THE ENGINE IS UNBREAKABLE!")
        print(f"{'=' * 70}")

        sys.stdout = _real_stdout
        _log_file.close()
        print(f"\n📄 Full test log saved to: {log_path}")
        sys.exit(0 if all_ok else 1)

    # ── .hunt Scripts or Inline Prompts ───────────────────────────────────────
    tee = _Tee(LOG_FILE)
    sys.stdout = tee

    try:
        files = _collect(target)
        
        # If no files found and target doesn't look like a file/dir, treat as inline prompt
        if not files and target and not target.endswith(".hunt") and not os.path.exists(target):
            await _run_prompt(target, headless)
            return
            
        if not files:
            print(f"📭 No .hunt scripts found in target: {target or TEST_DIR}")
            return

        print(f"😼 Manul CLI: Found {len(files)} target(s) in hunting grounds.")

        results: list[tuple[str, str, float]] = []
        total_start = time.perf_counter()

        for path in files:
            t0      = time.perf_counter()
            success = await _run_hunt_script(path, headless)
            elapsed = time.perf_counter() - t0
            results.append((os.path.basename(path), "PASS" if success else "FAIL", elapsed))

        total = time.perf_counter() - total_start
        passed = sum(1 for _, s, _ in results if s == "PASS")

        print(f"\n\n{'='*20} HUNT SUMMARY {'='*20}")
        for name, status, secs in results:
            icon  = "✅" if status == "PASS" else "❌"
            timer = f"{secs:5.1f}s"
            print(f"{icon} {name.ljust(34)} {status}  {timer}")
        print("="*60)
        print(f"   {passed}/{len(results)} passed  •  total {total:.1f}s")
        print("="*60)
        print(f"\n📄 Full log saved to: {LOG_FILE}")

    finally:
        sys.stdout = tee._term
        tee.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🐾 Manul returned to the den.")