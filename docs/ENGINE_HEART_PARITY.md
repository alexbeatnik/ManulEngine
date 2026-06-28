# ManulEngine ↔ ManulHeart — Parity Audit

> Working document for bringing **ManulEngine** (Python, `/ManulEngine`) and
> **ManulHeart** (Go, `/ManulHeart`) to identical functionality, and updating
> the **VS Code extension** (`/ManulEngineExtension`) to work with both.
>
> **Direction policy:** *best-of / case-by-case* — for each divergence the
> more complete/correct side is the reference; the other is brought up to it.
> Per-runtime intentional splits (e.g. `CALL PYTHON` vs `CALL GO`) are **kept**.

Status legend: ✅ aligned · ⚠️ divergent (fix) · ➖ intentional per-runtime split

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
- **Action:** diff the **run_history.json record shape** and the **report JSON** field-by-field; align keys/semantics. HTML *markup* need not be byte-identical, but section structure + status/`flaky`/`warning` semantics must match. (Note: Engine just removed the `healed` field — Heart must not emit it either.) Pri: Med.

## 5. Agent CLI JSON shape (`schema`/`map`/`read`/`run-step`)

- Engine `agent_cli.py`; Heart `pkg/agent/{agent,describe,render}.go` + `run-step`/`read`/`map`/`schema`.
- **Diffed `manul schema` (no browser):** top-level keys **identical** (`agent_commands, engine, failure_reasons, hunt_rules, page_map, step_outcome, targeting, verbs, version`); `page_map` shape **identical**. ✅
- **DONE:** Engine `verbs` list was missing its own `CHECK`/`UNCHECK`/`PRINT`/`SCREENSHOT` — added (Engine agent schema now matches its DSL).
- ⚠️ **Remaining divergences (semantic — need decisions, do not guess):**
  - **`verb` naming:** Engine uses DSL spaces (`DOUBLE CLICK`, `VERIFY SOFTLY`, `WAIT FOR`, `FOR EACH`); Heart uses enum form (`DOUBLE_CLICK`, `VERIFY_SOFT`, `WAIT_FOR`, `FOR_EACH`). Best-of = the human DSL form (what agents write) → normalize Heart's `verb` field to spaces.
  - **`failure_reasons`:** Heart superset adds `ambiguous`, `timeout`. Engine only emits `ok/not_found/verify_failed/action_failed`. Advertising reasons Engine never emits is misleading → either Engine starts emitting them (resolver/action change, golden-test risk) or Heart documents them as Heart-only.
  - **`step_outcome.score`:** Heart includes a numeric `score`; Engine's outcome omits it. Engine has the confidence internally → could add, but it's a run-step output-shape change.
  - **`run-step --compact`:** Heart has it (compact StepOutcome); Engine `run-step` lacks `--compact`.
  - Not yet diffed: `map`/`read`/`run-step` live JSON (need a fixture page on both). Pri: High but decision-gated.

## 6. Contracts (the frozen shared surface) — biggest structural gap

| Repo | Has | Missing |
|---|---|---|
| Engine | 8× `MANUL_*_CONTRACT.md` | `EXTENSION_ENGINE_CONTRACT.md` |
| Heart | `EXTENSION_ENGINE_CONTRACT.md` | all 8× `MANUL_*_CONTRACT.md` |
| Extension | vendors the 8× `MANUL_*_CONTRACT.md` | — |

**Action (high value, low risk):** both engines should carry the **same full set** — the 8 `MANUL_*` contracts **and** `EXTENSION_ENGINE_CONTRACT.md`. Reconcile content where behavior diverges (e.g. `CALL GO` vs `CALL PYTHON`, no `controls_cache`/`model`/`healed`). The extension's `contracts/` then mirrors the reconciled set. Pri: High.

## 7. Extension (`/ManulEngineExtension`) — Phase 2 (after parity)

Dual-runtime plumbing already exists (`runtimeDetector.ts` python/go, `CALL GO`/`CALL PYTHON`, per-runtime min-versions, DSL filtering in `shared/index.ts`). Work needed:

- ⚠️ **Dead persistent-cache surface** — Engine removed the on-disk controls cache and Heart never had one. Remove: `cacheTreeProvider.ts` (+ test), `manul.clearAllCache`/`clearSiteCache`/`refreshCache` commands, the Cache tree view, and `controls_cache_dir` reads in `configPanel.ts`. Pri: High.
- **Config panel** — drop any removed keys (`model`, `ai_*`, `controls_cache_*`); keep `semantic_cache_enabled`. Pri: High.
- **Min versions / version probe** — `MIN_MANUL_ENGINE_VERSION` (0.0.9.29) and `MIN_MANUL_HEART_VERSION` are stale vs Engine 0.1.0; align to the reconciled CLI surface. Pri: Med.
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
