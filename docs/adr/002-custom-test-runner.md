# ADR-002: Custom test runner instead of pytest

**Status:** Accepted
**Date:** 2026-04

## Context

ManulEngine needs a test suite that exercises heuristic scoring, DOM
resolution, and Playwright integration against synthetic HTML pages
served locally.  The suite must be deterministic — no network, no AI, no
external state.

## Decision

Use a custom `run_tests.py` / `_test_runner.py` harness instead of pytest.

Each `test_*.py` file exports an `async def run_suite(page, assert_eq)`,
receives a Playwright `Page` pointing at a local HTML fixture, and calls
a simple `assert_eq(actual, expected, label)` helper.  The runner
collects pass/fail counts and prints a summary.

## Consequences

- **Pro:** Zero external test-framework dependency.  `python run_tests.py`
  works out of the box after `pip install -e .`.
- **Pro:** Fixtures are served via `page.set_content(HTML)`, eliminating
  file I/O and network timing.
- **Pro:** Output format is tightly controlled — one line per assertion,
  a final scorecard, and exit code 0/1.
- **Con:** No built-in parametrise, markers, or fixture injection from
  pytest.
- **Con:** Contributors familiar with pytest need to learn the custom
  patterns.

## Mitigations

- Test files are short and self-contained (~50–100 assertions each).
- Adding a new test only requires creating `test_NN_name.py` with a
  `run_suite()` coroutine — the runner discovers it automatically.
- The custom runner is used only for the synthetic DOM laboratory.
  Integration hunts and user-facing tests use the standard `manul` CLI.
