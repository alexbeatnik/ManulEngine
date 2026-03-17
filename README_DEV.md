
---

# 😼 ManulEngine v0.0.9.5 — Deterministic Web & Desktop Automation Runtime

**ManulEngine — Deterministic Web & Desktop Automation Runtime.**
Write deterministic automation scripts in plain-English Hunt DSL. Run E2E tests, RPA workflows, synthetic monitoring, and AI-agent actions — powered by blazing-fast JS heuristics and Playwright. Automate Chromium, Firefox, WebKit — and desktop apps via Electron.

No CSS selectors. No XPath fragility. No cloud API bills.
ManulEngine is an interpreter for the `.hunt` DSL — a Playwright-backed runtime that resolves DOM elements with a mathematically sound `DOMScorer` (normalised 0.0–1.0 float scoring across 20+ signals) and a native JavaScript `TreeWalker`. Deterministic, reproducible, and fast enough to run anywhere.

> The Manul goes hunting and never returns without its prey.

> **Zero AI required. Zero cloud dependency. Zero flakiness by design.**
> Playwright speed. Heuristic precision. Optional local micro-LLMs via Ollama — only when you need them.

---

## 📁 Project Structure

```text
ManulEngine/
├── manul.py                          Dev CLI entry point (intercepts `test` subcommand)
├── manul_engine_configuration.json   Project configuration (JSON)
│   ├── pyproject.toml                        Build config — package: manul-engine 0.0.9.5
├── requirements.txt                  Python dependencies
├── manul_engine/                     Core automation engine package
│   ├── __init__.py                   Public API — exports ManulEngine
│   ├── cli.py                        Installed CLI entry point (`manul` command + `manul scan` + `manul record` + `manul daemon` subcommands)
│   ├── lifecycle.py                  Global Lifecycle Hook Registry (@before_all, @after_all, @before_group, @after_group)
│   ├── hooks.py                      [SETUP] / [TEARDOWN] hook parser and executor
│   ├── controls.py                   Custom Controls registry (@custom_control, get_custom_control, load_custom_controls)
│   ├── recorder.py                   Semantic Test Recorder — JS injection, Python bridge, DSL generator
│   ├── scheduler.py                  Built-in Scheduler — parse_schedule(), Schedule dataclass, daemon_main()
│   ├── _test_runner.py               Dev-only synthetic test runner (not in public CLI)
│   ├── prompts.py                    JSON config loader, thresholds, LLM prompts
│   ├── helpers.py                    Pure utility functions, env helpers, timing constants
│   ├── js_scripts.py                 All JavaScript injected into the browser (incl. SCAN_JS)
│   ├── scoring.py                    Heuristic element-scoring algorithm (20+ rules)
│   ├── scanner.py                    Smart Page Scanner: scan_page(), build_hunt(), scan_main()
│   ├── core.py                       ManulEngine class (LLM, resolution, mission runner)
│   ├── cache.py                      Persistent per-site controls cache mixin
│   ├── actions.py                    Action execution mixin (click, type, select, hover, drag, scan_page)
│   ├── reporting.py                  StepResult, MissionResult, RunSummary dataclasses
│   ├── reporter.py                   Interactive HTML report generator (dark theme, control panel, tag chips, base64 screenshots)
│   ├── variables.py                  ScopedVariables — 4-level variable hierarchy (row, step, mission, global)
│   └── test/
│       ├── test_00_engine.py         Engine micro-suite (synthetic DOM via local HTML)
│       ├── test_01_ecommerce.py      Scenario pack: ecommerce
│       ├── ...
│       ├── test_12_ai_modes.py       Unit: Always-AI/strict/rejection
│       ├── test_13_controls_cache.py Unit: persistent controls cache
│       ├── test_14_qa_classics.py    Unit: legacy HTML patterns, tables, fieldsets
│       ├── test_15_facebook_final_boss.py
│       ├── test_16_hooks.py          Unit: [SETUP]/[TEARDOWN] hooks (41 assertions, no browser)
│       ├── test_17_frontend_hell.py  Unit: frontend anti-patterns (overlays, z-index traps, React portals)
│       ├── test_18_disambiguation.py Unit: ambiguous element targeting
│       ├── test_19_custom_controls.py Unit: Custom Controls registry + engine interception (19 assertions, no browser)
│       ├── test_20_variables.py      Unit: @var: static variable declaration (17 assertions, no browser)
│       ├── test_21_dynamic_vars.py   Unit: CALL PYTHON ... into {var} dynamic variable capture
│       ├── test_22_tags.py           Unit: @tags: / --tags CLI filter (20 assertions, no browser)
│       ├── test_23_advanced_interactions.py  Unit: PRESS/RIGHT CLICK/UPLOAD (48 assertions, no browser)
│       ├── test_24_reporting.py      Unit: StepResult/MissionResult/RunSummary dataclasses (45 assertions)
│       ├── test_25_reporter.py       Unit: HTML report generator (65 assertions, no browser)
│       ├── test_26_wikipedia_search.py Unit: name_attr heuristic scoring (20 assertions, no browser)
│       ├── test_27_lifecycle_hooks.py  Unit: Global Lifecycle Hook system (57 assertions, no browser)
│       ├── test_28_logical_steps.py    Unit: Logical STEP ordering and parser (48 assertions, no browser)
│       ├── test_29_iframe_routing.py   Synthetic: Cross-frame element resolution (25 assertions)
│       ├── test_30_heuristic_weights.py Synthetic+Unit: DOMScorer priority hierarchy (32 assertions)
│       ├── test_31_visibility_treewalker.py Synthetic+Unit: TreeWalker PRUNE/checkVisibility (20 assertions)
│       ├── test_32_verify_enabled.py Synthetic: VERIFY ENABLED/DISABLED state verification (20 assertions)
│       ├── test_33_call_python_args.py Unit: CALL PYTHON with positional arguments (44 assertions, no browser)
│       ├── test_34_verify_checked.py Synthetic: VERIFY checked/NOT checked (20 assertions)
│       ├── test_35_scanner.py       Synthetic+Unit: Smart Page Scanner build_hunt() (44 assertions)
│       ├── test_36_scoring_math.py   Unit: exact numerical scoring validation (29 assertions, no browser)
│       ├── test_37_enterprise_dsl.py Unit: Enterprise DSL — @data:, MOCK, VERIFY VISUAL/SOFTLY, reporter warnings (68 assertions, no browser)
│       ├── test_38_set_and_indent.py Unit: SET command & indentation robustness (v0.0.9.2)
│       ├── test_39_open_app.py       Unit: OPEN APP command — classify_step, RE_SYSTEM_STEP, _handle_open_app (32 assertions, no browser)
│       ├── test_40_self_healing_cache.py Unit: Self-Healing Controls Cache — stale detection, HEALED logging, cache auto-update (16 assertions)
│       ├── test_41_recorder.py      Unit: Semantic Test Recorder — JS bridge, DSL generator, step aggregation (no browser)
│       └── test_42_scheduler.py     Unit: Built-in Scheduler — parse_schedule, next_run_delay, ParsedHunt integration (51 assertions, no browser)
├── controls/                         User-owned custom Python handlers (auto-loaded at engine startup)
│   └── demo_custom.py                Reference implementation: React Datepicker handler with month navigation
├── tests/                            Integration hunt tests (real websites)
│   ├── demo_controls.hunt            Demo: Custom Controls workflow (companion to controls/demo_custom.py)
│   ├── demo_login.hunt               Demo: login with @var: static variables
│   ├── demo_variables.hunt           Demo: @var: + CALL PYTHON into {var} combined
│   ├── demoqa.hunt
│   ├── mega.hunt
│   ├── rahul.hunt
│   ├── saucedemo.hunt
│   └── wikipedia.hunt
├── reports/                          Generated logs and HTML reports (auto-created, .gitignored)
├── benchmarks/                       Adversarial benchmark suite (12 tasks, 4 HTML fixtures)
│   └── run_benchmarks.py            Benchmark runner: ManulEngine vs raw Playwright
├── prompts/                          LLM prompt templates for hunt file generation
│   ├── README.md                     Usage guide (Copilot, ChatGPT, Claude, Ollama)
│   ├── html_to_hunt.md               Prompt: HTML page → hunt steps
│   └── description_to_hunt.md        Prompt: plain-text description → hunt steps
└── vscode-extension/                 VS Code extension (language support + UI)
    └── package.json                  Extension manifest (v0.0.95)
    ├── src/
    │   ├── extension.ts              Activation, command registration, formatter registration
    │   ├── huntRunner.ts             Spawns manul CLI; cwd = workspace root
    │   ├── huntTestController.ts     VS Code Test Explorer integration
    │   ├── configPanel.ts            Webview sidebar: config editor + Ollama discovery
    │   ├── cacheTreeProvider.ts      Sidebar tree: controls cache browser
    │   ├── stepBuilderPanel.ts       Step Builder sidebar (incl. Live Page Scanner UI + Scan Page button)
    │   ├── schedulerPanel.ts         Scheduler Dashboard webview panel (daemon management UI)
    │   ├── formatter.ts              DocumentFormattingEditProvider for .hunt files (4-space action indent)
    │   └── debugControlPanel.ts      Singleton QuickPick overlay for interactive debug stepping
    └── syntaxes/hunt.tmLanguage.json Hunt file syntax grammar
```

