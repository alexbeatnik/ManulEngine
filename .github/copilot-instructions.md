
# Copilot Instructions — ManulEngine

## What is this project?

ManulEngine is a highly resilient, neuro-symbolic browser automation framework.
It drives Chromium (and optionally Firefox or WebKit) via Playwright, scores DOM elements with 20+ heuristic rules,
and falls back to a local LLM (Ollama) when the heuristics are ambiguous.
It is designed to bypass modern web traps (Shadow DOM, invisible overlays, zero-pixel honeypots, custom dropdowns) entirely locally — no cloud APIs.

Current operating mode in this repo is typically **mixed**:
- Heuristics rank candidates first.
- LLM is called only when heuristics are not confident (best score < `MANUL_AI_THRESHOLD`).
- When LLM is used, heuristic `score` is treated as a *prior* (hint), not a hard constraint (`MANUL_AI_POLICY=prior`).
- If `model` is `null` or not set, the engine runs in **heuristics-only mode** (AI fully disabled, threshold = 0).

**Stack:** Python 3.11 · Playwright async · Ollama (qwen2.5:0.5b, optional) · stdlib only (no dotenv)

## Repository layout

```text
manul.py                   Dev CLI entry point (intercepts `test` subcommand)
manul_engine_configuration.json  Project configuration (JSON, replaces .env)
pages.json                 Page name registry for Auto-Nav annotations (nested per-site format)
pyproject.toml             Build config — package name: manul-engine, version: 0.0.9.0
manul_engine/
  __init__.py              public API — re-exports ManulEngine
  core.py                  ManulEngine class (LLM, resolution, run_mission, self-healing)
  cache.py                 _ControlsCacheMixin (persistent per-site controls cache)
  actions.py               _ActionsMixin (navigate, scroll, extract, verify, drag, press, right_click, upload, _execute_step, scan_page)
  reporting.py             StepResult, MissionResult, RunSummary dataclasses
  reporter.py              Self-contained HTML report generator (dark theme, native <details>/<summary> accordions, Flexbox step layout, base64 screenshots, control panel with Show Only Failed toggle and tag filter chips)
  prompts.py               JSON config loader, thresholds, LLM prompt templates
  scoring.py               DOMScorer class — normalised 0.0–1.0 float scoring, WEIGHTS dict, SCALE=177,778, pre-compiled regex, score_elements() backward-compatible API
  js_scripts.py            All JS injected into the browser (TreeWalker-based SNAPSHOT_JS with PRUNE set, SCAN_JS)
  scanner.py               Smart Page Scanner — scan_page(), build_hunt(), scan_main()
  helpers.py               substitute_memory(), extract_quoted(), env_bool(), detect_mode(), classify_step(), timing constants
  cli.py                   Public installed CLI entry point (manul command + manul scan subcommand); ParsedHunt NamedTuple
  controls.py              Custom Controls registry (@custom_control, get_custom_control, load_custom_controls)
  hooks.py                 [SETUP] / [TEARDOWN] hook parser and executor
  lifecycle.py             Global Lifecycle Hook Registry (@before_all, @after_all, @before_group, @after_group, GlobalContext, load_hooks_file)
  _test_runner.py          Dev-only synthetic test runner (not in public CLI)
  test/
    test_00_engine.py       synthetic DOM micro-suite (local HTML via Playwright)
    test_01_ecommerce.py    synthetic DOM scenario pack
    ...
    test_15_facebook_final_boss.py
    test_16_hooks.py        [SETUP]/[TEARDOWN] unit tests (41 assertions, no browser)
    test_17_frontend_hell.py   frontend anti-patterns (overlays, z-index traps, React portals)
    test_18_disambiguation.py  ambiguous element targeting
    test_19_custom_controls.py Custom Controls registry + engine interception (19 assertions, no browser)
    test_20_variables.py       @var: static variable declaration (17 assertions, no browser)
    test_21_dynamic_vars.py    CALL PYTHON ... into {var} dynamic variable capture
    test_22_tags.py            @tags: / --tags CLI filter (20 assertions, no browser)
    test_23_advanced_interactions.py  PRESS/RIGHT CLICK/UPLOAD commands (48 assertions, no browser)
    test_24_reporting.py       StepResult/MissionResult/RunSummary dataclasses (45 assertions)
    test_25_reporter.py        HTML report generator (65 assertions, no browser)
    test_26_wikipedia_search.py  name_attr heuristic scoring (20 assertions, no browser)
    test_27_lifecycle_hooks.py   Global Lifecycle Hook system (57 assertions, no browser)
    test_28_logical_steps.py     Logical STEP ordering and parser (48 assertions, no browser)
    test_29_iframe_routing.py    Cross-frame element resolution (25 assertions)
    test_30_heuristic_weights.py DOMScorer priority hierarchy (32 assertions)
    test_31_visibility_treewalker.py TreeWalker PRUNE/checkVisibility (20 assertions)
    test_32_verify_enabled.py    VERIFY ENABLED/DISABLED state verification (20 assertions)
    test_33_call_python_args.py  CALL PYTHON with positional arguments (44 assertions, no browser)
    test_34_verify_checked.py    VERIFY checked/NOT checked state verification (20 assertions, no browser)
    test_35_scanner.py           Smart Page Scanner build_hunt() (44 assertions, no browser)
    test_36_scoring_math.py      Exact numerical scoring validation (29 assertions, no browser)
tests/
  demoqa.hunt             integration: forms, checkboxes, radios, tables
  mega.hunt               integration: all element types, drag-drop, shadow DOM, custom dropdowns
  rahul.hunt              integration: radios, autocomplete, hover
  saucedemo.hunt          integration: login, inventory, cart
  wikipedia.hunt          integration: search, navigate, extract, verify, shadow-dom inputs
  demo_controls.hunt      integration: Custom Controls workflow
  demo_login.hunt         integration: login with @var: static variables
  demo_variables.hunt     integration: @var: + CALL PYTHON into {var} combined
vscode-extension/
  package.json              Extension manifest (v0.0.90)
  src:
    extension.ts            Activation, command registration
    huntRunner.ts           Spawns manul CLI; cwd resolved to workspace root
    huntTestController.ts   VS Code Test Explorer integration (step-level reporting)
    configPanel.ts          Webview sidebar: config editor + Ollama model discovery
    cacheTreeProvider.ts    Sidebar tree: controls cache browser
    stepBuilderPanel.ts     Sidebar webview: step-insertion buttons + new hunt file (incl. Scan Page)
    debugControlPanel.ts    Singleton QuickPick overlay for interactive debug stepping
    constants.ts            Shared constants (DEFAULT_CONFIG_FILENAME, PAUSE_MARKER, terminal names, getConfigFileName())
  syntaxes/hunt.tmLanguage.json  Hunt file syntax grammar
```

