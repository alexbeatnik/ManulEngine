<p align="center">
    <img src="https://raw.githubusercontent.com/alexbeatnik/ManulEngine/main/images/manul.png" alt="ManulEngine mascot" width="180" />
</p>

# ManulEngine

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/manul-engine?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/manul-engine)
[![Manul Engine Extension](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=Manul%20Engine%20Extension&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)
[![MCP Server](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-mcp-server?label=MCP%20Server&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-mcp-server)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-d97706)](#status)

Deterministic, DSL-first web and desktop automation on top of Playwright, with explainable heuristics, a standalone Python API, and optional local AI fallback.

## Status

**Status: Alpha. Developed by a single person.**

This project is actively being battle-tested. Bugs are expected, APIs may evolve, and there are no promises about stability or production readiness. The core claim is transparency: when a step works, you should understand why; when it fails, you should have enough signal to diagnose it.

## Core Philosophy

ManulEngine is an interpreter for the `.hunt` DSL. A hunt file expresses intent in plain English, the runtime snapshots the DOM, ranks candidates with heuristics, and executes through Playwright.

### Determinism first

The primary resolver is not an LLM. It is a deterministic scoring system backed by DOM traversal and weighted heuristics:

- DOM collection uses a native `TreeWalker` in injected JavaScript.
- Candidate ranking is handled by `DOMScorer`.
- Scores are normalized on a `0.0` to `1.0` confidence scale.
- Weighted channels include `cache`, `semantics`, `text`, `attributes`, and `proximity`.

That means the engine can explain more than "element not found". It can show whether a target lost because text affinity was weak, semantic alignment was poor, the candidate was hidden, or another channel outweighed it.

### Transparency instead of AI magic

The recommended default is heuristics-only mode:

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true,
  "semantic_cache_enabled": true
}
```

When a local Ollama model is enabled, it acts as a fallback for ambiguous cases rather than the primary execution path.

### Dual-persona workflow

The authoring model is intentionally split across two layers:

- QA, analysts, and operators write plain-English `.hunt` steps.
- SDETs extend those flows with Python hooks, lifecycle setup, and custom controls when a UI or backend dependency should not be forced into the generic DSL path.

The intended boundary is straightforward:

- Keep business intent and readable flow in the DSL.
- Keep environment setup, backend interaction, and custom widget handling in Python.

## Why ManulEngine

Most browser automation tools sold as AI automation are cloud wrappers around selectors and retries. ManulEngine is aiming at the opposite design.

### Deterministic first, not AI-first

The runtime resolves DOM elements through a native JavaScript `TreeWalker` plus a weighted `DOMScorer`. That gives you a repeatable result from page state plus step text, not from prompt variance.

### Explainable instead of opaque

When the engine chooses the wrong target, you should be able to inspect the actual scoring channels that drove the result. The point is not just success cases. The point is actionable failure analysis.

### One artifact for two personas

QA, ops, and analysts can keep the flow readable in `.hunt`. SDETs can attach Python, lifecycle hooks, and custom controls without splitting the scenario into two separate systems.

### Optional AI fallback, off by default

`"model": null` remains the recommended default. When a local Ollama model is enabled, it is a fallback for ambiguous cases, not the primary execution engine.

## Four Automation Pillars

ManulEngine is not only a test runner. The same runtime and the same DSL can cover four adjacent use cases:

1. QA and E2E testing
2. RPA workflows
3. Synthetic monitoring
4. AI agent execution targets

### QA and E2E testing

Write plain-English flows, verify outcomes, attach reports and screenshots when needed, and keep selectors out of the test source.

### RPA workflows

Use the same DSL to log into portals, download files, fill forms, extract values, and hand work to Python when a backend or filesystem step is involved.

### Synthetic monitoring

Pair `.hunt` files with `@schedule:` and `manul daemon` to run scheduled health checks with the same execution model as your test flows.

### AI agent execution targets

If an external agent needs to drive the browser, `.hunt` is a safer constrained target than raw Playwright code because the runtime still owns validation, scoring, retries, and reporting.

## Key Features

### Explainability layers

The runtime and companion Manul Engine Extension for VS Code expose multiple explainability layers instead of forcing you to inspect a terminal dump.

**CLI: `--explain`**

```bash
manul --explain tests/saucedemo.hunt
manul --explain --headless tests/ --html-report
```

That mode prints candidate rankings and per-channel scoring breakdowns for each resolved step.

Representative CLI explain output:

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

**VS Code: title bar action**

During a debug pause, the extension exposes `Explain Current Step` in the editor title bar so you can request explanation data for the paused step without leaving the editor.

**VS Code: hover tooltips in debug mode**

Run a hunt in Debug mode through Test Explorer, then hover over any resolved step line in the `.hunt` file. The extension shows the stored per-channel breakdown directly on that line.

### Desktop and Electron automation via `executable_path`

ManulEngine is not limited to browser tabs. Because it runs on Playwright, it can also drive Electron-based desktop applications.

Set `executable_path` in the runtime config and use `OPEN APP` instead of `NAVIGATE`:

```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "/path/to/YourElectronApp"
}
```

```text
@context: Desktop smoke test
@title: Desktop Smoke

