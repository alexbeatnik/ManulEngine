<p align="center">
  <img src="https://raw.githubusercontent.com/alexbeatnik/ManulEngine/main/images/manul.png" alt="ManulEngine mascot" width="180" />
</p>

# 😼 ManulEngine v0.0.9.27 — Deterministic Web & Desktop Automation Runtime

**ManulEngine — Deterministic Web & Desktop Automation Runtime.**
Write deterministic automation scripts in plain-English Hunt DSL. Run E2E tests, RPA workflows, synthetic monitoring, and AI-agent actions — powered by blazing-fast JS heuristics and Playwright. Automate Chromium, Firefox, WebKit — and desktop apps via Electron.

No CSS selectors. No XPath fragility. No cloud API bills.
ManulEngine is an interpreter for the `.hunt` DSL — a Playwright-backed runtime that resolves DOM elements with a mathematically sound `DOMScorer` (normalised `0.0–1.0` float scoring across 20+ signals) and a native JavaScript `TreeWalker`. Deterministic, reproducible, and fast enough to run anywhere.

> The Manul goes hunting and never returns without its prey.

> **Status: Alpha.**
> **Developed by a single person.**
>
> The architecture is strong, but the project is still being battle-tested on real-world DOMs. Bugs are expected, APIs may evolve, and there are no promises or guarantees of stability. The goal is transparent failure analysis rather than inflated promises.

---

## 📁 Project Structure

