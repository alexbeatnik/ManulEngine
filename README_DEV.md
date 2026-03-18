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

## Runtime Shape

ManulEngine now has three distinct but connected layers:

1. File parsing through `parse_hunt_file()` in `cli.py`
2. Hierarchical block parsing through `parse_hunt_blocks()` in `helpers.py`
3. Execution through `run_mission()` in `core.py` or `run_steps()` in `api.py`

That split is deliberate. `parse_hunt_file()` still owns headers, hook extraction, tags, vars, and file-line bookkeeping. The runtime block model is created later by `parse_hunt_blocks()`, which turns mission text into block-aware execution objects.

## Repository Pointers

| File | Responsibility |
| --- | --- |
| `pyproject.toml` | Package metadata and release version |
| `manul_engine/cli.py` | CLI parsing, `ParsedHunt`, hook orchestration, data-driven iteration, breakpoint line mapping |
| `manul_engine/helpers.py` | `classify_step()`, `parse_logical_step()`, `parse_hunt_blocks()`, `HuntBlock` |
| `manul_engine/core.py` | Browser lifecycle, hierarchical mission runner, structured stdout, action dispatch |
| `manul_engine/api.py` | `ManulSession` programmatic facade and inline DSL execution |
| `manul_engine/controls.py` | Custom control registry and lazy loading |
| `manul_engine/reporting.py` | `StepResult`, `BlockResult`, `MissionResult`, `RunSummary` |
| `manul_engine/reporter.py` | HTML report generation |

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

## `run_mission()` Flow

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
- a breakpoint on a child action maps to that action’s runtime index

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

## `ManulSession`

`api.py` is now a first-class surface, not an afterthought.

`ManulSession` owns:

- Playwright lifecycle
- direct navigation and interaction helpers
- `run_steps()` for inline DSL execution without spinning up the CLI path

The inline runner was updated to use the same hierarchical block model as `run_mission()` so behavior stays aligned between `.hunt` and pure-Python usage.

When changing DSL execution semantics, update both:

- `manul_engine/core.py`
- `manul_engine/api.py`

## Lazy Loading for Custom Controls

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

## Parser Responsibilities

### `parse_hunt_file()` in `cli.py`

Still returns the 10-field `ParsedHunt` named tuple:

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

## Heuristic and API Rules That Still Matter

- Confidence is documented and explained on a normalized `0.0` to `1.0` scale
- `model: null` remains the recommended default
- Ollama is optional and fallback-only
- desktop automation through `executable_path` and `OPEN APP` must remain supported
- Python escape hatches are explicit and should not be hidden behind vague AI framing

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

- Promoted `ManulSession` as a first-class public API
- Introduced hierarchical block parsing and fail-fast block execution
- Added structured block/action stdout tags for UI parsing
- Added `BlockResult` and block-aware mission reporting
- Switched custom controls to just-in-time loading per hunt

## Footer

**Version:** 0.0.9.8

Apache-2.0.
