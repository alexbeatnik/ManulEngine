# Reports & Explainability

> **ManulEngine v0.0.9.29**

ManulEngine provides multiple layers of observability: HTML reports with screenshots, per-channel scoring breakdowns, and an interactive What-If Analysis REPL.

## HTML Reports

### Generating a report

```bash
manul --html-report tests/
manul --html-report --screenshot on-fail tests/    # screenshots on failure
manul --html-report --screenshot always tests/     # screenshot every step
```

This creates `reports/manul_report.html` — a self-contained, dark-themed HTML file with no external dependencies.

### Report features

- **Dashboard stats**: total tests, passed, failed, flaky, total duration, pass-rate progress bar
- **Collapsible accordions**: each mission and each STEP block is a `<details>/<summary>` accordion. Failed blocks auto-expand; passed blocks are collapsed by default
- **Inline screenshots**: base64-encoded PNGs embedded directly in the HTML (no external files)
- **Tag filter chips**: dynamically generated from all missions' `@tags`; click to filter
- **"Show Only Failed" toggle**: checkbox in the control panel to hide passing tests
- **Run Session banner**: shows session ID and merged invocation count

### Screenshot modes

| Mode | CLI flag | Behavior |
|------|----------|----------|
| **on-fail** (default) | `--screenshot on-fail` | Captures a screenshot only when a step fails |
| **always** | `--screenshot always` | Captures a screenshot after every step (forensic) |
| **none** | `--screenshot none` | No screenshots |

### Session merging

When you run `manul --html-report` multiple times, recent invocations within the same report session are **merged** into a single HTML file instead of overwriting it. The session state is persisted in `reports/manul_report_state.json`.

This means you can run different test files or retries and see all results aggregated in one report.

### Run history

Each test run appends a JSON Lines entry to `reports/run_history.json`:

```json
{"file": "tests/login.hunt", "name": "Login Smoke", "timestamp": "2026-04-14T10:30:00", "status": "pass", "duration_ms": 3400}
```

The VS Code extension's Scheduler Dashboard reads this file to display sparkline history per hunt file.

---

## Explain Mode

Explain mode reveals exactly how the engine scored and selected each element. This is the primary debugging tool when a step resolves to the wrong element or fails unexpectedly.

### Enabling explain mode

```bash
manul --explain tests/login.hunt
```

Or set in configuration:

```json
{
  "explain_mode": true
}
```

### Reading the output

For each resolved element, explain mode prints a per-channel breakdown:

```text
┌─ EXPLAIN: Target = "Login"
│  Step: Click the 'Login' button
│
│  #1 <button> "Login"
│     total:      0.593
│     text:       0.281
│     attributes: 0.050
│     semantics:  0.225
│     proximity:  0.037
│     cache:      0.000
│
│  #2 <a> "Login link"
│     total:      0.312
│     text:       0.187
│     attributes: 0.025
│     semantics:  0.100
│     proximity:  0.000
│     cache:      0.000
│
└─ Decision: selected "Login" with score 0.593
```

### Scoring channels explained

| Channel | Weight | What it measures |
|---------|--------|------------------|
| **cache** | 2.0 | Semantic cache reuse (in-session learned elements) and persistent controls cache match |
| **semantics** | 0.60 | Element type alignment, dev naming conventions, checkbox/radio strictness |
| **text** | 0.45 | Text content match: `data-qa`, `aria-label`, `placeholder`, visible text, `name` attribute |
| **attributes** | 0.25 | HTML `id`, class names, structural attributes |
| **proximity** | 0.10 | DOM depth reuse (or contextual distance when `NEAR`/`ON HEADER`/`ON FOOTER`/`INSIDE` is active) |

**Final score** = weighted sum × penalty multiplier × SCALE (177,778).

**Penalties:**
- Disabled element: ×0.0 (zeroes the entire score)
- Hidden element: ×0.1

### Key scoring signals

| Signal | Score impact | Channel |
|--------|-------------|---------|
| Semantic cache hit | +1.0 (≈355k scaled) | cache |
| `data-qa` exact match | +1.0 (≈80k scaled) | text |
| `html_id` exact match | +0.6 (≈26k scaled) | attributes |
| Exact text/aria/placeholder | +0.625 (≈50k scaled) | text |
| Element type alignment | +0.05–0.30 | semantics |
| Contextual reuse (same xpath) | +0.05 (≈17k scaled) | cache |