---

## 🏛️ Architecture — ManulEngine as a Runtime

ManulEngine is not a test library bolted onto Playwright. It is a **runtime** — an interpreter for the `.hunt` DSL that sits between human-authored (or AI-generated) automation scripts and the browser.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  .hunt DSL             (human-authored or AI-generated)    │
│  QA tests · RPA scripts · synthetic monitors · agent tasks  │
└─────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Parser (cli.py)                                             │
│  parse_hunt_file() → ParsedHunt NamedTuple                   │
│  Extracts: @context, @title, @tags, @data, @var,             │
│  [SETUP]/[TEARDOWN], step lines                               │
└─────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Execution Engine (core.py → run_mission)                     │
│  DOMScorer (scoring.py) · TreeWalker (js_scripts.py)          │
│  Element resolution → Action dispatch → Self-healing          │
└───────────┬─────────────────────┬─────────────────────┬──────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ Custom Controls │  │ Python Hooks       │  │ Persistent Cache  │
│ (controls.py)   │  │ [SETUP]/[TEARDOWN] │  │ (cache.py)        │
│ @custom_control  │  │ CALL PYTHON        │  │ Per-site storage  │
└────────────────┘  │ @before_all        │  └───────────────────┘
                    └───────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Playwright (async)                                          │
│  Chromium · Firefox · WebKit · Electron                       │
└──────────────────────────────────────────────────────────────────────────┘
```

This architecture is what makes ManulEngine a **true runtime** rather than just a test library. The `.hunt` DSL is the instruction set. The parser and engine are the interpreter. Playwright is the I/O layer. Users write scripts — QA tests, RPA workflows, synthetic monitors, or AI-agent actions — in the same deterministic DSL, and the runtime executes them identically.

---

## 🚀 What's New in v0.0.9.5 — Explain Mode

* **Run with Explain Mode (VS Code Button):** New `manul.runExplain` command with `$(output)` icon in the editor title bar for `.hunt` files. One click runs the hunt file with `--explain --workers 1` and streams the full heuristic scoring breakdown to the **ManulEngine: Explain Heuristics** output channel. Available alongside the existing CodeLens-based `manul.explainHuntFile`.

### Previous highlights (v0.0.9.4)

## 🚀 What's New in v0.0.9.4 — Hardening & Transparency

* **Explainable Heuristics (`--explain`):** `DOMScorer` can now emit a per-candidate channel breakdown (text, attributes, semantics, proximity, cache) alongside the final score. Enabled via `manul --explain tests/` or `MANUL_EXPLAIN=1`. The top-3 candidates for each resolution step are printed to the console with full score-channel details, making it trivial to audit why a particular element was chosen — or wasn't.
* **Strict Variable Scoping (`ScopedVariables`):** The runtime memory system (`self.memory`) is replaced by a `ScopedVariables` 4-level hierarchy (Row → Step → Mission → Global). `@data:` row values are injected at `row` scope and auto-cleared between iterations; `EXTRACT` and `CALL PYTHON ... into {var}` capture at `step` scope; `@var:` declarations live at `mission` scope; lifecycle hooks (`@before_all`) populate `global` scope. Zero state leakage between data-driven iterations.
* **Benchmark Suite (`benchmarks/`):** 12 adversarial tasks across 4 HTML fixtures (`dynamic_ids`, `overlapping`, `nested_tables`, `custom_dropdown`) comparing ManulEngine heuristic resolution against raw Playwright locators. Run with `python benchmarks/run_benchmarks.py`.

### Previous highlights (v0.0.9.3)

## 🚀 What's New in v0.0.9.3 — The Scheduler Update

* **Built-in Scheduler (`@schedule:` + `manul daemon`):** `parse_hunt_file()` extracts the new `@schedule:` header into the 10th field of `ParsedHunt`. `manul_engine/scheduler.py` implements `parse_schedule()` (6 regex patterns: interval N units, unit shorthands, daily at HH:MM, every weekday, every weekday at HH:MM) returning a frozen `Schedule` dataclass, plus `next_run_delay()` and `_seconds_until_time/weekday()` helpers. `daemon_main(args)` is the CLI entry point: discovers `*.hunt` files with `@schedule:`, launches one `asyncio.Task` per file in an infinite sleep→run→log loop, and runs forever. No external dependencies (no APScheduler, no cron). The `manul daemon <directory>` subcommand is routed in `cli.py` alongside `scan` and `record`.
* **Advanced Scheduler Dashboard (VS Code Extension):** `schedulerPanel.ts` — a `WebviewPanel`-based Visual RPA Manager. `findAllHunts()` scans workspace for **all** `.hunt` files (reads first 20 lines per file, early-exits on step lines), returning both scheduled and unscheduled entries. HTML renders a **search bar** (filters by filename), **Scheduled Tasks** / **Unscheduled Tasks** split sections, per-file schedule editor (preset `<select>` combobox + custom text input + Apply button), status dot (green when running, grey when stopped), and Start/Stop/Refresh controls. `mutateScheduleHeader()` uses `vscode.WorkspaceEdit` to inject, replace, or remove `@schedule:` lines in `.hunt` files. The `updateSchedule` message handler bridges the webview UI to the file mutation logic. Start spawns `manul daemon <tests_home> --headless` in a `"Manul Daemon"` terminal; Stop disposes it. Command `manul-engine.openScheduler` registered in `extension.ts` with a `$(calendar)` icon in all sidebar view titles.
* **Persistent Run History & Sparklines:** `reporting.py` exposes `append_run_history(mission)` — appends a JSON Lines record (`file`, `name`, `timestamp`, `status`, `duration_ms`) to `reports/run_history.json`. Hooked in `cli.py` (sequential loop, parallel subprocess results, `@before_all`/`@before_group` failure paths) and `scheduler.py` (`_run_scheduled_job()`). `schedulerPanel.ts` imports `fs`, adds `RunHistoryRecord` interface and `readRunHistory(wsRoot, limit=5)` function that parses the JSON Lines file and returns the last N records per filename. `_sendAllFiles()` posts `{ files, history }` to the webview. Frontend JS renders a sparkline (colour-coded dots: green=pass, red=fail, yellow=flaky/warning) and relative-time label ("3m ago") per file row.
* **Self-Healing Controls Cache:** The persistent controls cache now detects stale entries. When a cached locator no longer matches any live DOM candidate, the engine re-resolves via heuristics, updates the cache, and logs `🩹 HEALED`. Stale-but-unhealed entries surface as `⚠️ STALE` warnings in the HTML report.
* **Semantic Test Recorder (`manul record`):** `recorder.py` injects a recording overlay into the browser; user actions (click, type, navigate) are captured and translated into `.hunt` DSL in real time. `manul record <URL>` launches the recorder and saves a hunt file to `tests_home/`.

### Previous highlights (v0.0.9.2)

## 🚀 What's New in v0.0.9.2 — The Mastermind

* **YAML-Like Indentation:** The step parser (`run_mission()`) now strips all leading whitespace from every step line before classification. Hunt files can use clean hierarchical formatting — action lines indented under `STEP` headers — without affecting execution. Tabs and mixed indentation are handled identically. The VS Code extension ships a built-in **Auto-Formatter** (registered as a `DocumentFormattingEditProvider` in `formatter.ts`) that enforces 4-space indentation for action lines under `STEP` blocks.
* **`SET` Command — Mid-Flight Variable Assignment:** `SET {variable} = value` is classified by `classify_step()` as `"set_var"` and handled directly in the step loop. Regex: `^SET\s+\{?(\w+)\}?\s*=\s*(.+)$`. Both `{braced}` and bare-key forms accepted. Quoted values are auto-unquoted via `strip('"').strip("'")`. The variable is written to `self.memory[key]` immediately. Works alongside `@var:` (pre-populated via `initial_vars` before step 1) and `EXTRACT` (populated mid-flight from DOM text).
* **Enterprise Browser & Electron Support:** New `channel` and `executable_path` config keys in `prompts.py` (`_KEY_MAP` entries + module constants). `core.py` `__init__` reads `prompts.CHANNEL` / `prompts.EXECUTABLE_PATH`; `run_mission()` builds a `_launch_opts` dict and conditionally adds `channel` / `executable_path` kwargs to `browser.launch()`. Enables targeting installed browser channels (`"chrome"`, `"msedge"`) or custom executables (Electron). Env var overrides: `MANUL_CHANNEL`, `MANUL_EXECUTABLE_PATH`.
* **`OPEN APP` — Desktop/Electron Attachment:** New step kind `"open_app"` in `classify_step()` (regex: `\bOPEN\s+APP\b`). Handler `_handle_open_app(page, ctx)` in `actions.py` returns `tuple[bool, page]` — checks `ctx.pages` for an existing Electron window, falls back to `ctx.wait_for_event("page")`, then calls `wait_for_load_state("domcontentloaded")`. The `page` variable in `run_mission()` is reassigned from the returned tuple because the handler returns the Electron app's actual window (different from the initially-created empty page).
* **VS Code Auto-Formatter (`formatter.ts`):** New `DocumentFormattingEditProvider` for `.hunt` files. Classifies each line as metadata (`@context:`, `@var:`, `@tags:`, `@data:`, `@blueprint:`), hook block (`[SETUP]`, `[TEARDOWN]`, `[END SETUP]`, `[END TEARDOWN]`), comment (`#`), STEP header, `DONE.`, or action — and indents actions with 4 spaces. All other line types remain flush-left. Registered via `vscode.languages.registerDocumentFormattingEditProvider('hunt', ...)`.

