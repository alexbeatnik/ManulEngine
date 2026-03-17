# ManulEngine

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-d97706)](#status-alpha)

Deterministic, DSL-first web and desktop automation on top of Playwright, with explainable heuristics and optional local AI fallback.

## Status: Alpha

**This project is currently in Alpha. While the core architecture is solid, it is actively being battle-tested. Bugs are expected, and APIs may evolve.**

ManulEngine is aiming for transparent behavior, not inflated claims. The default path is deterministic heuristics. When a step fails or resolves ambiguously, the goal is to make that outcome inspectable.

## Core Philosophy

ManulEngine is an interpreter for the `.hunt` DSL. A hunt file describes intent in plain English, the runtime snapshots the DOM, ranks candidates with heuristics, and executes the chosen action through Playwright.

### Determinism first

The primary resolver is not an LLM. It is a scoring system backed by DOM traversal and heuristics:

- DOM collection uses a native `TreeWalker` in injected JavaScript.
- Candidate ranking is handled by `DOMScorer`.
- Scores are normalized on a `0.0` to `1.0` confidence scale.
- Weighted channels include `cache`, `semantics`, `text`, `attributes`, and `proximity`.

That means the engine can tell you more than "element not found". It can usually show whether a target lost because the text match was weak, the semantics were wrong, the candidate was hidden, or some other scoring channel dominated.

### Transparency instead of AI magic

ManulEngine does not need a model to operate. The recommended default is heuristics-only mode:

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true,
  "semantic_cache_enabled": true
}
```

When a local Ollama model is enabled, it is a fallback path for ambiguous cases, not the primary execution model.

### Dual-persona workflow

The project is built around two layers that can coexist in the same automation asset:

- QA, analysts, or operators write plain-English `.hunt` steps.
- SDETs extend those flows with Python hooks, lifecycle setup, and custom controls when a UI component exceeds what the generic resolver should handle.

The intended split is simple:

- Put business intent and readable flow in the DSL.
- Put infrastructure setup, backend access, and custom widget logic in Python.

## Getting Started

### Install

```bash
pip install manul-engine
playwright install
```

Optional local AI fallback:

```bash
pip install "manul-engine[ai]"
ollama pull qwen2.5:0.5b
ollama serve
```

### Full configuration example

Create `manul_engine_configuration.json` in the workspace root. All keys are optional, but this example shows the current runtime surface area:

```json
{
  "model": null,
  "browser": "chromium",
  "browser_args": [],
  "headless": false,

  "ai_always": false,
  "ai_policy": "prior",
  "ai_threshold": null,

  "timeout": 5000,
  "nav_timeout": 30000,

  "controls_cache_enabled": true,
  "controls_cache_dir": "cache",
  "semantic_cache_enabled": true,

  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "tests_home": "tests",
  "auto_annotate": false,

  "executable_path": null,
  "channel": null,

  "retries": 0,
  "screenshot": "on-fail",
  "html_report": false
}
```

Notes:

- `model: null` keeps the runtime fully heuristics-only.
- `browser_args` passes extra launch flags to the browser.
- `ai_always`, `ai_policy`, and `ai_threshold` only matter when a model is enabled.
- `controls_cache_dir`, `tests_home`, and `auto_annotate` control runtime filesystem behavior.
- `channel` targets an installed browser such as Chrome or Edge.
- `executable_path` targets a custom executable such as an Electron app.

### First hunt file

```text
@context: Smoke test for a login flow
@title: Login Smoke
@var: {email} = admin@example.com
@var: {password} = secret123

STEP 1: Open the app
    NAVIGATE to https://example.com/login
    VERIFY that 'Sign In' is present

STEP 2: Authenticate
    Fill 'Email' field with '{email}'
    Fill 'Password' field with '{password}'
    Click the 'Sign In' button
    VERIFY that 'Dashboard' is present

DONE.
```

### Run it

```bash
manul tests/login.hunt
```

Useful commands:

```bash
python manul.py test
manul tests/
manul --headless tests/saucedemo.hunt
manul --html-report --screenshot on-fail tests/
manul --explain tests/saucedemo.hunt
```

## Key Features

### Desktop app execution with `executable_path`

ManulEngine is not limited to browser tabs. Because it runs on Playwright, it can also drive Electron-based desktop apps.

Set `executable_path` in the config and use `OPEN APP` instead of `NAVIGATE`:

```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "/path/to/YourElectronApp"
}
```

```text
@context: Desktop smoke test
@title: Desktop Smoke

STEP 1: Attach to the window
    OPEN APP
    VERIFY that 'Welcome' is present

STEP 2: Exercise the main screen
    Click the 'Settings' button
    VERIFY that 'Preferences' is present

DONE.
```

This is practical for Electron-based apps such as Slack, Discord, VS Code, or internal desktop shells.

### Smart Recorder

The recorder is meant to capture intent, not just raw pointer activity. One concrete example is native `<select>` handling: the injected recorder tracks semantic `change` events and emits meaningful DSL such as `Select 'Option' from 'Dropdown'` instead of recording a brittle sequence of low-level clicks on `<option>` elements.

### IDE hover debugger and explain mode

The VS Code extension is the primary IDE surface for `.hunt` files.

Important debugging workflows:

- Run a hunt in Debug mode through Test Explorer.
- Use the `[🔍 Explain]` action to request explanation data for the current step.
- Hover over a step line to see the stored scoring breakdown for the resolved target.

That hover view is the shortest path to understanding why the engine preferred one candidate over another.

Representative CLI explain output:

```text
┌─ EXPLAIN: Target = "Login"
│  Step: Click the 'Login' button
│
│  #1 <button> "Login"
│     total:      0.593
│     text:       0.281
│     attributes: 0.050
│     semantics:  0.225
│     proximity:  0.037
│     cache:      0.000
│
└─ Decision: selected "Login" with score 0.593
```

### Python hooks and custom controls

When the generic resolver should not be forced to understand a bespoke widget, ManulEngine gives SDETs an explicit escape hatch:

- `[SETUP]` / `[TEARDOWN]` hooks for environment and data setup.
- `CALL PYTHON` for backend lookups or computed values.
- `@before_all` / `@after_all` lifecycle hooks for suite-wide orchestration.
- `@custom_control` handlers for complex UI elements.

That is the intended balance: keep the common path readable, and keep the hard edge cases programmable.

## What's New in v0.0.9.6

- The public README was rewritten to reflect the actual current posture of the project: alpha-stage, strong architectural direction, but still being battle-tested.
- The messaging now emphasizes determinism, transparency, and DX instead of broad marketing claims.
- The documentation now explicitly frames `DOMScorer` as a normalized `0.0` to `1.0` heuristic system rather than hiding behavior behind vague AI language.
- The README now highlights the Manul Studio debugging workflow, especially `[🔍 Explain]` and hover-based scoring inspection.
- Desktop automation via `executable_path` and `OPEN APP` is now called out as a first-class workflow.
- The smart recorder's handling of native `<select>` `change` events is documented explicitly.
- README version references are aligned to `0.0.9.6` for the Python runtime line.
