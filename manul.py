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
            from framework import engine as _engine
            _OrigEngine = _engine.ManulEngine
            class _PatchedEngine(_OrigEngine):
                def __init__(self, *a, **kw):
                    kw.setdefault("headless", headless)
                    super().__init__(*a, **kw)
            _engine.ManulEngine = _PatchedEngine
            try:
                result = await module.main()
            finally:
                _engine.ManulEngine = _OrigEngine

        return bool(result)

    except Exception as exc:
        print(f"\n💥 CRASH: {exc}")
        import traceback
        traceback.print_exc()
        return False


# ── Run inline mission prompt ─────────────────────────────────────────────────
async def _run_prompt(prompt: str, headless: bool) -> None:
    from framework.engine import ManulEngine
    print(f"\n{'='*54}")
    print("🐾 EXECUTING DIRECT HUNT")
    print(f"{'='*54}")
    print(f"📜 Mission: {prompt[:120]}{'…' if len(prompt) > 120 else ''}")

    manul  = ManulEngine(headless=headless)
    result = await manul.run_mission(prompt)
    status = "✅ ACCOMPLISHED" if result else "💀 FAILED"
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
    args     = sys.argv[1:]
    headless = "--headless" in args
    args     = [a for a in args if a != "--headless"]

    # Decide what to run
    target = args[0] if args else None
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
        print(f"🐱 Manul CLI: Found {len(files)} target(s) in hunting grounds.")

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