
# Copilot Instructions — ManulEngine

## GLOBAL DOC SYNC RULE

> **CRITICAL — Read this first.**
> Whenever the user asks to update documentation, a README, or a feature's description, you **MUST** automatically update the repo-local core files to keep the project's positioning and syntax rules perfectly synchronised:
> 1. `README.md` — public-facing feature docs and version footer
> 2. `README_DEV.md` — internal architecture docs and version title/footer
> 3. `.github/copilot-instructions.md` — AI training context and syntax rules
> 4. `.cursorrules` — repo-local assistant guidance, pinned version examples, and install commands
>
> A feature that appears in one file but not the others is a documentation bug.
> This `.github/copilot-instructions.md` file is the single canonical source of Copilot/LLM instructions for this repository. Any mirrored copies used by tooling or templates must reference this file or be kept byte-for-byte in sync as generated artifacts.
> If the same change also affects the companion Manul Engine Extension for VS Code's Marketplace listing or release notes, update those in the separate extension repository when that repo is part of the task.

## SOLO DEV ALPHA POSITIONING

> **CRITICAL — Read this first.**
> In this repository, ManulEngine should be documented as a solo-developed alpha-stage runtime with a companion Manul Engine Extension for VS Code. Manul Studio, when mentioned, is a separate repository rather than the IDE surface of this one.
> Never imply guarantees of stability, maturity, support, or production-readiness.
> When project status is relevant, be explicit that bugs are expected, APIs may change, and the project is meant for exploration and technical feedback rather than production CI/CD promises.

## AI Identity Directive

**CRITICAL — Read this first.**
ManulEngine is a **deterministic, DSL-first Web & Desktop Automation Runtime**. It is NOT an AI-first tool, and it is NOT limited to E2E testing. When generating scripts, answering questions, or suggesting solutions:

1. **Prioritise deterministic actions.** Always default to the plain-English DSL (`CLICK`, `FILL`, `VERIFY`, `NAVIGATE`, `EXTRACT`, `PRESS`, etc.) and the built-in `DOMScorer` heuristics. These are the primary resolution mechanism.
2. **Do not overly rely on the LLM fallback mechanism.** ManulEngine is designed around deterministic `TreeWalker` + `0.0–1.0` float heuristic scoring. The LLM is a last-resort safety net for genuinely ambiguous elements — not a default path, and not a basis for stability promises.
3. **Understand the Dual Persona Workflow.** Manual QA writes plain English `.hunt` DSL — no code required. SDETs extend the same files with Python hooks (`[SETUP]`/`[TEARDOWN]`, `CALL PYTHON`, `@before_all`/`@after_all`), Custom Controls (`@custom_control`), and data-driven parameters (`@data:`). Both personas work on the same artifact.
4. **When suggesting config**, always recommend `"model": null` (heuristics-only) as the default. Only suggest enabling an Ollama model when the user explicitly needs AI self-healing.
5. **Never describe ManulEngine as "AI-powered" or "neuro-symbolic".** The correct framing is: "a deterministic, DSL-first Web & Desktop Automation Runtime backed by Playwright, with optional local AI for self-healing."
6. **Understand the four automation pillars.** ManulEngine scripts (`.hunt` files) can serve as QA/E2E tests, RPA workflows, synthetic monitors, or AI-agent execution targets. The same DSL commands (`NAVIGATE`, `CLICK`, `FILL`, `EXTRACT`, `VERIFY`, `CALL PYTHON`, etc.) apply to all four use cases. When generating `.hunt` files, adapt the structure to the user's intent — a monitoring script may skip `VERIFY` in favour of `EXTRACT`; an RPA script may use `CALL PYTHON` extensively for data processing; an AI-agent script should use strict DSL commands (never raw Playwright calls) for safety.
7. **When updating public docs, keep the runtime-reference layer intact.** README.md is not only a landing page. It should retain concrete sections for explainability layers, configuration surface, automation pillars, desktop automation, hooks/variables orchestration, and test/benchmark coverage.
8. **When documenting the companion Manul Engine Extension for VS Code for end users, prefer the published Marketplace install path.** Do not default public docs to local extension build instructions unless the user explicitly asks about extension development.
9. **For public README assets, use absolute URLs.** If an image or badge must render on PyPI or other package indexes, use an absolute GitHub raw URL rather than a relative repository path like `images/foo.png`.

## What is this project?

ManulEngine is a deterministic, DSL-first Web & Desktop Automation Runtime.
It acts as an interpreter for the `.hunt` DSL — a Playwright-backed engine that can run E2E tests, RPA workflows, synthetic monitors, and AI-agent actions.
It drives Chromium (and optionally Firefox or WebKit) via Playwright, resolves DOM elements with a mathematically sound `DOMScorer` (normalised 0.0–1.0 float scoring across 20+ heuristic signals and a native JavaScript `TreeWalker`),
and optionally falls back to a local LLM (Ollama) as a self-healing safety net when the heuristics are genuinely ambiguous.
It also supports desktop app automation via Electron (`executable_path` + `OPEN APP` command).
It is designed to bypass modern web traps (Shadow DOM, invisible overlays, zero-pixel honeypots, custom dropdowns) entirely locally — no cloud APIs.

The architecture is: `Hunt DSL` → `Parser` → `Execution Engine` → `Controls/Python Hooks` → `Playwright`. This makes ManulEngine a true runtime rather than just a test library — the same engine executes QA suites, RPA automations, cron-scheduled monitors, and constrained AI-agent scripts identically.

Current operating mode in this repo is typically **heuristics-only** (recommended default):
- The `DOMScorer` and `TreeWalker` handle element resolution deterministically.
- LLM is called only when explicitly enabled AND heuristics confidence is below `MANUL_AI_THRESHOLD`.
- When LLM is used, heuristic `score` is treated as a *prior* (hint), not a hard constraint (`MANUL_AI_POLICY=prior`).
- If `model` is `null` or not set (the default), the engine runs in **heuristics-only mode** (AI fully disabled, threshold = 0).

**Stack:** Python 3.11 · Playwright async · Ollama (qwen2.5:0.5b, optional) · stdlib only (no dotenv)

## Repository layout

