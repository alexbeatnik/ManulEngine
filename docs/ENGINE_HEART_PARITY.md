# ManulEngine ↔ ManulEngine (Go) — Parity Audit

> Working document for bringing **ManulEngine** (Python, `/ManulEngine`) and
> **ManulEngine (Go)** (Go, `/ManulEngineGo`) to identical functionality, and updating
> the **VS Code extension** (`/ManulEngineExtension`) to work with both.
>
> **Direction policy:** *best-of / case-by-case* — for each divergence the
> more complete/correct side is the reference; the other is brought up to it.
> Per-runtime intentional splits (e.g. `CALL PYTHON` vs `CALL GO`) are **kept**.

Status legend: ✅ aligned · ⚠️ divergent (fix) · ➖ intentional per-runtime split

> Naming note: **"Heart"** below is historical shorthand for **ManulEngine (Go)**
> (the project was renamed from *ManulHeart* during 0.1.0); "Engine" = ManulEngine (Python).

---

## 0. Already aligned (no work)

- **Scorer weights** — both: `cache 2.0 · semantics 0.60 · text 0.45 · attributes 0.25 · proximity 0.10`
  (Engine `scoring.py:WEIGHTS`, Heart `pkg/scorer/scorer.go:58‑64`; both have `scoring_math` golden tests). ✅
- **Core DSL verbs** — NAVIGATE/CLICK/FILL/TYPE/SELECT/HOVER/DRAG/PRESS/VERIFY/EXTRACT/SCROLL/WAIT/SET/MOCK/IF/ELIF/ELSE/REPEAT/WHILE/FOR EACH/USE/DONE/STEP, plus RIGHT CLICK, DOUBLE CLICK, UPLOAD, CHECK/UNCHECK. ✅
- **Agent CLI surface** — both expose `schema` / `map` / `read` / `run-step`. ✅ (JSON shape parity → §5)
- **Runtime is CDP-native** — both drive system Chrome over CDP, no Playwright. ✅

---

## 1. DSL divergences

| Item | Engine | Heart | Best-of direction | Pri |
|---|---|---|---|---|
| `OPEN APP` (attach Electron/running Chrome) | ✅ | ✗ | **Add to Heart** (it already has `--cdp`/`--executable-path` to attach) | High |
| `SCAN PAGE` (in-DSL scan step) | ✅ | ✗? (has `scan` CLI only) | **Add to Heart** in-DSL step | Med |
| `PRINT` / `SCREENSHOT` explicit steps | ✗? | ✅ (`CmdPrint`,`CmdScreenshot`) | **Add to Engine** | Med |
| `PAUSE` / `HIGHLIGHT` / `DEBUG VARS` debug steps | partial (`DEBUG`) | ✅ (`CmdPause`,`CmdHighlight`,`CmdDebugVars`) | **Reconcile** debug-step vocabulary both ways | Med |
| `CALL STEP` (invoke named STEP) | ✗ (uses `USE`/imports) | ✅ (`CmdCallStep`) | Decide: keep Engine `USE` model, or add `CALL STEP` to both | Low |
| `VERIFY FIELD` / `VERIFY SOFTLY` naming | `VERIFY ENABLED/CHECKED`, `… SOFTLY` | `CmdVerifyField`,`CmdVerifySoft` | **Normalize wording** so both parse the same text | Med |
| Block terminators (`END IF`/`END REPEAT`/…) | implicit/`END` tolerant | explicit `CmdEnd*` | Confirm both accept the same forms | Low |
| `CALL PYTHON` ↔ `CALL GO` | `CALL PYTHON` | `CALL GO` | ➖ intentional per-runtime; both must reject the other's verb cleanly | — |

## 2. CLI subcommands & flags

