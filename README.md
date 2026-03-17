# 😼 ManulEngine — Deterministic Web & Desktop Automation Runtime

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)

**ManulEngine v0.0.9.5 — The Deterministic, DSL-First Web & Desktop Automation Runtime with Explainable Heuristics.**

Write automation scripts in plain English. Run E2E tests, RPA workflows, synthetic monitors, and AI-agent actions — on **web browsers and desktop apps** alike — powered by a mathematically provable heuristic engine and Playwright. Every element resolution is transparent, reproducible, and auditable down to the individual scoring channel.

No CSS selectors. No XPath fragility. No cloud API bills. No black boxes.

> The Manul goes hunting and never returns without its prey.

> **Zero AI required. Zero cloud dependency. Zero flakiness by design.**
> Playwright speed. Heuristic precision. Full scoring transparency — via CLI or **Hover tooltips in your IDE**. Optional local micro-LLMs via Ollama — only when you need them.

---

## What Makes v0.0.9.5 Different

ManulEngine has evolved from a web automation wrapper into a **transparent, Desktop-capable automation platform**. This release focuses on three pillars: **Explainability**, **Developer Experience**, and **Web + Desktop versatility**.

### Explainable Heuristics — See the Math, Not a Black Box

The `DOMScorer` uses a strict, normalised **0.0 to 1.0 confidence scale** across five weighted channels (Text, Attributes, Semantics, Proximity, Cache). Every element resolution is a pure mathematical function — no randomness, no token limits, no hidden model weights. With `--explain`, the engine prints the full per-channel breakdown for every step. But the real breakthrough is in the IDE.

### IDE-Native Transparency — Hover to Understand

The companion VS Code extension now offers **three layers of explainability**, all without leaving the editor:

1. **`🔍` Title Bar Button** — One-click "Explain Current Step" from the editor title bar during a Debug session.
2. **Hover Tooltips in Debug Mode** — **The killer DX feature.** Run a hunt in Debug Mode, then simply **hover your mouse over any step** in the `.hunt` file. A rich tooltip appears instantly, showing the exact mathematical breakdown of *why* the engine selected a specific DOM element — candidate rankings, per-channel scores, and the final decision. No terminal. No output channel. Just hover.

![Demo: Hover over a step in debug mode to see the heuristic breakdown](link)

### Desktop App Testing — Discord, Slack, Spotify, and Beyond

ManulEngine now automates **Electron-based desktop applications** — Discord, Slack, Spotify, VS Code itself — using the same DSL and the same heuristic engine. Point `executable_path` at any Electron app, use `OPEN APP` instead of `NAVIGATE`, and write your steps in plain English. The engine attaches to the app's window, waits for DOM settlement, and runs your hunt identically to a web test.

### Smart Recording with Native Elements

The Injected Recorder (`manul record`) now handles native `<select>` dropdowns using semantic `change` events, generating clean DSL commands (`Select 'Option' from 'Dropdown'`) instead of raw click sequences. Clicks on `<select>` and `<option>` elements are intelligently suppressed — only the final selection is captured.

---

## 🔍 Why ManulEngine?

Most "AI testing" tools are cloud-dependent wrappers that trade speed and reliability for hype. ManulEngine takes the opposite approach.

### Deterministic First — Not an AI Wrapper

The core engine is a **lightning-fast JavaScript `TreeWalker`** paired with a **mathematically sound `DOMScorer`**. Every element resolution is a pure function of DOM state and weighted heuristic signals — no randomness, no token limits, no API latency. The result is 100% predictable: same page, same step, same outcome. Every time.

### Dual Persona Workflow — Testing for Humans, Power for Engineers

QA engineers write `.hunt` files in a plain-English DSL — no programming required. SDETs extend the same files with Python hooks (`[SETUP]`/`[TEARDOWN]`, `CALL PYTHON`, `@before_all`), Custom Controls, and data-driven parameters. Both personas work on the same artifact. No translation layer, no framework lock-in.

### Optional AI Fallback — Off by Default

AI (Ollama / local micro-LLMs) is **turned off by default** (`"model": null`). The heuristics engine handles the vast majority of real-world UIs on its own. When you do enable a model, it acts as a self-healing fallback — only invoked when heuristic confidence drops below a threshold. No cloud calls. No per-click charges. No flaky non-determinism in your CI pipeline.

---

## 🏛️ Beyond Testing: 4 Pillars of Automation

ManulEngine is not just a test runner — it is a **Universal Web & Desktop Automation Runtime**. The same `.hunt` DSL, the same heuristics engine, and the same Playwright backend power four distinct automation pillars:

### 1. QA & E2E Testing

The core offering. Write plain-English test scenarios, use Python hooks for DB seeding and teardown, attach `@data:` files for data-driven runs, and generate interactive HTML reports. ManulEngine replaces fragile selector-based test suites with deterministic, human-readable scripts that survive UI refactors.

