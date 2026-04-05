#!/usr/bin/env python3
"""
🐾 run_tests.py — run the internal synthetic DOM test suite (dev only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs all test_*.py suites inside manul_engine/test/ against locally
rendered HTML pages.  No real websites, no internet required.

This script replaces the old `python manul.py test` invocation.

Usage (from the repo root):
  python run_tests.py
"""

import asyncio
import os
import sys

# Make manul_engine importable from the repo root without an editable install.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from manul_engine._test_runner import run_tests  # noqa: E402


def main() -> None:
    _reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(_reports_dir, exist_ok=True)
    log_path = os.path.join(_reports_dir, "last_test_run.log")
    all_ok = asyncio.run(run_tests(log_path))
    print(f"\n📄 Full test log saved to: {log_path}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🐾 Manul returned to the den.")