```text
ManulEngine/
├── manul.py                          Dev CLI entry point (run hunts from repo root without install)
├── run_tests.py                      Synthetic DOM test suite runner (dev only)
├── bump_version.py                   Version bumper — updates all 18 files from pyproject.toml
├── manul_engine_configuration.json   Project configuration (JSON)
├── pyproject.toml                    Build config — package: manul-engine 0.0.9.27
├── requirements.txt                  Python dependencies
├── manul_engine/                     Core automation engine package
│   ├── __init__.py                   Public API — exports ManulEngine, ManulSession, EngineConfig, all exception classes
│   ├── exceptions.py                Structured exception hierarchy (ManulEngineError base, 7 concrete subclasses)
│   ├── _types.py                    Shared type definitions — ElementSnapshot TypedDict
│   ├── api.py                        ManulSession — public Python API facade (async context manager, Playwright lifecycle)
│   ├── config.py                     EngineConfig frozen dataclass — injectable configuration; validate() method checks invariants
│   ├── cli.py                        Installed CLI entry point (`manul` command + `manul scan` + `manul record` + `manul daemon` subcommands)
│   ├── lifecycle.py                  Global Lifecycle Hook Registry (@before_all, @after_all, @before_group, @after_group)
│   ├── hooks.py                      [SETUP] / [TEARDOWN] hook parser and executor; thread-safe _CACHE_LOCK; 30s CALL PYTHON timeout warning
│   ├── controls.py                   Custom Controls registry (@custom_control, get_custom_control, load_custom_controls); thread-safe _REGISTRY_LOCK
│   ├── recorder.py                   Semantic Test Recorder — JS injection, Python bridge, DSL generator
│   ├── scheduler.py                  Built-in Scheduler — parse_schedule(), Schedule dataclass, daemon_main()
│   ├── _test_runner.py               Dev-only synthetic test runner (not in public CLI)
│   ├── prompts.py                    JSON config loader, thresholds, LLM prompts
│   ├── helpers.py                    Pure utility functions, env helpers, timing constants
│   ├── js_scripts.py                 All JavaScript injected into the browser (incl. SCAN_JS)
│   ├── scoring.py                    Heuristic element-scoring algorithm (20+ rules)
│   ├── scanner.py                    Smart Page Scanner: scan_page(), build_hunt(), scan_main()
│   ├── core.py                       ManulEngine class (resolution, mission runner)
│   ├── cache.py                      Persistent per-site controls cache mixin
│   ├── debug.py                      _DebugMixin (element highlighting, debug prompt, breakpoint protocol, What-If REPL integration)
│   ├── explain_next.py               ExplainNextDebugger — interactive What-If Analysis REPL (PageContext, WhatIfResult, heuristic pre-check, LLM dry-run)
│   ├── llm.py                        LLMProvider protocol + OllamaProvider / NullProvider
│   ├── logging_config.py             Centralized logging hierarchy (stderr, MANUL_LOG_LEVEL)
│   ├── actions.py                    Action execution mixin (click, type, select, hover, drag, scan_page)
│   ├── reporting.py                  StepResult, MissionResult, RunSummary dataclasses; run_history + report-session state persistence
│   ├── reporter.py                   Interactive HTML report generator (dark theme, control panel, tag chips, Run Session banner, base64 screenshots)
│   ├── variables.py                  ScopedVariables — 5-level variable hierarchy (row, step, mission, global, import)
│   ├── imports.py                   @import/@export/USE system; _MAX_IMPORT_DEPTH=10 guard
│   ├── packager.py                  Pack/install .huntlib archives — pack(), install(), _update_lockfile(), resolve_lockfile()
│   └── test/
│       ├── test_00_engine.py         Engine micro-suite (synthetic DOM via local HTML)
│       ├── test_01_ecommerce.py      Scenario pack: ecommerce
│       ├── ...
│       ├── test_12_ai_modes.py       Unit: Always-AI/strict/rejection
│       ├── test_13_controls_cache.py Unit: persistent controls cache
│       ├── test_14_qa_classics.py    Unit: legacy HTML patterns, tables, fieldsets
│       ├── test_15_facebook_final_boss.py
│       ├── test_16_hooks.py          Unit: [SETUP]/[TEARDOWN] hooks (56 assertions, no browser)
│       ├── test_17_frontend_hell.py  Unit: frontend anti-patterns (overlays, z-index traps, React portals)
│       ├── test_18_disambiguation.py Unit: ambiguous element targeting
│       ├── test_19_custom_controls.py Unit: Custom Controls registry + engine interception (28 assertions, no browser)
│       ├── test_20_variables.py      Unit: @var: static variable declaration + @script alias parsing (23 assertions, no browser)
│       ├── test_21_dynamic_vars.py   Unit: CALL PYTHON ... into {var} dynamic variable capture
│       ├── test_22_tags.py           Unit: @tags: / --tags CLI filter (20 assertions, no browser)
│       ├── test_23_advanced_interactions.py  Unit: PRESS/RIGHT CLICK/UPLOAD/explicit waits (58 assertions, no browser)
│       ├── test_24_reporting.py      Unit: StepResult/MissionResult/RunSummary dataclasses (67 assertions)
│       ├── test_25_reporter.py       Unit: HTML report generator (70 assertions, no browser)
│       ├── test_26_wikipedia_search.py Unit: name_attr heuristic scoring (20 assertions, no browser)
│       ├── test_27_lifecycle_hooks.py  Unit: Global Lifecycle Hook system (57 assertions, no browser)
│       ├── test_28_logical_steps.py    Unit: Logical STEP ordering and parser (58 assertions, no browser)
│       ├── test_29_iframe_routing.py   Synthetic: Cross-frame element resolution (25 assertions)
│       ├── test_30_heuristic_weights.py Synthetic+Unit: DOMScorer priority hierarchy (32 assertions)
│       ├── test_31_visibility_treewalker.py Synthetic+Unit: TreeWalker PRUNE/checkVisibility (20 assertions)
│       ├── test_32_verify_enabled.py Synthetic: VERIFY ENABLED/DISABLED state verification (20 assertions)
│       ├── test_33_call_python_args.py Unit: CALL PYTHON with positional arguments + unresolved @script alias handling (50 assertions, no browser)
│       ├── test_34_verify_checked.py Synthetic: VERIFY checked/NOT checked (20 assertions)
│       ├── test_35_scanner.py       Synthetic+Unit: Smart Page Scanner build_hunt() (44 assertions)
│       ├── test_36_scoring_math.py   Unit: exact numerical scoring validation (29 assertions, no browser)
│       ├── test_37_enterprise_dsl.py Unit: Enterprise DSL — @data:, MOCK, VERIFY VISUAL/SOFTLY, explicit waits, reporter warnings (75 assertions, no browser)
│       ├── test_38_set_and_indent.py Unit: SET command & indentation robustness (v0.0.9.2)
│       ├── test_39_open_app.py       Unit: OPEN APP command — classify_step, RE_SYSTEM_STEP, _handle_open_app (41 assertions, no browser)
│       ├── test_40_self_healing_cache.py Unit: Self-Healing Controls Cache — stale detection, HEALED logging, cache auto-update (16 assertions)
│       ├── test_41_recorder.py      Unit: Semantic Test Recorder — JS bridge, DSL generator, step aggregation (no browser)
│       ├── test_42_scheduler.py     Unit: Built-in Scheduler — parse_schedule, next_run_delay, ParsedHunt integration (51 assertions, no browser)
│       ├── test_43_scoped_variables.py Unit: ScopedVariables 5-level hierarchy, scope isolation, dict compat (44 assertions, no browser)
│       ├── test_44_explain_mode.py   Unit: DOMScorer explain output, channel breakdown, --explain CLI flag (33 assertions, no browser)
│       ├── test_45_api.py            Unit: ManulSession public Python API facade (50 assertions, no browser)
│       ├── test_46_attribute_semantic.py Unit: attribute-semantic icon matching, camelCase dev attrs, cart badges, false-positive resistance (34 assertions, no browser)
│       ├── test_47_contextual_proximity.py Unit: contextual NEAR / HEADER / FOOTER / INSIDE scoring and parser rules (67 assertions, no browser)
│       ├── test_48_prompts_config.py  Unit: Configuration loading, threshold derivation, page-name lookup, _KEY_MAP, env_bool (83 assertions, no browser)
│       ├── test_50_imports.py         Unit: @import/@export/USE directive system (84 assertions, no browser)
│       ├── test_51_packager.py        Unit: Pack/install .huntlib archives and lockfile (21 assertions, no browser)
│       ├── test_52_exports.py         Unit: @export validation, wildcard exports, access control (19 assertions, no browser)
│       └── test_53_explain_next.py    Unit: ExplainNextDebugger What-If Analysis REPL + debug protocol (112 assertions, no browser)
├── demo/                             Integration demo hunts and supporting assets
│   ├── run_demo.py                   Runner script (sets CWD, calls manul CLI)
│   ├── manul_engine_configuration.json Demo-specific config (heuristics-only)
│   ├── pages.json                    Page-name registry for demo sites
│   ├── tests/                        Integration .hunt files
│   │   ├── saucedemo.hunt            SauceDemo checkout flow with @var and NEAR qualifier
│   │   ├── demoqa.hunt               DemoQA form, checkbox, radio, and table coverage
│   │   ├── mega.hunt                 Large UI gauntlet: drag-drop, shadow DOM, scroll
│   │   ├── rahul.hunt                Rahul Shetty practice flow: radio, autocomplete, hover
│   │   └── call_python_variants.hunt All CALL PYTHON variants: positional args, aliases, to/into capture
│   ├── scripts/                      Python helpers used by call_python_variants.hunt
│   ├── controls/                     Educational @custom_control examples
│   ├── examples/                     Additional Python helpers for CALL PYTHON demos
│   ├── playground/                   Experimental nested-module demos
│   └── benchmarks/                   Adversarial benchmark suite (12 tasks, 5 HTML fixtures)
├── reports/                          Generated logs and HTML reports (auto-created, .gitignored)
├── contracts/                        Machine-readable contracts for downstream tooling
│   ├── MANUL_API_CONTRACT.md        ManulSession Python API surface
│   ├── MANUL_CLI_CONTRACT.md        CLI interface: subcommands, flags, exit codes
│   ├── MANUL_CONFIG_CONTRACT.md     Configuration keys, env vars, defaults, variable scoping
│   ├── MANUL_DSL_CONTRACT.md        .hunt DSL commands, metadata, qualifiers
│   ├── MANUL_HOOKS_CONTRACT.md      Hooks, lifecycle decorators, module resolution
│   ├── MANUL_REPORTING_CONTRACT.md  Reporting dataclasses, persistence, HTML report
│   └── MANUL_SCORING_CONTRACT.md    DOMScorer heuristics, element snapshot shape
├── prompts/                          LLM prompt templates for hunt file generation
│   ├── README.md                     Usage guide (Copilot, ChatGPT, Claude, Ollama)
│   ├── html_to_hunt.md               Prompt: HTML page → hunt steps
│   └── description_to_hunt.md        Prompt: plain-text description → hunt steps
├── docs/
│   └── adr/                          Architecture Decision Records (ADR-001 through ADR-004)
├── Dockerfile                        Multi-stage CI/CD runner image (ghcr.io/alexbeatnik/manul-engine)
├── .dockerignore                     Build-context exclusions for Docker
├── docker-compose.yml                Local dev/CI compose: manul, manul-daemon services
├── .github/dependabot.yml            Automated dependency updates (pip + github-actions, weekly)
└── .github/workflows/
    ├── synthetic-tests.yml            PR quality gate (synthetic test suite)
    ├── lint.yml                       Ruff lint + format check on PR and push to main
    ├── release.yml                    Unified release: PyPI + GHCR + GitHub Release on v* tag (includes lint gate)
    ├── docker-dev.yml                 Dev Docker image on main push (amd64-only)
    └── manul-ci.yml                   Reusable example workflow for downstream repos
```

