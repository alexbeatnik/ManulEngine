
---

# 😼 ManulEngine v0.0.8.6 — The Mastermind

ManulEngine is a relentless hybrid (neuro-symbolic) framework for browser automation and E2E testing.

Forget brittle CSS/XPath locators that break on every UI update—write tests in plain English.
Stop paying for expensive cloud APIs and waiting seconds for every click—leverage local micro-LLMs via Ollama.

Manul combines the blazing speed of Playwright, powerful JavaScript DOM heuristics, and the reasoning of local neural networks. It is fast, private, and highly resilient to UI changes.

> The Manul goes hunting and never returns without its prey.

> **ManulEngine runs on a potato.**
> No GPU. No cloud APIs. No $0.02 per click.
> Just Playwright, heuristics, and optional tiny local models.

---

## 📁 Project Structure

```text
ManulEngine/
├── manul.py                          Dev CLI entry point (intercepts `test` subcommand)
├── manul_engine_configuration.json   Project configuration (JSON)
├── pyproject.toml                    Build config — package: manul-engine 0.0.8.6
├── requirements.txt                  Python dependencies
├── manul_engine/                     Core automation engine package
│   ├── __init__.py                   Public API — exports ManulEngine
│   ├── cli.py                        Installed CLI entry point (`manul` command + `manul scan` subcommand)
│   ├── hooks.py                      [SETUP] / [TEARDOWN] hook parser and executor
│   ├── controls.py                   Custom Controls registry (@custom_control, get_custom_control, load_custom_controls)
│   ├── _test_runner.py               Dev-only synthetic test runner (not in public CLI)
│   ├── prompts.py                    JSON config loader, thresholds, LLM prompts
│   ├── helpers.py                    Pure utility functions, env helpers, timing constants
│   ├── js_scripts.py                 All JavaScript injected into the browser (incl. SCAN_JS)
│   ├── scoring.py                    Heuristic element-scoring algorithm (20+ rules)
│   ├── scanner.py                    Smart Page Scanner: scan_page(), build_hunt(), scan_main()
│   ├── core.py                       ManulEngine class (LLM, resolution, mission runner)
│   ├── cache.py                      Persistent per-site controls cache mixin
│   ├── actions.py                    Action execution mixin (click, type, select, hover, drag, scan_page)
│   └── test/
│       ├── test_00_engine.py         Engine micro-suite (synthetic DOM via local HTML)
│       ├── test_01_ecommerce.py      Scenario pack: ecommerce
│       ├── ...
│       ├── test_12_ai_modes.py       Unit: Always-AI/strict/rejection
│       ├── test_13_controls_cache.py Unit: persistent controls cache
│       ├── test_14_qa_classics.py    Unit: legacy HTML patterns, tables, fieldsets
        ├── test_15_facebook_final_boss.py
        ├── test_16_hooks.py          Unit: [SETUP]/[TEARDOWN] hooks (no browser)
        ├── test_19_custom_controls.py Unit: Custom Controls registry + engine interception (19 assertions, no browser)
        └── test_20_variables.py      Unit: @var: static variable declaration + initial_vars interpolation (17 assertions, no browser)
├── controls/                         User-owned custom Python handlers (auto-loaded at engine startup)
│   └── demo_custom.py                Reference implementation: React Datepicker handler with month navigation
├── tests/                            Integration hunt tests (real websites)
│   ├── demo_controls.hunt            Demo: Custom Controls workflow (companion to controls/demo_custom.py)
│   ├── demoqa.hunt
│   ├── mega.hunt
│   ├── rahul.hunt
│   ├── saucedemo.hunt
│   └── wikipedia.hunt
├── prompts/                          LLM prompt templates for hunt file generation
│   ├── README.md                     Usage guide (Copilot, ChatGPT, Claude, Ollama)
│   ├── html_to_hunt.md               Prompt: HTML page → hunt steps
│   └── description_to_hunt.md        Prompt: plain-text description → hunt steps
└── vscode-extension/                 VS Code extension (language support + UI)
    ├── package.json                  Extension manifest (v0.0.86)
    ├── src/
    │   ├── extension.ts              Activation, command registration
    │   ├── huntRunner.ts             Spawns manul CLI; cwd = workspace root
    │   ├── huntTestController.ts     VS Code Test Explorer integration
    │   ├── configPanel.ts            Webview sidebar: config editor + Ollama discovery
    │   ├── cacheTreeProvider.ts      Sidebar tree: controls cache browser
    │   ├── stepBuilderPanel.ts       Step Builder sidebar (incl. Live Page Scanner UI + Scan Page button)
    │   └── debugControlPanel.ts      Singleton QuickPick overlay for interactive debug stepping
    └── syntaxes/hunt.tmLanguage.json Hunt file syntax grammar
```

