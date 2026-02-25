# Copilot Instructions — ManulEngine

## What is this project?

ManulEngine is a neuro-symbolic browser automation framework.
It drives Chromium via Playwright, scores DOM elements with 20+ heuristic rules,
and falls back to a local LLM (Ollama) when the heuristics are ambiguous.
Everything runs locally — no cloud APIs.

**Stack:** Python 3.11 · Playwright async · Ollama (qwen2.5:0.5b) · python-dotenv

## Repository layout

```
manul.py                   CLI entry point
engine/
  __init__.py              public API  — re-exports ManulEngine
  core.py                  ManulEngine class (LLM, resolution, run_mission)
  actions.py               _ActionsMixin (navigate, scroll, extract, verify, drag, _execute_step)
  prompts.py               .env config, thresholds, LLM prompt templates
  scoring.py               score_elements() — pure function, 20+ heuristic rules
  js_scripts.py            SNAPSHOT_JS (DOM collector), VISIBLE_TEXT_JS
  helpers.py               substitute_memory(), extract_quoted(), timing constants
  test/
    test_engine.py          60-trap Monster DOM unit test suite
tests/
  hunt_demoqa.py            integration: forms, checkboxes, radios, tables
  hunt_expandtesting.py     integration: login, inputs, dropdown
  hunt_mega.py              integration: all element types, drag-drop, shadow DOM
  hunt_rahul.py             integration: radios, autocomplete, hover
  hunt_wikipedia.py         integration: search, navigate, extract, verify
```

## How the engine works

1. **Snapshot** — JS injects into the page and collects all interactive elements with metadata (tag, text, ARIA, data-qa, xpath, type, disabled, checked, options).
2. **Exact-match pass** — quick filter by `name`, `aria-label`, `data-qa` substring.
3. **Heuristic scoring** — `score_elements()` ranks candidates. Key weights: semantic cache 20k, context memory 10k, data-qa 8k, ARIA 3.5k, text 3k, type bonuses, disabled -20k.
4. **LLM fallback** — if best score < threshold, ask the LLM to pick the element.
5. **Anti-phantom guard** — reject LLM picks that don't match search terms (input/select modes).
6. **Action** — type / click / select / hover / drag on the resolved locator.
7. **Self-healing** — on failure, blacklist the element, clear context, re-resolve (up to 3 retries).

## Interaction modes

Detected from step keywords:
- `input` — "type", "fill", "enter"
- `clickable` — "click", "double", "check", "uncheck"
- `select` — "select", "choose"
- `hover` — "hover"
- `drag` — "drag" + "drop"
- `locate` — fallback (highlight only)

## Code patterns to follow

- Import: `from engine import ManulEngine` (never `framework`)
- `scoring.py` is **stateless** — pure function, receives `learned_elements` and `last_xpath` as kwargs
- `actions.py` is a **mixin** (`_ActionsMixin`) inherited by `ManulEngine` in `core.py`
- `prompts.py` owns all `.env` settings and prompt strings
- Steps are numbered strings like `"1. CLICK 'Submit'"` — the engine parses them
- Optional steps contain "if exists" / "optional" **outside** the quoted target

## Running tests

```bash
# Activate venv
env\Scripts\activate          # Windows
source env/bin/activate       # Linux/Mac

# Unit tests (60 traps, no browser, no LLM)
python manul.py test

# Integration tests (needs Playwright browsers + running Ollama)
python manul.py               # all hunts
python manul.py hunt_demoqa.py # single hunt
python manul.py --headless     # headless mode
```

**Rule:** after any engine change, `python manul.py test` must stay **60/60**.

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `MANUL_MODEL` | `qwen2.5:0.5b` | Ollama model name |
| `MANUL_HEADLESS` | `False` | Run browser headless |
| `MANUL_AI_THRESHOLD` | auto | Score threshold before LLM fallback |
| `MANUL_TIMEOUT` | `5000` | Default action timeout (ms) |
| `MANUL_NAV_TIMEOUT` | `30000` | Navigation timeout (ms) |

Threshold auto-calculation by model size: `<1b → 500`, `1-4b → 750`, `5-9b → 1000`, `10-19b → 1500`, `20b+ → 2000`.

## Common pitfalls

- Never add `await` before `page.locator()`  — locators are sync, only actions are awaited.
- `SNAPSHOT_JS` traverses **shadow DOM** — don't duplicate that logic in Python.
- `score_elements()` must remain a standalone function (no `self`) for testability.
- The anti-phantom guard only applies to `input` and `select` modes — don't extend to `clickable`.
- Check/uncheck detection uses `"check" in lower` but `"uncheck" in lower` takes priority — order matters.
- Optional step guard requires the search term to match text/value/aria **exactly** (case-insensitive).
- `_do_drag` receives `source_id` — always find the source element by `source_id`, never assume `raw_els[0]`.
- `_handle_verify` must respect `is_negative` for `checked` state — return `not checked` when step says "is not checked".
- CLI `--headless` monkey-patch must target **both** `engine.core.ManulEngine` **and** `engine.ManulEngine` (the package re-export), because hunts import from the package level.

## Element data shape

Each element dict returned by `SNAPSHOT_JS` contains:

```
id, name, tag_name, input_type, xpath, role, disabled,
aria_label, data_qa, html_id, icon_classes, is_select,
is_shadow, checked, options, value, aria_disabled
```

- `name` includes section context: `"Section -> Element Name input text"`.
  The scoring strips `" input <type>"` suffix and splits on `" -> "` to get the core name.
- `is_shadow` = True means the element lives inside a shadow root — use `window.manulClick(id)` / `window.manulType(id, text)` instead of Playwright locators.

## Resolution fallback chain

```
Semantic cache (20k) → Context memory (10k) → data-qa (8k) → ARIA (3.5k)
  → Text match (3k) → Type bonuses → Word overlap → LLM fallback
```

Threshold gate: if `best_score >= threshold` → skip LLM entirely.
Above 20k → instant cache reuse. Above 10k → context reuse.

## Step format

Steps are numbered strings parsed by `run_mission()`:

```
"1. NAVIGATE to https://example.com"
"2. Fill 'Username' field with 'admin'"
"3. Click the 'Login' button"
"4. VERIFY that 'Welcome' is present."
"5. EXTRACT 'Product' into {product_name}"
"6. DONE."
```

Special keywords parsed by `run_mission()` directly (before `_execute_step`):
`NAVIGATE`, `WAIT`, `SCROLL`, `EXTRACT`, `VERIFY`, `DONE`.

Everything else goes through `_execute_step` (mode detection → resolve → action).

## Memory & variables

- `self.memory` — dict of `{var_name: value}` populated by EXTRACT steps.
- `substitute_memory()` replaces `{var}` placeholders in subsequent steps.
- `self.learned_elements` — semantic cache: `(mode, search_texts, target_field) → {name, tag}`.
- `self.last_xpath` — context memory for blind steps (no quoted target).

## Writing integration tests (hunt files)

```python
import asyncio
from engine import ManulEngine

async def main():
    manul = ManulEngine()
    return await manul.run_mission("""
        1. NAVIGATE to https://example.com
        2. Click the 'Submit' button
        3. VERIFY that 'Success' is present.
        4. DONE.
    """)

if __name__ == "__main__":
    asyncio.run(main())
```

- File must be named `tests/hunt_*.py` with an `async def main()` returning bool.
- If `main()` accepts `headless` parameter, the CLI injects it automatically.
- Otherwise the CLI monkey-patches `ManulEngine` to honour `--headless`.