Companion Manul Engine Extension for VS Code source is maintained separately and is not included in this workspace.

---

## 🏛️ Architecture — ManulEngine as a Runtime

ManulEngine is not a test library bolted onto Playwright. It is a **runtime** — an interpreter for the `.hunt` DSL that sits between human-authored (or AI-generated) automation scripts and the browser.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  .hunt DSL             (human-authored or AI-generated)                 │
│  QA tests · RPA scripts · synthetic monitors · agent tasks              │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Parser (cli.py)                                                        │
│  parse_hunt_file() → ParsedHunt NamedTuple                              │
│  Extracts: @context, @title, @tags, @data, @var,                        │
│  [SETUP]/[TEARDOWN], step lines                                         │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Execution Engine (core.py → run_mission)                               │
│  DOMScorer (scoring.py) · TreeWalker (js_scripts.py)                    │
│  Element resolution → Action dispatch → Self-healing                    │
└───────────┬─────────────────────┬─────────────────────┬──────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ Custom Controls │  │ Python Hooks       │  │ Persistent Cache  │
│ (controls.py)   │  │ [SETUP]/[TEARDOWN] │  │ (cache.py)        │
│ @custom_control │  │ CALL PYTHON        │  │ Per-site storage  │
└────────────────┘  │ @before_all        │  └───────────────────┘
                    └───────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Playwright (async)                                                     │
│  Chromium · Firefox · WebKit · Electron                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

This architecture is what makes ManulEngine a **true runtime** rather than just a test library. The `.hunt` DSL is the instruction set. The parser and engine are the interpreter. Playwright is the I/O layer. Users write scripts — QA tests, RPA workflows, synthetic monitors, or AI-agent actions — in the same deterministic DSL, and the runtime executes them identically.

### Previous Engine Overhaul

## 🚀 What's New: The Engine Overhaul

* **Normalised Heuristic Scoring (DOMScorer):** Scoring engine rewritten with `0.0–1.0` float arithmetic. Five weighted channels — `cache` (2.0), `semantics` (0.60), `text` (0.45), `attributes` (0.25), `proximity` (0.10) — combined via `WEIGHTS` dict and multiplied by `SCALE=177,778` for integer thresholds. `data-qa` exact match is the single strongest heuristic signal (+1.0 text). Penalties are clean multipliers: disabled ×0.0, hidden ×0.1. Pre-compiled regex patterns loaded once at module import; per-element strings normalised in a single `_preprocess()` pass.
* **TreeWalker-Based DOM Scanner:** `SNAPSHOT_JS` now walks the DOM with `document.createTreeWalker()` and a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`). Subtrees rejected in one hop — zero wasted traversal. Visibility checked via `checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })` with `offsetWidth/offsetHeight` fallback. No `getComputedStyle` in the hot loop.
* **Safe iframe Support:** `_snapshot()` iterates `page.frames`, injects `SNAPSHOT_JS` per frame, tags elements with `frame_index`. `_frame_for(page, el)` routes `locator()`/`evaluate()` to the correct Playwright `Frame`. Cross-origin frames silently skipped; stale indices fall back to main frame. All 12+ locator call-sites in `actions.py` route through `frame`.
* **Clean, Unnumbered DSL:** Scripts read like plain English (`NAVIGATE to url` instead of `1. NAVIGATE to url`).
* **Logical STEP Grouping:** `STEP [optional number]: [Description]` metadata blocks map manual QA cases directly into `.hunt` files.
* **Interactive Enterprise HTML Reporter:** Dual-mode, zero-dependency reporter with native HTML5 accordions, auto-expanding failures, Flexbox layout, **"Show Only Failed" toggle**, **tag filter chips**, and a visible **Run Session / Merged invocations** banner for recent cross-invocation report aggregation.
* **Global Lifecycle Hooks:** `@before_all`, `@after_all`, `@before_group`, `@after_group` orchestrate DB seeding and auth. `ctx.variables` serialise across parallel `--workers`.
* **Contextual UI Navigator (v0.0.9.13):** action steps can now add `NEAR 'Anchor'`, `ON HEADER`, `ON FOOTER`, and `INSIDE 'Container' row with 'Text'` qualifiers. `actions.py` parses the contextual hint before normal mode detection, resolves anchor or row context, and threads that data into the scorer. `DOMScorer` boosts the proximity channel from `0.10` to `1.5` when a contextual hint is present, then switches from DOM-depth proximity to Euclidean distance, viewport-region checks, or subtree membership depending on the qualifier.
* **Attribute-Semantic Matching for Functional Icons (v0.0.9.12):** `DOMScorer` now treats discrete keyword tokens in `html_id`, `class_name`, and `data_qa` as a strong signal even when visible text is unhelpful. This closes a real gap for cart-style links and other icon controls that only render badge counts (`"1"`, `"2"`, `"3"`) while the semantic meaning lives in attributes like `shopping_cart_link` or `shopping_cart_container`.
* **JIT Module Loading & Dotted Helper Imports (v0.0.9.11):** `CALL PYTHON` modules are imported on first use and cached for subsequent calls within the same process (`_module_cache` in `hooks.py`). `@custom_control` modules are loaded once on the first `run_mission()` call instead of during `ManulEngine.__init__`. Helper imports now rely on dotted Python module paths (`scripts.auth_helpers`, `package.module.function`) rather than configurable helper directories.

## ✨ Key Features

The public README is expected to preserve a richer runtime-reference layer, not only product positioning. In practice that means keeping explicit sections for explainability layers, four automation pillars, desktop automation, state/hook orchestration, and benchmark/test coverage.

### 🔍 Why ManulEngine?

Most "AI testing" tools are cloud-dependent wrappers that trade speed and reliability for hype. ManulEngine takes the opposite approach.

**Deterministic First — Not an AI Wrapper.** The core engine is a lightning-fast JavaScript `TreeWalker` paired with a mathematically sound `DOMScorer`. Every element resolution is a pure function of DOM state and weighted heuristic signals — no randomness, no token limits, no API latency. Same page, same step, same outcome. Every time.

**Dual Persona Workflow — Testing for Humans, Power for Engineers.** QA engineers write `.hunt` files in a plain-English DSL — no programming required. SDETs extend the same files with Python hooks, Custom Controls, and data-driven parameters. Both personas work on the same artifact.

**Optional AI Fallback — Off by Default.** AI (Ollama / local micro-LLMs) is **turned off by default** (`"model": null`). When enabled, it acts as a self-healing fallback — only invoked when heuristic confidence drops below a threshold. No cloud calls. No per-click charges. No flaky non-determinism in your CI pipeline.

### 🔍 Explainability Layers

The public/runtime docs should describe explainability as a multi-layer workflow:

- CLI `--explain` for raw candidate ranking and per-channel breakdowns.
- VS Code title bar action for step-local explain requests during a debug pause.
- VS Code hover tooltips for line-attached breakdowns after debug runs.

This is part of the product definition, not a side note.

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

### 📐 Contextual UI Navigator

The resolver now understands contextual qualifiers directly in the DSL when identical labels appear multiple times:

```text
Click the 'Delete' button NEAR 'John Doe'
Click the 'Login' button ON HEADER
Click the 'Privacy Policy' link ON FOOTER
Click the 'Delete' button INSIDE 'Actions' row with 'John Doe'
```

- `NEAR` resolves the anchor first, then scores candidates by Euclidean distance between element centers.
- `ON HEADER` prefers candidates inside `header` / `nav` ancestry or inside the top 15% of the viewport.
- `ON FOOTER` prefers candidates inside `footer` ancestry or inside the bottom 15% of the viewport.
- `INSIDE ... row with ...` resolves the row text, climbs to a container boundary (`tr`, `li`, `div[role=row]`, etc.), and limits scoring to that subtree.

This feature is deterministic: it does not add a planner layer or selector escape hatch. It feeds richer spatial context into the existing scoring pipeline.

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

The hook system in `manul_engine/hooks.py` runs synchronous Python before and after the browser mission. The same executor also powers inline `CALL PYTHON <module>.<func>` action steps inside the main mission body, so variable capture and module resolution behave the same way in both places.

**Execution lifecycle:**

```text
[SETUP] block         → runs before browser launches
  setup failure       → mission is marked BROKEN and browser steps are skipped
  browser mission     → hunt steps (may include CALL PYTHON steps)