---

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is handled by ultra-fast JavaScript and Python heuristics. The AI steps in only when genuine ambiguity arises.

When the LLM picker is used, Manul passes the heuristic `score` as a **prior** (hint) by default (`MANUL_AI_POLICY=prior`) — the model can override the ranking only with a clear, disqualifying reason.

### 🧹 [SETUP] / [TEARDOWN] Hooks and Inline `CALL PYTHON` Steps

Version 0.0.8.3 introduces a pre/post hook mechanism powered by `manul_engine/hooks.py`. Hooks allow arbitrary synchronous Python to run before and after the browser mission. Version 0.0.8.3 also extends this capability to **inline steps**: `CALL PYTHON <module>.<func>` can now appear as a regular numbered step anywhere in the main mission body.

**Execution lifecycle:**

```
[SETUP] block         → runs before browser launches
  browser mission     → numbered hunt steps (may include CALL PYTHON steps)
[TEARDOWN] block      → runs in finally{}, always after setup succeeds
```

**Architecture:** The main step executor in `core.py` (`run_mission()`) reuses `execute_hook_line()` from `hooks.py` directly — no duplicated module-resolution logic. The `hunt_dir` parameter is passed through `run_mission(hunt_dir=...)` so inline calls resolve modules relative to the `.hunt` file's directory, exactly as `[SETUP]`/`[TEARDOWN]` do. `cli.py` passes `hunt_dir` to `run_mission` alongside the mission text.

**Module resolution order** (per `CALL PYTHON` instruction — identical for hooks and inline steps):

1. Directory of the `.hunt` file — local project helpers.
2. `Path.cwd()` — project root.
3. Standard `importlib.import_module` — installed packages / PYTHONPATH.

**State isolation:** Modules found via steps 1 and 2 are executed with `spec.loader.exec_module(mod)` into a fresh `ModuleType` object that is **never inserted into `sys.modules`**. This rule applies equally to hook blocks and inline `CALL PYTHON` steps — no `sys.modules` pollution regardless of where in the file the call appears.

**Async rejection:** `asyncio.iscoroutinefunction()` is checked before invoking the callable. Async functions are explicitly rejected with a descriptive error message and a concrete workaround (`asyncio.run()` inside the helper). This applies to both hooks and inline calls.

**Error taxonomy and messages:**

| Error condition | User-facing message prefix |
|---|---|
| Unrecognised instruction | `"Unrecognised hook instruction: '...'"` |
| Missing `.` separator | `"requires '<module>.<function>'"` |
| Module not found | `"Module 'x' not found. Searched in: ..."` |
| Function not found | `"Could not find function 'f' in module 'x.py'. Available: [...]"` |
| Attribute not callable | `"'f' in 'x.py' is not callable (found <type>)"` |
| Async callable | `"'f' is async. Hook functions must be synchronous..."` |
| Function raises | `"'x.f()' raised ExcType: message"` |

**Key APIs in `hooks.py`:**

```python
extract_hook_blocks(raw_text)  → (setup_lines, teardown_lines, mission_body)
execute_hook_line(line, hunt_dir)  → HookResult(success, message, return_value, var_name)
run_hooks(lines, label, hunt_dir)  → bool
```