### Previous highlights (v0.0.9.1)

## 🚀 What's New in v0.0.9.1 — Enterprise DSL

* **Data-Driven Testing (`@data:`):** Declare `@data: users.csv` or `@data: data.json` in any `.hunt` file header. The engine loads each row (JSON array-of-objects or CSV via `DictReader`) and reruns the entire mission with row values injected as `{placeholders}`. Implemented in `cli.py` — `parse_hunt_file()` extracts the path into `ParsedHunt.data_file`; `_load_data_file()` resolves the path relative to hunt dir → CWD; `_run_hunt_file()` iterates rows, calls `manul.reset_session_state()` between iterations, and aggregates step results and soft errors.
* **Network Interception (`MOCK` / `WAIT FOR RESPONSE`):** `MOCK GET "/api/users" with 'mocks/users.json'` intercepts matching requests via Playwright `page.route()` with glob pattern `**{path}` and fulfills them from a local JSON file. `WAIT FOR RESPONSE "/api/data"` blocks until a matching network response arrives (uses `page.wait_for_response()` with substring match). Handlers in `actions.py`: `_handle_mock()`, `_handle_wait_for_response()`.
* **Visual Regression (`VERIFY VISUAL`):** `VERIFY VISUAL 'Logo'` resolves the element via heuristics, takes `loc.screenshot()`, saves a baseline PNG in `visual_baselines/` next to the hunt file on first run, and pixel-compares on subsequent runs. Uses PIL/Pillow `ImageChops.difference` when available (configurable threshold, default 1%), falls back to raw byte comparison. Handler: `_handle_verify_visual()`, static helper: `_compare_images()`.
* **Soft Assertions (`VERIFY SOFTLY`):** `VERIFY SOFTLY that 'Warning' is present` delegates to `_handle_verify()` (strips `SOFTLY` keyword) but does **not** break the step loop on failure. Failures are recorded in `_soft_errors: list[str]` and surfaced as `"warning"` status in `MissionResult`. The run continues to completion. Handler: `_handle_verify_softly()`.
* **HTML Reporter — Warning Status:** New amber `⚠️ Warning` stat card, `badge-warning` / `step-warning` / `status-warning` CSS classes, `soft-errors` block with `<ul>` list inside mission details, and a "Show Warnings" filter checkbox in the control panel (mutual exclusion with "Show Only Failed"). `RunSummary.warning` counter; pass-rate includes warnings.

### Previous Engine Overhaul

## 🚀 What's New: The Engine Overhaul

