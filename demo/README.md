# Demo Integration Hunts

This directory contains **integration demo** `.hunt` files that exercise ManulEngine
against real websites.  They require network access and installed Playwright browsers.

> **Note:** These are NOT unit/synthetic tests.  The synthetic DOM test suite lives
> in `manul_engine/test/` and is invoked with `python run_tests.py` from the repo root.

## Directory layout

```text
demo/
  run_demo.py                    Runner script (sets CWD, calls manul CLI)
  manul_engine_configuration.json  Demo-specific config (heuristics-only)
  pages.json                     Page-name registry for demo sites
  tests/                         Integration .hunt files
    saucedemo.hunt               E-commerce login + checkout flow (saucedemo.com)
    demoqa.hunt                  Forms, checkboxes, radios, tables (demoqa.com)
    mega.hunt                    All element types, drag-drop, shadow DOM
    rahul.hunt                   Radios, autocomplete, hovers
    call_python_variants.hunt    CALL PYTHON syntax showcase (hooks, aliases, args)
  scripts/                       Python helpers used by call_python_variants.hunt
  controls/                      Educational @custom_control examples
  examples/                      Additional Python helpers for CALL PYTHON demos
  playground/                    Experimental nested-module demos
  benchmarks/                    Adversarial benchmark suite (12 tasks, 5 HTML fixtures)
```

## Prerequisites

```bash
# From the repo root — install ManulEngine + Playwright browsers
pip install -e .
playwright install chromium
```

## Running demos

```bash
# Run ALL demo hunts (headed browser)
python demo/run_demo.py

# Run a single hunt
python demo/run_demo.py tests/saucedemo.hunt

# Headless mode
python demo/run_demo.py --headless

# Generate HTML report
python demo/run_demo.py --html-report

# Run with retries and screenshots
python demo/run_demo.py --retries 2 --screenshot on-fail --html-report

# Run with Firefox or WebKit
python demo/run_demo.py --browser firefox

# Or use the installed `manul` CLI directly (set CWD to demo/)
cd demo && manul tests/
cd demo && manul tests/saucedemo.hunt --headless
```

## Running benchmarks

```bash
cd demo/benchmarks
python run_benchmarks.py
```

## What each hunt demonstrates

| Hunt file | Real website | Key features |
|-----------|-------------|--------------|
| `saucedemo.hunt` | saucedemo.com | `@var` static variables, `NEAR` contextual qualifier, full checkout flow |
| `demoqa.hunt` | demoqa.com | Forms, checkboxes, radio buttons, web tables, date pickers |
| `mega.hunt` | testautomationpractice.blogspot.com | Drag-drop, shadow DOM, scroll, extract, pagination |
| `rahul.hunt` | rahulshettyacademy.com | Autocomplete, hover, negative assertions (`is NOT present`) |
| `call_python_variants.hunt` | *(no browser actions)* | `[SETUP]`/`[TEARDOWN]`, `@script` aliases, `CALL PYTHON` with args |
