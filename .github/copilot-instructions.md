
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
pyproject.toml             Build config — package name: manul-engine, version: 0.0.8.2
manul_engine/
  __init__.py              public API — re-exports ManulEngine
  core.py                  ManulEngine class (LLM, resolution, run_mission, self-healing)
  cache.py                 _ControlsCacheMixin (persistent per-site controls cache)
  actions.py               _ActionsMixin (navigate, scroll, extract, verify, drag, _execute_step, scan_page)
  prompts.py               JSON config loader, thresholds, LLM prompt templates
  scoring.py               score_elements() — pure function, 20+ heuristic rules
  js_scripts.py            All JS injected into the browser (includes SCAN_JS)
  scanner.py               Smart Page Scanner — scan_page(), build_hunt(), scan_main()
  helpers.py               substitute_memory(), extract_quoted(), env_bool(), timing constants
  cli.py                   Public installed CLI entry point (manul command + manul scan subcommand)
  hooks.py                 [SETUP] / [TEARDOWN] hook parser and executor
  _test_runner.py          Dev-only synthetic test runner (not in public CLI)
  test/
    test_00_engine.py       synthetic DOM micro-suite (local HTML via Playwright)
    test_01_ecommerce.py    synthetic DOM scenario pack
    ...
    test_15_facebook_final_boss.py
    test_16_hooks.py        [SETUP]/[TEARDOWN] unit tests (41 assertions, no browser)
tests/
  demoqa.hunt             integration: forms, checkboxes, radios, tables
  expandtesting.hunt      integration: login, inputs, dynamic tables
  mega.hunt               integration: all element types, drag-drop, shadow DOM, custom dropdowns
  rahul.hunt              integration: radios, autocomplete, hover
  wikipedia.hunt          integration: search, navigate, extract, verify, shadow-dom inputs
vscode-extension/
  package.json              Extension manifest (v0.0.83)
  src:
    extension.ts            Activation, command registration
    huntRunner.ts           Spawns manul CLI; cwd resolved to workspace root
    huntTestController.ts   VS Code Test Explorer integration (step-level reporting)
    configPanel.ts          Webview sidebar: config editor + Ollama model discovery
    cacheTreeProvider.ts    Sidebar tree: controls cache browser
    stepBuilderPanel.ts     Sidebar webview: step-insertion buttons + new hunt file (incl. Scan Page)
    debugControlPanel.ts    Singleton QuickPick overlay for interactive debug stepping
  syntaxes/hunt.tmLanguage.json  Hunt file syntax grammar
```

## How the engine works

1. **Snapshot** — JS injects into the page and collects all interactive elements.
2. **Exact-match pass** — quick filter by `name`, `aria-label`, `data-qa` substring.
3. **Heuristic scoring** — `score_elements()` ranks candidates using many small-to-medium signals (exact text/aria/placeholder matches, `data_qa`/`html_id`, developer naming conventions, element-type alignment, context words, etc.). The biggest single boosts in the current implementation are semantic cache reuse (+20_000) and blind context reuse (+10_000).
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

Steps are numbered strings parsed by `run_mission()`. They must be atomic browser instructions.

```text
"1. NAVIGATE to https://example.com"
"2. Fill 'Username' field with 'admin'"
"3. Click the 'Login' button"
"4. Select 'English' from the 'Language' dropdown"
"5. VERIFY that 'Welcome' is present."
"6. EXTRACT the 'Product Price' into {price}"
"7. SCROLL DOWN"
"8. DONE."

```

**System Keywords** parsed directly by `run_mission()` (these skip heuristics):

* `NAVIGATE to [url]`
* `WAIT [seconds]`
* `PRESS ENTER`
* `SCROLL DOWN` or `SCROLL DOWN inside the list`
* `EXTRACT [target] into {variable_name}`
* `VERIFY that [target] is present` / `is NOT present` / `is DISABLED` / `is checked`
* `SCAN PAGE` — scans the current page for interactive elements and prints a draft `.hunt` to the console.
* `SCAN PAGE into {filename}` — same, but also writes the draft to `{filename}`. Default output dir is `tests_home` from config.
* `DEBUG` / `PAUSE` — pauses execution at that step. In interactive terminal mode (`--debug`), draws a dashed red border around the resolved element and prompts the user; when run via VS Code extension, emits the debug pause protocol marker (see below).
* `DONE.`

Everything else goes through `_execute_step` (mode detection → resolve → action).
Optional steps contain "if exists" / "optional" **outside** the quoted target (e.g. `"Click 'Close Ad' if exists"`).

## Writing integration tests (hunt files)

Hunt files are plain-text test scenarios that the CLI parses via `parse_hunt_file()` (to extract `@context` / `@blueprint` and strip full-line `#` comments) before passing the mission body into `run_mission()`, which then parses and executes the numbered steps. They provide a robust way to write integration tests without Python boilerplate.