* **Normalised Heuristic Scoring (DOMScorer):** Scoring engine rewritten with `0.0–1.0` float arithmetic. Five weighted channels — `cache` (2.0), `semantics` (0.60), `text` (0.45), `attributes` (0.25), `proximity` (0.10) — combined via `WEIGHTS` dict and multiplied by `SCALE=177,778` for integer thresholds. `data-qa` exact match is the single strongest heuristic signal (+1.0 text). Penalties are clean multipliers: disabled ×0.0, hidden ×0.1. Pre-compiled regex patterns loaded once at module import; per-element strings normalised in a single `_preprocess()` pass.
* **TreeWalker-Based DOM Scanner:** `SNAPSHOT_JS` now walks the DOM with `document.createTreeWalker()` and a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`). Subtrees rejected in one hop — zero wasted traversal. Visibility checked via `checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })` with `offsetWidth/offsetHeight` fallback. No `getComputedStyle` in the hot loop.
* **Safe iframe Support:** `_snapshot()` iterates `page.frames`, injects `SNAPSHOT_JS` per frame, tags elements with `frame_index`. `_frame_for(page, el)` routes `locator()`/`evaluate()` to the correct Playwright `Frame`. Cross-origin frames silently skipped; stale indices fall back to main frame. All 12+ locator call-sites in `actions.py` route through `frame`.
* **Clean, Unnumbered DSL:** Scripts read like plain English (`NAVIGATE to url` instead of `1. NAVIGATE to url`).
* **Logical STEP Grouping:** `STEP [optional number]: [Description]` metadata blocks map manual QA cases directly into `.hunt` files.
* **Interactive Enterprise HTML Reporter:** Dual-mode, zero-dependency reporter with native HTML5 accordions, auto-expanding failures, Flexbox layout, **"Show Only Failed" toggle**, and **tag filter chips** — inline Vanilla JS, zero dependencies.
* **Global Lifecycle Hooks:** `@before_all`, `@after_all`, `@before_group`, `@after_group` orchestrate DB seeding and auth. `ctx.variables` serialise across parallel `--workers`.

## ✨ Key Features

### 🔍 Why ManulEngine?

Most "AI testing" tools are cloud-dependent wrappers that trade speed and reliability for hype. ManulEngine takes the opposite approach.

**Deterministic First — Not an AI Wrapper.** The core engine is a lightning-fast JavaScript `TreeWalker` paired with a mathematically sound `DOMScorer`. Every element resolution is a pure function of DOM state and weighted heuristic signals — no randomness, no token limits, no API latency. Same page, same step, same outcome. Every time.

**Dual Persona Workflow — Testing for Humans, Power for Engineers.** QA engineers write `.hunt` files in a plain-English DSL — no programming required. SDETs extend the same files with Python hooks, Custom Controls, and data-driven parameters. Both personas work on the same artifact.

**Optional AI Fallback — Off by Default.** AI (Ollama / local micro-LLMs) is **turned off by default** (`"model": null`). When enabled, it acts as a self-healing fallback — only invoked when heuristic confidence drops below a threshold. No cloud calls. No per-click charges. No flaky non-determinism in your CI pipeline.

### ⚡ Heuristics Engine — The Mathematical Core

Element resolution is driven entirely by the `DOMScorer` — a normalised `0.0–1.0` float scoring system across five weighted channels:

| Channel | Weight | What it covers |
|---|---|---|
| `cache` | 2.0 | Semantic cache reuse (+1.0), blind context reuse (+0.05) |
| `semantics` | 0.60 | Element-type alignment, role synergy, Shadow DOM bonus |
| `text` | 0.45 | aria/placeholder exact (+0.625), data-qa exact (+1.0), name matching |
| `attributes` | 0.25 | target_field → html_id (+0.6), context words in dev names |
| `proximity` | 0.10 | DOM depth-based form context |

Final score: `(text×W_text + attr×W_attr + sem×W_sem + prox×W_prox + cache×W_cache) × penalty_mult × SCALE`. `SCALE=177,778` maps the weighted float to the integer range expected by `core.py` thresholds (200k for semantic cache, 10k for confidence short-circuit).

When the LLM picker is used, Manul passes the heuristic `score` as a **prior** (hint) by default (`MANUL_AI_POLICY=prior`) — the model can override the ranking only with a clear, disqualifying reason.

### 🧠 Deep Accessibility Heuristics

Manul scores elements using 20+ signals including `aria-label`, `placeholder`, `name` attribute, `data-qa`, `html_id`, semantic `input type`, and contextual section headings. This makes it reliable on modern SPAs and complex design systems (React, Vue, Angular, Wikipedia Vector 2022 / Codex) without any configuration — accessibility attributes are treated as first-class identifiers at the scoring level (`name_attr` exact match: +0.0375 text / ~3k scaled; `data-qa` exact: +1.0 text / ~80k scaled).

### 🌐 Global Lifecycle Hooks (`manul_hooks.py`)

Version 0.0.8.8 introduces a suite-level hook system backed by `manul_engine/lifecycle.py`. Four decorators bracket the full CLI lifecycle:

| Decorator | Fires | Failure semantics |
|---|---|---|
| `@before_all` | Once, before any hunt starts | Failure aborts entire suite; `@after_all` still runs |
| `@after_all` | Once, after all hunts finish | Always runs; failure logged, never overrides suite result |
| `@before_group(tag=)` | Before each matching hunt | Failure skips that mission; `@after_group` still fires |
| `@after_group(tag=)` | After each matching hunt (pass or fail) | Always runs; failure logged, never overrides mission result |

**Quick start:** create `manul_hooks.py` alongside your `.hunt` files.

```python
# tests/manul_hooks.py
from manul_engine import before_all, after_all, before_group, GlobalContext

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
```

**`GlobalContext`** has two fields:
- `variables: dict[str, str]` — propagated into every matching hunt as `initial_vars`; available as `{placeholder}` in steps.
- `metadata: dict[str, object]` — arbitrary per-hook scratch space; not injected into the engine.

**Key implementation notes:**
- `manul_hooks.py` is discovered via `load_hooks_file(directory)` in `lifecycle.py`, executed in an isolated `ModuleType` (same sandbox as `[SETUP]`/`[TEARDOWN]`) — never inserted into `sys.modules`.
- The module-level `registry` singleton collects decorations; decorators reject `async` callables at registration time with `TypeError`.
- `_run_hunt_file()` in `cli.py` accepts a `global_vars` kwarg; lifecycle vars are merged with per-file `@var:` declarations (`@var:` always wins).
- **Parallel workers:** `ctx.variables` is serialised as JSON into the `MANUL_GLOBAL_VARS` env var before worker subprocesses are spawned. Workers call `deserialize_global_vars()` at startup to inherit the shared state. `{placeholder}` substitution works identically in parallel and sequential modes.
- `registry.clear()` is called at the start of each `main()` invocation to prevent stale registrations from a previous run (important for the test runner).

Unit tests: `manul_engine/test/test_27_lifecycle_hooks.py` (57 assertions, no browser).

### 🧹 [SETUP] / [TEARDOWN] Hooks and Inline `CALL PYTHON` Steps

Version 0.0.8.3 introduces a pre/post hook mechanism powered by `manul_engine/hooks.py`. Hooks allow arbitrary synchronous Python to run before and after the browser mission. Version 0.0.8.3 also extends this capability to **inline steps**: `CALL PYTHON <module>.<func>` can now appear as a plain action step anywhere in the main mission body.

**Execution lifecycle:**

```
[SETUP] block         → runs before browser launches
  browser mission     → hunt steps (may include CALL PYTHON steps)