### When to use explain mode

- A step resolves to the **wrong element** — explain mode shows which signals are pulling toward the wrong candidate
- A step **fails to resolve** — the scoring breakdown shows whether any candidates scored above the threshold
- You're writing **custom controls** — use explain mode to verify the heuristic isn't already handling the element well
- **Debugging disambiguation** — see how `NEAR`, `ON HEADER`, `INSIDE` qualifiers affect the proximity channel

---

## What-If Analysis REPL

During a `--debug` pause, you can evaluate hypothetical steps against the live DOM without executing them.

### Terminal mode

```bash
manul --debug tests/login.hunt
```

When paused at a step, type `w` to enter the What-If REPL:

```text
[PAUSED] Step 3: Click the 'Submit' button
> w

═══ What-If Analysis REPL ═══
Type a step to evaluate, or 'q' to quit.

what-if> Click the 'Login' button
───────────────────────────
Confidence: 8.5 / 10
Match: <button> "Login" (score: 0.593)
Risk: LOW — single strong candidate
Suggestion: Step should resolve correctly
───────────────────────────

what-if> Fill 'NonExistent' with 'test'
───────────────────────────
Confidence: 1.2 / 10
Match: <input> "Search" (score: 0.089)
Risk: HIGH — no strong match found
Suggestion: No element matches 'NonExistent'. Check the target name.
───────────────────────────

what-if> q
```

### One-shot explain (terminal)

Type `e` at a debug pause for one-shot evaluation of the current step without entering the REPL.

### VS Code extension

During a debug pause in the VS Code extension, click the **"Explain Current Step"** button (lightbulb icon) in the editor title bar. The extension sends `explain-next` via the debug protocol and displays the scoring breakdown.

The `ExplainHoverProvider` also shows hover tooltips over resolved step lines with the per-channel breakdown.

---

## Interpreting Results

### Mission statuses

| Status | Meaning |
|--------|---------|
| `pass` | All steps and all verifications succeeded |
| `fail` | One or more steps failed |
| `broken` | `[SETUP]` hook failed — browser steps were skipped |
| `warning` | All hard verifications passed, but one or more `VERIFY SOFTLY` failed |

### Block-level output

```text
[📦 BLOCK START] STEP 1: Open the login page
  [▶️ ACTION START] NAVIGATE to https://example.com
  [✅ ACTION PASS]  NAVIGATE to https://example.com (1.2s)
  [▶️ ACTION START] VERIFY that 'Sign In' is present
  [✅ ACTION PASS]  VERIFY that 'Sign In' is present (0.1s)
[🟩 BLOCK PASS] STEP 1: Open the login page
```

| Marker | Meaning |
|--------|---------|
| `[📦 BLOCK START]` | STEP block begins |
| `[▶️ ACTION START]` | Individual action begins |
| `[✅ ACTION PASS]` | Action succeeded (with duration) |
| `[❌ ACTION FAIL]` | Action failed — remaining block actions are skipped |
| `[🟩 BLOCK PASS]` | All actions in the block passed |
| `[🟥 BLOCK FAIL]` | One or more actions failed |

### Self-healing indicators

When the engine retries with self-healing:

```text
[🔄 RETRY 1/3] Scrolling and re-scanning...
[🛡️ SELF-HEAL] Blacklisted element #42, retrying with fresh snapshot
```

The engine scrolls, blacklists bad candidates, re-snapshots the DOM, and retries (up to 3 times).

### Diagnostic tips

| Symptom | What to check |
|---------|---------------|
| Wrong element clicked | Run with `--explain` to see scoring breakdown. Add a type hint (`button`, `link`) or contextual qualifier (`NEAR`, `INSIDE`) |
| Element not found | Verify the text matches what's visible on the page. Try `WAIT FOR 'Element' to be visible` before the action |
| Flaky results | Check if the page has animations or lazy loading. Add explicit waits. Consider using the controls cache |
| Slow resolution | Enable `controls_cache_enabled` and `semantic_cache_enabled` in config |