```text
manul.py                   Dev CLI entry point (run hunts from repo root without install)
run_tests.py               Synthetic DOM test suite runner (dev only)
bump_version.py            Version bumper — updates all 18 files from pyproject.toml
manul_engine_configuration.json  Project configuration (JSON, replaces .env)
pyproject.toml             Build config — package name: manul-engine, version: 0.0.9.27
manul_engine/
  __init__.py              public API — re-exports ManulEngine, ManulSession, EngineConfig, all exception classes
  exceptions.py            Structured exception hierarchy (ManulEngineError base, ConfigurationError, ElementResolutionError, HookExecutionError, HuntImportError, VerificationError, SessionError, ScheduleError)
  _types.py                Shared type definitions — ElementSnapshot TypedDict used across scoring, core, actions
  api.py                   ManulSession — public Python API facade (async context manager, Playwright lifecycle)
  config.py                EngineConfig frozen dataclass — injectable configuration (replaces module-global reads); validate() method checks invariants
  core.py                  ManulEngine class (resolution, run_mission, self-healing)
  cache.py                 _ControlsCacheMixin (persistent per-site controls cache)
  debug.py                 _DebugMixin (element highlighting, debug prompt, breakpoint protocol, What-If REPL integration)
  explain_next.py          ExplainNextDebugger — interactive What-If Analysis REPL (PageContext, WhatIfResult, heuristic pre-check, LLM dry-run)
  llm.py                   LLMProvider protocol + OllamaProvider / NullProvider (JSON fence-stripping)
  logging_config.py        Centralized logging under ``manul_engine`` hierarchy (stderr, MANUL_LOG_LEVEL)
  actions.py               _ActionsMixin (navigate, scroll, explicit waits, extract, verify, drag, press, right_click, upload, _execute_step, scan_page)
  reporting.py             StepResult, BlockResult, MissionResult, RunSummary dataclasses; append_run_history() + report-session persistence (reports/run_history.json, reports/manul_report_state.json)
  reporter.py              Self-contained HTML report generator (dark theme, native <details>/<summary> accordions, Flexbox step layout, base64 screenshots, control panel with Show Only Failed toggle, tag filter chips, Run Session banner)
  prompts.py               JSON config loader, thresholds, LLM prompt templates
  scoring.py               DOMScorer class — normalised 0.0–1.0 float scoring, WEIGHTS dict, SCALE=177,778, pre-compiled regex, score_elements() backward-compatible API
  js_scripts.py            All JS injected into the browser (TreeWalker-based SNAPSHOT_JS with PRUNE set, SCAN_JS)
  scanner.py               Smart Page Scanner — scan_page(), build_hunt(), scan_main()
  helpers.py               HuntBlock, parse_hunt_blocks(), substitute_memory(), extract_quoted(), env_bool(), detect_mode(), classify_step(), timing constants
  cli.py                   Public installed CLI entry point (manul command + manul scan + manul record + manul daemon subcommands); ParsedHunt NamedTuple
  controls.py              Custom Controls registry (@custom_control, get_custom_control, load_custom_controls); thread-safe _REGISTRY_LOCK
  hooks.py                 [SETUP] / [TEARDOWN] hook parser and executor; thread-safe _CACHE_LOCK; 30s CALL PYTHON timeout warning
  lifecycle.py             Global Lifecycle Hook Registry (@before_all, @after_all, @before_group, @after_group, GlobalContext, load_hooks_file)
  recorder.py              Semantic Test Recorder — JS injection, Python bridge, DSL generator
  scheduler.py             Built-in Scheduler — parse_schedule(), Schedule dataclass, next_run_delay(), daemon_main()
  variables.py             ScopedVariables — 5-level variable hierarchy (row, step, mission, global, import)
  imports.py               @import/@export/USE system — parse_import_directive(), resolve_imports(), expand_use_directives(), validate_exports(); _MAX_IMPORT_DEPTH=10 guard
  packager.py              Pack/install .huntlib archives — pack(), install(), _update_lockfile(), resolve_lockfile()
  _test_runner.py          Dev-only synthetic test runner (not in public CLI)
  test/
    test_00_engine.py       synthetic DOM micro-suite (local HTML via Playwright)
    test_01_ecommerce.py    synthetic DOM scenario pack
    ...
    test_15_facebook_final_boss.py
    test_16_hooks.py        [SETUP]/[TEARDOWN] unit tests (56 assertions, no browser)
    test_17_frontend_hell.py   frontend anti-patterns (overlays, z-index traps, React portals)
    test_18_disambiguation.py  ambiguous element targeting
    test_19_custom_controls.py Custom Controls registry + engine interception (28 assertions, no browser)
    test_20_variables.py       @var: static variable declaration + @script alias parsing (23 assertions, no browser)
    test_21_dynamic_vars.py    CALL PYTHON ... into {var} dynamic variable capture
    test_22_tags.py            @tags: / --tags CLI filter (20 assertions, no browser)
    test_23_advanced_interactions.py  PRESS/RIGHT CLICK/UPLOAD/explicit wait commands (58 assertions, no browser)
    test_24_reporting.py       StepResult/MissionResult/RunSummary dataclasses (67 assertions)
    test_25_reporter.py        HTML report generator (70 assertions, no browser)
    test_26_wikipedia_search.py  name_attr heuristic scoring (20 assertions, no browser)
    test_27_lifecycle_hooks.py   Global Lifecycle Hook system (57 assertions, no browser)
    test_28_logical_steps.py     Logical STEP ordering and parser (58 assertions, no browser)
    test_29_iframe_routing.py    Cross-frame element resolution (25 assertions)
    test_30_heuristic_weights.py DOMScorer priority hierarchy (32 assertions)
    test_31_visibility_treewalker.py TreeWalker PRUNE/checkVisibility (20 assertions)
    test_32_verify_enabled.py    VERIFY ENABLED/DISABLED state verification (20 assertions)
    test_33_call_python_args.py  CALL PYTHON with positional arguments + unresolved @script alias handling (50 assertions, no browser)
    test_34_verify_checked.py    VERIFY checked/NOT checked state verification (20 assertions, no browser)
    test_35_scanner.py           Smart Page Scanner build_hunt() (44 assertions, no browser)
    test_36_scoring_math.py      Exact numerical scoring validation (29 assertions, no browser)
    test_37_enterprise_dsl.py    Enterprise DSL: @data:, MOCK, VERIFY VISUAL/SOFTLY, explicit waits, reporter warnings (75 assertions, no browser)
    test_38_set_and_indent.py    SET command & indentation robustness (v0.0.9.2)
    test_39_open_app.py          OPEN APP command — classify_step, _handle_open_app (41 assertions, no browser)
    test_40_self_healing_cache.py Self-Healing Controls Cache (16 assertions)
    test_41_recorder.py          Semantic Test Recorder JS bridge + DSL generator + step aggregation (no browser)
    test_42_scheduler.py         Built-in Scheduler — parse_schedule, next_run_delay, ParsedHunt integration (51 assertions, no browser)
    test_43_scoped_variables.py  ScopedVariables 5-level hierarchy, scope isolation, dict compat (44 assertions, no browser)
    test_44_explain_mode.py      DOMScorer explain output, channel breakdown, --explain CLI flag (33 assertions, no browser)
    test_45_api.py               ManulSession public Python API facade (50 assertions, no browser)
    test_46_attribute_semantic.py Attribute-semantic icon matching, camelCase dev attrs, cart badges, false-positive resistance (34 assertions, no browser)
    test_47_contextual_proximity.py Contextual NEAR / HEADER / FOOTER / INSIDE scoring and parser coverage (67 assertions, no browser)
    test_48_prompts_config.py  Configuration loading, threshold derivation, page-name lookup, _KEY_MAP, env_bool (83 assertions, no browser)
    test_50_imports.py         @import/@export/USE directive system (84 assertions, no browser)
    test_51_packager.py        Pack/install .huntlib archives and lockfile (21 assertions, no browser)
    test_52_exports.py         @export validation, wildcard exports, access control (19 assertions, no browser)
    test_53_explain_next.py   ExplainNextDebugger What-If Analysis REPL + debug protocol (112 assertions, no browser)
demo/
  run_demo.py              Runner script for integration hunts (sets CWD, calls manul CLI)
  manul_engine_configuration.json  Demo-specific config (heuristics-only)
  pages.json               Page-name registry for demo sites
  tests/
    saucedemo.hunt         integration: login, inventory, cart (saucedemo.com)
    demoqa.hunt            integration: forms, checkboxes, radios, tables (demoqa.com)
    mega.hunt              integration: all element types, drag-drop, shadow DOM
    rahul.hunt             integration: radios, autocomplete, hover
    call_python_variants.hunt  integration: all CALL PYTHON variants (hooks, aliases, args)
  scripts/                 Python helpers used by call_python_variants.hunt
  controls/                Educational @custom_control examples
  examples/                Additional Python helpers for CALL PYTHON demos
  playground/              Experimental nested-module demos
  benchmarks/              Adversarial benchmark suite (12 tasks, 5 HTML fixtures)
docs/
  adr/                     Architecture Decision Records (ADR-001 through ADR-004)
contracts/
  MANUL_API_CONTRACT.md    Machine-readable contract: ManulSession Python API
  MANUL_CLI_CONTRACT.md    Machine-readable contract: CLI interface
  MANUL_CONFIG_CONTRACT.md Machine-readable contract: configuration surface
  MANUL_DSL_CONTRACT.md    Machine-readable contract: .hunt DSL commands
  MANUL_HOOKS_CONTRACT.md  Machine-readable contract: hooks & lifecycle
  MANUL_REPORTING_CONTRACT.md Machine-readable contract: reporting pipeline
  MANUL_SCORING_CONTRACT.md  Machine-readable contract: DOMScorer heuristics
Dockerfile                 Multi-stage CI/CD runner image (ghcr.io/alexbeatnik/manul-engine)
.dockerignore              Build-context exclusions for Docker
docker-compose.yml         Local dev/CI compose: manul, manul-daemon services
.github/workflows/
  synthetic-tests.yml      PR quality gate (synthetic test suite)
  lint.yml                 Ruff lint + format check on PR and push to main
  release.yml              Unified release: PyPI + GHCR + GitHub Release on v* tag (includes lint gate)
  docker-dev.yml           Dev Docker image on main push (amd64-only)
  manul-ci.yml             Reusable example workflow for downstream repos
.github/dependabot.yml     Automated dependency updates (pip + github-actions, weekly)
```

## How the engine works

1. **Snapshot** — `SNAPSHOT_JS` walks the DOM with `document.createTreeWalker()` and a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`). Visibility is checked via `checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })` with `offsetWidth/offsetHeight` fallback. Hidden checkbox/radio/file inputs are kept (special-input exception). `_snapshot()` iterates `page.frames`, injects the script per frame, and tags each element with `frame_index`.
2. **Exact-match pass** — quick filter by `name`, `aria-label`, `data-qa` substring.
3. **Heuristic scoring** — `DOMScorer.score_all()` ranks candidates using normalised `0.0–1.0` floats across five weighted channels: `cache` (2.0), `semantics` (0.60), `text` (0.45), `attributes` (0.25), `proximity` (0.10). Final score = weighted sum × penalty multiplier × `SCALE` (177,778). The biggest single boosts are semantic cache reuse (+1.0 cache / 200k+ scaled) and `data-qa` exact match (+1.0 text / ~80k scaled). Penalties: disabled ×0.0, hidden ×0.1.
  When a contextual qualifier is active, the proximity channel weight is raised to `1.5` and switches from DOM-depth reuse to one of: Euclidean anchor distance (`NEAR`), viewport/ancestor routing (`ON HEADER` / `ON FOOTER`), or subtree membership (`INSIDE`).
4. **LLM fallback** — if best score < threshold, ask the LLM to pick the element.
5. **AI Rejection & Anti-phantom guard** — LLM can return `{"id": null}` if no plausible target is found. Engine handles `null` by blacklisting the current candidates and triggering self-healing.
6. **Action** — type / click / select / hover / drag. Non-shadow interactions primarily use Playwright with `force=True` plus retries; Shadow DOM interactions use a **JS fallback** (`window.manulClick`, `window.manulType`) to bypass elements that Playwright cannot target.
7. **Self-healing** — on failure or AI rejection, scroll down, blacklist bad IDs, and retry (up to 3 retries). Each element-resolution attempt may also scroll-and-retry internally.
8. **Persistent controls cache** — successful control resolutions are stored in a per-site folder with separate per-page subfolders (page-object style), each containing `controls.json`, and reused on later runs. Cached controls are reused only if a matching live candidate still exists in the current snapshot; changed controls overwrite previous entries for that URL page.

## Interaction modes

Detected from step keywords:

* `input` — "type", "fill", "enter"
* `clickable` — "click", "double", "check", "uncheck"
* `select` — "select", "choose"
* `hover` — "hover"
* `drag` — "drag" + "drop"
* `locate` — fallback (highlight only)

## Step format

Steps are parsed by `run_mission()` and must be atomic browser instructions. **STEP-grouped (unnumbered) is the canonical format for all new files.** The legacy numbered format is supported for backward compatibility, but the runtime now executes them as hierarchical blocks: `STEP` headers become parent containers and child actions beneath them execute with fail-fast semantics.

**STEP-grouped format — canonical (use this for all new files):**

```text
STEP 1: Navigate to the login page
NAVIGATE to https://example.com/login
VERIFY that 'Sign In' is present

STEP 2: Fill credentials
Fill 'Username' field with 'admin'
Fill 'Password' field with 'secret'
Click the 'Login' button
VERIFY that 'Welcome' is present.

