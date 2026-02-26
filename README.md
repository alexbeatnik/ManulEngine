# 😼 ManulEngine v0.02 --- The Mastermind

ManulEngine is a relentless hybrid (neuro-symbolic) framework for
browser automation and E2E testing.

Forget brittle CSS/XPath locators that break on every UI update---write
tests in plain English.
Stop paying for expensive cloud APIs and waiting seconds for every
click---leverage local micro-LLMs via Ollama.

Manul combines the blazing speed of Playwright, powerful JavaScript DOM
heuristics, and the reasoning of local neural networks.
It is fast, private, and highly resilient to UI changes.

> The Manul goes hunting and never returns without its prey.

------------------------------------------------------------------------

## 📁 Project Structure

```
browser-manul/
├── manul.py              CLI runner (test files, inline prompts, unit tests)
├── requirements.txt      Python dependencies
├── .env                  Runtime configuration (model, threshold, headless)
├── engine/               Core automation engine package
│   ├── __init__.py       Public API — exports ManulEngine
│   ├── prompts.py        Configuration, thresholds, LLM prompts
│   ├── helpers.py        Pure utility functions and timing constants
│   ├── js_scripts.py     JavaScript injected into the browser (DOM snapshot)
│   ├── scoring.py        Heuristic element-scoring algorithm (20+ rules)
│   ├── core.py           ManulEngine class (LLM, resolution, mission runner)
│   ├── actions.py        Action execution mixin (click, type, select, hover, drag)
│   └── test/
│       ├── test_engine.py       Engine micro-suite (synthetic DOM, no browser)
│       ├── test_01_ecommerce.py  Scenario pack: ecommerce (synthetic DOM)
│       ├── test_02_social.py     Scenario pack: social (synthetic DOM)
│       ├── ...                  More packs (see engine/test/)
│       └── test_10_mess.py       Scenario pack: misc edge-cases (synthetic DOM)
└── tests/                Integration hunt tests (real websites)
    ├── hunt_demoqa.py
    ├── hunt_expandtesting.py
    ├── hunt_mega.py
    ├── hunt_rahul.py
    └── hunt_wikipedia.py
```

------------------------------------------------------------------------

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is
handled by ultra-fast JavaScript.
The AI steps in only when genuine ambiguity arises.

**Result:** Execution speeds significantly faster than "AI-first"
automation approaches.

------------------------------------------------------------------------

### 🎛️ Adjustable AI Threshold (Paranoia Level)

Control how quickly Manul falls back to the local LLM via `.env`:

- **Lower threshold** → fewer AI calls (heuristics win more often)
- **Higher threshold** → more AI calls ("paranoid" verification / disambiguation)

-   **Low (200--500):** Blazing speed. Manul trusts its heuristic
    algorithms for most tasks.
-   **Default (auto):** Derived from model size (see `engine/prompts.py`).
-   **High (2,000+):** More AI involvement on ambiguous steps.

Tip: set `MANUL_AI_THRESHOLD=0` to force **heuristics-only** runs (never call the LLM).

Note: if you pass a **free-text** task (not a numbered step list), Manul will still use the LLM planner to generate steps.
To avoid Ollama entirely, provide a numbered mission.

### 📴 AI disabled / offline mode

If you don't want (or can't run) Ollama:

- Set `MANUL_AI_THRESHOLD=0` — disables the **element picker** LLM fallback.
- Provide a **numbered mission** — otherwise the free-text **planner** still needs the LLM.

------------------------------------------------------------------------

### 👻 Smart Anti-Phantom Guard

Strict protection against LLM hallucinations.

If the model tries to:
- Type into a radio button
- Click a hidden element

The Guard:
1. Blocks the action
2. Blacklists the element
3. Triggers a self-healing cycle

------------------------------------------------------------------------

### 🌑 Shadow DOM Penetration

Manul sees no barriers.
The engine automatically pierces Shadow Roots, interacting with elements
hidden deep in the shadow tree as easily as standard DOM elements.

------------------------------------------------------------------------

# 🛠️ Installation

ManulEngine runs fully locally on your machine.

------------------------------------------------------------------------

## 1️⃣ Clone the Repository

``` bash
git clone https://github.com/alexbeatnik/browser-manul.git
cd browser-manul
```

------------------------------------------------------------------------

## 2️⃣ Setup Environment

``` bash
pip install -r requirements.txt
python -m playwright install chromium
```

If you want AI fallback, install + run Ollama locally:

```bash
ollama pull qwen2.5:0.5b
ollama serve
```

------------------------------------------------------------------------

## 3️⃣ Configuration (.env)

Create a `.env` file in the root directory:

``` env
MANUL_MODEL=qwen2.5:0.5b
MANUL_HEADLESS=False

# AI Threshold: lower = fewer AI calls, higher = more AI calls
# MANUL_AI_THRESHOLD=0
# MANUL_AI_THRESHOLD=500

MANUL_TIMEOUT=5000
MANUL_NAV_TIMEOUT=30000
```

------------------------------------------------------------------------

# 🖥️ CLI Usage

``` bash
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

------------------------------------------------------------------------

## 🌍 Integration hunts (real sites)

Files under `tests/hunt_*.py` are **integration hunts**: they open real websites and execute end-to-end flows.

Prerequisites:

- Playwright browsers installed: `python -m playwright install chromium`
- Network access (sites can change and may be flaky)
- Ollama **only if** you want AI fallback on ambiguous steps

Deterministic tip (no AI calls):

```bash
# PowerShell (heuristics-only)
$env:MANUL_AI_THRESHOLD=0; python manul.py hunt_wikipedia.py
```

------------------------------------------------------------------------

# 🚀 Quick Start

Create a test file:

    tests/hunt_mission.py

``` python
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

------------------------------------------------------------------------

# 📜 Available Commands

  -----------------------------------------------------------------------
  Category                                    Command
  ------------------------------------------- ---------------------------
  Navigation                                  NAVIGATE to \[URL\]

  Input                                       Fill \[Field\] with
                                              \[Text\], Type \[Text\]
                                              into \[Field\]

  Click                                       Click \[Element\], DOUBLE
                                              CLICK \[Element\]

  Selection                                   Select \[Option\] from
                                              \[Dropdown\], Check
                                              \[Checkbox\]

  Data                                        EXTRACT \[Target\] into
                                              {variable}

  Verification                                VERIFY that \[Text\] is
                                              present/absent, VERIFY that
                                              \[Element\] is
                                              checked/disabled

  Finish                                      DONE
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 🐾 Chaos Chamber Verified

The engine is battle-tested in a synthetic DOM laboratory (no Playwright)
plus real-site integration hunts.

-   **Synthetic DOM packs:** scenario suites under `engine/test/` (ecommerce, social, saas, travel, fintech, media, gov/health, crm, edtech, mess).
-   **Engine micro-suite:** core edge-cases and regressions in `engine/test/test_engine.py`.
-   **Integration hunts:** real-site flows under `tests/hunt_*.py` (requires Playwright; Ollama only if you want AI fallback).

Run the synthetic suite:

``` bash
python manul.py test

# PowerShell (heuristics-only, deterministic)
$env:MANUL_AI_THRESHOLD=0; python manul.py test
```

------------------------------------------------------------------------

**Version:** 0.02
**Codename:** The Mastermind
**Status:** Hunting...
