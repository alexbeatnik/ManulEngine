# CLAUDE.md — ManulEngine

**Version:** 0.1.0
**Project:** Deterministic, DSL-first browser & desktop automation runtime driving system Chrome directly over the Chrome DevTools Protocol (CDP, in `manul_engine/cdp/`). Fully deterministic — NO in-engine LLM; external LLM agents drive it via the agent CLI (`manul map`/`run-step`/`read`/`schema`). (Playwright AND the optional Ollama layer were both removed during 0.1.0 — single runtime dep: `websockets`.)

This file is the operating manual for Claude Code working in this repo. It is loaded into every Claude session here. Keep it short, factual, and current — don't restate the README.

---

## Architecture in 30 seconds

```
manul_engine/
  __init__.py     re-exports the public API (ManulEngine, ManulSession, custom_control, …)
  api.py          ManulSession  — high-level async context manager (Python-only users)
  core.py         ManulEngine   — DSL runner (.hunt files); composed from mixins
  actions.py      _ActionsMixin — click / fill / select / hover / drag executors
  debug.py        _DebugMixin   — interactive debug pause + extension-protocol handshake
  helpers.py      pure functions: parse_hunt_blocks, classify_step, substitute_memory, …
  hooks.py        @before_all / @after_group lifecycle + CALL PYTHON
  imports.py      @import / USE block resolution for .hunt libraries
  controls.py     @custom_control registry (page-scoped overrides)
  scoring.py      heuristic element scorer (text · attrs · semantics · proximity · cache)
  agent_cli.py    agent-facing CLI: schema/map/read/run-step (JSON for external LLM drivers)
  scanner.py      DOM snapshot → draft .hunt file (manul scan <URL>)
  recorder.py     interactive recorder (manul record <URL>)
  reporter.py     HTML + JSON test reports
  scheduler.py    daemon mode (cron-style @schedule:)
  cdp/            native Chrome DevTools Protocol backend (replaces Playwright):
                    conn.py (WebSocket JSON-RPC), chrome.py (launch system Chrome),
                    page.py (CDPPage/CDPFrame/CDPElement, per-frame exec contexts),
                    browser.py (CDPBrowser), protocol.py + keys.py (JS/key maps)
  variables.py    ScopedVariables (5 levels: row > step > mission > global > import)
  prompts.py      global config (THRESHOLDS, BROWSER_ARGS, …)
  config.py       EngineConfig dataclass (injectable; takes priority over prompts.* globals)
  cli.py          manul CLI entry point (sync_main → asyncio runner)
  test/           54 synthetic-DOM unit tests (test_00..test_53, run via run_tests.py)
contracts/        MANUL_*_CONTRACT.md — frozen public-surface contracts (DSL/API/CLI/etc.)
custom-instructions/  AI assistant instruction snippets (Cursor/Copilot/Claude)
demo/             example .hunt suites used in CI smoke runs
docs/, prompts/, reports/   runtime artifacts and docs
```

`ManulEngine` inherits from two mixins (`_DebugMixin, _ActionsMixin`). Action handlers live in `actions.py`; the orchestration loop lives in `core.py:run_mission`. The conditional-branch path lives in `core.py:_dispatch_step` and intentionally mirrors the main loop — these two paths are sibling executors, **not** duplicates. Don't merge them blindly.

## Public surface (do NOT silently break)

The contracts in `contracts/MANUL_*_CONTRACT.md` are load-bearing. If you change anything that's documented there — DSL keywords, CLI flags, `ManulSession` / `ManulEngine` ctor kwargs, `EngineConfig` fields, hook/lifecycle decorators, reporter JSON shape, scoring weights — you **must** update the matching contract file in the same change and bump the version. The `__init__.py` `__all__` list is the runtime mirror of these contracts.

## Configuration layering (highest → lowest precedence)

1. Explicit kwargs to `ManulEngine(…)` / `ManulSession(…)`
2. `EngineConfig` instance passed via `config=`
3. Module globals in `manul_engine/prompts.py` (read at construction time, **not** at runtime)
4. Environment variables (`MANUL_*`)
5. `manul_engine_configuration.json`

