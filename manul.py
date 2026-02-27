#!/usr/bin/env python3
"""
🐾 Manul CLI — Browser Automation Runner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage:
  python manul.py                             run all hunt_*.py in ./tests/
  python manul.py hunt_login.py               run one test by filename
  python manul.py tests/hunt_login.py         run one test by path
  python manul.py --headless                  run all tests headless
  python manul.py hunt_login.py --headless    run one test headless
  python manul.py "1. Navigate to ..."        run an inline mission prompt
  python manul.py test                        run engine unit tests (60 traps)
"""

import asyncio
import importlib.util
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

    def isatty(self) -> bool:           # needed by some libraries
        return False

    def close(self) -> None:
        self._file.close()


# ── Execute a single hunt_*.py file ──────────────────────────────────────────
async def _run_file(path: str, headless: bool) -> bool:
    """Import a hunt_*.py module and call its main(), injecting headless if accepted."""
    print(f"\n{'='*54}")
    print(f"🐾 EXECUTING: {os.path.basename(path)}")
    print(f"{'='*54}")

    try:
        spec   = importlib.util.spec_from_file_location("_hunt_module", path)
        module = importlib.util.module_from_spec(spec)           # type: ignore[arg-type]
        spec.loader.exec_module(module)                          # type: ignore[union-attr]

        import inspect
        sig = inspect.signature(module.main)
        if "headless" in sig.parameters:
            result = await module.main(headless=headless)
        else:
            # Monkey-patch ManulEngine to honour the CLI headless flag
            import engine as _engine_pkg
            from engine import core as _engine
            _OrigEngine = _engine.ManulEngine
            class _PatchedEngine(_OrigEngine):
                def __init__(self, *a, **kw):
                    kw.setdefault("headless", headless)
                    super().__init__(*a, **kw)
            _engine.ManulEngine = _PatchedEngine
            _engine_pkg.ManulEngine = _PatchedEngine
            try:
                result = await module.main()
            finally:
                _engine.ManulEngine = _OrigEngine
                _engine_pkg.ManulEngine = _OrigEngine

        return bool(result)

    except Exception as exc:
        print(f"\n💥 CRASH: {exc}")
        import traceback
        traceback.print_exc()
        return False


# ── Run inline mission prompt ─────────────────────────────────────────────────
async def _run_prompt(prompt: str, headless: bool) -> None:
    from engine import ManulEngine
    print(f"\n{'='*54}")
    print("🐾 EXECUTING DIRECT HUNT")
    print(f"{'='*54}")
    print(f"📜 Mission: {prompt[:120]}{'…' if len(prompt) > 120 else ''}")

    manul  = ManulEngine(headless=headless)
    result = await manul.run_mission(prompt)
    status = "✅ ACCOMPLISHED" if result else "🙀 FAILED"
    print(f"\n{status}")


# ── Collect test files ────────────────────────────────────────────────────────
def _collect(target: str | None) -> list[str]:
    """Resolve target to a list of absolute file paths."""
    if target is None:
        if not os.path.isdir(TEST_DIR):
            print(f"❌ Tests directory not found: {TEST_DIR}")
            sys.exit(1)
        return sorted(
            os.path.join(TEST_DIR, f)
            for f in os.listdir(TEST_DIR)
            if f.startswith("hunt_") and f.endswith(".py")
        )

    # Try as-is, then inside TEST_DIR
    for candidate in [target, os.path.join(TEST_DIR, target)]:
        if os.path.isfile(candidate):
            return [os.path.abspath(candidate)]

    print(f"❌ File not found: {target}")
    sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────
async def main() -> None:
    # Ensure UTF-8 output for emoji-heavy logs on Windows.
    # This avoids UnicodeEncodeError under legacy codepages.
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    args     = sys.argv[1:]
    headless = "--headless" in args
    args     = [a for a in args if a != "--headless"]

    # Decide what to run
    target = args[0] if args else None

    # ── Engine unit tests ─────────────────────────────────────────────────
    if target == "test":
        import importlib
        import io
        import re as _re

        # Ensure UTF-8 output for emoji-heavy test suites on Windows
        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(
                sys.stdout.detach(), encoding="utf-8", errors="replace", line_buffering=True
            )

        # Tee test output to last_test_run.log + capture SCORE lines
        log_path = os.path.join(ROOT, "last_test_run.log")
        _real_stdout = sys.stdout
        _log_file    = open(log_path, "w", encoding="utf-8")
        _score_lines: list[str] = []

        class _TestTee:
            def write(self, msg):
                _real_stdout.write(msg)
                _log_file.write(msg)
                # Capture score lines for grand summary
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
        suite_results: list[tuple[str, int, int]] = []   # (name, passed, total)

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
            # Extract score from captured lines
            for sl in _score_lines[before:]:
                m = _re.search(r"(\d+)/(\d+)", sl)
                if m:
                    suite_results.append((mod_name, int(m.group(1)), int(m.group(2))))

        # ── Grand Summary ─────────────────────────────────────────────────
        total_passed = sum(p for _, p, _ in suite_results)
        total_tests  = sum(t for _, _, t in suite_results)

        print(f"\n\n{'=' * 70}")
        print("🐾 GRAND SUMMARY")
        print(f"{'=' * 70}")
        for name, p, t in suite_results:
            icon = "✅" if p == t else "❌"
            label = name.replace("test_", "").replace("_", " ").upper()
            print(f"   {icon} {label:<30} {p:>4}/{t}")
        print(f"{'─' * 70}")
        print(f"   {'TOTAL':<30} {total_passed:>4}/{total_tests}")
        if total_passed == total_tests:
            print("\n🏆 ALL TESTS PASSED — THE MANUL IS UNBREAKABLE!")
        print(f"{'=' * 70}")

        sys.stdout = _real_stdout
        _log_file.close()
        print(f"\n📄 Full test log saved to: {log_path}")
        sys.exit(0 if all_ok else 1)

    is_prompt = (
        target is not None
        and not target.endswith(".py")
        and not os.path.isfile(target)
        and not os.path.isfile(os.path.join(TEST_DIR, target))
    )

    # Mirror output to log file
    tee = _Tee(LOG_FILE)
    sys.stdout = tee

    try:
        if is_prompt:
            await _run_prompt(target, headless)
            return

        files = _collect(target)
        print(f"😼 Manul CLI: Found {len(files)} target(s) in hunting grounds.")

        results: list[tuple[str, str, float]] = []
        total_start = time.perf_counter()

        for path in files:
            t0      = time.perf_counter()
            success = await _run_file(path, headless)
            elapsed = time.perf_counter() - t0
            results.append((os.path.basename(path), "PASS" if success else "FAIL", elapsed))

        total = time.perf_counter() - total_start
        passed = sum(1 for _, s, _ in results if s == "PASS")

        # ── Summary ───────────────────────────────────────────────────────
        print(f"\n\n{'='*20} HUNT SUMMARY {'='*20}")
        for name, status, secs in results:
            icon  = "✅" if status == "PASS" else "❌"
            timer = f"{secs:5.1f}s"
            print(f"{icon} {name.ljust(34)} {status}  {timer}")
        print("="*54)
        print(f"   {passed}/{len(results)} passed  •  total {total:.1f}s")
        print("="*54)
        print(f"\n📄 Full log saved to: {LOG_FILE}")

    finally:
        sys.stdout = tee._term
        tee.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🐾 Manul returned to the den.")