## How the engine works

1. **Snapshot** — `SNAPSHOT_JS` walks the DOM with `document.createTreeWalker()` and a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`). Visibility is checked via `checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })` with `offsetWidth/offsetHeight` fallback. Hidden checkbox/radio/file inputs are kept (special-input exception). `_snapshot()` iterates `page.frames`, injects the script per frame, and tags each element with `frame_index`.
2. **Exact-match pass** — quick filter by `name`, `aria-label`, `data-qa` substring.
3. **Heuristic scoring** — `DOMScorer.score_all()` ranks candidates using normalised `0.0–1.0` floats across five weighted channels: `cache` (2.0), `semantics` (0.60), `text` (0.45), `attributes` (0.25), `proximity` (0.10). Final score = weighted sum × penalty multiplier × `SCALE` (177,778). The biggest single boosts are semantic cache reuse (+1.0 cache / 200k+ scaled) and `data-qa` exact match (+1.0 text / ~80k scaled). Penalties: disabled ×0.0, hidden ×0.1.
4. **LLM fallback** — if best score < threshold, ask the LLM to pick the element.
5. **AI Rejection & Anti-phantom guard** — LLM can return `{"id": null}` if no plausible target is found. Engine handles `null` by blacklisting the current candidates and triggering self-healing.
6. **Action** — type / click / select / hover / drag. Non-shadow interactions primarily use Playwright with `force=True` plus retries; Shadow DOM interactions use a **JS fallback** (`window.manulClick`, `window.manulType`) to bypass elements that Playwright cannot target.
7. **Self-healing** — on failure or AI rejection, scroll down, blacklist bad IDs, and retry (up to 3 retries). Each element-resolution attempt may also scroll-and-retry internally.
8. **Persistent controls cache** — successful control resolutions are stored in a per-site folder with separate per-page subfolders (page-object style), each containing `controls.json`, and reused on later runs. Cached controls are reused only if a matching live candidate still exists in the current snapshot; changed controls overwrite previous entries for that URL page.

## Interaction modes

Detected from step keywords:

* `input` — "type", "fill", "enter"
* `clickable` — "click", "double", "check", "uncheck"
* `select` — "select", "choose"
* `hover` — "hover"
* `drag` — "drag" + "drop"
* `locate` — fallback (highlight only)

## Step format

Steps are parsed by `run_mission()` and must be atomic browser instructions. **STEP-grouped (unnumbered) is the canonical format for all new files.** The legacy numbered format is supported for backward compatibility.

**STEP-grouped format — canonical (use this for all new files):**

```text
STEP 1: Navigate to the login page
NAVIGATE to https://example.com/login
VERIFY that 'Sign In' is present

STEP 2: Fill credentials
Fill 'Username' field with 'admin'
Fill 'Password' field with 'secret'
Click the 'Login' button
VERIFY that 'Welcome' is present.

STEP 3: Wrap up
EXTRACT the 'Product Price' into {price}
DONE.
```

**Numbered format — legacy (backward compat only, do not use for new files):**

```text
"1. NAVIGATE to https://example.com"
"2. Fill 'Username' field with 'admin'"
"3. Click the 'Login' button"
"4. VERIFY that 'Welcome' is present."
"5. DONE."
```

Rules for STEP-grouped files:
* `run_mission()` switches to line-by-line parsing when it detects **either** a `STEP` marker OR recognizable action keywords (NAVIGATE, VERIFY, DONE, etc.) in an unnumbered file. STEP markers are not required — a file containing only plain unnumbered action lines is parsed directly without them.
* `STEP [number]: [description]` — number is optional; description is used for console output and HTML report section headers.
* Blank lines between groups are allowed and ignored.
* All other keywords (NAVIGATE, VERIFY, DONE, etc.) work identically in both formats.
* Mixed numbered+STEP (e.g. `1. STEP 1: ...`) is also valid: the numbered split runs and STEP markers are detected by `classify_step()` as `"logical_step"` kind, same as in STEP-grouped mode.

**System Keywords** parsed directly by `run_mission()` (these skip heuristics):

* `NAVIGATE to [url]`
* `WAIT [seconds]`
* `PRESS ENTER`
* `PRESS [Key]` — Presses any key or combination globally (e.g. `PRESS Escape`, `PRESS Control+A`).
* `PRESS [Key] on [Target]` — Presses a key on a specific resolved element (e.g. `PRESS ArrowDown on 'Search Input'`).
* `RIGHT CLICK [Target]` — Right-clicks a resolved element to open a context menu.
* `UPLOAD 'File' to 'Target'` — Uploads a file to a file-input element. Path is resolved relative to the `.hunt` file's directory, then CWD. Both file path and target must be quoted.
* `SCROLL DOWN` or `SCROLL DOWN inside the list`
* `EXTRACT [target] into {variable_name}`
* `VERIFY that [target] is present` / `is NOT present` / `is DISABLED` / `is ENABLED` / `is checked`
* `SCAN PAGE` — scans the current page for interactive elements and prints a draft `.hunt` to the console.
* `SCAN PAGE into {filename}` — same, but also writes the draft to `{filename}`. Default output dir is `tests_home` from config.
* `DEBUG` / `PAUSE` — pauses execution at that step. In interactive terminal mode (`--debug`), draws a dashed red border around the resolved element and prompts the user; when run via VS Code extension, emits the debug pause protocol marker (see below).
* `DONE.`

Everything else goes through `_execute_step` (mode detection → resolve → action).
Optional steps contain "if exists" / "optional" **outside** the quoted target (e.g. `"Click 'Close Ad' if exists"`).

## Writing integration tests (hunt files)

Hunt files are plain-text test scenarios parsed by `parse_hunt_file()` (extracts `@context` / `@title` / `@tags`, strips `#` comments, collects hook blocks) then executed by `run_mission()`. **The STEP-grouped unnumbered format is the mandatory standard for all new hunt files.** The legacy numbered format is still supported but must not be used in new files.

### 1. File Naming & Location
* For this repo's default auto-discovery (`python manul.py` with no target), hunt files are discovered under the `tests/` directory.
* You can also pass a specific `.hunt` file or a directory path to `manul.py` to run hunts from any location.
* Must use the `.hunt` extension. The filename can be anything — no prefix is required or enforced.

### 2. Metadata Headers
Placed at the top of the file. Used by the engine for logging and LLM context.
* `@context: [description]` — Strategic context passed to the engine.
* `@title: [short_title]` — Short title representing the test suite. `@blueprint:` is also accepted for backward compatibility.
* `@tags: tag1, tag2` — Arbitrary comma-separated run tags. Used with `manul --tags smoke tests/` to filter which files execute.