[TEARDOWN] block      → runs in finally{}, always after setup succeeds
```

**Architecture:** The main step executor in `core.py` (`run_mission()`) reuses `execute_hook_line()` from `hooks.py` directly — no duplicated module-resolution logic. The `hunt_dir` parameter is passed through `run_mission(hunt_dir=...)` so inline calls resolve modules relative to the `.hunt` file's directory, exactly as `[SETUP]`/`[TEARDOWN]` do. `cli.py` passes `hunt_dir` to `run_mission` alongside the mission text.

**Module resolution order** (per `CALL PYTHON` instruction — identical for hooks and inline steps):

1. Directory of the `.hunt` file.
2. `Path.cwd()` — project root.
3. Standard `importlib.import_module` — installed packages / PYTHONPATH.

**State isolation:** Modules found via the file-based search steps are executed with `spec.loader.exec_module(mod)` into a fresh `ModuleType` object that is **never inserted into `sys.modules`**. This rule applies equally to hook blocks and inline `CALL PYTHON` steps — no `sys.modules` pollution regardless of where in the file the call appears.

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

**Supported hook instructions:**

```text
PRINT "message with {vars}"
CALL PYTHON <module>.<function>
CALL PYTHON <module>.<function> with args: "arg1" "arg2"
CALL PYTHON <module>.<function> into {result}
CALL PYTHON <module>.<function> with args: "arg1" "arg2" into {result}
```

**File-local script aliases:**

```text
@script: {auth} = scripts.auth_helpers
@script: {api} = helpers.api_client

CALL PYTHON {auth}.issue_token into {token}
CALL PYTHON {api}.fetch_otp "{token}" into {otp}
```

`parse_hunt_file()` rewrites `CALL PYTHON {alias}.func` to the corresponding dotted module path before the mission or hook block is executed. Alias declarations stay header-only and never appear in the mission body.

**`HookResult` fields:** `success: bool`, `message: str`, `return_value: str | None`, `var_name: str | None`, `return_mapping: dict[str, str]`. The `return_value` / `var_name` pair is populated when the step used `into {var}` / `to {var}` capture syntax. `return_mapping` is populated when a helper returns a top-level dict; its keys are flattened into the shared variable context so later hook lines and browser steps can reference `{key}` directly.

**Positional arguments:** `CALL PYTHON` accepts optional positional arguments between the dotted function name and the optional `into {var}` clause. Arguments are tokenised with `shlex.split()` — single-quoted, double-quoted, and unquoted tokens are all accepted. The optional `with args:` prefix is treated as syntax sugar and stripped before parsing. `{var}` placeholders inside arguments are resolved from the engine's runtime memory (`self.memory` for inline steps, `parsed_vars`/`variables` dict for hook blocks). Unresolved placeholders are kept as-is.

Full syntax variants:

```text
CALL PYTHON <module>.<function>
CALL PYTHON <module>.<function> "arg1" 'arg2' {var}
CALL PYTHON <module>.<function> "arg1" {var} into {result}
CALL PYTHON <module>.<function> into {result}
```

The regex uses a two-step parsing approach: `_RE_CALL_PYTHON` captures the dotted name and everything after it; `_RE_INTO_VAR` then strips the trailing `into/to {var}` clause from the remainder. What's left becomes the raw arguments string, parsed by `_parse_call_args()`. This cleanly handles all four variants without backtracking issues.

**Dynamic Variables via `CALL PYTHON ... into {var}`:** Inline `CALL PYTHON` steps may optionally bind their return value to a mission variable:

```text
STEP 1: OTP verification
CALL PYTHON api_helpers.fetch_otp into {dynamic_otp}
Fill 'Security Code' with '{dynamic_otp}'
```

`execute_hook_line` captures the return value from `func()`, converts it to a string, and stores it in `HookResult.return_value`. `run_mission` then writes it to `self.memory[var_name]`, making it available for `{placeholder}` substitution in every subsequent step — exactly like `EXTRACT` or `@var:` variables. Both `into` and `to` are accepted as the keyword. Dynamic-variable unit tests live in `manul_engine/test/test_21_dynamic_vars.py`.

When a hook helper returns a dict such as `{"tenant_id": 42, "otp": 123456}`, `bind_hook_result()` flattens it into shared variables. That makes both `{tenant_id}` and `{otp}` available immediately to later hook lines and to the browser mission without additional glue code.

`parse_hunt_file()` in `cli.py` returns a **12-field `ParsedHunt` NamedTuple** `(mission, context, title, step_file_lines, setup_lines, teardown_lines, parsed_vars, tags, data_file, schedule, exports, imports)`. It also strips header-only `@script:` declarations, validates that they use dotted Python import paths, and rewrites `CALL PYTHON {alias}.func` usages to their real module paths before returning the mission and hook lines. `parse_hunt_file()` also resolves `@import:` directives via `resolve_imports()` and expands `USE` directives via `expand_use_directives()` before returning the mission text. `_run_hunt_file()` calls `run_hooks` before and after the mission with the correct `finally` semantics, and passes `hunt_dir` to `run_mission()` so that inline `CALL PYTHON` steps in the mission body can resolve modules from the same search roots.

The full hook unit test suite (`56 tests, no browser`) lives in `manul_engine/test/test_16_hooks.py`.

### 📋 Static Variable Declaration (`@var:`) and Script Aliases (`@script:`)

Version 0.0.8.7 adds static test-data declaration at the top of `.hunt` files:

```text
@var: {user_email} = admin@example.com
@var: {password}   = secret123
@script: {auth}    = scripts.auth_helpers
@script: {issue_login_token} = scripts.auth_helpers.issue_login_token

