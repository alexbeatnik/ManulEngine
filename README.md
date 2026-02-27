
---

# 😼 ManulEngine v0.02 — The Mastermind

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
├── .env                  Runtime configuration (model, threshold, headless) — currently committed
├── engine/               Core automation engine package
│   ├── __init__.py       Public API — exports ManulEngine
│   ├── prompts.py        Configuration, thresholds, LLM prompts
│   ├── helpers.py        Pure utility functions and timing constants
│   ├── js_scripts.py     JavaScript injected into the browser (DOM snapshot & deep text)
│   ├── scoring.py        Heuristic element-scoring algorithm (20+ rules)
│   ├── core.py           ManulEngine class (LLM, resolution, mission runner)
│   ├── actions.py        Action execution mixin (click, type, select, hover, drag)
│   └── test/
│       ├── test_engine.py       Engine micro-suite (synthetic DOM via local HTML; uses Playwright)
│       ├── test_01_ecommerce.py Scenario pack: ecommerce (synthetic DOM)
│       ├── test_02_social.py    Scenario pack: social (synthetic DOM)
│       ├── ...                  More packs (see engine/test/)
│       ├── test_10_mess.py      Scenario pack: misc edge-cases (synthetic DOM)
│       └── test_11_cyber.py     Scenario pack: cyber/terminal (synthetic DOM)
└── tests/                Integration hunt tests (real websites)
    ├── hunt_demoqa.py
    ├── hunt_expandtesting.py
    ├── hunt_mega.py
    ├── hunt_rahul.py
    ├── hunt_wikipedia.py
    └── hunt_cyber.py            100-step DevSecOps & Terminal simulation
```

---

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is handled by ultra-fast JavaScript and Python heuristics. The AI steps in only when genuine ambiguity arises.

### 🛡️ Unbreakable JS Fallbacks

Modern websites love to hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. If native Playwright actions (`click()`, `type()`) fail due to element occlusion, Manul falls back to direct DOM event dispatches (`window.manulClick`, `window.manulType`) to keep execution moving.

### 🌑 Shadow DOM Awareness

The DOM snapshotter recursively inspects shadow roots and can interact with elements in the shadow tree.

### 👻 Smart Anti-Phantom Guard & AI Rejection

Strict protection against LLM hallucinations. If the model is unsure it can return `{"id": null}`; the engine treats that as a rejection and retries with self-healing.

### 🎛️ Adjustable AI Threshold (Paranoia Level)

Control how quickly Manul falls back to the local LLM via `.env`:

* **Low (200–500):** Blazing speed. Manul trusts heuristics.
* **Default (auto):** Derived from model size (e.g., `qwen2.5:0.5b` uses 500).
* **High (2,000+):** More AI involvement on ambiguous steps.

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

Create or edit `.env` in the repo root:

```env
MANUL_MODEL=qwen2.5:0.5b
MANUL_HEADLESS=False

# AI Threshold: lower = fewer AI calls, higher = more AI calls
# MANUL_AI_THRESHOLD=0
# MANUL_AI_THRESHOLD=500

MANUL_TIMEOUT=5000
MANUL_NAV_TIMEOUT=30000
```

---

## 🖥️ CLI Usage

```bash
# Run all integration tests (tests/hunt_*.py)
python manul.py

# Run a specific hunt
python manul.py hunt_demoqa.py

# Run in headless mode
python manul.py --headless

# Run inline mission
python manul.py "1. NAVIGATE to https://example.com  2. Click the 'More' link  3. DONE."

# Run synthetic DOM laboratory tests (local HTML via Playwright; no real websites)
python manul.py test
```

---

## 🚀 Quick Start

Create a test file: `tests/hunt_mission.py`

```python
import asyncio
from engine import ManulEngine

async def main(headless: bool = False) -> bool:
    manul = ManulEngine(headless=headless)

    mission = (
        "1. NAVIGATE to https://demoqa.com/text-box\n"
        "2. Fill 'Full Name' field with 'Ghost Manul'\n"
        "3. Click the 'Submit' button\n"
        "4. VERIFY that 'Ghost Manul' is present.\n"
        "5. DONE."
    )

    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())
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

## 🐾 Chaos Chamber Verified (1100+ Tests)

The engine is battle-tested with **1177+** synthetic DOM/unit tests covering the web's most annoying UI patterns.

* **Synthetic DOM packs:** 11 scenario suites under `engine/test/`.
* **Integration hunts:** Real-site E2E flows under `tests/hunt_*.py` (requires Playwright). Includes `hunt_cyber.py` — a 100-step terminal and dashboard simulation.

Run the synthetic suite:

```bash
python manul.py test

# PowerShell (heuristics-only, deterministic)
$env:MANUL_AI_THRESHOLD=0; python manul.py test
```

---

**Version:** 0.02

**Codename:** The Mastermind

**Status:** Hunting...