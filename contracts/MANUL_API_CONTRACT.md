# ManulEngine — Python API Contract

> **Machine-readable contract for the ManulSession programmatic Python API.**
> Consumed by downstream Python integrations, pytest wrappers, RPA frameworks, and AI-agent harnesses.

```json
{
  "version": "0.0.9.29",
  "generatedFrom": "manul_engine/api.py :: ManulSession; manul_engine/__init__.py :: re-exports",

  "importPath": "from manul_engine import ManulSession",

  "class": "ManulSession",
  "description": "High-level async context manager for programmatic browser automation. Manages its own Playwright lifecycle. All element resolution routes through the full ManulEngine pipeline (cache → heuristics → optional LLM fallback).",

  "constructor": {
    "parameters": [
      { "name": "model",           "type": "str | None",       "default": null,   "description": "Ollama model name. None = heuristics-only." },
      { "name": "headless",        "type": "bool | None",      "default": null,   "description": "Run browser headless. None = read from config." },
      { "name": "browser",         "type": "str | None",       "default": null,   "description": "'chromium' | 'firefox' | 'webkit'. None = read from config." },
      { "name": "browser_args",    "type": "list[str] | None", "default": null,   "description": "Extra browser launch flags." },
      { "name": "ai_threshold",    "type": "int | None",       "default": null,   "description": "Custom LLM fallback threshold." },
      { "name": "disable_cache",   "type": "bool",             "default": false,  "description": "Disable persistent controls cache." },
      { "name": "semantic_cache",  "type": "bool | None",      "default": null,   "description": "Enable in-session semantic cache." },
      { "name": "channel",         "type": "str | None",       "default": null,   "description": "Playwright browser channel (e.g. 'chrome', 'msedge')." },
      { "name": "executable_path", "type": "str | None",       "default": null,   "description": "Custom browser or Electron executable path." }
    ]
  },

  "lifecycle": {
    "contextManager": {
      "usage": "async with ManulSession(...) as session: ...",
      "entry": "Calls start() — launches Playwright, spawns browser, opens initial page.",
      "exit": "Calls close() — tears down browser and Playwright."
    },
    "explicit": {
      "start": { "signature": "() -> ManulSession", "description": "Launch browser and open page. Returns self for chaining." },
      "close": { "signature": "() -> None", "description": "Close browser and tear down Playwright." }
    }
  },

  "properties": [
    { "name": "page",   "type": "playwright.async_api.Page",   "description": "Active Playwright Page object. Useful for advanced one-off Playwright calls." },
    { "name": "engine", "type": "ManulEngine",                  "description": "Underlying ManulEngine instance (read-only)." },
    { "name": "memory", "type": "ScopedVariables",              "description": "Shortcut to engine's scoped variable store." }
  ],

  "methods": {
    "navigation": [
      {
        "name": "navigate",
        "signature": "(url: str) -> None",
        "description": "Navigate to URL and wait for DOM settlement (2s stability wait).",
        "dslEquivalent": "NAVIGATE to 'url'"
      }
    ],

    "actions": [
      {
        "name": "click",
        "signature": "(target: str, *, double: bool = False) -> bool",
        "returns": "True on success, False on failure",
        "description": "Click or double-click an element resolved via the heuristic pipeline.",
        "dslEquivalent": "Click the 'target' button / DOUBLE CLICK the 'target'"
      },
      {
        "name": "fill",
        "signature": "(target: str, text: str) -> bool",
        "returns": "True on success, False on failure",
        "description": "Type text into an input field. Clears existing content first.",
        "dslEquivalent": "Fill 'target' field with 'text'"
      },
      {
        "name": "select",
        "signature": "(option: str, target: str) -> bool",
        "returns": "True on success, False on failure",
        "description": "Select an option from a dropdown. Falls back to click for non-<select> elements.",
        "dslEquivalent": "Select 'option' from the 'target' dropdown"
      },
      {
        "name": "hover",
        "signature": "(target: str) -> bool",
        "returns": "True on success, False on failure",
        "dslEquivalent": "HOVER over the 'target'"
      },
      {
        "name": "drag",
        "signature": "(source: str, destination: str) -> bool",
        "returns": "True on success, False on failure",
        "dslEquivalent": "Drag the element 'source' and drop it into 'destination'"
      },
      {
        "name": "right_click",
        "signature": "(target: str) -> bool",
        "returns": "True on success, False on failure",
        "dslEquivalent": "RIGHT CLICK 'target'"
      },
      {
        "name": "press",
        "signature": "(key: str, target: str | None = None) -> bool",
        "returns": "True on success, False on failure",
        "description": "Press a key globally (target=None) or on a specific resolved element.",
        "dslEquivalent": "PRESS key / PRESS key on 'target'"
      },
      {
        "name": "upload",
        "signature": "(file_path: str, target: str) -> bool",
        "returns": "True on success, False on failure",
        "dslEquivalent": "UPLOAD 'file_path' to 'target'"
      },
      {
        "name": "scroll",
        "signature": "(target: str | None = None) -> None",
        "description": "Scroll main page (target=None) or a specific container.",
        "dslEquivalent": "SCROLL DOWN / SCROLL DOWN inside the 'target'"
      }
    ],

    "assertions": [
      {
        "name": "verify",
        "signature": "(target: str, *, present: bool = True, enabled: bool | None = None, checked: bool | None = None) -> bool",
        "returns": "True if assertion passes, False otherwise",
        "description": "Assert element state: presence, enabled/disabled, checked/unchecked.",
        "dslEquivalent": "VERIFY that 'target' is present / is NOT present / is ENABLED / is DISABLED / is checked / is NOT checked"
      }
    ],

    "extraction": [
      {
        "name": "extract",
        "signature": "(target: str, variable: str | None = None) -> str | None",
        "returns": "Extracted text, or None on failure",
        "description": "Extract visible text from an element. Optionally stores in memory under variable name.",
        "dslEquivalent": "EXTRACT the 'target' into {variable}"
      }
    ],

    "timing": [
      {
        "name": "wait",
        "signature": "(seconds: float) -> None",
        "description": "Hard sleep for N seconds.",
        "dslEquivalent": "WAIT N"
      }
    ],

    "dslExecution": [
      {
        "name": "run_steps",
        "signature": "(steps: str, context: str = '') -> MissionResult",
        "returns": "MissionResult with status, steps, blocks, error, soft_errors",
        "description": "Execute raw DSL multi-line steps against the current open page. Reuses browser session (no launch/teardown). Does NOT apply CLI features (retries, auto-screenshots, HTML report).",
        "behavior": [
          "Strips comments (#), metadata (@*), hook blocks ([SETUP]/[TEARDOWN])",
          "Detects format: STEP-grouped, numbered, or plain action keywords",
          "Parses into HuntBlocks via parse_hunt_blocks()",
          "Routes each action through the full engine pipeline"
        ],
        "returnShape": {
          "file": "'' (empty string)",
          "name": "'<api>'",
          "status": "pass | fail | warning",
          "steps": "list[StepResult]",
          "blocks": "list[BlockResult]",
          "soft_errors": "list[str]"
        }
      }
    ]
  },

  "internalRouting": "Each method generates a synthetic DSL step string internally and calls the appropriate ManulEngine._execute_step / _handle_* handler — the same code path used by .hunt file execution.",

  "usageExamples": {
    "purePython": [
      "async with ManulSession(headless=True) as session:",
      "    await session.navigate('https://example.com/login')",
      "    await session.fill('Username field', 'admin')",
      "    await session.fill('Password field', 'secret')",
      "    await session.click('Log in button')",
      "    await session.verify('Welcome')",
      "    price = await session.extract('Product Price')"
    ],
    "mixedDSL": [
      "async with ManulSession() as session:",
      "    await session.navigate('https://example.com')",
      "    result = await session.run_steps(\"\"\"",
      "        STEP 1: Search",
      "            Fill 'Search' with 'ManulEngine'",
      "            PRESS Enter",
      "            VERIFY that 'Results' is present",
      "    \"\"\")",
      "    assert result.status == 'pass'"
    ]
  }
}
```
