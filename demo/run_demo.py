#!/usr/bin/env python3
"""
🐾 run_demo.py — run integration demo hunts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Convenience script for running the demo .hunt files that ship
with the ManulEngine repository.  These are *integration* tests
hitting real websites (Sauce Demo, DemoQA, etc.) — they require
network access and installed Playwright browsers.

Usage (from the repo root):
  python demo/run_demo.py                       run all demo hunts (headed)
  python demo/run_demo.py --headless            run all demo hunts headless
  python demo/run_demo.py saucedemo.hunt        run a single hunt
  python demo/run_demo.py --html-report         generate HTML report

The script changes CWD to `demo/` so that manul_engine_configuration.json,
pages.json, controls/, and scripts/ are resolved correctly.
"""

import os
import sys

# Ensure the repo root (one level up) is on sys.path so manul_engine is importable.
_DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_DEMO_DIR)
sys.path.insert(0, _REPO_ROOT)

# Switch CWD to demo/ so config, pages, controls, scripts resolve from here.
os.chdir(_DEMO_DIR)

from manul_engine.cli import sync_main  # noqa: E402

if __name__ == "__main__":
    # If no target was given, default to tests/ subdir (all .hunt files).
    args = sys.argv[1:]
    if not any(a.endswith(".hunt") or os.path.isdir(a) or a == "." for a in args):
        args.append("tests")

    sys.argv = ["manul"] + args
    sync_main()
