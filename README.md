<p align="center">
  <img src="images/manul.png" alt="ManulEngine mascot" width="180" />
</p>

# ManulEngine

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-d97706)](#status)

Deterministic, DSL-first web and desktop automation backed by Playwright, with a standalone Python API and optional local AI fallback for ambiguous cases.

## Status

ManulEngine is a solo-developed alpha-stage runtime.

Bugs are expected. APIs may change. There are no promises of stability, support, or production readiness. The project is meant for exploration, technical feedback, and transparent failure analysis rather than production CI/CD guarantees.

## What It Is

ManulEngine is no longer just a CLI that runs `.hunt` files. It is a standalone Python module with two primary authoring layers:

- `.hunt` DSL for readable QA, RPA, monitoring, and agent-target flows
- `ManulSession` for direct programmatic automation in pure Python

Both layers route through the same runtime: deterministic DOM snapshotting, weighted heuristic scoring, optional local AI fallback, structured reporting, and Playwright execution.

## Why It Exists

Most browser automation failures are hard to diagnose because the runtime tells you what failed, not why. ManulEngine is built around the opposite approach:

- Deterministic resolution first, not AI-first execution
- Explainable heuristics with normalized `0.0` to `1.0` confidence semantics
- A shared artifact model for QA-friendly DSL and SDET-grade Python escape hatches
- Local execution only, including desktop automation through `OPEN APP` and `executable_path`

## Core Capabilities

- Standalone Python API through `ManulSession`
- Hunt DSL runtime for web, desktop, RPA, synthetic monitoring, and constrained agent actions
- Smart Lazy Loading (JIT) for Controls: only the custom control modules required by the current hunt are loaded before execution
- Hierarchical Step-level Reporting: `STEP` declarations become parent blocks, actions run beneath them, and a block passes only if all hard actions pass
- Structured stdout logging for block-aware UI parsing
- Deterministic `DOMScorer` heuristics with optional local Ollama fallback when confidence is low
- Shadow DOM, iframe, overlay, and custom widget handling
- Persistent controls cache and in-session semantic cache reuse
- Hooks, variables, tags, data-driven runs, screenshots, retries, and HTML reporting

## Four Automation Pillars

The same runtime supports four adjacent use cases:

1. QA and E2E flows
2. RPA and form-driving workflows
3. Synthetic monitors with `@schedule:` and `manul daemon`
4. Constrained browser execution targets for external agents

## Public Python API

`ManulSession` is the clean API surface for users who want to write automation directly in Python without authoring `.hunt` files.

```python
import asyncio

from manul_engine import ManulSession


async def main() -> None:
    async with ManulSession(headless=True) as session:
        await session.navigate("https://www.saucedemo.com/")
        await session.fill("Username field", "standard_user")
        await session.fill("Password field", "secret_sauce")
        await session.click("Login button")
        await session.verify("Products")
        price = await session.extract("Backpack price")
        print({"price": price})


asyncio.run(main())
```

`ManulSession` also supports `run_steps()` when you want to mix Python orchestration with short inline DSL fragments.

```python
import asyncio

from manul_engine import ManulSession


async def main() -> None:
    async with ManulSession() as session:
        await session.navigate("https://example.com")
        result = await session.run_steps(
            """
STEP 1: Search
    Fill 'Search' with 'ManulEngine'
    PRESS Enter
    VERIFY that 'Results' is present
DONE.
"""
        )
        assert result.status == "pass"


asyncio.run(main())
```

## Hunt DSL

The canonical format for new `.hunt` files is STEP-grouped and unnumbered.

```text
@context: SauceDemo smoke flow
@title: saucedemo_smoke
@var: {username} = standard_user
@var: {password} = secret_sauce

STEP 1: Login
    NAVIGATE to https://www.saucedemo.com/
    Fill 'Username' field with '{username}'
    Fill 'Password' field with '{password}'
    Click the 'Login' button
    VERIFY that 'Products' is present

STEP 2: Add item
    Click the 'Add to cart' button
    VERIFY that '1' is present

DONE.
```

The runtime now executes these files as hierarchical blocks:

- `STEP` lines are parent containers
- indented commands are child actions
- block execution is fail-fast for hard failures
- block and action state are both available for reports and UI integrations

## Structured Logging

When a hunt runs, stdout is now block-aware and regex-friendly.

```text
[📦 BLOCK START] STEP 1: Login
  [▶️ ACTION START] NAVIGATE to https://www.saucedemo.com/
  [✅ ACTION PASS] duration: 2.33s
  [▶️ ACTION START] Fill 'Username' field with 'standard_user'
  [✅ ACTION PASS] duration: 0.84s
[🟩 BLOCK PASS] STEP 1: Login
```

If a hard action fails, the rest of that block is skipped and the block is marked failed.

## Explainability

The recommended default remains heuristics-only mode.

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true,
  "semantic_cache_enabled": true
}
```

Useful explainability workflows:

- `manul --explain tests/saucedemo.hunt`
- VS Code debug pauses with step-local explainability
- HTML reports with per-action status and screenshots

The engine frames confidence in normalized heuristic terms. The local LLM, when enabled, is a fallback rather than the primary resolver.

## Desktop Automation

ManulEngine can drive Electron and other custom Chromium-based desktop apps through Playwright.

```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "/path/to/electron-app"
}
```

```text
STEP 1: Attach to the app
    OPEN APP
    VERIFY that 'Welcome' is present

STEP 2: Navigate settings
    Click the 'Settings' button
    VERIFY that 'Preferences' is present