**`HookResult` fields:** `success: bool`, `message: str`, `return_value: str | None`, `var_name: str | None`. The last two fields are populated when the step used the `into {var}` / `to {var}` capture syntax (see *Dynamic Variables* below); they are `None` for plain `CALL PYTHON` steps.

**Dynamic Variables via `CALL PYTHON ... into {var}`:** Inline `CALL PYTHON` steps may optionally bind their return value to a mission variable:

```text
1. CALL PYTHON api_helpers.fetch_otp into {dynamic_otp}
2. Fill 'Security Code' with '{dynamic_otp}'
```

`execute_hook_line` captures the return value from `func()`, converts it to a string, and stores it in `HookResult.return_value`. `run_mission` then writes it to `self.memory[var_name]`, making it available for `{placeholder}` substitution in every subsequent step — exactly like `EXTRACT` or `@var:` variables. Both `into` and `to` are accepted as the keyword. Dynamic-variable unit tests live in `manul_engine/test/test_21_dynamic_vars.py`.

`parse_hunt_file()` in `cli.py` returns an **8-tuple** `(mission, context, blueprint, step_file_lines, setup_lines, teardown_lines, parsed_vars, tags)`. `_run_hunt_file()` calls `run_hooks` before and after the mission with the correct `finally` semantics, and passes `hunt_dir` to `run_mission()` so that inline `CALL PYTHON` steps in the mission body can resolve modules from the same search roots.

The full hook unit test suite (`41 tests, no browser`) lives in `manul_engine/test/test_16_hooks.py`.

### 📋 Static Variable Declaration (`@var:`)

Version 0.0.8.6 adds static test-data declaration at the top of `.hunt` files:

```text
@var: {user_email} = admin@example.com
@var: {password}   = secret123

1. Fill 'Email' with '{user_email}'
2. Fill 'Password' with '{password}'
```

**How it works:** `parse_hunt_file()` scans for `@var: {key} = value` header lines and returns them as `parsed_vars` (the 7th element of the 8-tuple). `_run_hunt_file()` passes `parsed_vars` to `run_mission(initial_vars=...)`, which pre-populates `self.memory` before the step loop starts. Both brace and bare-key forms are accepted (`@var: {key} = val` and `@var: key = val` are equivalent). Values are stripped of leading/trailing whitespace. Malformed `@var:` lines (no `=`) are silently skipped.

**Design rule:** When generating or suggesting `.hunt` test files, **never** hardcode test data (emails, passwords, usernames, search queries, IDs, etc.) directly into `Fill` or `Type` steps. Always declare them at the top via `@var:` and reference them via `{placeholder}`. This keeps test logic separate from test data.

Unit tests: `manul_engine/test/test_20_variables.py` (17 assertions, no browser).

### 🏷️ Arbitrary Tags (`@tags:`) and `--tags` CLI Filter

Version 0.0.8.6 adds a tagging system that lets users run subsets of `.hunt` files without changing directory layout or file names.

**Hunt file header:**
```text
@context: Login flow
@tags: smoke, auth, regression

1. NAVIGATE to https://example.com/login
2. DONE.
```

**CLI usage:**
```bash
manul tests/ --tags smoke               # run only files tagged 'smoke'
manul tests/ --tags smoke,critical      # OR logic — run files with either tag
```

**Intersection rule:** A file is included in the run if its `@tags:` list shares at least one tag with the `--tags` argument.  Files with no `@tags:` header are **always excluded** when `--tags` is active.

**How it works:** `parse_hunt_file()` now extracts `@tags:` into the **8th element** of the tuple (`tags: list[str]`).  The CLI also exposes `_read_tags(path)` — a fast header-only scanner that stops at the first numbered step — used to pre-filter files in `main()` without running the full parse twice.  Tag filtering prints a one-line summary (`🏷️ --tags '...': N skipped, M matched.`) before the run starts.

Unit tests: `manul_engine/test/test_22_tags.py` (20 assertions, no browser).

### 🎛️ Custom Controls & Page Object Model

