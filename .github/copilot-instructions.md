
# Copilot Instructions — ManulEngine

## What is this project?

ManulEngine is a highly resilient, neuro-symbolic browser automation framework.
It drives Chromium via Playwright, scores DOM elements with 20+ heuristic rules,
and falls back to a local LLM (Ollama) when the heuristics are ambiguous.
It is designed to bypass modern web traps (Shadow DOM, invisible overlays, zero-pixel honeypots, custom dropdowns) entirely locally — no cloud APIs.

Current operating mode in this repo is typically **mixed**:
- Heuristics rank candidates first.
- LLM is called only when heuristics are not confident (best score < `MANUL_AI_THRESHOLD`).
- When LLM is used, heuristic `score` is treated as a *prior* (hint), not a hard constraint (`MANUL_AI_POLICY=prior`).

**Stack:** Python 3.11 · Playwright async · Ollama (qwen2.5:0.5b) · python-dotenv

## Repository layout

```text
manul.py                   CLI entry point
engine/
  __init__.py              public API — re-exports ManulEngine
  core.py                  ManulEngine class (LLM, resolution, run_mission, self-healing)
  cache.py                 _ControlsCacheMixin (persistent per-site controls cache)
  actions.py               _ActionsMixin (navigate, scroll, extract, verify, drag, _execute_step)
  prompts.py               .env config, thresholds, LLM prompt templates (handles null-rejection)
  scoring.py               score_elements() — pure function, 20+ heuristic rules (text/attrs/type/context)
  js_scripts.py            All JS injected into the browser: SNAPSHOT_JS, VISIBLE_TEXT_JS, EXTRACT_DATA_JS, DEEP_TEXT_JS, STATE_CHECK_JS
  helpers.py               substitute_memory(), extract_quoted(), env_bool(), timing constants
  test/
    test_engine.py          synthetic DOM micro-suite (local HTML via Playwright)
    test_01_ecommerce.py    synthetic DOM scenario pack
    ...
    test_10_mess.py         synthetic DOM scenario pack
    test_11_cyber.py        synthetic DOM scenario pack
    test_12_ai_modes.py     synthetic DOM unit: Always-AI/strict/rejection
    test_13_controls_cache.py synthetic DOM unit: persistent controls cache hit/miss
    test_14_qa_classics.py  synthetic DOM unit: legacy HTML patterns, tables, fieldsets
    test_15_facebook_final_boss.py synthetic DOM scenario pack: complex UI, dynamic states
tests/
  hunt_demoqa.hunt          integration: forms, checkboxes, radios, tables
  hunt_expandtesting.hunt   integration: login, inputs, dynamic tables
  hunt_mega.hunt            integration: all element types, drag-drop, shadow DOM, custom dropdowns
  hunt_rahul.hunt           integration: radios, autocomplete, hover
  hunt_wikipedia.hunt       integration: search, navigate, extract, verify, shadow-dom inputs

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
* `SCROLL DOWN` or `SCROLL DOWN inside the list`
* `EXTRACT [target] into {variable_name}`
* `VERIFY that [target] is present` / `is NOT present` / `is DISABLED` / `is checked`
* `DONE.`

Everything else goes through `_execute_step` (mode detection → resolve → action).
Optional steps contain "if exists" / "optional" **outside** the quoted target (e.g. `"Click 'Close Ad' if exists"`).

## Writing integration tests (hunt files)

Hunt files are plain-text test scenarios parsed directly by `run_mission()`. They provide a robust way to write integration tests without Python boilerplate.

### 1. File Naming & Location
* Must be placed in the `tests/` directory.
* Must use the `.hunt` extension (common convention: `hunt_*.hunt`).

### 2. Metadata Headers
Placed at the top of the file. Used by the engine for logging and LLM context.
* `@context: [description]` — Strategic context passed to the engine.
* `@blueprint: [tag_name]` — Short tag representing the test suite.

### 3. Comments
* Use `#` for comments. Comments are ignored during execution.

### 4. Step Formatting
* Each action must be a numbered, atomic instruction (e.g., `1. `, `2. `).
* Elements should be wrapped in single or double quotes for best heuristic matching (e.g., `'Submit'`, `"Password"`).

### 5. System Keywords (Exact Matches)
These bypass heuristics and are handled directly by the engine parser:
* `NAVIGATE to [url]` — Loads a URL and waits for DOM settlement.
* `WAIT [seconds]` — Hard sleep (e.g., `WAIT 2`).
* `SCROLL DOWN` / `SCROLL DOWN inside the list` / `SCROLL DOWN to the very bottom`
* `EXTRACT [target] into {variable_name}` — Extracts text data into memory.
* `VERIFY that [target] is present` (or `is NOT present`, `is DISABLED`, `is checked`)
* `DONE.` — Explicitly ends the mission.

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
* **Exact Text Matching:** Put target texts in quotes (`'Save'`) to yield a high heuristic score (+5000).
* **Verify After Actions:** Always use a `VERIFY` step after taking a significant action (e.g., login, form submit) before assuming the new page state.
* **Implicit Context:** The engine reuses context if you refer to previous elements implicitly, e.g., `Type "Password" into that field`.