DONE.
```

## Variables, Hooks, and Python Escape Hatches

The runtime keeps readable business flow in the DSL and pushes environment-specific or backend-specific logic into Python.

- `@var:` for static variables
- `SET {name} = value` for runtime assignment
- `EXTRACT ... into {var}` for UI-derived values
- `CALL PYTHON ... into {var}` for computed or backend-derived values
- `[SETUP]` and `[TEARDOWN]` for file-local orchestration
- `manul_hooks.py` with lifecycle decorators for suite-wide orchestration
- `@custom_control` for complex widgets that should bypass generic heuristics

## Smart Lazy Loading for Controls

Custom controls are no longer eagerly imported as a blanket startup step for every run. Before a hunt executes, the CLI extracts the required control names from the mission and loads only the matching modules from `controls/`.

That reduces cold-start noise, keeps unrelated handler side effects out of the run, and makes large control libraries more manageable.

## Installation

From PyPI:

```bash
pip install manul-engine==0.0.9.8
playwright install chromium
```

Optional local AI fallback:

```bash
pip install "manul-engine[ai]==0.0.9.8"
ollama pull qwen2.5:0.5b
ollama serve
```

## Configuration

Create `manul_engine_configuration.json` in the workspace root. All keys are optional. Environment variables always override JSON values.

```json
{
  "model": null,
  "headless": false,
  "browser": "chromium",
  "browser_args": [],
  "ai_threshold": null,
  "ai_always": false,
  "ai_policy": "prior",
  "controls_cache_enabled": true,
  "controls_cache_dir": "cache",
  "semantic_cache_enabled": true,
  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "timeout": 5000,
  "nav_timeout": 30000,
  "tests_home": "tests",
  "auto_annotate": false,
  "channel": null,
  "executable_path": null,
  "retries": 0,
  "screenshot": "on-fail",
  "html_report": false
}
```

Configuration reference:

| Key | Default | Description |
| --- | --- | --- |
| `model` | `null` | Ollama model name. `null` keeps the runtime heuristics-only. |
| `headless` | `false` | Run the browser headless. |
| `browser` | `"chromium"` | Browser engine: `chromium`, `firefox`, or `webkit`. |
| `browser_args` | `[]` | Extra launch flags passed to the browser. |
| `ai_threshold` | auto | Score threshold before optional LLM fallback. |
| `ai_always` | `false` | Always ask the LLM picker. Forced off when `model` is `null`. |
| `ai_policy` | `"prior"` | Treat heuristic score as a hint or a strict constraint. |
| `controls_cache_enabled` | `true` | Enable the persistent per-site controls cache. |
| `controls_cache_dir` | `"cache"` | Cache directory relative to CWD or absolute path. |
| `semantic_cache_enabled` | `true` | Enable in-session semantic cache reuse. |
| `log_name_maxlen` | `0` | Truncate element names in logs. `0` disables truncation. |
| `log_thought_maxlen` | `0` | Truncate LLM thought strings in logs. `0` disables truncation. |
| `timeout` | `5000` | Default action timeout in milliseconds. |
| `nav_timeout` | `30000` | Navigation timeout in milliseconds. |
| `tests_home` | `"tests"` | Default output directory for generated hunts. |
| `auto_annotate` | `false` | Insert `# 📍 Auto-Nav:` comments after URL changes during a run. |
| `channel` | `null` | Installed browser channel such as `chrome` or `msedge`. |
| `executable_path` | `null` | Absolute path to a custom executable such as Electron. |
| `retries` | `0` | Retry failed hunt files this many times. |
| `screenshot` | `"on-fail"` | Screenshot mode: `none`, `on-fail`, or `always`. |
| `html_report` | `false` | Generate `reports/manul_report.html` after the run. |

Representative environment overrides:

```bash
export MANUL_HEADLESS=true
export MANUL_BROWSER=firefox
export MANUL_MODEL=qwen2.5:0.5b
export MANUL_CHANNEL=chrome
export MANUL_EXECUTABLE_PATH=/path/to/electron-app
```

## CLI Quick Start

```bash
manul tests/
manul tests/saucedemo.hunt
manul --headless tests/
manul --browser firefox tests/
manul --tags smoke tests/
manul --retries 2 --screenshot on-fail --html-report tests/
manul --explain tests/saucedemo.hunt
manul scan https://example.com
manul daemon tests/ --headless
python manul.py test
```

## Testing and Benchmarks

The project is alpha, but it is not undocumented or untested.

- `python manul.py test` runs the synthetic and unit suite
- `tests/*.hunt` holds integration-style hunts
- `benchmarks/run_benchmarks.py` exercises adversarial fixtures such as dynamic IDs, overlays, nested tables, and custom dropdowns

Representative coverage areas include:

- logical STEP grouping and hierarchical execution
- `ManulSession` API behavior
- scheduler parsing
- lifecycle hooks
- scoped variables
- HTML reporting
- iframe routing
- visibility filtering and TreeWalker behavior
- custom controls and lazy control loading

## What's New in v0.0.9.8

- `ManulSession` is now a first-class public API surface for standalone Python automation
- `.hunt` execution now uses a Hierarchical Block System where `STEP` lines become blocks and child actions execute beneath them with fail-fast semantics
- stdout now emits structured block and action tags for external UI parsing
- custom controls now use Just-In-Time loading so only the required handlers are imported for the current hunt
- reporting now carries both per-action and per-block state

## License

**Version:** 0.0.9.8

Apache-2.0.