### 3. Comments
* Use `#` at the beginning of a line for comments. Any line whose trimmed text starts with `#` is ignored during execution; `#` appearing after a step on the same line is treated as part of the step text, not a comment.

### 4. Step Formatting
**STEP-grouped (unnumbered) is the mandatory standard for all new hunt files.**
* Use `STEP N: label` headers to mark logical groups. The STEP number is optional (`STEP: label` is also valid).
* All action lines following a STEP header must be **plain, unnumbered text** — no `1.` prefix, no bullet points, no dashes.
* `run_mission()` detects `STEP` markers **or** recognizable action keywords (NAVIGATE, VERIFY, DONE, etc.) and automatically switches to line-by-line splitting. STEP markers are not required — a file with only plain unnumbered action lines is also parsed directly.
* Blank lines between groups are allowed and ignored.
* The classic numbered format (`1. CMD`, `2. CMD`, …) is still supported for backward compatibility, but numeric prefixes are stripped from the HTML report and must not be used when generating new files.
* Only genuinely free-form natural language with no recognized keywords is routed through the LLM planner (less deterministic; requires Ollama).
* Elements should be wrapped in single or double quotes for best heuristic matching (e.g., `'Submit'`, `"Password"`).

**ABSOLUTE RULE — Zero Tolerance:**
> When generating or suggesting `.hunt` files:
> 1. You MUST use the **Clean, Unnumbered DSL Syntax**. NEVER prepend numbers (`1. `, `2. `) to execution actions.
> 2. You MUST use **Logical `STEP` Grouping** (`STEP [optional number]: [Description]`) to structure E2E flows, matching manual QA test cases. These map perfectly to the Enterprise HTML Reporter's accordions.

### 5. System Keywords (parser-detected)
These keywords are detected via word-boundary regex, bypass heuristics, and are handled directly by the engine parser:
* `NAVIGATE to [url]` — Loads a URL and waits for DOM settlement.
* `WAIT [seconds]` — Hard sleep (e.g., `WAIT 2`).
* `PRESS ENTER` — Presses the Enter key on the currently focused element (useful to submit forms after filling a field).
* `PRESS [Key]` — Presses any key or combination globally (e.g. `PRESS Escape`, `PRESS Control+A`). Mapped to `page.keyboard.press(key)`.
* `PRESS [Key] on [Target]` — Presses a key on a specific element resolved via heuristics (e.g. `PRESS ArrowDown on 'Search Input'`). Mapped to `locator.press(key)`.
* `RIGHT CLICK [Target]` — Right-clicks a resolved element (e.g. `RIGHT CLICK 'Context Menu Area'`). Mapped to `locator.click(button='right')`. Shadow DOM elements dispatch a JS `contextmenu` event.
* `UPLOAD 'File' to 'Target'` — Uploads a file to a file-input element (e.g. `UPLOAD 'avatar.png' to 'Profile Picture'`). Both file path and target must be quoted. File path is resolved relative to the `.hunt` file's directory first, then CWD. Mapped to `locator.set_input_files(path)`.
* `SCROLL DOWN` — Scrolls the main page down by one viewport height. `SCROLL DOWN inside the list` — scrolls the first dropdown-style scroll container (e.g., `#dropdown` or any element whose class name contains `dropdown`) all the way to the bottom (by setting `scrollTop = scrollHeight`). Phrases like `SCROLL DOWN to the very bottom` are accepted but currently behave the same as a single `SCROLL DOWN` on the main page (they do not auto-scroll the page all the way to the bottom).
* `EXTRACT [target] into {variable_name}` — Extracts text data into memory.
* `VERIFY that [target] is present` (or `is NOT present`, `is DISABLED`, `is ENABLED`, `is checked`)
* `SCAN PAGE` — Runs `SCAN_JS` on the current page, maps results to hunt steps, prints a draft to console.
* `SCAN PAGE into {filename}` — Same, but also writes the draft to `{filename}`. Output defaults to `{tests_home}/draft.hunt` (reads `tests_home` from `manul_engine_configuration.json`, defaults to `tests/`).
* `DONE.` — Explicitly ends the mission.
* `[SETUP]` / `[END SETUP]` — Block wrapping `CALL PYTHON <module>.<function>` lines. Runs **before** the browser launches. If any line fails, the mission is skipped and teardown is not called.
* `[TEARDOWN]` / `[END TEARDOWN]` — Cleanup block. Runs in a `finally` block **after** the mission (pass or fail). Only executed if `[SETUP]` succeeded. Failure is logged but does not override the mission result.
* Inside hook blocks, each non-blank non-comment line must have the form: `CALL PYTHON <module>.<function>` (optionally with positional arguments — see Section 7b). The module is resolved in this order: the `.hunt` file's directory → `CWD` → standard `importlib.import_module`. Target functions must be **synchronous**.
* **Inline `CALL PYTHON` steps** — `CALL PYTHON <module>.<function>` (with optional positional arguments) is also valid as a standard numbered step anywhere in the main mission body (outside hook blocks). It uses the identical module resolution, state isolation, and sync-only rules as hook blocks. A failure stops the mission immediately.

### 6. Interaction Actions (Parsed Modes)
If not a System Keyword, the engine detects the interaction mode based on verbs:
* **Clicking (`clickable`)**: `Click the 'Login' button`, `DOUBLE CLICK the 'Image'`, `Click on the 'Home' link`.
* **Typing (`input`)**: `Fill 'Email' field with 'test@manul.ai'`, `Type 'Search' into that field`.
* **Select/Dropdown (`select`)**: `Select 'Option 1' from the 'Menu' dropdown`.
* **Checkboxes/Radios (`clickable`)**: `Check the checkbox for 'Terms'`, `Uncheck the checkbox for 'Promo'`, `Click the radio button for 'Male'`.
* **Hovering (`hover`)**: `HOVER over the 'Menu'`.
* **Drag & Drop (`drag`)**: `Drag the element "Item" and drop it into "Box"`.
* **Locate (`locate`)**: `Locate the text input...` (highlights without acting).

### 7. Variables & Memory
Variables extracted using `EXTRACT` can be substituted in downstream steps.
* *Extract:* `EXTRACT the Price of 'Laptop' into {laptop_price}`
* *Reuse:* `VERIFY that '{laptop_price}' is present.`

### 7a. Static Variable Declaration (`@var:`)
Declare static test data at the top of the file using `@var: {key} = value`. These values are pre-populated into the engine's runtime memory before any step runs and can be interpolated exactly like `EXTRACT` variables.
* Both brace and bare-key forms are accepted: `@var: {email} = ...` and `@var: email = ...` are equivalent. Keys are stored without braces.
* Values may contain spaces and are stripped of leading/trailing whitespace.
* **MANDATORY rule for AI-generated hunt files:** When generating or suggesting `.hunt` test files, **NEVER hardcode test data** (emails, passwords, usernames, search queries, IDs, etc.) directly inside `Fill`, `Type`, or `Select` steps. **ALWAYS** declare them at the top using `@var:` and reference them via `{placeholder}` in the steps.