STEP 1: Login
Fill 'Email' with '{user_email}'
Fill 'Password' with '{password}'
CALL PYTHON {auth}.issue_login_token into {login_token}
CALL PYTHON {issue_login_token} into {login_token_2}
```

**How it works:** `parse_hunt_file()` scans for `@var: {key} = value` header lines and returns them as `parsed_vars`. `_run_hunt_file()` passes `parsed_vars` to `run_mission(initial_vars=...)`, which pre-populates `self.memory` before the step loop starts. Both brace and bare-key forms are accepted (`@var: {key} = val` and `@var: key = val` are equivalent). Values are stripped of leading/trailing whitespace. Malformed `@var:` lines (no `=`) are silently skipped.

`@script:` uses the same declaration shape for both helper-module aliases and helper-callable aliases. Examples: `@script: {auth} = scripts.auth_helpers` and `@script: {issue_login_token} = scripts.auth_helpers.issue_login_token`. The parser requires a valid dotted Python import path, rejects slash paths or `.py` suffixes, and rewrites later `CALL PYTHON {auth}.func` or `CALL PYTHON {issue_login_token}` usages in both hook blocks and mission steps.

**Design rule:** When generating or suggesting `.hunt` test files, **never** hardcode test data (emails, passwords, usernames, search queries, IDs, etc.) directly into `Fill` or `Type` steps. Always declare them at the top via `@var:` and reference them via `{placeholder}`. This keeps test logic separate from test data.

Unit tests: `manul_engine/test/test_20_variables.py` (23 assertions, no browser).

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
manul path/to/hunts/ --tags smoke               # run only files tagged 'smoke'
manul path/to/hunts/ --tags smoke,critical      # OR logic — run files with either tag
```

**Intersection rule:** A file is included in the run if its `@tags:` list shares at least one tag with the `--tags` argument. Files with no `@tags:` header are **always excluded** when `--tags` is active.

**How it works:** `parse_hunt_file()` now extracts `@tags:` into the `tags: list[str]` field. The CLI also exposes `_read_tags(path)` — a fast header-only scanner that stops at the first action or STEP header line — used to pre-filter files in `main()` without running the full parse twice. Tag filtering prints a one-line summary (`🏷️ --tags '...': N skipped, M matched.`) before the run starts.

Unit tests: `manul_engine/test/test_22_tags.py` (20 assertions, no browser).

### 🎛️ Custom Controls & Page Object Model

Custom Controls provide a first-class escape hatch for UI elements that heuristics and AI cannot reliably target: React virtual tables, canvas widgets, multi-step date-pickers, drag-to-rank lists, etc.

**How it ties into `pages.json`:**
The page name key in the decorator must match the value returned by `lookup_page_name(page.url)` at runtime — whatever is mapped in `pages.json` for the current URL. This makes the routing declarative: update the page name in `pages.json` and all dependent custom controls follow.

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

### 🐍 Public Python API (`ManulSession`)

`ManulSession` is a high-level async context manager for programmatic browser automation in pure Python. It manages its own Playwright lifecycle and routes all element-resolution calls through the full ManulEngine pipeline (cache → heuristics → optional LLM fallback). Callers never need to think about selectors.

```python
from manul_engine import ManulSession

async with ManulSession(headless=True) as session:
    await session.navigate("https://example.com/login")
    await session.fill("Username field", "admin")
    await session.fill("Password field", "secret")
    await session.click("Log in button")
    await session.verify("Welcome")
    price = await session.extract("Product Price")
```

Core methods: `navigate`, `click`, `fill`, `select`, `hover`, `drag`, `right_click`, `press`, `upload`, `scroll`, `verify`, `extract`, `wait`, `run_steps`. Properties: `page`, `engine`, `memory`.

`run_steps()` accepts a multi-line DSL string and executes it against the already-open browser — useful for mixing programmatic Python with `.hunt` DSL snippets.

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
pip install playwright==1.58.0
playwright install chromium
```

### From wheel (packaged)

```bash
pip install manul-engine==0.0.9.27
playwright install chromium
```

Optional — local LLM via Ollama:

```bash
pip install ollama==0.6.1
ollama pull qwen2.5:0.5b
ollama serve
```

## ⚙️ Configuration (manul_engine_configuration.json)

Create `manul_engine_configuration.json` in your project root. All keys are optional.
Environment variables (`MANUL_*`) always override JSON values — useful for CI/CD.

The public README is expected to keep the full current runtime surface area plus representative `MANUL_*` override examples. Do not collapse it to a minimal JSON snippet unless it is clearly labelled as a minimal example.

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
  "custom_controls_dirs": ["controls"],
  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "tests_home": "tests",
  "auto_annotate": false,
  "channel": null,
  "executable_path": null,
  "workers": 1,
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

Synthetic tests (`python run_tests.py`) disable cache by default for deterministic, side-effect-free results.

---

## 🖥️ CLI Usage

```bash
# Installed CLI (after pip install manul-engine)
manul path/to/hunts/                   # run all *.hunt files
manul path/to/file.hunt                # single hunt
manul --headless path/to/hunts/        # headless mode
manul --browser firefox path/to/hunts/ # run in Firefox
manul path/to/hunts/ --workers 4       # run 4 hunt files in parallel
manul .                                # all *.hunt in current directory

