# ManulEngine

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-d97706)](#status-alpha)

ManulEngine is a deterministic, DSL-first web and desktop automation runtime built on top of Playwright.

It executes plain-English `.hunt` scripts for browser automation, Electron app automation, E2E testing, RPA workflows, synthetic monitoring, and constrained AI-agent execution. The resolver is heuristics-first, explainable, and designed to tell you what happened when a step succeeds or fails.

## Status: Alpha

**This project is currently in Alpha. While the core architecture is solid and feature-rich, it is actively being battle-tested on real-world DOMs. Bugs are expected, and APIs may evolve.**

The goal is not to promise perfect outcomes. The goal is to make automation behavior inspectable and debuggable:

- Deterministic heuristics are the default path.
- Optional local AI fallback is off by default.
- Failures should be transparent enough that you can understand why a step failed, not just that it failed.

If you want a short version of the philosophy: ManulEngine does not promise 100% stability. It aims for 100% transparency when things go wrong.

## What It Is

ManulEngine is a runtime with a narrow, opinionated execution model:

- Author intent in `.hunt` DSL.
- Parse the file into structured steps.
- Snapshot the DOM with a native `TreeWalker`.
- Rank candidates with `DOMScorer` using normalized heuristic channels.
- Execute through Playwright.
- Fall back to a local Ollama model only when explicitly enabled and only when the heuristic confidence is too low.

That gives you a system that is easy to reason about in the common case and still has an escape hatch for genuinely ambiguous pages.

## Why Teams Use It

### Explainable heuristics

Element resolution is not hidden behind vague "AI magic". `DOMScorer` uses a normalized `0.0` to `1.0` confidence scale and combines five weighted channels:

- `cache`
- `semantics`
- `text`
- `attributes`
- `proximity`

When you run with explain mode, the engine can show the exact per-channel breakdown for the top candidates. If it missed the target, you can usually see whether the problem was weak text affinity, poor semantic alignment, hidden state, stale cache reuse, or something else concrete.

### Manul Studio for VS Code

The companion VS Code extension is the main IDE experience for `.hunt` files.

It provides:

- Hunt DSL syntax support and formatting.
- Run and debug integration through the Test Explorer.
- Interactive breakpoint stepping.
- A configuration panel, cache browser, step builder, and scheduler dashboard.
- The `[🔍 Explain]` editor action during debug sessions.
- The most useful feature for debugging locator behavior: after a debug run, hovering over a step line shows a tooltip with the exact scoring breakdown for the chosen target.

That hover workflow matters because it keeps the explanation attached to the line you are looking at. You do not need to cross-reference a terminal dump just to understand why the resolver preferred one candidate over another.

### Web and desktop automation in one model

ManulEngine uses Playwright for both traditional browser automation and Electron-style desktop automation.

For desktop use cases, set `executable_path` in the config and start your script with `OPEN APP` instead of `NAVIGATE`. This makes it practical to automate Electron-based desktop apps such as Slack, Discord, VS Code, or any internal Electron shell, without changing the core DSL.

### Dual-persona workflow

The project is designed around two authoring layers that can live in the same test asset:

- QA, analysts, and operators can write plain-English `.hunt` steps.
- SDETs can extend the same flow with Python hooks, lifecycle setup, and custom controls when the UI gets weird.

This keeps most scenarios readable while still giving engineers a precise escape hatch for components like virtual tables, canvas widgets, custom date pickers, or bespoke dropdowns.

### Smart recorder

The recorder is not just a click logger. It captures meaningful interaction intent and already handles tricky native controls such as `<select>` dropdowns by recording semantic `change` events instead of noisy click sequences on `<option>` elements.

## Quick Example

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

## Desktop Example

```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "/path/to/YourElectronApp",
  "controls_cache_enabled": true
}
```

```text
@context: Smoke test for an Electron app
@title: Desktop Smoke

STEP 1: Attach to the running window
    OPEN APP
    VERIFY that 'Welcome' is present

STEP 2: Exercise the main screen
    Click the 'Settings' button
    VERIFY that 'Preferences' is present

DONE.
```

## Explainability Workflow

### CLI

```bash
manul --explain tests/saucedemo.hunt
```

Representative output:

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

### VS Code / Manul Studio

1. Run the file in Debug mode.
2. Pause on a step.
3. Use the `[🔍 Explain]` action if you want the current step explained on demand.
4. Hover over a step line to inspect the stored scoring breakdown as a tooltip.

That tooltip is the fastest way to answer questions like:

- Why did it prefer the link instead of the button?
- Why was the score low enough to trigger fallback?
- Did semantic cache reuse dominate this resolution?
- Was the target penalized because it was hidden or disabled?

## Architecture

```text
.hunt DSL
  -> parser
  -> execution engine
  -> DOM snapshot via TreeWalker
  -> candidate ranking via DOMScorer
  -> action dispatch via Playwright
  -> optional local AI fallback
```

Key implementation traits:

- DOM snapshots are built with injected JavaScript in `manul_engine/js_scripts.py`.
- Candidate ranking lives in `manul_engine/scoring.py`.
- Actions and mission execution live in `manul_engine/actions.py` and `manul_engine/core.py`.
- The runtime supports web pages, same-origin iframes, Shadow DOM, and Electron app windows.
- Reports, step history, and screenshots are first-class runtime outputs rather than afterthoughts.

## Dual-Persona Authoring Model

### Hunt DSL for intent

The DSL is meant to stay readable:

- `NAVIGATE`
- `CLICK`
- `FILL`
- `VERIFY`
- `EXTRACT`
- `PRESS`
- `UPLOAD`
- `OPEN APP`

This is the layer for test flow, business intent, and high-level assertions.

### Python for edge cases

When a UI component does not fit cleanly into heuristics-first resolution, use Python:

- `[SETUP]` / `[TEARDOWN]` hooks for state management.
- `CALL PYTHON` for backend interactions or computed values.
- `@before_all` / `@after_all` lifecycle hooks for suite-wide setup.
- `@custom_control` handlers for complex widgets.

That split is deliberate. It keeps the default workflow simple without pretending that every UI can or should be abstracted into plain English.

## Installation

### Python package

```bash
pip install manul-engine
playwright install
```

### Optional local AI fallback

```bash
pip install "manul-engine[ai]"
ollama pull qwen2.5:0.5b
ollama serve
```

The recommended default is still heuristics-only mode:

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true,
  "semantic_cache_enabled": true
}
```

## Configuration

The runtime reads `manul_engine_configuration.json` from the workspace root.

Common fields:

```json
{
  "model": null,
  "browser": "chromium",
  "headless": false,
  "timeout": 5000,
  "nav_timeout": 30000,
  "controls_cache_enabled": true,
  "semantic_cache_enabled": true,
  "executable_path": null,
  "channel": null,
  "retries": 0,
  "screenshot": "on-fail",
  "html_report": false
}
```

Notes:

- `model: null` disables AI completely and keeps the engine heuristics-only.
- `channel` targets an installed browser such as Chrome or Edge.
- `executable_path` targets a custom executable such as an Electron desktop app.
- `retries`, screenshots, and HTML reporting are runtime controls, not DSL commands.

## What The Project Tries To Be Good At

- Deterministic element resolution before any AI fallback is considered.
- Debuggability when a step fails or resolves ambiguously.
- A readable automation DSL that does not force non-engineers into Playwright internals.
- A pragmatic extension model for SDETs who need full Python control.
- Strong IDE ergonomics for authoring, debugging, and inspecting runs.

## What It Does Not Claim

- It does not claim zero flakiness.
- It does not claim that heuristics solve every UI cleanly.
- It does not claim the current APIs are frozen.
- It does not claim the optional AI path is the primary mechanism.

This is an alpha-stage runtime with a disciplined architecture, not a finished platform pretending to be one.

## Running Tests

```bash
python manul.py test
manul tests/
manul --headless tests/saucedemo.hunt
manul --html-report --screenshot on-fail tests/
```

## Repository Layout

```text
manul.py
manul_engine_configuration.json
pages.json
pyproject.toml
manul_engine/
  core.py
  actions.py
  scoring.py
  js_scripts.py
  scanner.py
  hooks.py
  lifecycle.py
  recorder.py
  reporter.py
  reporting.py
  scheduler.py
vscode-extension/
  package.json
  src/
tests/
controls/
benchmarks/
```

## Manul Studio

The VS Code extension is the primary IDE surface for ManulEngine and is the easiest way to experience the project as intended.

Core capabilities:

- Run and debug `.hunt` files from the editor and Test Explorer.
- Step Builder and scheduler dashboard for faster authoring.
- Config panel for runtime settings.
- Cache browser for persistent control cache inspection.
- Explain output channel plus hover-based scoring inspection.

Marketplace package versioning note:

- The Python runtime version is `0.0.9.6`.
- The VS Code Marketplace manifest uses three-part npm semver and is published as `0.0.96` for this release line.

## Contributing

If you find a resolver miss, a DSL edge case, or an extension bug, the most useful reports include:

- The `.hunt` step text.
- The explain output or hover scoring breakdown.
- Whether the run was heuristics-only or used an Ollama model.
- A minimal DOM fixture or screenshot when possible.

That kind of report is much easier to act on than a generic "it clicked the wrong thing" issue.

## License

Apache-2.0.

**Version:** 0.0.9.6
