---
name: run-hunt-tests
description: Run the ManulEngine synthetic-DOM test suite (manul_engine/test/test_*.py — 54 function-based suites, NOT unittest) and surface failures concisely. Invoke when the user says "run tests", "run the suite", "are tests passing", "запусти тести", or after non-trivial code changes to core.py / scoring.py / helpers.py / actions.py / cli.py before reporting work as done.
---

# run-hunt-tests

The repo ships a custom function-based suite under `manul_engine/test/` that exercises scoring, parsing, lifecycle, recording, scheduling, the DSL surface, and the reporter against synthetic DOM HTML — no external network. The convenience entry point is `run_tests.py` at the repo root.

**It is NOT unittest.** No test file defines a `unittest.TestCase`; each `test_*.py` exposes an async `run_laboratory()` / `run_suite()` that prints a `SCORE: <pass>/<total>` line, and `manul_engine/_test_runner.py` imports every module and calls that runner. Consequently `python -m unittest manul_engine.test.test_NN` reports "Ran 0 tests" — do **not** use it. Run a single suite as a script instead (see below).

## When to invoke

- User asks "run tests", "run the suite", "do the tests pass", "запусти тести".
- After editing any of: `manul_engine/core.py`, `manul_engine/scoring.py`, `manul_engine/helpers.py`, `manul_engine/actions.py`, `manul_engine/cli.py`, `manul_engine/cdp/*.py`, `manul_engine/debug.py` — before declaring the change done.
- After bumping the version (smoke test).

Do NOT invoke for docs-only changes or for edits confined to `contracts/`, `README*.md`, `custom-instructions/`.

## Execution order

Use the project venv interpreter (`.venv/bin/python`). The single runtime dependency is `websockets`; the browser-backed suites drive a **system Chrome/Chromium over CDP** (no Playwright, no bundled browser). If there is no venv or `import websockets` fails, set the environment up first via the **setup-dev-env** skill — do not pretend tests ran.

1. **Sanity check the environment.** `.venv/bin/python -c "import websockets"`. If it errors, run **setup-dev-env**, then retry. Stop if it still fails.
2. **Full suite (default).** `.venv/bin/python run_tests.py` from the repo root. This calls `_test_runner.run_tests`, which imports every `test_*.py` and invokes its `run_laboratory()`/`run_suite()`, forcing the in-session semantic cache off (`MANUL_SEMANTIC_CACHE_ENABLED=False`) for determinism. It writes a full log and prints a per-suite `pass/total` summary.
3. **Single suite (when targeted).** Run the file **as a script** — `.venv/bin/python manul_engine/test/test_NN_<name>.py` (e.g. `test_34_scoring_math`). Each file has a `__main__` block that calls its own runner. (`python -m unittest …` does NOT work — these aren't TestCases.)
4. **No-browser suites run anywhere.** Pure-logic suites (e.g. `test_34_scoring_math`, `test_49_explain_next`) need no browser and run as scripts on any host. Use these to validate scoring/parsing changes when no Chrome is available.
5. **Quick syntax-only check (no browser needed).** `.venv/bin/python -m py_compile manul_engine/*.py` — confirm parse-level correctness when you can't run the suite.

> **Browser note.** The browser-backed suites launch a system Chrome/Chromium over CDP via `CDPBrowser`. They run wherever a Chrome/Chromium binary is on `PATH` (set `MANUL_CHANNEL=chrome`/`chromium` or `executable_path` if it isn't auto-found). On a host without any Chrome, run the no-browser suites and state the limitation explicitly.

## Reporting results

- On full pass: report `<N> tests passed` and the wall-clock time. Do not paste the full verbose log.
- On any failure: paste the **last failing assertion + traceback** plus the test file:line. Do not paste passing tests. If multiple tests fail, group by the file they live in.
- If the suite errors out before running any test (import error, missing browser binary): say so explicitly, paste the error, do not claim "tests passed".

## Common pitfalls

- Tests are hermetic — they launch a system Chrome/Chromium over CDP and load synthetic DOM via `set_content()` / `file://` fixtures (no real network). A failure that reads "ERR_NETWORK" usually means a fixture wasn't written; investigate the test's setup, not the network.
- Some tests deliberately monkey-patch module globals in `prompts.py`. Run failing tests in isolation before deciding the failure is real — order-dependent failures point to a missing fixture cleanup, not a code bug.
- Scoring tests (`test_34_scoring_math`, `test_28_heuristic_weights`, `test_44_contextual_proximity`) carry **golden numbers**. If they fail after editing `scoring.py`, you likely changed a weight — confirm with the user before "fixing" the test by updating goldens.
- Tests have ruff per-file-ignores in `pyproject.toml` (`F841`, `F811`, etc.). Don't try to clean those up — they're intentional.

## Reference

- Entry point: `run_tests.py`
- Suite root: `manul_engine/test/`
- Conventions: `manul_engine/test/__init__.py` documents the synthetic-DOM helper API.