| Item | Engine | Heart | Best-of direction | Pri |
|---|---|---|---|---|
| `--cdp <endpoint>` (attach to running browser) | ✗ | ✅ | **Add to Engine** | High |
| `--json` / `--jsonl` (machine output) | agent CLI only | ✅ on `run` | **Add to Engine** `run` | High |
| `--target` / `--user-data-dir` | ✗ | ✅ | **Add to Engine** | Med |
| `--verbose` | ✗ (uses `MANUL_LOG_LEVEL`) | ✅ | **Add to Engine** alias | Low |
| `--workers` | ✅ real (multiprocessing) | ⚠️ placeholder (`_ = fs.Int`) | **Wire Heart's flag to its existing `pkg/worker.WorkerPool`** | High |
| `--browser` | ✅ (chromium/electron) | ⚠️ placeholder + stale "firefox/webkit" help | **Make Heart honor/validate it** (chromium/electron); drop firefox/webkit text | Med |
| `--html-report` default | `false` | `true` | **Pick one default** (recommend `false`, CI-predictable) | Med |
| `--disable-cache` | ✗ (uses `semantic_cache` config) | ✅ | **Add `--disable-cache` alias to Engine** mapped to semantic cache | Med |
| `pack` / `install` (`.huntlib`) | ✅ | ✗ | Decide: port to Heart, or mark Engine-only in both contracts | Low |
| `pages` / `controls` subcommands | ✅ | ✅ | Confirm identical args/output | Med |

## 3. Config keys & env vars

Engine `EngineConfig`: `headless, browser, browser_args, channel, executable_path, timeout, nav_timeout, semantic_cache_enabled, auto_annotate, retries, screenshot, html_report, explain_mode, log_name_maxlen, log_thought_maxlen, tests_home, verify_max_retries, custom_controls_dirs`.

| Env var | Engine | Heart | Best-of direction | Pri |
|---|---|---|---|---|
| `MANUL_CHANNEL` | ✅ | ✗ | **Add to Heart** (channel→binary resolution) | Med |
| `MANUL_BROWSER_ARGS` (env) | ✅(JSON+code) | ✅ | confirm same parsing (comma/space) | Low |
| `MANUL_CDP_ENDPOINT` | ✗ | ✅ | **Add to Engine** (pairs with `--cdp`) | Med |
| `MANUL_DISABLE_CACHE` | ✗ (`MANUL_SEMANTIC_CACHE_ENABLED`) | ✅ | **Unify**: support both names on both sides | Med |
| `MANUL_VERBOSE` / `MANUL_DEBUG` / `MANUL_DEBUG_PAUSE` | partial | ✅ | **Add to Engine** | Low |
| `MANUL_EXPLAIN_NEXT` | ? | ✅ | confirm/add to Engine | Low |
| `MANUL_TAGS` (env) | ✗ (flag only) | ✅ | **Add env to Engine** | Low |
| `MANUL_LOG_NAME_MAXLEN` / `…_THOUGHT_MAXLEN` | ✅ | ✗ | **Add to Heart** | Low |
| `MANUL_TESTS_HOME` | ✅ | ✅ | aligned | — |

## 4. Reporter & artifacts

- Both have HTML reports + `run_history.json` (Engine `reporter.py`/`reporting.py`; Heart `pkg/report/{index,run_history}.go`).
- **DONE / verified aligned:** the shared, cross-consumed artifact **`run_history.json` is byte-shape identical** — both engines write exactly `{file, name, timestamp, status, duration_ms}` (no `healed` on either side), and the extension's `schedulerPanel.ts` reader consumes exactly those fields. ✅ No change needed.
- HTML markup + `manul_report_state.json` are **engine-internal** report-generation artifacts (Python template vs Go template; report-session merge is Engine-only). They are not consumed cross-engine; acceptably divergent per the policy (structure/`flaky`/`warning` semantics already match). No action.

## 5. Agent CLI JSON shape (`schema`/`map`/`read`/`run-step`)

