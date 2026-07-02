---
name: setup-dev-env
description: Create a working Python virtualenv for ManulEngine and run its tests. ManulEngine drives a system Chrome/Chromium directly over CDP — there is no Playwright and no bundled-browser download. Invoke when the user says "create venv", "setup env", "set up the environment", "install deps", "створи венв", "налаштуй середовище", or when a test run fails with "No module named 'websockets'" or "Chrome/Chromium not found".
---

# setup-dev-env

ManulEngine is a CDP-native Python package: it drives a **system Chrome/Chromium** directly over the Chrome DevTools Protocol via a raw WebSocket. The single runtime dependency is `websockets` — there is **no Playwright and no bundled-browser download**. A clean dev loop needs three things: a virtualenv, the package installed editable, and a Chrome/Chromium binary on `PATH`.

## When to invoke

- User asks to "create a venv", "set up the dev environment", "install dependencies", "створи венв".
- A test/run attempt fails with `ModuleNotFoundError: No module named 'websockets'` (no venv / not installed) or `Chrome/Chromium not found` (no system browser on `PATH`).

## Creating the venv

The system Python here is **3.14 only**, and on this host `python3 -m venv` can fail (`ensurepip` missing — needs the `python3.14-venv` apt package, which needs sudo) and `pip` is **PEP 668 externally-managed**. The reliable, sudo-free path is the `virtualenv` package:

1. **Probe first.** `python3 --version`; `python3 -m venv .venv` — if it creates `.venv/bin/python`, use it and skip to step 3.
2. **Fallback to `virtualenv`** when `venv` is unavailable:
   ```bash
   pip3 install --user --break-system-packages -q virtualenv
   ~/.local/bin/virtualenv -p python3 .venv
   ```
   `--user --break-system-packages` installs `virtualenv` into the user site only; it does **not** touch system packages. (`requires-python` is `>=3.11`.)
3. **Install the package editable:**
   ```bash
   .venv/bin/python -m pip install -e .          # runtime only — pulls just `websockets`
   .venv/bin/python -m pip install -e ".[dev]"   # + build/twine/ruff/mypy (lint, format, package)
   ```
   There is no `[ai]` extra and no `playwright install` step — both were removed in 0.1.0.

Always invoke the interpreter as `.venv/bin/python` (do not rely on `source activate` persisting — the shell state resets between tool calls in this harness).

## The browser — a system Chrome on PATH

The CDP launcher (`manul_engine/cdp/chrome.py:find_chrome`) resolves a real binary in this precedence: explicit `executable_path` → `channel` mapping → `MANUL_CHANNEL` env → platform default candidates (`google-chrome-stable`, `google-chrome`, `chromium-browser`, `chromium`). So if any of those is on `PATH`, tests and engine runs work with **no extra setup**.

- **Verify a browser is present:** `command -v google-chrome chromium chromium-browser`.
- **If none is found / the wrong one is picked:** set `MANUL_CHANNEL=chrome` (or `chromium`), or `executable_path=/path/to/chrome`. `channel` is Chromium-only (`browser=chromium`, the default).
- **CI installs it via apt**, not Playwright: `sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium` (see `.github/workflows/synthetic-tests.yml`).
- Headless/sandbox: the launcher adds `--headless=new` when headless; on locked-down CI containers pass `--no-sandbox` via `MANUL_BROWSER_ARGS`.

## Running tests

The synthetic-DOM suite drives the system Chrome over CDP and loads fixtures via `set_content()` / `file://` (no real network), so the **full suite runs anywhere a Chrome/Chromium is present** — including this host.

```bash
.venv/bin/python run_tests.py                                 # full suite (54 function-based suites)
.venv/bin/python manul_engine/test/test_34_scoring_math.py    # single suite as a script
.venv/bin/python manul_engine/test/test_49_explain_next.py    # pure-logic suite, no browser needed
```

Pure-logic suites (scoring math, explain-next, parsing, config) need **no** browser and run on any host; use them when no Chrome is available. See the **run-hunt-tests** skill for result-reporting conventions.

## Common pitfalls

- Looking for a `playwright install` / `.[ai]` / Ollama step — none exists anymore. The only runtime dep is `websockets`; the browser is a system Chrome.
- Using `source .venv/bin/activate` and expecting it to persist — call `.venv/bin/python` explicitly each time.
- `pip install` without `--break-system-packages` for the one-time `virtualenv` bootstrap — it fails under PEP 668. (Never use that flag on the *project* install — that goes inside the venv, which is not externally-managed.)
- Reporting "the suite passed" when no Chrome was on `PATH` and only the no-browser suites ran — be explicit about what executed.
- Committing `.venv/` — it is build output. Confirm it is git-ignored; never `git add` it.

## Reference

- Runtime dep + extras: `pyproject.toml` → `[project].dependencies` (`websockets`) and `[project.optional-dependencies].dev`.
- Browser discovery: `manul_engine/cdp/chrome.py` (`find_chrome`, `_CHANNEL_BINARIES`, `_LINUX_CANDIDATES`).
- Channel/executable config: `MANUL_CHANNEL` / `channel`, `executable_path` — see `contracts/MANUL_CONFIG_CONTRACT.md`.
- Full-suite runner: `run_tests.py` and the `run-hunt-tests` skill.