## Code patterns to follow

* Import: `from engine import ManulEngine` (never `framework`).
* `scoring.py` is **stateless** — pure function, receives `learned_elements` and `last_xpath` as kwargs.
* **Safety first in `scoring.py`:** Always cast fetched attributes using `str(el.get("...", ""))`. JavaScript can pass objects (like `SVGAnimatedString` for SVG icons) instead of strings, which will crash Python's `.lower()`.
* `actions.py` is a **mixin** (`_ActionsMixin`) inherited by `ManulEngine` in `core.py`.
* `cache.py` is a **mixin** (`_ControlsCacheMixin`) inherited by `ManulEngine` in `core.py`. It owns all persistent per-site controls-cache logic.
* `ManulEngine` MRO: `class ManulEngine(_ControlsCacheMixin, _ActionsMixin)` in `core.py`.
* `prompts.py` owns all `.env` settings and prompt strings.
* `js_scripts.py` owns **all** JavaScript constants injected into the browser — no inline JS in Python files.
* `helpers.py` provides `env_bool(name, default)` for parsing boolean env vars; used by `prompts.py`.

## Running tests

```bash
# Activate venv
env\Scripts\activate          # Windows
source env/bin/activate       # Linux/Mac

# Synthetic DOM laboratory tests (local HTML via Playwright; no real websites)
python manul.py test

# Integration tests (needs Playwright browsers; Ollama optional)
python manul.py               # run all hunt_*.py scripts
python manul.py hunt_wikipedia.py # single hunt
python manul.py --headless     # headless mode


Ollama is optional, but required for:
- free-text tasks (AI planner)
- AI element-picker fallback when heuristics confidence is below `MANUL_AI_THRESHOLD`


```

**Rule:** after any engine change, `python manul.py test` must exit with code **0**.
Tip: Set `MANUL_AI_THRESHOLD=0` to force heuristics-only resolution. This ensures deterministic unit tests without making expensive/variable LLM calls.
Note: `python manul.py test` disables persistent controls cache by default for deterministic synthetic suites. `test_13_controls_cache.py` explicitly enables cache in a temporary `cache/run_<datetime>` folder and removes it after the test.

## Configuration (.env)

| Variable | Default | Description |
| --- | --- | --- |
| `MANUL_MODEL` | `qwen2.5:0.5b` | Ollama model name |
| `MANUL_HEADLESS` | `False` | Run browser headless |
| `MANUL_DOTENV_OVERRIDE` | `False` | If `True`, repo `.env` overrides process env vars (useful locally; CI/prod usually wants env to win) |
| `MANUL_AI_THRESHOLD` | auto | Score threshold before LLM fallback |
| `MANUL_AI_ALWAYS` | `False` | If `True`, always ask the LLM picker (bypasses heuristic short-circuits) |
| `MANUL_AI_POLICY` | `prior` | How to treat heuristic score in LLM picker: `prior` (hint) or `strict` (force max-score) |
| `MANUL_CONTROLS_CACHE_ENABLED` | `True` | Enables persistent per-site controls cache |
| `MANUL_CONTROLS_CACHE_DIR` | `cache` | Directory for persistent controls cache files |
| `MANUL_LOG_NAME_MAXLEN` | `0` | If > 0, truncates element names in logs (whitespace is compacted regardless) |
| `MANUL_LOG_THOUGHT_MAXLEN` | `0` | If > 0, truncates LLM "thought" strings in logs |
| `MANUL_TIMEOUT` | `5000` | Default action timeout (ms) |
| `MANUL_NAV_TIMEOUT` | `30000` | Navigation timeout (ms) |

Threshold auto-calculation by model size: `<1b → 500`, `1-4b → 750`, `5-9b → 1000`, `10-19b → 1500`, `20b+ → 2000`.

Suggested `.env` for mixed mode (the current default expectation):

```env
MANUL_AI_THRESHOLD=500
MANUL_AI_ALWAYS=False
MANUL_AI_POLICY=prior
MANUL_CONTROLS_CACHE_ENABLED=True
```

Dotenv precedence note:
- Default behavior is `MANUL_DOTENV_OVERRIDE=False` (process env wins).
- For local prompt-tuning where you want repo `.env` to win over stale shell env vars, set `MANUL_DOTENV_OVERRIDE=True`.

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

The engine does not use a single fixed “chain constant”; it sums many heuristic signals in [engine/scoring.py](../engine/scoring.py). The *highest-signal* boosts (and the cutoffs used in [engine/core.py](../engine/core.py)) are:

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