[TEARDOWN] block      → runs in finally{}, always after setup succeeds
```

**Architecture:** The main step executor in `core.py` (`run_mission()`) reuses `execute_hook_line()` from `hooks.py` directly — no duplicated module-resolution logic. The `hunt_dir` parameter is passed through `run_mission(hunt_dir=...)` so inline calls resolve modules relative to the `.hunt` file's directory, exactly as `[SETUP]`/`[TEARDOWN]` do. `cli.py` passes `hunt_dir` to `run_mission` alongside the mission text.

**Module resolution order** (per `CALL PYTHON` instruction — identical for hooks and inline steps):

1. Directory of the `.hunt` file — local project helpers.
2. `Path.cwd()` — project root.
3. Standard `importlib.import_module` — installed packages / PYTHONPATH.

**State isolation:** Modules found via steps 1 and 2 are executed with `spec.loader.exec_module(mod)` into a fresh `ModuleType` object that is **never inserted into `sys.modules`**. This rule applies equally to hook blocks and inline `CALL PYTHON` steps — no `sys.modules` pollution regardless of where in the file the call appears.

**Async rejection:** `asyncio.iscoroutinefunction()` is checked before invoking the callable. Async functions are explicitly rejected with a descriptive error message and a concrete workaround (`asyncio.run()` inside the helper). This applies to both hooks and inline calls.

**Error taxonomy and messages:**

| Error condition | User-facing message prefix |
|---|---|
| Unrecognised instruction | `"Unrecognised hook instruction: '...'"` |
| Missing `.` separator | `"requires '<module>.<function>'"` |
| Module not found | `"Module 'x' not found. Searched in: ..."` |
| Function not found | `"Could not find function 'f' in module 'x.py'. Available: [...]"` |
| Attribute not callable | `"'f' in 'x.py' is not callable (found <type>)"` |
| Async callable | `"'f' is async. Hook functions must be synchronous..."` |
| Function raises | `"'x.f()' raised ExcType: message"` |

**Key APIs in `hooks.py`:**

```python
extract_hook_blocks(raw_text)  → (setup_lines, teardown_lines, mission_body)
execute_hook_line(line, hunt_dir, variables)  → HookResult(success, message, return_value, var_name)
run_hooks(lines, label, hunt_dir, variables)  → bool
```

**`HookResult` fields:** `success: bool`, `message: str`, `return_value: str | None`, `var_name: str | None`. The last two fields are populated when the step used the `into {var}` / `to {var}` capture syntax (see *Dynamic Variables* below); they are `None` for plain `CALL PYTHON` steps. When `into/to` is present, `return_value` is **always** set to `str(ret)` — even when the function returns `None` (yielding the string `"None"`). This guarantees that `{var}` is always bound after a capture step.

**Positional arguments (v0.0.9.1):** `CALL PYTHON` now accepts optional positional arguments between the dotted function name and the optional `into {var}` clause. Arguments are tokenised with `shlex.split()` — single-quoted, double-quoted, and unquoted tokens are all accepted. `{var}` placeholders inside arguments are resolved from the engine’s runtime memory (`self.memory` for inline steps, `parsed_vars`/`variables` dict for hook blocks). Unresolved placeholders are kept as-is.

Full syntax variants:

```text
CALL PYTHON <module>.<function>
CALL PYTHON <module>.<function> "arg1" 'arg2' {var}
CALL PYTHON <module>.<function> "arg1" {var} into {result}
CALL PYTHON <module>.<function> into {result}
```

The regex uses a two-step parsing approach: `_RE_CALL_PYTHON` captures the dotted name and everything after it; `_RE_INTO_VAR` then strips the trailing `into/to {var}` clause from the remainder. What’s left becomes the raw arguments string, parsed by `_parse_call_args()`. This cleanly handles all four variants without backtracking issues.

**Dynamic Variables via `CALL PYTHON ... into {var}`:** Inline `CALL PYTHON` steps may optionally bind their return value to a mission variable:

```text
STEP 1: OTP verification
CALL PYTHON api_helpers.fetch_otp into {dynamic_otp}
Fill 'Security Code' with '{dynamic_otp}'
```

`execute_hook_line` captures the return value from `func()`, converts it to a string, and stores it in `HookResult.return_value`. `run_mission` then writes it to `self.memory[var_name]`, making it available for `{placeholder}` substitution in every subsequent step — exactly like `EXTRACT` or `@var:` variables. Both `into` and `to` are accepted as the keyword. Dynamic-variable unit tests live in `manul_engine/test/test_21_dynamic_vars.py`.

`parse_hunt_file()` in `cli.py` returns a **10-field `ParsedHunt` NamedTuple** `(mission, context, title, step_file_lines, setup_lines, teardown_lines, parsed_vars, tags, data_file, schedule)`. `_run_hunt_file()` calls `run_hooks` before and after the mission with the correct `finally` semantics, and passes `hunt_dir` to `run_mission()` so that inline `CALL PYTHON` steps in the mission body can resolve modules from the same search roots.

The full hook unit test suite (`41 tests, no browser`) lives in `manul_engine/test/test_16_hooks.py`.

### 📋 Static Variable Declaration (`@var:`)

Version 0.0.8.7 adds static test-data declaration at the top of `.hunt` files:

```text
@var: {user_email} = admin@example.com
@var: {password}   = secret123

STEP 1: Login
Fill 'Email' with '{user_email}'
Fill 'Password' with '{password}'
```

**How it works:** `parse_hunt_file()` scans for `@var: {key} = value` header lines and returns them as `parsed_vars` (the 7th element of the 9-field NamedTuple). `_run_hunt_file()` passes `parsed_vars` to `run_mission(initial_vars=...)`, which pre-populates `self.memory` before the step loop starts. Both brace and bare-key forms are accepted (`@var: {key} = val` and `@var: key = val` are equivalent). Values are stripped of leading/trailing whitespace. Malformed `@var:` lines (no `=`) are silently skipped.

**Design rule:** When generating or suggesting `.hunt` test files, **never** hardcode test data (emails, passwords, usernames, search queries, IDs, etc.) directly into `Fill` or `Type` steps. Always declare them at the top via `@var:` and reference them via `{placeholder}`. This keeps test logic separate from test data.

Unit tests: `manul_engine/test/test_20_variables.py` (17 assertions, no browser).

### 🏷️ Arbitrary Tags (`@tags:`) and `--tags` CLI Filter

Version 0.0.8.7 adds a tagging system that lets users run subsets of `.hunt` files without changing directory layout or file names.

**Hunt file header:**
```text
@context: Login flow
@tags: smoke, auth, regression

