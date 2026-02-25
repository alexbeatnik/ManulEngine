# 🐱 ManulEngine v0.01 --- The Mastermind

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

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is
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

------------------------------------------------------------------------

### 👻 Smart Anti-Phantom Guard

Strict protection against LLM hallucinations.

If the model tries to: - Type into a radio button
- Click a hidden element

The Guard: 1. Blocks the action
2. Blacklists the element
3. Triggers a self-healing cycle

------------------------------------------------------------------------

### 🌑 Shadow DOM Penetration

Manul sees no barriers.
The engine automatically pierces Shadow Roots, interacting with elements
hidden deep in the shadow tree as easily as standard DOM elements.

------------------------------------------------------------------------

### 🧬 Semantic Cache & Context Memory

-   **Cache (20,000+ points):** Manul "learns" elements it successfully
    resolved via AI, skipping the LLM in future runs.
-   **Memory (10,000+ points):** The engine maintains context of the
    last active element to continue logical action chains.

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
python -m venv env

# Windows
env\Scripts\activate

# Linux / macOS
source env/bin/activate

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

# 🚀 Quick Start

Create a test file:

    tests/hunt_mission.py

``` python
import asyncio
from framework.engine import ManulEngine

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

The engine is battle-tested against the **24 Deadly DOM Traps**,
successfully handling:

-   The Legend Trap (finding inputs via fieldset/legend)
-   Data-QA Supremacy (prioritizing automation-specific attributes)
-   ARIA Recognition (locating elements via hidden labels)
-   Ghost Opacity (interacting with near-transparent elements)
-   Readonly Hijacking (typing into locked fields)

------------------------------------------------------------------------

**Version:** 0.01
**Codename:** The Mastermind
**Status:** Hunting...