STEP 3: Wrap up
EXTRACT the 'Product Price' into {price}
DONE.
```

**Numbered format — legacy (backward compat only, do not use for new files):**

```text
"1. NAVIGATE to https://example.com"
"2. Fill 'Username' field with 'admin'"
"3. Click the 'Login' button"
"4. VERIFY that 'Welcome' is present."
"5. DONE."
```

Rules for STEP-grouped files:
* `run_mission()` switches to line-by-line parsing when it detects **either** a `STEP` marker OR recognizable action keywords (NAVIGATE, VERIFY, DONE, etc.) in an unnumbered file. STEP markers are not required — a file containing only plain unnumbered action lines is parsed directly without them.
* Runtime grouping is performed by `parse_hunt_blocks()` in `helpers.py`, not by `parse_hunt_file()`. `parse_hunt_file()` still returns raw mission text plus metadata; `parse_hunt_blocks()` turns the mission into `HuntBlock` objects for execution.
* Each block starts with `[📦 BLOCK START] <STEP ...>` on stdout. Child actions emit `[▶️ ACTION START]`, then `[✅ ACTION PASS]` or `[❌ ACTION FAIL]`. Hard failures abort the rest of the block and emit `[🟥 BLOCK FAIL]`; complete success emits `[🟩 BLOCK PASS]`.
* `STEP [number]: [description]` — number is optional; description is used for console output and HTML report section headers.
* Blank lines between groups are allowed and ignored.
* All other keywords (NAVIGATE, VERIFY, DONE, etc.) work identically in both formats.
* Mixed numbered+STEP (e.g. `1. STEP 1: ...`) is also valid: the numbered split runs and STEP markers are detected by `classify_step()` as `"logical_step"` kind, same as in STEP-grouped mode.

**Contextual qualifiers for action steps:**
* Action steps may append `NEAR 'Anchor Text'` to bias resolution by Euclidean distance to a resolved anchor element.
* Action steps may append `ON HEADER` to prefer candidates in `header` / `nav` ancestry or the top 15% of the viewport.
* Action steps may append `ON FOOTER` to prefer candidates in `footer` ancestry or the bottom 15% of the viewport.
* Action steps may append `INSIDE 'Container' row with 'Text'` to resolve a matching row/container first and restrict candidate scoring to that subtree.
* These qualifiers are deterministic DSL syntax, not planner hints. They feed directly into `parse_contextual_hint()` in `helpers.py`, geometry exported by `SNAPSHOT_JS`, and contextual proximity scoring in `DOMScorer`.

**System Keywords** parsed directly by `run_mission()` (these skip heuristics):

* `NAVIGATE to [url]`
* `WAIT [seconds]`
* `Wait for "Text" to be visible` / `Wait for 'Spinner' to disappear` / `Wait for "Element" to be hidden` — Explicit wait step routed to Playwright `locator.wait_for()`. `disappear` maps to `hidden`.
* `PRESS ENTER`
* `PRESS [Key]` — Presses any key or combination globally (e.g. `PRESS Escape`, `PRESS Control+A`).
* `PRESS [Key] on [Target]` — Presses a key on a specific resolved element (e.g. `PRESS ArrowDown on 'Search Input'`).
* `RIGHT CLICK [Target]` — Right-clicks a resolved element to open a context menu.
* `UPLOAD 'File' to 'Target'` — Uploads a file to a file-input element. Path is resolved relative to the `.hunt` file's directory, then CWD. Both file path and target must be quoted.
* `SCROLL DOWN` or `SCROLL DOWN inside the list`
* `EXTRACT [target] into {variable_name}`
* `VERIFY that [target] is present` / `is NOT present` / `is DISABLED` / `is ENABLED` / `is checked`
* `Verify "element_name" [button|field|element|input] has text "Expected Text"` — resolves the target via heuristics, reads `locator.inner_text().strip()`, and asserts strict equality.
* `Verify "element_name" [button|field|element|input] has placeholder "Expected Placeholder"` — resolves the target, reads its `placeholder` attribute, and asserts strict equality.
* `Verify "element_name" [button|field|element|input] has value "Expected Value"` — resolves the target, reads its current value via `locator.input_value()` with a `value`-attribute fallback, normalizes missing values to an empty string, and asserts strict equality.
* `VERIFY VISUAL 'Element'` — Takes an element screenshot and compares against a baseline in `visual_baselines/`. Saves baseline on first run. Uses PIL/Pillow threshold comparison (default 1%) or raw byte fallback.
* `VERIFY SOFTLY that [target] is present` — Same as VERIFY but does **not** stop execution on failure. Failures are collected as soft errors and surfaced as `"warning"` status.
* `MOCK METHOD "url_pattern" with 'mock_file'` — Intercepts matching network requests via `page.route()` and fulfills from a local file. METHOD: GET, POST, PUT, PATCH, DELETE. Mock file resolved relative to hunt dir → CWD.
* `WAIT FOR RESPONSE "url_pattern"` — Blocks until a network response matching the URL pattern arrives (substring match via `page.wait_for_response()`). Uses `nav_timeout`.
* `SCAN PAGE` — scans the current page for interactive elements and prints a draft `.hunt` to the console.
* `SCAN PAGE into {filename}` — same, but also writes the draft to `{filename}`. Default output dir is `tests_home` from config.
* `SET {variable_name} = value` — Sets a runtime variable mid-flight. Both `{braced}` and bare key forms accepted. Quoted values (`'...'` / `"..."`) are auto-unquoted. The variable is immediately available for `{placeholder}` substitution in all subsequent steps.
* `DEBUG` / `PAUSE` — pauses execution at that step. In interactive terminal mode (`--debug`), draws a dashed red border around the resolved element and prompts the user; when run via VS Code extension, emits the debug pause protocol marker (see below).
* `DONE.`

Everything else goes through `_execute_step` (mode detection → resolve → action).
Optional steps contain "if exists" / "optional" **outside** the quoted target (e.g. `"Click 'Close Ad' if exists"`).

## Writing integration tests (hunt files)

Hunt files are plain-text test scenarios parsed by `parse_hunt_file()` (extracts `@context` / `@title` / `@tags`, strips `#` comments, collects hook blocks) then executed by `run_mission()`. **The STEP-grouped unnumbered format is the mandatory standard for all new hunt files.** The legacy numbered format is still supported but must not be used in new files.

### 1. File Naming & Location
* Hunt files can live in any directory. Pass a `.hunt` file or a directory path to `manul` to run them.
* You can also pass a specific `.hunt` file or a directory path to `manul.py` to run hunts from any location.
* Must use the `.hunt` extension. The filename can be anything — no prefix is required or enforced.

### 2. Metadata Headers
Placed at the top of the file. Used by the engine for logging and LLM context.
* `@context: [description]` — Strategic context passed to the engine.
* `@title: [short_title]` — Short title representing the test suite. `@blueprint:` is also accepted for backward compatibility.
* `@script: {alias} = package.module` or `@script: {callable_alias} = package.module.function` — File-local alias for later `CALL PYTHON {alias}.function` or `CALL PYTHON {callable_alias}` usage. The parser accepts dotted Python import paths only and rejects slash paths or `.py` suffixes.
* `@tags: tag1, tag2` — Arbitrary comma-separated run tags. Used with `manul --tags smoke path/` to filter which files execute.
* `@data: path/to/file.json` — Data-driven testing. Points to a JSON (array-of-objects) or CSV file. The engine loads each row and reruns the entire mission with row values injected as `{placeholders}`. Path resolved relative to hunt file directory, then CWD.
* `@schedule: <expression>` — Built-in scheduler header. Declares a schedule for the daemon mode (`manul daemon`). Supported expressions: `every N seconds/minutes/hours`, `every minute/hour`, `daily at HH:MM`, `every <weekday>`, `every <weekday> at HH:MM`. Parsed by `parse_schedule()` in `scheduler.py`. Files without `@schedule:` are ignored by the daemon.
* `@import: Block1, Block2 from source.hunt` — Imports named STEP blocks from another `.hunt` file. Supports named imports (`@import: Login, Logout from lib/auth.hunt`), wildcard (`@import: * from lib.hunt`), aliases (`@import: Login as AuthLogin from lib.hunt`), and package-style sources (`@import: Login from @my-lib`). Imported blocks are expanded inline via `USE` directives. `@var:` declarations from the source file are inherited at `LEVEL_IMPORT` (lowest priority).
* `@export: Block1, Block2` — Declares which STEP blocks are importable by other `.hunt` files. Multiple `@export:` lines are allowed. `@export: *` makes all blocks available. When no `@export:` is declared and a wildcard `@import: *` is used, all blocks are available (open by default).

### 3. Comments
* Use `#` at the beginning of a line for comments. Any line whose trimmed text starts with `#` is ignored during execution; `#` appearing after a step on the same line is treated as part of the step text, not a comment.

### 4. Step Formatting
**STEP-grouped (unnumbered) is the mandatory standard for all new hunt files.**
* Use `STEP N: label` headers to mark logical groups. The STEP number is optional (`STEP: label` is also valid).
* All action lines following a STEP header must be **plain, unnumbered text** — no `1.` prefix, no bullet points, no dashes.
* `run_mission()` detects `STEP` markers **or** recognizable action keywords (NAVIGATE, VERIFY, DONE, etc.) and automatically switches to line-by-line splitting. STEP markers are not required — a file with only plain unnumbered action lines is also parsed directly.
* Blank lines between groups are allowed and ignored.
* The classic numbered format (`1. CMD`, `2. CMD`, …) is still supported for backward compatibility, but numeric prefixes are stripped from the HTML report and must not be used when generating new files.
* Only genuinely free-form natural language with no recognized keywords is routed through the LLM planner (less deterministic; requires Ollama).
* Elements should be wrapped in single or double quotes for best heuristic matching (e.g., `'Submit'`, `"Password"`).

**ABSOLUTE RULE — Zero Tolerance:**
> When generating or suggesting `.hunt` files:
> 1. You MUST use the **Clean, Unnumbered DSL Syntax**. NEVER prepend numbers (`1. `, `2. `) to execution actions.
> 2. You MUST use **Logical `STEP` Grouping** (`STEP [optional number]: [Description]`) to structure E2E flows, matching manual QA test cases. These map perfectly to the Enterprise HTML Reporter's accordions.
> 3. You MUST use **4-space indentation** for all action lines under `STEP` headers; comments inside a `STEP` or hook block follow the same 4-space indentation. `STEP` headers themselves, metadata lines (`@context:`, `@var:`, `@script:`, `@tags:`, `@data:`, `@import:`, `@export:`), hook block markers (`[SETUP]`/`[TEARDOWN]`), top-level comments (`#` before the first `STEP`), and `DONE.` must remain flush-left (zero indentation). This matches the VS Code Auto-Formatter output (`Shift+Alt+F`).

### 5. System Keywords (parser-detected)
These keywords are detected via word-boundary regex, bypass heuristics, and are handled directly by the engine parser:
* `NAVIGATE to [url]` — Loads a URL and waits for DOM settlement.
* `OPEN APP` — Attaches to an Electron/Desktop app's default window instead of navigating to a URL. Use as the first step in `.hunt` files targeting `executable_path` apps. The handler checks `ctx.pages` for an existing window, falls back to `ctx.wait_for_event("page")`, waits for DOM settlement. Returns `(success, page)` — the `page` variable in `run_mission()` is reassigned.
* `WAIT [seconds]` — Hard sleep (e.g., `WAIT 2`).
* `Wait for "Text" to be visible` / `Wait for 'Spinner' to disappear` / `Wait for "Element" to be hidden` — Explicit wait syntax. The parser extracts the quoted target and desired state; `disappear` is treated as `hidden`, and execution goes through Playwright `locator.wait_for(state=...)` with the runtime timeout.
* `PRESS ENTER` — Presses the Enter key on the currently focused element (useful to submit forms after filling a field).
* `PRESS [Key]` — Presses any key or combination globally (e.g. `PRESS Escape`, `PRESS Control+A`). Mapped to `page.keyboard.press(key)`.
* `PRESS [Key] on [Target]` — Presses a key on a specific element resolved via heuristics (e.g. `PRESS ArrowDown on 'Search Input'`). Mapped to `locator.press(key)`.
* `RIGHT CLICK [Target]` — Right-clicks a resolved element (e.g. `RIGHT CLICK 'Context Menu Area'`). Mapped to `locator.click(button='right')`. Shadow DOM elements dispatch a JS `contextmenu` event.
* `UPLOAD 'File' to 'Target'` — Uploads a file to a file-input element (e.g. `UPLOAD 'avatar.png' to 'Profile Picture'`). Both file path and target must be quoted. File path is resolved relative to the `.hunt` file's directory first, then CWD. Mapped to `locator.set_input_files(path)`.
* `SCROLL DOWN` — Scrolls the main page down by one viewport height. `SCROLL DOWN inside the list` — scrolls the first dropdown-style scroll container (e.g., `#dropdown` or any element whose class name contains `dropdown`) all the way to the bottom (by setting `scrollTop = scrollHeight`). Phrases like `SCROLL DOWN to the very bottom` are accepted but currently behave the same as a single `SCROLL DOWN` on the main page (they do not auto-scroll the page all the way to the bottom).
* `EXTRACT [target] into {variable_name}` — Extracts text data into memory.
* `VERIFY that [target] is present` (or `is NOT present`, `is DISABLED`, `is ENABLED`, `is checked`)
* `VERIFY VISUAL 'Element'` — Takes an element screenshot and compares against a baseline in `visual_baselines/`. Saves baseline on first run. Uses PIL/Pillow threshold comparison (default 1%) or raw byte fallback.
* `VERIFY SOFTLY that [target] is present` — Same as VERIFY but does **not** stop execution on failure. Failures are collected as soft errors and surfaced as `"warning"` status.
* `MOCK METHOD "url_pattern" with 'mock_file'` — Intercepts matching network requests via `page.route()` and fulfills from a local file. METHOD: GET, POST, PUT, PATCH, DELETE. Mock file resolved relative to hunt dir → CWD.
* `WAIT FOR RESPONSE "url_pattern"` — Blocks until a network response matching the URL pattern arrives (substring match via `page.wait_for_response()`). Uses `nav_timeout`.
* `SCAN PAGE` — Runs `SCAN_JS` on the current page, maps results to hunt steps, prints a draft to console.
* `SCAN PAGE into {filename}` — Same, but also writes the draft to `{filename}`. Output defaults to `{tests_home}/draft.hunt` (reads `tests_home` from `manul_engine_configuration.json`).
* `SET {variable_name} = value` — Sets a runtime variable mid-flight. Both `{braced}` and bare key forms accepted. Quoted values are auto-unquoted. Available for `{placeholder}` substitution in subsequent steps.
* `USE BlockName` — Expands an imported STEP block inline at parse time. The block must have been imported via `@import:`. Aliased names (from `as` clause) are supported. Case-insensitive matching. Expanded actions replace the `USE` line in the mission body with synthetic line numbers (0).
* `DONE.` — Explicitly ends the mission.
* `[SETUP]` / `[END SETUP]` — Block wrapping `PRINT ...` and `CALL PYTHON ...` lines. Runs **before** the browser launches. If any line fails, the mission is marked as `broken` and browser steps are skipped.
* `[TEARDOWN]` / `[END TEARDOWN]` — Cleanup block. Runs in a `finally` block **after** the mission (pass or fail). Only executed if `[SETUP]` succeeded. Failure is logged but does not override the mission result.
* Inside hook blocks, each non-blank non-comment line must be either `PRINT "message with {vars}"` or `CALL PYTHON <module>.<function>` (optionally with positional arguments or `with args:` and optional `into {var}` capture — see Section 7b). `CALL PYTHON {alias}.function` and `CALL PYTHON {callable_alias}` are also valid when the file declares matching `@script:` aliases in the header. The module is resolved in this order: the `.hunt` file's directory → `CWD` → standard `importlib.import_module`. Target functions must be **synchronous**.
* **Inline `CALL PYTHON` steps** — `CALL PYTHON <module>.<function>` (with optional positional arguments) is also valid as a standard numbered step anywhere in the main mission body (outside hook blocks). It uses the identical module resolution, state isolation, and sync-only rules as hook blocks. A failure stops the mission immediately.

