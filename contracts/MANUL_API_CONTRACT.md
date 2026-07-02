# ManulEngine — Python API Contract

> **Machine-readable contract for the ManulSession programmatic Python API.**
> Consumed by downstream Python integrations, pytest wrappers, RPA frameworks, and AI-agent harnesses.

```json
{
  "version": "0.1.0",
  "generatedFrom": "manul_engine/api.py :: ManulSession; manul_engine/__init__.py :: re-exports",

  "importPath": "from manul_engine import ManulSession",

  "class": "ManulSession",
  "description": "High-level async context manager for programmatic browser automation. Manages its own Chrome/CDP lifecycle. All element resolution routes through the deterministic ManulEngine heuristic scoring pipeline.",

  "constructor": {
    "parameters": [
      { "name": "headless",        "type": "bool | None",      "default": null,   "description": "Run browser headless. None = read from config." },
      { "name": "browser",         "type": "str | None",       "default": null,   "description": "'chromium' (launch) or 'electron' (attach over CDP). None = read from config." },
      { "name": "browser_args",    "type": "list[str] | None", "default": null,   "description": "Extra browser launch flags." },
      { "name": "disable_cache",   "type": "bool",             "default": false,  "description": "Disable the in-session semantic cache (learned_elements)." },
      { "name": "semantic_cache",  "type": "bool | None",      "default": null,   "description": "Enable in-session semantic cache. None = read from config." },
      { "name": "channel",         "type": "str | None",       "default": null,   "description": "Chrome/Chromium channel binary (e.g. 'chrome', 'msedge')." },
      { "name": "executable_path", "type": "str | None",       "default": null,   "description": "Custom browser or Electron executable path." }
    ]
  },

  "lifecycle": {
    "contextManager": {
      "usage": "async with ManulSession(...) as session: ...",
      "entry": "Calls start() — launches Chrome via CDP and opens the initial page.",
      "exit": "Calls close() — closes the page and the Chrome process."
    },
    "explicit": {
      "start": { "signature": "() -> ManulSession", "description": "Launch browser and open page. Returns self for chaining." },
      "close": { "signature": "() -> None", "description": "Close the page and the Chrome process." }
    }
  },

  "properties": [
    { "name": "page",   "type": "manul_engine.cdp.CDPPage",   "description": "Active CDPPage object. Useful for advanced one-off CDP calls (await page.query(...), page.evaluate(...))." },
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

  "customControls": {
    "importPath": "from manul_engine import ControlContext, custom_control, list_custom_controls",
    "decorator": {
      "signature": "@custom_control(page: str, target: str)",
      "description": "Register a function as the handler for (page, target). Page must match lookup_page_name(page.url). Target is matched case-insensitively against the quoted token in the .hunt step. Both sync and async handlers are accepted; the engine awaits async ones.",
      "handlerSignature": "(ctx: ControlContext) -> Any | Awaitable[Any]",
      "validation": "Decorator validates the signature at registration via inspect.signature(). Handlers with the legacy 3-argument shape (page, action_type, value) are rejected with TypeError; the message names ControlContext, the breaking version (0.0.9.30), and a one-line migration recipe."
    },
    "ControlContext": {
      "module": "manul_engine.controls",
      "kind": "dataclass(slots=True)",
      "fields": [
        { "name": "page",      "type": "manul_engine.cdp.CDPPage", "description": "Live CDPPage. Use await ctx.page.query(...), ctx.page.evaluate(...) etc." },
        { "name": "action",    "type": "str",                       "description": "DSL mode: 'input' | 'clickable' | 'select' | 'hover' | 'drag' | 'locate'." },
        { "name": "value",     "type": "str | None",                "description": "Type/select value. None for click/hover/locate." },
        { "name": "target",    "type": "str",                       "description": "Quoted target token from the step (preserves case)." },
        { "name": "page_name", "type": "str",                       "description": "Resolved pages.json label that matched @custom_control(page=…)." },
        { "name": "url",       "type": "str",                       "description": "page.url snapshot at dispatch time." },
        { "name": "step",      "type": "str",                       "description": "Original step text with {variables} substituted." }
      ]
    },
    "introspection": {
      "function": "list_custom_controls() -> list[dict[str, str]]",
      "description": "Returns one dict per registration: {page, target, handler, source}, sorted by (page.lower(), target.lower()). Empty list when nothing is registered."
    },
    "diagnostics": {
      "function": "diagnose_custom_control_miss(page_name, target_name) -> str | None",
      "description": "Returns a one-line hint when a step's target has a registered handler under a DIFFERENT page label (typical pages.json ↔ @custom_control(page=…) mismatch). Returns None when the target is unregistered or already matches the current page. Both run_mission() and _dispatch_step() print the hint just before falling through to heuristic resolution."
    }
  },


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
