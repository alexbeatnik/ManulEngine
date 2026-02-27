
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
  actions.py               _ActionsMixin (navigate, scroll, extract, verify, drag, _execute_step)
  prompts.py               .env config, thresholds, LLM prompt templates (handles null-rejection)
  scoring.py               score_elements() — pure function, 20+ heuristic rules (text/attrs/type/context)
  js_scripts.py            SNAPSHOT_JS (DOM collector + JS fallbacks), VISIBLE_TEXT_JS
  helpers.py               substitute_memory(), extract_quoted(), timing constants
  test/
    test_engine.py          synthetic DOM micro-suite (local HTML via Playwright)
    test_01_ecommerce.py    synthetic DOM scenario pack
    ...
    test_10_mess.py         synthetic DOM scenario pack
    test_11_cyber.py        synthetic DOM scenario pack
    test_12_ai_modes.py     synthetic DOM unit: Always-AI/strict/rejection
    test_13_controls_cache.py synthetic DOM unit: persistent controls cache hit/miss
tests/
  hunt_demoqa.py            integration: forms, checkboxes, radios, tables
  hunt_expandtesting.py     integration: login, inputs, dynamic tables
  hunt_mega.py              integration: all element types, drag-drop, shadow DOM, custom dropdowns
  hunt_rahul.py             integration: radios, autocomplete, hover
  hunt_wikipedia.py         integration: search, navigate, extract, verify, shadow-dom inputs
  hunt_cyber.py             integration: 100-step devsecops and terminal simulation

```

## How the engine works

1. **Snapshot** — JS injects into the page and collects all interactive elements.
2. **Exact-match pass** — quick filter by `name`, `aria-label`, `data-qa` substring.
3. **Heuristic scoring** — `score_elements()` ranks candidates using many small-to-medium signals (exact text/aria/placeholder matches, `data_qa`/`html_id`, developer naming conventions, element-type alignment, context words, etc.). The biggest single boosts in the current implementation are semantic cache reuse (+20_000) and blind context reuse (+10_000).
4. **LLM fallback** — if best score < threshold, ask the LLM to pick the element.
5. **AI Rejection & Anti-phantom guard** — LLM can return `{"id": null}` if no plausible target is found. Engine handles `null` by blacklisting the current candidates and triggering self-healing.
6. **Action** — type / click / select / hover / drag. Non-shadow interactions primarily use Playwright with `force=True` plus retries; Shadow DOM interactions use a **JS fallback** (`window.manulClick`, `window.manulType`) to bypass elements that Playwright cannot target.
7. **Self-healing** — on failure or AI rejection, scroll down, blacklist bad IDs, and retry (up to 3 retries). Each element-resolution attempt may also scroll-and-retry internally.
8. **Persistent controls cache** — successful control resolutions can be saved per-site to disk and reused on later runs. Cached controls are reused only if a matching live candidate still exists in the current snapshot.

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

```python
import asyncio
from engine import ManulEngine

async def main(headless: bool = False) -> bool:
    manul = ManulEngine(headless=headless)

    mission = """
        1. NAVIGATE to https://example.com
        2. Click the 'Submit' button
        3. VERIFY that 'Success' is present.
        4. DONE.
    """
    
    return await manul.run_mission(mission, strategic_context="My example site")

if __name__ == "__main__":
    asyncio.run(main())

```

* File must be named `tests/hunt_*.py` with an `async def main()` returning `bool`.
* If `main()` accepts `headless` parameter, the CLI injects it automatically.
* Otherwise, the CLI monkey-patches `ManulEngine` to honour the `--headless` flag.

## Code patterns to follow

* Import: `from engine import ManulEngine` (never `framework`).
* `scoring.py` is **stateless** — pure function, receives `learned_elements` and `last_xpath` as kwargs.
* **Safety first in `scoring.py`:** Always cast fetched attributes using `str(el.get("...", ""))`. JavaScript can pass objects (like `SVGAnimatedString` for SVG icons) instead of strings, which will crash Python's `.lower()`.
* `actions.py` is a **mixin** (`_ActionsMixin`) inherited by `ManulEngine` in `core.py`.
* `prompts.py` owns all `.env` settings and prompt strings.

## Running tests

```bash
# Activate venv
env\Scripts\activate          # Windows
source env/bin/activate       # Linux/Mac

# Synthetic DOM laboratory tests (local HTML via Playwright; no real websites)
python manul.py test

# Integration tests (needs Playwright browsers; Ollama optional)
python manul.py               # run all hunt_*.py scripts
python manul.py hunt_demoqa.py # single hunt
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