Custom Controls provide a first-class escape hatch for UI elements that heuristics and AI cannot reliably target: React virtual tables, canvas widgets, multi-step date-pickers, drag-to-rank lists, etc.

**How it ties into `pages.json`:**
The page name key in the decorator must match the value returned by `lookup_page_name(page.url)` at runtime — i.e. whatever is mapped in `pages.json` for the current URL. This makes the routing completely declarative: update the page name in `pages.json` and all dependent custom controls follow.

**Decorator syntax:**

```python
# controls/checkout.py
from manul_engine import custom_control

@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_datepicker(page, action_type: str, value: str | None) -> None:
    """
    page        — live Playwright Page
    action_type — "input" | "clickable" | "select" | "hover" | "drag" | "locate"
    value       — for 'input' steps: the text to type; None for everything else
    """
    input_loc = page.locator(".react-datepicker__input-container input").first
    if action_type == "input" and value:
        await input_loc.click()
        await input_loc.fill(value)
```

Both sync and async handlers are accepted; the engine awaits async ones.

**Auto-loading:**
`load_custom_controls(workspace_dir)` is called from `ManulEngine.__init__` with `Path.cwd()`. It imports every `*.py` file (not starting with `_`) from `controls/` in an isolated `ModuleType` — same sandboxing pattern as `[SETUP]`/`[TEARDOWN]` hooks.

**Interception point:**
In `run_mission()`, the `else` branch (action steps) runs `get_custom_control(page_name, target)` before taking any DOM snapshot. If a handler is found, it is called with `(page, mode, value)` and `_execute_step` is bypassed entirely. If not found, the normal heuristic/AI pipeline runs.

**Module layout:**

```text
controls/              # user-owned; loaded by load_custom_controls() at startup
  __init__.py          # optional; not loaded (filenames starting with _ are skipped)
  checkout.py          # @custom_control(page="Checkout Page", target="...")
  search.py            # @custom_control(page="Search Results", target="...")
manul_engine/
  controls.py          # registry: _CUSTOM_CONTROLS, @custom_control, get_custom_control,
                       #           load_custom_controls
```

**Corresponding hunt file (no change needed for QA):**

```text
@context: Checkout smoke test

1. NAVIGATE to https://example.com/checkout
2. Fill 'React Datepicker' with '2026-12-25'
3. Click the 'Place Order' button
4. VERIFY that 'Order confirmed' is present.
5. DONE.
```

---

### 🛡️ Ironclad JS Fallbacks

Modern websites love to hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. Manul primarily uses Playwright interactions with `force=True` plus retries/self-healing; for Shadow DOM elements it falls back to direct JS helpers (`window.manulClick`, `window.manulType`) to keep execution moving.

### 🪝 Shadow DOM Awareness

The DOM snapshotter recursively inspects shadow roots and can interact with elements in the shadow tree.

### 👻 Smart Anti-Phantom Guard & AI Rejection

Strict protection against LLM hallucinations. If the model is unsure it can return `{"id": null}`; the engine treats that as a rejection and retries with self-healing.

### 🎛️ Adjustable AI Threshold (Paranoia Level)

Control how quickly Manul falls back to the local LLM via `manul_engine_configuration.json` or `MANUL_AI_THRESHOLD` env var:

* **Low (200–500):** Blazing speed. Manul trusts heuristics.
* **Default (auto):** Derived from model size (e.g., `qwen2.5:0.5b` → 500).
* **High (2,000+):** More AI involvement on ambiguous steps.

If `ai_threshold` is `null` (default) and a model is set, Manul auto-calculates from the model size:

| Model size | Auto threshold |
| --- | --- |
| `< 1b` | `500` |
| `1b – 4b` | `750` |
| `5b – 9b` | `1000` |
| `10b – 19b` | `1500` |
| `20b+` | `2000` |

You can always override auto-threshold by setting `"ai_threshold"` in `manul_engine_configuration.json` or via `MANUL_AI_THRESHOLD` env var.

### 📴 Heuristics-Only Mode (no Ollama needed)

Set `"model": null` in `manul_engine_configuration.json` (or omit the key entirely):

