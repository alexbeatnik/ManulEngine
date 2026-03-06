# 😼 ManulEngine — The Mastermind

[![PyPI](https://img.shields.io/pypi/v/manul-engine?label=PyPI&logo=pypi)](https://pypi.org/project/manul-engine/)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/manul-engine.manul-engine?label=VS%20Code%20Marketplace&logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=manul-engine.manul-engine)

ManulEngine is a relentless hybrid (neuro-symbolic) framework for browser automation and E2E testing.

Forget brittle CSS/XPath locators that break on every UI update — write tests in plain English.
Stop paying for expensive cloud APIs — leverage local micro-LLMs via **Ollama**, entirely on your machine.

Manul combines the blazing speed of **Playwright**, powerful JavaScript DOM heuristics, and the reasoning of local neural networks. It is fast, private, and highly resilient to UI changes.

> The Manul goes hunting and never returns without its prey.

---

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is handled by ultra-fast JavaScript and Python heuristics. The AI steps in only when genuine ambiguity arises.

When the LLM picker is used, Manul passes the heuristic score as a **prior** (hint) by default — the model can override the ranking only with a clear, disqualifying reason.

### 🛡️ Unbreakable JS Fallbacks

Modern websites love to hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. Manul uses Playwright with `force=True` plus retries and self-healing; for Shadow DOM elements it falls back to direct JS helpers to keep execution moving.

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

---

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
@blueprint: smoke

1. NAVIGATE to https://demoqa.com/text-box
2. Fill 'Full Name' field with 'Ghost Manul'
3. Click the 'Submit' button
4. VERIFY that 'Ghost Manul' is present.
5. DONE.
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
manul "1. NAVIGATE to https://example.com  2. Click the 'More' link  3. DONE."

# Run multiple hunt files in parallel (4 concurrent browsers)
manul my_tests/ --workers 4

# Smart Page Scanner — scan a URL and generate a draft hunt file
manul scan https://example.com                    # outputs to tests/draft.hunt (tests_home)
manul scan https://example.com tests/my.hunt      # explicit output file
manul scan https://example.com --headless         # headless scan
```

### 3. Python API

```python
import asyncio
from manul_engine import ManulEngine

async def main():
    manul = ManulEngine(headless=True)
    await manul.run_mission("""
        1. NAVIGATE to https://demoqa.com/text-box
        2. Fill 'Full Name' field with 'Ghost Manul'
        3. Click the 'Submit' button
        4. VERIFY that 'Ghost Manul' is present.
        5. DONE.
    """)

asyncio.run(main())
```

---

## 📜 Hunt File Format

Hunt files are plain-text test scenarios with a `.hunt` extension.

### Headers (optional)

```text
@context: Strategic context passed to the LLM planner
@blueprint: short-tag
```

### Comments

Lines starting with `#` are ignored.

### System Keywords

| Keyword | Description |
|---|---|
| `NAVIGATE to [URL]` | Load a URL and wait for DOM settlement |
| `WAIT [seconds]` | Hard sleep |
| `PRESS ENTER` | Press Enter on the currently focused element (submit forms after filling a field) |
| `SCROLL DOWN` | Scroll the main page down one viewport |
| `EXTRACT [target] into {var}` | Extract text into a memory variable |
| `VERIFY that [target] is present` | Assert text/element is visible |
| `VERIFY that [target] is NOT present` | Assert absence |
| `VERIFY that [target] is DISABLED` | Assert element state |
| `VERIFY that [target] is checked` | Assert checkbox state |
| `SCAN PAGE` | Scan the current page for interactive elements and print a draft `.hunt` to the console |
| `SCAN PAGE into {filename}` | Same, and also write the draft to `{filename}` (default: `tests_home/draft.hunt`) |
| `DONE.` | End the mission |

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
  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "workers": 1
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
| `controls_cache_enabled` | `true` | Persistent per-site controls cache |
| `controls_cache_dir` | `"cache"` | Cache directory (relative to CWD or absolute) |
| `timeout` | `5000` | Default action timeout (ms) |
| `nav_timeout` | `30000` | Navigation timeout (ms) |
| `log_name_maxlen` | `0` | Truncate element names in logs (0 = no limit) |
| `log_thought_maxlen` | `0` | Truncate LLM thoughts in logs (0 = no limit) |
| `workers` | `1` | Number of hunt files to run concurrently (each gets its own browser) |
| `tests_home` | `"tests"` | Default directory for new hunt files and `SCAN PAGE` / `manul scan` output |

---

## 📋 Available Commands

| Category | Command Syntax |
|---|---|
| **Navigation** | `NAVIGATE to [URL]` |
| **Input** | `Fill [Field] with [Text]`, `Type [Text] into [Field]` |
| **Click** | `Click [Element]`, `DOUBLE CLICK [Element]` |
| **Selection** | `Select [Option] from [Dropdown]`, `Check [Checkbox]`, `Uncheck [Checkbox]` |
| **Mouse Action** | `HOVER over [Element]`, `Drag [Element] and drop it into [Target]` |
| **Data Extraction** | `EXTRACT [Target] into {variable_name}` |
| **Verification** | `VERIFY that [Text] is present/absent`, `VERIFY that [Element] is checked/disabled` |
| **Page Scanner** | `SCAN PAGE`, `SCAN PAGE into {filename}` |
| **Flow Control** | `WAIT [seconds]`, `PRESS ENTER`, `SCROLL DOWN` |
| **Finish** | `DONE.` |

> Append `if exists` or `optional` to any step (outside quoted text) to make it non-blocking,
> e.g. `Click 'Close Ad' if exists`

---

## 🐾 Battle-Tested

ManulEngine is verified against **1200+ synthetic DOM tests** covering:

- Shadow DOM, invisible overlays, zero-pixel honeypots
- Custom dropdowns, drag-and-drop, hover menus
- Legacy HTML (tables, fieldsets, unlabelled inputs)
- AI rejection & self-healing loops
- Persistent controls cache hit/miss cycles

---

**Version:** 0.0.7 · **Status:** Hunting...
