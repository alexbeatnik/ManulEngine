---
name: setup-dev-env
description: Create a working Python virtualenv for ManulEngine and run its tests, including the workaround for hosts where Playwright has no prebuilt browser (e.g. ubuntu26.04) — drive the system Chrome via channel='chrome' / MANUL_CHANNEL. Invoke when the user says "create venv", "setup env", "set up the environment", "install deps", "створи венв", "налаштуй середовище", or when a test run fails with "No module named 'playwright'" / "does not support chromium on <os>".
---

# setup-dev-env

This repo is a Playwright-based Python package. A clean dev loop needs three things: a virtualenv, the package installed editable with its extras, and a browser Playwright can drive. On bleeding-edge hosts the third step is the one that bites — Playwright ships no prebuilt browser for very new distros, so you fall back to the system Chrome.

## When to invoke

- User asks to "create a venv", "set up the dev environment", "install dependencies", "створи венв".
- A test/run attempt fails with `ModuleNotFoundError: No module named 'playwright'` (no venv / not installed) or `Playwright does not support <browser> on <os>` (no prebuilt browser for this host).

## Creating the venv

The system Python here is **3.14 only**, and on this host `python3 -m venv` fails (`ensurepip` missing — needs the `python3.14-venv` apt package, which needs sudo) and `pip` is **PEP 668 externally-managed**. The reliable, sudo-free path is the `virtualenv` package:

1. **Probe first.** `python3 --version`; `python3 -m venv .venv` — if it creates `.venv/bin/python`, use it and skip to step 3.
2. **Fallback to `virtualenv`** when `venv` is unavailable:
   ```bash
   pip3 install --user --break-system-packages -q virtualenv
   ~/.local/bin/virtualenv -p python3.14 .venv
   ```
   `--user --break-system-packages` installs `virtualenv` into the user site only; it does **not** touch system packages.
3. **Install the package editable with extras:**
   ```bash
   .venv/bin/python -m pip install -e ".[dev]"     # playwright + ollama + test tooling
   ```
   Use `".[ai]"` if the user only wants the Ollama self-healing extra, plain `-e .` for runtime-only.

Always invoke the interpreter as `.venv/bin/python` (do not rely on `source activate` persisting — the shell state resets between tool calls in this harness).

## Browser binaries — the host caveat

`.venv/bin/python -m playwright install chromium` (also `firefox`, `webkit`) **fails on this host**:

```
ERROR: Playwright does not support chromium on ubuntu26.04-x64
```

`PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04` changes the *message* but still finds no matching build — there is genuinely no prebuilt browser for this distro in the pinned Playwright release. Do **not** burn time retrying overrides.

The workaround: a **system browser** is present (`/usr/bin/google-chrome`, `/usr/bin/firefox`) and Playwright 1.60 can drive Chrome through the `channel` option:

```bash
.venv/bin/python - <<'PY'
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True)
        pg = await b.new_page(); await pg.set_content("<button>Hi</button>")
        print("OK:", await pg.inner_text("button")); await b.close()
asyncio.run(main())
PY
```

For engine runs via `ManulSession` / the `manul` CLI, set **`MANUL_CHANNEL=chrome`** (config key `channel`) — `api.py` passes it straight to `launch()`. This only works with `browser=chromium` (the default); channel is Chromium-only.

## Running tests on this host

- **Pure-logic tests need no browser** and run as-is — they are plain scripts with a `__main__` runner, not unittest-discoverable:
  ```bash
  .venv/bin/python manul_engine/test/test_49_explain_next.py   # 112 assertions, exercises llm.py + explain_next.py
  .venv/bin/python manul_engine/test/test_34_scoring_math.py   # scoring goldens, no DOM
  ```
- **Browser-backed tests** (`test_01_ecommerce.py` … `test_15_*`, etc.) call `p.chromium.launch()` **directly with no channel**, so they require the bundled Chromium — they will **not** run on this host without patching each test to pass `channel="chrome"`. Do not claim the full suite passed here; run the no-browser tests, state the browser-test limitation explicitly, and defer to `run-hunt-tests` on a supported host.

## Common pitfalls

- Reporting "the suite passed" after only the no-browser tests ran. Be explicit about which tests executed and why the rest were skipped.
- Using `source .venv/bin/activate` and expecting it to persist — call `.venv/bin/python` explicitly each time.
- Retrying `playwright install` with platform overrides — it cannot succeed on an unsupported distro; go straight to `channel="chrome"`.
- `pip install` without `--break-system-packages` for the one-time `virtualenv` bootstrap — it fails under PEP 668. (Never use that flag on the *project* install — that goes inside the venv, which is not externally-managed.)
- Committing `.venv/` — it is build output. Confirm it is git-ignored; never `git add` it.

## Reference

- Extras: `pyproject.toml` → `[project.optional-dependencies]` (`ai`, `dev`).
- Launch path / channel handling: `manul_engine/api.py` (`_launch_opts["channel"] = eng.channel`).
- Channel config key: `MANUL_CHANNEL` / `channel` — see `contracts/MANUL_CONFIG_CONTRACT.md`.
- Full-suite runner (supported hosts): `run_tests.py` and the `run-hunt-tests` skill.
