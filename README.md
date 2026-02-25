# 🐱 ManulEngine v0.01 --- The Mastermind

**ManulEngine** is a relentless hybrid (neuro-symbolic) framework for
browser automation and E2E testing.

Instead of writing brittle CSS/XPath locators that break on every UI
update, you write tests in **plain English**.\
Instead of paying for expensive cloud APIs and waiting seconds for every
click, you use **micro-LLMs locally**.

Manul combines the blazing speed of Playwright, powerful JavaScript DOM
heuristics, and the reasoning of local neural networks (via Ollama).\
It is designed to be fast, private, and highly resilient to UI changes.

> The Manul goes hunting and never returns without its prey.

------------------------------------------------------------------------

## ✨ Key Features

### ⚡ Heuristics-First Architecture

95% of the heavy lifting (element finding, assertions, DOM parsing) is
handled by ultra-fast JavaScript.\
The AI steps in only when genuine ambiguity arises.

Result: dramatically faster execution than AI-first automation
approaches.

------------------------------------------------------------------------

### 👻 Smart Anti-Phantom Guard

Strict protection against LLM hallucinations.

If the model tries to: - Type text into a radio button - Select an
option from a checkbox - Perform an illogical action

The Guard: 1. Blocks the action\
2. Rejects the candidate\
3. Triggers a self-healing cycle

------------------------------------------------------------------------

### 🚑 Self-Healing Loops

If an element is: - Missing\
- Blocked\
- Rejected

Manul: - Adds it to a blocklist\
- Scrolls if needed\
- Retries up to 5 times

------------------------------------------------------------------------

### 🧠 Semantic Cache

When Manul successfully resolves a complex element using AI, it learns
it.

Future interactions: - Skip the LLM\
- Execute instantly\
- Receive high internal scoring (20,000+)

------------------------------------------------------------------------

### 📊 Structured Table Extractor

Dynamically parses tables into:

``` python
List[Dict]
```

Manul: - Matches your natural language request\
- Aligns it with actual table headers\
- Extracts precise cell data without hardcoded logic

------------------------------------------------------------------------

### 🔒 Zero Data Leak

All website data: - Stays local\
- Is never sent to the cloud\
- Is never stored externally

Ideal for: - Fintech\
- Healthcare\
- Secure enterprise networks

------------------------------------------------------------------------

# 🛠️ Installation

ManulEngine runs fully locally.

Requirements: - Python 3.10+ - Playwright - Ollama

------------------------------------------------------------------------

## 1️⃣ Clone the Repository

``` bash
git clone https://github.com/alexbeatnik/browser-manul.git
cd browser-manul
```

------------------------------------------------------------------------

## 2️⃣ Setup Python Environment

``` bash
python -m venv env

# Linux / macOS
source env/bin/activate  

# Windows
# env\Scripts\activate   

pip install playwright ollama
```

------------------------------------------------------------------------

## 3️⃣ Install Playwright Browsers

``` bash
python -m playwright install chromium
```

------------------------------------------------------------------------

## 4️⃣ Install and Run Ollama

Recommended model:

    qwen2.5:0.5b

Download and run:

``` bash
ollama run qwen2.5:0.5b
```

------------------------------------------------------------------------

# 🚀 Quick Start

Create a test file:

    tests/hunt_mission.py

``` python
import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine(headless=False)

    mission = (
        "1. NAVIGATE to https://the-internet.herokuapp.com/login\n"
        "2. Fill 'Username' field with 'tomsmith'\n"
        "3. Fill 'Password' field with 'SuperSecretPassword!'\n"
        "4. Click the 'Login' button\n"
        "5. VERIFY that 'You logged into a secure area!' is present.\n"
        "6. DONE."
    )

    print("🐾 Running LOGIN HUNT...")
    success = await manul.run_mission(mission)

    if success:
        print("🏆 HUNT SUCCESSFUL")
    else:
        print("❌ HUNT FAILED")

if __name__ == "__main__":
    asyncio.run(main())
```

Run:

``` bash
python tests/hunt_mission.py
```

------------------------------------------------------------------------

# 📜 Available Commands

### Navigation

    NAVIGATE to [URL]

### Input

    Fill [Field] with [Text]
    Type [Text] into [Field]

### Click

    Click [Element]
    DOUBLE CLICK [Element]

### Checkbox / Radio

    Check [Checkbox]
    Uncheck [Checkbox]

### Dropdown

    Select [Option] from [Dropdown]

### Hover

    HOVER over [Element]

### Scroll

    SCROLL DOWN

### Extract

    EXTRACT [Target] into {variable}

### Verify

    VERIFY that [Text] is present
    VERIFY that [Text] is absent
    VERIFY that [Element] is checked
    VERIFY that [Element] is disabled

### Finish

    DONE

------------------------------------------------------------------------

# 🤝 Roadmap & Contributing

Version 0.01 is the first public release.

Manul already: - Completes 50-step Wikipedia marathons\
- Works with Shadow DOM\
- Extracts multi-dimensional tables\
- Uses local LLMs without sacrificing speed

------------------------------------------------------------------------

# 🐾 Philosophy

Manul is not just an AI agent.

It is: - Deterministic heuristics\
- Neural fallback\
- Strict validation layer\
- Self-healing automation engine

AI is only a tool.\
Control always remains in the engine.

------------------------------------------------------------------------

**Version:** 0.01\
**Codename:** The Mastermind