### 1. File Naming & Location
* For this repo's default auto-discovery (`python manul.py` with no target), hunt files are discovered under the `tests/` directory.
* You can also pass a specific `.hunt` file or a directory path to `manul.py` to run hunts from any location.
* Must use the `.hunt` extension. The filename can be anything — no prefix is required or enforced.

### 2. Metadata Headers
Placed at the top of the file. Used by the engine for logging and LLM context.
* `@context: [description]` — Strategic context passed to the engine.
* `@blueprint: [tag_name]` — Short tag representing the test suite.

### 3. Comments
* Use `#` at the beginning of a line for comments. Any line whose trimmed text starts with `#` is ignored during execution; `#` appearing after a step on the same line is treated as part of the step text, not a comment.

### 4. Step Formatting
* For deterministic hunts and when running without Ollama, each action should be a numbered, atomic instruction (e.g., `1. `, `2. `). Free-form, non-numbered text is also accepted and will be routed through the LLM planner, but may produce less deterministic runs.
* Elements should be wrapped in single or double quotes for best heuristic matching (e.g., `'Submit'`, `"Password"`).

### 5. System Keywords (parser-detected)
These keywords are detected via word-boundary regex, bypass heuristics, and are handled directly by the engine parser:
* `NAVIGATE to [url]` — Loads a URL and waits for DOM settlement.
* `WAIT [seconds]` — Hard sleep (e.g., `WAIT 2`).
* `PRESS ENTER` — Presses the Enter key on the currently focused element (useful to submit forms after filling a field).
* `SCROLL DOWN` — Scrolls the main page down by one viewport height. `SCROLL DOWN inside the list` — scrolls the first dropdown-style scroll container (e.g., `#dropdown` or any element whose class name contains `dropdown`) all the way to the bottom (by setting `scrollTop = scrollHeight`). Phrases like `SCROLL DOWN to the very bottom` are accepted but currently behave the same as a single `SCROLL DOWN` on the main page (they do not auto-scroll the page all the way to the bottom).
* `EXTRACT [target] into {variable_name}` — Extracts text data into memory.
* `VERIFY that [target] is present` (or `is NOT present`, `is DISABLED`, `is checked`)
* `SCAN PAGE` — Runs `SCAN_JS` on the current page, maps results to hunt steps, prints a draft to console.
* `SCAN PAGE into {filename}` — Same, but also writes the draft to `{filename}`. Output defaults to `{tests_home}/draft.hunt` (reads `tests_home` from `manul_engine_configuration.json`, defaults to `tests/`).
* `DONE.` — Explicitly ends the mission.
* `[SETUP]` / `[END SETUP]` — Block wrapping `CALL PYTHON <module>.<function>` lines. Runs **before** the browser launches. If any line fails, the mission is skipped and teardown is not called.
* `[TEARDOWN]` / `[END TEARDOWN]` — Cleanup block. Runs in a `finally` block **after** the mission (pass or fail). Only executed if `[SETUP]` succeeded. Failure is logged but does not override the mission result.
* Inside hook blocks, each non-blank non-comment line must have the form: `CALL PYTHON <module>.<function>`. The module is resolved in this order: the `.hunt` file's directory → `CWD` → standard `importlib.import_module`. Target functions must be **synchronous**.

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

### 8. Best Practices
* **Specify Element Type:** Include words like `button`, `field`, `link`, `dropdown`, `checkbox`, `radio` outside quotes. This acts as a strong heuristic signal.
* **Exact Text Matching:** Put target texts in quotes (`'Save'`) to yield a high heuristic score.
* **Verify After Actions:** Always use a `VERIFY` step after taking a significant action (e.g., login, form submit) before assuming the new page state.
* **Implicit Context:** The engine reuses context if you refer to previous elements implicitly, e.g., `Type "Password" into that field`.