### 6. Interaction Actions (Parsed Modes)
If not a System Keyword, the engine detects the interaction mode based on verbs:
* **Clicking (`clickable`)**: `Click the 'Login' button`, `DOUBLE CLICK the 'Image'`, `Click on the 'Home' link`.
* **Typing (`input`)**: `Fill 'Email' field with 'test@manul.ai'`, `Type 'Search' into that field`.
* **Select/Dropdown (`select`)**: `Select 'Option 1' from the 'Menu' dropdown`.
* **Checkboxes/Radios (`clickable`)**: `Check the checkbox for 'Terms'`, `Uncheck the checkbox for 'Promo'`, `Click the radio button for 'Male'`.
* **Hovering (`hover`)**: `HOVER over the 'Menu'`.
* **Drag & Drop (`drag`)**: `Drag the element "Item" and drop it into "Box"`.
* **Locate (`locate`)**: `Locate the text input...` (highlights without acting).

### 7. Variables & Memory
Variables extracted using `EXTRACT` can be substituted in downstream steps.
* *Extract:* `EXTRACT the Price of 'Laptop' into {laptop_price}`
* *Reuse:* `VERIFY that '{laptop_price}' is present.`

### 7a. Static Variable Declaration (`@var:`)
Declare static test data at the top of the file using `@var: {key} = value`. These values are pre-populated into the engine's runtime memory before any step runs and can be interpolated exactly like `EXTRACT` variables.
* Both brace and bare-key forms are accepted: `@var: {email} = ...` and `@var: email = ...` are equivalent. Keys are stored without braces.
* Values may contain spaces and are stripped of leading/trailing whitespace.
* `@script:` follows the same declaration shape for Python helper aliases: `@script: {auth} = scripts.auth_helpers`, then `CALL PYTHON {auth}.issue_token into {token}`; or `@script: {issue_token} = scripts.auth_helpers.issue_token`, then `CALL PYTHON {issue_token} into {token}`.
* **MANDATORY rule for AI-generated hunt files:** When generating or suggesting `.hunt` test files, **NEVER hardcode test data** (emails, passwords, usernames, search queries, IDs, etc.) directly inside `Fill`, `Type`, or `Select` steps. **ALWAYS** declare them at the top using `@var:` and reference them via `{placeholder}` in the steps.
* **MANDATORY contextual rule for AI-generated hunt files:** When the user describes repeated controls, tables, cards, navbars, or footers, prefer contextual qualifiers (`NEAR`, `ON HEADER`, `ON FOOTER`, `INSIDE ... row with ...`) instead of inventing selectors or relying on vague prose.

Correct:
```text
@var: {user_email} = admin@example.com
@var: {password}   = secret123

STEP 1: Login
Fill 'Email' with '{user_email}'
Fill 'Password' with '{password}'
```

Wrong (do not do this):
```text
STEP 1: Login
Fill 'Email' with 'admin@example.com'
Fill 'Password' with 'secret123'
```

### 7b. Dynamic Variable Capture (`CALL PYTHON ... into {var}`)
`CALL PYTHON <module>.<function> [args...] into {variable_name}` captures the **return value** of the function as a string and stores it in the engine's runtime memory, available for `{placeholder}` substitution in all subsequent steps. The `to` keyword is accepted as an alias for `into`.
* The function must be **synchronous** and return any value; the engine calls `str()` on the result before storing it.
* **Positional arguments** can be passed after the dotted function name, before the optional `into {var}` clause. Arguments are tokenised with `shlex.split()` — single-quoted, double-quoted, and unquoted tokens are all accepted. `{var}` placeholders inside arguments are resolved from the engine's runtime memory (or the `parsed_vars`/`variables` dict for hook blocks).
* Calls without arguments remain fully backward-compatible — `CALL PYTHON mod.func` and `CALL PYTHON mod.func into {var}` work exactly as before.
* **MANDATORY rule for AI-generated hunt files:** Whenever a step needs data that comes from a backend call, API, OTP service, or any computed value, capture it with `CALL PYTHON ... into {var}` and reference the result via `{var}` in following steps. Never hardcode computed or runtime values directly in steps.

Full syntax variants:
```text
CALL PYTHON <module>.<function>
CALL PYTHON {alias}.<function>
CALL PYTHON {callable_alias}
CALL PYTHON <module>.<function> "arg1" 'arg2' {var}
CALL PYTHON <module>.<function> "arg1" {var} into {result}
CALL PYTHON <module>.<function> into {result}
```

Correct:
```text
3. CALL PYTHON helpers.api.get_otp "{email}" into {otp_code}
4. Fill 'OTP' field with '{otp_code}'
```

Wrong (do not do this):
```text
4. Fill 'OTP' field with '123456'
```

### 8. Best Practices
* **Specify Element Type:** Include words like `button`, `field`, `link`, `dropdown`, `checkbox`, `radio` outside quotes. This acts as a strong heuristic signal.
* **Exact Text Matching:** Put target texts in quotes (`'Save'`) to yield a high heuristic score.
* **Mandatory post-input guard:** After every generated `Fill` or `Type` step, immediately emit a strict value assertion using `Verify "{element_name}" field/input has value "{expected_value}"` before moving on to the next logical action.
* **Strict text/placeholder assertions:** When the user asks for exact text or placeholder validation, generate only `Verify "{element_name}" {type} has text "{expected_text}"` or `Verify "{element_name}" field/input has placeholder "{expected_placeholder}"`. Do not invent alternate assertion verbs.
* **Strict value assertions:** When the user asks for the current inputted value or textarea content, generate only `Verify "{element_name}" field/input has value "{expected_value}"`.
* **Verify After Actions:** Always use a `VERIFY` step after taking a significant action (e.g., login, form submit) before assuming the new page state.
* **Implicit Context:** The engine reuses context if you refer to previous elements implicitly, e.g., `Type "Password" into that field`.
* **MANDATORY — Reporting, Screenshots, and Retries are CLI/Execution concerns, NOT DSL syntax.** Never write steps like `RETRY 3`, `TAKE SCREENSHOT`, `GENERATE REPORT`, or similar in `.hunt` files. These features are controlled exclusively via CLI flags (`--retries`, `--screenshot`, `--html-report`), `manul_engine_configuration.json` keys (`retries`, `screenshot`, `html_report`), or VS Code Extension settings (`manulEngine.retries`, `manulEngine.screenshotMode`, `manulEngine.htmlReport`). When asked to add retries or reporting to a test, instruct the user to use CLI flags or config — never inject pseudo-steps into the hunt file.

### 9. Python Hooks (`[SETUP]` / `[TEARDOWN]`) and Inline `CALL PYTHON` Steps
Hook blocks run synchronous Python functions **outside the browser** — the primary use case is injecting database state or calling an API before the mission starts. Inline `CALL PYTHON` steps run **inside the mission** as numbered steps, with identical safety guarantees.
* When generating `.hunt` tests that require specific initial data (users, records, session tokens), **ALWAYS** use `[SETUP]` with `CALL PYTHON`. Never use brittle UI steps (e.g., "Click Create User") as test preconditions.
* Hook syntax is bracket-only. Do not invent `SETUP:` / `TEARDOWN:` aliases.
* **CRITICAL — Inline Python for mid-test backend interaction:** When a step requires interacting with a backend, database, or API mid-test — such as fetching an OTP, a magic link, a confirmation token, or triggering a backend job before a UI action — **DO NOT simulate it via the UI**. Use an inline `CALL PYTHON <module>.<func>` step directly in the numbered sequence. This is faster, more reliable, and immune to UI timing issues.
  ```text
  2. CLICK the 'Send OTP' button
  3. CALL PYTHON api_helpers.fetch_otp "{email}" into {otp}
  4. Fill 'OTP' field with '{otp}'
  ```
* `[TEARDOWN]` cleanup runs whether the mission passed or failed. Use it to delete test records and reset state.
* `PRINT "..."` is valid inside hook blocks and should be used for human-readable setup/cleanup logging.
* `CALL PYTHON ... with args: ...` is valid in both hook blocks and inline steps when you want explicit argument separation in examples.
* If a setup hook fails, the resulting mission status is `broken`, not `fail`.
* Target functions **must be synchronous**. Async callables are explicitly rejected with a descriptive error.
* Module resolution order: hunt file's directory → `CWD` → `sys.path`. `@script: {alias} = package.module` can alias a helper module for later `CALL PYTHON {alias}.func` usage, and `@script: {callable_alias} = package.module.function` can alias a specific helper callable for later `CALL PYTHON {callable_alias}` usage. `@script` values must be valid dotted Python import paths. Modules from the file-based scopes are executed in isolation — never inserted into `sys.modules` — preventing cross-test contamination.

