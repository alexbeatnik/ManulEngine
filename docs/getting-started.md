# Getting Started

> **ManulEngine v0.0.9.29**

This guide walks you through creating your first `.hunt` test, running it, and viewing the results.

## Prerequisites

Make sure you have completed the [installation](installation.md):

```bash
pip install manul-engine==0.0.9.29
playwright install
```

## Your First Hunt File

Create a file called `tests/login.hunt`:

```text
@context: Smoke test for the SauceDemo login page
@title: SauceDemo Login
@var: {username} = standard_user
@var: {password} = secret_sauce

STEP 1: Open the login page
    NAVIGATE to https://www.saucedemo.com
    VERIFY that 'Swag Labs' is present

STEP 2: Log in with valid credentials
    FILL 'Username' field with '{username}'
    VERIFY "Username" field has value "{username}"
    FILL 'Password' field with '{password}'
    CLICK the 'Login' button
    VERIFY that 'Products' is present

STEP 3: Add an item to the cart
    CLICK the 'Add to cart' button NEAR 'Sauce Labs Backpack'
    VERIFY that 'Remove' is present

DONE.
```

### Key patterns in this file

- **`@var:`** declares test data up front — never hardcode values inside steps.
- **`STEP N: description`** groups actions into logical blocks.
- **`VERIFY`** confirms page state after every significant action.
- **`NEAR`** disambiguates when multiple buttons share the same label.
- **`DONE.`** marks the end of the mission.

## Running the Test

### Basic run (headed browser)

```bash
manul tests/login.hunt
```

A browser window opens, the engine executes each step, and results are printed to the terminal.

### Headless mode

```bash
manul --headless tests/login.hunt
```

### Run all tests in a directory

```bash
manul tests/
```

### Run with tags

Add `@tags: smoke` to your hunt file header, then:

```bash
manul --tags smoke tests/
```

Only files with the `smoke` tag will execute.

## Reading the Output

Terminal output follows this pattern:

```text
[📦 BLOCK START] STEP 1: Open the login page
  [▶️ ACTION START] NAVIGATE to https://www.saucedemo.com
  [✅ ACTION PASS]  NAVIGATE to https://www.saucedemo.com (1.2s)
  [▶️ ACTION START] VERIFY that 'Swag Labs' is present
  [✅ ACTION PASS]  VERIFY that 'Swag Labs' is present (0.1s)
[🟩 BLOCK PASS] STEP 1: Open the login page

[📦 BLOCK START] STEP 2: Log in with valid credentials
  ...
[🟩 BLOCK PASS] STEP 2: Log in with valid credentials

✅ MISSION PASS — SauceDemo Login (3.4s)
```

- `[🟩 BLOCK PASS]` — all actions in the STEP succeeded.
- `[🟥 BLOCK FAIL]` — an action in the STEP failed; remaining actions in that block are skipped.
- `[✅ ACTION PASS]` / `[❌ ACTION FAIL]` — individual action results.

## Generating HTML Reports

```bash
manul --html-report --screenshot on-fail tests/login.hunt
```

This creates `reports/manul_report.html` — a self-contained dark-themed HTML file with:

- Dashboard stats (total / passed / failed / duration)
- Collapsible accordions per mission and per step
- Inline base64 screenshots on failed steps
- Tag filter chips
- "Show Only Failed" toggle

Open it in any browser:

```bash
open reports/manul_report.html          # macOS
xdg-open reports/manul_report.html      # Linux
```

See [Reports & Explainability](reports.md) for details.

## Using Explain Mode

To see exactly how the engine resolved each element:

```bash
manul --explain tests/login.hunt
```

Each resolved step prints a per-channel scoring breakdown. See [Reports → Explain Mode](reports.md#explain-mode) for details.

## Debug Mode

### Terminal debug (pause before every step)

```bash
manul --debug tests/login.hunt
```

Press Enter to advance through each step. During a pause you can:
- Type `e` for one-shot explain analysis of the current step.
- Type `w` to enter the What-If Analysis REPL for hypothetical step evaluation.

### VS Code debug (gutter breakpoints)

With the Manul Engine Extension installed, set breakpoints in the gutter of your `.hunt` file and use the Debug run profile in Test Explorer. The extension pauses at each breakpoint with a QuickPick menu offering Next Step, Continue, Highlight Element, Debug Stop, and Stop Test.

## Scanning a Page

Generate a draft `.hunt` file from a live page:

```bash
manul scan https://www.saucedemo.com
```

This outputs a draft hunt to `tests/draft.hunt` (or the `tests_home` directory from your config). Edit the draft to turn it into a real test.

```bash
manul scan https://www.saucedemo.com my_test.hunt    # custom output file
manul scan https://www.saucedemo.com --headless       # headless scan
```

## Project Structure

A typical ManulEngine project looks like this:

```text
my-project/
├── manul_engine_configuration.json    # Engine config (optional, all defaults work)
├── pages.json                         # Page name mappings for auto-annotate
├── tests/
│   ├── login.hunt                     # Test files
│   ├── checkout.hunt
│   └── manul_hooks.py                 # Global lifecycle hooks (@before_all, etc.)
├── controls/
│   └── datepicker.py                  # Custom control handlers
├── scripts/
│   └── db_helpers.py                  # Python helpers for CALL PYTHON
├── reports/
│   ├── manul_report.html              # Generated HTML report
│   └── run_history.json               # Run history (JSON Lines)
└── cache/                             # Persistent controls cache (auto-generated)
```

## Next Steps

- [DSL Syntax Reference](dsl-syntax.md) — full command reference, variables, conditionals, custom controls
- [Reports & Explainability](reports.md) — HTML reports, explain mode, What-If REPL
- [Integration](integration.md) — Python API, CI/CD, Docker