STEP 1: Attach to the window
    OPEN APP
    VERIFY that 'Welcome' is present

STEP 2: Exercise the main screen
    Click the 'Settings' button
    VERIFY that 'Preferences' is present

DONE.
```

### Smart recorder for native controls

The recorder is meant to capture intent, not just raw pointer activity. A concrete example is native `<select>` handling: the injected recorder observes semantic `change` events and emits DSL such as `Select 'Option' from 'Dropdown'` instead of recording a brittle chain of low-level clicks on `<option>` elements.

### Python hooks and custom controls

When the generic resolver should not be forced to understand a bespoke widget, ManulEngine provides an explicit SDET escape hatch:

- `[SETUP]` / `[TEARDOWN]` hooks for environment and data setup.
- `CALL PYTHON` for backend lookups or computed values.
- `@before_all` / `@after_all` lifecycle hooks for suite-wide orchestration.
- `@custom_control` handlers for complex UI elements.

That balance is intentional: keep the common path readable, and keep the edge cases programmable.

### Public Python API (`ManulSession`)

For users who prefer writing automation in pure Python, the runtime exports `ManulSession`: an async context manager that owns the Playwright lifecycle and exposes clean methods for navigation, clicks, fills, verifications, and extraction.

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

`ManulSession` can also execute raw DSL snippets against the already-open browser via `run_steps()`:

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

### State, variables, and scope

Variable handling is strict rather than ad hoc. The runtime supports `@var:`, `@script:`, `EXTRACT`, `SET`, and `CALL PYTHON ... into {var}` with deterministic placeholder substitution in downstream steps.

Useful patterns:

- `@var:` for static test data at the top of the file.
- `@script:` for file-local aliases such as `@script: {auth} = scripts.auth_helpers`, then `CALL PYTHON {auth}.issue_token into {token}`; or callable aliases such as `@script: {issue_token} = scripts.auth_helpers.issue_token`, then `CALL PYTHON {issue_token} into {token}`.
- `EXTRACT ... into {var}` for values pulled from the UI.
- `SET {var} = value` for mid-run assignment.
- `CALL PYTHON module.func into {var}` for backend-generated runtime values such as OTPs or tokens.

Scope precedence is explicit:

| Priority | Scope | Source |
|---|---|---|
| 1 | Row vars | `@data:` iteration values |
| 2 | Step vars | `EXTRACT`, `SET`, `CALL PYTHON ... into {var}` |
| 3 | Mission vars | `@var:` declarations |
| 4 | Global vars | lifecycle hooks and process-level state |
| 5 | Import vars | `@var:` inherited from `@import:` source files |

### Tags and data-driven runs

The runtime also supports selective execution and data-driven loops without changing the DSL model.

```text
@tags: smoke, auth
@data: users.csv
```

```bash
manul tests/ --tags smoke
```

### Lifecycle orchestration and hooks

There are two levels of Python orchestration:

- Per-file `[SETUP]` / `[TEARDOWN]` and inline `CALL PYTHON` for file-local setup or backend calls.
- Suite-level `manul_hooks.py` with `@before_all`, `@after_all`, `@before_group`, and `@after_group` for shared state across multiple hunts.

### Benchmarks and test coverage

The repo ships with both synthetic tests and adversarial fixtures. The point is not to claim maturity. The point is to show that the scoring model, parser, hooks, recorder, scheduler, and reporter are exercised against concrete failure modes.

- `python manul.py test` runs the synthetic and unit suite.
- `benchmarks/run_benchmarks.py` exercises dynamic IDs, overlapping traps, nested tables, and custom dropdown fixtures.
- `tests/*.hunt` holds integration-style hunts for real browser flows.

## Getting Started

### Install

```bash
pip install manul-engine==0.0.9.23
playwright install
```

If you install standalone Python dependencies manually instead of using the packaged extras, the current minimums in this release line are `playwright==1.58.0` and `ollama==0.6.1`.

Optional local AI fallback:

```bash
pip install "manul-engine[ai]==0.0.9.23"
ollama pull qwen2.5:0.5b
ollama serve
```

### Manul Engine Extension

ManulEngine has a companion Manul Engine Extension for VS Code. Normal installation should use the published Marketplace build:

- https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine

```bash
code --install-extension manul-engine.manul-engine
```

### MCP Server for Copilot Chat

A separate VS Code extension turns ManulEngine into a native MCP server so GitHub Copilot chat can drive a real browser through natural language:

- https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-mcp-server

```bash
code --install-extension manul-engine.manul-mcp-server
```

After installation and **Reload Window**, `ManulMcpServer` appears in the MCP Servers panel and Copilot gains the following tools:

| Tool | What it does |
|------|--------------|
| `manul_run_step` | Run a single DSL step or natural-language action in the browser |
| `manul_run_goal` | Convert a natural-language goal into steps and execute them |
| `manul_run_hunt` | Run a full `.hunt` document passed as text |
| `manul_run_hunt_file` | Run a `.hunt` file from disk |
| `manul_validate_hunt` | Validate a `.hunt` document without running it |
| `manul_normalize_step` | Preview how a step will be normalized to DSL before sending it |
| `manul_get_state` | Get current browser and session state |
| `manul_preview_goal` | Preview goal-to-DSL conversion without execution |
| `manul_scan_page` | List all interactive elements on the current page |
| `manul_save_hunt` | Save a `.hunt` file to disk |

The MCP bridge maintains a persistent Playwright session across calls. No separate HTTP server is required — the extension spawns a Python runner directly.

Natural-language input is accepted for `manul_run_step` and `manul_run_goal` and normalized to proper DSL before execution:

```
# These are equivalent:
manul_run_step: click login
manul_run_step: Click the 'login' button
```

See the [ManulMcpServer repository](https://github.com/alexbeatnik/ManulMcpServer) for the full developer guide.

### Configuration

Create `manul_engine_configuration.json` in the workspace root. All keys are optional, but this file is the main runtime control plane:

```json
{
  "model": null,
  "browser": "chromium",
  "browser_args": [],
  "headless": false,
  "ai_always": false,
  "ai_policy": "prior",
  "ai_threshold": null,
  "timeout": 5000,
  "nav_timeout": 30000,
  "controls_cache_enabled": true,
  "controls_cache_dir": "cache",
  "semantic_cache_enabled": true,
    "custom_controls_dirs": ["controls"],
  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "tests_home": "tests",
  "auto_annotate": false,
  "executable_path": null,
  "channel": null,
  "workers": 1,
  "retries": 0,
  "screenshot": "on-fail",
  "html_report": false
}
```

Notes:

- `model: null` keeps the runtime fully heuristics-only.
- `browser_args` passes extra launch flags to the browser.
- `ai_always`, `ai_policy`, and `ai_threshold` only matter when a model is enabled.
- `controls_cache_dir`, `tests_home`, and `auto_annotate` control runtime filesystem behavior.
- `custom_controls_dirs` lists directories where `@custom_control` Python modules are scanned. Default: `["controls"]`.
- `channel` targets an installed browser such as Chrome or Edge.
- `executable_path` targets a custom executable such as an Electron app.

Environment variables always win over JSON config:

```bash
export MANUL_HEADLESS=true
export MANUL_BROWSER=firefox
export MANUL_MODEL=qwen2.5:0.5b
export MANUL_WORKERS=4
export MANUL_EXPLAIN=true
```

Configuration reference:

| Key | Default | Description |
|---|---|---|
| `model` | `null` | Ollama model name. `null` keeps the runtime heuristics-only. |
| `headless` | `false` | Hide the browser window. |
| `browser` | `"chromium"` | Browser engine: `chromium`, `firefox`, or `webkit`. |
| `browser_args` | `[]` | Extra launch flags for the browser. |
| `ai_threshold` | auto | Score threshold before optional LLM fallback. |
| `ai_always` | `false` | Always ask the LLM picker. Only makes sense when `model` is set. |
| `ai_policy` | `"prior"` | Treat heuristic score as a prior hint or as a strict constraint. |
| `controls_cache_enabled` | `true` | Enable the persistent per-site controls cache. |
| `controls_cache_dir` | `"cache"` | Cache directory relative to CWD or absolute path. |
| `semantic_cache_enabled` | `true` | Enable in-session semantic cache reuse. |
| `custom_controls_dirs` | `["controls"]` | List of directories scanned for `@custom_control` Python modules. Resolved relative to CWD. |
| `timeout` | `5000` | Default action timeout in ms. |
| `nav_timeout` | `30000` | Navigation timeout in ms. |
| `log_name_maxlen` | `0` | Truncate element names in logs. `0` means no limit. |
| `log_thought_maxlen` | `0` | Truncate LLM thought strings in logs. `0` means no limit. |
| `workers` | `1` | Max hunt files to run in parallel. |
| `tests_home` | `"tests"` | Default output directory for new hunts and scan output. |
| `auto_annotate` | `false` | Insert `# 📍 Auto-Nav:` comments after URL changes during a run. |
| `channel` | `null` | Installed browser channel such as `chrome` or `msedge`. |
| `executable_path` | `null` | Absolute path to a custom executable such as Electron. |
| `retries` | `0` | Retry failed hunt files this many times. |
| `screenshot` | `"on-fail"` | Screenshot mode: `none`, `on-fail`, or `always`. |
| `html_report` | `false` | Generate or refresh `reports/manul_report.html` after the run. Recent CLI invocations within the same report session are merged instead of silently overwriting the last file. |
| `explain_mode` | `false` | Enable DOMScorer explain output. Shows per-channel scoring breakdowns for each resolved element. |

HTML report notes:

- The runtime stores recent report-session state in `reports/manul_report_state.json`.
- This is what lets separate CLI or Test Explorer invocations accumulate into one `reports/manul_report.html` during a recent session window.
- The HTML header now shows `Run Session` and `Merged invocations` so it is obvious when the file contains more than one invocation.

### First hunt file

```text
@context: Smoke test for a login flow
@title: Login Smoke
@var: {email} = admin@example.com
@var: {password} = secret123

STEP 1: Open the app
    NAVIGATE to https://example.com/login
    VERIFY that 'Sign In' is present

STEP 2: Authenticate
    Fill 'Email' field with '{email}'
    Fill 'Password' field with '{password}'
    Wait for 'Sign In' to be visible
    Click the 'Sign In' button
    VERIFY that 'Dashboard' is present

DONE.
```

### Run it

```bash
manul tests/login.hunt
```

Useful commands:

```bash
python manul.py test
manul tests/
manul --headless tests/saucedemo.hunt
manul --html-report --screenshot on-fail tests/
manul --explain tests/saucedemo.hunt
```

When `--html-report` is enabled, repeated runs from VS Code Test Explorer no longer leave only the final hunt in the HTML output. The runtime merges recent invocations into the same report session and labels the report header accordingly.

## Runtime Reference

Useful capabilities that get lost when the README is trimmed too aggressively:

- `OPEN APP` plus `executable_path` lets the same DSL drive Electron apps.
- `@schedule:` plus `manul daemon` turns a hunt into a built-in monitor or RPA task.
- `@var:`, `EXTRACT`, `SET`, and `CALL PYTHON ... into {var}` give you deterministic variable flow without hardcoding runtime values.
- `[SETUP]`, `[TEARDOWN]`, inline `CALL PYTHON`, and `manul_hooks.py` cover environment setup, backend calls, and suite-wide orchestration.
- `@custom_control` is the explicit escape hatch when a widget should be handled with raw Playwright instead of generic heuristics.
- `SCAN PAGE` and `manul record` accelerate authoring without replacing the readable DSL with low-level recordings.
- `Wait for "Text" to be visible`, `Wait for 'Spinner' to disappear`, and `Wait for "Submit" to be hidden` give the DSL a deterministic explicit-wait path backed by Playwright `locator.wait_for()` instead of hardcoded sleeps.

### Contextual UI navigation

When identical controls exist multiple times on the page, the DSL can now add a contextual qualifier instead of dropping into brittle selectors.

```text
Click the 'Delete' button NEAR 'John Doe'
Click the 'Login' button ON HEADER
Click the 'Privacy Policy' link ON FOOTER
Click the 'Delete' button INSIDE 'Actions' row with 'John Doe'
```

- `NEAR 'Anchor'` biases ranking by Euclidean pixel distance to the resolved anchor element.
- `ON HEADER` prefers elements in the top 15% of the viewport or inside `header` / `nav` ancestry.
- `ON FOOTER` prefers elements in the bottom 15% of the viewport or inside `footer` ancestry.
- `INSIDE 'Container' row with 'Text'` narrows the search to the resolved row or container subtree before normal action scoring continues.

### Explicit waits

Use explicit waits when the DOM is still settling after navigation or after an action triggers async UI updates.

```text
Wait for "Welcome, User" to be visible
Wait for 'Loading...' to disappear
Wait for "Submit" to be hidden
```

`disappear` maps to Playwright's `hidden` state, so the runtime treats `hidden` and `disappear` as the same wait target internally.

### Strict assertions

Use strict assertions when you need exact element text, exact placeholder attributes, or exact current field values instead of loose presence checks.

```text
Verify "save" button has text "Save me"
Verify "Error message" element has text "Invalid credentials"
Verify 'Login' field has placeholder "Login/Email"
Verify "Search" input has placeholder "Type to search..."
Verify "Email" field has value "captain@manul.com"
Verify "Notes" element has value "treasure map"
```

- `Verify "<element_name>" <type> has text "<expected_text>"` resolves the element through the normal DOM heuristics, reads `locator.inner_text().strip()`, and performs strict `==` comparison.
- `Verify "<element_name>" <type> has placeholder "<expected_placeholder>"` resolves the element, reads the `placeholder` attribute, and performs strict `==` comparison.
- `Verify "<element_name>" <type> has value "<expected_value>"` resolves the element, reads its current value with `input_value()` and a `value`-attribute fallback, normalizes missing values to `""`, and performs strict `==` comparison.
- On mismatch, the runtime raises a readable assertion that includes the resolved element locator plus `Expected` and `Actual` values.

### Static variables and hooks

```text
@var: {email} = admin@example.com
@var: {password} = secret123
@script: {db} = scripts.db_helpers
@script: {seed_admin_user} = scripts.db_helpers.seed_admin_user

[SETUP]
    PRINT "Preparing demo user for {email}"
    CALL PYTHON {seed_admin_user} with args: "{email}" "{password}"
    CALL PYTHON {db}.issue_login_token with args: "{email}" into {login_token}
[END SETUP]

STEP 1: Login
    NAVIGATE to https://example.com/login
    Fill 'Email' field with '{email}'
    Fill 'Password' field with '{password}'
    Click the 'Sign In' button
    VERIFY that 'Dashboard' is present

STEP 2: OTP verification
    Click the 'Send OTP' button
    CALL PYTHON api_helpers.fetch_otp with args: "{email}" "{login_token}" into {otp}
    Fill 'OTP' field with '{otp}'
    Click the 'Verify' button
    VERIFY that 'Welcome' is present

[TEARDOWN]
    PRINT "Cleaning up seeded user for {email}"
    CALL PYTHON {db}.clean_database with args: "{email}"
[END TEARDOWN]
```

- Hook syntax is bracket-only: `[SETUP]` / `[END SETUP]` and `[TEARDOWN]` / `[END TEARDOWN]`.
- `PRINT "..."` is valid inside hook blocks and resolves `{variables}` before printing.
- `CALL PYTHON ... with args: ...` is optional sugar for positional arguments; plain `CALL PYTHON mod.func "arg"` still works.
- `@script:` lets you declare a file-local alias once and reuse either `CALL PYTHON {alias}.func` or `CALL PYTHON {callable_alias}` in hooks and mission steps.
- `@script:` must use dotted Python import paths only: `scripts.db_helpers` or `scripts.db_helpers.issue_login_token`. Slash paths like `scripts/db_helpers.py` are rejected.
- File-based helpers resolve from the `.hunt` directory first, then the project root, before falling back to normal imports via `sys.path`.
- If setup fails, the mission is marked as `broken` and the browser steps are skipped. Teardown still runs after the mission whenever setup succeeded.

Supported `CALL PYTHON` forms:

```text
CALL PYTHON package.module.function
CALL PYTHON package.module.function with args: "arg1" "arg2"
CALL PYTHON package.module.function "arg1" "arg2" into {result}
CALL PYTHON package.module.function into {result}
CALL PYTHON {module_alias}.function
CALL PYTHON {module_alias}.function into {result}
CALL PYTHON {callable_alias}
CALL PYTHON {callable_alias} with args: "arg1" "arg2"
CALL PYTHON {callable_alias} into {result}
```

Alias examples:

```text
@script: {db} = scripts.db_helpers
@script: {issue_login_token} = scripts.db_helpers.issue_login_token
```

### Tags, scheduler, and execution controls

```text
@tags: smoke, regression
@schedule: every 5 minutes
@import: Login, Logout from lib/auth.hunt
@export: Checkout
```

```bash
manul tests/ --tags smoke
manul daemon tests/ --headless
manul pack lib/auth --output dist/
manul install dist/auth-1.0.0.huntlib
```

Shared library support: `@import:` pulls named STEP blocks from other `.hunt` files, `USE Login` expands them inline, and `@export:` controls which blocks are importable. Package archives (`.huntlib`) can be packed and installed with `manul pack` and `manul install`.

### Global lifecycle hooks

```python
from manul_engine import before_all, after_all, GlobalContext

@before_all
def setup(ctx: GlobalContext) -> None:
    ctx.variables["BASE_URL"] = "https://staging.example.com"

@after_all
def teardown(ctx: GlobalContext) -> None:
    cleanup_test_data()
```

## Testing and Benchmarks

The project is alpha, but it is not undocumented or untested.

- `python manul.py test` runs the synthetic and unit suite
- `tests/*.hunt` holds integration-style hunts
- `benchmarks/run_benchmarks.py` exercises adversarial fixtures such as dynamic IDs, overlays, nested tables, and custom dropdowns

Representative coverage areas include:

- logical STEP grouping and hierarchical execution
- `ManulSession` API behavior
- scheduler parsing
- lifecycle hooks
- scoped variables
- HTML reporting
- iframe routing
- visibility filtering and TreeWalker behavior
- custom controls and lazy control loading

## Docker CI/CD Runner

ManulEngine ships an alpha-stage headless CI runner image for browser automation pipelines.

```bash
docker run --rm --shm-size=1g \
  -v $(pwd)/tests:/workspace/tests:ro \
  -v $(pwd)/reports:/workspace/reports \
  ghcr.io/alexbeatnik/manul-engine:0.0.9.23 \
  --html-report --screenshot on-fail tests/
```

All `MANUL_*` environment variables work as overrides:

```bash
docker run --rm --shm-size=1g \
  -e MANUL_WORKERS=4 \
  -e MANUL_BROWSER=firefox \
  -v $(pwd)/tests:/workspace/tests:ro \
  -v $(pwd)/reports:/workspace/reports \
  ghcr.io/alexbeatnik/manul-engine:0.0.9.23 \
  tests/
```

The image runs as non-root user `manul` (UID 1000), includes `dumb-init` for proper signal handling, and sets `--no-sandbox --disable-dev-shm-usage` by default. Build with additional browsers via `--build-arg BROWSERS="chromium firefox"`. A `docker-compose.yml` is included for local development with `manul` and `manul-daemon` services.

## What's New in v0.0.9.23

- **Security hygiene:** Eliminated false-positive "shell access" alert from package security scanners (socket.dev) by dynamically constructing markdown code-fence markers in the LLM response parser.
- **Manual release tagging workflow:** New `release_tag.yml` GitHub Actions workflow for creating version tags via `workflow_dispatch` without requiring a local git environment.

<details>
<summary>v0.0.9.22</summary>

- **@import / @export / USE system:** Reusable `.hunt` libraries. `@import: Login from lib/auth.hunt` pulls named STEP blocks, `USE Login` expands them inline, and `@export:` controls visibility. `@var:` from source files inherit at the lowest (import) scope. Wildcard imports, aliases (`@import: Login as AuthLogin`), and package-style sources (`@import: Login from @my-lib`) are all supported.
- **`manul pack` / `manul install` CLI:** Pack `.hunt` libraries into distributable `.huntlib` archives and install them locally or globally (`~/.manul/hunt_libs/`). Lockfile (`huntlib-lock.json`) tracks installed versions.
- **Docker CI/CD runner:** Multi-stage `Dockerfile` packaging ManulEngine as a headless CI runner image (`ghcr.io/alexbeatnik/manul-engine`). Non-root `manul` user (UID 1000), `dumb-init` PID 1, Chromium-only by default (configurable via `BROWSERS` build arg). Includes `docker-compose.yml` with `manul` and `manul-daemon` services.
- **GitHub Actions workflows:** `release.yml` handles unified release automation (PyPI + GHCR + GitHub Release on `v*` tags), `docker-dev.yml` pushes dev images on `main` merge, and `manul-ci.yml` provides a reusable example workflow for downstream repositories.

</details>

## License

**Version:** 0.0.9.23

Apache-2.0.