## Code patterns to follow

* Import: `from manul_engine import ManulEngine` (never `engine` or `framework`). For the programmatic API: `from manul_engine import ManulSession`. For injectable configuration: `from manul_engine import EngineConfig`.
* `exceptions.py` owns the structured exception hierarchy: `ManulEngineError(Exception)` is the base class. Concrete exceptions: `ConfigurationError(ManulEngineError, ValueError)`, `ElementResolutionError(ManulEngineError)`, `HookExecutionError(ManulEngineError)`, `HuntImportError(ManulEngineError)`, `VerificationError(ManulEngineError)`, `SessionError(ManulEngineError, RuntimeError)`, `ScheduleError(ManulEngineError, ValueError)`. Multi-inheritance preserves backward compatibility with `except ValueError` / `except RuntimeError` in existing code. All exceptions are re-exported from `__init__.py`.
* `_types.py` owns shared type definitions. `ElementSnapshot` is a `TypedDict(total=False)` describing the shape of element dicts returned by `SNAPSHOT_JS`. Used with `TYPE_CHECKING` imports in `core.py`, `actions.py`, and `scoring.py` for IDE support and future type-checking.
* `config.py` owns `EngineConfig` — a frozen dataclass with 24 fields mirroring the JSON config surface. `EngineConfig.from_file(path)` loads JSON + env overlay. `ManulEngine.__init__` accepts an optional `config: EngineConfig` parameter; when provided, all settings are read from the config object instead of module-level globals. All runtime configuration (timeouts, AI settings, auto-annotate, etc.) is stored as instance attributes on `ManulEngine` — never read from `prompts.*` at call time. `validate()` method checks invariants: browser enum, screenshot mode, channel+chromium compat, non-negative timeouts/retries, ai_always requires model.
* `scoring.py` owns `DOMScorer` class — normalised `0.0–1.0` float scoring with five weighted channels (`WEIGHTS` dict: cache=2.0, text=0.45, attributes=0.25, semantics=0.60, proximity=0.10). `SCALE=177,778` maps the weighted float to integer thresholds expected by `core.py`. `score_elements()` is the backward-compatible entry point that delegates to `DOMScorer.score_all()`. Receives `learned_elements` and `last_xpath` as kwargs. Pre-compiled regex loaded at module import; per-element strings normalised in `_preprocess()`.
* **Safety first in `scoring.py`:** Always cast fetched attributes using `str(el.get("...", ""))`. JavaScript can pass objects (like `SVGAnimatedString` for SVG icons) instead of strings, which will crash Python's `.lower()`.
* **iframe routing in `core.py`:** `_snapshot()` iterates `page.frames`, evaluates `SNAPSHOT_JS` per frame, tags elements with `frame_index`. `_frame_for(page, el)` resolves the correct Playwright `Frame` by index with stale fallback to main frame. All 12+ locator call-sites in `actions.py` route through the resolved frame. Cross-origin frames are silently skipped (3-retry, 1.5s backoff on `closed` errors).
* **TreeWalker in `js_scripts.py`:** `SNAPSHOT_JS` uses `document.createTreeWalker()` with a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`). Visibility checked via `checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })` with `offsetWidth/offsetHeight` fallback. Hidden checkbox/radio/file inputs are kept (special-input exception). No `getComputedStyle` in the hot loop.
* `actions.py` is a **mixin** (`_ActionsMixin`) inherited by `ManulEngine` in `core.py`. Explicit waits live here as `_handle_wait_for_element()` and are executed as parser-level system steps rather than generic heuristic actions.
* **Input phrasing in `actions.py`:** steps containing `into` are parsed as value-first (`Type 'VALUE' into 'TARGET'`); `Fill ... with ...` and generic enter/fill phrasing remain value-last. Do not invert these forms when generating DSL.
* `cache.py` is a **mixin** (`_ControlsCacheMixin`) inherited by `ManulEngine` in `core.py`. It owns all persistent per-site controls-cache logic.
* `ManulEngine` MRO: `class ManulEngine(_DebugMixin, _ControlsCacheMixin, _ActionsMixin)` in `core.py`.
* `prompts.py` loads config from `manul_engine_configuration.json` (CWD first, then package root fallback). No dotenv dependency.
* `js_scripts.py` owns **all** JavaScript constants injected into the browser — no inline JS in Python files. This includes `SCAN_JS` (Smart Page Scanner).
* `scanner.py` owns the standalone scan logic: `SCAN_JS` is imported from `js_scripts.py`; `build_hunt()` maps raw element dicts to hunt steps; `scan_page()` is the async Playwright runner; `scan_main()` is the async CLI entry called by `cli.py`. `_default_output()` reads `tests_home` from the config to derive the default output path. `SCAN_JS.bestLabel()` should prefer associated checkbox/radio labels, and scan entries may include `manul_id` plus current non-empty values for fillable controls.
* `helpers.py` provides `HuntBlock`, `parse_hunt_blocks(task, file_lines=None)`, `env_bool(name, default)`, `detect_mode(step)`, and `classify_step(step)`. `parse_hunt_blocks()` is the runtime-level hierarchical parser that groups STEP headers into parent blocks and action lines into child lists while preserving block and action file lines for breakpoint mapping.
* **Null model = heuristics-only:** When `model` is `None`, `_llm_json()` returns `None` immediately. `get_threshold(None)` returns `0`. No Ollama calls are made.
* **`scan_main` must be `async`** — it is called with `await` from inside `cli.main()` which runs under `asyncio.run()`. Never use `asyncio.run()` inside `scan_main`.
* **Debug mode:** `ManulEngine(debug_mode=True, break_steps={N,...})`. `debug_mode=True` (from `--debug`) highlights the resolved element and pauses before every step using `input()` in TTY or Playwright's `page.pause()`. `break_steps` (from `--break-lines`) pauses only at listed step indices using the stdout/stdin panel protocol when stdout is not a TTY. The two are mutually exclusive in practice — the extension only ever sets `break_steps` via `--break-lines`.
* **Element highlight in debug mode:** When `debug_mode=True` (or a `break_steps` pause fires), the engine calls `highlight_element(page, locator)` which injects `<style id="manul-debug-style">` (once) and sets `data-manul-debug-highlight="true"` on the target element, producing a persistent 4px magenta outline + glow that stays until `clear_highlight(page)` is called just before the action executes. A separate `_highlight()` method draws a short 2-second flash (non-debug, `setTimeout` inside JS) for non-pausing visual feedback.
* `hooks.py` owns all `[SETUP]` / `[TEARDOWN]` parsing (`extract_hook_blocks()`) and execution (`execute_hook_line()`, `run_hooks()`). It also supports `PRINT`, optional `with args:` sugar, the fixed helper-module resolution order (`hunt dir -> CWD -> sys.path`), and `bind_hook_result()` for sharing scalar or dict-returned variables across hook lines and browser steps. `_module_cache` is a module-level `dict[str, ModuleType]` that caches resolved modules by absolute file path (JIT loading). `_resolve_module()` returns `tuple[ModuleType, bool]` (module, from_cache). `clear_module_cache()` resets the cache (used for test isolation). All `_module_cache` access is guarded by `_CACHE_LOCK` (`threading.Lock`) for thread safety. `execute_hook_line()` logs a warning when a `CALL PYTHON` function takes longer than 30 seconds. `parse_hunt_file()` in `cli.py` returns a `ParsedHunt` NamedTuple with 12 fields: `mission`, `context`, `title`, `step_file_lines`, `setup_lines`, `teardown_lines`, `parsed_vars`, `tags`, `data_file`, `schedule`, `exports`, `imports`. It also strips header-only `@script:` declarations and rewrites `CALL PYTHON {alias}.func` and `CALL PYTHON {callable_alias}` usages to real dotted paths before returning the mission and hook lines. `parse_hunt_file()` does not build hierarchical blocks; the runtime layer does that later with `parse_hunt_blocks()`. `parsed_vars` is a `dict[str, str]` populated from `@var: {key} = value` header lines. `tags` is a `list[str]` populated from `@tags: tag1, tag2` header lines; empty list when absent. `schedule` is a `str` from `@schedule: <expression>`; empty string when absent. `exports` is a `list[str]` from `@export:` header lines; empty list when absent. `imports` is a `list[ImportDirective]` from `@import:` header lines; empty list when absent. `parse_hunt_file()` also resolves imports via `resolve_imports()` and expands `USE` directives via `expand_use_directives()` before returning the mission text. Modules resolved via `importlib.util.spec_from_file_location` + `spec.loader.exec_module(fresh_ModuleType)` — **never** inserted into `sys.modules`. Target functions must be synchronous; async callables are rejected before invocation.
* **Auto-Nav annotation:** When `auto_annotate` is enabled, `run_mission()` captures `url_before = page.url` before every action. For `NAVIGATE` actions, the annotation is written above the action itself. For all other actions, `url_after` is checked in the `finally` block — if the URL changed, `_auto_annotate_navigate(page, hunt_file, action_file_lines, action_idx+1)` is called to insert a comment above the next action line. The comment uses the mapped page name when found in `pages.json`, or the full URL when the lookup returns an `"Auto:"` placeholder.
* **`pages.json` — nested per-site format:** `{ "<site_root_url>": { "Domain": "<display_name>", "<regex_or_exact_url>": "<page_name>" } }`. `lookup_page_name(url)` in `prompts.py` re-reads this file from disk on **every call** (live edits take effect immediately with no restart). Resolution order: exact URL key → regex/substring patterns (skipping `"Domain"` key) → `"Domain"` fallback. When no site block matches, a new nested entry is auto-generated. The longest-prefix site block wins when multiple blocks could match.
* **`_debug_prompt()` `debug-stop` token:** When Python receives `"debug-stop"` on stdin from the VS Code extension (user pressed ⏹ Debug Stop), it clears **both** `self._user_break_steps = set()` and `self.break_steps = set()`, then breaks the pause loop. The test run continues to completion without any further pauses.
* **`_debug_prompt()` `explain-next` token:** When Python receives `"explain-next"` (or `"explain-next {\"step\":\"...\"}"` with optional JSON payload) on stdin, it evaluates the step via `ExplainNextDebugger.evaluate()`, emits `\x00MANUL_EXPLAIN_NEXT\x00{json}\n` to stdout (JSON contains all `WhatIfResult` fields serialized by `_result_to_dict()`), prints `format_report()`, and stays in the pause loop (`continues: true`). In terminal mode, `e` or `explain-next` triggers the same evaluation but without the wire marker.
* **`_debug_prompt()` `what-if` token in extension mode:** The `what-if` interactive REPL is **disabled** in extension protocol mode (stdin is not a TTY) because stdin is reserved for debug control tokens. Sending `what-if` prints an informational message and stays paused. In terminal mode, `w` or `what-if` enters the full `ExplainNextDebugger.run_repl()`.
* **Reporting & HTML reports:** `reporting.py` owns `StepResult`, `BlockResult`, `MissionResult` (with `__bool__` — truthy if status != `"fail"`; has `tags: list[str]` for `@tags` from `.hunt` files and `blocks: list[BlockResult]` for hierarchical execution), plus `RunSummary` fields `session_id` and `invocation_count` for recent cross-invocation HTML-report aggregation. `append_run_history(mission)` appends JSON Lines to `reports/run_history.json` (keys: `file`, `name`, `timestamp`, `status`, `duration_ms`). Separate HTML-report session state is persisted in `reports/manul_report_state.json` so repeated CLI or VS Code Test Explorer invocations can merge into the same `reports/manul_report.html` instead of overwriting it with only the last run. History is appended by `cli.py` (sequential, parallel, and failure paths) and `scheduler.py` (`_run_scheduled_job()`). `reporter.py` owns `generate_report(summary, output_path)` — produces a self-contained dark-themed HTML file with dashboard stats, native `<details>/<summary>` accordions (collapsed by default, auto-expanded on failure), Flexbox step rows, inline base64 screenshots, a **control panel** with "Show Only Failed" checkbox toggle, **tag filter chips** (dynamically collected from all missions' `tags`), and a visible **Run Session / Merged invocations** banner. Each `<div class="mission">` carries `data-status` and `data-tags` attributes for JS filtering. All artifacts (logs, HTML reports, persisted report state) are saved to `reports/` (auto-created by `cli.py`). The `reports/` directory is `.gitignored`.
* **Scoring early exit:** `DOMScorer.score_all()` accepts an optional `early_exit_score: int | None` parameter. When a scored element exceeds the threshold and explain mode is off, remaining elements are skipped. This reduces O(n) scoring on large DOMs.
* **Screenshot capture:** `run_mission()` accepts `screenshot_mode` (`"none"`, `"on-fail"`, `"always"`). Screenshots are stored as base64 PNGs in `StepResult.screenshot`.

## Running tests

```bash
# Activate venv (common folder names: .venv, venv, env, .env)
source .venv/bin/activate       # Linux/Mac (.venv)
source venv/bin/activate        # Linux/Mac (venv)
.venv\Scripts\activate          # Windows

