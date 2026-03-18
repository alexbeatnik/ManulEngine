<p align="center">
  <img src="images/manul.png" alt="ManulEngine mascot" width="180" />
</p>

# 😼 ManulEngine v0.0.9.8 — Contributor Notes

ManulEngine is a deterministic, DSL-first web and desktop automation runtime.

This document is for contributors working on the Python runtime itself. It is intentionally technical, direct, and aligned with the current alpha posture of the project.

## Status

The project is solo-developed and alpha-stage.

Bugs are expected. APIs may change. Do not document or implement features as if the runtime is production-stable.

## Release Line

- Python package version: `0.0.9.8`
- Public package name: `manul-engine`
- Public Python entry points: `ManulEngine`, `ManulSession`

## Project Structure

```text
ManulEngine/
├── manul.py                          Dev CLI entry point (intercepts `test` subcommand)
├── manul_engine_configuration.json   Project configuration (JSON)
├── pyproject.toml                    Build config — package: manul-engine 0.0.9.8
├── requirements.txt                  Python dependencies
├── manul_engine/                     Core automation engine package
│   ├── __init__.py                   Public API — exports ManulEngine, ManulSession
│   ├── api.py                        ManulSession — public Python API facade (async context manager, Playwright lifecycle)
│   ├── cli.py                        Installed CLI entry point (`manul` command + `manul scan` + `manul record` + `manul daemon` subcommands)
│   ├── lifecycle.py                  Global Lifecycle Hook Registry (@before_all, @after_all, @before_group, @after_group)
│   ├── hooks.py                      [SETUP] / [TEARDOWN] hook parser and executor
│   ├── controls.py                   Custom Controls registry (@custom_control, get_custom_control, load_custom_controls)
│   ├── recorder.py                   Semantic Test Recorder — JS injection, Python bridge, DSL generator
│   ├── scheduler.py                  Built-in Scheduler — parse_schedule(), Schedule dataclass, daemon_main()
│   ├── _test_runner.py               Dev-only synthetic test runner (not in public CLI)
│   ├── prompts.py                    JSON config loader, thresholds, LLM prompts
│   ├── helpers.py                    HuntBlock, parse_hunt_blocks(), classify_step(), env helpers, timing constants
│   ├── js_scripts.py                 All JavaScript injected into the browser (incl. SCAN_JS)
│   ├── scoring.py                    Heuristic element-scoring algorithm (20+ rules, normalized 0.0–1.0 channels)
│   ├── scanner.py                    Smart Page Scanner: scan_page(), build_hunt(), scan_main()
│   ├── core.py                       ManulEngine class (LLM, resolution, hierarchical mission runner)
│   ├── cache.py                      Persistent per-site controls cache mixin
│   ├── actions.py                    Action execution mixin (click, type, select, hover, drag, scan_page)
│   ├── reporting.py                  StepResult, BlockResult, MissionResult, RunSummary dataclasses
│   ├── reporter.py                   Interactive HTML report generator (dark theme, control panel, tag chips, base64 screenshots)
│   ├── variables.py                  ScopedVariables — 4-level variable hierarchy (row, step, mission, global)
│   └── test/
│       ├── test_00_engine.py         Engine micro-suite (synthetic DOM via local HTML)
│       ├── test_01_ecommerce.py      Scenario pack: ecommerce
│       ├── ...
│       ├── test_16_hooks.py          Unit: [SETUP]/[TEARDOWN] hooks (41 assertions, no browser)
│       ├── test_19_custom_controls.py Unit: Custom Controls registry + engine interception
│       ├── test_20_variables.py      Unit: @var: static variable declaration
│       ├── test_21_dynamic_vars.py   Unit: CALL PYTHON ... into {var} dynamic variable capture
│       ├── test_22_tags.py           Unit: @tags: / --tags CLI filter
│       ├── test_24_reporting.py      Unit: StepResult, BlockResult, MissionResult, RunSummary
│       ├── test_27_lifecycle_hooks.py Unit: Global Lifecycle Hook system
│       ├── test_28_logical_steps.py  Unit: Logical STEP ordering and parser
│       ├── test_29_iframe_routing.py Synthetic: Cross-frame element resolution
│       ├── test_30_heuristic_weights.py Synthetic+Unit: DOMScorer priority hierarchy
│       ├── test_31_visibility_treewalker.py Synthetic+Unit: TreeWalker PRUNE/checkVisibility
│       ├── test_37_enterprise_dsl.py Unit: @data:, MOCK, VERIFY VISUAL/SOFTLY, reporter warnings
│       ├── test_39_open_app.py       Unit: OPEN APP command support
│       ├── test_42_scheduler.py      Unit: Built-in Scheduler
│       ├── test_43_scoped_variables.py Unit: ScopedVariables hierarchy
│       ├── test_44_explain_mode.py   Unit: DOMScorer explain output, --explain CLI flag
│       └── test_45_api.py            Unit: ManulSession public Python API facade
├── controls/                         User-owned custom Python handlers
├── tests/                            Integration hunt tests
├── reports/                          Generated logs and HTML reports
├── benchmarks/                       Adversarial benchmark suite
└── prompts/                          LLM prompt templates for hunt file generation
```