### 2. RPA (Robotic Process Automation)

Automate repetitive business tasks — logging into a CRM, downloading invoices, filling compliance forms, scraping vendor portals — without writing fragile Selenium code. A `.hunt` file is a self-contained automation script: `NAVIGATE`, `FILL`, `CLICK`, `EXTRACT`, `CALL PYTHON`. Schedule it with `@schedule:` and the built-in daemon and let the Manul do the work.

### 3. Synthetic Monitoring

Run `.hunt` scripts on a schedule to verify production health. A three-step checkout flow, an API-backed dashboard, a login gate — if it works in a hunt file, it works as a synthetic monitor. Pair with `--html-report` and `--screenshot on-fail` for instant incident forensics.

### 4. AI Agent Execution

The safest way to execute AI-generated browser actions. Instead of letting LLMs hallucinate raw Playwright calls, have them generate strict `.hunt` DSL — a constrained, validated instruction set. ManulEngine's deterministic engine executes the script safely, with built-in retries, self-healing, and screenshot capture. No prompt injection into the browser. No unbounded API calls. Full auditability.

---

## 🖥️ Beyond the Web: Desktop App Automation

ManulEngine automates **Electron-based desktop applications** using the same DSL, the same heuristic engine, and the same scoring transparency as web testing. Discord, Slack, Spotify, VS Code — any app built on Electron exposes a Chromium DevTools interface that ManulEngine can attach to.

### How it works

1. Set `executable_path` in your config to the path of the Electron app.
2. Use `OPEN APP` as the first step instead of `NAVIGATE`.
3. Write your steps in plain English — the engine attaches to the app's window and resolves elements identically to a web page.

**Configuration — Discord example on Linux:**

```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "/usr/share/discord/Discord",
  "controls_cache_enabled": true
}
```

**Configuration — Discord example on Windows:**

```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "C:\\Users\\YourUser\\AppData\\Local\\Discord\\app-1.0.9051\\Discord.exe",
  "controls_cache_enabled": true
}
```

**Hunt file for a desktop app:**

```text
@context: Smoke test for the Discord desktop client
@title: Discord Desktop Smoke

STEP 1: Attach to the app window
    OPEN APP
    VERIFY that 'Discord' is present

STEP 2: Navigate to a server
    Click the 'My Server' icon
    VERIFY that 'Text Channels' is present
    DONE.
```

![Demo: Desktop app automation with ManulEngine](link)

> **Note:** `OPEN APP` waits for the app's default window to appear, attaches to it, and waits for DOM settlement. No `NAVIGATE` step is needed. Use `executable_path` for Electron apps; for installed browser channels (Chrome, Edge), use `channel` instead.

---

## 🔍 Explainable Heuristics — Full Scoring Transparency

ManulEngine does not use a "black box" AI model to pick DOM elements. Every resolution is a **pure mathematical function** of the DOM state, weighted heuristic signals, and your step text. The engine provides **three levels of transparency** — from CLI output to IDE hover tooltips.

### CLI: `--explain`

```bash
# Run any hunt file with scoring transparency
manul --explain tests/smoke.hunt

# Combine with other flags
manul --explain --headless tests/ --html-report
```

Example output for a `Click the 'Login' button` step:

```
    ┌─ 🔍 EXPLAIN: Target = "Login"
    │  Step: Click the 'Login' button
    │  Top 3 candidates:
    │
    │  #1  <button> "Login button"  → Total: 0.593
    │       Text:       +0.281
    │       Attributes: +0.050
    │       Semantics:  +0.225
    │       Proximity:  +0.037
    │       Cache:      +0.000
    │
    │  #2  <a> "Login link"  → Total: 0.180
    │       Text:       +0.141
    │       Attributes: +0.011
    │       Semantics:  +0.017
    │       Proximity:  +0.011
    │       Cache:      +0.000
    │
    │  #3  <span> "Login → Account"  → Total: 0.048
    │       Text:       +0.028
    │       Attributes: +0.006
    │       Semantics:  +0.008
    │       Proximity:  +0.006
    │       Cache:      +0.000
    │
    └─ ✅ Decision: Selected "Login button" with score 0.593
```

### IDE: Title Bar & Hover Tooltips

The VS Code extension surfaces `--explain` directly in the editor:

- **🔍 Explain Current Step (Title Bar Button)** — During a Debug session, click the `🔍` icon in the editor title bar to trigger an explain action on the current paused step.
- **🔍 Hover Tooltips in Debug Mode** — After running a hunt in Debug Mode, hover over any step line to see the full heuristic breakdown as a rich Markdown tooltip.

### IDE: Hover Tooltips in Debug Mode (Killer Feature)