Never read `prompts.X` at runtime — read once at `__init__` and store on `self`. The same applies to `EngineConfig`. There is one deliberate exception: `prompts.lookup_page_name()` is mtime-cached so live edits to `pages.json` are picked up within a mission.

## Versioning rule

Single source of truth: `pyproject.toml → version`. Use `bump_version.py <new>` — it updates 18 files (READMEs, Dockerfile, docker-compose.yml, GitHub workflows, contracts, copilot/cursor instruction files). Never edit version strings by hand. Confirm with `python bump_version.py --show`. Bump the version in the same change as any contract-affecting code change.

## DSL invariants (`.hunt` files)

- A `.hunt` file is plain UTF-8 text. Headers (`@title:`, `@context:`, `@var:`, `@tags:`, `@data:`, `@schedule:`, `@import:`, `@export:`) appear before the first numbered step.
- Steps may be **numbered** (`1. Click "Login"`) or **unnumbered** (raw action lines). Both forms parse via `parse_hunt_blocks`.
- Blocks are delimited by `STEP <name>` / `END STEP`; conditional control flow is `IF / ELIF / ELSE / END IF`; loops are `LOOP / END LOOP` (also `WHILE`, `FOR ROW`).
- Hunt files are interpreted, not compiled. Errors are surfaced through `MissionResult.status` (`pass` / `warning` / `fail`) plus `StepResult.error`.

## What to fix vs. leave alone

- **Always fix:** import-after-statement, function-local imports of stdlib modules already needed at module scope, dead `_kwargs.pop` defaults, `except Exception: pass` without `_log.debug`, version drift between `pyproject.toml` and a contract.
- **Leave alone:** the seemingly-duplicated step execution in `core.py:run_mission` vs `_dispatch_step` (they intentionally mirror); the `STEP` / `END STEP` whitespace tolerance; the per-mixin `_log = logger.getChild("<mod>")` pattern; the explicit `# noqa: …` and ruff per-file ignores in `pyproject.toml` — they are deliberate.
- **Ask first:** any change to `scoring.py` weights or `THRESHOLD_*` constants in `core.py` (these change test golden numbers); any new public kwarg on `ManulEngine` / `ManulSession`; any new DSL keyword.

## Tests

- Run all: `python run_tests.py` (imports each `test_*.py` and calls its `run_laboratory()`/`run_suite()` — these are function-based suites, **not** `unittest.TestCase`).
- Run one: run the file as a script — `python manul_engine/test/test_34_scoring_math.py`. (`python -m unittest manul_engine.test.test_34_scoring_math` reports "Ran 0 tests" — there are no TestCases.)
- Tests use synthetic DOM HTML loaded via `CDPPage.set_content()` / `file://`, driven by system Chrome over CDP, no external network. They exercise scoring, parsing, lifecycle, recording, scheduling, the full DSL surface, and the reporter. Don't add real-network tests — keep the suite hermetic.
- The ruff per-file-ignores for `manul_engine/test/*` are intentional; tests intentionally use shadowing, unused locals, and asserts.

## Style & tone

Match the existing logging idiom: `_log = logger.getChild("<module>")` at the top, `print("    🐾 …")` for user-facing CLI output (the indented emoji prefixes are part of the UX — don't strip them in refactors), `_log.debug(…)` for engine internals. Don't introduce new top-level helpers in `core.py` — push pure logic into `helpers.py` or `scoring.py`.

## Common pitfalls

- Adding a new step kind: register it in `helpers.classify_step`, add the dispatch branch in **both** `core.py:run_mission` (main loop) and `core.py:_dispatch_step` (conditional-branch executor), then add a `test_NN_*.py` covering at least the happy path and one failure path.
- Touching `BROWSER_ARGS` / `HEADLESS_MODE` / `BROWSER` defaults: update `prompts.py`, `config.py`, the README "Configuration" table, and `MANUL_CONFIG_CONTRACT.md`.
- The only cache is the in-session **semantic cache** (`learned_elements`, `semantic_cache_enabled`): it feeds the scorer as one channel and never bypasses scoring. There is no persistent on-disk controls cache — it was removed because a cached entry could resolve to a different live element.
