# 😼 ManulEngine — The Mastermind

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)

ManulEngine is a relentless hybrid (neuro-symbolic) framework for browser automation and E2E testing.

Forget brittle CSS/XPath locators that break on every UI update — write tests in plain English.
Stop paying for expensive cloud APIs — leverage local micro-LLMs via **Ollama**, entirely on your machine.

Manul combines the blazing speed of **Playwright**, 20+ JavaScript DOM heuristics, and the reasoning of local neural networks. It is fast, private, and highly resilient to UI changes.

> The Manul goes hunting and never returns without its prey.

> **ManulEngine runs on a potato.**
> No GPU. No cloud APIs. No $0.02 per click.
> Just Playwright, heuristics, and optional tiny local models.

---

## 🚀 What's New: The Enterprise Update

* **Clean, Unnumbered DSL:** The requirement for line numbers before actions has been completely dropped. Scripts now read exactly like plain English (`NAVIGATE to url` instead of `1. NAVIGATE to url`).
* **Logical STEP Grouping:** `STEP [optional number]: [Description]` metadata blocks allow mapping manual QA cases directly into `.hunt` files. Unmatched quotes inside descriptions (e.g. `STEP: Pallas's cat`) are cleanly isolated.
* **Enterprise HTML Reporter:** The reporter is now dual-mode and zero-dependency, featuring native HTML5 accordions (`<details>`), auto-expanding failures, and a clean Flexbox layout instead of old-school tables.
* **Global Lifecycle Hooks:** `@before_all`, `@after_all`, `@before_group`, and `@after_group` orchestrate complex DB seeding and auth logic. `ctx.variables` are securely serialized across parallel `--workers`.
* **Bulletproof DOM Heuristics:** The updated `SNAPSHOT_JS` rigorously filters out invisible or hidden UI elements (like hidden sticky headers), and effortlessly handles deeply nested modern frameworks (e.g. Wikipedia Vector 2022 / Codex) by strongly prioritizing `aria-label` and `name_attr`.
* **VS Code Extension Polish:** The Step Builder is now context-aware, verifying `vscode.window.activeTextEditor` to prevent accidental insertions in non-`.hunt` files, and provides robust syntax highlighting for the unnumbered DSL.

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is handled by ultra-fast JavaScript and Python heuristics. The AI steps in only when genuine ambiguity arises.

When the LLM picker is used, Manul passes the heuristic score as a **prior** (hint) by default — the model can override the ranking only with a clear, disqualifying reason.

### 🛡️ Ironclad JS Fallbacks

Modern websites love to hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. Manul uses Playwright with `force=True` plus retries and self-healing; for Shadow DOM elements it falls back to direct JS helpers to keep execution moving.

### 🧠 Deep Accessibility Heuristics