Run a hunt file in **Debug Mode** (via VS Code Test Explorer's Debug profile or `--break-lines`). After the run completes, **hover your mouse over any step line** in the `.hunt` file. A rich Markdown tooltip appears instantly, showing:

- The **top candidates** with their per-channel scores (Text, Attributes, Semantics, Proximity, Cache)
- The **final decision** — which element was selected and why
- The **confidence score** on the normalised 0.0–1.0 scale

No terminal scrolling. No output channel switching. The explanation is **attached to the exact line** in your editor.

![Demo: Hover over a step to see the heuristic breakdown as a tooltip](link)

**Why this matters:**
- **Zero debug guesswork.** When a step targets the wrong element, hover over it to see *exactly* which signals pulled the score in each direction.
- **Deterministic auditability.** Every score is a reproducible mathematical result. Same page, same step, same breakdown. Every time.
- **No AI required.** The explain output comes from the heuristic scorer, not an LLM. It works in heuristics-only mode (`"model": null`) — the recommended default.

In VS Code, you can see this explain output directly via hover tooltips on `.hunt` steps during Debug mode, or by clicking the `🔍 Explain Current Step` title bar button while paused at a breakpoint. Set `MANUL_EXPLAIN=true` for CI pipelines.

---

## ✨ Key Features

### ⚡ Heuristics Engine — The Mathematical Core

Element resolution is driven entirely by the `DOMScorer` — a strict, normalised **0.0 to 1.0 confidence scale** across five weighted channels:

| Channel | Weight | Purpose |
|---|---|---|
| `cache` | 2.0 | Reuse previously resolved elements — a semantic cache hit yields a **perfect 1.0 confidence score** |
| `semantics` | 0.60 | Element-type alignment, role synergy |
| `text` | 0.45 | Text, aria-label, placeholder, data-qa matching |
| `attributes` | 0.25 | html_id, dev naming conventions |
| `proximity` | 0.10 | DOM depth-based form context |

Final score = weighted sum × penalty multiplier × `SCALE` (177,778). An exact `data-qa` match scores +1.0 text (~80k scaled) — the single strongest heuristic signal. Disabled elements are crushed by a ×0.0 multiplier. No guesswork, no randomness.

Confidence scores above `MAX_THEORETICAL_SCORE` (e.g. semantic cache hits at ~355k) are clamped to `1.0` in explain-mode output, providing a clean, human-readable scale.

### 🌳 TreeWalker — Zero-Waste DOM Traversal

`SNAPSHOT_JS` walks the DOM with a native `document.createTreeWalker()` and a `PRUNE` set that rejects entire irrelevant subtrees (`SCRIPT`, `STYLE`, `SVG`, `NOSCRIPT`, `TEMPLATE`, etc.) in a single hop. Visibility is checked via the zero-layout-thrash `checkVisibility()` API. No `querySelectorAll`. No `getComputedStyle` in the hot loop.

### 🧠 20+ Accessibility Signals

Manul scores elements using `aria-label`, `placeholder`, `name`, `data-qa`, `html_id`, semantic `input type`, contextual section headings, and more. Modern SPAs (React, Vue, Angular) and complex design systems (Wikipedia Vector 2022 / Codex) work without any tuning — accessibility attributes are first-class identifiers.

### 🛡️ Ironclad JS Fallbacks

Modern websites hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. Manul uses Playwright with `force=True` plus retries and self-healing; for Shadow DOM elements it falls back to direct JS helpers to keep execution moving.

### 🌑 Shadow DOM & iframe Awareness

The DOM snapshotter recursively walks shadow roots via `TreeWalker` and scans same-origin iframes by iterating `page.frames`. Each element carries a `frame_index` that routes all downstream actions to the correct Playwright `Frame`. Cross-origin frames are silently skipped.

### 🗂️ Persistent Controls Cache

Successful element resolutions are stored per-site in a file-based cache and reused on subsequent runs. Stale entries are **self-healed** at runtime — when a cached locator no longer matches any live DOM candidate, the engine re-resolves via heuristics and updates the cache automatically.

### ⚡ Semantic Cache — Perfect 1.0 Confidence on Reuse

The in-session semantic cache (`learned_elements`) remembers every resolved element within a single run. When the same `(mode, target_text, target_field)` combination is encountered again, the cache grants a **perfect 1.0 confidence score** (×2.0 cache weight = ~355k scaled) — bypassing all other scoring channels and guaranteeing **lightning-fast execution** for stable UI elements. The engine short-circuits at scores ≥ 200,000, skipping the LLM entirely. Reset on each new `ManulEngine` instance.

### 🤖 Optional AI Fallback (Ollama)

When enabled, the local LLM acts as a self-healing safety net — only invoked when heuristic confidence drops below a configurable threshold. The heuristic `score` is passed as a **prior** (hint) — the model can override only with a clear reason. AI rejection (`{"id": null}`) triggers scroll-and-retry self-healing.

| Model size | Auto threshold |
|---|---|
| `< 1b` | `500` |
| `1b – 4b` | `750` |
| `5b – 9b` | `1000` |
| `10b – 19b` | `1500` |
| `20b+` | `2000` |

Set `"model": null` (the default) to run in **heuristics-only mode** — no Ollama, no AI, fully deterministic.

### 🔄 Automatic Retries — Tame Flaky Tests

Real-world E2E tests flake. Network hiccups, slow renders, third-party scripts — you name it. ManulEngine lets you retry failed hunts automatically:

```bash
manul tests/ --retries 2                # retry each failed hunt up to 2 times
manul tests/ --retries 3 --html-report  # retry + generate an HTML report
```

Or set `"retries": 2` in `manul_engine_configuration.json` for a permanent default. Each retry is a full fresh run — no stale state carried over.

### 📊 Interactive Enterprise HTML Reporter

One flag. One self-contained HTML file. Dark-themed dashboard with pass/fail stats, native HTML5 `<details>` step accordions, inline base64 screenshots, and XSS-safe output — zero external dependencies, zero CDN, zero server.

**Enterprise Upgrades:**
* **Dual-Mode Rendering:** If `STEP` blocks are used, steps are grouped into logical Accordions. Passing steps collapse by default; failing steps auto-expand to show exactly what broke.
* **Flexbox Layout:** Dropped clunky tables for a sleek Flexbox design ensuring perfect text alignment and zero text mashing.
* **"Show Only Failed" Toggle:** A control-panel checkbox instantly hides all passing tests — zero-click triage for large suites.
* **Tag Filter Chips:** All `@tags` from executed hunt files are collected and rendered as clickable chips. Click a tag to show only matching tests — perfect for filtering by `smoke`, `regression`, `login`, etc.
* **Warning Status:** Amber `⚠️ Warning` badges for soft assertion failures (`VERIFY SOFTLY`).

```bash
manul tests/ --html-report                          # report saved to reports/manul_report.html
manul tests/ --screenshot always --html-report      # embed a screenshot for every step
manul tests/ --screenshot on-fail --html-report     # screenshots only on failures
```

All artifacts (logs, reports) are saved to the `reports/` directory — your workspace stays clean.

> **Note:** Per-step details (accordion + embedded screenshots) require `--workers 1` (the default). When `--workers > 1`, the report aggregates per-hunt results only.

### 📋 STEP Groups — Manual Test Cases Meet Automation

Use `STEP N: Description` headers to mirror the structure of your manual test plan directly in the `.hunt` file. The engine renders each group as an accordion section in the HTML report — with its own pass/fail badge and action count — so stakeholders can read results without decoding raw step indices.

```text
STEP 1: Login
    NAVIGATE to https://myapp.com/login
    Fill 'Email' with '{email}'
    Fill 'Password' with '{password}'
    Click 'Sign In' button
    VERIFY that 'Dashboard' is present.

STEP 2: Add item to cart
    Click 'Add to cart' near 'Laptop Pro'
    NAVIGATE to https://myapp.com/cart
    VERIFY that 'Laptop Pro' is present.
```

`STEP` headers produce zero browser actions — they are pure metadata. Action lines must be written as **plain text without leading numbers** — never prefix with `1.`, `2.`, etc.

---

## 🎛️ Custom Controls — Escape Hatch for Complex UI

Some UI elements defeat general-purpose heuristics: React virtual tables, canvas-based date-pickers, WebGL widgets, drag-to-sort lists. **Custom Controls** let QA write plain English while an SDET handles the Playwright logic in Python.

```python
# controls/booking.py
from manul_engine import custom_control

@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_datepicker(page, action_type, value):
    await page.locator(".react-datepicker__input-container input").fill(value or "")
```

```text
# tests/checkout.hunt  — no change needed for the QA author
Fill 'React Datepicker' with '2026-12-25'
```

The engine loads every `.py` file in `controls/` at startup. No configuration required.

---

## 🎬 Smart Recording — `manul record`

`manul record https://example.com` opens a browser with a live recording overlay. Click, type, select, and navigate — every action is captured and translated into clean `.hunt` DSL in real time. Stop the recording and a ready-to-run hunt file is saved.

The recorder now handles **native `<select>` dropdowns** using semantic `change` events, generating clean `Select 'Option' from 'Dropdown'` commands instead of raw click sequences. Clicks on `<select>` and `<option>` elements are intelligently suppressed — only the final selection is captured.

---

## 🧠 State Management & Strict Scoping

ManulEngine enforces a **strict four-level variable precedence hierarchy** that eliminates state leakage between data-driven loop iterations and makes variable resolution fully deterministic:

| Priority | Level | Source | Lifetime |
|---|---|---|---|
| **1 (highest)** | Row Vars | `@data:` CSV/JSON iteration | Cleared after each data row |
| **2** | Step Vars | `EXTRACT`, `CALL PYTHON into {var}`, `SET` | Cleared after each data row |
| **3** | Mission Vars | `@var:` file header declarations | Persists for the entire mission |
| **4 (lowest)** | Global Vars | CLI, env vars, `@before_all` hooks | Persists across all missions |

A higher-level variable always shadows a lower-level one with the same name. When a `@data:` row defines `{email}`, it overrides any `@var: {email}` declaration — no ambiguity, no surprises.

```text
@var: {email}    = default@example.com          # Level 3 — Mission
@var: {password} = secret123                    # Level 3 — Mission
@data: users.csv                                # Level 1 — Row (overrides email per iteration)

STEP 1: Login with row data
    NAVIGATE to https://myapp.com/login
    Fill 'Email' with '{email}'                 # ← uses Row value when @data provides it
    Fill 'Password' with '{password}'           # ← uses Mission value (no row override)
    Click the 'Sign In' button
    VERIFY that 'Dashboard' is present.
```

### Inspecting variable state at runtime

Use `DEBUG VARS` as a step to print the complete scoping state at any point during execution:

```text
STEP 2: Debug
    EXTRACT the 'Order ID' into {order_id}
    DEBUG VARS
```

Output:

```
  ┌─ Level 1 — Row Vars (@data)
  │  {email} = user1@test.com
  └──────────────────────────────────────────────────
  ┌─ Level 2 — Step Vars (EXTRACT / CALL PYTHON into)
  │  {order_id} = ORD-12345
  └──────────────────────────────────────────────────
  ┌─ Level 3 — Mission Vars (@var:)
  │  {password} = secret123
  └──────────────────────────────────────────────────
  ┌─ Level 4 — Global Vars (CLI / env / @before_all)
  │  {BASE_URL} = https://staging.example.com
  └──────────────────────────────────────────────────
```

### Zero state leakage guarantee

Between `@data:` iterations, the engine clears Level 1 (Row) and Level 2 (Step) variables automatically. Mission-scoped (`@var:`) and Global-scoped (lifecycle hooks) variables persist unchanged. This means:
- An `EXTRACT` from iteration 1 never bleeds into iteration 2.
- A `CALL PYTHON ... into {var}` capture is scoped to the current iteration.
- `@var:` declarations are immutable across iterations — they act as constants.


---

## 📋 Static Variables — Clean Test Data, Zero Hardcoding

Declare all test data at the top of your `.hunt` file with `@var:`:

```text
@var: {email}    = admin@example.com
@var: {password} = secret123

STEP 1: Login
    NAVIGATE to https://myapp.com/login
    Fill 'Email' with '{email}'
    Fill 'Password' with '{password}'
    Click the 'Sign In' button
    VERIFY that 'Dashboard' is present.
```

---

## 🏷️ Tags — Run Exactly What You Need

```text
@tags: smoke, auth, regression
```

```bash
manul tests/ --tags smoke               # run only 'smoke'-tagged files
manul tests/ --tags smoke,critical      # OR logic — either tag matches
```

---

## ⚡ Python Hooks — Fast Preconditions & Mid-Test Backend Calls

`[SETUP]` and `[TEARDOWN]` run synchronous Python functions outside the browser. Inline `CALL PYTHON` steps run inside the mission for mid-test backend interactions.

```text
@var: {email} = admin@example.com

[SETUP]
CALL PYTHON db_helpers.seed_admin_user
[END SETUP]

STEP 1: Login
    NAVIGATE to https://myapp.com/login
    Fill 'Email' field with '{email}'
    Click the 'Sign In' button
    VERIFY that 'Dashboard' is present.

STEP 2: OTP verification
    Click the 'Send OTP' button
    CALL PYTHON api_helpers.fetch_otp "{email}" into {otp}
    Fill 'OTP' field with '{otp}'
    Click the 'Verify' button
    VERIFY that 'Welcome' is present.

[TEARDOWN]
CALL PYTHON db_helpers.clean_database
[END TEARDOWN]
```

| Block | When it runs | Abort behaviour |
|---|---|---|
| `[SETUP]` | Before the browser launches | Failure skips mission + teardown |
| `[TEARDOWN]` | After the mission (pass or fail) | Failure is logged, does not override mission result |
| Inline `CALL PYTHON` | During the mission, as a step | Failure stops the mission immediately |

---

## 🌐 Global Lifecycle Hooks — Enterprise-Scale Orchestration

For multi-file test suites that need shared state — a global auth token, a seeded database, a per-run environment flag — create a `manul_hooks.py` file in the same directory as your `.hunt` files. The engine discovers and loads it automatically.

```python
# tests/manul_hooks.py
from manul_engine import before_all, after_all, before_group, after_group, GlobalContext

@before_all
def global_setup(ctx: GlobalContext) -> None:
    ctx.variables["BASE_URL"] = "https://staging.example.com"
    ctx.variables["API_TOKEN"] = fetch_token_from_vault()

@after_all
def global_teardown(ctx: GlobalContext) -> None:
    db.rollback_all_test_data()

@before_group(tag="smoke")
def seed_smoke(ctx: GlobalContext) -> None:
    ctx.variables["ORDER_ID"] = db.create_temp_order()

@after_group(tag="smoke")
def clean_smoke(ctx: GlobalContext) -> None:
    ctx.variables.pop("ORDER_ID", None)
```

Variables written to `ctx.variables` are injected into every matching mission as `{placeholder}`-ready data — shared across all hunt files.

| Hook | When it fires | Failure behaviour |
|---|---|---|
| `@before_all` | Once before the first hunt file | Aborts the entire suite; `@after_all` still runs |
| `@after_all` | Once after all hunts finish | Always runs; failure logged, does not override suite result |
| `@before_group(tag=)` | Before each hunt file whose `@tags:` contains `tag` | Failure skips that mission; `@after_group` still runs for it |
| `@after_group(tag=)` | After each matching mission (pass or fail) | Always runs; failure logged, does not override mission result |

When running with `--workers N`, `@before_all` runs in the orchestrator process and `ctx.variables` are serialised via `MANUL_GLOBAL_VARS` into worker subprocesses.

---

## 💻 System Requirements

| | Minimum | Recommended |
|---|---|---|
| **CPU** | any | modern laptop |
| **RAM** | 4 GB | 8 GB |
| **GPU** | none | none |
| **Model** | — (heuristics-only) | `qwen2.5:0.5b` |

## 🛠️ Installation

```bash
pip install manul-engine
playwright install chromium
```

### Optional: Local LLM (Ollama)

Ollama is only needed for AI element-picker fallback or free-text mission planning.

```bash
pip install ollama          # Python client library
ollama pull qwen2.5:0.5b   # download model (requires Ollama app: https://ollama.com)
ollama serve
```

---

## 🚀 Quick Start

### 1. Create a hunt file

`my_tests/smoke.hunt`

```text
@context: Demo smoke test
@title: smoke
@tags: smoke

@var: {name} = Ghost Manul

STEP 1: Fill text box form
    NAVIGATE to https://demoqa.com/text-box
    Fill 'Full Name' field with '{name}'
    Click the 'Submit' button
    VERIFY that '{name}' is present.
    DONE.
```

### 2. Run it

```bash
# Run a specific hunt file
manul my_tests/smoke.hunt

# Run all *.hunt files in a folder
manul my_tests/

# Run headless
manul my_tests/ --headless

# Choose a different browser
manul my_tests/ --browser firefox
manul my_tests/ --headless --browser webkit

# Run an inline one-liner
manul "NAVIGATE to https://example.com  Click the 'More' link  DONE."

# Run multiple hunt files in parallel (4 concurrent browsers)
manul my_tests/ --workers 4

# Run only files tagged 'smoke'
manul my_tests/ --tags smoke

# Retry failed hunts up to 2 times
manul my_tests/ --retries 2

# Generate a standalone HTML report
manul my_tests/ --html-report

# Screenshots on failure + HTML report + retries (the full CI combo)
manul my_tests/ --retries 2 --screenshot on-fail --html-report

# Screenshots for every step (detailed forensic report)
manul my_tests/ --screenshot always --html-report

# Run with full heuristic transparency
manul --explain my_tests/smoke.hunt

# Interactive debug mode (terminal)
manul --debug my_tests/smoke.hunt

# Smart Page Scanner — scan a URL and generate a draft hunt file
manul scan https://example.com
manul scan https://example.com tests/my.hunt
manul scan https://example.com --headless

# Semantic Test Recorder — record interactions as .hunt DSL
manul record https://example.com
```

> **VS Code:** Place gutter breakpoints in any `.hunt` file and run the **Debug profile** in Test Explorer. Use the QuickPick overlay: Next Step, Continue All, Highlight Element, Debug Stop, or Stop Test.

### Daemon Mode & Scheduling (RPA / Monitoring)

ManulEngine includes a built-in scheduler — no external cron jobs required. Add a `@schedule:` header to any `.hunt` file and launch the daemon:

```text
@context: Production health check
@title: Checkout Monitor
@schedule: every 5 minutes

STEP 1: Verify checkout flow
    NAVIGATE to https://shop.example.com
    Click the 'Add to Cart' button
    Click the 'Checkout' button
    VERIFY that 'Order Summary' is present
    DONE.
```

```bash
manul daemon tests/ --headless
```

Supported `@schedule:` expressions:

| Expression | Meaning |
|---|---|
| `every 30 seconds` | Run every 30 seconds |
| `every 5 minutes` | Run every 5 minutes |
| `every hour` | Run every hour |
| `daily at 09:00` | Run once a day at 09:00 |
| `every monday` | Run once a week on Monday at 00:00 |
| `every friday at 14:30` | Run once a week on Friday at 14:30 |

### 3. Python API

```python
import asyncio
from manul_engine import ManulEngine

async def main():
    manul = ManulEngine(headless=True)
    await manul.run_mission("""
        STEP 1: Fill text box form
        NAVIGATE to https://demoqa.com/text-box
        Fill 'Full Name' field with 'Ghost Manul'
        Click the 'Submit' button
        VERIFY that 'Ghost Manul' is present.
        DONE.
    """)

asyncio.run(main())
```

---

## 📜 Hunt File Format — Reference

Hunt files are plain-text automation scripts with a `.hunt` extension.

### Headers (optional)

```text
@context: Strategic context for the engine
@title: short-tag
@tags: smoke, auth, regression
@var: {email} = admin@example.com
@data: users.csv
@schedule: every 5 minutes
```

### Comments

Lines starting with `#` are ignored.

### System Keywords

| Keyword | Description |
|---|---|
| `NAVIGATE to [URL]` | Load a URL and wait for DOM settlement |
| `OPEN APP` | Attach to an Electron/Desktop app's default window |
| `WAIT [seconds]` | Hard sleep |
| `PRESS ENTER` | Press Enter on the currently focused element |
| `PRESS [Key]` | Press any key or combination globally (e.g. `PRESS Escape`, `PRESS Control+A`) |
| `PRESS [Key] on [Target]` | Press a key on a specific element |
| `RIGHT CLICK [Target]` | Right-click an element to open a context menu |
| `UPLOAD 'File' to 'Target'` | Upload a file to a file input element |
| `SCROLL DOWN` | Scroll the main page down one viewport |
| `EXTRACT [target] into {var}` | Extract text into a memory variable |
| `VERIFY that [target] is present` | Assert text/element is visible |
| `VERIFY that [target] is NOT present` | Assert absence |
| `VERIFY that [target] is DISABLED` | Assert element is disabled |
| `VERIFY that [target] is ENABLED` | Assert element is enabled |
| `VERIFY that [target] is checked` | Assert checkbox state |
| `VERIFY VISUAL 'Element'` | Pixel-compare element screenshot against a saved baseline |
| `VERIFY SOFTLY that [target] is present` | Non-blocking assertion (failure = warning, not stop) |
| `MOCK METHOD "url" with 'file'` | Intercept matching network requests with a local mock |
| `WAIT FOR RESPONSE "url"` | Block until a matching network response arrives |
| `SCAN PAGE` | Scan the page for interactive elements and print a draft `.hunt` |
| `SET {variable} = value` | Set a runtime variable mid-flight |
| `DEBUG` / `PAUSE` | Pause execution at that step |
| `DONE.` | End the mission |

### Interaction Steps

```text
Click the 'Login' button
Fill 'Email' field with 'test@example.com'
Select 'Option A' from the 'Language' dropdown
Check the checkbox for 'Terms'
HOVER over the 'Menu'
Drag the element "Item" and drop it into "Box"
Click 'Close Ad' if exists              # non-blocking (optional step)
```

---

## ⚙️ Configuration

Create `manul_engine_configuration.json` in your project root — all settings are optional:

```json
{
  "model": null,
  "headless": false,
  "browser": "chromium",
  "browser_args": [],
  "timeout": 5000,
  "nav_timeout": 30000,
  "controls_cache_enabled": true,
  "controls_cache_dir": "cache",
  "semantic_cache_enabled": true,
  "tests_home": "tests",
  "channel": null,
  "executable_path": null,
  "retries": 0,
  "screenshot": "on-fail",
  "html_report": false
}
```

> Set `"model": null` (or omit it) to disable AI entirely and run in **heuristics-only mode** — the recommended default.

Environment variables (`MANUL_*`) always override JSON values — useful for CI/CD:

```bash
export MANUL_HEADLESS=true
export MANUL_MODEL=qwen2.5:0.5b
export MANUL_BROWSER=firefox
export MANUL_EXPLAIN=true
```

| Key | Default | Description |
|---|---|---|
| `model` | `null` | Ollama model name. `null` = heuristics-only (no AI) |
| `headless` | `false` | Hide browser window |
| `browser` | `"chromium"` | Browser engine: `chromium`, `firefox`, or `webkit` |
| `browser_args` | `[]` | Extra launch flags for the browser (array of strings) |
| `ai_threshold` | auto | Score threshold before LLM fallback. `null` = auto by model size |
| `ai_always` | `false` | Always use LLM picker, bypass heuristic short-circuits |
| `ai_policy` | `"prior"` | `"prior"` (LLM may override score) or `"strict"` (enforce max-score) |
| `controls_cache_enabled` | `true` | Persistent per-site controls cache (file-based, survives between runs) |
| `controls_cache_dir` | `"cache"` | Cache directory (relative to CWD or absolute) |
| `semantic_cache_enabled` | `true` | In-session semantic cache; perfect 1.0 confidence on reuse |
| `timeout` | `5000` | Default action timeout (ms) |
| `nav_timeout` | `30000` | Navigation timeout (ms) |
| `log_name_maxlen` | `0` | Truncate element names in logs (0 = no limit) |
| `log_thought_maxlen` | `0` | Truncate LLM thoughts in logs (0 = no limit) |
| `workers` | `1` | Number of hunt files to run concurrently (each gets its own browser) |
| `tests_home` | `"tests"` | Default directory for new hunt files and `SCAN PAGE` output |
| `auto_annotate` | `false` | Auto-insert `# 📍 Auto-Nav:` comments when the browser URL changes |
| `channel` | `null` | Playwright browser channel (e.g. `"chrome"`, `"msedge"`) |
| `executable_path` | `null` | Absolute path to a custom browser executable (e.g. Electron) |
| `retries` | `0` | Number of times to retry a failed hunt file (0 = no retries) |
| `screenshot` | `"on-fail"` | `"none"`, `"on-fail"` (default), or `"always"` |
| `html_report` | `false` | Generate `reports/manul_report.html` after the run |

---

## 🤖 Generate Hunt Files with AI Prompts

The `prompts/` directory contains ready-to-use LLM prompt templates:

| Prompt file | When to use |
|---|---|
| `prompts/html_to_hunt.md` | Paste a page's HTML source → get complete hunt steps |
| `prompts/description_to_hunt.md` | Describe a page or flow in plain text → get hunt steps |

See [`prompts/README.md`](prompts/README.md) for usage with GitHub Copilot, ChatGPT, Claude, and local Ollama.

---

## 📋 Available Commands — Quick Reference

| Category | Command Syntax |
|---|---|
| **Navigation** | `NAVIGATE to [URL]`, `OPEN APP` |
| **Input** | `Fill [Field] with [Text]`, `Type [Text] into [Field]` |
| **Click** | `Click [Element]`, `DOUBLE CLICK [Element]`, `RIGHT CLICK [Element]` |
| **Selection** | `Select [Option] from [Dropdown]`, `Check [Checkbox]`, `Uncheck [Checkbox]` |
| **Mouse Action** | `HOVER over [Element]`, `Drag [Element] and drop it into [Target]` |
| **Data Extraction** | `EXTRACT [Target] into {variable_name}` |
| **Verification** | `VERIFY that [Text] is present/absent`, `VERIFY that [Element] is checked/disabled/enabled`, `VERIFY VISUAL 'Element'`, `VERIFY SOFTLY ...` |
| **Network** | `MOCK METHOD "url" with 'file'`, `WAIT FOR RESPONSE "url"` |
| **Page Scanner** | `SCAN PAGE`, `SCAN PAGE into {filename}` |
| **Debug** | `DEBUG` / `PAUSE` |
| **Keyboard** | `PRESS ENTER`, `PRESS [Key]`, `PRESS [Key] on [Element]` |
| **File Upload** | `UPLOAD 'File' to 'Element'` |
| **Variables** | `SET {variable} = value`, `@var: {name} = value` |
| **Flow Control** | `WAIT [seconds]`, `SCROLL DOWN` |
| **Finish** | `DONE.` |

> Append `if exists` or `optional` to any step (outside quoted text) to make it non-blocking.

---

## 🏋️ Benchmarks & Proof

ManulEngine ships with a dedicated benchmark suite (`benchmarks/`) that pits its heuristic engine against raw Playwright locators on adversarial HTML fixtures:

| Fixture | What it tests |
|---|---|
| `dynamic_ids.html` | Randomised `id` and `class` attributes on every page load |
| `overlapping.html` | Hidden traps, zero-pixel elements, offscreen honeypots, duplicate buttons |
| `nested_tables.html` | Deeply nested `<table>` layouts without IDs or ARIA labels |
| `custom_dropdown.html` | `<div>`-based custom dropdown with ARIA roles alongside a native `<select>` |

```bash
python benchmarks/run_benchmarks.py
```

Raw Playwright locators work when you know the exact selector. ManulEngine's heuristics work when you only know what the element *means* — which is every real-world scenario where selectors break after a UI refactor.

---

## 🐾 Battle-Tested

ManulEngine is verified against **2358 synthetic DOM tests** across 45 test suites covering:

- Shadow DOM, invisible overlays, zero-pixel honeypots
- Same-origin iframe element routing and cross-frame resolution
- Normalised DOMScorer weighting hierarchy (data-qa > text > attributes)
- TreeWalker PRUNE-set filtering and `checkVisibility()` visibility gating
- Custom dropdowns, drag-and-drop, hover menus
- Legacy HTML (tables, fieldsets, unlabelled inputs)
- AI rejection & self-healing loops
- Persistent controls cache hit/miss and self-healing cycles
- Desktop/Electron app attachment via `OPEN APP`

---

**Version:** 0.0.9.5 · **Stack:** Python 3.11 · Playwright · Ollama (optional) · **Status:** Hunting...
