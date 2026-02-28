
---

# 😼 ManulEngine v0.04 — The Mastermind

ManulEngine is a relentless hybrid (neuro-symbolic) framework for browser automation and E2E testing.

Forget brittle CSS/XPath locators that break on every UI update—write tests in plain English.
Stop paying for expensive cloud APIs and waiting seconds for every click—leverage local micro-LLMs via Ollama.

Manul combines the blazing speed of Playwright, powerful JavaScript DOM heuristics, and the reasoning of local neural networks. It is fast, private, and highly resilient to UI changes.

> The Manul goes hunting and never returns without its prey.

---

## 📁 Project Structure

```text
browser-manul/
├── manul.py              CLI runner (test files, inline prompts, unit tests)
├── requirements.txt      Python dependencies
├── .env                  Optional runtime configuration (model, threshold, headless)
├── .env.example          Example configuration template
├── engine/               Core automation engine package
│   ├── __init__.py       Public API — exports ManulEngine
│   ├── prompts.py        Configuration, thresholds, LLM prompts
│   ├── helpers.py        Pure utility functions, env helpers, timing constants
│   ├── js_scripts.py     All JavaScript injected into the browser (DOM snapshot, JS fallbacks, extraction, verification)
│   ├── scoring.py        Heuristic element-scoring algorithm (20+ rules)
│   ├── core.py           ManulEngine class (LLM, resolution, mission runner)
│   ├── cache.py          Persistent per-site controls cache mixin (_ControlsCacheMixin)
│   ├── actions.py        Action execution mixin (click, type, select, hover, drag)
│   └── test/
│       ├── test_engine.py       Engine micro-suite (synthetic DOM via local HTML; uses Playwright)
│       ├── test_01_ecommerce.py Scenario pack: ecommerce (synthetic DOM)
│       ├── test_02_social.py    Scenario pack: social (synthetic DOM)
│       ├── ...                  More packs (see engine/test/)
│       ├── test_10_mess.py      Scenario pack: misc edge-cases (synthetic DOM)
│       ├── test_11_cyber.py     Scenario pack: cyber/terminal (synthetic DOM)
│       ├── test_12_ai_modes.py  Unit test: Always-AI/strict/rejection
│       ├── test_13_controls_cache.py Unit test: persistent controls cache
│       ├── test_14_qa_classics.py Unit test: legacy HTML patterns, tables, fieldsets
│       └── test_15_facebook_final_boss.py Scenario pack: complex UI, dynamic states
└── tests/                Integration hunt tests (real websites, .hunt format)
    ├── hunt_demoqa.hunt
    ├── hunt_expandtesting.hunt
    ├── hunt_mega.hunt
    ├── hunt_rahul.hunt
    └── hunt_wikipedia.hunt
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

Control how quickly Manul falls back to the local LLM via `.env`:

* **Low (200–500):** Blazing speed. Manul trusts heuristics.
* **Default (auto):** Derived from model size (e.g., `qwen2.5:0.5b` uses 500).
* **High (2,000+):** More AI involvement on ambiguous steps.

If `MANUL_AI_THRESHOLD` is **not set** (missing or commented out in `.env`), Manul auto-calculates it from the model size:

| Model size | Auto threshold |
| --- | --- |
| `< 1b` | `500` |
| `1b – 4b` | `750` |
| `5b – 9b` | `1000` |
| `10b – 19b` | `1500` |
| `20b+` | `2000` |

You can always override this by explicitly setting `MANUL_AI_THRESHOLD` in `.env`.

### 📴 Offline / Heuristics-Only Mode

If you don't want (or can't run) Ollama:

* Set `MANUL_AI_THRESHOLD=0` — disables the element-picker LLM fallback.
* Provide a numbered mission — the engine will rely on deterministic heuristics.

---

## 🛠️ Installation

ManulEngine runs fully locally on your machine.

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/alexbeatnik/browser-manul.git
cd browser-manul
```

### 2️⃣ Setup Environment

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

If you want AI fallback, install + run Ollama locally:

```bash
ollama pull qwen2.5:0.5b
ollama serve
```

### 3️⃣ Configuration (.env)

`.env` is optional. If it doesn't exist, ManulEngine uses built-in defaults.

By default, **process environment variables win** over `.env` (safer for CI/prod). If you want the repo `.env` to override already-set environment variables (useful for local prompt tuning), set:

```env
MANUL_DOTENV_OVERRIDE=True
```

Typical **mixed mode** setup (heuristics-first + AI fallback) looks like this:

```env
MANUL_AI_THRESHOLD=500
MANUL_AI_ALWAYS=False
MANUL_AI_POLICY=prior
```

Optional log compacting (helps when element `name` contains long context or `<select>` option lists):

```env
# 0 = no truncation (default)
MANUL_LOG_NAME_MAXLEN=160
MANUL_LOG_THOUGHT_MAXLEN=220
```

Persistent controls cache (per-site folder + per-URL file):

```env
# Enable/disable disk cache for resolved controls
MANUL_CONTROLS_CACHE_ENABLED=True

# Optional custom directory (default: repo-root cache/)
# MANUL_CONTROLS_CACHE_DIR=cache
```

Layout example:

```text
cache/
    example.com/
        root/
            controls.json
        text-box/
            controls.json
```

If a cached control for a URL is resolved again with updated attributes, the entry is overwritten.
Each distinct page URL gets its own cache file, so dynamic routes like
`/user/dsdfddg/1/medication-list` and `/user/zzxxyyq/2/medication-list`
are stored separately.

Synthetic `engine/test` runs via `python manul.py test` disable this cache by default
for deterministic, side-effect-free results.

Create `.env` by copying the template:

```bash
copy .env.example .env
```

Then edit `.env` in the repo root:

```env
MANUL_MODEL=qwen2.5:0.5b
MANUL_HEADLESS=False

# AI Threshold: lower = fewer AI calls, higher = more AI calls
# MANUL_AI_THRESHOLD=0
# MANUL_AI_THRESHOLD=500

# Force the LLM element picker for ALL element resolutions
# (bypasses heuristic short-circuits like semantic cache/context reuse)
# MANUL_AI_ALWAYS=True

# Optional: control how the LLM treats heuristic scores when selecting:
#   prior  = score is a hint; LLM may override with a clear reason (default)
#   strict = enforce max-score determinism (useful for synthetic/id-strict tests)
# MANUL_AI_POLICY=prior

# Optional: keep logs compact (collapse whitespace; truncate long names/thoughts)
# MANUL_LOG_NAME_MAXLEN=160
# MANUL_LOG_THOUGHT_MAXLEN=220

MANUL_TIMEOUT=5000
MANUL_NAV_TIMEOUT=30000
```

---

## 🖥️ CLI Usage

```bash
# Run all integration tests (tests/*.hunt)
python manul.py

# Run a specific hunt
python manul.py hunt_wikipedia.py

# Run in headless mode
python manul.py --headless

# Run inline mission
python manul.py "1. NAVIGATE to https://example.com  2. Click the 'More' link  3. DONE."

# Run synthetic DOM laboratory tests (local HTML via Playwright; no real websites)
python manul.py test
```

---

## 🚀 Quick Start

Create a hunt file: `tests/hunt_mission.hunt`

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
python manul.py tests/hunt_mission.hunt
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
| **Flow Control** | `WAIT [seconds]`, `SCROLL DOWN` |
| **Finish** | `DONE.` |

*Note: You can append `if exists` or `optional` to the end of any step (outside quoted text) to make it non-blocking, e.g. `Click 'Close Ad' if exists`.*

---

## 🐾 Chaos Chamber Verified (1227+ Tests)

The engine is battle-tested with **1227+** synthetic DOM/unit tests covering the web's most annoying UI patterns.

* **Synthetic DOM packs:** scenario suites under `engine/test/`.
* **Controls cache regression suite:** `engine/test/test_13_controls_cache.py` (disk cache hit/miss with temporary run folder cleanup).
* **AI modes regression suite:** `engine/test/test_12_ai_modes.py` (Always-AI, strict override, AI rejection).
* **QA Classics regression suite:** `engine/test/test_14_qa_classics.py` (legacy HTML patterns, tables, fieldsets).
* **Integration hunts:** Real-site E2E flows under `tests/*.hunt` (requires Playwright).

Run the synthetic suite:

```bash
python manul.py test

# PowerShell (heuristics-only, deterministic)
$env:MANUL_AI_THRESHOLD=0; python manul.py test
```

---

**Version:** 0.04

**Codename:** The Mastermind

**Status:** Hunting...