Correct:
```text
@var: {user_email} = admin@example.com
@var: {password}   = secret123

STEP 1: Login
Fill 'Email' with '{user_email}'
Fill 'Password' with '{password}'
```

Wrong (do not do this):
```text
STEP 1: Login
Fill 'Email' with 'admin@example.com'
Fill 'Password' with 'secret123'
```

### 7b. Dynamic Variable Capture (`CALL PYTHON ... into {var}`)
`CALL PYTHON <module>.<function> [args...] into {variable_name}` captures the **return value** of the function as a string and stores it in the engine's runtime memory, available for `{placeholder}` substitution in all subsequent steps. The `to` keyword is accepted as an alias for `into`.
* The function must be **synchronous** and return any value; the engine calls `str()` on the result before storing it.
* **Positional arguments** can be passed after the dotted function name, before the optional `into {var}` clause. Arguments are tokenised with `shlex.split()` — single-quoted, double-quoted, and unquoted tokens are all accepted. `{var}` placeholders inside arguments are resolved from the engine's runtime memory (or the `parsed_vars`/`variables` dict for hook blocks).
* Calls without arguments remain fully backward-compatible — `CALL PYTHON mod.func` and `CALL PYTHON mod.func into {var}` work exactly as before.
* **MANDATORY rule for AI-generated hunt files:** Whenever a step needs data that comes from a backend call, API, OTP service, or any computed value, capture it with `CALL PYTHON ... into {var}` and reference the result via `{var}` in following steps. Never hardcode computed or runtime values directly in steps.

Full syntax variants:
```text
CALL PYTHON <module>.<function>
CALL PYTHON <module>.<function> "arg1" 'arg2' {var}
CALL PYTHON <module>.<function> "arg1" {var} into {result}
CALL PYTHON <module>.<function> into {result}
```

Correct:
```text
3. CALL PYTHON helpers.api.get_otp "{email}" into {otp_code}
4. Fill 'OTP' field with '{otp_code}'
```

Wrong (do not do this):
```text
4. Fill 'OTP' field with '123456'
```

### 8. Best Practices
* **Specify Element Type:** Include words like `button`, `field`, `link`, `dropdown`, `checkbox`, `radio` outside quotes. This acts as a strong heuristic signal.
* **Exact Text Matching:** Put target texts in quotes (`'Save'`) to yield a high heuristic score.
* **Verify After Actions:** Always use a `VERIFY` step after taking a significant action (e.g., login, form submit) before assuming the new page state.
* **Implicit Context:** The engine reuses context if you refer to previous elements implicitly, e.g., `Type "Password" into that field`.
* **MANDATORY — Reporting, Screenshots, and Retries are CLI/Execution concerns, NOT DSL syntax.** Never write steps like `RETRY 3`, `TAKE SCREENSHOT`, `GENERATE REPORT`, or similar in `.hunt` files. These features are controlled exclusively via CLI flags (`--retries`, `--screenshot`, `--html-report`), `manul_engine_configuration.json` keys (`retries`, `screenshot`, `html_report`), or VS Code Extension settings (`manulEngine.retries`, `manulEngine.screenshotMode`, `manulEngine.htmlReport`). When asked to add retries or reporting to a test, instruct the user to use CLI flags or config — never inject pseudo-steps into the hunt file.

### 9. Python Hooks (`[SETUP]` / `[TEARDOWN]`) and Inline `CALL PYTHON` Steps
Hook blocks run synchronous Python functions **outside the browser** — the primary use case is injecting database state or calling an API before the mission starts. Inline `CALL PYTHON` steps run **inside the mission** as numbered steps, with identical safety guarantees.
* When generating `.hunt` tests that require specific initial data (users, records, session tokens), **ALWAYS** use `[SETUP]` with `CALL PYTHON`. Never use brittle UI steps (e.g., "Click Create User") as test preconditions.
* **CRITICAL — Inline Python for mid-test backend interaction:** When a step requires interacting with a backend, database, or API mid-test — such as fetching an OTP, a magic link, a confirmation token, or triggering a backend job before a UI action — **DO NOT simulate it via the UI**. Use an inline `CALL PYTHON <module>.<func>` step directly in the numbered sequence. This is faster, more reliable, and immune to UI timing issues.
  ```text
  2. CLICK the 'Send OTP' button
  3. CALL PYTHON api_helpers.fetch_otp "{email}" into {otp}
  4. Fill 'OTP' field with '{otp}'
  ```
* `[TEARDOWN]` cleanup runs whether the mission passed or failed. Use it to delete test records and reset state.
* Target functions **must be synchronous**. Async callables are explicitly rejected with a descriptive error.
* Module resolution order: hunt file's directory → `CWD` → `sys.path`. Modules from the first two scopes are executed in isolation — never inserted into `sys.modules` — preventing cross-test contamination.

## Code patterns to follow