### 9. Python Hooks (`[SETUP]` / `[TEARDOWN]`)
Hook blocks run synchronous Python functions **outside the browser** — the primary use case is injecting database state or calling an API before the mission starts.
* When generating `.hunt` tests that require specific initial data (users, records, session tokens), **ALWAYS** use `[SETUP]` with `CALL PYTHON`. Never use brittle UI steps (e.g., "Click Create User") as test preconditions.
* `[TEARDOWN]` cleanup runs whether the mission passed or failed. Use it to delete test records and reset state.
* Target functions **must be synchronous**. Async callables are explicitly rejected with a descriptive error.
* Module resolution order: hunt file's directory → `CWD` → `sys.path`. Modules from the first two scopes are executed in isolation — never inserted into `sys.modules` — preventing cross-test contamination.

## Code patterns to follow

* Import: `from manul_engine import ManulEngine` (never `engine` or `framework`).
* `scoring.py` is **stateless** — pure function, receives `learned_elements` and `last_xpath` as kwargs.
* **Safety first in `scoring.py`:** Always cast fetched attributes using `str(el.get("...", ""))`. JavaScript can pass objects (like `SVGAnimatedString` for SVG icons) instead of strings, which will crash Python's `.lower()`.
* `actions.py` is a **mixin** (`_ActionsMixin`) inherited by `ManulEngine` in `core.py`.
* `cache.py` is a **mixin** (`_ControlsCacheMixin`) inherited by `ManulEngine` in `core.py`. It owns all persistent per-site controls-cache logic.
* `ManulEngine` MRO: `class ManulEngine(_ControlsCacheMixin, _ActionsMixin)` in `core.py`.
* `prompts.py` loads config from `manul_engine_configuration.json` (CWD first, then package root fallback). No dotenv dependency.
* `js_scripts.py` owns **all** JavaScript constants injected into the browser — no inline JS in Python files. This includes `SCAN_JS` (Smart Page Scanner).
* `scanner.py` owns the standalone scan logic: `SCAN_JS` is imported from `js_scripts.py`; `build_hunt()` maps raw element dicts to hunt steps; `scan_page()` is the async Playwright runner; `scan_main()` is the async CLI entry called by `cli.py`. `_default_output()` reads `tests_home` from the config to derive the default output path.
* `helpers.py` provides `env_bool(name, default)` for parsing boolean env vars; used by `prompts.py`.
* **Null model = heuristics-only:** When `model` is `None`, `_llm_json()` returns `None` immediately. `get_threshold(None)` returns `0`. No Ollama calls are made.
* **`scan_main` must be `async`** — it is called with `await` from inside `cli.main()` which runs under `asyncio.run()`. Never use `asyncio.run()` inside `scan_main`.
* **Debug mode:** `ManulEngine(debug_mode=True, break_steps={N,...})`. `debug_mode=True` (from `--debug`) highlights the resolved element and pauses before every step using `input()` in TTY or Playwright's `page.pause()`. `break_steps` (from `--break-lines`) pauses only at listed step indices using the stdout/stdin panel protocol when stdout is not a TTY. The two are mutually exclusive in practice — the extension only ever sets `break_steps` via `--break-lines`.
* **Element highlight in debug mode:** Before every action when `debug_mode=True`, the engine injects JS to draw a dashed red border on the target element for 500 ms so the tester can visually confirm which element was picked.
* `hooks.py` owns all `[SETUP]` / `[TEARDOWN]` parsing (`extract_hook_blocks()`) and execution (`execute_hook_line()`, `run_hooks()`). `parse_hunt_file()` in `cli.py` returns a **6-tuple** `(mission, context, blueprint, step_file_lines, setup_lines, teardown_lines)`. Modules resolved via `importlib.util.spec_from_file_location` + `spec.loader.exec_module(fresh_ModuleType)` — **never** inserted into `sys.modules`. Target functions must be synchronous; async callables are rejected before invocation.

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

# Interactive debug mode (terminal) — pauses before every step, prompts ENTER
manul --debug tests/saucedemo.hunt

# Gutter breakpoint mode (used by VS Code extension debug runner)
# Pause at steps whose file line numbers match; emits stdin/stdout debug protocol
manul --break-lines 5,10,15 tests/saucedemo.hunt

