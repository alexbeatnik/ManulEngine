#!/usr/bin/env python3
"""
🐾 manul.py — repository dev launcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Convenience wrapper for running Manul directly from the repository root
without installing the package.

All public hunt-runner logic lives in manul_engine/cli.py.
Synthetic test suite: python run_tests.py
Demo integration hunts: python demo/run_demo.py

Usage:
  python manul.py .                        run all *.hunt files in CWD
  python manul.py path/to/file.hunt        run a single hunt file
  python manul.py --headless path/         headless mode
"""

import os
import sys

# Make manul_engine importable from the repo root without an editable install.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    from manul_engine.cli import sync_main
    sync_main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🐾 Manul returned to the den.")
