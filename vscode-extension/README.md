# 😼 ManulEngine — VS Code Extension

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)

The official VS Code extension for **ManulEngine** — a deterministic, DSL-based E2E browser automation platform.

Write tests in plain English `.hunt` files. Run them at Playwright speed. Resolve elements with a mathematically sound `DOMScorer` (0.0–1.0 float scoring, 20+ heuristic signals) and a native `TreeWalker` — no CSS selectors, no XPath, no cloud APIs.

> The Manul goes hunting and never returns without its prey.

> **Zero AI required. Zero cloud dependency. Zero flakiness by design.**
> Playwright speed. Heuristic precision. Optional local micro-LLMs via Ollama — only when you need them.

---

## 🤝 Dual Persona Workflow — Testing for Humans, Power for Engineers

ManulEngine bridges the gap between Manual QA and Engineering. You don't write controls — you write tests.

* **For Manual QA:** Open a `.hunt` file and write scenarios in plain English — no Python, CSS, or XPath needed. The deterministic heuristics engine resolves elements reliably across UI changes.
* **For Developers / SDETs:** No more maintaining thousands of brittle `page.locator()` calls. For complex custom UI elements, write a Python control hook with the full Playwright API. The QA team keeps writing plain English — your hook handles the Playwright logic behind the scenes.

---

## VS Code Extension Features

