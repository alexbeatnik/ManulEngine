
---

# 😼 ManulEngine v0.0.8.2 — The Mastermind

ManulEngine is a relentless hybrid (neuro-symbolic) framework for browser automation and E2E testing.

Forget brittle CSS/XPath locators that break on every UI update—write tests in plain English.
Stop paying for expensive cloud APIs and waiting seconds for every click—leverage local micro-LLMs via Ollama.

Manul combines the blazing speed of Playwright, powerful JavaScript DOM heuristics, and the reasoning of local neural networks. It is fast, private, and highly resilient to UI changes.

> The Manul goes hunting and never returns without its prey.

---

## 📁 Project Structure

```text
ManulEngine/
├── manul.py                          Dev CLI entry point (intercepts `test` subcommand)
├── manul_engine_configuration.json   Project configuration (JSON)
├── pyproject.toml                    Build config — package: manul-engine 0.0.8.2
├── requirements.txt                  Python dependencies
├── manul_engine/                     Core automation engine package
│   ├── __init__.py                   Public API — exports ManulEngine
│   ├── cli.py                        Installed CLI entry point (`manul` command + `manul scan` subcommand)
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
│       └── test_15_facebook_final_boss.py
├── tests/                            Integration hunt tests (real websites)
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
    ├── package.json                  Extension manifest (v0.0.82)
    ├── src/
    │   ├── extension.ts              Activation, command registration
    │   ├── huntRunner.ts             Spawns manul CLI; cwd = workspace root
    │   ├── huntTestController.ts     VS Code Test Explorer integration
    │   ├── configPanel.ts            Webview sidebar: config editor + Ollama discovery
    │   ├── cacheTreeProvider.ts      Sidebar tree: controls cache browser
    │   ├── stepBuilderPanel.ts       Step Builder sidebar (incl. Scan Page button)
    │   └── debugControlPanel.ts      Singleton QuickPick overlay for interactive debug stepping
    └── syntaxes/hunt.tmLanguage.json Hunt file syntax grammar
```

---

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is handled by ultra-fast JavaScript and Python heuristics. The AI steps in only when genuine ambiguity arises.

When the LLM picker is used, Manul passes the heuristic `score` as a **prior** (hint) by default (`MANUL_AI_POLICY=prior`) — the model can override the ranking only with a clear, disqualifying reason.

### 🛡️ Unbreakable JS Fallbacks

Modern websites love to hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. Manul primarily uses Playwright interactions with `force=True` plus retries/self-healing; for Shadow DOM elements it falls back to direct JS helpers (`window.manulClick`, `window.manulType`) to keep execution moving.

### 🌑 Shadow DOM Awareness

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

  "log_name_maxlen": 0,
  "log_thought_maxlen": 0,
  "workers": 1,
  "tests_home": "tests"
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

## 🐾 Chaos Chamber Verified (1227+ Tests)

The engine is battle-tested with **1227+** synthetic DOM/unit tests covering the web's most annoying UI patterns.

* **Synthetic DOM packs:** scenario suites under `manul_engine/test/`.
* **Controls cache regression suite:** `manul_engine/test/test_13_controls_cache.py` (disk cache hit/miss with temporary run folder cleanup).
* **AI modes regression suite:** `manul_engine/test/test_12_ai_modes.py` (Always-AI, strict override, AI rejection).
* **QA Classics regression suite:** `manul_engine/test/test_14_qa_classics.py` (legacy HTML patterns, tables, fieldsets).
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

The `vscode-extension/` directory contains a companion VS Code extension (v0.0.7) that provides:

| Feature | Details |
| --- | --- |
| **Hunt language support** | Syntax highlighting, bracket matching, and comment toggling for `.hunt` files |
| **Test Explorer integration** | Hunt files appear in VS Code's native Test Explorer; **real-time** step-level pass/fail reporting while the hunt is running |
| **Config sidebar** | Webview panel to edit `manul_engine_configuration.json` visually; **Workers** combobox; **Add Default Prompts** button; live Ollama model discovery via `localhost:11434` |
| **Cache browser** | Tree-view sidebar showing the controls cache hierarchy (`site → page → controls.json`) |
| **Run commands** | `ManulEngine: Run Hunt File` (output panel) and `ManulEngine: Run Hunt File in Terminal` (raw CLI) |
| **Debug run profile** | Test Explorer exposes a **Debug** run profile alongside the normal one; places gutter breakpoints (red dots) in `.hunt` files, pauses at each with a floating QuickPick overlay — **⏭ Next Step** / **▶ Continue All**. The Test Explorer **Stop** button aborts the run cleanly (no hanging QuickPick). On Linux, a system notification appears via `notify-send` when execution pauses. |
| **Step Builder** | Sidebar buttons for every step type including **Debug / Pause** (inserts `DEBUG` step) |
| **Bounded concurrency** | Test Explorer respects `workers` config or `manulEngine.workers` VS Code setting (default: 1) |

### Extension behaviour notes

* **Working directory:** The extension spawns `manul` with `cwd` set to the **VS Code workspace folder root** (not the directory of the `.hunt` file). This ensures `manul_engine_configuration.json` and the cache directory are always resolved from the project root, matching what you get when running `manul` from the terminal.
* **Debug protocol:** `runHuntFileDebugPanel` spawns `manul` with `--break-lines` (never `--debug`) and piped stdio. Python emits `\x00MANUL_DEBUG_PAUSE\x00{"step":"...","idx":N}\n` when pausing; TS responds with `"next\n"` or `"continue\n"`. "Next Step" adds `idx+1` to active break-steps; "Continue All" resets to original gutter breakpoints.
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

**Version:** 0.0.8.2

**Codename:** The Mastermind

**Status:** Hunting...