# Synthetic DOM laboratory tests (local HTML via Playwright; no real websites)
python run_tests.py

# Integration demo hunts (needs network + Playwright browsers; Ollama optional)
python demo/run_demo.py                              # run all demo hunts (headed)
python demo/run_demo.py tests/saucedemo.hunt         # single hunt
python demo/run_demo.py --headless                   # headless mode

# General hunt execution (installed manul CLI or dev launcher)
manul path/to/hunts/                     # run all *.hunt files in a dir
manul path/to/file.hunt                  # single hunt
manul --headless path/to/hunts/          # headless mode
manul --browser firefox path/to/hunts/   # run in Firefox instead of Chromium
manul --tags smoke path/to/hunts/        # run only files tagged 'smoke'
manul --tags smoke,regression path/      # files tagged smoke OR regression

# Interactive debug mode (terminal) — pauses before every step, prompts ENTER
manul --debug path/to/file.hunt

# Gutter breakpoint mode (used by VS Code extension debug runner)
# Pause at steps whose file line numbers match; emits stdin/stdout debug protocol
manul --break-lines 5,10,15 path/to/file.hunt

# Smart Page Scanner
manul scan https://example.com                   # scan → draft.hunt (tests_home default)
manul scan https://example.com output.hunt       # scan → explicit output file
manul scan https://example.com --headless        # headless scan

# Retries, screenshots, HTML reports
manul path/ --retries 2                          # retry failed hunts up to 2 times
manul path/ --html-report                        # generate reports/manul_report.html
manul path/ --retries 2 --screenshot on-fail --html-report  # full CI combo
manul path/ --screenshot always --html-report    # every-step forensic report
```

Ollama is optional — only needed as a last-resort self-healing fallback:
- AI element-picker fallback when heuristics confidence is below `ai_threshold`
- free-text tasks (AI planner) — rarely used in practice

To use Ollama: install the [Ollama app](https://ollama.com), run `pip install ollama==0.6.1` (Python client), pull a model (`ollama pull qwen2.5:0.5b`), and start the server (`ollama serve`).

**Rule:** after any engine change, `python run_tests.py` must exit with code **0**.
Tip: `"model": null` (the default) forces heuristics-only mode. This is the recommended configuration for deterministic tests and CI pipelines.
Note: `python run_tests.py` disables persistent controls cache by default for deterministic synthetic suites. `test_13_controls_cache.py` explicitly enables cache in a temporary `cache/run_<datetime>` folder and removes it after the test.

## Docker CI/CD Runner

ManulEngine ships a multi-stage `Dockerfile` that packages the engine as a headless CI runner image published to `ghcr.io/alexbeatnik/manul-engine`.

```bash
docker run --rm --shm-size=1g \
  -v $(pwd)/hunts:/workspace/hunts:ro \
  -v $(pwd)/reports:/workspace/reports \
  ghcr.io/alexbeatnik/manul-engine:0.0.9.27 \
  --html-report --screenshot on-fail hunts/
```

Image characteristics:
* Two-stage build: `deps` (pip install + Playwright browsers) → `runtime` (slim, no build tools or pip cache).
* Non-root user `manul` (UID 1000). No `--privileged` needed.
* `dumb-init` as PID 1 for proper signal handling and exit-code propagation.
* CI defaults baked in: `MANUL_HEADLESS=true`, `MANUL_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage"`, `TZ=UTC`, `LANG=C.UTF-8`.
* Build args: `MANUL_VERSION` (pip version), `PYTHON_VERSION` (base image), `BROWSERS` (space-separated, default `chromium`).
* Volume mount pattern: `/workspace/hunts` (ro), `/workspace/reports` (rw), `/workspace/cache` (rw), `/workspace/controls` (ro), `/workspace/scripts` (ro).

`docker-compose.yml` defines two services: `manul` (test runner) and `manul-daemon` (scheduled hunts, `restart: unless-stopped`).

GitHub Actions workflows:
* `release.yml` — unified release pipeline: synthetic tests → PyPI publish (OIDC) → GHCR multi-arch image → GitHub Release.
* `docker-dev.yml` — dev Docker image on main push (amd64-only, built from source via `Dockerfile.dev`).
* `manul-ci.yml` — reusable example workflow for downstream repos to run `.hunt` tests against the published image.

## Configuration (manul_engine_configuration.json)

JSON file at the **project root** (CWD when `manul` is invoked). All keys are optional.
Environment variables (`MANUL_*`) always override JSON values.

| Key | Default | Description |
| --- | --- | --- |
| `model` | `null` | Ollama model name. `null` = heuristics-only (no AI) |
| `headless` | `false` | Run browser headless |
| `browser` | `"chromium"` | Browser engine: `chromium` (default), `firefox`, or `webkit` |
| `browser_args` | `[]` | Extra launch flags passed to the browser (array of strings). Overridable via `MANUL_BROWSER_ARGS` (comma/space-separated) |
| `ai_threshold` | auto | Score threshold before LLM fallback. `null` = auto-derive from model size |
| `ai_always` | `false` | If `true`, always ask the LLM picker (bypasses heuristic short-circuits). Has no effect and is forced to `false` when `model` is `null` |
| `ai_policy` | `"prior"` | How to treat heuristic score in LLM picker: `"prior"` (hint) or `"strict"` (force max-score) |
| `controls_cache_enabled` | `true` | Enables persistent per-site controls cache (file-based, survives between runs) |
| `controls_cache_dir` | `"cache"` | Directory for cache files (relative to CWD or absolute) |
| `semantic_cache_enabled` | `true` | Enables in-session semantic cache (`learned_elements`). Remembers resolved elements within a single run (+200,000 score boost). Resets on each new `ManulEngine` instance |
| `custom_controls_dirs` | `["controls"]` | List of directories scanned for `@custom_control` Python modules. Resolved relative to CWD. Overridable via `MANUL_CUSTOM_CONTROLS_DIRS` (comma-separated). Legacy alias: `custom_modules_dirs` / `MANUL_CUSTOM_MODULES_DIRS` |
| `log_name_maxlen` | `0` | If > 0, truncates element names in logs |
| `log_thought_maxlen` | `0` | If > 0, truncates LLM “thought” strings in logs |
| `timeout` | `5000` | Default action timeout (ms) |
| `nav_timeout` | `30000` | Navigation timeout (ms) |
| `tests_home` | `"tests"` | Default directory for new hunt files and `SCAN PAGE` / `manul scan` output |
| `auto_annotate` | `false` | If `true`, engine automatically inserts `# 📍 Auto-Nav: <name>` comments into `.hunt` files whenever the page URL changes during a run. Page names come from `pages.json`; falls back to full URL for unmapped pages. Overridable via `MANUL_AUTO_ANNOTATE` env var |
| `channel` | `null` | Playwright browser channel — use an installed browser instead of the bundled one. E.g. `"chrome"`, `"chrome-beta"`, `"msedge"`. Overridable via `MANUL_CHANNEL` |
| `executable_path` | `null` | Absolute path to a custom browser executable (e.g. Electron). Overridable via `MANUL_EXECUTABLE_PATH` |
| `retries` | `0` | Number of times to retry a failed hunt file before marking it as failed (0 = no retries) |
| `screenshot` | `"on-fail"` | Screenshot capture mode: `"on-fail"` (default — failed steps only), `"always"` (every step), `"none"` (disabled) |
| `html_report` | `false` | Generate or refresh a self-contained HTML report after the run (`reports/manul_report.html`). Recent invocations within the same report session are merged via `reports/manul_report_state.json`. |
| `explain_mode` | `false` | Enable DOMScorer explain output. Shows per-channel scoring breakdowns for each resolved element. Overridable via `MANUL_EXPLAIN` |
Threshold auto-calculation by model size: `<1b → 500`, `1-4b → 750`, `5-9b → 1000`, `10-19b → 1500`, `20b+ → 2000`, `null → 0`.

Suggested config for heuristics-only (recommended default — no Ollama needed):

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true
}
```

When documenting the configuration in public-facing docs, do not present a shortened JSON snippet as if it were the full key set. Either label it clearly as a minimal example or include the full current runtime surface area.
The public README should keep the configuration key table and representative `MANUL_*` override examples because users rely on it as the shortest runtime reference, not only as marketing-facing intro text.

Suggested config for enterprise browser (e.g. Chrome stable or Edge):

```json
{
  "model": null,
  "browser": "chromium",
  "channel": "chrome",
  "controls_cache_enabled": true
}
```

Suggested config for Electron app testing:

```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "/path/to/electron",
  "controls_cache_enabled": true
}
```

Electron `.hunt` file example (use `OPEN APP` instead of `NAVIGATE`):

```text
@context: Testing an Electron desktop application
@title: Electron App Smoke Test

STEP 1: Attach to the app window
    OPEN APP
    VERIFY that 'Welcome' is present

STEP 2: Interact with app UI
    Click the 'Settings' button
    VERIFY that 'Preferences' is present
    DONE.