# Interactive debug mode (terminal) — pauses before every step, prompts ENTER
manul --debug path/to/file.hunt

# Gutter breakpoint mode (VS Code extension debug runner)
manul --break-lines 5,10,15 path/to/file.hunt

# Smart Page Scanner
manul scan https://example.com
manul scan https://example.com output.hunt
manul scan https://example.com --headless
manul scan https://example.com --browser firefox

# Retry failed hunts up to 2 times
manul path/to/hunts/ --retries 2

# Generate a standalone HTML report
manul path/to/hunts/ --html-report

# Report header shows Run Session and Merged invocations when recent
# CLI/Test Explorer runs are aggregated into the same HTML report.

# Screenshots on failure + HTML report + retries
manul path/to/hunts/ --retries 2 --screenshot on-fail --html-report

# Screenshots for every step
manul path/to/hunts/ --screenshot always --html-report

# Synthetic DOM test suite (dev only, no install needed)
python run_tests.py

# Integration demo hunts (needs network + Playwright browsers)
python demo/run_demo.py
python demo/run_demo.py tests/saucedemo.hunt
python demo/run_demo.py --headless
```

---

## 🐳 Docker CI/CD Runner

ManulEngine ships a multi-stage `Dockerfile` that packages the engine as a headless CI runner image published to `ghcr.io/alexbeatnik/manul-engine`.

```bash
docker run --rm --shm-size=1g \
  -v $(pwd)/hunts:/workspace/hunts:ro \
  -v $(pwd)/reports:/workspace/reports \
  ghcr.io/alexbeatnik/manul-engine:0.0.9.27 \
  --html-report --screenshot on-fail hunts/
```

**Image characteristics:**
* Two-stage build: `deps` (pip install + Playwright browsers) → `runtime` (slim, no build tools or pip cache).
* Non-root user `manul` (UID 1000). No `--privileged` needed.
* `dumb-init` as PID 1 for proper signal handling and exit-code propagation.
* CI defaults baked in: `MANUL_HEADLESS=true`, `MANUL_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage"`, `TZ=UTC`, `LANG=C.UTF-8`.
* Build args: `MANUL_VERSION` (pip version), `PYTHON_VERSION` (base image), `BROWSERS` (space-separated, default `chromium`).
* Volume mount pattern: `/workspace/tests` (ro), `/workspace/reports` (rw), `/workspace/cache` (rw), `/workspace/controls` (ro), `/workspace/scripts` (ro).

**docker-compose.yml** defines two services:
* `manul` — test runner
* `manul-daemon` — scheduled hunts (`restart: unless-stopped`)

**GitHub Actions workflows:**
* `release.yml` — unified release pipeline: synthetic tests → PyPI publish (OIDC) → GHCR multi-arch image → GitHub Release.
* `docker-dev.yml` — pushes a `main`-tagged dev image to GHCR on every merge to `main`.
* `manul-ci.yml` — reusable example workflow for downstream repos to run `.hunt` tests against the published image.

---

## 🚀 Quick Start

Create a hunt file: `my_mission.hunt`

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
manul my_mission.hunt
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
| **Verification** | `VERIFY that [Text] is present/absent`, `VERIFY that [Element] is checked/disabled/enabled`, `Verify '<element>' <type> has text '<expected>'`, `Verify '<element>' <type> has placeholder '<expected>'`, `Verify '<element>' <type> has value '<expected>'` |
| **Page Scanner** | `SCAN PAGE`, `SCAN PAGE into {filename}` |
| **Debug** | `DEBUG` / `PAUSE` — pause execution at that step (use with `--debug` or VS Code gutter breakpoints) |
| **Keyboard** | `PRESS ENTER`, `PRESS [Key]`, `PRESS [Key] on [Element]` |
| **File Upload** | `UPLOAD 'File' to 'Element'` |
| **Variables** | `SET {variable} = value`, `@var: {name} = value` (header declaration) |
| **Flow Control** | `WAIT [seconds]`, `Wait for "Text" to be visible`, `Wait for 'Spinner' to disappear`, `Wait for "Element" to be hidden`, `SCROLL DOWN` |
| **Finish** | `DONE.` |

*Note: You can append `if exists` or `optional` to the end of any step (outside quoted text) to make it non-blocking, e.g. `Click 'Close Ad' if exists`.*

`disappear` is an alias for Playwright's `hidden` state. The runtime routes these explicit waits through `locator.wait_for()` instead of using hard sleeps.

### Strict Assertions

Use strict assertions when the DSL must validate the exact visible text, exact placeholder attribute, or exact current field value on a resolved element.

```text
Verify "save" button has text "Save me"
Verify "Error message" element has text "Invalid credentials"
Verify 'Login' field has placeholder "Login/Email"
Verify "Search" input has placeholder "Type to search..."
Verify "Email" field has value "captain@manul.com"
Verify "Notes" element has value "treasure map"
```

- `Verify "<element_name>" <type> has text "<expected_text>"` routes through the normal resolver, then compares `locator.inner_text().strip()` with strict equality.
- `Verify "<element_name>" <type> has placeholder "<expected_placeholder>"` resolves the target and compares `locator.get_attribute("placeholder")` with strict equality.
- `Verify "<element_name>" <type> has value "<expected_value>"` resolves the target, reads the current control value via `locator.input_value()` with a `value`-attribute fallback, normalizes missing values to `""`, and compares with strict equality.
- Failed strict assertions raise `AssertionError` with the resolved locator plus readable `Expected` and `Actual` values.

---

## 🐾 Chaos Chamber Verified (2868 Tests)

The engine is battle-tested with **2868** synthetic DOM/unit tests across 52 test suites covering the web's most annoying UI patterns — including iframe routing, DOMScorer weight hierarchies, TreeWalker filtering, visibility edge cases, attribute-semantic icon matching, camelCase developer attributes, and contextual UI disambiguation across repeated controls.