> Hunt file language support, one-click test runner, interactive debug runner with gutter breakpoints, Step Builder for plain-English `.hunt` files, configuration UI, and cache browser for [ManulEngine](https://github.com/alexbeatnik/ManulEngine) — deterministic DSL-based browser automation.

## 🚀 What's New in v0.0.9.1 — Enterprise DSL

* **Data-Driven Testing (`@data:`):** Declare `@data: users.csv` or `@data: data.json` in hunt file headers. The engine loads each row and reruns the mission with row values injected as `{placeholders}`. Supports JSON and CSV.
* **Network Interception:** `MOCK GET "/api/users" with 'mocks/users.json'` intercepts requests via Playwright `page.route()`. `WAIT FOR RESPONSE "/api/data"` blocks until a matching response arrives. Syntax-highlighted in `.hunt` files.
* **Visual Regression:** `VERIFY VISUAL 'Logo'` takes an element screenshot and compares it against a stored baseline. Baselines saved in `visual_baselines/` next to the hunt file.
* **Soft Assertions:** `VERIFY SOFTLY that 'Warning' is present` records a failure but continues execution. Soft failures surface as `"warning"` status in CLI and HTML reporter.
* **Reporter Warning Status:** Amber `⚠️ Warning` badges, step-level warning styling, soft-errors block, and a "Show Warnings" filter checkbox.

### Previous highlights (v0.0.9.0)

## 🚀 What's New in v0.0.9.0 — The Power User Update

* **`VERIFY ... is ENABLED`:** State verification now supports both `ENABLED` and `DISABLED` checks. The Step Builder includes a dedicated 🔓 **Verify enabled** button alongside the existing 🔒 **Verify disabled** button.
* **`CALL PYTHON` with Arguments:** Hook functions and inline `CALL PYTHON` steps now accept positional arguments — static strings, unquoted tokens, and `{var}` placeholders resolved at runtime. The Step Builder offers four Python step variants: plain call, call with args, call with capture, and call with args + capture.
* **`ENABLED` Syntax Highlighting:** The `ENABLED` keyword is now highlighted in `.hunt` files alongside `DISABLED`, `NOT`, and other state modifiers.

### Previous highlights
* **Normalised Heuristic Scoring (DOMScorer):** Scoring rewritten with `0.0–1.0` float arithmetic. Five weighted channels — `cache`, `semantics`, `text`, `attributes`, `proximity` — combined via `WEIGHTS` dict and `SCALE=177,778`. `data-qa` exact match is the single strongest signal. Penalties are clean multipliers: disabled ×0.0, hidden ×0.1.
* **TreeWalker-Based DOM Scanner:** `SNAPSHOT_JS` walks the DOM with `document.createTreeWalker()` and a `PRUNE` set. Subtrees rejected in one hop — zero wasted traversal. Visibility via `checkVisibility()` API with `offsetWidth/offsetHeight` fallback.
* **Safe iframe Support:** `_snapshot()` iterates `page.frames`, injects snapshot JS per frame, tags elements with `frame_index`. Cross-origin frames silently skipped; stale indices fall back to main frame.
* **Clean, Unnumbered DSL:** Scripts read like plain English (`NAVIGATE to url` instead of `1. NAVIGATE to url`).
* **Logical STEP Grouping:** `STEP [optional number]: [Description]` blocks map manual QA cases directly into `.hunt` files.
* **Interactive Enterprise HTML Reporter:** Dual-mode, zero-dependency reporter with native HTML5 accordions, auto-expanding failures, Flexbox layout, **"Show Only Failed" toggle**, and **tag filter chips**.
* **Global Lifecycle Hooks:** `@before_all`, `@after_all`, `@before_group`, `@after_group` orchestrate DB seeding and auth. `ctx.variables` serialise across parallel `--workers`.

## Features

### 🎨 Hunt File Language Support
- Syntax highlighting for `.hunt` files
- Comment toggling (`#`)
- Bracket/quote matching and auto-closing
- File icon in the explorer

### ▶️ Run Hunt Files
Three ways to run a `.hunt` file:

| Method | How |
|--------|-----|
| **Editor title button** | Click the `▶` icon in the top-right of the editor when a `.hunt` file is open |
| **Explorer context menu** | Right-click a `.hunt` file → *ManulEngine: Run Hunt File* |
| **Terminal mode** | Right-click → *ManulEngine: Run Hunt File in Terminal* (runs raw in the integrated terminal) |

Output streams live into a dedicated **ManulEngine** output channel. ✅ / ❌ status is appended on completion.

### 🐛 Debug Mode
Place breakpoints by clicking the editor gutter next to any step number in a `.hunt` file. Then run the **Debug** profile in Test Explorer (or use `ManulEngine: Debug Hunt File` from the Command Palette / editor title).

- Execution pauses at each breakpointed step with a floating **QuickPick overlay** — no modal dialogs, no Cancel button
- **⏭ Next Step** — advance exactly one step and pause again
- **▶ Continue All** — run until the next gutter breakpoint or end of hunt
- **Stop button** — clicking Stop in Test Explorer dismisses the QuickPick and terminates the run cleanly; Python never hangs
- **👁 Highlight Element** — a third QuickPick option that re-scrolls the browser to the persistently highlighted target element and re-shows the pause overlay without advancing the step
- **Linux:** VS Code window is raised via `xdotool`/`wmctrl` and a 5-second system notification appears via `notify-send` when execution pauses
- **Persistent magenta highlight** — the resolved target element is outlined with a `4px solid #ff00ff` border + glow while execution is paused; the highlight is removed automatically just before the action executes
- Debug output streams live into the **ManulEngine Debug** output channel
- Uses `--break-lines` protocol (piped stdio): Python emits a marker on stdout; extension responds on stdin — browser opens and navigates normally on step 1

### 🧪 Test Explorer Integration
Hunt files appear in the **VS Code Test Explorer** as top-level test items (one per file). Two run profiles are available:
- **Run** (default) — runs the hunt normally using the output panel
- **Debug** — runs with gutter breakpoints and the floating QuickPick pause overlay (see Debug Mode above)

For both profiles:
- Each step is shown as a child item with pass/fail status
- Failed steps display the engine output as the failure message
- Steps that were never reached are marked as skipped
- The step tree is cleared after the run so the explorer shows the correct file-level count

### ⚙️ Configuration Panel
An interactive sidebar panel for editing `manul_engine_configuration.json` without touching the file directly.

- **Model** — Ollama model name (leave blank for **heuristics-only mode** — the recommended default)
- **AI Policy** — `prior` (heuristic as hint) or `strict` — only relevant when a model is set
- **AI Threshold** — score cutoff before optional LLM fallback (`null` = auto)
- **AI Always** — always call the LLM picker (automatically disabled when no model is set; not recommended)
- **Browser** — browser engine: Chromium, Firefox, or WebKit
- **Browser Args** — extra launch flags for the browser (comma-separated)
- **Headless** — run browser headless
- **Timeouts** — action and navigation timeouts in ms
- **Persistent Controls Cache / Semantic Cache** — two separate cache toggles: **Persistent Controls Cache** (`controls_cache_enabled`) stores resolved locators on disk per site/page across runs; **Semantic Cache** (`semantic_cache_enabled`) remembers resolved elements within a single run (+200,000 score boost, resets when the process ends). Both default to enabled and can be toggled independently from the sidebar
- **Auto-Annotate Page Navigation** — when enabled, the engine automatically inserts `# 📍 Auto-Nav:` comments in the hunt file whenever the browser URL changes during a run (after clicks, form submissions, etc.) — not just on explicit `NAVIGATE` steps. Page names are resolved from `pages.json`; if no mapping is found the full URL is used instead
- **Log truncation** — max length for element names and LLM thoughts in logs
- **Workers** — max number of hunt files to run concurrently in Test Explorer (1–4)
- **Ollama status indicator** — live dot showing whether Ollama is reachable at `localhost:11434`, with model autocomplete from the running instance

Changes are saved to `manul_engine_configuration.json` at the workspace root. An **Add Default Prompts** button copies built-in prompt templates into `prompts/` if they don't already exist. A *Generate Default Config* button creates the file if it doesn't exist yet.

### 🗂️ Cache Browser
The **Cache** sidebar tree shows per-site cache entries created by ManulEngine's persistent controls cache. You can:
- Browse sites and their cached page entries
- Clear the cache for a specific site (trash icon on hover)
- Clear all cache entries at once (toolbar button)
- Refresh the tree manually

### 🧱 Step Builder
A sidebar panel that lets you insert hunt steps with a single click — no typing required.

- **＋ New Hunt File** button — prompts for a name, creates a `.hunt` file with a starter template in the `tests_home` directory (configured via `tests_home` in `manul_engine_configuration.json`, defaults to `tests/`), and opens it
- **🔍 Live Page Scanner** — paste any URL into the sidebar text input and click **Run Scan**; the extension invokes `manul scan <URL>` as a child process with a progress notification, then automatically opens the freshly generated `tests_home/draft.hunt` in the editor — no terminal required
- **Step buttons** — one button per step type: Navigate, Fill field, Click, Double Click, Right Click, Select, Check, Radio, Hover, Drag & Drop, Extract, Verify present/absent/disabled/enabled, Press Enter, Press Key, Upload File, Wait, Scroll Down, **Scan Page**, **🐍 Call Python**, **🐍 Call Python + Args**, **🐍 Call Python → Var**, **🐍 Call Python Args → Var**, **Debug / Pause**, Done
- **🐍 Call Python** — appends `CALL PYTHON module_name.function_name` to the end of the current `.hunt` file with a single click; rename the placeholders and your Python function runs inline as part of the test — no block wrappers needed
- **🐍 Call Python + Args** — appends `CALL PYTHON module_name.function_name 'arg1' {var}` with tabstop placeholders for the module, function, and arguments
- **🐍 Call Python → Var** — appends `CALL PYTHON module_name.function_name into {variable_name}`; the function's return value is captured as a string and bound to `{variable_name}`, available for `{placeholder}` substitution in all subsequent steps
- **🐍 Call Python Args → Var** — appends `CALL PYTHON module_name.function_name 'arg1' {var} into {result}` with tabstop placeholders for the full syntax; combines arguments and return value capture in one step
- **Hooks buttons** — **🔧 Insert [SETUP]** and **🧹 Insert [TEARDOWN]** insert pre-filled hook blocks with `CALL PYTHON module.function` placeholders; **🎯 Generate Demo Test** scaffolds a complete hunt file with setup, UI steps, and teardown in one click
- **Scan Page** — inserts `SCAN PAGE into draft.hunt`; when the engine executes this step it scans the current browser page for interactive elements and writes a ready-to-run draft hunt file to `tests_home/draft.hunt`
- Each click appends to the currently open `.hunt` file and positions the cursor inside the first `''` pair for immediate editing
- Requires the `.hunt` file to be the active editor tab.

---

## 💻 System Requirements

| | Minimum | Recommended |
|---|---|---|
| **CPU** | any | modern laptop |
| **RAM** | 4 GB | 8 GB |
| **GPU** | none | none |
| **Model** | — (heuristics-only) | `qwen2.5:0.5b` |

## Requirements

- **ManulEngine** installed in the workspace or globally:
  ```bash
  pip install manul-engine          # global / user
  # or in a project venv:
  pip install -e .
  ```
- **Python 3.11+**
- **Playwright** browsers (installed by ManulEngine's setup)
- **Ollama** (optional) — only needed as a last-resort self-healing fallback when the deterministic heuristics engine cannot confidently resolve an element
  ```bash
  pip install ollama   # Python client library
  ```
  Plus the [Ollama app](https://ollama.com) running locally with a model pulled (e.g. `ollama pull qwen2.5:0.5b`)

---

## Auto-detection of the `manul` executable

The extension probes the following locations in order (platform-aware):

1. Custom path from **`manulEngine.manulPath`** setting (if set and exists)
2. `.venv/bin/manul` in the workspace root (also checks `venv/`, `env/`, `.env/`)
3. `~/.local/bin/manul` (pip --user, Linux/macOS)
4. `~/Library/Python/*/bin/manul` (pip --user, macOS)
5. `~/.local/pipx/venvs/manul-engine/bin/manul` (pipx)
6. `/opt/homebrew/bin/manul` (Homebrew, Apple Silicon)
7. `/usr/local/bin/manul`, `/usr/bin/manul` (system-wide)
8. Shell login init lookup (`$SHELL -lc 'command -v manul'`) — sources fish/zsh/bash/pyenv/conda init so shims are found
9. Windows: `%APPDATA%\Python\*\Scripts\manul.exe`, `%LOCALAPPDATA%\Programs\Python\*\Scripts\manul.exe`

---

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `manulEngine.manulPath` | `""` | Absolute path to the `manul` CLI. Leave empty to auto-detect. |
| `manulEngine.configFile` | `manul_engine_configuration.json` | Config file name resolved from the workspace root. |
| `manulEngine.workers` | `null` | Max concurrent hunt files in Test Explorer. Overrides `workers` in config. Leave empty to use the config value (default: 1). |
| `manulEngine.htmlReport` | `false` | Generate a self-contained HTML report after each run (saved to `reports/manul_report.html`). |
| `manulEngine.retries` | `0` | Number of times to retry a failed hunt file before marking it as failed (0–10). |
| `manulEngine.screenshotMode` | `"on-fail"` | Screenshot capture mode: `none`, `on-fail` (failed steps only), `always` (every step). |

---

## Getting Started

1. Install ManulEngine:
   ```bash
   pip install manul-engine
   playwright install chromium
   ```

2. Open your project folder in VS Code. The extension activates automatically when a `.hunt` file is present.

3. Run `ManulEngine: Generate Default Config` from the Command Palette to create `manul_engine_configuration.json`.

4. Open the **ManulEngine** activity bar panel to configure Ollama and cache settings.

5. Open or create a `.hunt` file and click ▶ to run it.

---

## Example Hunt File

```hunt
@context: Login and verify dashboard
@title: smoke_login
@tags: smoke, auth

@var: {user_email} = user@example.com
@var: {password}   = secret

STEP 1: Login
NAVIGATE to https://example.com/login
Fill 'Email' field with '{user_email}'
Fill 'Password' field with '{password}'
Click the 'Sign In' button
VERIFY that 'Welcome' is present.
DONE.
```

See the [ManulEngine README](https://github.com/alexbeatnik/ManulEngine) for the full step reference.

---

## 🎛️ Custom Controls — Python Power Behind Simple Steps

Some UI elements cannot be reliably targeted by heuristics or AI: React virtual tables, canvas datepickers, WebGL widgets, and similar custom components. **Custom Controls** bridge the gap by routing specific `.hunt` steps to hand-written Playwright Python — while the hunt file stays plain English.

**How it works:**

1. Create a `controls/` directory in your workspace root.
2. Add a `.py` file with a `@custom_control` handler:
   ```python
   # controls/booking.py
   from manul_engine import custom_control

   @custom_control(page="Checkout Page", target="React Datepicker")
   async def handle_datepicker(page, action_type, value):
       await page.locator(".react-datepicker__input-container input").fill(value or "")
   ```
3. Map the URL to `"Checkout Page"` in `pages.json` (editable via the Config Panel).
4. Write a normal `.hunt` step — no special syntax required:
   ```text
   Fill 'React Datepicker' with '2026-12-25'
   ```

The extension runs `.hunt` files via the same `manul` CLI. Custom Controls are loaded automatically on engine startup — no extension configuration needed. Debug breakpoints, Test Explorer integration, and live output streaming all work exactly the same whether a step uses a custom control or the standard heuristic pipeline.

> **Team workflow:** QA authors keep writing plain English. SDETs own the `controls/` directory. The `.hunt` file never needs to change when the underlying Playwright logic evolves.

---

## Release Notes

### 0.0.91
- **📊 Data-Driven Testing (`@data:`)** — declare `@data: users.csv` or `@data: data.json` in hunt file headers. The engine reruns the mission for each row with values injected as `{placeholders}`. Supports JSON (array-of-objects) and CSV (DictReader)
- **🔀 Network Interception (`MOCK` / `WAIT FOR RESPONSE`)** — `MOCK GET "/api/users" with 'mocks/users.json'` intercepts requests via `page.route()`. `WAIT FOR RESPONSE "/api/data"` blocks until a matching response arrives. Supports GET, POST, PUT, PATCH, DELETE
- **📸 Visual Regression (`VERIFY VISUAL`)** — `VERIFY VISUAL 'Logo'` takes an element screenshot, saves a baseline on first run, and pixel-compares on subsequent runs. Uses PIL/Pillow threshold comparison or raw byte fallback
- **⚠️ Soft Assertions (`VERIFY SOFTLY`)** — `VERIFY SOFTLY that 'Warning' is present` records a failure but continues execution. All soft failures are aggregated and surfaced as `"warning"` status
- **🟡 Reporter Warning Status** — amber Warning stat card, `badge-warning` badges, `step-warning` row styling, soft-errors block, and "Show Warnings" filter checkbox in control panel
- Core engine bump to **0.0.9.1**

### 0.0.90
- **🔓 `VERIFY ... is ENABLED`** — state verification now supports `ENABLED` alongside `DISABLED`. Assert that interactive elements (buttons, inputs, selects, ARIA-role elements) are active before proceeding. `ENABLED` keyword highlighted in `.hunt` syntax. Step Builder adds a dedicated 🔓 **Verify enabled** button
- **🐍 `CALL PYTHON` with Arguments** — hook functions and inline `CALL PYTHON` steps now accept optional positional arguments: `CALL PYTHON helpers.multiply "6" "7" into {product}`. Arguments are tokenised with `shlex.split()`; `{var}` placeholders are resolved from the engine's runtime memory. Step Builder adds two new buttons: **Call Python + Args** and **Call Python Args → Var** with full tabstop snippet support
- **📊 Interactive HTML Reporter** — control panel with **"Show Only Failed" checkbox** and **tag filter chips**. All `@tags` are auto-collected and rendered as clickable chips; missions carry `data-status` and `data-tags` attributes for instant JS-powered filtering. Zero external dependencies
- **Dual Persona Workflow** — QA writes plain English, SDETs write Python hooks that accept dynamic `{variable}` arguments directly from `.hunt` files. The Step Builder now covers all four CALL PYTHON variants: plain, with args, with capture, and with args + capture
- Core engine bump to **0.0.9.0**

### 0.0.89
- **🧮 Normalised Float Scoring** — `DOMScorer` rewritten with `0.0–1.0` floats across five weighted channels (`cache`, `text`, `attributes`, `semantics`, `proximity`), combined via `WEIGHTS` dict and `SCALE=177,778` for integer thresholds. Pre-compiled regex, single `_preprocess()` pass per element. Clean penalty multipliers: disabled ×0.0, hidden ×0.1
- **🌲 TreeWalker DOM Scanner** — `SNAPSHOT_JS` replaced with `document.createTreeWalker()` traversal and a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`). Subtrees rejected in one hop. Visibility via `checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })` with `offsetWidth/offsetHeight` fallback. Special exception: hidden checkbox/radio/file inputs remain discoverable
- **🖼️ iframe Support** — `_snapshot()` iterates `page.frames`, injects snapshot JS per frame, tags elements with `frame_index`. `_frame_for()` routes all downstream locator calls to the correct Playwright `Frame`. Cross-origin frames are skipped; transient "frame closed" errors are retried up to 3 times with backoff
- Core engine bump to **0.0.8.9**

### 0.0.88
- **🌐 Global Lifecycle Hooks** — create `manul_hooks.py` alongside your `.hunt` files and use `@before_all`, `@after_all`, `@before_group(tag=)`, `@after_group(tag=)` decorators from `manul_engine` to wire up suite-level setup and teardown in pure Python. Variables written to `ctx.variables` in any hook are injected into every matching hunt as `{placeholder}` data — no per-file `@var:` needed. Works identically whether running with `--workers 1` (sequential) or `--workers N` (parallel subprocesses): the orchestrator serialises shared variables into `MANUL_GLOBAL_VARS` before spawning workers so every browser process inherits the same state
- **🧠 Deep Accessibility Heuristics** — element scoring now uses the HTML `name` attribute as a first-class signal (`name_attr` exact match: +0.0375 text / ~3k scaled; substring: +0.0125 / ~1k scaled). This resolves long-standing issues with modern SPA design systems (React, Vue, Wikipedia Vector 2022 / Codex) where inputs use `aria-label` and `name` as the primary identifiers instead of visible text. No configuration change required — the improvement is automatic
- **Suite-level failure semantics** — `@before_all` failure aborts the entire suite (all remaining hunts recorded as failed); `@after_all` always fires in the `finally` block. `@before_group` failure skips only the matching mission; `@after_group` still runs for it. Cleanup hooks continue past individual errors so teardown is never partially skipped
- Core engine bump to **0.0.8.8**

### 0.0.87
- **📊 HTML Reports** — new `manulEngine.htmlReport` toggle in Config Panel (“📊 Reporting & Retries” section); generates a self-contained dark-themed HTML report with dashboard stats, per-step accordion, and inline base64 screenshots after each run. Report is saved to `reports/manul_report.html` in the workspace root
- **🔄 Automatic Retries** — new `manulEngine.retries` setting (0–10) in Config Panel; retries each failed hunt the specified number of times before marking it as failed. Each retry is a full fresh browser run
- **📷 Screenshot Capture** — new `manulEngine.screenshotMode` selector (`none` / `on-fail` / `always`) in Config Panel; screenshots are embedded as base64 in the HTML report
- All three settings are auto-injected as CLI flags (`--html-report`, `--retries`, `--screenshot`) when running hunts via the extension — no manual CLI arguments needed
- All artifacts (logs, reports) are now saved to the `reports/` directory — workspace stays clean

### 0.0.86
- **📌 Static Variable Declaration (`@var:`)** — declare test data at the top of any `.hunt` file using `@var: {key} = value`; values are pre-populated into the engine's runtime memory before step 1 runs and can be interpolated anywhere a `{placeholder}` is accepted (e.g. `Fill 'Email' with '{user_email}'`). Both brace and bare-key forms are accepted. Keeps test data separate from test logic — no more hardcoded credentials scattered across steps
- **🐍 Dynamic Variable Capture (`CALL PYTHON ... into {var}`)** — `CALL PYTHON module.function into {variable_name}` (or `to {var}`) captures the return value of any synchronous Python function and stores it as a string in runtime memory; use immediately in subsequent steps via `{variable_name}`. Enables mid-test backend calls (OTP retrieval, magic links, DB tokens) without hardcoding values
- **🐍 "Call Python → Var" button in Step Builder** — one-click insertion of `CALL PYTHON module_name.function_name into {variable_name}` scaffold directly into the active `.hunt` file
- **🏷️ Arbitrary Tags (`@tags:`) and `--tags` CLI filter** — declare comma-separated tags at the top of any `.hunt` file with `@tags: smoke, auth, regression`; run `manul tests/ --tags smoke` to execute only matching files (OR logic: file must contain at least one requested tag; untagged files are excluded when `--tags` is active)
- Core engine bump to **0.0.8.7**

### 0.0.85
- Core engine bump to **0.0.8.6** — internal improvements and bug fixes

### 0.0.84
- **🎛️ Custom Controls** — decorator-based Python handler registry (`@custom_control(page, target)`) for complex UI elements (React virtual tables, canvas widgets, WebGL, multi-step datepickers); handlers in `controls/` are auto-loaded at engine startup; `controls/demo_custom.py` and `tests/demo_controls.hunt` ship as a reference implementation
- **🔍 Live Page Scanner in Step Builder** — new URL input + **Run Scan** button in the Step Builder sidebar; invokes `manul scan <URL>` as a child process with a progress notification and automatically opens the generated `tests_home/draft.hunt` in the editor — no terminal required

### 0.0.84
- **⏹ Debug Stop / 🛑 Stop Test buttons** — two new actions in the floating debug QuickPick overlay replace the old implicit close/abort behaviour: **Debug Stop** skips all remaining breakpoints (including user-set gutter ones) and runs the test to the end without further pauses; **Stop Test** sends a clean `abort` signal to Python, waits 500 ms for graceful shutdown, then kills the process
- **Auto-Annotate Page Navigation** — new `auto_annotate` toggle in the Config Panel sidebar; when enabled, the engine inserts `# 📍 Auto-Nav:` comments in the hunt file whenever the browser URL changes, not only on explicit `NAVIGATE` steps (e.g. after a Login button click that redirects to the dashboard). Page names are resolved from `pages.json`; unmapped URLs fall back to the full URL
- **`pages.json` nested format** — page registry now uses a two-level structure: top-level keys are site roots (URL prefix, e.g. `"https://www.saucedemo.com/"`), values are objects with a special `"Domain"` key (site display name) and regex/exact-URL keys for specific pages. Supports multiple sites in one file. Exact URL keys take priority over regex patterns; the `"Domain"` value is returned as a fallback when no page pattern matches but the URL belongs to the site
- **`lookup_page_name` exact-match fix** — previously a root URL key like `"https://www.saucedemo.com/"` would match all its subpages via `re.search()`, overriding page-specific patterns. Exact keys are now checked first
- **Persistent magenta highlight** — when the engine pauses at a debug step, the resolved target element is outlined with a persistent magenta border (`outline: 4px solid #ff00ff` + glow) that stays visible until the user proceeds; the highlight is injected via `<style id="manul-debug-style">` + `data-manul-debug-highlight` attribute and fully removed by `clear_highlight()` before the action executes
- **👁 Highlight Element QuickPick button** — a QuickPick option that re-scrolls the browser to the persistently highlighted target element and re-displays the QuickPick without advancing the step
- **Two separate cache controls in config panel** — `controls_cache_enabled` is now labelled **Persistent Controls Cache** (file-based, disk, per-site across runs) and `semantic_cache_enabled` is labelled **Semantic Cache** (in-session `learned_elements`, +200,000 score boost within a single run, resets when the process ends); both default to enabled and can be toggled independently

### 0.0.83
- **Inline `CALL PYTHON` steps** — `CALL PYTHON module.function` now works as an action step anywhere in the mission body (not just in hook blocks); use it to fetch OTPs, trigger backend jobs, or seed data mid-test without leaving the `.hunt` file
- **🐍 Call Python button in Step Builder** — inserts a `CALL PYTHON module_name.function_name` scaffold with a single click; `ManulEngine: Insert Inline CALL PYTHON Step` command also available in the Command Palette
- **Python Hooks** — `[SETUP]` / `[TEARDOWN]` blocks in `.hunt` files now invoke synchronous Python functions before/after the browser mission via `CALL PYTHON module.function`; setup failure skips mission + teardown; teardown always runs in a `finally` block
- **Hooks buttons in Step Builder** — **🔧 Insert [SETUP]**, **🧹 Insert [TEARDOWN]**, and **🎯 Generate Demo Test** buttons added to the Step Builder sidebar
- **`ManulEngine: Insert [SETUP] Block`**, **`ManulEngine: Insert [TEARDOWN] Block`**, **`ManulEngine: Generate Demo Test`** commands available in the Command Palette

### 0.0.82
- **Interactive Debug Mode** — place gutter breakpoints (red dots) next to steps in any `.hunt` file; run the new **Debug** profile in Test Explorer or invoke `ManulEngine: Debug Hunt File` to step through a hunt interactively
- **Floating QuickPick pause overlay** — when execution pauses at a breakpoint, a floating overlay appears with **⏭ Next Step** (advance one step) and **▶ Continue All** (run to next gutter breakpoint or end); no Cancel button, no modal tab
- **`--debug` CLI flag** — interactive terminal debug mode: engine pauses before every step and prompts ENTER; draws a dashed red border around the resolved element for 500 ms
- **`--break-lines` CLI flag** — gutter breakpoint mode used by the extension; pauses at steps matching file line numbers via stdout/stdin JSON protocol; never blocks the NAVIGATE step
- **`DEBUG` / `PAUSE` step keyword** — inserts an explicit pause at that point in any hunt run
- **Debug run profile** added to Test Explorer alongside the normal run profile
- **Visual element highlighting** — dashed red border injected via JS on the resolved element for 500 ms before each action (active in `--debug` mode)

### 0.0.81
- **Bug fix** — `manul scan <URL> test.hunt` (bare filename as positional arg) now correctly saves to `tests_home/test.hunt` instead of CWD/test.hunt

### 0.0.80
- **Smart Page Scanner** — new `manul scan <URL>` CLI command opens a browser, scans the page for interactive elements (including Shadow DOM), and generates a draft `.hunt` file in the `tests_home` directory
- **`SCAN PAGE into {filename}`** step keyword — same scanner available as an in-test step; use it mid-hunt to capture a page's elements and save a draft for later refinement
- **Scan Page** button added to the Step Builder sidebar
- **Model dropdown fix** — replaced `<input list="datalist">` (rendered offset in VS Code Electron webview) with a plain `<select>` populated from Ollama API; first option is always `null (heuristics-only)`

### 0.0.7
- Fix step-insertion buttons in Step Builder sidebar — inline `onclick` handlers were blocked by VS Code webview CSP; replaced with `data-template` attributes and `addEventListener`
- Fix step insertion when sidebar webview steals editor focus — track last known `.hunt` document URI and use `WorkspaceEdit` for reliable insertion
- New **Step Builder** sidebar panel with one-click step templates (Navigate, Fill, Click, Select, Verify, Extract, etc.) and a **＋ New Hunt File** button

### 0.0.61
- Add `PRESS ENTER` system keyword — submits focused form fields without requiring a visible submit button

### 0.0.60
- Version bump to 0.0.6 — aligns with Python package `manul-engine 0.0.6`

### 0.0.54
- **Real-time step reporting** — hunt steps appear in Test Explorer with pass/fail status *while the hunt is running*, not just after it finishes
- **Bounded concurrency** — Test Explorer now respects the `workers` setting (from `manul_engine_configuration.json` or the new `manulEngine.workers` VS Code setting) instead of running all hunt files with unbounded `Promise.all`
- **Workers combobox** — config panel sidebar exposes a Workers field (1–4)
- **Add Default Prompts** button — copies built-in prompt templates into `prompts/` with one click
- Executable auto-detection now checks `venv/`, `env/`, and `.env/` in addition to `.venv/` — fixes `spawn manul ENOENT` for projects that use a non-dotted venv folder name

### 0.0.53
- Hunt file syntax highlighting, Test Explorer integration, configuration panel, cache browser
- Smart `manul` executable auto-detection across pip, pipx, Homebrew, pyenv, conda, and custom paths
- Per-file workspace root resolution for multi-root workspaces
- PowerShell-aware terminal command (`&` prefix)
- Shell-specific login flags (bash/zsh vs fish vs sh/dash)
- Fallback cache eviction on transient shell lookup failures
- Font size improvements in the configuration panel
- Browser selection (`chromium`, `firefox`, `webkit`) in the configuration panel
- Browser args field for passing extra launch flags to the browser