# Smart Page Scanner
manul scan https://example.com                   # scan → tests/draft.hunt (tests_home default)
manul scan https://example.com tests/my.hunt     # scan → explicit output file
manul scan https://example.com --headless        # headless scan
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
| `controls_cache_enabled` | `true` | Enables persistent per-site controls cache |
| `controls_cache_dir` | `"cache"` | Directory for cache files (relative to CWD or absolute) |
| `log_name_maxlen` | `0` | If > 0, truncates element names in logs |
| `log_thought_maxlen` | `0` | If > 0, truncates LLM “thought” strings in logs |
| `timeout` | `5000` | Default action timeout (ms) |
| `nav_timeout` | `30000` | Navigation timeout (ms) |
| `tests_home` | `"tests"` | Default directory for new hunt files and `SCAN PAGE` / `manul scan` output |
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

## Common pitfalls & Advanced Learnings

* **Native Select vs Custom Dropdowns:** Playwright's `select_option()` crashes on non-`<select>` tags. If `mode == "select"` but the element is a `div`/`span`, gracefully fallback to a standard `click()`.
* **Overlapped Elements:** Modern UIs use invisible overlays. The engine primarily uses Playwright with `force=True` plus retries/alternate candidates; JS helpers (`window.manulClick`, `window.manulType`) are mainly used for Shadow DOM elements.
* **Deep Text Verification:** Standard `document.body.innerText` does not see text inside Shadow DOMs or Input values. `_handle_verify` uses a JS collector (`VISIBLE_TEXT_JS`) plus fallback checks.
* **Form Auto-clearing:** Before typing into an input using `loc.type()`, always `await loc.fill("")` to prevent appending text to pre-filled placeholders (especially critical on Wikipedia and search bars).
* **Checkbox/Radio strictness:** Heuristics must ruthlessly penalize (-50_000) non-checkbox elements when the user specifically asks to "Check" or "Select the radio", to prevent clicking a nearby `<td>` that happens to share the target text.
* **SVG quirks:** `el.className` might not be a string. In `SNAPSHOT_JS`, safely extract it: `typeof el.className === 'string' ? el.className : el.getAttribute('class')`.
* **Table Extraction & Legacy HTML:** When extracting rows based on text, use the shared `wordMatch()` helper from `EXTRACT_DATA_JS` instead of ad‑hoc `.includes()` calls. It uses word-boundary matching for short tokens and falls back to substring matching for longer tokens to reduce partial hits (e.g., "Javascript" vs "Java"). For legacy forms without explicit `<label>` tags, inputs inside `<fieldset>` should inherit context from `<legend>`.
* **AI Rejection loop:** If LLM returns `{"id": null}`, add the current top candidates to a `failed_ids` set, scroll the page, and retry `_snapshot` to discover hidden elements.

## Resolution fallback chain

The engine does not use a single fixed “chain constant”; it sums many heuristic signals in [engine/scoring.py](../manul_engine/scoring.py). The *highest-signal* boosts (and the cutoffs used in [manul_engine/core.py](../manul_engine/core.py)) are:

1. Semantic cache reuse: +20_000 (and `core.py` short-circuits at score ≥ 20_000)
2. Blind/context reuse (same xpath as last step): +10_000 (and `core.py` short-circuits at score ≥ 10_000)
3. Exact `data_qa` match: +10_000 (substring: +3_000)
4. Exact `html_id` match to target/search text: +10_000 (exact to `target_field` can be +15_000)
5. Exact text/aria/placeholder/name match: typically +5_000 (partial matches are smaller)
6. Element-type alignment & dev naming conventions: usually +300 … +15_000 depending on mode (e.g., checkbox/radio strictness)
7. LLM fallback: used only when best score < `MANUL_AI_THRESHOLD` (unless AI is disabled via threshold ≤ 0)

## Element data shape

Each element dict returned by `SNAPSHOT_JS` contains:
`id, name, xpath, is_select, is_shadow, is_contenteditable, class_name, tag_name, input_type, data_qa, html_id, icon_classes, aria_label, placeholder, role, disabled, aria_disabled`.

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