STEP 1: Navigate
NAVIGATE to https://example.com/login
DONE.
```

**CLI usage:**
```bash
manul tests/ --tags smoke               # run only files tagged 'smoke'
manul tests/ --tags smoke,critical      # OR logic — run files with either tag
```

**Intersection rule:** A file is included in the run if its `@tags:` list shares at least one tag with the `--tags` argument.  Files with no `@tags:` header are **always excluded** when `--tags` is active.

**How it works:** `parse_hunt_file()` now extracts `@tags:` into the **8th element** of the tuple (`tags: list[str]`).  The CLI also exposes `_read_tags(path)` — a fast header-only scanner that stops at the first action or STEP header line — used to pre-filter files in `main()` without running the full parse twice.  Tag filtering prints a one-line summary (`🏷️ --tags '...': N skipped, M matched.`) before the run starts.

Unit tests: `manul_engine/test/test_22_tags.py` (20 assertions, no browser).

### 🎛️ Custom Controls & Page Object Model

Custom Controls provide a first-class escape hatch for UI elements that heuristics and AI cannot reliably target: React virtual tables, canvas widgets, multi-step date-pickers, drag-to-rank lists, etc.

**How it ties into `pages.json`:**
The page name key in the decorator must match the value returned by `lookup_page_name(page.url)` at runtime — i.e. whatever is mapped in `pages.json` for the current URL. This makes the routing completely declarative: update the page name in `pages.json` and all dependent custom controls follow.

**Decorator syntax:**

```python
# controls/checkout.py
from manul_engine import custom_control

@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_datepicker(page, action_type: str, value: str | None) -> None:
    """
    page        — live Playwright Page
    action_type — "input" | "clickable" | "select" | "hover" | "drag" | "locate"
    value       — for 'input' steps: the text to type; None for everything else
    """
    input_loc = page.locator(".react-datepicker__input-container input").first
    if action_type == "input" and value:
        await input_loc.click()
        await input_loc.fill(value)
```

Both sync and async handlers are accepted; the engine awaits async ones.

**Auto-loading:**
`load_custom_controls(workspace_dir)` is called from `ManulEngine.__init__` with `Path.cwd()`. It imports every `*.py` file (not starting with `_`) from `controls/` in an isolated `ModuleType` — same sandboxing pattern as `[SETUP]`/`[TEARDOWN]` hooks.

**Interception point:**
In `run_mission()`, the `else` branch (action steps) runs `get_custom_control(page_name, target)` before taking any DOM snapshot. If a handler is found, it is called with `(page, mode, value)` and `_execute_step` is bypassed entirely. If not found, the normal heuristic/AI pipeline runs.

**Module layout:**

```text
controls/              # user-owned; loaded by load_custom_controls() at startup
  __init__.py          # optional; not loaded (filenames starting with _ are skipped)
  checkout.py          # @custom_control(page="Checkout Page", target="...")
  search.py            # @custom_control(page="Search Results", target="...")
manul_engine/
  controls.py          # registry: _CUSTOM_CONTROLS, @custom_control, get_custom_control,
                       #           load_custom_controls
```

**Corresponding hunt file (no change needed for QA):**

```text
@context: Checkout smoke test