## Runtime Shape

ManulEngine has three distinct but connected layers:

1. File parsing through `parse_hunt_file()` in `cli.py`
2. Hierarchical block parsing through `parse_hunt_blocks()` in `helpers.py`
3. Execution through `run_mission()` in `core.py` or `run_steps()` in `api.py`

That split is deliberate. `parse_hunt_file()` still owns headers, hook extraction, tags, vars, and file-line bookkeeping. The runtime block model is created later by `parse_hunt_blocks()`, which turns mission text into block-aware execution objects.

## Architecture

ManulEngine is not a test library bolted onto Playwright. It is a runtime: an interpreter for the `.hunt` DSL that sits between human-authored automation scripts and the browser.

```text
.hunt DSL -> Parser -> Execution Engine -> Controls / Hooks / Cache -> Playwright
```

The `.hunt` DSL is the instruction set. The parser and engine are the interpreter. Playwright is the I/O layer. The same runtime executes QA tests, RPA workflows, synthetic monitors, and constrained agent actions.

## Engine Baseline

The current engine posture still depends on the same core changes introduced across the recent release line:

- normalized `0.0–1.0` heuristic scoring in `DOMScorer`
- `TreeWalker`-based DOM collection in injected JavaScript
- frame-aware snapshotting and iframe routing
- unnumbered STEP-grouped DSL as the canonical authoring format
- explicit reporting and structured stdout instead of ad hoc console logging
- hooks, scoped variables, and custom controls as first-class escape hatches

## Why The Runtime Matters

Most browser automation tools report failure as a binary outcome. ManulEngine is designed to preserve enough structure to explain why a step failed, what candidates were considered, and where the orchestration layer made its decision.

That is why the codebase is split between:

- raw file parsing
- runtime block parsing
- execution orchestration
- scoring and snapshotting
- action handlers
- reporting and artifact generation

Each of those layers has a separate responsibility and should stay separate.

## Heuristics Engine

Element resolution is driven by `DOMScorer`, a normalized `0.0–1.0` float scoring system across five weighted channels:

| Channel | Weight | What it covers |
| --- | --- | --- |
| `cache` | 2.0 | Semantic cache reuse and blind context reuse |
| `semantics` | 0.60 | Element-type alignment, roles, mode synergy |
| `text` | 0.45 | Text, aria-label, placeholder, `data-qa`, `name` |
| `attributes` | 0.25 | `html_id`, target-field affinity, dev naming |
| `proximity` | 0.10 | DOM depth and local form context |

Final score:

```text
(text×W_text + attr×W_attr + sem×W_sem + prox×W_prox + cache×W_cache) × penalty_mult × SCALE
```

`SCALE=177,778` maps the weighted float into the integer range expected by runtime cutoffs in `core.py`.

Important contributor rules:

- confidence should be documented and explained on a normalized `0.0` to `1.0` scale
- `model: null` remains the recommended default
- Ollama is fallback-only, not the primary resolver
- accessibility-facing attributes are first-class heuristic signals, not optional sugar

## Hierarchical Execution Model

### Why it changed

The old runner treated `STEP` declarations and executable commands as a flat list. That made terminal logs noisy, made UI integration awkward, and blurred the distinction between logical group boundaries and real browser actions.

The current model is hierarchical:

- `STEP ...` lines define parent blocks
- action lines beneath them become child actions
- files with no explicit `STEP` headers are grouped into a synthetic default block for backward compatibility

### Data structure

`helpers.py` now defines `HuntBlock`:

```python
@dataclass(slots=True)
class HuntBlock:
    block_name: str
    actions: list[str] = field(default_factory=list)
    block_line: int | None = None
    action_lines: list[int] = field(default_factory=list)
    synthetic: bool = False
```

`parse_hunt_blocks(task, file_lines=None)` is the runtime-level parser that creates these objects.

Important behavior:

- canonicalizes STEP labels via `normalize_logical_step()`
- preserves action ordering exactly as written
- records the file line for the block header and each action when available
- creates `STEP: Default` when a mission has no explicit blocks