```

Suggested config for mixed mode (optional AI self-healing fallback):

```json
{
  "model": "qwen2.5:0.5b",
  "browser": "chromium",
  "browser_args": [],
  "ai_policy": "prior",
  "controls_cache_enabled": true
}
```

## Custom Controls

`manul_engine/controls.py` owns the Custom Controls registry:

* `_CUSTOM_CONTROLS` — module-level `dict[tuple[str, str], Callable]` keyed by `(page_name_lower, target_name_lower)`. All registry access is guarded by `_REGISTRY_LOCK` (`threading.Lock`) for thread safety.
* `@custom_control(page, target)` — decorator; both sync and async handlers accepted.
* `get_custom_control(page_name, target_name) -> Callable | None` — case-insensitive lookup.
* `load_custom_controls(workspace_dir, required_modules=None, custom_modules_dirs=None)` — supports just-in-time loading for custom controls. The loader is fed from `custom_controls_dirs` config (default: `["controls"]`; legacy alias `custom_modules_dirs`). The CLI computes `required_controls = extract_required_controls(hunt.mission, workspace_dir, custom_modules_dirs)` before engine startup, then `run_mission()` calls `load_custom_controls()` unconditionally so only the Python files needed for each hunt are imported. Per-file idempotency (`_LOADED_FILES`) prevents duplicate imports across sequential runs. Modules still execute in isolated `ModuleType` sandboxes.

**Interception point in `core.py`:** the `else` branch of the step loop (action steps) checks `get_custom_control(lookup_page_name(page.url), first_quoted_token)` before any DOM snapshot. If a handler is found, it is called with `(page, mode, value)` and `_execute_step` is skipped entirely via `elif not await self._execute_step(...)` on the else path.

**Decorator rule for AI assistants — MANDATORY:**
When asked to automate a **complex or custom UI element** (virtual table, canvas-based widget, custom dropdown built with divs, WebGL control, multi-step datepicker, etc.), do NOT attempt to force complex `.hunt` step sequences or try to abuse standard heuristics. INSTEAD:
1. Write a Python function in `controls/<descriptive_name>.py` using the `@custom_control(page='...', target='...')` decorator.
2. Use the standard Playwright `page` object and its full API inside the function.
3. Write a single plain-English step in the `.hunt` file to trigger it (e.g. `Fill 'React Datepicker' with '2026-12-25'`).

Example — CORRECT:
```python
# controls/checkout.py
from manul_engine import custom_control

@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_datepicker(page, action_type: str, value: str | None) -> None:
    loc = page.locator(".react-datepicker__input-container input").first
    if action_type == "input" and value:
        await loc.click()
        await loc.fill(value)
```
```text
# tests/checkout.hunt
Fill 'React Datepicker' with '2026-12-25'
```

Example — WRONG (do not do this):
```text
# tests/checkout.hunt
2. Click the '.react-datepicker__input-container input' element
3. Fill the first input inside the calendar widget with '2026-12-25'
4. Click on day cell number 25 in the calendar grid
```

The page name in `@custom_control(page=...)` must match the value returned by `lookup_page_name(page.url)`, i.e. what is mapped in `pages.json` for the target URL.

---

## Public Python API (`ManulSession`)

`api.py` owns `ManulSession` — a high-level async context manager for programmatic browser automation in pure Python. It manages its own Playwright lifecycle and routes all element-resolution calls through the full ManulEngine pipeline (cache → heuristics → optional LLM fallback). Callers never need to think about selectors.

**Import:** `from manul_engine import ManulSession`

**Constructor parameters** mirror `ManulEngine`'s: `model`, `headless`, `browser`, `browser_args`, `ai_threshold`, `disable_cache`, `semantic_cache`, `channel`, `executable_path`.

**Lifecycle:**
* `async with ManulSession(...) as session:` — launches browser, opens page; tears down on exit.
* `start()` / `close()` — explicit lifecycle for non-context-manager usage.

**Core methods** (all async, all route through the smart pipeline):
* `navigate(url)` — loads URL, waits for DOM settlement.
* `click(target, double=False)` — click or double-click.
* `fill(target, text)` — type into a field.
* `select(option, target)` — dropdown selection.
* `hover(target)`, `drag(source, destination)`, `right_click(target)`.
* `press(key, target=None)` — key press, optionally on a resolved element.
* `upload(file_path, target)` — file upload.
* `scroll(target=None)` — scroll page or container.
* `verify(target, present=True, enabled=None, checked=None)` — assertion.
* `extract(target, variable=None)` — extract text, optionally into memory.
* `wait(seconds)` — hard sleep.
* `run_steps(steps, context)` — execute raw DSL multi-line steps against the current open page (reuses browser session, does not launch/teardown).

**Properties:** `page` (active Playwright Page), `engine` (underlying ManulEngine), `memory` (ScopedVariables store).

**Internally**, each method generates a synthetic DSL step string and calls the appropriate `ManulEngine._execute_step` / `_handle_*` handler — the same code path used by `.hunt` file execution.

**Usage (pure Python, no .hunt files needed):**
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

**Usage (mixing programmatic API with DSL snippets):**
```python
async with ManulSession() as session:
    await session.navigate("https://example.com")
    result = await session.run_steps("""
        STEP 1: Search
            Fill 'Search' with 'ManulEngine'
            PRESS Enter
            VERIFY that 'Results' is present
    """)
    assert result.status == "pass"
