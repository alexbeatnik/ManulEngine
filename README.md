# 🐱 ManulEngine v0.02 --- The Mastermind

ManulEngine is a relentless hybrid (neuro-symbolic) framework for
ManulEngine is a relentless hybrid (neuro-symbolic) framework for
browser automation and E2E testing.

Forget brittle CSS/XPath locators that break on every UI update---write
tests in plain English.
Stop paying for expensive cloud APIs and waiting seconds for every
click---leverage local micro-LLMs via Ollama.
Forget brittle CSS/XPath locators that break on every UI update---write
tests in plain English.
Stop paying for expensive cloud APIs and waiting seconds for every
click---leverage local micro-LLMs via Ollama.

Manul combines the blazing speed of Playwright, powerful JavaScript DOM
heuristics, and the reasoning of local neural networks.
It is fast, private, and highly resilient to UI changes.
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
│       └── test_engine.py  60-trap Monster DOM unit test suite
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
handled by ultra-fast JavaScript.
The AI steps in only when genuine ambiguity arises.

**Result:** Execution speeds significantly faster than "AI-first"
automation approaches.

------------------------------------------------------------------------

### 🎛️ Adjustable AI Threshold (Paranoia Level)

Control the engine's confidence via `.env` using a scoring system:

-   **Low (200--500):** Blazing speed. Manul trusts its heuristic
    algorithms for most tasks.
-   **High (10,000+):** "Paranoid" mode. The AI Agent verifies almost
    every step for maximum precision.
**Result:** Execution speeds significantly faster than "AI-first"
automation approaches.

------------------------------------------------------------------------

### 🎛️ Adjustable AI Threshold (Paranoia Level)

Control the engine's confidence via `.env` using a scoring system:

-   **Low (200--500):** Blazing speed. Manul trusts its heuristic
    algorithms for most tasks.
-   **High (10,000+):** "Paranoid" mode. The AI Agent verifies almost
    every step for maximum precision.

------------------------------------------------------------------------

### 👻 Smart Anti-Phantom Guard

Strict protection against LLM hallucinations.

If the model tries to: - Type into a radio button
- Click a hidden element
If the model tries to: - Type into a radio button
- Click a hidden element

The Guard: 1. Blocks the action
2. Blacklists the element
The Guard: 1. Blocks the action
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
ManulEngine runs fully locally on your machine.

------------------------------------------------------------------------

## 1️⃣ Clone the Repository

``` bash
git clone https://github.com/alexbeatnik/browser-manul.git
cd browser-manul
```

------------------------------------------------------------------------

## 2️⃣ Setup Environment
## 2️⃣ Setup Environment

``` bash
pip install playwright ollama python-dotenv
python -m playwright install chromium
```

------------------------------------------------------------------------

## 3️⃣ Configuration (.env)

Create a `.env` file in the root directory:

``` env
MANUL_MODEL=qwen2.5:0.5b
MANUL_HEADLESS=False

# AI Threshold: 500 (standard), 10000 (maximum verification)
MANUL_AI_THRESHOLD=500

MANUL_TIMEOUT=5000
```

------------------------------------------------------------------------

# �️ CLI Usage

``` bash
# Run all integration tests (tests/hunt_*.py)
python manul.py

# Run a specific test
python manul.py hunt_demoqa.py

# Run in headless mode
python manul.py --headless

# Run inline mission
python manul.py "1. NAVIGATE to https://example.com  2. Click the 'More' link  3. DONE."

# Run engine unit tests (60 traps)
python manul.py test
```

------------------------------------------------------------------------

# �🚀 Quick Start

Create a test file:

    tests/hunt_mission.py

``` python
import asyncio
from engine import ManulEngine

async def main():
    # Settings are automatically loaded from .env
    manul = ManulEngine()
    # Settings are automatically loaded from .env
    manul = ManulEngine()

    mission = (
        "1. NAVIGATE to https://demoqa.com/text-box\n"
        "2. Fill 'Full Name' field with 'Ghost Manul'\n"
        "3. Click the 'Submit' button\n"
        "4. VERIFY that 'Ghost Manul' is present.\n"
        "5. DONE."
        "1. NAVIGATE to https://demoqa.com/text-box\n"
        "2. Fill 'Full Name' field with 'Ghost Manul'\n"
        "3. Click the 'Submit' button\n"
        "4. VERIFY that 'Ghost Manul' is present.\n"
        "5. DONE."
    )

    await manul.run_mission(mission)
    await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())
```

------------------------------------------------------------------------

# 📜 Available Commands

  -----------------------------------------------------------------------
  Category                                    Command
  ------------------------------------------- ---------------------------
  Navigation                                  Maps to \[URL\]

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
  -----------------------------------------------------------------------
  Category                                    Command
  ------------------------------------------- ---------------------------
  Navigation                                  Maps to \[URL\]

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

The engine is battle-tested against **60 DOM Traps** (Monster DOM),
successfully handling:

-   **24 core traps:** Legend Form, Phantom Guard, ARIA Recognition,
    Shadow DOM, Data-QA Supremacy, Ghost Opacity, Readonly Hijacking,
    Section Context, Icon-Only Buttons, Disabled Avoidance, and more.
-   **4 optional traps:** "if exists" / "optional" keyword handling
    with exact-match guarding against false positives.
-   **6 bug-regression traps:** Check/Uncheck mode detection, Select
    triple collision, Optional partial-match decoy, data-qa hyphen
    mapping, Native checkbox JS click.
-   **12 hunt-site pattern traps:** Textarea vs Input, Double-click,
    Date input, Search input, Pagination, Day checkboxes, Country
    dropdown, Hover, Checkbox toggle, Fill+Enter.
-   **14 normal element tests:** Simple form fills, button clicks, link
    clicks, readonly fill, radio, checkbox, VERIFY text/checked,
    EXTRACT from table.

Run the full suite:

``` bash
python manul.py test
```

------------------------------------------------------------------------

**Version:** 0.02
**Codename:** The Mastermind
**Status:** Hunting...
**Status:** Hunting...