### Fail-fast semantics inside a block

Execution is now nested:

1. Start block
2. Run action 1
3. Run action 2
4. Stop the block immediately on the first hard failure
5. Mark the block failed
6. Stop the mission unless the failure was a soft assertion

Soft assertions remain warnings. They mark the action as `warning`, keep the block alive, and allow the mission to continue.

Hard failures remain fail-fast.

## run_mission() Flow

The main loop in `core.py` now does this:

1. Parse raw mission text into block objects
2. Flatten action file lines for Auto-Nav annotation and breakpoint mapping
3. Iterate blocks
4. Emit block-start stdout tag
5. Iterate actions inside the block
6. Emit action-start stdout tag
7. Dispatch the action through the existing system keyword or `_execute_step()` pipeline
8. Record `StepResult`
9. Aggregate `BlockResult`
10. Emit block-pass or block-fail stdout tag

The existing action handlers were intentionally preserved. The refactor changed orchestration, not the action execution APIs.

## Structured Stdout Contract

External tools now rely on the stdout shape. Treat these tags as a compatibility surface.

### Block tags

```text
[📦 BLOCK START] STEP 1: Login
[🟩 BLOCK PASS] STEP 1: Login
[🟥 BLOCK FAIL] STEP 1: Login
```

### Action tags

```text
  [▶️ ACTION START] NAVIGATE to https://www.saucedemo.com/
  [✅ ACTION PASS] duration: 2.33s
  [❌ ACTION FAIL] Element not found
```

### Rules contributors must preserve

- block-start emits exactly once per block
- action-start emits exactly once per child action
- hard action failure emits `ACTION FAIL` and aborts the rest of the block
- successful block completion emits `BLOCK PASS`
- failed block completion emits `BLOCK FAIL`
- warning-only blocks currently complete as pass at the stdout summary level unless future UI requirements require a dedicated warning tag

If you change these tags, you are changing a UI integration contract.

## Breakpoint Mapping

`cli.py` still maps editor gutter file lines to runtime action indices.

Because `STEP` headers are no longer executable actions, their mapping changed:

- a breakpoint on a block header maps to the first action inside that block
- a breakpoint on a child action maps to that action's runtime index

This mapping now uses `parse_hunt_blocks()` instead of raw `step_file_lines` enumeration.

## Reporting Model

`reporting.py` now exposes both action-level and block-level result objects:

```python
@dataclass
class StepResult:
    index: int
    text: str
    status: str = "pass"
    duration_ms: float = 0.0
    error: str | None = None
    screenshot: str | None = None
    logical_step: str | None = None
    healed: bool = False


@dataclass
class BlockResult:
    name: str
    status: str = "pass"
    duration_ms: float = 0.0
    error: str | None = None
    actions: list[StepResult] = field(default_factory=list)
```

`MissionResult.blocks` stores the block list alongside the flattened `steps` list.

That gives downstream consumers two views of the same run:

- flattened actions for legacy consumers and line-level details
- explicit blocks for modern reporters and UI tree rendering

## Explainability

The contributor-facing explanation model should stay multi-layered, even without editor-specific documentation in this file:

- CLI `--explain` for raw candidate ranking and per-channel breakdowns
- structured reporting objects that preserve action and block state
- normalized heuristic confidence wording rather than raw integer score language

This is part of the runtime contract, not a side note.

## Global Lifecycle Hooks

Suite-level orchestration is owned by `manul_engine/lifecycle.py`. Four decorators bracket the CLI lifecycle:

| Decorator | Fires | Failure semantics |
| --- | --- | --- |
| `@before_all` | Once, before any hunt starts | Failure aborts entire suite; `@after_all` still runs |
| `@after_all` | Once, after all hunts finish | Always runs; failure logged, never overrides suite result |
| `@before_group(tag=...)` | Before each matching hunt | Failure skips that mission; `@after_group` still fires |
| `@after_group(tag=...)` | After each matching hunt | Always runs; failure logged, never overrides mission result |

`GlobalContext` exposes:

- `variables: dict[str, str]` for data propagated into matching hunts
- `metadata: dict[str, object]` for hook-local scratch state

Key rules:

- lifecycle hooks must be synchronous
- modules are resolved in isolation and are not inserted into `sys.modules`
- lifecycle variables merge with per-file `@var:` declarations, with file-local declarations winning on key collision

## [SETUP] / [TEARDOWN] and Inline CALL PYTHON

`hooks.py` owns the parsing and execution of synchronous Python helpers.

Execution lifecycle:

```text
[SETUP] block -> browser mission -> [TEARDOWN] block
```

