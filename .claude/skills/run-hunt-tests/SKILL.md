---
name: run-hunt-tests
description: Run the ManulEngine synthetic-DOM unit-test suite (manul_engine/test/test_*.py — ~56 files) and surface failures concisely. Invoke when the user says "run tests", "run the suite", "are tests passing", "запусти тести", or after non-trivial code changes to core.py / scoring.py / helpers.py / actions.py / cli.py before reporting work as done.
---

# run-hunt-tests

The repo ships a unittest-based suite under `manul_engine/test/` that exercises scoring, parsing, lifecycle, recording, scheduling, the DSL surface, and the reporter against synthetic DOM HTML — no external network. The convenience entry point is `run_tests.py` at the repo root.

## When to invoke

- User asks "run tests", "run the suite", "do the tests pass", "запусти тести".
- After editing any of: `manul_engine/core.py`, `manul_engine/scoring.py`, `manul_engine/helpers.py`, `manul_engine/actions.py`, `manul_engine/cli.py`, `manul_engine/cache.py`, `manul_engine/debug.py` — before declaring the change done.
- After bumping the version (smoke test).

Do NOT invoke for docs-only changes or for edits confined to `contracts/`, `README*.md`, `custom-instructions/`.

## Execution order

1. **Sanity check the environment.** Run `python -c "import playwright"` first. If it errors, tell the user the suite needs `pip install -e .[dev]` and `playwright install chromium`, then stop — do not pretend tests ran.
2. **Full suite (default).** `python run_tests.py` from the repo root. The wrapper calls `python -m unittest discover manul_engine/test -v`.
3. **Single test (when targeted).** `python -m unittest manul_engine.test.test_NN_<name> -v` — e.g. `test_36_scoring_math`. Use this when the user names a specific area or when iterating on a single failure.
4. **Quick syntax-only check (no Playwright needed).** `python -m py_compile manul_engine/*.py` — useful when Playwright isn't installed and you only need to confirm parse-level correctness.

## Reporting results

- On full pass: report `<N> tests passed` and the wall-clock time. Do not paste the full verbose log.
- On any failure: paste the **last failing assertion + traceback** plus the test file:line. Do not paste passing tests. If multiple tests fail, group by the file they live in.
- If the suite errors out before running any test (import error, missing browser binary): say so explicitly, paste the error, do not claim "tests passed".

## Common pitfalls

- Tests are hermetic — they spawn `chromium` via Playwright against `/tmp/*.html` fixtures. A failure that reads "ERR_NETWORK" usually means a fixture wasn't written; investigate the test's `setUp`, not the network.
- Some tests deliberately monkey-patch module globals in `prompts.py`. Run failing tests in isolation before deciding the failure is real — order-dependent failures point to a missing fixture cleanup, not a code bug.
- Scoring tests (`test_36_scoring_math`, `test_30_heuristic_weights`, `test_47_contextual_proximity`) carry **golden numbers**. If they fail after editing `scoring.py`, you likely changed a weight — confirm with the user before "fixing" the test by updating goldens.
- Tests have ruff per-file-ignores in `pyproject.toml` (`F841`, `F811`, etc.). Don't try to clean those up — they're intentional.

## Reference

- Entry point: `run_tests.py`
- Suite root: `manul_engine/test/`
- Conventions: `manul_engine/test/__init__.py` documents the synthetic-DOM helper API.