```json
{ "model": null }
```

This disables the LLM element-picker and planner completely (`threshold = 0`). No Ollama process needed. The engine relies entirely on deterministic heuristics — fastest, most reproducible mode.

---

## 💻 System Requirements

| | Minimum | Recommended |
|---|---|---|
| **CPU** | any | modern laptop |
| **RAM** | 4 GB | 8 GB |
| **GPU** | none | none |
| **Model** | — (heuristics-only) | `qwen2.5:0.5b` |

## 🛠️ Installation

### From source (dev mode)

```bash
git clone https://github.com/alexbeatnik/ManulEngine.git
cd ManulEngine
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install playwright
playwright install chromium
```

### From wheel (packaged)

```bash
pip install manul-engine
playwright install chromium
```

Optional — local LLM via Ollama:

```bash
pip install ollama          # Python client library
ollama pull qwen2.5:0.5b   # download model (requires Ollama app: https://ollama.com)
ollama serve
```

## ⚙️ Configuration (manul_engine_configuration.json)

Create `manul_engine_configuration.json` in your project root. All keys are optional.
Environment variables (`MANUL_*`) always override JSON values — useful for CI/CD.

```json
{
  "model": "qwen2.5:0.5b",
  "headless": false,
  "browser": "chromium",
  "browser_args": [],
  "timeout": 5000,
  "nav_timeout": 30000,

  "ai_always": false,       // forced to false when model is null
  "ai_policy": "prior",
  "ai_threshold": null,

  "controls_cache_enabled": true,
  "controls_cache_dir": "cache",
  "semantic_cache_enabled": true,

  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "workers": 1,
  "tests_home": "tests",
  "auto_annotate": false
}
```

> Set `"model": null` (or omit) → heuristics-only mode, no Ollama needed.

Cache layout:

```text
cache/
    example.com/
        root/
            controls.json
        text-box/
            controls.json
```

Relative `controls_cache_dir` is resolved against CWD (the directory where you invoke `manul`), not the package installation path.

Synthetic tests (`python manul.py test`) disable cache by default for deterministic, side-effect-free results.

---

## 🖥️ CLI Usage

```bash
# Installed CLI (after pip install manul-engine)
manul tests/                       # run all *.hunt files
manul tests/wikipedia.hunt         # single hunt
manul --headless tests/            # headless mode
manul --browser firefox tests/     # run in Firefox
manul tests/ --workers 4           # run 4 hunt files in parallel
manul .                            # all *.hunt in current directory

# Interactive debug mode (terminal) — pauses before every step, prompts ENTER
manul --debug tests/saucedemo.hunt

# Gutter breakpoint mode (VS Code extension debug runner)
manul --break-lines 5,10,15 tests/saucedemo.hunt

# Smart Page Scanner
manul scan https://example.com                  # scan → tests/draft.hunt (tests_home from config)
manul scan https://example.com tests/my.hunt    # explicit output file
manul scan https://example.com --headless       # headless scan
manul scan https://example.com --browser firefox

# Dev launcher (from repo root, no install needed)
python manul.py test               # run synthetic DOM laboratory tests
python manul.py tests/             # run integration hunts
python manul.py --headless tests/  # headless
```

---

## 🚀 Quick Start

Create a hunt file: `tests/mission.hunt`

```text
@context: Demo flow
@blueprint: smoke

1. NAVIGATE to https://demoqa.com/text-box
2. Fill 'Full Name' field with 'Ghost Manul'
3. Click the 'Submit' button
4. VERIFY that 'Ghost Manul' is present.
5. DONE.
```

Run it:

```bash
manul tests/mission.hunt
```

---

## 📜 Available Commands