* `huntRunner.ts` — `runHunt()` spawns `manul` with `cwd` set to the **VS Code workspace folder root** (resolved via `vscode.workspace.getWorkspaceFolder()`), not `path.dirname(huntFile)`. This ensures `manul_engine_configuration.json` and relative `controls_cache_dir` paths are always resolved from the project root, matching CLI behaviour.
* `huntRunner.ts` — `findManulExecutable()` probes local venv folders in order: `.venv`, `venv`, `env`, `.env` (both `bin/manul` on Unix and `Scripts\manul.exe` on Windows) before falling back to user-level install paths and a login-shell lookup. When adding new candidate paths, keep this order and always guard Windows/macOS-only paths with `isWin` / `process.platform` checks.
* `huntRunner.ts` — `runHuntFileDebugPanel(manulExe, huntFile, onData, token?, breakLines?, onPause?)` spawns with `--workers 1` and optionally `--break-lines N,M,...`. **Never pass `--debug`** — `--debug` pauses before every step including step 1 (NAVIGATE), which hangs before the browser has loaded anything. Only `--break-lines` + the stdin/stdout protocol is used for the panel runner.
* **Debug protocol:** Python (`core.py`) detects it is not a TTY (piped stdout) and emits `\x00MANUL_DEBUG_PAUSE\x00{"step":"...","idx":N}\n` on stdout when pausing. The TS side line-buffers stdout, detects the marker, calls `onPause(step, idx)` and writes `"next\n"` or `"continue\n"` to stdin.
* **Break-step semantics:** `ManulEngine.__init__` accepts `break_steps: set[int] | None`. `_user_break_steps` stores the original user-defined set; `break_steps` is the mutable active set. When the user picks **Next Step**: `break_steps.add(idx + 1)`. When the user picks **Continue All**: `break_steps = set(_user_break_steps)` (resets to original gutter breakpoints). This ensures "Next" advances exactly one step and "Continue" runs to the next gutter breakpoint or end.
* `debugControlPanel.ts` — singleton `DebugControlPanel.getInstance(ctx)`. `showPause(step, idx)` uses `vscode.window.createQuickPick()` (low-level API, not `showQuickPick`) so the picker can be hidden programmatically. `ignoreFocusOut: true` keeps it visible while Playwright runs. `abort()` calls `_activeQp.hide()`, which triggers `onDidHide` → resolves the promise with `"next"` so Python's `stdin.readline()` always unblocks. `dispose()` also calls `hide()` and resets the singleton. `tryRaiseWindow(idx, stepText)` (Linux only): spawns `xdotool search --onlyvisible --class "Code" windowactivate` (X11 focus), falls back to `wmctrl -a "Visual Studio Code"`, then fires `notify-send -u normal -t 5000` (5-second system notification, disappears automatically — do NOT use `-u critical` which ignores `-t` on GNOME/KDE).
* `huntTestController.ts` — has a **Debug run profile** in addition to the normal run profile. It calls `runHuntFileDebugPanel` with `onPause: (step, idx) => panel.showPause(step, idx)` and runs sequentially (no concurrency). **Stop button wiring:** `token.onCancellationRequested(() => panel.abort())` — this is essential; without it the QuickPick stays open after Stop is pressed and Python hangs. The disposable is stored and `.dispose()`d after the loop. Debug profile also calls `workbench.view.testing.focus` (in addition to `workbench.panel.testResults.view.focus`) to show the Test Explorer tree with per-step spinning/pass/fail indicators.
* `configPanel.ts` — `doSave()` forces `ai_always: false` whenever `model` is empty/null (`modelVal !== '' && g('ai_always').checked`). Do not remove this guard — saving `ai_always: true` with no model would produce an invalid config that causes runtime errors. The `syncAiAlways()` function also disables and unchecks the `ai_always` checkbox in the UI when the model field is cleared.
* Config panel reads/writes `manul_engine_configuration.json` at the workspace root using `_configPath()`. The config file name is user-configurable via the `manulEngine.configFile` VS Code setting.
* Ollama model discovery: the panel fetches `http://localhost:11434/api/tags` on open and populates a `<select>` dropdown with installed model names (replaced legacy `<datalist>` + `<input>` to fix rendering offset in Electron webview). First option is always `null (heuristics-only)`. The stored model is always preserved as an option even when Ollama is offline.
* Build: `cd vscode-extension && npm install && npm run compile`. Use `npx vsce package` to produce a `.vsix`. Press F5 in VS Code with the extension folder open to launch a dev Extension Host.