#!/usr/bin/env python3
"""
🐾 manul.py — repository dev launcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Convenience wrapper for running Manul directly from the repository root
without installing the package.

All public hunt-runner logic lives in manul_engine/cli.py.
The internal test suite lives in manul_engine/_test_runner.py.
Demo integration hunts live in demo/ — use demo/run_demo.py to run them.

Usage:
  python manul.py test                     run internal synthetic DOM test suite (dev only)
  python manul.py .                        run all *.hunt files in CWD
  python manul.py path/to/file.hunt        run a single hunt file
  python manul.py --headless path/         headless mode
"""

import asyncio
import os
import sys

# Make manul_engine importable from the repo root without an editable install.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    # Intercept `test` before passing control to the public CLI so that the
    # test command is only available through this dev launcher.
    args = [a for a in sys.argv[1:] if a != "--headless"]
    if args and args[0] == "test":
        from manul_engine._test_runner import run_tests
        _reports_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(_reports_dir, exist_ok=True)
        log_path = os.path.join(_reports_dir, "last_test_run.log")
        all_ok = asyncio.run(run_tests(log_path))
        print(f"\n📄 Full test log saved to: {log_path}")
        sys.exit(0 if all_ok else 1)

    from manul_engine.cli import sync_main
    sync_main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🐾 Manul returned to the den.")