| Category | Command Syntax |
| --- | --- |
| **Navigation** | `NAVIGATE to [URL]` |
| **Input** | `Fill [Field] with [Text]`, `Type [Text] into [Field]` |
| **Click** | `Click [Element]`, `DOUBLE CLICK [Element]` |
| **Selection** | `Select [Option] from [Dropdown]`, `Check [Checkbox]`, `Uncheck [Checkbox]` |
| **Mouse Action** | `HOVER over [Element]`, `Drag [Element] and drop it into [Target]` |
| **Data Extraction** | `EXTRACT [Target] into {variable_name}` |
| **Verification** | `VERIFY that [Text] is present/absent`, `VERIFY that [Element] is checked/disabled` |
| **Page Scanner** | `SCAN PAGE`, `SCAN PAGE into {filename}` |
| **Debug** | `DEBUG` / `PAUSE` — pause execution at that step (use with `--debug` or VS Code gutter breakpoints) |
| **Flow Control** | `WAIT [seconds]`, `PRESS ENTER`, `SCROLL DOWN` |
| **Finish** | `DONE.` |

*Note: You can append `if exists` or `optional` to the end of any step (outside quoted text) to make it non-blocking, e.g. `Click 'Close Ad' if exists`.*

---

## 🐾 Chaos Chamber Verified (1427+ Tests)

The engine is battle-tested with **1427+** synthetic DOM/unit tests covering the web's most annoying UI patterns.

* **Synthetic DOM packs:** scenario suites under `manul_engine/test/`.
* **Controls cache regression suite:** `manul_engine/test/test_13_controls_cache.py` (disk cache hit/miss with temporary run folder cleanup).
* **AI modes regression suite:** `manul_engine/test/test_12_ai_modes.py` (Always-AI, strict override, AI rejection).
* **QA Classics regression suite:** `manul_engine/test/test_14_qa_classics.py` (legacy HTML patterns, tables, fieldsets).
* **Custom Controls unit suite:** `manul_engine/test/test_19_custom_controls.py` (registry correctness + engine interception, 19 assertions, no browser).
* **Static Variables unit suite:** `manul_engine/test/test_20_variables.py` (parser correctness, `initial_vars` interpolation, 17 assertions, no browser).
* **Integration hunts:** Real-site E2E flows under `tests/*.hunt` (requires Playwright).

Run the synthetic suite:

```bash
# From repo root (dev mode)
python manul.py test

# Heuristics-only (no Ollama), deterministic:
# Set "model": null in manul_engine_configuration.json
python manul.py test
```

---

## 🤖 LLM Prompts for Hunt File Generation

The `prompts/` directory contains ready-to-use LLM prompt templates that let you generate complete `.hunt` test files automatically.

| File | Purpose |
|---|---|
| `prompts/html_to_hunt.md` | Paste HTML → get hunt steps |
| `prompts/description_to_hunt.md` | Describe a flow in plain text → get hunt steps |
| `prompts/README.md` | Full usage guide for all LLM clients |

### Usage options

**GitHub Copilot Chat (VS Code)**
- Attach `prompts/html_to_hunt.md` via the paperclip icon, paste HTML in the message.
- Or use `#file:prompts/html_to_hunt.md` reference inline in the chat.
- Or open a blank `.hunt` file, press `Ctrl+I`, and reference the prompt file.

**ChatGPT / Claude (web):** Copy the entire prompt file, replace the `<!-- PASTE ... HERE -->` placeholder, send.

**API (Python):** Use the prompt file content as the `system` message and your HTML/description as the `user` message.

**Ollama (local):** `cat prompts/html_to_hunt.md mypage.html | ollama run qwen2.5:7b`

---

## 🖱️ VS Code Extension

The `vscode-extension/` directory contains a companion VS Code extension (v0.0.86) that provides:

