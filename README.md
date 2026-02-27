
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
├── .env                  Runtime configuration (model, threshold, headless)
├── engine/               Core automation engine package
│   ├── __init__.py       Public API — exports ManulEngine
│   ├── prompts.py        Configuration, thresholds, LLM prompts
│   ├── helpers.py        Pure utility functions and timing constants
│   ├── js_scripts.py     JavaScript injected into the browser (DOM snapshot & deep text)
│   ├── scoring.py        Heuristic element-scoring algorithm (Mode Synergy, 20+ rules)
│   ├── core.py           ManulEngine class (LLM, resolution, mission runner)
│   ├── actions.py        Action execution mixin (click, type, select, hover, drag)
│   └── test/
│       ├── test_engine.py       Engine micro-suite (synthetic DOM, no browser)
│       ├── test_01_ecommerce.py Scenario pack: ecommerce (synthetic DOM)
│       ├── test_02_social.py    Scenario pack: social (synthetic DOM)
│       ├── ...                  More packs (see engine/test/)
│       └── test_10_mess.py      Scenario pack: misc edge-cases (synthetic DOM)
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

### ⚡ Heuristics-First Architecture & Mode Synergy

95% of the heavy lifting (element finding, assertions, DOM parsing) is handled by ultra-fast JavaScript and Python heuristics. The AI steps in only when genuine ambiguity arises.
**Mode Synergy:** The engine intelligently correlates exact text matches with HTML semantics (e.g., prioritizing a `<button>` over a `<div>` if both say "Submit").

### 🛡️ Unbreakable JS Fallbacks

Modern websites love to hide elements behind invisible overlays, custom dropdowns, and zero-pixel traps. If native Playwright actions (`click()`, `type()`) fail due to element occlusion, Manul seamlessly falls back to direct DOM Event dispatches (`window.manulClick`, `KeyboardEvent`) to guarantee execution.

### 🌑 Deep Shadow DOM Penetration

Manul sees no barriers. The engine automatically pierces Shadow Roots, interacting with elements hidden deep in the shadow tree, and utilizes recursive deep-text extraction to verify state that standard DOM parsers miss.

### 👻 Smart Anti-Phantom Guard & AI Rejection

Strict protection against LLM hallucinations.
If the model is unsure or tries to interact with a bad target:

1. The LLM can explicitly return `null`.
2. The Guard blocks the action and blacklists the bad element.
3. Triggers a self-healing cycle (scrolling, re-scanning the DOM) to uncover hidden elements.

### 🎛️ Adjustable AI Threshold (Paranoia Level)

Control how quickly Manul falls back to the local LLM via `.env`:

* **Low (200–500):** Blazing speed. Manul trusts its heuristic algorithms for most tasks.
* **Default (auto):** Derived from model size (e.g., `qwen2.5:0.5b` uses 500).
* **High (2,000+):** More AI involvement on ambiguous steps ("paranoid" mode).

### 📴 Offline / Heuristics-Only Mode

If you don't want (or can't run) Ollama:

* Set `MANUL_AI_THRESHOLD=0` — disables the **element picker** LLM fallback entirely.
* Provide a **numbered mission** — the engine will rely 100% on its deterministic heuristics.

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

Create a `.env` file in the root directory:

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

# Run a specific test
python manul.py hunt_demoqa.py

# Run in headless mode
python manul.py --headless

# Run inline mission
python manul.py "1. NAVIGATE to https://example.com  2. Click the 'More' link  3. DONE."

# Run synthetic engine tests (no Playwright)
python manul.py test

```

---

## 🚀 Quick Start

Create a test file: `tests/hunt_mission.py`

```python
import asyncio
from engine import ManulEngine

async def main():
    # Settings are automatically loaded from .env
    manul = ManulEngine()

    mission = (
        "1. NAVIGATE to https://demoqa.com/text-box\n"
        "2. Fill 'Full Name' field with 'Ghost Manul'\n"
        "3. Click the 'Submit' button\n"
        "4. VERIFY that 'Ghost Manul' is present.\n"
        "5. DONE."
    )

    await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())

```

---

## 📜 Available Commands

| Category | Command Syntax |
| --- | --- |
| **Navigation** | `Maps to [URL]` |
| **Input** | `Fill [Field] with [Text]`, `Type [Text] into [Field]` |
| **Click** | `Click [Element]`, `DOUBLE CLICK [Element]` |
| **Selection** | `Select [Option] from [Dropdown]`, `Check [Checkbox]`, `Uncheck [Checkbox]` |
| **Mouse Action** | `HOVER over [Element]`, `Drag [Element] and drop it into [Target]` |
| **Data Extraction** | `EXTRACT [Target] into {variable_name}` |
| **Verification** | `VERIFY that [Text] is present/absent`, `VERIFY that [Element] is checked/disabled` |
| **Flow Control** | `WAIT [seconds]`, `SCROLL DOWN` |
| **Finish** | `DONE` |

*Note: You can append `if exists` or `optional` to the end of any step to make it non-blocking.*

---

## 🐾 Chaos Chamber Verified (1100+ Tests)

The engine is battle-tested against **1177+** of the web's most annoying UI patterns. It guarantees robust execution across a synthetic DOM laboratory and real-site integration hunts.

* **Synthetic DOM packs:** 10 scenario suites under `engine/test/` (E-Commerce, Social, SaaS, Travel, Fintech, Media, Gov/Health, CRM, EdTech, and "The Unholy Mess").
* **Integration hunts:** Real-site E2E flows under `tests/hunt_*.py` (requires Playwright). Includes `hunt_cyber.py` — an epic 100-step terminal and dashboard simulation.

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