Inline `CALL PYTHON <module>.<function>` steps in the mission body reuse the same resolution and validation logic.

Contributor rules:

- helper functions must be synchronous
- module resolution order is hunt directory, CWD, then standard import resolution
- file-local modules execute in isolated module objects, never via global `sys.modules` insertion
- `CALL PYTHON ... into {var}` captures the return value as a string for downstream placeholder substitution

## Variables and Scope

Runtime values can enter the mission through multiple channels:

- `@var:` for static declarations
- `SET {name} = value` for mid-flight assignment
- `EXTRACT ... into {var}` for UI-derived values
- `CALL PYTHON ... into {var}` for computed or backend-derived values
- lifecycle hooks for suite-level values

`ScopedVariables` keeps row, step, mission, and global state separated.

## Tags, Scheduling, and Data-Driven Runs

The parser and CLI also own non-execution metadata that materially affects orchestration:

- `@tags:` for run filtering
- `@data:` for JSON/CSV iteration
- `@schedule:` for daemon scheduling

When changing `ParsedHunt`, remember that multiple layers depend on field ordering and compatibility.

## Custom Controls

Custom controls are the deliberate escape hatch for complex widgets that should not be brute-forced through generic heuristics.

Core pieces:

- `@custom_control(page="...", target="...")`
- `get_custom_control(page_name, target_name)`
- `load_custom_controls(workspace_dir, required_modules=...)`

The engine checks for a matching custom control before performing a normal DOM snapshot for an action step.

## Lazy Loading For Custom Controls

Custom control loading changed from eager blanket import to hunt-aware lazy loading.

### Current flow

1. `cli.py` parses the hunt file
2. `extract_required_controls(hunt.mission, workspace_dir)` determines which control targets are needed
3. `ManulEngine(...)` is constructed with `required_controls=...`
4. `load_custom_controls(workspace_dir, required_modules=required_controls)` imports only the matching Python files from `controls/`

### Why it matters

- reduces startup overhead for large control libraries
- avoids importing unrelated handlers and their side effects
- keeps debugging focused on the controls that actually participate in the mission

Do not regress this back to unconditional eager loading without a strong reason.

## ManulSession

`api.py` is now a first-class surface, not an afterthought.

`ManulSession` owns:

- Playwright lifecycle
- direct navigation and interaction helpers
- `run_steps()` for inline DSL execution without spinning up the CLI path

The inline runner uses the same hierarchical block model as `run_mission()` so behavior stays aligned between `.hunt` and pure-Python usage.

When changing DSL execution semantics, update both:

- `manul_engine/core.py`
- `manul_engine/api.py`

## Parser Responsibilities

`parse_hunt_file()` in `cli.py` still returns the 10-field `ParsedHunt` named tuple:

```python
ParsedHunt(
    mission,
    context,
    title,
    step_file_lines,
    setup_lines,
    teardown_lines,
    parsed_vars,
    tags,
    data_file,
    schedule,
)
```

Important distinction:

- `mission` remains raw executable text
- hierarchical grouping happens later through `parse_hunt_blocks()`

That keeps the CLI parser stable while allowing the runtime execution model to evolve.

## Desktop Automation

Desktop support remains part of the runtime contract.

Contributor rules:

- do not regress `executable_path` support
- keep `OPEN APP` as the DSL surface for Electron and similar desktop flows
- preserve the same orchestration semantics as browser-backed runs wherever possible

## Contributor Testing Expectations

After touching the runner, parser, reporting model, or API surface, validate at least the focused suites that cover the changed behavior.

Relevant suites for the 0.0.9.8 release line:

- `test_24_reporting.py`
- `test_28_logical_steps.py`
- `test_37_enterprise_dsl.py`
- `test_38_set_and_indent.py`
- `test_39_open_app.py`
- `test_42_scheduler.py`
- `test_45_api.py`

Project rule still applies:

```bash
python manul.py test
```

must exit with code `0` after engine changes.

## Contributor Quick Commands

```bash
pip install manul-engine==0.0.9.8
pip install "manul-engine[ai]==0.0.9.8"
python manul.py test
manul tests/saucedemo.hunt --explain
manul tests/ --retries 2 --screenshot on-fail --html-report
```

## Release Notes for v0.0.9.8

- promoted `ManulSession` as a first-class public API
- introduced hierarchical block parsing and fail-fast block execution
- added structured block/action stdout tags for UI parsing
- added `BlockResult` and block-aware mission reporting
- switched custom controls to just-in-time loading per hunt

## Footer

**Version:** 0.0.9.8

Apache-2.0.