| Feature | Details |
| --- | --- |
| **Hunt language support** | Syntax highlighting, bracket matching, and comment toggling for `.hunt` files |
| **Test Explorer integration** | Hunt files appear in VS Code's native Test Explorer; **real-time** step-level pass/fail reporting while the hunt is running |
| **Config sidebar** | Webview panel to edit `manul_engine_configuration.json` visually; **Workers** combobox; **Add Default Prompts** button; live Ollama model discovery via `localhost:11434` |
| **Cache browser** | Tree-view sidebar showing the controls cache hierarchy (`site → page → controls.json`) |
| **Run commands** | `ManulEngine: Run Hunt File` (output panel) and `ManulEngine: Run Hunt File in Terminal` (raw CLI) |
| **Debug run profile** | Test Explorer exposes a **Debug** run profile alongside the normal one; places gutter breakpoints (red dots) in `.hunt` files, pauses at each with a floating QuickPick overlay — **⏭ Next Step** / **▶ Continue All**. The Test Explorer **Stop** button aborts the run cleanly (no hanging QuickPick). On Linux, a system notification appears via `notify-send` when execution pauses. |
| **Step Builder** | Sidebar buttons for every step type including **Debug / Pause** (inserts `DEBUG` step); **� Call Python → Var** (inserts `CALL PYTHON module.function into {variable_name}` and captures the return value as a mission variable); **�🔍 Live Page Scanner** — URL input + Run Scan button that invokes `manul scan <URL>` directly and opens the result in the editor |
| **Bounded concurrency** | Test Explorer respects `workers` config or `manulEngine.workers` VS Code setting (default: 1) |

### Extension behaviour notes

* **Working directory:** The extension spawns `manul` with `cwd` set to the **VS Code workspace folder root** (not the directory of the `.hunt` file). This ensures `manul_engine_configuration.json` and the cache directory are always resolved from the project root, matching what you get when running `manul` from the terminal.
* **Debug protocol:** `runHuntFileDebugPanel` spawns `manul` with `--break-lines` (never `--debug`) and piped stdio. Python emits `\x00MANUL_DEBUG_PAUSE\x00{"step":"...","idx":N}\n` when pausing; TS responds on stdin with one of: `"next\n"` (pause at idx+1), `"continue\n"` (restore original gutter breakpoints), `"debug-stop\n"` (clear all breakpoints, run to end), or `"abort\n"` (then kill the process after 500 ms). The QuickPick overlay exposes five actions: **⏭ Next Step**, **▶ Continue All**, **👁 Highlight Element**, **⏹ Debug Stop**, **🛑 Stop Test**.
* **Auto-annotate:** When `auto_annotate` is enabled (via the Config Panel or `MANUL_AUTO_ANNOTATE` env var), the engine inserts/overwrites `# 📍 Auto-Nav:` comments above any step that follows a URL change — not only explicit `NAVIGATE` steps. URL tracking happens in `run_mission()`: `url_before` is captured before each step's `try` block; after the step's `finally`, if `page.url != url_before` and there is a next step, `_auto_annotate_navigate(page, hunt_file, step_file_lines, i+1)` is called. NAVIGATE steps annotate above themselves as before.
* **`pages.json` format:** Nested two-level dict — `{ "site_root_url": { "Domain": "display name", "regex_or_exact_url": "Page Name", ... } }`. `lookup_page_name()` in `prompts.py` re-reads the file on every call, finds the longest-prefix matching site block, then tries exact URL → regex patterns → `"Domain"` fallback. Auto-generated placeholders are stored under `{ "Domain": "Auto: domain/path" }` for the detected site root. Unknown unmapped pages write back `"Auto: ..."` as the display name in the comment. Auto-population uses a safe **deep-merge**: existing site blocks and their user-defined page mappings are never overwritten — only new top-level site keys or new page keys within a previously-unseen site block are added.
* **`ai_always` guard:** The config panel automatically forces `ai_always` to `false` when no model is selected, preventing an invalid heuristics-only config from being saved with `ai_always: true`.
* **Ollama discovery:** On panel open the extension fetches `http://localhost:11434/api/tags` and populates a `<select>` with installed model names. If Ollama is not running the field accepts free-text input instead.

### Building the extension

```bash
cd vscode-extension
npm install
npm run compile      # tsc one-shot
npm run watch        # incremental (dev)
npx vsce package     # produce .vsix
```

Press **F5** in VS Code (with the extension folder open) to launch a dev Extension Host.

---

**Version:** 0.0.8.6

**Codename:** The Mastermind

**Status:** Hunting...