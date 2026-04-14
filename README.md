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

Write browser automation in plain English. ManulEngine interprets `.hunt` files through deterministic DOM heuristics on top of Playwright — no selectors, no cloud APIs, no AI required.

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

Explicit waits use Playwright's `locator.wait_for()` instead of hardcoded sleeps. Strict assertions resolve the element through heuristics and compare exact text, value, or placeholder with `==`.

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

### Dual-persona workflow

Manual QA writes plain-English `.hunt` steps — no code required. SDETs extend the same files with Python hooks (`[SETUP]` / `[TEARDOWN]`, `CALL PYTHON`), lifecycle orchestration (`@before_all` / `@after_all`), and `@custom_control` handlers for complex widgets. Both personas work on the same artifact.

### Optional AI, off by default

`"model": null` is the recommended default. When a local Ollama model is enabled, it acts as a last-resort fallback for genuinely ambiguous elements. The engine is not AI-powered — it is heuristics-first with an optional AI safety net.

---

## Four Automation Pillars

The same runtime and the same DSL serve four use cases:

| Pillar | How |
|---|---|
| **QA / E2E testing** | Write plain-English flows, verify outcomes, attach HTML reports and screenshots. No selectors in the test source. |
| **RPA workflows** | Log into portals, fill forms, extract values, hand off to Python for backend or filesystem steps. |
| **Synthetic monitoring** | Pair `.hunt` files with `@schedule:` and `manul daemon` for recurring health checks. |
| **AI agent targets** | Constrained DSL execution is safer than raw Playwright for external agents — the runtime still owns scoring, retries, and validation. |

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
- **Custom controls** — `@custom_control(page, target)` decorator lets SDETs handle complex widgets (datepickers, virtual tables, canvas elements) with raw Playwright while the hunt file keeps a single readable step.
- **Lifecycle hooks** — `@before_all`, `@after_all`, `@before_group`, `@after_group` in `manul_hooks.py` for suite-wide setup and teardown.
- **HTML reports** — `--html-report` generates a self-contained dark-themed report with accordions, screenshots, tag filters, and run-session merging across CLI invocations.
- **Docker CI runner** — `ghcr.io/alexbeatnik/manul-engine:0.0.9.29` runs headless in CI with `dumb-init`, non-root user, and `MANUL_*` env overrides.

---

## Quickstart

### Install

```bash
pip install manul-engine==0.0.9.29
playwright install
```

Optional local AI fallback (not required):

```bash
pip install "manul-engine[ai]==0.0.9.29"
ollama pull qwen2.5:0.5b && ollama serve
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
| `model` | `null` | Ollama model name. `null` = heuristics-only. |
| `headless` | `false` | Hide the browser window. |
| `browser` | `"chromium"` | `chromium`, `firefox`, or `webkit`. |
| `browser_args` | `[]` | Extra browser launch flags. |
| `ai_threshold` | auto | Score threshold before LLM fallback. |
| `ai_always` | `false` | Always invoke LLM picker (requires `model`). |
| `ai_policy` | `"prior"` | Heuristic score as prior hint or strict constraint. |
| `controls_cache_enabled` | `true` | Persistent per-site controls cache. |
| `controls_cache_dir` | `"cache"` | Cache directory (relative or absolute). |
| `semantic_cache_enabled` | `true` | In-session semantic cache (+200k score boost). |
| `custom_controls_dirs` | `["controls"]` | Directories scanned for `@custom_control` modules. |
| `timeout` | `5000` | Action timeout (ms). |
| `nav_timeout` | `30000` | Navigation timeout (ms). |
| `workers` | `1` | Max parallel hunt files. |
| `tests_home` | `"tests"` | Default output for new hunts and scans. |
| `auto_annotate` | `false` | Insert `# 📍 Auto-Nav:` comments on URL changes. |
| `channel` | `null` | Installed browser channel (`chrome`, `msedge`). |
| `executable_path` | `null` | Path to Electron or custom browser executable. |
| `retries` | `0` | Retry failed hunts N times. |
| `screenshot` | `"on-fail"` | `none`, `on-fail`, or `always`. |
| `html_report` | `false` | Generate `reports/manul_report.html`. |
| `explain_mode` | `false` | Per-channel scoring breakdown in output. |

Environment variables (`MANUL_HEADLESS`, `MANUL_BROWSER`, `MANUL_MODEL`, `MANUL_WORKERS`, etc.) always override JSON config.

### Docker

```bash
docker run --rm --shm-size=1g \
  -v $(pwd)/hunts:/workspace/hunts:ro \
  -v $(pwd)/reports:/workspace/reports \
  ghcr.io/alexbeatnik/manul-engine:0.0.9.29 \
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
playwright install

python run_tests.py                              # synthetic + unit suite
python demo/run_demo.py                          # integration hunts (needs network)
python demo/benchmarks/run_benchmarks.py         # adversarial DOM fixtures
```

---

## Get Involved

ManulEngine is alpha-stage and solo-developed. If deterministic, explainable browser automation interests you:

- Try it: `pip install manul-engine==0.0.9.29 && playwright install`
- File issues: [github.com/alexbeatnik/ManulEngine/issues](https://github.com/alexbeatnik/ManulEngine/issues)

---

## What's New in v0.0.9.29

- **Loop constructs (`REPEAT` / `FOR EACH` / `WHILE`):** Iterative execution blocks in `.hunt` files. `REPEAT N TIMES:` for fixed counts, `FOR EACH {var} IN {collection}:` for data iteration, `WHILE <condition>:` for dynamic polling. Full nesting with conditionals, `{i}` auto-counter, WHILE safety limit (100 iterations), empty body validation. 123-assertion test suite.
- **Complete user guide** — new `docs/` folder with structured documentation: overview, installation, getting started, full DSL syntax reference, reports & explainability, and integration guides.

<details>
<summary>v0.0.9.28</summary>

- **Conditional branching (`IF` / `ELIF` / `ELSE`):** Block-style branching in `.hunt` files based on element presence, visible text, or variable state. Indentation-based body detection, nesting support, and `ConditionalSyntaxError` for malformed blocks. 97-assertion test suite.
- **What-If Analysis REPL (`ExplainNextDebugger`):** Interactive debug REPL for hypothetical step evaluation. During a debug pause, type `w` (terminal) to enter the REPL or `e` / send `explain-next` (extension protocol) for one-shot evaluation. Combines DOMScorer heuristic scoring with optional LLM analysis to produce a 0–10 confidence rating, element match info, risk assessment, and corrective suggestions. The best heuristic match is highlighted with a persistent magenta outline on the live page. 112-assertion test suite.
- **What-If execute bug fixes:** `_execute_step()` recursive call now passes `strategic_context` and `step_idx` by keyword. Injected What-If steps run through `substitute_memory()` so `{var}` placeholders resolve before execution.
- **LLM JSON fence-stripping:** `_parse_llm_json()` now strips markdown code fences before JSON parsing.

</details>

## License

**Version:** 0.0.9.29

Apache-2.0.