* **Synthetic DOM packs:** scenario suites under `manul_engine/test/`.
* **Controls cache regression suite:** `manul_engine/test/test_13_controls_cache.py`.
* **AI modes regression suite:** `manul_engine/test/test_12_ai_modes.py`.
* **QA Classics regression suite:** `manul_engine/test/test_14_qa_classics.py`.
* **Custom Controls unit suite:** `manul_engine/test/test_19_custom_controls.py`.
* **Static Variables unit suite:** `manul_engine/test/test_20_variables.py`.
* **Dynamic Variables unit suite:** `manul_engine/test/test_21_dynamic_vars.py`.
* **Tags unit suite:** `manul_engine/test/test_22_tags.py`.
* **Advanced interactions unit suite:** `manul_engine/test/test_23_advanced_interactions.py`.
* **Reporting unit suite:** `manul_engine/test/test_24_reporting.py`.
* **HTML reporter unit suite:** `manul_engine/test/test_25_reporter.py`.
* **Wikipedia Search Input unit suite:** `manul_engine/test/test_26_wikipedia_search.py`.
* **Lifecycle Hooks unit suite:** `manul_engine/test/test_27_lifecycle_hooks.py`.
* **Logical Steps unit suite:** `manul_engine/test/test_28_logical_steps.py`.
* **iframe Routing synthetic suite:** `manul_engine/test/test_29_iframe_routing.py`.
* **Heuristic Weights synthetic+unit suite:** `manul_engine/test/test_30_heuristic_weights.py`.
* **Visibility & TreeWalker synthetic+unit suite:** `manul_engine/test/test_31_visibility_treewalker.py`.
* **VERIFY ENABLED/DISABLED synthetic suite:** `manul_engine/test/test_32_verify_enabled.py`.
* **CALL PYTHON with arguments unit suite:** `manul_engine/test/test_33_call_python_args.py`.
* **VERIFY checked/NOT checked synthetic suite:** `manul_engine/test/test_34_verify_checked.py`.
* **Smart Page Scanner synthetic+unit suite:** `manul_engine/test/test_35_scanner.py`.
* **Scoring Math unit suite:** `manul_engine/test/test_36_scoring_math.py`.
* **Enterprise DSL unit suite:** `manul_engine/test/test_37_enterprise_dsl.py`.
* **SET & Indentation unit suite:** `manul_engine/test/test_38_set_and_indent.py`.
* **OPEN APP unit suite:** `manul_engine/test/test_39_open_app.py`.
* **Self-Healing Cache unit suite:** `manul_engine/test/test_40_self_healing_cache.py`.
* **Recorder unit suite:** `manul_engine/test/test_41_recorder.py`.
* **Scheduler unit suite:** `manul_engine/test/test_42_scheduler.py`.
* **Scoped Variables unit suite:** `manul_engine/test/test_43_scoped_variables.py`.
* **Explain Mode unit suite:** `manul_engine/test/test_44_explain_mode.py`.
* **Public Python API unit suite:** `manul_engine/test/test_45_api.py`.
* **Attribute-semantic heuristic suite:** `manul_engine/test/test_46_attribute_semantic.py`.
* **Contextual navigator unit suite:** `manul_engine/test/test_47_contextual_proximity.py`.
* **Prompts & Config unit suite:** `manul_engine/test/test_48_prompts_config.py`.
* **Imports unit suite:** `manul_engine/test/test_50_imports.py`.
* **Packager unit suite:** `manul_engine/test/test_51_packager.py`.
* **Exports unit suite:** `manul_engine/test/test_52_exports.py`.
* **Integration hunts:** Real-site E2E flows under `demo/tests/*.hunt` — run with `python demo/run_demo.py` (requires Playwright + network).

Run the synthetic suite:

```bash
# From repo root (dev mode)
python run_tests.py

# Heuristics-only (no Ollama), deterministic:
# Set "model": null in manul_engine_configuration.json
python run_tests.py
```

---

## 🤖 LLM Prompts for Hunt File Generation

The `prompts/` directory contains ready-to-use LLM prompt templates that let you generate complete `.hunt` test files automatically.

| File | Purpose |
|---|---|
| `prompts/html_to_hunt.md` | Paste HTML → get hunt steps |
| `prompts/description_to_hunt.md` | Describe a flow in plain text → get hunt steps |
| `prompts/README.md` | Full usage guide for all LLM clients |

The default prompt templates now also teach contextual disambiguation syntax for repeated controls:

- `NEAR 'Anchor'`
- `ON HEADER`
- `ON FOOTER`
- `INSIDE 'Container' row with 'Text'`

### Usage options

**GitHub Copilot Chat (VS Code)**
- Attach `prompts/html_to_hunt.md` via the paperclip icon, paste HTML in the message.
- Or use `#file:prompts/html_to_hunt.md` reference inline in the chat.
- Or open a blank `.hunt` file, press `Ctrl+I`, and reference the prompt file.

**ChatGPT / Claude (web):** Copy the entire prompt file, replace the `<!-- PASTE ... HERE -->` placeholder, send.

**API (Python):** Use the prompt file content as the `system` message and your HTML/description as the `user` message.

**Ollama (local):** `cat prompts/html_to_hunt.md mypage.html | ollama run qwen2.5:7b`

---

## 🖱️ Manul Engine Extension

The companion Manul Engine Extension for VS Code is published separately from this runtime repository. Normal installation should use the published Marketplace build.

Marketplace page:

- https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine

Install from VS Code or via CLI:

```bash
code --install-extension manul-engine.manul-engine
```

The published extension provides:

| Feature | Details |
| --- | --- |
| **Hunt language support** | Syntax highlighting, bracket matching, and comment toggling for `.hunt` files |
| **Test Explorer integration** | Hunt files appear in VS Code's native Test Explorer; **real-time** step-level pass/fail reporting while the hunt is running |
| **Config sidebar** | Webview panel to edit `manul_engine_configuration.json` visually; **Workers** combobox; **Add Default Prompts** button; live Ollama model discovery via `localhost:11434` |
| **Cache browser** | Tree-view sidebar showing the controls cache hierarchy (`site → page → controls.json`) |
| **Run commands** | `ManulEngine: Run Hunt File` (output panel) and `ManulEngine: Run Hunt File in Terminal` (raw CLI) |
| **Debug run profile** | Test Explorer exposes a **Debug** run profile alongside the normal one; places gutter breakpoints (red dots) in `.hunt` files, pauses at each with a floating QuickPick overlay — **⏭ Next Step** / **▶ Continue All**. The Test Explorer **Stop** button aborts the run cleanly. |
| **Step Builder** | Sidebar buttons for every step type including **Open App**, **Set Variable**, **Verify Softly**, **Verify Visual**, **Mock Request**, **Wait Response**, **Wait Visible / Hidden**, **Debug / Pause**, **CALL PYTHON into {var}**, and **Live Page Scanner** |
| **Explain Heuristics CodeLens** | CodeLens above actionable steps that runs the file with `--explain` and streams the scoring breakdown to a dedicated output channel |
| **Bounded concurrency** | Test Explorer respects `workers` config or `manulEngine.workers` VS Code setting |