STEP 1: Checkout
NAVIGATE to https://example.com/checkout
Fill 'React Datepicker' with '2026-12-25'
Click the 'Place Order' button
VERIFY that 'Order confirmed' is present.
DONE.
```

---

### 🛡️ Ironclad JS Fallbacks

Modern websites love to hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. Manul primarily uses Playwright interactions with `force=True` plus retries/self-healing; for Shadow DOM elements it falls back to direct JS helpers (`window.manulClick`, `window.manulType`) to keep execution moving.

### 🪢 Shadow DOM & iframe Awareness

The DOM snapshotter walks shadow roots via `TreeWalker` and scans same-origin iframes by iterating `page.frames`. Every element dict carries a `frame_index`; `_frame_for(page, el)` routes all downstream Playwright calls to the correct `Frame`. Cross-origin frames are silently skipped with retry logic (3 attempts, 1.5s backoff on `closed` errors).

### 👻 Anti-Phantom Guard & AI Rejection

When the optional AI fallback is enabled, strict protection against LLM hallucinations is enforced. If the model is unsure it returns `{"id": null}`; the engine treats that as a rejection, blacklists the candidates, and retries with self-healing.

### 🤖 Optional AI Fallback (Ollama)

When enabled via `"model": "qwen2.5:0.5b"` in config, the local LLM acts purely as a self-healing safety net — only invoked when heuristic confidence drops below a configurable threshold. The heuristic `score` is passed as a **prior** (hint) — the model can override only with a clear reason.

If `ai_threshold` is `null` (default) and a model is set, Manul auto-calculates from the model size:

| Model size | Auto threshold |
| --- | --- |
| `< 1b` | `500` |
| `1b – 4b` | `750` |
| `5b – 9b` | `1000` |
| `10b – 19b` | `1500` |
| `20b+` | `2000` |

Set `"model": null` (the default) to run in **heuristics-only mode** — no Ollama, no AI, fully deterministic. This is the recommended mode for CI pipelines.

---

## 💻 System Requirements

| | Minimum | Recommended |
|---|---|---|
| **CPU** | any | modern laptop |
| **RAM** | 4 GB | 8 GB |
| **GPU** | none | none |
| **Model** | — (heuristics-only) | `qwen2.5:0.5b` |

## 🛠️ Installation

### From source (dev mode)

```bash
git clone https://github.com/alexbeatnik/ManulEngine.git
cd ManulEngine
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install playwright
playwright install chromium
```

### From wheel (packaged)

```bash
pip install manul-engine
playwright install chromium
```

Optional — local LLM via Ollama:

```bash
pip install ollama          # Python client library
ollama pull qwen2.5:0.5b   # download model (requires Ollama app: https://ollama.com)
ollama serve
```

## ⚙️ Configuration (manul_engine_configuration.json)

Create `manul_engine_configuration.json` in your project root. All keys are optional.
Environment variables (`MANUL_*`) always override JSON values — useful for CI/CD.

```json
{
  "model": "qwen2.5:0.5b",
  "headless": false,
  "browser": "chromium",
  "browser_args": [],
  "timeout": 5000,
  "nav_timeout": 30000,

  "ai_always": false,       // forced to false when model is null
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

> Set `"model": null` (or omit) → heuristics-only mode, no Ollama needed.

Cache layout:

```text
cache/
    example.com/
        root/
            controls.json
        text-box/
            controls.json
```

Relative `controls_cache_dir` is resolved against CWD (the directory where you invoke `manul`), not the package installation path.

Synthetic tests (`python manul.py test`) disable cache by default for deterministic, side-effect-free results.

---

## 🖥️ CLI Usage

```bash
# Installed CLI (after pip install manul-engine)
manul tests/                       # run all *.hunt files
manul tests/wikipedia.hunt         # single hunt
manul --headless tests/            # headless mode
manul --browser firefox tests/     # run in Firefox
manul tests/ --workers 4           # run 4 hunt files in parallel
manul .                            # all *.hunt in current directory

# Interactive debug mode (terminal) — pauses before every step, prompts ENTER
manul --debug tests/saucedemo.hunt

# Gutter breakpoint mode (VS Code extension debug runner)
manul --break-lines 5,10,15 tests/saucedemo.hunt

# Smart Page Scanner
manul scan https://example.com                  # scan → tests/draft.hunt (tests_home from config)
manul scan https://example.com tests/my.hunt    # explicit output file
manul scan https://example.com --headless       # headless scan
manul scan https://example.com --browser firefox

# Retry failed hunts up to 2 times
manul tests/ --retries 2

# Generate a standalone HTML report (saved to reports/manul_report.html)
manul tests/ --html-report

# Screenshots on failure + HTML report + retries (full CI combo)
manul tests/ --retries 2 --screenshot on-fail --html-report

# Screenshots for every step (detailed forensic report)
manul tests/ --screenshot always --html-report

# Dev launcher (from repo root, no install needed)
python manul.py test               # run synthetic DOM laboratory tests
python manul.py tests/             # run integration hunts
python manul.py --headless tests/  # headless
```

---

## 🚀 Quick Start

Create a hunt file: `tests/mission.hunt`

```text
@context: Demo flow
@title: smoke

STEP 1: Fill text box form
NAVIGATE to https://demoqa.com/text-box
Fill 'Full Name' field with 'Ghost Manul'
Click the 'Submit' button
VERIFY that 'Ghost Manul' is present.
DONE.
```

Run it:

```bash
manul tests/mission.hunt
```

---

## 📜 Available Commands

| Category | Command Syntax |
| --- | --- |
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

*Note: You can append `if exists` or `optional` to the end of any step (outside quoted text) to make it non-blocking, e.g. `Click 'Close Ad' if exists`.*

---

## 🐾 Chaos Chamber Verified (2358 Tests)

The engine is battle-tested with **2358** synthetic DOM/unit tests across 45 test suites covering the web's most annoying UI patterns — including iframe routing, DOMScorer weight hierarchies, TreeWalker filtering, and visibility edge cases.

* **Synthetic DOM packs:** scenario suites under `manul_engine/test/`.
* **Controls cache regression suite:** `manul_engine/test/test_13_controls_cache.py` (disk cache hit/miss with temporary run folder cleanup).
* **AI modes regression suite:** `manul_engine/test/test_12_ai_modes.py` (Always-AI, strict override, AI rejection).
* **QA Classics regression suite:** `manul_engine/test/test_14_qa_classics.py` (legacy HTML patterns, tables, fieldsets).
* **Custom Controls unit suite:** `manul_engine/test/test_19_custom_controls.py` (registry correctness + engine interception, 19 assertions, no browser).
* **Static Variables unit suite:** `manul_engine/test/test_20_variables.py` (parser correctness, `initial_vars` interpolation, 17 assertions, no browser).
* **Dynamic Variables unit suite:** `manul_engine/test/test_21_dynamic_vars.py` (`CALL PYTHON ... into {var}` capture and substitution).
* **Tags unit suite:** `manul_engine/test/test_22_tags.py` (`@tags:` parsing + `--tags` CLI filter, 20 assertions, no browser).
* **Advanced interactions unit suite:** `manul_engine/test/test_23_advanced_interactions.py` (PRESS, RIGHT CLICK, UPLOAD commands, 48 assertions, no browser).
* **Reporting unit suite:** `manul_engine/test/test_24_reporting.py` (StepResult, MissionResult, RunSummary dataclasses, 45 assertions, no browser).
* **HTML reporter unit suite:** `manul_engine/test/test_25_reporter.py` (HTML report generation, base64 screenshots, XSS safety, interactive control panel, tag filtering, 65 assertions, no browser).
* **Wikipedia Search Input unit suite:** `manul_engine/test/test_26_wikipedia_search.py` (`name_attr` heuristic scoring for `<input name="search">` on Vector 2022 skin, 20 assertions, no browser).
* **Lifecycle Hooks unit suite:** `manul_engine/test/test_27_lifecycle_hooks.py` (`@before_all`, `@after_all`, `@before_group`, `@after_group`, `GlobalContext`, `load_hooks_file`, serialize/deserialize, 57 assertions, no browser).
* **Logical Steps unit suite:** `manul_engine/test/test_28_logical_steps.py` (Unnumbered DSL, STEP grouping, snippet injection logic, 48 assertions, no browser).
* **iframe Routing synthetic suite:** `manul_engine/test/test_29_iframe_routing.py` (`_snapshot` frame iteration, `frame_index` tagging, `_frame_for` routing and stale fallback, 25 assertions).
* **Heuristic Weights synthetic+unit suite:** `manul_engine/test/test_30_heuristic_weights.py` (DOMScorer float scoring, WEIGHTS/SCALE constants, `data-qa` dominance, disabled/hidden penalties, mode synergy, 32 assertions).
* **Visibility & TreeWalker synthetic+unit suite:** `manul_engine/test/test_31_visibility_treewalker.py` (PRUNE set subtree skipping, `checkVisibility` filtering, special hidden inputs, snapshot element counts, 20 assertions).
* **VERIFY ENABLED/DISABLED synthetic suite:** `manul_engine/test/test_32_verify_enabled.py` (STATE_CHECK_JS enabled/disabled logic, buttons, inputs, selects, textareas, ARIA roles, CSS-based states, 20 assertions).
* **CALL PYTHON with arguments unit suite:** `manul_engine/test/test_33_call_python_args.py` (`_parse_call_args`, variable resolution, file-based helper execution, engine integration with memory, backward compatibility, 44 assertions, no browser).
* **VERIFY checked/NOT checked synthetic suite:** `manul_engine/test/test_34_verify_checked.py` (checkbox state verification via JS checked property, ARIA checked, mixed states, 20 assertions).
* **Smart Page Scanner synthetic+unit suite:** `manul_engine/test/test_35_scanner.py` (`build_hunt()` element-to-step mapping, keyword generation, metadata headers, edge cases, 44 assertions).
* **Scoring Math unit suite:** `manul_engine/test/test_36_scoring_math.py` (exact numerical scoring validation, WEIGHTS/SCALE constants, channel arithmetic, penalty multipliers, 29 assertions, no browser).
* **Enterprise DSL unit suite:** `manul_engine/test/test_37_enterprise_dsl.py` (`@data:` parsing, `_load_data_file` JSON/CSV loading, MOCK/WAIT FOR RESPONSE/VERIFY VISUAL/VERIFY SOFTLY classification, `ParsedHunt` 9-field compat, reporter warning HTML, `RunSummary.warning`, 68 assertions, no browser).
* **SET & Indentation unit suite:** `manul_engine/test/test_38_set_and_indent.py` (SET command parsing, regex validation, `substitute_memory` integration, `@var:`+SET coexistence, indentation stripping robustness, tab handling, no browser).
* **OPEN APP unit suite:** `manul_engine/test/test_39_open_app.py` (`classify_step` detection, `RE_SYSTEM_STEP` matching, `_handle_open_app` mock tests — existing pages, wait_for_event, failure path, parse_hunt_file integration, 32 assertions, no browser).
* **Self-Healing Cache unit suite:** `manul_engine/test/test_40_self_healing_cache.py` (stale detection, HEALED logging, cache auto-update, HTML reporter badge, 16 assertions).
* **Recorder unit suite:** `manul_engine/test/test_41_recorder.py` (JS injection bridge, DSL step generator, step aggregation, hunt file output, no browser).
* **Scheduler unit suite:** `manul_engine/test/test_42_scheduler.py` (`parse_schedule` all 6 expression forms, case insensitivity, error cases, `next_run_delay`, `_seconds_until_time/weekday`, ParsedHunt integration, Schedule immutability, all 7 weekday names, 51 assertions, no browser).
* **Scoped Variables unit suite:** `manul_engine/test/test_43_scoped_variables.py` (`ScopedVariables` 4-level hierarchy, scope isolation, row-scope auto-clear for `@data:`, `DEBUG VARS` output, dict compatibility, 43 assertions, no browser).
* **Explain Mode unit suite:** `manul_engine/test/test_44_explain_mode.py` (`DOMScorer` explain output, per-candidate channel breakdown, top-3 ranking, `--explain` CLI flag, `MANUL_EXPLAIN` env var, 27 assertions, no browser).
* **Integration hunts:** Real-site E2E flows under `tests/*.hunt` (requires Playwright).

Run the synthetic suite:

```bash
# From repo root (dev mode)
python manul.py test

# Heuristics-only (no Ollama), deterministic:
# Set "model": null in manul_engine_configuration.json
python manul.py test
```

---

## 🤖 LLM Prompts for Hunt File Generation

The `prompts/` directory contains ready-to-use LLM prompt templates that let you generate complete `.hunt` test files automatically.

| File | Purpose |
|---|---|
| `prompts/html_to_hunt.md` | Paste HTML → get hunt steps |
| `prompts/description_to_hunt.md` | Describe a flow in plain text → get hunt steps |
| `prompts/README.md` | Full usage guide for all LLM clients |

### Usage options

**GitHub Copilot Chat (VS Code)**
- Attach `prompts/html_to_hunt.md` via the paperclip icon, paste HTML in the message.
- Or use `#file:prompts/html_to_hunt.md` reference inline in the chat.
- Or open a blank `.hunt` file, press `Ctrl+I`, and reference the prompt file.

**ChatGPT / Claude (web):** Copy the entire prompt file, replace the `<!-- PASTE ... HERE -->` placeholder, send.

**API (Python):** Use the prompt file content as the `system` message and your HTML/description as the `user` message.

**Ollama (local):** `cat prompts/html_to_hunt.md mypage.html | ollama run qwen2.5:7b`

---

## 🖱️ VS Code Extension

The `vscode-extension/` directory contains a companion VS Code extension (v0.0.95) that provides:

| Feature | Details |
| --- | --- |
| **Hunt language support** | Syntax highlighting, bracket matching, and comment toggling for `.hunt` files |
| **Test Explorer integration** | Hunt files appear in VS Code's native Test Explorer; **real-time** step-level pass/fail reporting while the hunt is running |
| **Config sidebar** | Webview panel to edit `manul_engine_configuration.json` visually; **Workers** combobox; **Add Default Prompts** button; live Ollama model discovery via `localhost:11434` |
| **Cache browser** | Tree-view sidebar showing the controls cache hierarchy (`site → page → controls.json`) |
| **Run commands** | `ManulEngine: Run Hunt File` (output panel) and `ManulEngine: Run Hunt File in Terminal` (raw CLI) |
| **Debug run profile** | Test Explorer exposes a **Debug** run profile alongside the normal one; places gutter breakpoints (red dots) in `.hunt` files, pauses at each with a floating QuickPick overlay — **⏭ Next Step** / **▶ Continue All**. The Test Explorer **Stop** button aborts the run cleanly (no hanging QuickPick). On Linux, a system notification appears via `notify-send` when execution pauses. |
| **Step Builder** | Sidebar buttons for every step type including **Open App**, **Set Variable**, **Verify Softly**, **Verify Visual**, **Mock Request**, **Wait Response**, **Debug / Pause** (inserts `DEBUG` step); **🐍 Call Python → Var** (inserts `CALL PYTHON module.function into {variable_name}` and captures the return value as a mission variable); **🔍 Live Page Scanner** — URL input + Run Scan button that invokes `manul scan <URL>` directly and opens the result in the editor |
| **Explain Heuristics CodeLens** | **🔍 Explain Heuristics** CodeLens above every actionable step (Click, Fill, Select, Verify, etc.) in `.hunt` files. Clicking the lens runs the file with `--explain` and streams the scoring breakdown to a dedicated **ManulEngine: Explain Heuristics** output channel. Editor title bar `🔍` button for quick access. Toggle via `manulEngine.explainCodeLens` setting |
| **Bounded concurrency** | Test Explorer respects `workers` config or `manulEngine.workers` VS Code setting (default: 1) |

### Extension behaviour notes

* **Working directory:** The extension spawns `manul` with `cwd` set to the **VS Code workspace folder root** (not the directory of the `.hunt` file). This ensures `manul_engine_configuration.json` and the cache directory are always resolved from the project root, matching what you get when running `manul` from the terminal.
* **Debug protocol:** `runHuntFileDebugPanel` spawns `manul` with `--break-lines` (never `--debug`) and piped stdio. Python emits `\x00MANUL_DEBUG_PAUSE\x00{"step":"...","idx":N}\n` when pausing; TS responds on stdin with one of: `"next\n"` (pause at idx+1), `"continue\n"` (restore original gutter breakpoints), `"debug-stop\n"` (clear all breakpoints, run to end), or `"abort\n"` (then kill the process after 500 ms). The QuickPick overlay exposes five actions: **⏭ Next Step**, **▶ Continue All**, **👁 Highlight Element**, **⏹ Debug Stop**, **🛑 Stop Test**.
* **Auto-annotate:** When `auto_annotate` is enabled (via the Config Panel or `MANUL_AUTO_ANNOTATE` env var), the engine inserts/overwrites `# 📍 Auto-Nav:` comments above any step that follows a URL change — not only explicit `NAVIGATE` steps. URL tracking happens in `run_mission()`: `url_before` is captured before each step's `try` block; after the step's `finally`, if `page.url != url_before` and there is a next step, `_auto_annotate_navigate(page, hunt_file, step_file_lines, i+1)` is called. NAVIGATE steps annotate above themselves as before.
* **`pages.json` format:** Nested two-level dict — `{ "site_root_url": { "Domain": "display name", "regex_or_exact_url": "Page Name", ... } }`. `lookup_page_name()` in `prompts.py` re-reads the file on every call, finds the longest-prefix matching site block, then tries exact URL → regex patterns → `"Domain"` fallback. Auto-generated placeholders are stored under `{ "Domain": "Auto: domain/path" }` for the detected site root. Unknown unmapped pages write back `"Auto: ..."` as the display name in the comment. Auto-population uses a safe **deep-merge**: existing site blocks and their user-defined page mappings are never overwritten — only new top-level site keys or new page keys within a previously-unseen site block are added.
* **`ai_always` guard:** The config panel automatically forces `ai_always` to `false` when no model is selected, preventing an invalid heuristics-only config from being saved with `ai_always: true`.
* **Ollama discovery:** On panel open the extension fetches `http://localhost:11434/api/tags` and populates a `<select>` with installed model names. If Ollama is not running the field accepts free-text input instead.

### Building the extension

```bash
cd vscode-extension
npm install
npm run compile      # tsc one-shot
npm run watch        # incremental (dev)
npx vsce package     # produce .vsix
```

Press **F5** in VS Code (with the extension folder open) to launch a dev Extension Host.

---

**Version:** 0.0.9.5

**Codename:** Explain Mode

**Status:** Hunting...