- Engine `agent_cli.py`; Heart `pkg/agent/{agent,describe,render}.go` + `run-step`/`read`/`map`/`schema`.
- **Diffed `manul schema` (no browser):** top-level keys **identical** (`agent_commands, engine, failure_reasons, hunt_rules, page_map, step_outcome, targeting, verbs, version`); `page_map` shape **identical**. ✅
- **DONE:** Engine `verbs` list was missing its own `CHECK`/`UNCHECK`/`PRINT`/`SCREENSHOT` — added (Engine agent schema now matches its DSL).
- **DONE (best-of):**
  - **`verb` naming** normalized to the human DSL form in Heart (`DOUBLE CLICK`, `RIGHT CLICK`, `UPLOAD`, `VERIFY SOFTLY`, `WAIT FOR`, `WAIT FOR RESPONSE`, `FOR EACH`, `CALL GO`). ✅
  - **`failure_reasons` now identical** in both: `ok, not_found, ambiguous, timeout, verify_failed, action_failed`. Engine's run-step now maps timeout errors → `timeout` and refines failures: no candidates → `not_found`, candidates-but-low-confidence → `ambiguous`. ✅
  - **`step_outcome.score`** documented + emitted in both. ✅
  - **`run-step --compact`** accepted by both (Engine output is already compact). ✅
  - **`MOCK`** added to Heart's verbs (it supports `CmdMock`). ✅
