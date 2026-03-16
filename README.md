# 😼 ManulEngine — The Universal Web Automation Runtime

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)

**ManulEngine — The Deterministic, DSL-First Web Automation Runtime with Explainable Heuristics.**
Write automation scripts in plain-English Hunt DSL. Run E2E tests, RPA workflows, synthetic monitoring, and AI-agent actions — powered by blazing-fast JS heuristics and Playwright. Every element resolution is explainable, reproducible, and mathematically provable.

No CSS selectors. No XPath fragility. No cloud API bills.
ManulEngine is an interpreter for the `.hunt` DSL — a Playwright-backed runtime that resolves DOM elements with a mathematically sound `DOMScorer` (normalised 0.0–1.0 float scoring across 20+ signals) and a native JavaScript `TreeWalker`. Deterministic, reproducible, and fast enough to run anywhere: CI pipelines, cron jobs, or a developer's laptop.

> The Manul goes hunting and never returns without its prey.

> **Zero AI required. Zero cloud dependency. Zero flakiness by design.**
> Playwright speed. Heuristic precision. Full scoring transparency via `--explain`. Optional local micro-LLMs via Ollama — only when you need them.

---

## 🚀 What's New in v0.0.9.4 — Hardening & Transparency

* **Explainable Heuristics (`--explain`):** Run any hunt with `manul --explain tests/smoke.hunt` to see a full per-element scoring breakdown for every step. The engine prints the top 3 candidates with their individual channel scores (Text, Attributes, Semantics, Proximity, Cache) and the final decision — making heuristic resolution fully transparent. No more "why did it click that?" mysteries. See the [Explainable Heuristics](#-explainable-heuristics----explain) section below.
* **Strict Variable Scoping (`ScopedVariables`):** The engine now enforces a strict four-level variable precedence hierarchy: `Row Vars (@data)` > `Step Vars (EXTRACT / CALL PYTHON into)` > `Mission Vars (@var:)` > `Global Vars (CLI / env / @before_all)`. This eliminates state leakage between `@data:` loop iterations and makes variable resolution fully predictable. A new `DEBUG VARS` step command prints the complete scoping state at any point during execution. See the [State Management & Strict Scoping](#-state-management--strict-scoping) section below.
* **Benchmark Suite (`manul-benchmarks`):** A dedicated proof suite in `benchmarks/` that pits ManulEngine's heuristic resolution against raw Playwright locators on adversarial HTML fixtures — dynamic IDs, overlapping elements, deeply nested tables, custom dropdowns. The benchmarks mathematically prove the engine's resilience against patterns that break rigid selectors. See the [Benchmarks & Proof](#-benchmarks--proof) section below.

### Previous highlights (v0.0.9.3)

## 🚀 What's New in v0.0.9.3 — The Scheduler Update

* **Built-in Scheduler (`@schedule:` + `manul daemon`):** Add a `@schedule: every 5 minutes` header to any `.hunt` file and launch `manul daemon tests/ --headless` — the engine runs scheduled hunts in an infinite async loop with zero external dependencies. Supports interval expressions (`every N seconds/minutes/hours`), daily schedules (`daily at 09:00`), and weekly schedules (`every monday at 14:30`). Perfect for RPA workflows and synthetic monitoring.
* **Advanced Scheduler Dashboard (VS Code Extension):** A visual RPA manager that displays **all** `.hunt` files in the workspace, split into **Scheduled** and **Unscheduled** sections. A live search bar filters by filename. Each file row includes a combobox with preset schedule options and a custom input — click **Apply** to inject, update, or remove the `@schedule:` header directly in the file. The dashboard also provides **Start Daemon** / **Stop Daemon** buttons that manage the `manul daemon` process directly in the integrated terminal.
* **Persistent Run History & Sparklines:** Every hunt execution (CLI, parallel workers, and daemon mode) appends a JSON record to `reports/run_history.json` (JSON Lines format: `file`, `name`, `timestamp`, `status`, `duration_ms`). The Scheduler Dashboard reads this file and renders a **sparkline** (last 5 runs as 🟢/🔴/🟡 dots) and a **relative timestamp** (e.g. "3m ago") next to each file row — giving instant visibility into test health without leaving the editor.
* **Self-Healing Controls Cache:** The persistent controls cache now detects stale entries at runtime. When a cached locator no longer matches any live DOM candidate, the engine re-resolves the element via heuristics, updates the cache file automatically, and logs a `🩹 HEALED` event. Failed healings are surfaced as `⚠️ STALE` warnings in the HTML report.
* **Semantic Test Recorder (`manul record`):** `manul record https://example.com` opens a browser with a live recording overlay — click, type, and navigate; every action is captured and translated into clean `.hunt` DSL in real time. Stop the recording and a ready-to-run hunt file is saved to `tests_home/`.

### Previous highlights (v0.0.9.2)

## 🚀 What's New in v0.0.9.2 — The Mastermind

* **YAML-Like Indentation:** Hunt files now support clean hierarchical formatting — action lines under `STEP` headers can be indented with spaces or tabs. The parser strips all leading whitespace before processing. The VS Code extension ships a built-in **Auto-Formatter** (`Shift+Alt+F`) that enforces 4-space indentation for action lines under each `STEP` block.
* **`SET` Command — Mid-Flight Variable Assignment:** `SET {variable} = value` assigns or overrides a runtime variable at any point during execution. Both `{braced}` and bare-key forms are accepted. Quoted values are auto-unquoted. The variable is immediately available for `{placeholder}` substitution in all subsequent steps — works alongside `@var:` (static) and `EXTRACT` (dynamic) variables.
* **Enterprise Browser & Electron Support:** New `channel` and `executable_path` config keys let you target installed browser channels (`"chrome"`, `"chrome-beta"`, `"msedge"`) or point to a custom browser executable (e.g. Electron). Overridable via `MANUL_CHANNEL` and `MANUL_EXECUTABLE_PATH` environment variables.
* **`OPEN APP` — Desktop/Electron Attachment:** New DSL command that attaches to an Electron or desktop application's default window instead of navigating to a URL. Use `OPEN APP` as the first step in `.hunt` files targeting `executable_path` apps — the engine waits for the app's window, attaches to it, and waits for DOM settlement. No `NAVIGATE` needed.
* **VS Code Auto-Formatter:** The extension now registers a `DocumentFormattingEditProvider` for `.hunt` files. Press `Shift+Alt+F` (or enable Format on Save) to auto-indent action lines and inline comments with 4 spaces under each `STEP` or hook block. `STEP` headers, metadata (`@context:`, `@var:`, `@tags:`), top-level comments, and `DONE.` remain flush-left.

### Previous highlights (v0.0.9.1)

## 🚀 What's New in v0.0.9.1 — Enterprise DSL

* **Data-Driven Testing (`@data:`):** Declare `@data: users.csv` or `@data: data.json` in any `.hunt` file header. The engine loads each row and reruns the entire mission with row values injected as `{placeholders}`. Supports JSON (array-of-objects) and CSV (DictReader). Zero code changes — same hunt file, *N* executions.
* **Network Interception (`MOCK` / `WAIT FOR RESPONSE`):** `MOCK GET "/api/users" with 'mocks/users.json'` intercepts matching requests via Playwright `page.route()` and fulfills them from a local file. `WAIT FOR RESPONSE "/api/data"` blocks until a matching network response arrives. Supports GET, POST, PUT, PATCH, DELETE.
* **Visual Regression (`VERIFY VISUAL`):** `VERIFY VISUAL 'Logo'` takes an element screenshot, saves a baseline on first run, and pixel-compares on subsequent runs. Baselines live in `visual_baselines/` next to the hunt file. Uses PIL/Pillow when available (threshold-based diff), falls back to raw byte comparison.
* **Soft Assertions (`VERIFY SOFTLY`):** `VERIFY SOFTLY that 'Warning' is present` records a failure but does **not** stop the mission. All soft failures are collected and surfaced as a `"warning"` status in both the CLI summary and the HTML reporter (amber badges, dedicated filter chip, soft-errors block).
* **HTML Reporter — Warning Status:** New amber `⚠️ Warning` stat card, `badge-warning` badges, `step-warning` row styling, `soft-errors` block with itemised list, and a "Show Warnings" filter checkbox in the control panel.

### Previous highlights (v0.0.9.0)

## 🚀 What's New in v0.0.9.0 — The Power User Update

* **`VERIFY ... is ENABLED`:** State verification now supports both `ENABLED` and `DISABLED` checks. Assert that interactive elements are truly active before attempting actions — `VERIFY that 'Submit' is ENABLED`.
* **`CALL PYTHON` with Arguments:** Hook functions and inline `CALL PYTHON` steps now accept positional arguments — static strings, unquoted tokens, and `{var}` placeholders resolved at runtime. `CALL PYTHON helpers.multiply "6" "7" into {product}`. Arguments are tokenised with `shlex.split()`.
* **Interactive HTML Reporter:** Control panel with **"Show Only Failed" checkbox** and **tag filter chips**. All `@tags` from executed hunt files are auto-collected and rendered as clickable chips for instant filtering. Missions carry `data-status` and `data-tags` attributes — all powered by inline Vanilla JS with zero external dependencies.
* **Dual Persona Workflow:** QA writes plain English. SDETs write Python hooks that now accept dynamic arguments (`{variables}`) directly from the `.hunt` file — no code changes needed on the QA side when backend logic evolves.

### Previous highlights

* **Normalised Heuristic Scoring (DOMScorer):** The scoring engine now uses `0.0–1.0` float arithmetic under the hood. Five weighted channels — `cache` (2.0), `semantics` (0.60), `text` (0.45), `attributes` (0.25), `proximity` (0.10) — are combined via a `WEIGHTS` dict and multiplied by `SCALE=177,778` to produce the final integer score. Exact `data-qa` match is the single strongest heuristic signal (+1.0 text). Penalties are clean multipliers: disabled ×0.0, hidden ×0.1.
* **TreeWalker-Based DOM Scanner:** `SNAPSHOT_JS` no longer calls `querySelectorAll` — it walks the DOM with a native `TreeWalker` and a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`) that rejects entire subtrees in one hop. Visibility is checked via the zero-layout-thrash `checkVisibility()` API with automatic `offsetWidth/offsetHeight` fallback. Hidden file/checkbox/radio inputs are preserved as special exceptions.
* **Safe iframe Support:** `_snapshot()` iterates `page.frames`, injects `SNAPSHOT_JS` into each same-origin frame, and tags every returned element with `frame_index`. `_frame_for(page, el)` routes all downstream `locator()` and `evaluate()` calls to the correct Playwright `Frame`. Cross-origin and detached frames are silently skipped with retry logic.
* **Clean, Unnumbered DSL:** Scripts now read exactly like plain English (`NAVIGATE to url` instead of `1. NAVIGATE to url`).
* **Logical STEP Grouping:** `STEP [optional number]: [Description]` metadata blocks map manual QA cases directly into `.hunt` files.
* **Interactive Enterprise HTML Reporter:** Dual-mode, zero-dependency reporter with native HTML5 accordions, auto-expanding failures, Flexbox layout, **"Show Only Failed" toggle**, and **tag-based filtering chips** — all powered by inline Vanilla JS with zero external dependencies.
* **Global Lifecycle Hooks:** `@before_all`, `@after_all`, `@before_group`, `@after_group` orchestrate DB seeding and auth. `ctx.variables` serialise across parallel `--workers`.

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

## 🔍 Explainable Heuristics  — `--explain`

ManulEngine does not use a "black box" AI model to pick DOM elements. Every resolution is a **pure mathematical function** of the DOM state, weighted heuristic signals, and your step text. With `--explain`, the engine prints the full scoring breakdown for every step — making the decision process fully auditable.

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
    │  #1  <button> "Login button"  → Total: 105445
    │       Text:          +50000
    │       Attributes:     +8889
    │       Semantics:     +40000
    │       Proximity:      +6556
    │       Cache:              +0
    │  #2  <a> "Login link"  → Total: 32000
    │       Text:          +25000
    │       Attributes:     +2000
    │       Semantics:      +3000
    │       Proximity:      +2000
    │       Cache:              +0
    │  #3  <span> "Login → Account"  → Total: 8500
    │       Text:           +5000
    │       Attributes:     +1000
    │       Semantics:      +1500
    │       Proximity:      +1000
    │       Cache:              +0
    └─ ✅ Decision: Selected "Login button" with score 105445
```

**Why this matters for QA engineers:**
- **Zero debug guesswork.** When a step targets the wrong element, `--explain` shows you *exactly* which signals pulled the score in each direction — text match, attribute match, semantic alignment, or DOM proximity.
- **Deterministic auditability.** Every score is a reproducible mathematical result. Same page, same step, same breakdown. Every time.
- **No AI required.** The explain output comes from the heuristic scorer, not an LLM. It works in heuristics-only mode (`"model": null`) — the recommended default.

Set `"explain_mode": true` in `manul_engine_configuration.json` to enable it permanently, or use the `MANUL_EXPLAIN=true` environment variable for CI pipelines.

### Visual Explainability in VS Code (Explain Step)

The companion VS Code extension surfaces `--explain` directly in the editor. Every actionable step line (Click, Fill, Select, Verify, etc.) in a `.hunt` file gets a clickable **🔍 Explain Heuristics** CodeLens above it. Click any lens — the extension runs the entire hunt file with `--explain` and streams the score breakdown into a dedicated **ManulEngine: Explain Heuristics** output channel, auto-focused so you see results immediately.

No more guessing why a test clicked the wrong element. The scoring math is one click away.

The CodeLens can be toggled off via `manulEngine.explainCodeLens` in VS Code settings. The `🔍` button also appears in the editor title bar for quick access.

---

## 🏛️ Beyond Testing: 4 Pillars of Automation

ManulEngine is not just a test runner — it is a **Universal Web Automation Runtime**. The same `.hunt` DSL, the same heuristics engine, and the same Playwright backend power four distinct automation pillars:

### 1. QA & E2E Testing

The core offering. Write plain-English test scenarios, use Python hooks for DB seeding and teardown, attach `@data:` files for data-driven runs, and generate interactive HTML reports. ManulEngine replaces fragile selector-based test suites with deterministic, human-readable scripts that survive UI refactors.

### 2. RPA (Robotic Process Automation)

Automate repetitive business tasks — logging into a CRM, downloading invoices, filling compliance forms, scraping vendor portals — without writing fragile Selenium code. A `.hunt` file is a self-contained automation script: `NAVIGATE`, `FILL`, `CLICK`, `EXTRACT`, `CALL PYTHON`. Schedule it with cron or a task runner and let the Manul do the work.

### 3. Synthetic Monitoring

Run `.hunt` scripts on a schedule to verify production health. A three-step checkout flow, an API-backed dashboard, a login gate — if it works in a hunt file, it works as a synthetic monitor. Pair with `--html-report` and `--screenshot on-fail` for instant incident forensics.

### 4. AI Agent Execution

The safest way to execute AI-generated browser actions. Instead of letting LLMs hallucinate raw Playwright calls, have them generate strict `.hunt` DSL — a constrained, validated instruction set. ManulEngine's deterministic engine executes the script safely, with built-in retries, self-healing, and screenshot capture. No prompt injection into the browser. No unbounded API calls. Full auditability.

---

## ✨ Key Features

### ⚡ Heuristics Engine — The Mathematical Core

Element resolution is driven entirely by the `DOMScorer` — a normalised `0.0–1.0` float scoring system across five weighted channels:

| Channel | Weight | Purpose |
|---|---|---|
| `cache` | 2.0 | Reuse previously resolved elements |
| `semantics` | 0.60 | Element-type alignment, role synergy |
| `text` | 0.45 | Text, aria-label, placeholder, data-qa matching |
| `attributes` | 0.25 | html_id, dev naming conventions |
| `proximity` | 0.10 | DOM depth-based form context |

Final score = weighted sum × penalty multiplier × `SCALE` (177,778). An exact `data-qa` match scores +1.0 text (~80k scaled) — the single strongest signal. Disabled elements are crushed by a ×0.0 multiplier. No guesswork, no randomness.

### 🌳 TreeWalker — Zero-Waste DOM Traversal

`SNAPSHOT_JS` walks the DOM with a native `document.createTreeWalker()` and a `PRUNE` set that rejects entire irrelevant subtrees (`SCRIPT`, `STYLE`, `SVG`, `NOSCRIPT`, `TEMPLATE`, etc.) in a single hop. Visibility is checked via the zero-layout-thrash `checkVisibility()` API. No `querySelectorAll`. No `getComputedStyle` in the hot loop.

### 🧠 20+ Accessibility Signals

Manul scores elements using `aria-label`, `placeholder`, `name`, `data-qa`, `html_id`, semantic `input type`, contextual section headings, and more. Modern SPAs (React, Vue, Angular) and complex design systems (Wikipedia Vector 2022 / Codex) work without any tuning — accessibility attributes are first-class identifiers.

### 🛡️ Ironclad JS Fallbacks

Modern websites hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. Manul uses Playwright with `force=True` plus retries and self-healing; for Shadow DOM elements it falls back to direct JS helpers to keep execution moving.

### 🌑 Shadow DOM & iframe Awareness

The DOM snapshotter recursively walks shadow roots via `TreeWalker` and scans same-origin iframes by iterating `page.frames`. Each element carries a `frame_index` that routes all downstream actions to the correct Playwright `Frame`. Cross-origin frames are silently skipped.

### 🗂️ Persistent Controls Cache

Successful element resolutions are stored per-site and reused on subsequent runs — making repeated test flows dramatically faster.

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

```bash
manul tests/ --html-report                          # report saved to reports/manul_report.html
manul tests/ --screenshot always --html-report      # embed a screenshot for every step
manul tests/ --screenshot on-fail --html-report     # screenshots only on failures
```

All artifacts (logs, reports) are saved to the `reports/` directory — your workspace stays clean.

> **Note:** Per-step details (accordion + embedded screenshots) require `--workers 1` (the default). When `--workers > 1`, the report aggregates per-hunt results only.

### 📋 STEP Groups — Manual Test Cases Meet Automation

ManulEngine bridges the gap between manual QA test cases ("Steps & Expected Results") and automation. Use `STEP N: Description` headers to mirror the structure of your manual test plan directly in the `.hunt` file. The engine renders each group as an accordion section in the HTML report — with its own pass/fail badge and action count — so stakeholders can read results without decoding raw step indices.

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

`STEP` headers produce zero browser actions — they are pure metadata. The `STEP N:` tag is optional but highly recommended: it maps 1:1 to manual QA test cases and gives the HTML report its accordion structure. Action lines that follow must be written as **plain text without leading numbers** — never prefix with `1.`, `2.`, etc.

---

## 🎛️ Custom Controls — Escape Hatch for Complex UI

Some UI elements defeat general-purpose heuristics entirely: React virtual tables, canvas-based date-pickers, WebGL widgets, drag-to-sort lists. **Custom Controls** let you write plain English in the hunt file while an SDET handles the underlying Playwright logic in Python.

* **For Manual QA / Testers:** Keep writing plain English steps. If a step targets a Custom Control, the engine routes it to a Python handler automatically. The `.hunt` file stays readable and unchanged.
* **For SDETs / Developers:** Register a handler with a one-line decorator tied to a page name from `pages.json`. Use any Playwright API inside — no heuristics, no AI involvement.

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

> **See it in action:** `controls/demo_custom.py` is a fully-working reference handler for a React Datepicker (with month navigation). `tests/demo_controls.hunt` is the companion hunt file — run it as-is to see the routing in action.

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

Declare all test data at the top of your `.hunt` file with `@var:`. Values are injected into the engine’s memory before step 1 runs and can be referenced anywhere via `{placeholder}` — keeping your test logic clean and your data in one place.

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

Both `@var: {key} = value` and `@var: key = value` are accepted. Variables declared with `@var:` work identically to those created by `EXTRACT` and `CALL PYTHON ... into {var}`.

---

## 🏷️ Tags — Run Exactly What You Need

Tag any `.hunt` file and cherry-pick which tests to run — no directory juggling required.

```text
@tags: smoke, auth, regression

NAVIGATE to https://example.com/login
DONE.
```

```bash
manul tests/ --tags smoke               # run only 'smoke'-tagged files
manul tests/ --tags smoke,critical      # OR logic — either tag matches
```

Files without `@tags:` are excluded when `--tags` is active. Zero config, zero complexity.

---

## ⚡ Lightning-Fast Preconditions with Python Hooks

Stop wasting hours on brittle UI-based preconditions. With `[SETUP]` and `[TEARDOWN]` hooks you can inject test data directly into your database or call an API in pure Python — keeping your `.hunt` files crystal clear and your test runs dramatically faster.

```text
@var: {email}    = admin@example.com
@var: {password} = secret

[SETUP]
CALL PYTHON db_helpers.seed_admin_user
[END SETUP]

STEP 1: Login
NAVIGATE to https://myapp.com/login
Fill 'Email' field with '{email}'
Fill 'Password' field with '{password}'
Click the 'Sign In' button
VERIFY that 'Dashboard' is present.

[TEARDOWN]
CALL PYTHON db_helpers.clean_database
[END TEARDOWN]
```

Hooks run **outside the browser**: `[SETUP]` fires before the browser opens; `[TEARDOWN]` fires in a `finally` block — always — regardless of whether the test passed or failed. If setup fails, the mission is skipped and teardown is not called (there's nothing to clean up).

| Block | When it runs | Abort behaviour |
|---|---|---|
| `[SETUP]` | Before the browser launches | Failure skips mission + teardown |
| `[TEARDOWN]` | After the mission (pass or fail) | Failure is logged, does not override mission result |

The helper module is resolved relative to the `.hunt` file's directory first, then the CWD, then standard `sys.path` — no configuration needed.

### 🐍 Inline Python Calls

Need to fetch an OTP from the database mid-test? Or trigger a backend job before clicking "Refresh"? Call Python functions directly as action lines right in the middle of your UI flow.

```text
STEP 2: OTP verification
Fill 'Email' field with 'test@manul.com'
Click the 'Send OTP' button
CALL PYTHON api_helpers.fetch_and_set_otp
Fill 'OTP' field with '{otp}'
Click the 'Login' button
VERIFY that 'Dashboard' is present.
```

The same module resolution rules apply as for `[SETUP]`/`[TEARDOWN]`: hunt file directory → CWD → `sys.path`. Functions must be synchronous. If the call fails, the mission stops immediately — just like any other failed step. No special syntax or block wrapping required.

#### Passing arguments to Python functions

`CALL PYTHON` now accepts optional positional arguments — static strings, unquoted tokens, and `{var}` placeholders resolved from the engine’s runtime memory:

```text
CALL PYTHON helpers.multiply "6" "7" into {product}
CALL PYTHON api.send_email "{user_email}" "Welcome!"
CALL PYTHON utils.concat 'a' 'b' 'c' into {result}
```

Arguments are tokenised with `shlex.split()` — single-quoted, double-quoted, and unquoted tokens are all accepted. `{var}` placeholders inside arguments are resolved from the engine’s runtime memory; unresolved placeholders are kept as-is.

#### Capturing return values with `into {var}`

Append `into {var_name}` (or `to {var_name}`) to bind the function’s return value directly into an in-mission variable:

```text
CALL PYTHON api_helpers.fetch_otp into {dynamic_otp}
Fill 'Security Code' field with '{dynamic_otp}'
```

Combine arguments and capture in one line:

```text
CALL PYTHON api_helpers.fetch_otp "{email}" into {otp}
Fill 'OTP' field with '{otp}'
```

The raw return value is converted to a string (`str(return_value)`) and stored under the variable name. It is then available for `{placeholder}` substitution in every subsequent step, exactly like variables populated by `EXTRACT` or `@var:`.
---
## 🌐 Global Lifecycle Hooks — Enterprise-Scale Test Orchestration

For multi-file test suites that need shared state — a global auth token, a seeded database, a per-run environment flag — create a `manul_hooks.py` file in the same directory as your `.hunt` files. The engine discovers and loads it automatically.

```python
# tests/manul_hooks.py
from manul_engine import before_all, after_all, before_group, after_group, GlobalContext

@before_all
def global_setup(ctx: GlobalContext) -> None:
    """Runs once before any hunt file starts."""
    ctx.variables["BASE_URL"] = "https://staging.example.com"
    ctx.variables["API_TOKEN"] = fetch_token_from_vault()

@after_all
def global_teardown(ctx: GlobalContext) -> None:
    """Always runs after all hunt files finish, pass or fail."""
    db.rollback_all_test_data()

@before_group(tag="smoke")
def seed_smoke(ctx: GlobalContext) -> None:
    """Runs before every hunt file tagged @tags: smoke."""
    ctx.variables["ORDER_ID"] = db.create_temp_order()

@after_group(tag="smoke")
def clean_smoke(ctx: GlobalContext) -> None:
    ctx.variables.pop("ORDER_ID", None)
```

Variables written to `ctx.variables` are injected into every matching mission as `{placeholder}`-ready data — identical to `@var:` declarations, but shared across all hunt files:

```text
# tests/checkout.hunt
@tags: smoke

STEP 1: Checkout
NAVIGATE to '{BASE_URL}/checkout'
Fill 'API Token' field with '{API_TOKEN}'
DONE.
```

### Hook execution order and failure semantics

| Hook | When it fires | Failure behaviour |
|---|---|---|
| `@before_all` | Once before the first hunt file | Aborts the entire suite; `@after_all` still runs |
| `@after_all` | Once after all hunts finish | Always runs; failure logged, does not override suite result |
| `@before_group(tag=)` | Before each hunt file whose `@tags:` contains `tag` | Failure skips that mission; `@after_group` still runs for it |
| `@after_group(tag=)` | After each matching mission (pass or fail) | Always runs; failure logged, does not override mission result |

### Parallel workers

When running with `--workers N`, `@before_all` runs in the orchestrator process and its `ctx.variables` are serialised as JSON into the `MANUL_GLOBAL_VARS` environment variable before worker subprocesses are spawned. Each worker deserialises them at startup — `{placeholder}` substitution works identically in parallel and sequential modes.

> **Rule for adding pre-test setup:** If a test scenario requires a database record, a seeded user, a valid auth token, or any per-suite environment state, **always** use `@before_all` or `@before_group` in `manul_hooks.py`. Never add setup steps to individual `.hunt` files — they are slow, brittle, and couple production UI flows to test infrastructure.

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

# Run only files tagged 'smoke' OR 'critical'
manul my_tests/ --tags smoke,critical

# Retry failed hunts up to 2 times
manul my_tests/ --retries 2

# Generate a standalone HTML report (saved to reports/manul_report.html)
manul my_tests/ --html-report

# Screenshots on failure + HTML report + retries (the full CI combo)
manul my_tests/ --retries 2 --screenshot on-fail --html-report

# Screenshots for every step (detailed forensic report)
manul my_tests/ --screenshot always --html-report

# Interactive debug mode (terminal) — pause before every step, confirm in terminal
manul --debug my_tests/smoke.hunt

# VS Code: place red-dot gutter breakpoints in any .hunt file, then run the Debug profile
# in Test Explorer — ⏭ Next Step / ▶ Continue All / ■ Stop (Stop dismisses QuickPick cleanly)

# Smart Page Scanner — scan a URL and generate a draft hunt file
manul scan https://example.com                    # outputs to tests/draft.hunt (tests_home)
manul scan https://example.com tests/my.hunt      # explicit output file
manul scan https://example.com --headless         # headless scan
```

> **VS Code:** The Step Builder sidebar includes a **Live Page Scanner** — paste a URL and click **🔍 Run Scan** to invoke the scanner without opening a terminal. The generated `draft.hunt` opens automatically in the editor.

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

Run the daemon:

```bash
# Start the daemon — runs all scheduled .hunt files in the directory
manul daemon tests/ --headless

# With screenshot capture and a specific browser
manul daemon tests/ --headless --browser firefox --screenshot on-fail
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

The daemon is a long-running process — each scheduled hunt file gets its own async task. If one run fails, the daemon logs the error and continues to the next scheduled execution. Stop with `Ctrl+C`.

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

## 📜 Hunt File Format

Hunt files are plain-text test scenarios with a `.hunt` extension.

### Headers (optional)

```text
@context: Strategic context passed to the LLM planner
@title: short-tag
@tags: smoke, auth, regression
```

`@tags:` declares a comma-separated list of arbitrary tag names.  Use `manul --tags smoke tests/` to run only files whose `@tags:` header contains at least one matching tag.  Untagged files are excluded when `--tags` is active.

### Comments

Lines starting with `#` are ignored.

### System Keywords

| Keyword | Description |
|---|---|
| `NAVIGATE to [URL]` | Load a URL and wait for DOM settlement |
| `OPEN APP` | Attach to an Electron/Desktop app's default window (use instead of `NAVIGATE` when `executable_path` is set) |
| `WAIT [seconds]` | Hard sleep |
| `PRESS ENTER` | Press Enter on the currently focused element (submit forms after filling a field) |
| `PRESS [Key]` | Press any key or combination globally (e.g. `PRESS Escape`, `PRESS Control+A`) |
| `PRESS [Key] on [Target]` | Press a key on a specific element (e.g. `PRESS ArrowDown on 'Search Input'`) |
| `RIGHT CLICK [Target]` | Right-click an element to open a context menu |
| `UPLOAD 'File' to 'Target'` | Upload a file to a file input element (both must be quoted; path relative to `.hunt` file or CWD) |
| `SCROLL DOWN` | Scroll the main page down one viewport |
| `EXTRACT [target] into {var}` | Extract text into a memory variable |
| `VERIFY that [target] is present` | Assert text/element is visible |
| `VERIFY that [target] is NOT present` | Assert absence |
| `VERIFY that [target] is DISABLED` | Assert element is disabled |
| `VERIFY that [target] is ENABLED` | Assert element is enabled / interactable |
| `VERIFY that [target] is checked` | Assert checkbox state |
| `SCAN PAGE` | Scan the current page for interactive elements and print a draft `.hunt` to the console |
| `SCAN PAGE into {filename}` | Same, and also write the draft to `{filename}` (default: `tests_home/draft.hunt`) |
| `DONE.` | End the mission |

### Python Hooks & Inline Python Calls

Optional `[SETUP]`/`[TEARDOWN]` blocks (placed at the top/bottom of the file) and inline `CALL PYTHON` steps (used anywhere in the numbered sequence) all share the same execution model.

```text
[SETUP]
# Lines starting with # are ignored.
CALL PYTHON <module_path>.<function_name>
[END SETUP]

STEP 1: Authenticate
NAVIGATE to https://myapp.com
CALL PYTHON api_helpers.fetch_otp into {dynamic_otp}
Fill 'Security Code' with '{dynamic_otp}'
VERIFY that 'Dashboard' is present.

[TEARDOWN]
CALL PYTHON <module_path>.<function_name>
[END TEARDOWN]
```

Rules:
- Functions must be **synchronous** (async functions are explicitly rejected).
- A single `[SETUP]`/`[TEARDOWN]` block may contain multiple `CALL PYTHON` lines; they run sequentially — first failure stops the block.
- An inline `CALL PYTHON` step that fails stops the mission immediately, just like any other failed step.
- Append `into {var_name}` (or `to {var_name}`) to a `CALL PYTHON` step to bind the function's return value into a variable: `CALL PYTHON api.fetch_otp into {otp}`. The value is converted to a string and available for `{placeholder}` substitution in all subsequent steps.
- Pass positional arguments after the dotted function name: `CALL PYTHON helpers.multiply "6" "7" into {product}`. Arguments are tokenised with `shlex.split()` and `{var}` placeholders are resolved from runtime memory.
- The module is searched in: hunt file directory → CWD → `sys.path`. No import configuration needed.

### Interaction Steps

```text
# Clicking
Click the 'Login' button
DOUBLE CLICK the 'Image'

# Typing
Fill 'Email' field with 'test@example.com'
Type 'hello' into the 'Search' field

# Dropdowns
Select 'Option A' from the 'Language' dropdown

# Checkboxes / Radios
Check the checkbox for 'Terms'
Uncheck the checkbox for 'Newsletter'
Click the radio button for 'Male'

# Hover & Drag
HOVER over the 'Menu'
Drag the element "Item" and drop it into "Box"

# Optional steps (non-blocking)
Click 'Close Ad' if exists
```

### Variables

```text
EXTRACT the price of 'Laptop' into {price}
VERIFY that '{price}' is present.
```

### Variable Declaration

Declare static test data at the top of the file using `@var:`. These values are pre-populated into the runtime memory before any step runs and can be interpolated anywhere a variable placeholder `{name}` is accepted.

```text
@var: {email}    = admin@example.com
@var: {password} = secret123

STEP 1: Login
NAVIGATE to https://myapp.com/login
Fill 'Email' with '{email}'
Fill 'Password' with '{password}'
Click the 'Login' button
```

The surrounding `{}` braces in the declaration are optional — `@var: email = ...` and `@var: {email} = ...` are equivalent. Values are stripped of leading/trailing whitespace. Declared variables behave exactly like variables populated by `EXTRACT` and can be used interchangeably with them in downstream steps.

---

## 🤖 Generate Hunt Files with AI Prompts

The `prompts/` directory contains ready-to-use LLM prompt templates that let you generate complete `.hunt` test files automatically — no manual step writing needed.

| Prompt file | When to use |
|---|---|
| `prompts/html_to_hunt.md` | Paste a page's HTML source → get complete hunt steps |
| `prompts/description_to_hunt.md` | Describe a page or flow in plain text → get hunt steps |

### Quick example — GitHub Copilot Chat

1. Open Copilot Chat (`Ctrl+Alt+I`).
2. Click the paperclip icon → attach `prompts/html_to_hunt.md`.
3. Paste your HTML in the chat and press Enter.
4. Save the response as `tests/<name>.hunt` and run `manul tests/<name>.hunt`.

See [`prompts/README.md`](prompts/README.md) for usage with ChatGPT, Claude, OpenAI/Anthropic API, and local Ollama.

---

## ⚙️ Configuration

Create `manul_engine_configuration.json` in your project root — all settings are optional:

```json
{
  "model": "qwen2.5:0.5b",
  "headless": false,
  "browser": "chromium",
  "browser_args": [],
  "timeout": 5000,
  "nav_timeout": 30000,
  "ai_always": false,
  "ai_policy": "prior",
  "ai_threshold": null,
  "controls_cache_enabled": true,
  "controls_cache_dir": "cache",
  "semantic_cache_enabled": true,
  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "workers": 1,
  "tests_home": "tests",
  "auto_annotate": false,

  "channel": null,
  "executable_path": null,

  "retries": 0,
  "screenshot": "on-fail",
  "html_report": false
}
```

> Set `"model": null` (or omit it) to disable AI entirely and run in **heuristics-only mode**.

Environment variables (`MANUL_*`) always override JSON values — useful for CI/CD:

```bash
export MANUL_HEADLESS=true
export MANUL_AI_THRESHOLD=0
export MANUL_MODEL=qwen2.5:0.5b
export MANUL_BROWSER=firefox
export MANUL_BROWSER_ARGS="--disable-gpu,--lang=uk"
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
| `semantic_cache_enabled` | `true` | In-session semantic cache; remembers resolved elements within a single run (+200,000 score boost) |
| `timeout` | `5000` | Default action timeout (ms) |
| `nav_timeout` | `30000` | Navigation timeout (ms) |
| `log_name_maxlen` | `0` | Truncate element names in logs (0 = no limit) |
| `log_thought_maxlen` | `0` | Truncate LLM thoughts in logs (0 = no limit) |
| `workers` | `1` | Number of hunt files to run concurrently (each gets its own browser) |
| `tests_home` | `"tests"` | Default directory for new hunt files and `SCAN PAGE` / `manul scan` output |
| `auto_annotate` | `false` | Automatically insert `# 📍 Auto-Nav:` comments in hunt files whenever the browser URL changes (not only on `NAVIGATE` steps). Page names are resolved from `pages.json`; unmapped URLs fall back to the full URL |
| `channel` | `null` | Playwright browser channel — use an installed browser instead of the bundled one. E.g. `"chrome"`, `"chrome-beta"`, `"msedge"`. Overridable via `MANUL_CHANNEL` |
| `executable_path` | `null` | Absolute path to a custom browser executable (e.g. Electron). Overridable via `MANUL_EXECUTABLE_PATH` |
| `retries` | `0` | Number of times to retry a failed hunt file before marking it as failed (0 = no retries) |
| `screenshot` | `"on-fail"` | Screenshot capture mode: `"none"` (no screenshots), `"on-fail"` (default — failed steps only), `"always"` (every step) |
| `html_report` | `false` | Generate a self-contained HTML report after the run (`reports/manul_report.html`) |

---

## 📋 Available Commands

| Category | Command Syntax |
|---|---|
| **Navigation** | `NAVIGATE to [URL]`, `OPEN APP` |
| **Input** | `Fill [Field] with [Text]`, `Type [Text] into [Field]` |
| **Click** | `Click [Element]`, `DOUBLE CLICK [Element]`, `RIGHT CLICK [Element]` |
| **Selection** | `Select [Option] from [Dropdown]`, `Check [Checkbox]`, `Uncheck [Checkbox]` |
| **Mouse Action** | `HOVER over [Element]`, `Drag [Element] and drop it into [Target]` |
| **Data Extraction** | `EXTRACT [Target] into {variable_name}` |
| **Verification** | `VERIFY that [Text] is present/absent`, `VERIFY that [Element] is checked/disabled/enabled` |
| **Page Scanner** | `SCAN PAGE`, `SCAN PAGE into {filename}` |
| **Debug** | `DEBUG` / `PAUSE` — pause execution at that step (use with `--debug` or VS Code gutter breakpoints) |
| **Keyboard** | `PRESS ENTER`, `PRESS [Key]`, `PRESS [Key] on [Element]` |
| **File Upload** | `UPLOAD 'File' to 'Element'` |
| **Variables** | `SET {variable} = value`, `@var: {name} = value` (header declaration) |
| **Flow Control** | `WAIT [seconds]`, `SCROLL DOWN` |
| **Finish** | `DONE.` |

> Append `if exists` or `optional` to any step (outside quoted text) to make it non-blocking,
> e.g. `Click 'Close Ad' if exists`

---

## 🏋️ Benchmarks & Proof

ManulEngine ships with a dedicated benchmark suite (`benchmarks/`) that mathematically proves its heuristic engine outperforms rigid Playwright locators on adversarial UI patterns. The suite runs 12 tasks across 4 HTML fixtures designed to simulate the worst real-world DOM scenarios:

| Fixture | What it tests |
|---|---|
| `dynamic_ids.html` | Randomised `id` and `class` attributes on every page load |
| `overlapping.html` | Hidden traps, zero-pixel elements, offscreen honeypots, duplicate buttons |
| `nested_tables.html` | Deeply nested `<table>` layouts without IDs or ARIA labels |
| `custom_dropdown.html` | `<div>`-based custom dropdown with ARIA roles alongside a native `<select>` |

Each task is executed twice: once with a raw Playwright locator (the baseline), and once with ManulEngine's `DOMScorer` heuristics. The results table shows resolution success and timing for both approaches.

```bash
# Run the benchmark suite
python benchmarks/run_benchmarks.py
```

Example output:

```
ManulEngine vs Raw Playwright — Benchmark Results
────────────────────────────────────────────────────────────────
dynamic_ids.html       Fill 'Username' field       PW: OK  14ms   Manul: OK  10ms
dynamic_ids.html       Click the 'Log In' button   PW: OK  12ms   Manul: OK   9ms
overlapping.html       Click 'Submit Order' button  PW: OK  16ms   Manul: OK  11ms
...
TOTAL                  12 tasks                12/12 avg 20ms  10/12 avg 10ms
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
- Persistent controls cache hit/miss cycles

---

**Version:** 0.0.9.4 · **Status:** Hunting...