```

**When to recommend ManulSession vs .hunt files:**
* Recommend `ManulSession` when the user wants to write automation in pure Python, integrate with existing pytest suites, build RPA scripts, or use ManulEngine as a library.
* Recommend `.hunt` files when the user wants shared QA artifacts readable by non-technical stakeholders, or when using the Manul Engine Extension for VS Code's Test Explorer / debug features.

---

## Common pitfalls & Advanced Learnings

* **Global Lifecycle Hooks — mandatory rule:** When a user asks to set up a database, perform a global login, seed test data, obtain an auth token, or do any pre-suite or pre-group environment setup, you **MUST** generate a `manul_hooks.py` file using `@before_all` or `@before_group(tag=...)` from `manul_engine`. **Never** add setup steps to individual `.hunt` files — that couples UI flows to infrastructure, slows each run, and makes teardown unreliable. The only correct pattern:
  ```python
  # tests/manul_hooks.py
  from manul_engine import before_all, after_all, GlobalContext

  @before_all
  def setup(ctx: GlobalContext) -> None:
      ctx.variables["TOKEN"] = auth_service.get_token()

  @after_all
  def teardown(ctx: GlobalContext) -> None:
      auth_service.revoke_token(ctx.variables["TOKEN"])
  ```
  The token is then available as `{TOKEN}` in all `.hunt` files without any per-file declaration.

* **Native Select vs Custom Dropdowns:** Playwright's `select_option()` crashes on non-`<select>` tags. If `mode == "select"` but the element is a `div`/`span`, gracefully fallback to a standard `click()`.
* **Overlapped Elements:** Modern UIs use invisible overlays. The engine primarily uses Playwright with `force=True` plus retries/alternate candidates; JS helpers (`window.manulClick`, `window.manulType`) are mainly used for Shadow DOM elements.
* **Deep Text Verification:** Standard `document.body.innerText` does not see text inside Shadow DOMs or Input values. `_handle_verify` uses a JS collector (`VISIBLE_TEXT_JS`) plus fallback checks.
* **Form Auto-clearing:** Before typing into an input using `loc.type()`, always `await loc.fill("")` to prevent appending text to pre-filled placeholders (especially critical on Wikipedia and search bars).
* **Input order semantics:** `Type 'VALUE' into 'TARGET'` is value-first because `into` marks the target after the first quoted string. `Fill 'TARGET' field with 'VALUE'` stays target-first/value-last. Do not describe or generate these forms interchangeably.
* **Checkbox/Radio strictness:** Heuristics must ruthlessly penalize (-50_000) non-checkbox elements when the user specifically asks to "Check" or "Select the radio", to prevent clicking a nearby `<td>` that happens to share the target text.
* **Scanner label quality:** For checkbox/radio controls, prefer visible label association (`label[for]`, wrapping `<label>`, adjacent label) over generic text extraction so generated hunt identifiers match what humans see.
* **Contextual navigation:** Prefer DSL qualifiers such as `NEAR 'Search'`, `ON HEADER`, `ON FOOTER`, and `INSIDE 'Actions' row with 'John Doe'` before suggesting brittle selectors or custom controls for repeated standard widgets.
* **SVG quirks:** `el.className` might not be a string. In `SNAPSHOT_JS`, safely extract it: `typeof el.className === 'string' ? el.className : el.getAttribute('class')`.
* **Table Extraction & Legacy HTML:** When extracting rows based on text, use the shared `wordMatch()` helper from `EXTRACT_DATA_JS` instead of ad‑hoc `.includes()` calls. It uses word-boundary matching for short tokens and falls back to substring matching for longer tokens to reduce partial hits (e.g., "Javascript" vs "Java"). For legacy forms without explicit `<label>` tags, inputs inside `<fieldset>` should inherit context from `<legend>`.
* **AI Rejection loop:** If LLM returns `{"id": null}`, add the current top candidates to a `failed_ids` set, scroll the page, and retry `_snapshot` to discover hidden elements.

## Resolution fallback chain

The engine uses normalised `0.0–1.0` float scoring in `DOMScorer` (see `scoring.py`). Final integer scores = weighted sum × `SCALE` (177,778). The *highest-signal* boosts (and the cutoffs used in `core.py`) are:

1. Semantic cache reuse: +1.0 cache × W_cache(2.0) → ~355k scaled (`core.py` short-circuits at score ≥ 200_000)
2. Blind/context reuse (same xpath as last step): +0.05 cache → ~17k scaled (`core.py` short-circuits at score ≥ 10_000)
3. Exact `data-qa` match: +1.0 text × W_text(0.45) → ~80k scaled (substring: +0.375 → ~30k)
4. Exact `html_id` match: +0.6 attr × W_attr(0.25) → ~26k scaled (target_field exact: higher via multi-channel)
5. Exact text/aria/placeholder match: +0.625 text → ~50k scaled; partial matches are smaller
6. Element-type alignment & dev naming conventions: +0.05–0.30 semantics depending on mode (checkbox/radio strictness: -0.50 penalty)
7. Penalties: disabled ×0.0 (zeroes entire score), hidden ×0.1
8. LLM fallback: used only when best score < `MANUL_AI_THRESHOLD` (unless AI is disabled via threshold ≤ 0)

## Element data shape

Each element dict returned by `SNAPSHOT_JS` contains:
`id, name, xpath, is_select, is_shadow, is_contenteditable, class_name, tag_name, input_type, data_qa, html_id, icon_classes, aria_label, placeholder, role, disabled, aria_disabled, name_attr, frame_index`.

* `frame_index` — integer index into `page.frames` (0 = main frame). `_frame_for(page, el)` uses this to route Playwright calls to the correct Frame. Stale indices fall back to main frame.
* `name_attr` — the HTML `name` attribute (e.g. `name="search"` on Wikipedia's Codex search input). Scoring treats it as a text signal: exact match +0.0375 text / ~3k scaled; substring +0.0125 / ~1k scaled. Always cast with `str(el.get("name_attr", ""))` before comparing.

* `name` includes section context: `"Section -> Element Name input text"`.
* For `<select>` elements, `name` embeds options: `"dropdown [Option A | Option B]"`.

## Memory & variables

* `self.memory` — dict of `{var_name: value}` populated by EXTRACT steps.
* `substitute_memory()` replaces `{var}` placeholders.
* `self.learned_elements` — semantic cache: `(mode, search_texts, target_field) → {name, tag}`.
* `self.last_xpath` — used for Contextual Reuse (if next step says "in that field").

## Companion Manul Engine Extension for VS Code

The companion extension is published separately from this runtime repository. When the extension source is checked out in its own repository or added to the workspace, it provides hunt file language support, Test Explorer integration, a config sidebar, cache browser, and an interactive debug runner.

**Key rules when editing extension code:**

* `constants.ts` — centralised shared constants module. All string literals for config filenames (`DEFAULT_CONFIG_FILENAME`), debug protocol markers (`PAUSE_MARKER`), and terminal names (`TERMINAL_NAME`, `DEBUG_TERMINAL_NAME`, `DAEMON_TERMINAL_NAME`) live here. `getConfigFileName()` reads the `manulEngine.configFile` VS Code setting with a fallback to `DEFAULT_CONFIG_FILENAME`. **Every** TS file that references the config filename or terminal names must import from `constants.ts` — never hardcode these strings inline.
* `huntRunner.ts` — `runHunt()` spawns `manul` with `cwd` set to the **VS Code workspace folder root** (resolved via `vscode.workspace.getWorkspaceFolder()`), not `path.dirname(huntFile)`. This ensures `manul_engine_configuration.json` and relative `controls_cache_dir` paths are always resolved from the project root, matching CLI behaviour.
* `huntRunner.ts` — `findManulExecutable()` probes local venv folders in order: `.venv`, `venv`, `env`, `.env` (both `bin/manul` on Unix and `Scripts\manul.exe` on Windows) before falling back to user-level install paths and a login-shell lookup. When adding new candidate paths, keep this order and always guard Windows/macOS-only paths with `isWin` / `process.platform` checks.
* `huntRunner.ts` — `runHuntFileDebugPanel(manulExe, huntFile, onData, token?, breakLines?, onPause?)` spawns with `--workers 1` and optionally `--break-lines N,M,...`. **Never pass `--debug`** — `--debug` pauses before every step including step 1 (`NAVIGATE`), which hangs before the browser has loaded anything. Only `--break-lines` + the stdin/stdout protocol is used for the panel runner.
* **Debug protocol:** Python (`core.py`) detects it is not a TTY (piped stdout) and emits `\x00MANUL_DEBUG_PAUSE\x00{"step":"...","idx":N}\n` on stdout when pausing. The TS side line-buffers stdout, detects the marker, calls `onPause(step, idx)` and writes `"next\n"`, `"continue\n"`, or `"debug-stop\n"` to stdin. The `onPause` return type is `Promise<"next" | "continue" | "highlight" | "debug-stop" | "stop-test">`. Sending `"abort\n"` + killing the process after 500 ms implements **Stop Test**; `"debug-stop\n"` implements **Debug Stop** (run to end, no more pauses).
* **Break-step semantics:** `ManulEngine.__init__` accepts `break_steps: set[int] | None`. `_user_break_steps` stores the original user-defined set; `break_steps` is the mutable active set. When the user picks **Next Step**: `break_steps.add(idx + 1)`. When the user picks **Continue All**: `break_steps = set(_user_break_steps)` (resets to original gutter breakpoints). This ensures "Next" advances exactly one step and "Continue" runs to the next gutter breakpoint or end.
* `debugControlPanel.ts` — singleton `DebugControlPanel.getInstance(ctx)`. `showPause(step, idx)` uses `vscode.window.createQuickPick()` (low-level API, not `showQuickPick`) so the picker can be hidden programmatically. `ignoreFocusOut: true` keeps it visible while Playwright runs. `abort()` calls `_activeQp.hide()`, which triggers `onDidHide` → resolves the promise with `"next"` so Python's `stdin.readline()` always unblocks. `dispose()` also calls `hide()` and resets the singleton. `tryRaiseWindow(idx, stepText)` (Linux only): spawns `xdotool search --onlyvisible --class "Code" windowactivate` (X11 focus), falls back to `wmctrl -a "Visual Studio Code"`, then fires `notify-send -u normal -t 5000` (5-second system notification, disappears automatically — do NOT use `-u critical` which ignores `-t` on GNOME/KDE). The QuickPick has **5 items**: Next Step, Continue All, Highlight Element, **⏹ Debug Stop** (sends `"debug-stop"` — clears all breakpoints so the run completes without further pauses), **🛑 Stop Test** (sends `"abort"` + kills the process after 500 ms). `PauseChoice` type: `"next" | "continue" | "highlight" | "debug-stop" | "stop-test"`.
* `huntTestController.ts` — has a **Debug run profile** in addition to the normal run profile. It calls `runHuntFileDebugPanel` with `onPause: (step, idx) => panel.showPause(step, idx)` and runs sequentially (no concurrency). **Stop button wiring:** `token.onCancellationRequested(() => panel.abort())` — this is essential; without it the QuickPick stays open after Stop is pressed and Python hangs. The disposable is stored and `.dispose()`d after the loop. Debug profile also calls `workbench.view.testing.focus` (in addition to `workbench.panel.testResults.view.focus`) to show the Test Explorer tree with per-step spinning/pass/fail indicators.
* `configPanel.ts` — `doSave()` forces `ai_always: false` whenever `model` is empty/null (`modelVal !== '' && g('ai_always').checked`). Do not remove this guard — saving `ai_always: true` with no model would produce an invalid config that causes runtime errors. The `syncAiAlways()` function also disables and unchecks the `ai_always` checkbox in the UI when the model field is cleared.
* `configPanel.ts` — Two separate cache controls: `controls_cache_enabled` is labelled **"Persistent Controls Cache"** (file-based, per-site storage, survives between runs); `semantic_cache_enabled` is labelled **"Semantic Cache"** (in-session `learned_elements`, +200,000 score boost within a single run, resets when process ends). The `controls_cache_dir` field is labelled "controls_cache_dir". Both default to `true`. Do not merge these two settings.
* `configPanel.ts` — `auto_annotate` checkbox (default `false`): labelled **"Auto-Annotate Page Navigation"**. When enabled, the engine writes `# 📍 Auto-Nav: <name>` comments into `.hunt` files live whenever the URL changes. `doSave()` writes `auto_annotate: g('auto_annotate').checked`; `doLoad()` reads `g('auto_annotate').checked = !!config.auto_annotate`.
* Config panel reads/writes `manul_engine_configuration.json` at the workspace root using `_configPath()`. The config file name is resolved via `getConfigFileName()` from `constants.ts`, which reads the `manulEngine.configFile` setting.
* Ollama model discovery: the panel fetches `http://localhost:11434/api/tags` on open and populates a `<select>` dropdown with installed model names (replaced legacy `<datalist>` + `<input>` to fix rendering offset in Electron webview). First option is always `null (heuristics-only)`. The stored model is always preserved as an option even when Ollama is offline.
* `schedulerPanel.ts` — Advanced Scheduler Dashboard / Visual RPA Manager. `findAllHunts()` scans workspace for **all** `.hunt` files (not just scheduled ones), returns `HuntFileEntry[]` with `relPath`, `absUri`, and `schedule` (empty string if unscheduled). The webview splits files into **Scheduled Tasks** and **Unscheduled Tasks** sections with a **search bar** for filename filtering. Each file row has a `<select>` combobox (preset schedule options: None, every 30 seconds, every 1/5/15 minutes, every hour, daily at 09:00, weekly, Custom…), a hidden/disabled custom text `<input>` that activates when "Custom…" is selected, and an **Apply** button. Apply sends `{ command: 'updateSchedule', filePath: absUri, schedule: '...' }` to the extension. `mutateScheduleHeader(fileUri, schedule)` uses `vscode.WorkspaceEdit` to inject (after last `@`-prefixed metadata line), replace, or remove the `@schedule:` header. The file is saved after mutation and the webview refreshes automatically. **Run History & Sparklines:** `readRunHistory(wsRoot, limit=5)` reads `reports/run_history.json` (JSON Lines), returns a map of filename → last N `RunHistoryRecord` entries. `_sendAllFiles()` posts both `files` and `history` to the webview. The frontend renders a sparkline (pass=🟢, fail=🔴, flaky/warning=🟡) and a relative-time label ("3m ago") per file row.
* `explainLensProvider.ts` — Legacy `ExplainLensProvider` CodeLens provider source file. Currently **not registered** in `extension.ts` or `package.json` (commands `manul.explainHuntFile` / `manul.runExplain` and setting `manulEngine.explainCodeLens` are not contributed). The file remains in the source tree for potential future use but is dead code. The active explain UI is the `ExplainHoverProvider` (see below).
* `explainHoverProvider.ts` — `ExplainHoverProvider` implements `HoverProvider` for `.hunt` files. During debug runs, `--explain` is auto-injected; `ExplainOutputParser` parses stdout explain blocks (`┌─ 🔍 EXPLAIN` … `└─ ✅ Decision`) keyed by file line number. When the user hovers over a resolved step line, a rich Markdown tooltip with the per-channel scoring breakdown is shown. A separate `manul.debug.explainStep` command (title: "Manul: Explain Current Step", `$(lightbulb-autofix)` icon) is contributed in `package.json` as an editor title bar button; it calls `DebugControlPanel.triggerExplain()` to send `"explain"` via stdin to the paused Python process. The explain output channel name constant lives in `constants.ts` (`EXPLAIN_OUTPUT_CHANNEL`).
* **Docs/install rule:** when writing **public-facing docs for end users**, prefer the published Marketplace install path for the extension. Only document local `npm` / `vsce` / `F5` build workflows when the user is explicitly asking about extension development.
* **Dev build rule:** when you are actually editing extension source code in its separate repository, run `npm install` and `npm run compile` from that repository's root folder. Use `npx vsce package` only when packaging is explicitly relevant. Press `F5` in VS Code with the extension folder open only for extension-development workflows.

## Version Bump

The repository ships `bump_version.py` at the project root. It reads the canonical version from `pyproject.toml` and updates **every** file that embeds the version string (34 occurrences across 18 files: pyproject.toml, Dockerfile, docker-compose.yml, README.md, README_DEV.md, .cursorrules, .github/copilot-instructions.md, custom-instructions mirror, 8 contracts, CI workflows).

```bash
python bump_version.py 0.0.9.28 --dry-run   # preview changes
python bump_version.py 0.0.9.28             # apply
python bump_version.py --show                # print current version
```

**MANDATORY:** When the version changes, always use `bump_version.py` instead of editing files manually. Never edit version strings by hand — the script ensures all files stay in sync.

Companion Manul Engine Extension for VS Code versioning and Marketplace release notes are maintained in the separate extension repository.