- **Intentional residual (not divergences):** `CALL PYTHON` (Engine) vs `CALL GO` (Heart) — per-runtime; `FULL SCAN`/`SCAN PAGE`/`WAIT FOR SELECTOR` are Engine-only features Heart doesn't implement.
- **DONE — live-diffed on a shared fixture page (2026-07-02):** one headless Chrome, both engines attached over CDP:
  - `map` — **byte-identical** after adding `editable` to Heart's `MapElement`. ✅
  - `read` (targeted + `--selector`) — identical values and JSON shape; Heart now always emits JSON (was plain text by default). ✅
  - `run-step` — Heart now defaults to the compact StepOutcome JSON (was human log; `--json` keeps the full ExecutionResult as a Go extra). Same element resolved by both. ✅
  - **Fixed in Heart:** flags after positionals were silently ignored (`manul read 'X' --cdp …` connected to the default 9222) — Go's `flag` stops at the first non-flag; added interleaved parsing to `read`/`run-step`/`scan`/`record`/`daemon`. ✅
  - **Fixed in Heart:** `VERIFY '<label>' has value|text|placeholder "<expected>"` parsed but was **unimplemented at runtime** (always failed with `target ''`) — implemented the attribute form. ✅
  - **Fixed in Engine:** `NAVIGATE to file://…` was rejected (`https?://`-only regex) — file:// is now first-class, like Heart. ✅
  - **E2E:** the same .hunt (NAVIGATE file:// → VERIFY present → FILL → VERIFY has value → CLICK → VERIFY → PRINT) **passes on both engines**, exit 0; `run_history.json` JSONL entries identical in shape. ✅
- **Known residual divergence (open):** `run-step`/`Step` **`score` scale** — Engine emits `raw/SCALE` confidence (e.g. `0.837`), Heart emits the scorer's clamped total (`clamp(raw,0,1)` → `1.0` on strong matches). Same winner either way; align the mapping later (pick one presentation, update both contracts + tests).

## 6. Contracts (the frozen shared surface) — biggest structural gap

| Repo | Has | Missing |
|---|---|---|
| Engine | 8× `MANUL_*_CONTRACT.md` | `EXTENSION_ENGINE_CONTRACT.md` |
| Heart | `EXTENSION_ENGINE_CONTRACT.md` | all 8× `MANUL_*_CONTRACT.md` |
| Extension | vendors the 8× `MANUL_*_CONTRACT.md` | — |

**DONE:**
- `EXTENSION_ENGINE_CONTRACT.md` is now in **all three** repos, byte-identical (framing updated for both runtimes).
- Engine + Extension carry the full 8× `MANUL_*` set (synced; current — cdp/json/print/screenshot, no model/ai/cache).
- **Heart adoption — DONE (9/9).** Heart now carries the full contract set, all JSON blocks valid, `go build ./...` green:
  - *Mechanically reconciled (5):* `SCORING`, `REPORTING`, `CONFIG`, `CLI`, `DSL` — Go paths under `pkg/`/`cmd/manul`; `CALL GO` for `CALL PYTHON`; Engine-only items removed (`pack`/`install` from CLI; `FULL SCAN`/`SCAN PAGE`/`WAIT FOR SELECTOR` from DSL); stale `firefox`/`webkit` browser values fixed to `chromium`/`electron` in all 3 repos; "shared surface" header on each.
  - *Authored against Heart internals (3):*
    - `MANUL_HOOKS` — `[SETUP]`/`[TEARDOWN]` blocks + `RegisterGoCall`/`RegisterCustomControl` process-init registration + `GoCallInvocation` + 5-level `ScopedVariables`. Documents the absence of Python `@before_all`/`MANUL_GLOBAL_VARS`.
    - `MANUL_DEBUG` — shared stdin/stdout wire protocol (pause/explain markers, commands, 1-based idx) cross-referencing `EXTENSION_ENGINE_CONTRACT`; `shouldPause` state; `explainNextPayload` (10 fields); notes Heart's `explain-next` is read-only (no `!execute` What-If injection).
    - `MANUL_API` — Heart's Go embedding API (`pkg/agent`: `Options`/`Launch`/`Attach`/`Session.{Read,ReadText,Step,Run,Map,Close}` + `Value`/`StepOutcome`/`RunOutcome`/`PageMap`/`Reason`), replacing the Python `ManulSession` contract.
  - `EXTENSION_ENGINE_CONTRACT` already present (×3 repos, identical).

## 7. Extension (`/ManulEngineExtension`) — Phase 2 (after parity)

Dual-runtime plumbing already exists (`runtimeDetector.ts` python/go, `CALL GO`/`CALL PYTHON`, per-runtime min-versions, DSL filtering in `shared/index.ts`). Work needed:

- ⚠️ **Dead persistent-cache surface** — Engine removed the on-disk controls cache and Heart never had one. Remove: `cacheTreeProvider.ts` (+ test), `manul.clearAllCache`/`clearSiteCache`/`refreshCache` commands, the Cache tree view, and `controls_cache_dir` reads in `configPanel.ts`. Pri: High.
- **Config panel** — drop any removed keys (`model`, `ai_*`, `controls_cache_*`); keep `semantic_cache_enabled`. Pri: High.
- **Min versions / version probe** — `MIN_MANUL_ENGINE_VERSION` (0.0.9.29) and `MIN_MANUL_ENGINE_GO_VERSION` are stale vs Engine 0.1.0; align to the reconciled CLI surface. Pri: Med.
- **Sync `contracts/`** with the reconciled §6 set; honor `EXTENSION_ENGINE_CONTRACT.md` as the wire spec. Pri: Med.
- Verify every spawn path (run/debug/scan/record/daemon) against **both** reconciled CLIs.

---

## Execution order (parity first, per user)

1. **Contracts (§6)** — establish the shared frozen surface in both repos. *No code-behavior change; safe.*
2. **Agent JSON (§5)** + **reporter (§4)** — machine surfaces external tools depend on.
3. **CLI flags/subcommands (§2)** — `--cdp/--json/--jsonl` into Engine; wire Heart `--workers`→WorkerPool, honor `--browser`; align `--html-report` default & `--disable-cache`.
4. **Config/env (§3)** — unify env-var names both ways.
5. **DSL (§1)** — `OPEN APP`→Heart; `PRINT`/`SCREENSHOT`→Engine; normalize VERIFY/debug wording.
6. **Extension (§7)** — kill dead cache surface, fix config panel/min-versions, sync contracts.

**Verification each batch:** Engine `python run_tests.py` (54 suites must stay green) · Heart `go test ./...` · Extension `npm run compile` + vitest. Keep both suites green batch-to-batch; never bump versions (user controls releases).