Manul scores elements using 20+ signals including `aria-label`, `placeholder`, `name`, `data-qa`, `html_id`, semantic `input type`, and contextual section headings. This means it handles modern single-page apps (React, Vue, Angular) and complex design systems (like Wikipedia's Vector 2022 / Codex skin) without any tuning — accessibility attributes are treated as first-class identifiers.

### 🌑 Shadow DOM Awareness

The DOM snapshotter recursively inspects shadow roots and can interact with elements inside the shadow tree.

### 👻 Smart Anti-Phantom Guard & AI Rejection

Strict protection against LLM hallucinations. If the model is unsure, it returns `{"id": null}`; the engine treats that as a rejection and retries with self-healing.

### 🎛️ Adjustable AI Threshold

Control how aggressively Manul falls back to the local LLM via `manul_engine_configuration.json` (`ai_threshold` key) or the `MANUL_AI_THRESHOLD` environment variable. If not set, Manul auto-calculates it from the model size:

| Model size | Auto threshold |
|---|---|
| `< 1b` | `500` |
| `1b – 4b` | `750` |
| `5b – 9b` | `1000` |
| `10b – 19b` | `1500` |
| `20b+` | `2000` |

Set `MANUL_AI_THRESHOLD=0` to disable the LLM entirely and run fully on deterministic heuristics.

### 🗂️ Persistent Controls Cache

Successful element resolutions are stored per-site and reused on subsequent runs — making repeated test flows dramatically faster.

### 🔄 Automatic Retries — Tame Flaky Tests

Real-world E2E tests flake. Network hiccups, slow renders, third-party scripts — you name it. ManulEngine lets you retry failed hunts automatically:

```bash
manul tests/ --retries 2                # retry each failed hunt up to 2 times
manul tests/ --retries 3 --html-report  # retry + generate an HTML report
```

Or set `"retries": 2` in `manul_engine_configuration.json` for a permanent default. Each retry is a full fresh run — no stale state carried over.

### 📊 Enterprise HTML Reporter

One flag. One self-contained HTML file. Dark-themed dashboard with pass/fail stats, native HTML5 `<details>` step accordions, inline base64 screenshots, and XSS-safe output — zero external dependencies, zero CDN, zero server.

**Enterprise Upgrades:**
* **Dual-Mode Rendering:** If `STEP` blocks are used, steps are grouped into logical Accordions. Passing steps collapse by default; failing steps auto-expand to show exactly what broke.
* **Flexbox Layout:** Dropped clunky tables for a sleek Flexbox design ensuring perfect text alignment and zero text mashing.

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
#### Capturing return values with `into {var}`

Append `into {var_name}` (or `to {var_name}`) to bind the function’s return value directly into an in-mission variable:

```text
CALL PYTHON api_helpers.fetch_otp into {dynamic_otp}
Fill 'Security Code' field with '{dynamic_otp}'
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
| `VERIFY that [target] is DISABLED` | Assert element state |
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
- Append `into {var_name}` (or `to {var_name}`) to a `CALL PYTHON` step to bind the function’s return value into a variable: `CALL PYTHON api.fetch_otp into {otp}`. The value is converted to a string and available for `{placeholder}` substitution in all subsequent steps.
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
| `retries` | `0` | Number of times to retry a failed hunt file before marking it as failed (0 = no retries) |
| `screenshot` | `"on-fail"` | Screenshot capture mode: `"none"` (no screenshots), `"on-fail"` (default — failed steps only), `"always"` (every step) |
| `html_report` | `false` | Generate a self-contained HTML report after the run (`reports/manul_report.html`) |

---

## 📋 Available Commands

| Category | Command Syntax |
|---|---|
| **Navigation** | `NAVIGATE to [URL]` |
| **Input** | `Fill [Field] with [Text]`, `Type [Text] into [Field]` |
| **Click** | `Click [Element]`, `DOUBLE CLICK [Element]`, `RIGHT CLICK [Element]` |
| **Selection** | `Select [Option] from [Dropdown]`, `Check [Checkbox]`, `Uncheck [Checkbox]` |
| **Mouse Action** | `HOVER over [Element]`, `Drag [Element] and drop it into [Target]` |
| **Data Extraction** | `EXTRACT [Target] into {variable_name}` |
| **Verification** | `VERIFY that [Text] is present/absent`, `VERIFY that [Element] is checked/disabled` |
| **Page Scanner** | `SCAN PAGE`, `SCAN PAGE into {filename}` |
| **Debug** | `DEBUG` / `PAUSE` — pause execution at that step (use with `--debug` or VS Code gutter breakpoints) |
| **Keyboard** | `PRESS ENTER`, `PRESS [Key]`, `PRESS [Key] on [Element]` |
| **File Upload** | `UPLOAD 'File' to 'Element'` |
| **Flow Control** | `WAIT [seconds]`, `SCROLL DOWN` |
| **Finish** | `DONE.` |

> Append `if exists` or `optional` to any step (outside quoted text) to make it non-blocking,
> e.g. `Click 'Close Ad' if exists`

---

## 🐾 Battle-Tested

ManulEngine is verified against **1653+ synthetic DOM tests** covering:

- Shadow DOM, invisible overlays, zero-pixel honeypots
- Custom dropdowns, drag-and-drop, hover menus
- Legacy HTML (tables, fieldsets, unlabelled inputs)
- AI rejection & self-healing loops
- Persistent controls cache hit/miss cycles

---

**Version:** 0.0.8.9 · **Status:** Hunting...