* Import: `from manul_engine import ManulEngine` (never `engine` or `framework`).
* `scoring.py` owns `DOMScorer` class — normalised `0.0–1.0` float scoring with five weighted channels (`WEIGHTS` dict: cache=2.0, text=0.45, attributes=0.25, semantics=0.60, proximity=0.10). `SCALE=177,778` maps the weighted float to integer thresholds expected by `core.py`. `score_elements()` is the backward-compatible entry point that delegates to `DOMScorer.score_all()`. Receives `learned_elements` and `last_xpath` as kwargs. Pre-compiled regex loaded at module import; per-element strings normalised in `_preprocess()`.
* **Safety first in `scoring.py`:** Always cast fetched attributes using `str(el.get("...", ""))`. JavaScript can pass objects (like `SVGAnimatedString` for SVG icons) instead of strings, which will crash Python's `.lower()`.
* **iframe routing in `core.py`:** `_snapshot()` iterates `page.frames`, evaluates `SNAPSHOT_JS` per frame, tags elements with `frame_index`. `_frame_for(page, el)` resolves the correct Playwright `Frame` by index with stale fallback to main frame. All 12+ locator call-sites in `actions.py` route through the resolved frame. Cross-origin frames are silently skipped (3-retry, 1.5s backoff on `closed` errors).
* **TreeWalker in `js_scripts.py`:** `SNAPSHOT_JS` uses `document.createTreeWalker()` with a `PRUNE` set (`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`). Visibility checked via `checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })` with `offsetWidth/offsetHeight` fallback. Hidden checkbox/radio/file inputs are kept (special-input exception). No `getComputedStyle` in the hot loop.
* `actions.py` is a **mixin** (`_ActionsMixin`) inherited by `ManulEngine` in `core.py`.
* `cache.py` is a **mixin** (`_ControlsCacheMixin`) inherited by `ManulEngine` in `core.py`. It owns all persistent per-site controls-cache logic.
* `ManulEngine` MRO: `class ManulEngine(_ControlsCacheMixin, _ActionsMixin)` in `core.py`.
* `prompts.py` loads config from `manul_engine_configuration.json` (CWD first, then package root fallback). No dotenv dependency.
* `js_scripts.py` owns **all** JavaScript constants injected into the browser — no inline JS in Python files. This includes `SCAN_JS` (Smart Page Scanner).
* `scanner.py` owns the standalone scan logic: `SCAN_JS` is imported from `js_scripts.py`; `build_hunt()` maps raw element dicts to hunt steps; `scan_page()` is the async Playwright runner; `scan_main()` is the async CLI entry called by `cli.py`. `_default_output()` reads `tests_home` from the config to derive the default output path.
* `helpers.py` provides `env_bool(name, default)` for parsing boolean env vars; `detect_mode(step)` returns the interaction mode string (`"input"`, `"clickable"`, `"select"`, `"hover"`, `"drag"`, `"locate"`); `classify_step(step)` returns a step kind string (`"navigate"`, `"wait"`, `"scroll"`, `"extract"`, `"verify"`, `"press_enter"`, `"press"`, `"right_click"`, `"upload"`, `"scan_page"`, `"call_python"`, `"debug"`, `"done"`, or `"action"`) — used by `run_mission()` and `_execute_step()` to avoid duplicated regex dispatches.
* **Null model = heuristics-only:** When `model` is `None`, `_llm_json()` returns `None` immediately. `get_threshold(None)` returns `0`. No Ollama calls are made.
* **`scan_main` must be `async`** — it is called with `await` from inside `cli.main()` which runs under `asyncio.run()`. Never use `asyncio.run()` inside `scan_main`.
* **Debug mode:** `ManulEngine(debug_mode=True, break_steps={N,...})`. `debug_mode=True` (from `--debug`) highlights the resolved element and pauses before every step using `input()` in TTY or Playwright's `page.pause()`. `break_steps` (from `--break-lines`) pauses only at listed step indices using the stdout/stdin panel protocol when stdout is not a TTY. The two are mutually exclusive in practice — the extension only ever sets `break_steps` via `--break-lines`.
* **Element highlight in debug mode:** When `debug_mode=True` (or a `break_steps` pause fires), the engine calls `highlight_element(page, locator)` which injects `<style id="manul-debug-style">` (once) and sets `data-manul-debug-highlight="true"` on the target element, producing a persistent 4px magenta outline + glow that stays until `clear_highlight(page)` is called just before the action executes. A separate `_highlight()` method draws a short 2-second flash (non-debug, `setTimeout` inside JS) for non-pausing visual feedback.
* `hooks.py` owns all `[SETUP]` / `[TEARDOWN]` parsing (`extract_hook_blocks()`) and execution (`execute_hook_line()`, `run_hooks()`). `parse_hunt_file()` in `cli.py` returns a `ParsedHunt` NamedTuple with 8 fields: `mission`, `context`, `title`, `step_file_lines`, `setup_lines`, `teardown_lines`, `parsed_vars`, `tags`. `parsed_vars` is a `dict[str, str]` populated from `@var: {key} = value` header lines. `tags` is a `list[str]` populated from `@tags: tag1, tag2` header lines; empty list when absent. Modules resolved via `importlib.util.spec_from_file_location` + `spec.loader.exec_module(fresh_ModuleType)` — **never** inserted into `sys.modules`. Target functions must be synchronous; async callables are rejected before invocation.
* **Auto-Nav annotation:** When `auto_annotate` is enabled, `run_mission()` captures `url_before = page.url` before every step. For `NAVIGATE` steps, the annotation is written above the step itself. For all other steps, `url_after` is checked in the `finally` block — if the URL changed, `_auto_annotate_navigate(page, hunt_file, step_file_lines, i+1)` is called to insert a comment above the *next* step line. The comment uses the mapped page name when found in `pages.json`, or the full URL when the lookup returns an `"Auto:"` placeholder.
* **`pages.json` — nested per-site format:** `{ "<site_root_url>": { "Domain": "<display_name>", "<regex_or_exact_url>": "<page_name>" } }`. `lookup_page_name(url)` in `prompts.py` re-reads this file from disk on **every call** (live edits take effect immediately with no restart). Resolution order: exact URL key → regex/substring patterns (skipping `"Domain"` key) → `"Domain"` fallback. When no site block matches, a new nested entry is auto-generated. The longest-prefix site block wins when multiple blocks could match.
* **`_debug_prompt()` `debug-stop` token:** When Python receives `"debug-stop"` on stdin from the VS Code extension (user pressed ⏹ Debug Stop), it clears **both** `self._user_break_steps = set()` and `self.break_steps = set()`, then breaks the pause loop. The test run continues to completion without any further pauses.
* **Reporting & HTML reports:** `reporting.py` owns `StepResult`, `MissionResult` (with `__bool__` — truthy if all steps passed; has `tags: list[str]` for `@tags` from `.hunt` files), and `RunSummary` dataclasses. `reporter.py` owns `generate_report(summary, output_path)` — produces a self-contained dark-themed HTML file with dashboard stats, native `<details>/<summary>` accordions (collapsed by default, auto-expanded on failure), Flexbox step rows, inline base64 screenshots, a **control panel** with "Show Only Failed" checkbox toggle, and **tag filter chips** (dynamically collected from all missions' `tags`). Each `<div class="mission">` carries `data-status` and `data-tags` attributes for JS filtering. All artifacts (logs, HTML reports) are saved to `reports/` (auto-created by `cli.py`). The `reports/` directory is `.gitignored`.
* **Screenshot capture:** `run_mission()` accepts `screenshot_mode` (`"none"`, `"on-fail"`, `"always"`). Screenshots are stored as base64 PNGs in `StepResult.screenshot`.

## Running tests

```bash
# Activate venv (common folder names: .venv, venv, env, .env)
source .venv/bin/activate       # Linux/Mac (.venv)
source venv/bin/activate        # Linux/Mac (venv)
.venv\Scripts\activate          # Windows

# Synthetic DOM laboratory tests (local HTML via Playwright; no real websites)
python manul.py test

# Integration tests (needs Playwright browsers; Ollama optional)
manul tests/                     # run all *.hunt files in tests/
manul tests/wikipedia.hunt       # single hunt
manul --headless tests/          # headless mode
manul --browser firefox tests/   # run in Firefox instead of Chromium
manul --tags smoke tests/        # run only files tagged 'smoke'
manul --tags smoke,regression tests/  # files tagged smoke OR regression

# Interactive debug mode (terminal) — pauses before every step, prompts ENTER
manul --debug tests/saucedemo.hunt

# Gutter breakpoint mode (used by VS Code extension debug runner)
# Pause at steps whose file line numbers match; emits stdin/stdout debug protocol
manul --break-lines 5,10,15 tests/saucedemo.hunt

# Smart Page Scanner
manul scan https://example.com                   # scan → tests/draft.hunt (tests_home default)
manul scan https://example.com tests/my.hunt     # scan → explicit output file
manul scan https://example.com --headless        # headless scan

# Retries, screenshots, HTML reports
manul tests/ --retries 2                          # retry failed hunts up to 2 times
manul tests/ --html-report                        # generate reports/manul_report.html
manul tests/ --retries 2 --screenshot on-fail --html-report  # full CI combo
manul tests/ --screenshot always --html-report    # every-step forensic report
```

Ollama is optional, but required for:
- free-text tasks (AI planner)
- AI element-picker fallback when heuristics confidence is below `ai_threshold`

To use Ollama: install the [Ollama app](https://ollama.com), run `pip install ollama` (Python client), pull a model (`ollama pull qwen2.5:0.5b`), and start the server (`ollama serve`).

**Rule:** after any engine change, `python manul.py test` must exit with code **0**.
Tip: Set `"ai_threshold": 0` (or `"model": null`) in `manul_engine_configuration.json` to force heuristics-only. Ensures deterministic unit tests without LLM calls.
Note: `python manul.py test` disables persistent controls cache by default for deterministic synthetic suites. `test_13_controls_cache.py` explicitly enables cache in a temporary `cache/run_<datetime>` folder and removes it after the test.

## Configuration (manul_engine_configuration.json)

JSON file at the **project root** (CWD when `manul` is invoked). All keys are optional.
Environment variables (`MANUL_*`) always override JSON values.

| Key | Default | Description |
| --- | --- | --- |
| `model` | `null` | Ollama model name. `null` = heuristics-only (no AI) |
| `headless` | `false` | Run browser headless |
| `browser` | `"chromium"` | Browser engine: `chromium` (default), `firefox`, or `webkit` |
| `browser_args` | `[]` | Extra launch flags passed to the browser (array of strings). Overridable via `MANUL_BROWSER_ARGS` (comma/space-separated) |
| `ai_threshold` | auto | Score threshold before LLM fallback. `null` = auto-derive from model size |
| `ai_always` | `false` | If `true`, always ask the LLM picker (bypasses heuristic short-circuits). Has no effect and is forced to `false` when `model` is `null` |
| `ai_policy` | `"prior"` | How to treat heuristic score in LLM picker: `"prior"` (hint) or `"strict"` (force max-score) |
| `controls_cache_enabled` | `true` | Enables persistent per-site controls cache (file-based, survives between runs) |
| `controls_cache_dir` | `"cache"` | Directory for cache files (relative to CWD or absolute) |
| `semantic_cache_enabled` | `true` | Enables in-session semantic cache (`learned_elements`). Remembers resolved elements within a single run (+200,000 score boost). Resets on each new `ManulEngine` instance |
| `log_name_maxlen` | `0` | If > 0, truncates element names in logs |
| `log_thought_maxlen` | `0` | If > 0, truncates LLM “thought” strings in logs |
| `timeout` | `5000` | Default action timeout (ms) |
| `nav_timeout` | `30000` | Navigation timeout (ms) |
| `tests_home` | `"tests"` | Default directory for new hunt files and `SCAN PAGE` / `manul scan` output |
| `auto_annotate` | `false` | If `true`, engine automatically inserts `# 📍 Auto-Nav: <name>` comments into `.hunt` files whenever the page URL changes during a run. Page names come from `pages.json`; falls back to full URL for unmapped pages. Overridable via `MANUL_AUTO_ANNOTATE` env var |
| `retries` | `0` | Number of times to retry a failed hunt file before marking it as failed (0 = no retries) |
| `screenshot` | `"on-fail"` | Screenshot capture mode: `"on-fail"` (default — failed steps only), `"always"` (every step), `"none"` (disabled) |
| `html_report` | `false` | Generate a self-contained HTML report after the run (`reports/manul_report.html`) |
Threshold auto-calculation by model size: `<1b → 500`, `1-4b → 750`, `5-9b → 1000`, `10-19b → 1500`, `20b+ → 2000`, `null → 0`.

Suggested config for mixed mode:

```json
{
  "model": "qwen2.5:0.5b",
  "browser": "chromium",
  "browser_args": [],
  "ai_policy": "prior",
  "controls_cache_enabled": true
}
```

Suggested config for heuristics-only (no Ollama needed):

```json
{
  "model": null,
  "browser": "chromium",
  "controls_cache_enabled": true
}
```

## Custom Controls

`manul_engine/controls.py` owns the Custom Controls registry:

* `_CUSTOM_CONTROLS` — module-level `dict[tuple[str, str], Callable]` keyed by `(page_name_lower, target_name_lower)`.
* `@custom_control(page, target)` — decorator; both sync and async handlers accepted.
* `get_custom_control(page_name, target_name) -> Callable | None` — case-insensitive lookup.
* `load_custom_controls(workspace_dir)` — auto-imports all `*.py` files (not starting with `_`) from `controls/` in the workspace root, executing each in an isolated `ModuleType` (same sandboxing as hooks). Called from `ManulEngine.__init__` via `load_custom_controls(str(Path.cwd()))`.

**Interception point in `core.py`:** the `else` branch of the step loop (action steps) checks `get_custom_control(lookup_page_name(page.url), first_quoted_token)` before any DOM snapshot. If a handler is found, it is called with `(page, mode, value)` and `_execute_step` is skipped entirely via `elif not await self._execute_step(...)` on the else path.

**Decorator rule for AI assistants — MANDATORY:**
When asked to automate a **complex or custom UI element** (virtual table, canvas-based widget, custom dropdown built with divs, WebGL control, multi-step datepicker, etc.), do NOT attempt to force complex `.hunt` step sequences or try to abuse standard heuristics. INSTEAD:
1. Write a Python function in `controls/<descriptive_name>.py` using the `@custom_control(page='...', target='...')` decorator.
2. Use the standard Playwright `page` object and its full API inside the function.
3. Write a single plain-English step in the `.hunt` file to trigger it (e.g. `Fill 'React Datepicker' with '2026-12-25'`).

Example — CORRECT:
```python
# controls/checkout.py
from manul_engine import custom_control

@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_datepicker(page, action_type: str, value: str | None) -> None:
    loc = page.locator(".react-datepicker__input-container input").first
    if action_type == "input" and value:
        await loc.click()
        await loc.fill(value)
```
```text
# tests/checkout.hunt
Fill 'React Datepicker' with '2026-12-25'
```

Example — WRONG (do not do this):
```text
# tests/checkout.hunt
2. Click the '.react-datepicker__input-container input' element
3. Fill the first input inside the calendar widget with '2026-12-25'
4. Click on day cell number 25 in the calendar grid
```

The page name in `@custom_control(page=...)` must match the value returned by `lookup_page_name(page.url)`, i.e. what is mapped in `pages.json` for the target URL.

---

## Common pitfalls & Advanced Learnings

* **Global Lifecycle Hooks — mandatory rule:** When a user asks to set up a database, perform a global login, seed test data, obtain an auth token, or do any pre-suite or pre-group environment setup, you **MUST** generate a `manul_hooks.py` file using `@before_all` or `@before_group(tag=...)` from `manul_engine`. **Never** add setup steps to individual `.hunt` files — that couples UI flows to infrastructure, slows each run, and makes teardown unreliable. The only correct pattern:
  ```python
  # tests/manul_hooks.py
  from manul_engine import before_all, after_all, GlobalContext

  @before_all
  def setup(ctx: GlobalContext) -> None:
      ctx.variables["TOKEN"] = auth_service.get_token()

  @after_all
  def teardown(ctx: GlobalContext) -> None:
      auth_service.revoke_token(ctx.variables["TOKEN"])
  ```
  The token is then available as `{TOKEN}` in all `.hunt` files without any per-file declaration.

* **Native Select vs Custom Dropdowns:** Playwright's `select_option()` crashes on non-`<select>` tags. If `mode == "select"` but the element is a `div`/`span`, gracefully fallback to a standard `click()`.
* **Overlapped Elements:** Modern UIs use invisible overlays. The engine primarily uses Playwright with `force=True` plus retries/alternate candidates; JS helpers (`window.manulClick`, `window.manulType`) are mainly used for Shadow DOM elements.
* **Deep Text Verification:** Standard `document.body.innerText` does not see text inside Shadow DOMs or Input values. `_handle_verify` uses a JS collector (`VISIBLE_TEXT_JS`) plus fallback checks.
* **Form Auto-clearing:** Before typing into an input using `loc.type()`, always `await loc.fill("")` to prevent appending text to pre-filled placeholders (especially critical on Wikipedia and search bars).
* **Checkbox/Radio strictness:** Heuristics must ruthlessly penalize (-50_000) non-checkbox elements when the user specifically asks to "Check" or "Select the radio", to prevent clicking a nearby `<td>` that happens to share the target text.
* **SVG quirks:** `el.className` might not be a string. In `SNAPSHOT_JS`, safely extract it: `typeof el.className === 'string' ? el.className : el.getAttribute('class')`.
* **Table Extraction & Legacy HTML:** When extracting rows based on text, use the shared `wordMatch()` helper from `EXTRACT_DATA_JS` instead of ad‑hoc `.includes()` calls. It uses word-boundary matching for short tokens and falls back to substring matching for longer tokens to reduce partial hits (e.g., "Javascript" vs "Java"). For legacy forms without explicit `<label>` tags, inputs inside `<fieldset>` should inherit context from `<legend>`.
* **AI Rejection loop:** If LLM returns `{"id": null}`, add the current top candidates to a `failed_ids` set, scroll the page, and retry `_snapshot` to discover hidden elements.

## Resolution fallback chain

The engine uses normalised `0.0–1.0` float scoring in `DOMScorer` (see `scoring.py`). Final integer scores = weighted sum × `SCALE` (177,778). The *highest-signal* boosts (and the cutoffs used in `core.py`) are:

1. Semantic cache reuse: +1.0 cache × W_cache(2.0) → ~355k scaled (`core.py` short-circuits at score ≥ 200_000)
2. Blind/context reuse (same xpath as last step): +0.05 cache → ~17k scaled (`core.py` short-circuits at score ≥ 10_000)
3. Exact `data-qa` match: +1.0 text × W_text(0.45) → ~80k scaled (substring: +0.375 → ~30k)
4. Exact `html_id` match: +0.6 attr × W_attr(0.25) → ~26k scaled (target_field exact: higher via multi-channel)
5. Exact text/aria/placeholder match: +0.625 text → ~50k scaled; partial matches are smaller
6. Element-type alignment & dev naming conventions: +0.05–0.30 semantics depending on mode (checkbox/radio strictness: -0.50 penalty)
7. Penalties: disabled ×0.0 (zeroes entire score), hidden ×0.1
8. LLM fallback: used only when best score < `MANUL_AI_THRESHOLD` (unless AI is disabled via threshold ≤ 0)

## Element data shape

Each element dict returned by `SNAPSHOT_JS` contains:
`id, name, xpath, is_select, is_shadow, is_contenteditable, class_name, tag_name, input_type, data_qa, html_id, icon_classes, aria_label, placeholder, role, disabled, aria_disabled, name_attr, frame_index`.

* `frame_index` — integer index into `page.frames` (0 = main frame). `_frame_for(page, el)` uses this to route Playwright calls to the correct Frame. Stale indices fall back to main frame.
* `name_attr` — the HTML `name` attribute (e.g. `name="search"` on Wikipedia's Codex search input). Scoring treats it as a text signal: exact match +0.0375 text / ~3k scaled; substring +0.0125 / ~1k scaled. Always cast with `str(el.get("name_attr", ""))` before comparing.

* `name` includes section context: `"Section -> Element Name input text"`.
* For `<select>` elements, `name` embeds options: `"dropdown [Option A | Option B]"`.

## Memory & variables

* `self.memory` — dict of `{var_name: value}` populated by EXTRACT steps.
* `substitute_memory()` replaces `{var}` placeholders.
* `self.learned_elements` — semantic cache: `(mode, search_texts, target_field) → {name, tag}`.
* `self.last_xpath` — used for Contextual Reuse (if next step says "in that field").

## VS Code extension (`vscode-extension/`)

A companion extension that provides hunt file language support, Test Explorer integration, a config sidebar, cache browser, and an interactive debug runner.

**Key rules when editing extension code:**

* `constants.ts` — centralised shared constants module. All string literals for config filenames (`DEFAULT_CONFIG_FILENAME`), debug protocol markers (`PAUSE_MARKER`), and terminal names (`TERMINAL_NAME`, `DEBUG_TERMINAL_NAME`) live here. `getConfigFileName()` reads the `manulEngine.configFile` VS Code setting with a fallback to `DEFAULT_CONFIG_FILENAME`. **Every** TS file that references the config filename or terminal names must import from `constants.ts` — never hardcode these strings inline.
* `huntRunner.ts` — `runHunt()` spawns `manul` with `cwd` set to the **VS Code workspace folder root** (resolved via `vscode.workspace.getWorkspaceFolder()`), not `path.dirname(huntFile)`. This ensures `manul_engine_configuration.json` and relative `controls_cache_dir` paths are always resolved from the project root, matching CLI behaviour.
* `huntRunner.ts` — `findManulExecutable()` probes local venv folders in order: `.venv`, `venv`, `env`, `.env` (both `bin/manul` on Unix and `Scripts\manul.exe` on Windows) before falling back to user-level install paths and a login-shell lookup. When adding new candidate paths, keep this order and always guard Windows/macOS-only paths with `isWin` / `process.platform` checks.
* `huntRunner.ts` — `runHuntFileDebugPanel(manulExe, huntFile, onData, token?, breakLines?, onPause?)` spawns with `--workers 1` and optionally `--break-lines N,M,...`. **Never pass `--debug`** — `--debug` pauses before every step including step 1 (NAVIGATE), which hangs before the browser has loaded anything. Only `--break-lines` + the stdin/stdout protocol is used for the panel runner.
* **Debug protocol:** Python (`core.py`) detects it is not a TTY (piped stdout) and emits `\x00MANUL_DEBUG_PAUSE\x00{"step":"...","idx":N}\n` on stdout when pausing. The TS side line-buffers stdout, detects the marker, calls `onPause(step, idx)` and writes `"next\n"`, `"continue\n"`, or `"debug-stop\n"` to stdin. The `onPause` return type is `Promise<"next" | "continue" | "highlight" | "debug-stop" | "stop-test">`. Sending `"abort\n"` + killing the process after 500 ms implements **Stop Test**; `"debug-stop\n"` implements **Debug Stop** (run to end, no more pauses).
* **Break-step semantics:** `ManulEngine.__init__` accepts `break_steps: set[int] | None`. `_user_break_steps` stores the original user-defined set; `break_steps` is the mutable active set. When the user picks **Next Step**: `break_steps.add(idx + 1)`. When the user picks **Continue All**: `break_steps = set(_user_break_steps)` (resets to original gutter breakpoints). This ensures "Next" advances exactly one step and "Continue" runs to the next gutter breakpoint or end.
* `debugControlPanel.ts` — singleton `DebugControlPanel.getInstance(ctx)`. `showPause(step, idx)` uses `vscode.window.createQuickPick()` (low-level API, not `showQuickPick`) so the picker can be hidden programmatically. `ignoreFocusOut: true` keeps it visible while Playwright runs. `abort()` calls `_activeQp.hide()`, which triggers `onDidHide` → resolves the promise with `"next"` so Python's `stdin.readline()` always unblocks. `dispose()` also calls `hide()` and resets the singleton. `tryRaiseWindow(idx, stepText)` (Linux only): spawns `xdotool search --onlyvisible --class "Code" windowactivate` (X11 focus), falls back to `wmctrl -a "Visual Studio Code"`, then fires `notify-send -u normal -t 5000` (5-second system notification, disappears automatically — do NOT use `-u critical` which ignores `-t` on GNOME/KDE). The QuickPick has **5 items**: Next Step, Continue All, Highlight Element, **⏹ Debug Stop** (sends `"debug-stop"` — clears all breakpoints so the run completes without further pauses), **🛑 Stop Test** (sends `"abort"` + kills the process after 500 ms). `PauseChoice` type: `"next" | "continue" | "highlight" | "debug-stop" | "stop-test"`.
* `huntTestController.ts` — has a **Debug run profile** in addition to the normal run profile. It calls `runHuntFileDebugPanel` with `onPause: (step, idx) => panel.showPause(step, idx)` and runs sequentially (no concurrency). **Stop button wiring:** `token.onCancellationRequested(() => panel.abort())` — this is essential; without it the QuickPick stays open after Stop is pressed and Python hangs. The disposable is stored and `.dispose()`d after the loop. Debug profile also calls `workbench.view.testing.focus` (in addition to `workbench.panel.testResults.view.focus`) to show the Test Explorer tree with per-step spinning/pass/fail indicators.
* `configPanel.ts` — `doSave()` forces `ai_always: false` whenever `model` is empty/null (`modelVal !== '' && g('ai_always').checked`). Do not remove this guard — saving `ai_always: true` with no model would produce an invalid config that causes runtime errors. The `syncAiAlways()` function also disables and unchecks the `ai_always` checkbox in the UI when the model field is cleared.
* `configPanel.ts` — Two separate cache controls: `controls_cache_enabled` is labelled **"Persistent Controls Cache"** (file-based, per-site storage, survives between runs); `semantic_cache_enabled` is labelled **"Semantic Cache"** (in-session `learned_elements`, +200,000 score boost within a single run, resets when process ends). The `controls_cache_dir` field is labelled "controls_cache_dir". Both default to `true`. Do not merge these two settings.
* `configPanel.ts` — `auto_annotate` checkbox (default `false`): labelled **"Auto-Annotate Page Navigation"**. When enabled, the engine writes `# 📍 Auto-Nav: <name>` comments into `.hunt` files live whenever the URL changes. `doSave()` writes `auto_annotate: g('auto_annotate').checked`; `doLoad()` reads `g('auto_annotate').checked = !!config.auto_annotate`.
* Config panel reads/writes `manul_engine_configuration.json` at the workspace root using `_configPath()`. The config file name is resolved via `getConfigFileName()` from `constants.ts`, which reads the `manulEngine.configFile` VS Code setting.
* Ollama model discovery: the panel fetches `http://localhost:11434/api/tags` on open and populates a `<select>` dropdown with installed model names (replaced legacy `<datalist>` + `<input>` to fix rendering offset in Electron webview). First option is always `null (heuristics-only)`. The stored model is always preserved as an option even when Ollama is offline.
* Build: `cd vscode-extension && npm install && npm run compile`. Use `npx vsce package` to produce a `.vsix`. Press F5 in VS Code with the extension folder open to launch a dev Extension Host.

## Version Bump Checklist

When the version changes, **ALL** of the following files must be updated:

| File | What to change |
|------|----------------|
| `pyproject.toml` | `version = "X.Y.Z"` under `[project]` |
| `README.md` | `**Version:** X.Y.Z` in the footer |
| `README_DEV.md` | Title `# 😼 ManulEngine vX.Y.Z`, pyproject.toml ref, extension manifest ref, VS Code extension version ref, lifecycle/test suite lists, footer `**Version:** X.Y.Z` |
| `vscode-extension/package.json` | `"version": "X.Y.Z"` (uses 3-digit semver, e.g. `"0.0.84"`) |
| `vscode-extension/README.md` | Add `### X.Y.Z` release notes section above the previous entry |
| `.github/copilot-instructions.md` | Version in the repo layout section (this file) |