<p align="center">
    <img src="https://raw.githubusercontent.com/alexbeatnik/ManulEngine/main/images/manul.png" alt="ManulEngine mascot" width="180" />
</p>

# ManulEngine

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/manul-engine?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/manul-engine)
[![Manul Engine Extension](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=Manul%20Engine%20Extension&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)
[![Manul Engine Extension (Open VSX)](https://img.shields.io/open-vsx/v/manul-engine/manul-engine?label=Open%20VSX&logo=eclipse-ide)](https://open-vsx.org/extension/manul-engine/manul-engine)
[![MCP Server](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-mcp-server?label=MCP%20Server&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-mcp-server)
[![MCP Server (Open VSX)](https://img.shields.io/open-vsx/v/manul-engine/manul-mcp-server?label=MCP%20Server%20Open%20VSX&logo=eclipse-ide)](https://open-vsx.org/extension/manul-engine/manul-mcp-server)
[![ManulAI Local Agent](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manulai-local-agent?label=ManulAI%20Local%20Agent&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manulai-local-agent)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-d97706)](#status)

**A deterministic automation runtime for both humans and LLM agents.** Write (or generate) `.hunt` files in plain English; ManulEngine resolves every element with deterministic DOM heuristics and drives Chrome directly over the Chrome DevTools Protocol (CDP) — no Playwright, no selectors, no cloud APIs, no AI required.

The same runtime serves two drivers from one artifact:

- **Humans** author readable `.hunt` steps (`Click the 'Login' button`) — QA tests, RPA, synthetic monitors. No selectors to maintain.
- **LLM agents** drive it through JSON CLI commands (`manul map` / `run-step` / `read` / `schema`) that target elements by human label, never CSS/XPath.

### Built for agents — and it's measurably cheaper on tokens

An agent has to *see* a page before it can act. A browser driver like Playwright or Selenium doesn't help here — it gives *code* access to the page, not the model. An LLM agent built on one still has to serialize the page into the prompt, and the usual ways are `page.content()` (**raw HTML**) or the **accessibility snapshot** — both expensive. `manul map` instead emits a compact, landmark-grouped view of just the labelled, interactive elements. Measured with the GPT-4 tokenizer (`cl100k_base`) on representative pages:

| What an agent feeds the model to perceive a page | Tokens | vs `manul map` |
| --- | --- | --- |
| Raw HTML (`page.content()`) | 2,216 – 2,241 | **4–8× more** |
| Accessibility tree (role + name) | 1,384 – 1,912 | **3.6–5× more** |
| **`manul map` (compact JSON)** | **278 – 528** | **1×** |

So the perception step that every browser-agent pays on *every* turn costs **~4–8× fewer tokens** with ManulEngine than dumping HTML, and **~3.6–5× fewer** than the a11y tree. These are clean synthetic pages — real-world HTML is far more bloated, so the gap widens in practice. (Reproduce: `python scripts/measure_tokens.py`.)

Authoring is also leaner and far more durable: the same checkout flow written as a `.hunt` file is a touch smaller than the equivalent Playwright script (175 vs 204 tokens) but — the real point — carries **zero CSS/XPath selectors** to break when the markup shifts.

> **Status: Alpha.** Solo-developed, actively battle-tested. Bugs are expected, APIs may evolve, and there are no promises about stability or production readiness. The core claim is transparency: when a step works, you can see exactly why; when it fails, you get the scoring breakdown to diagnose it.

> **📖 Full Documentation:** [Overview](docs/overview.md) · [Installation](docs/installation.md) · [Getting Started](docs/getting-started.md) · [DSL Syntax](docs/dsl-syntax.md) · [Reports & Explainability](docs/reports.md) · [Integration](docs/integration.md)

---

## Syntax First

ManulEngine runs `.hunt` files — plain-English automation scripts that read like manual QA steps. Here is the DSL in action.

### A complete flow

```text
@context: Smoke test for a login page
@title: Login Smoke
@var: {email} = admin@example.com
@var: {password} = secret123

STEP 1: Open the app
    NAVIGATE to https://example.com/login
    VERIFY that 'Sign In' is present

STEP 2: Authenticate
    FILL 'Email' field with '{email}'
    VERIFY "Email" field has value "{email}"
    FILL 'Password' field with '{password}'
    CLICK the 'Sign In' button
    VERIFY that 'Dashboard' is present

DONE.
```

Run it:

```bash
manul path/to/login.hunt
```

Every `@var:` is declared up front — never hardcode test data inside steps. `VERIFY` confirms state after every significant action. `DONE.` closes the mission.

> **Case-insensitive keywords.** All DSL keywords are case-insensitive at runtime — `CLICK`, `Click`, and `click` all work. The canonical form used in documentation and generated files is ALL UPPERCASE.
>
> **Element type hints are optional.** Words like `button`, `link`, `field`, `dropdown` placed after the target outside quotes are not required, but they provide a strong heuristic signal that boosts scoring accuracy. `CLICK the 'Login' button` and `CLICK the 'Login'` both work — the former is more precise.

### Conditional branching

Branch test logic with `IF` / `ELIF` / `ELSE` based on what the page actually contains. Nesting is supported.

```text
STEP 1: Adaptive login
    IF button 'SSO Login' exists:
        CLICK the 'SSO Login' button
        VERIFY that 'SSO Portal' is present
    ELIF text 'Sign In' is present:
        FILL 'Username' field with '{username}'
        CLICK the 'Sign In' button
    ELSE:
        CLICK the 'Create Account' link
```

Conditions can check element existence, visible text, variable equality, substring containment, or simple truthiness — all evaluated against the live page.

### Loops

Repeat actions with `REPEAT`, iterate data with `FOR EACH`, or poll dynamic state with `WHILE`. Loops nest freely with conditionals.

```text
@var: {products} = Laptop, Headphones, Mouse

STEP 1: Add products to cart
    FOR EACH {product} IN {products}:
        FILL 'Search' field with '{product}'
        PRESS Enter
        CLICK the 'Add to Cart' button NEAR '{product}'
        VERIFY that 'Added to cart' is present

STEP 2: Load all reviews
    WHILE button 'Load More' exists:
        CLICK the 'Load More' button
        WAIT 2

STEP 3: Retry checkout
    REPEAT 3 TIMES:
        CLICK the 'Place Order' button
        IF text 'Success' is present:
            VERIFY that 'Order confirmed' is present
```

`REPEAT N TIMES:` runs a fixed count. `FOR EACH {var} IN {collection}:` iterates comma-separated values. `WHILE <condition>:` repeats until the condition is false (safety limit: 100 iterations). `{i}` counter is auto-set on every iteration.

### Contextual navigation

When a page has repeating controls — multiple "Delete" buttons, "Edit" links in every row — use contextual qualifiers instead of brittle selectors.

```text
CLICK the 'Edit' button NEAR 'John Doe'
CLICK the 'Login' button ON HEADER
CLICK the 'Privacy Policy' link ON FOOTER
CLICK the 'Delete' button INSIDE 'Actions' row with 'John Doe'
```

`NEAR` ranks by pixel distance. `ON HEADER` / `ON FOOTER` scopes to viewport zones. `INSIDE` restricts scoring to a resolved row or container subtree.

### Variables, data-driven runs, and backend hooks

```text
@var: {email} = admin@example.com
@var: {password} = secret123
@script: {db} = scripts.db_helpers
@data: users.csv
@tags: smoke, auth

[SETUP]
    CALL PYTHON {db}.seed_user "{email}" "{password}"
[END SETUP]

STEP 1: Login
    NAVIGATE to https://example.com/login
    FILL 'Email' field with '{email}'
    FILL 'Password' field with '{password}'
    CLICK the 'Sign In' button
    VERIFY that 'Dashboard' is present

STEP 2: Fetch and use an OTP
    CLICK the 'Send OTP' button
    CALL PYTHON api_helpers.fetch_otp "{email}" into {otp}
    FILL 'OTP' field with '{otp}'
    CLICK the 'Verify' button
    VERIFY that 'Welcome' is present

[TEARDOWN]
    CALL PYTHON {db}.clean_database "{email}"
[END TEARDOWN]
```

`@data:` loops the entire mission over each row in a CSV or JSON file. `@tags:` lets you filter runs with `manul --tags smoke`. `[SETUP]` / `[TEARDOWN]` run Python outside the browser for data seeding and cleanup. `CALL PYTHON ... into {var}` captures return values mid-test — ideal for OTPs, tokens, and backend state.

### Explicit waits and strict assertions

```text
WAIT FOR 'Submit' to be visible
WAIT FOR 'Loading...' to disappear

VERIFY "Email" field has value "{email}"
VERIFY "Save" button has text "Save Changes"
VERIFY "Search" input has placeholder "Type to search..."
```

Explicit waits poll element visibility over CDP instead of hardcoded sleeps. Strict assertions resolve the element through heuristics and compare exact text, value, or placeholder with `==`.

`WAIT FOR SELECTOR 'css'` waits for a CSS selector to appear (useful for custom elements like `ytd-video-renderer` that have no stable visible text). The `WAIT FOR 'target' TO BE VISIBLE` form also accepts CSS selectors — if the quoted target looks like a CSS selector it routes to `page.wait_for_selector()` automatically.

### Page scanning for LLM agents

```text
FULL SCAN
```

`FULL SCAN` groups every interactive control on the page by its nearest semantic landmark (form, nav, header, dialog, section …) and prints a Markdown table per group. Designed for LLM-driven automation — an LLM can paste the output directly into its context window to decide which element to interact with next. Shadow DOM trees are traversed recursively, so controls inside custom elements (e.g. `<ytd-*>`, `<mwc-*>`) appear under a `[shadow]`-suffixed group.

Example output:

```
## Form: Login
| role       | label                            | locator                              | tag      | editable |
|------------|----------------------------------|--------------------------------------|----------|----------|
| textbox    | Email                            | #email                               | input    | yes      |
| textbox    | Password                         | #password                            | input    | yes      |
| button     | Sign In                          | text=Sign In                         | button   | no       |

## Navigation
| role       | label                            | locator                              | tag      | editable |
|------------|----------------------------------|--------------------------------------|----------|----------|
| link       | Home                             | text=Home                            | a        | no       |
| link       | About                            | text=About                           | a        | no       |
```

`SCAN PAGE` remains available for generating draft `.hunt` files from a live page.

### Agent commands — drive the engine from an external LLM

For agentic use, ManulEngine exposes a small set of **JSON-emitting CLI commands** (mirroring the Go sibling [ManulHeart](https://github.com/alexbeatnik/ManulHeart)). They attach to an **already-running Chrome over CDP**, so an external model keeps one browser open and issues stateless calls against it. The JSON payload goes to **stdout**; all engine logs go to **stderr**, so a driver can pipe the output straight into a prompt.

```bash
# 1. start Chrome once with remote debugging
google-chrome --remote-debugging-port=9222 &

# 2. let the model see the page, act, and read — by human label, never CSS/XPath
manul schema                                   # DSL grammar + agent JSON shapes (no browser)
manul map --tab example.com                    # compact landmark-grouped page map → JSON
manul run-step "Click the 'Login' button"      # run one instruction → step-outcome JSON
manul read 'Order total'                       # read one labelled value → {value, found, reason}
manul read --selector '#cart'                  # sanitized region text → {text, selector}
```

Shared flags: `--cdp <url>` (default `http://127.0.0.1:9222`) and `--tab <url-substr>` to pick a tab. `run-step` returns a non-zero exit code when the step fails, and surfaces `near` candidates (with `0.0–1.0` scores) on a failed or low-confidence match so the agent can retarget without a re-scan. `manul schema` is the machine-readable contract a driver pins instead of stuffing full docs into every prompt.

### Shared libraries and scheduling

```text
@import: Login, Logout from lib/auth.hunt
@export: Checkout
@schedule: every 5 minutes

STEP 1: Setup
    USE Login

STEP 2: Purchase flow
    CLICK the 'Buy Now' button
    VERIFY that 'Order Confirmed' is present

STEP 3: Cleanup
    USE Logout

DONE.
```

`@import:` / `USE` reuses named STEP blocks across files. `@export:` controls visibility. `@schedule:` plus `manul daemon` turns any hunt into a recurring monitor or RPA job.

### CLI

```bash
manul path/to/hunts/                             # run all .hunt files in a directory
manul --headless path/to/file.hunt               # headless single file
manul --tags smoke path/to/hunts/                # filter by tags
manul --html-report --screenshot on-fail path/   # reports + failure screenshots
manul --explain path/to/file.hunt                # per-step scoring breakdown
manul --debug path/to/file.hunt                  # pause before every step
manul --retries 2 path/to/hunts/                 # retry failed hunts
manul scan https://example.com                   # scan a page → draft.hunt
manul daemon path/to/hunts/ --headless           # run scheduled hunts
```

---

## Philosophy

### Determinism, not prompt variance

The primary resolver is not an LLM. It is a weighted heuristic scorer (`DOMScorer`) backed by a native JavaScript `TreeWalker`. Scores are normalized on a `0.0–1.0` confidence scale across five channels: `cache`, `semantics`, `text`, `attributes`, and `proximity`. The result is repeatable: same page state plus same step text equals same resolution — no prompt variance, no cloud dependency.

When `--explain` is enabled, every resolved step prints a per-channel breakdown so you can see exactly which signals drove the decision and which lost:

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
└─ Decision: selected "Login" with score 0.593
```

### Native CDP, no Playwright

ManulEngine talks to the browser through its **own** Chrome DevTools Protocol client — a thin async WebSocket transport in [`manul_engine/cdp/`](manul_engine/cdp/) with a single runtime dependency (`websockets`). There is no Playwright, no Node.js, and no bundled browser download: the engine launches the Chrome/Chromium you already have on `PATH` (or attaches to a running one) and drives it directly.

Why own the protocol layer:

- **One small dependency, fully inspectable.** The whole browser driver is a handful of readable Python files (`conn.py` transport, `chrome.py` launcher, `page.py` page/frame/element model) rather than a large vendored toolchain. What the engine sends to Chrome is exactly what you can read.
- **Trusted input by default.** Clicks and keystrokes are dispatched via CDP `Input.*` events at real coordinates, and form values go through the native value setter so React/Vue/Angular state updates fire — no `force` hacks needed.
- **Per-frame execution contexts.** A selector is resolved once inside the owning frame's execution context, then every operation runs against that handle — so same-origin iframes (and OOPIF child targets) are first-class, not an afterthought.
- **CDP is Chromium-only by design.** Because the protocol is Chrome's, the engine drives Chrome/Chromium only. Firefox/WebKit are intentionally not supported; pick the concrete binary with `channel` (`chrome`, `msedge`, `chromium`, …) or `executable_path`.

This is the same philosophy as the Go sibling [ManulHeart](https://github.com/alexbeatnik/ManulHeart): plain-English `.hunt` files, deterministic heuristics, and a hand-written CDP layer instead of a heavyweight automation framework.

### Dual-persona workflow

Manual QA writes plain-English `.hunt` steps — no code required. SDETs extend the same files with Python hooks (`[SETUP]` / `[TEARDOWN]`, `CALL PYTHON`), lifecycle orchestration (`@before_all` / `@after_all`), and `@custom_control` handlers for complex widgets. Both personas work on the same artifact.

### No AI in the loop — fully deterministic

ManulEngine has **no LLM inside it**. Element resolution is 100% the deterministic `DOMScorer` — same page state + same step ⇒ same result, every run, with no model to install, no temperature to pin, and no network calls. The *intelligence* lives in the external agent that drives the engine via the [agent commands](#agent-commands--drive-the-engine-from-an-external-llm) (`map` / `run-step` / `read` / `schema`); the runtime itself stays a predictable execution layer. (An optional in-process Ollama fallback existed in early development — it was removed in favour of this clean split.)

---

## Four Automation Pillars

The same runtime and the same DSL serve four use cases:

| Pillar | How |
|---|---|
| **QA / E2E testing** | Write plain-English flows, verify outcomes, attach HTML reports and screenshots. No selectors in the test source. |
| **RPA workflows** | Log into portals, fill forms, extract values, hand off to Python for backend or filesystem steps. |
| **Synthetic monitoring** | Pair `.hunt` files with `@schedule:` and `manul daemon` for recurring health checks. |
| **AI agent targets** | Constrained DSL execution is safer than raw CDP/scripting for external agents — the runtime still owns scoring, retries, and validation. |

---

## Key Features

- **Conditional branching & loops** — `IF` / `ELIF` / `ELSE` for adaptive flows; `REPEAT`, `FOR EACH`, `WHILE` for iterating data, retrying actions, and polling dynamic state. Full nesting support.
- **Explainability** — `--explain` prints per-channel scoring breakdowns on the CLI. The VS Code extension shows hover tooltips and a title-bar "Explain Current Step" action during debug pauses.
- **What-If Analysis REPL** — During a `--debug` pause, type `w` to enter an interactive REPL that evaluates hypothetical steps against the live DOM without executing them. Returns a 0–10 confidence score, risk assessment, and highlights the best match on the page.
- **Desktop / Electron** — Set `executable_path` in the config and use `OPEN APP` instead of `NAVIGATE` to drive Electron apps with the same DSL.
- **Python API (`ManulSession`)** — Async context manager for pure-Python automation. Routes every call through the full heuristic pipeline.
  ```python
  from manul_engine import ManulSession

  async with ManulSession(headless=True) as session:
      await session.navigate("https://example.com/login")
      await session.fill("Username field", "admin")
      await session.click("Log in button")
      await session.verify("Welcome")
  ```
- **Smart recorder** — Captures semantic intent (e.g., `Select 'Option' from 'Dropdown'`) instead of brittle pointer events.
- **Custom controls** — `@custom_control(page, target)` decorator lets SDETs handle complex widgets (datepickers, virtual tables, canvas elements) with raw CDP while the hunt file keeps a single readable step. Handlers receive a typed `ControlContext` (`ctx.page` / `ctx.action` / `ctx.value` / `ctx.target` / `ctx.page_name` / `ctx.url` / `ctx.step`); `manul controls list` shows the registry; misses against a sibling page print a one-line hint.
- **Lifecycle hooks** — `@before_all`, `@after_all`, `@before_group`, `@after_group` in `manul_hooks.py` for suite-wide setup and teardown.
- **HTML reports** — `--html-report` generates a self-contained dark-themed report with accordions, screenshots, tag filters, and run-session merging across CLI invocations.
- **Docker CI runner** — `ghcr.io/alexbeatnik/manul-engine:0.1.0` runs headless in CI with `dumb-init`, non-root user, and `MANUL_*` env overrides.

---

## Quickstart

### Install

```bash
pip install manul-engine==0.1.0
# Requires a system-installed Google Chrome / Chromium on PATH.
```

### Configure

Create `manul_engine_configuration.json` in the workspace root. All keys are optional:

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true,
  "semantic_cache_enabled": true
}
```

This is the minimal recommended config — fully heuristics-only, no AI dependency.

### Run

```bash
manul tests/login.hunt                           # single file
manul tests/                                     # all hunts in a directory
manul --headless --html-report tests/            # CI mode with reports
```

### Configuration reference

| Key | Default | Description |
|---|---|---|
| `headless` | `false` | Hide the browser window. |
| `browser` | `"chromium"` | `chromium` (launch system Chrome) or `electron` (attach to a running Chrome/Electron over CDP). |
| `browser_args` | `[]` | Extra browser launch flags. |
| `controls_cache_enabled` | `true` | Persistent per-site controls cache. |
| `controls_cache_dir` | `"cache"` | Cache directory (relative or absolute). |
| `semantic_cache_enabled` | `true` | In-session semantic cache (+200k score boost). |
| `custom_controls_dirs` | `["controls"]` | Directories scanned for `@custom_control` modules. |
| `timeout` | `5000` | Action timeout (ms). |
| `nav_timeout` | `30000` | Navigation timeout (ms). |
| `workers` | `1` | Max parallel hunt files. |
| `tests_home` | `"tests"` | Default output for new hunts and scans. |
| `auto_annotate` | `false` | Insert `# 📍 Auto-Nav:` comments on URL changes. |
| `channel` | `null` | Chrome/Chromium binary to launch (`chrome`, `msedge`, `chromium`, …). |
| `executable_path` | `null` | Explicit path to a Chrome/Chromium (or Electron) executable. |
| `retries` | `0` | Retry failed hunts N times. |
| `screenshot` | `"on-fail"` | `none`, `on-fail`, or `always`. |
| `html_report` | `false` | Generate `reports/manul_report.html`. |
| `explain_mode` | `false` | Per-channel scoring breakdown in output. |

Environment variables (`MANUL_HEADLESS`, `MANUL_BROWSER`, `MANUL_CHANNEL`, `MANUL_WORKERS`, etc.) always override JSON config.

### Docker

```bash
docker run --rm --shm-size=1g \
  -v $(pwd)/hunts:/workspace/hunts:ro \
  -v $(pwd)/reports:/workspace/reports \
  ghcr.io/alexbeatnik/manul-engine:0.1.0 \
  --html-report --screenshot on-fail hunts/
```

Non-root (`manul`, UID 1000), `dumb-init` as PID 1, `--no-sandbox` baked in. A `docker-compose.yml` ships with `manul` and `manul-daemon` services.

---

## Ecosystem

| Component | Role | Links |
|-----------|------|-------|
| **ManulEngine** | Deterministic automation runtime (Python). Heuristic element resolver, `.hunt` DSL, CLI runner. | [PyPI](https://pypi.org/project/manul-engine/) · [GitHub](https://github.com/alexbeatnik/ManulEngine) |
| **Manul Engine Extension** | VS Code extension for ManulEngine with debug panel, explain mode, and Test Explorer integration. | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-engine) · [GitHub](https://github.com/alexbeatnik/ManulEngineExtension) |
| **ManulMcpServer** | MCP bridge that gives Copilot Chat and other agents access to ManulEngine. | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-mcp-server) · [Open VSX](https://open-vsx.org/extension/manul-engine/manul-mcp-server) · [GitHub](https://github.com/alexbeatnik/ManulMcpServer) |
| **ManulAI Local Agent** | Autonomous AI agent for browser automation, powered by ManulEngine. | [Marketplace](https://marketplace.visualstudio.com/items?itemName=manul-engine.manulai-local-agent) · [Open VSX](https://open-vsx.org/extension/manul-engine/manulai-local-agent) · [GitHub](https://github.com/alexbeatnik/ManulAI-local-agent) |

### Contributing and running tests

```bash
git clone https://github.com/alexbeatnik/ManulEngine.git
cd ManulEngine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# Requires a system-installed Google Chrome / Chromium on PATH.

python run_tests.py                              # synthetic + unit suite
python demo/run_demo.py                          # integration hunts (needs network)
python demo/benchmarks/run_benchmarks.py         # adversarial DOM fixtures
```

---

## Get Involved

ManulEngine is alpha-stage and solo-developed. If deterministic, explainable browser automation interests you:

- Try it: `pip install manul-engine==0.1.0` (needs system Chrome/Chromium)
- File issues: [github.com/alexbeatnik/ManulEngine/issues](https://github.com/alexbeatnik/ManulEngine/issues)

---

## What's New in v0.1.0

- **Ollama / in-process LLM removed (BREAKING):** ManulEngine is now purely deterministic — there is no in-engine model. The `model`, `ai_threshold`, `ai_always`, `ai_policy` settings (and `MANUL_MODEL` / `MANUL_AI_*` / `MANUL_LLM_*` env vars) are gone, along with the free-text task planner and the What-If *LLM* analysis (the deterministic explain-next dry-run stays). Intelligence now lives in the external agent that drives the engine via the agent commands.
- **Playwright removed — native Chrome DevTools Protocol backend (BREAKING):** the entire browser layer is now ManulEngine's own CDP client in [`manul_engine/cdp/`](manul_engine/cdp/), driving system Chrome/Chromium over a raw WebSocket. The only runtime dependency is `websockets` (no Playwright, no Node.js, no bundled browser download). `ManulSession.page` is now a `manul_engine.cdp.CDPPage`; per-frame iframe routing uses real per-frame execution contexts. **Install requires a system Chrome/Chromium on `PATH`** (`playwright install` is gone).
- **`browser` is Chromium-only:** `firefox` / `webkit` are no longer accepted (CDP is Chrome's protocol). `browser` now selects launch mode — `chromium` (launch) or `electron` (attach to a running Chrome/Electron over CDP); choose the binary with `channel` / `executable_path`.
- **Agent CLI commands for external LLM drivers:** new `manul schema` / `map` / `read` / `run-step` subcommands emit compact JSON (stdout) while engine logs stay on stderr, attaching to an already-running Chrome over CDP — the surface an external model uses to see the page, act, and read by human label. Mirrors ManulHeart's agent commands.

<details>
<summary>v0.0.9.32 — FULL SCAN, WAIT FOR SELECTOR, CSS-aware waits</summary>

- **`FULL SCAN` DSL step:** groups every interactive control on the page by its nearest semantic landmark ancestor (`<form>`, `<nav>`, `<header>`, `<footer>`, `<dialog>`, `<section>`, ARIA roles) and prints a compact Markdown table per group. Designed for LLM-driven automation — paste the output into an LLM context window to decide what to interact with next. Shadow DOM trees are traversed recursively; controls inside custom elements appear under a `[shadow]`-suffixed group.
- **`WAIT FOR SELECTOR '<css>'` DSL step:** explicit CSS-selector wait via `page.wait_for_selector()`. Solves the SPA / YouTube use case where there is no stable visible text, only a DOM tag (`ytd-video-renderer`, `mwc-button`, etc.).
- **CSS-aware `WAIT FOR '…' TO BE VISIBLE`:** the existing step now auto-detects CSS selectors (starts with `#`, `.`, `[`, contains `-`, `>`, or `:`) and routes to `page.wait_for_selector()` instead of `get_by_text()`. Plain-text targets are unchanged.

</details>

<details>
<summary>v0.0.9.31</summary>

- **Page registry split into `pages/` directory (BREAKING):** page mappings now live as one JSON fragment per site under `<project>/pages/<safe_netloc>.json`. Run `manul pages migrate` once to split any pre-existing `pages.json`.
- **`ControlContext` API for `@custom_control` (BREAKING):** handlers now accept a single `ControlContext` argument exposing `page`, `action`, `value`, `target`, `page_name`, `url`, and `step`. Replace `async def fn(page, action_type, value)` with `async def fn(ctx: ControlContext)`.
- **`manul pages list` / `manul pages migrate` / `manul controls list` CLI commands.**
- **Custom Controls miss-diagnostics** and **visible dispatch log** without `--debug`.

</details>

<details>
<summary>v0.0.9.30</summary>

- **Loop constructs (`REPEAT` / `FOR EACH` / `WHILE`):** iterative execution blocks. `REPEAT N TIMES:` for fixed counts, `FOR EACH {var} IN {collection}:` for data iteration, `WHILE <condition>:` for dynamic polling. Full nesting with conditionals, `{i}` auto-counter, WHILE safety limit (100 iterations). 129-assertion test suite.
- **Complete user guide** — new `docs/` folder with structured documentation.

</details>

## License

**Version:** 0.1.0

Apache-2.0.