### Extension behaviour notes

* **Working directory:** The extension spawns `manul` with `cwd` set to the **VS Code workspace folder root**.
* **Debug protocol:** `runHuntFileDebugPanel` spawns `manul` with `--break-lines` and piped stdio. Python emits the debug pause marker; TypeScript replies with step-control commands.
* **Auto-annotate:** When `auto_annotate` is enabled, the engine inserts or overwrites `# 📍 Auto-Nav:` comments above steps that follow a URL change.
* **`pages.json` format:** Nested two-level dict — `{ "site_root_url": { "Domain": "display name", "regex_or_exact_url": "Page Name", ... } }`.
* **`ai_always` guard:** The config panel forces `ai_always` to `false` when no model is selected.
* **Ollama discovery:** On panel open the extension fetches `http://localhost:11434/api/tags` and populates a `<select>` with installed model names when available.

---

## 🔖 Version Bump

The repository ships `bump_version.py` at the project root. It reads the canonical version from `pyproject.toml` and updates **every** file that embeds the version string (34 occurrences across 18 files).

```bash
python bump_version.py 0.0.9.28 --dry-run   # preview changes (no files written)
python bump_version.py 0.0.9.28             # apply to all files
python bump_version.py --show                # print current version
```

Covered files: `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `README.md`, `README_DEV.md`, `.cursorrules`, `.github/copilot-instructions.md`, custom-instructions mirror, all 8 contracts, and CI workflows.

> **Rule:** never edit version strings by hand — always use `bump_version.py` to keep all files in sync.

---

## Release Notes: v0.0.9.27

- **What-If Analysis REPL (`ExplainNextDebugger`):** New `explain_next.py` module with interactive debug REPL for hypothetical step evaluation. During a debug pause, type `w` (terminal) to enter the REPL or `e` / send `explain-next` (extension protocol) for one-shot evaluation. Combines DOMScorer heuristic scoring with optional LLM analysis to produce a 0–10 confidence rating, element match info, risk assessment, and corrective suggestions. The best heuristic match is highlighted with a persistent magenta outline on the live page via the engine's `_debug_highlight` / `_clear_debug_highlight` methods. Classes: `PageContext` (read-only snapshot), `WhatIfResult` (structured result with `confidence_label` property and `format_report()`), `_HeuristicHit` (best candidate from scoring), `ExplainNextDebugger` (REPL controller). REPL commands: `!execute [N]`, `!history`, `!context`, `!quit`. Extension protocol: `explain-next` token emits `\x00MANUL_EXPLAIN_NEXT\x00{json}` marker with serialized `WhatIfResult` via `_result_to_dict()`; the `what-if` interactive REPL is disabled in extension protocol mode (stdin reserved for control tokens). Hooked into `debug.py` via `_get_explain_next()` lazy factory and `_what_if_execute_step` attribute in `core.py`. 112-assertion test suite (`test_53_explain_next.py`).
- **What-If execute bug fixes:** `_execute_step()` recursive call for What-If replacement now passes `strategic_context` and `step_idx` by keyword (was misordered as positional args, breaking debug/breakpoint behavior). Injected What-If steps in `core.py` now run through `substitute_memory()` so `{var}` placeholders are resolved before execution.
- **LLM JSON fence-stripping:** `_parse_llm_json()` in `llm.py` now strips markdown code fences (```` ``` ````) before JSON parsing, improving robustness with models that wrap JSON responses in triple-backtick blocks.

<details>
<summary>v0.0.9.26</summary>

- **`EngineConfig` frozen dataclass:** New `config.py` module with injectable `EngineConfig` replacing module-level globals. `ManulEngine.__init__` accepts an optional `config` parameter; all runtime settings are stored as instance attributes. `validate()` method checks invariants (browser enum, screenshot mode, channel+chromium compat, non-negative timeouts/retries, ai_always requires model).
- **Structured exception hierarchy:** New `exceptions.py` with `ManulEngineError` base class and 7 concrete subclasses (`ConfigurationError`, `ElementResolutionError`, `HookExecutionError`, `HuntImportError`, `VerificationError`, `SessionError`, `ScheduleError`). Multi-inheritance preserves backward compatibility. All exceptions re-exported from `__init__.py`.
- **Shared type definitions:** New `_types.py` with `ElementSnapshot` TypedDict describing the shape of element dicts returned by `SNAPSHOT_JS`. Used with `TYPE_CHECKING` imports in core, actions, and scoring.
- **Thread safety:** `controls.py` wraps registry access with `_REGISTRY_LOCK`; `hooks.py` wraps `_module_cache` access with `_CACHE_LOCK`.
- **Import depth guard:** `resolve_imports()` enforces `_MAX_IMPORT_DEPTH=10` to prevent runaway recursive imports.
- **Scoring early exit:** `DOMScorer.score_all()` accepts `early_exit_score` parameter — skips remaining elements when threshold is exceeded (not active in explain mode).
- **CALL PYTHON timeout warning:** `execute_hook_line()` warns when a function takes longer than 30 seconds.
- **Static analysis:** Ruff + mypy config in `pyproject.toml`; new `lint.yml` CI workflow gates on `ruff check` + `ruff format --check`; lint gate added to `release.yml`.
- **Dependabot:** `.github/dependabot.yml` for automated pip + github-actions dependency updates (weekly).
- **ADR documents:** `docs/adr/` with 4 Architecture Decision Records (mixin pattern, custom test runner, TreeWalker snapshot, heuristics-first resolution).
- **`run_mission()` decomposition:** Extracted `_launch_browser()` and `_parse_task()` from the 400-line `run_mission()` method.
- **Demo directory restructure:** All integration hunts, scripts, controls, benchmarks, and pages.json moved to `demo/`. New `demo/run_demo.py` runner. Synthetic test suite extracted to standalone `run_tests.py`.
- **Security hygiene:** Eliminated false-positive "shell access" alert from package security scanners (socket.dev).

</details>

**Version:** 0.0.9.27

**Codename:** Containerised Manul

**Status:** Hunting...