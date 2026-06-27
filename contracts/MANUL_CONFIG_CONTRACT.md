# ManulEngine — Configuration Contract

> **Machine-readable contract for the ManulEngine configuration surface.**
> Consumed by VS Code extension config panel, Manul Studio, CI/CD integrations, and downstream tooling.

```json
{
  "version": "0.1.0",
  "generatedFrom": "manul_engine/prompts.py :: _KEY_MAP, _CFG, get_threshold(), lookup_page_name(); manul_engine/variables.py :: ScopedVariables; manul_engine/helpers.py :: env_bool()",

  "configFile": {
    "filename": "manul_engine_configuration.json",
    "format": "JSON",
    "resolution": [
      "CWD (./manul_engine_configuration.json)",
      "Package root fallback (manul_engine/ directory)"
    ],
    "vscodeOverride": "manulEngine.configFile (VS Code extension setting via getConfigFileName())"
  },

  "priority": [
    "Environment variable MANUL_* (highest)",
    "JSON config file key",
    "Built-in default (lowest)"
  ],

  "booleanParsing": {
    "function": "env_bool(name, default)",
    "truthy": ["true", "1", "yes"],
    "falsy": "everything else",
    "caseInsensitive": true,
    "stripsWhitespace": true
  },

  "keys": [
    {
      "key": "headless",
      "envVar": "MANUL_HEADLESS",
      "type": "boolean",
      "default": false,
      "description": "Run browser in headless mode (no visible window).",
      "cliFlag": "--headless"
    },
    {
      "key": "browser",
      "envVar": "MANUL_BROWSER",
      "type": "string",
      "default": "chromium",
      "allowedValues": ["chromium", "electron"],
      "description": "Launch mode for the CDP backend, which always drives Chrome/Chromium. `chromium` launches a fresh system Chrome; `electron` attaches to an already-running Chrome/Electron over CDP (MANUL_CDP_PORT). Firefox/WebKit are no longer supported (CDP is Chromium-only). Use `channel`/`executable_path` to pick which Chrome binary to launch. Unknown values fall back to `chromium`.",
      "cliFlag": "--browser"
    },
    {
      "key": "browser_args",
      "envVar": "MANUL_BROWSER_ARGS",
      "type": "string[]",
      "default": [],
      "description": "Extra launch flags passed to the browser. JSON: native array. Env: comma-or-space-separated string.",
      "examples": [["--disable-gpu"], ["--window-size=1920,1080"]],
      "specialHandling": "List cannot round-trip via plain env string; env is split on comma/space."
    },
    {
      "key": "channel",
      "envVar": "MANUL_CHANNEL",
      "type": "string | null",
      "default": null,
      "description": "Chrome/Chromium channel — selects an installed browser binary (chrome, msedge, chromium, ...).",
      "examples": [null, "chrome", "chrome-beta", "msedge"],
      "validation": "Must be a valid Chrome channel identifier (chrome/chrome-beta/msedge/chromium/...) or null."
    },
    {
      "key": "executable_path",
      "envVar": "MANUL_EXECUTABLE_PATH",
      "type": "string | null",
      "default": null,
      "description": "Absolute path to a custom browser or Electron app executable. Used with OPEN APP command for desktop automation.",
      "cliFlag": "--executable-path"
    },
    {
      "key": "cdp_endpoint",
      "envVar": "MANUL_CDP_ENDPOINT",
      "type": "string | null",
      "default": null,
      "description": "Attach to an already-running browser at this CDP HTTP endpoint (e.g. http://127.0.0.1:9222) instead of launching a new Chrome. Mirrors ManulHeart's --cdp. When set, the engine connects via CDPBrowser.connect_over_cdp and drives the first existing page.",
      "cliFlag": "--cdp"
    },
    {
      "key": "timeout",
      "envVar": "MANUL_TIMEOUT",
      "type": "integer",
      "unit": "milliseconds",
      "default": 5000,
      "description": "Default action timeout for click, fill, select, hover operations.",
      "minimum": 0
    },
    {
      "key": "nav_timeout",
      "envVar": "MANUL_NAV_TIMEOUT",
      "type": "integer",
      "unit": "milliseconds",
      "default": 30000,
      "description": "Navigation timeout for NAVIGATE, page loads, and WAIT FOR RESPONSE.",
      "minimum": 0
    },
    {
      "key": "semantic_cache_enabled",
      "envVar": "MANUL_SEMANTIC_CACHE_ENABLED",
      "type": "boolean",
      "default": true,
      "description": "Enable in-session semantic cache (learned_elements). Feeds the scorer as one channel (never bypasses scoring); provides a +200,000 scaled score boost within a single run. Resets when the ManulEngine instance is destroyed.",
      "uiLabel": "Semantic Cache"
    },
    {
      "key": "custom_controls_dirs",
      "envVar": "MANUL_CUSTOM_CONTROLS_DIRS",
      "type": "string[]",
      "default": ["controls"],
      "description": "Directories scanned for @custom_control Python modules. Resolved relative to CWD. Env: comma-separated.",
      "legacyAlias": {
        "key": "custom_modules_dirs",
        "envVar": "MANUL_CUSTOM_MODULES_DIRS"
      }
    },
    {
      "key": "log_name_maxlen",
      "envVar": "MANUL_LOG_NAME_MAXLEN",
      "type": "integer",
      "default": 0,
      "description": "If > 0, truncates element names in console log output to this many characters.",
      "minimum": 0
    },
    {
      "key": "log_thought_maxlen",
      "envVar": "MANUL_LOG_THOUGHT_MAXLEN",
      "type": "integer",
      "default": 0,
      "description": "If > 0, truncates verbose 'thought'/diagnostic strings in console log output.",
      "minimum": 0
    },
    {
      "key": "workers",
      "envVar": "MANUL_WORKERS",
      "type": "integer",
      "default": 1,
      "minimum": 1,
      "description": "Max hunt files to run in parallel. Each worker spawns a separate subprocess with its own browser. Forced to 1 when --debug or --break-lines is active.",
      "cliFlag": "--workers"
    },
    {
      "key": "tests_home",
      "envVar": null,
      "type": "string",
      "default": "tests",
      "description": "Default directory for new hunt files, SCAN PAGE output, and manul scan default output. JSON-only — no env var override.",
      "note": "No MANUL_* env var for this key."
    },
    {
      "key": "auto_annotate",
      "envVar": "MANUL_AUTO_ANNOTATE",
      "type": "boolean",
      "default": false,
      "description": "Automatically inject '# 📍 Auto-Nav: <name>' comments into .hunt files whenever the page URL changes during a run. Page names from pages.json.",
      "uiLabel": "Auto-Annotate Page Navigation"
    },
    {
      "key": "retries",
      "envVar": "MANUL_RETRIES",
      "type": "integer",
      "default": 0,
      "minimum": 0,
      "description": "Number of times to retry a failed hunt file. Pass on retry marks status as 'flaky'.",
      "cliFlag": "--retries"
    },
    {
      "key": "screenshot",
      "envVar": "MANUL_SCREENSHOT",
      "type": "string",
      "default": "on-fail",
      "allowedValues": ["on-fail", "always", "none"],
      "description": "Screenshot capture mode. Screenshots stored as base64 PNGs in StepResult.screenshot and the HTML report.",
      "cliFlag": "--screenshot"
    },
    {
      "key": "html_report",
      "envVar": "MANUL_HTML_REPORT",
      "type": "boolean",
      "default": false,
      "description": "Generate self-contained HTML report after the run (reports/manul_report.html). Recent invocations merged via report session state.",
      "cliFlag": "--html-report"
    },
    {
      "key": "verify_max_retries",
      "envVar": "MANUL_VERIFY_MAX_RETRIES",
      "type": "integer",
      "default": 15,
      "minimum": 1,
      "description": "Maximum polling retries for VERIFY steps before declaring failure. Each retry waits ~1.0s for checked/enabled/disabled state verification and ~1.5s for text presence verification."
    },
    {
      "key": "explain_mode",
      "envVar": "MANUL_EXPLAIN",
      "type": "boolean",
      "default": false,
      "description": "Print detailed per-channel heuristic score breakdown for each element resolution.",
      "cliFlag": "--explain"
    }
  ],

  "pagesRegistry": {
    "directory": "<project>/pages/",
    "format": "One JSON fragment per site (file name = <safe_netloc>.json)",
    "resolution": [
      "CWD/pages/*.json — writable, directory auto-created if absent",
      "Override directory via MANUL_PAGES_DIR env var (absolute or CWD-relative)"
    ],
    "fragmentShapes": {
      "lean": {
        "description": "Preferred. site is the explicit site root; remaining keys are pattern→name mappings.",
        "example": {
          "site": "https://example.com/",
          "Domain": "Example Site",
          ".*/login": "Login Page",
          "https://example.com/dashboard": "Dashboard"
        }
      },
      "wrapped": {
        "description": "Back-compat shape mirroring the pre-0.0.9.30 nested form. The single top-level key is the site root.",
        "example": {
          "https://example.com/": {
            "Domain": "Example Site",
            ".*/login": "Login Page"
          }
        }
      }
    },
    "lookupFunction": "lookup_page_name(url: str) -> str",
    "lookupBehavior": [
      "Re-merges every pages/*.json fragment from disk on every call (live edits picked up instantly)",
      "Finds best-matching site block (longest-prefix wins across all fragments)",
      "Within site block: exact URL → regex/substring patterns (skipping 'Domain' key) → 'Domain' fallback",
      "Auto-populates new URLs by writing a per-site fragment pages/<safe_netloc>.json with placeholder 'Auto: domain/path'"
    ],
    "introspection": {
      "cli": "manul pages list",
      "description": "Print every site → pattern → label mapping discovered under pages/."
    },
    "migration": {
      "cli": "manul pages migrate",
      "description": "One-shot migration of a legacy pages.json (pre-0.0.9.30 monolithic file) into per-site fragments under pages/. Renames the original to pages.json.bak. The legacy flat file is no longer read by the engine."
    },
    "breakingChange": "0.0.9.30 — the monolithic pages.json file is no longer read or written by ManulEngine. Run `manul pages migrate` once to convert."
  },

  "scopedVariables": {
    "class": "ScopedVariables",
    "module": "manul_engine/variables.py",
    "levels": [
      {
        "id": "LEVEL_ROW",
        "priority": 1,
        "label": "row",
        "description": "Per-iteration variables from @data CSV/JSON rows. Cleared between data-driven iterations.",
        "populatedBy": "@data: file rows"
      },
      {
        "id": "LEVEL_STEP",
        "priority": 2,
        "label": "step",
        "description": "Runtime variables from EXTRACT, SET, and CALL PYTHON ... into {var}.",
        "populatedBy": "EXTRACT, SET, CALL PYTHON ... into {var}"
      },
      {
        "id": "LEVEL_MISSION",
        "priority": 3,
        "label": "mission",
        "description": "File-level @var: declarations and [SETUP] hook return values.",
        "populatedBy": "@var: headers, CALL PYTHON ... into {var} in [SETUP]"
      },
      {
        "id": "LEVEL_GLOBAL",
        "priority": 4,
        "label": "global",
        "description": "CLI/env context and @before_all lifecycle hook variables. Shared across all hunt files via MANUL_GLOBAL_VARS.",
        "populatedBy": "@before_all hooks, MANUL_GLOBAL_VARS env var"
      }
    ],
    "resolution": "Highest-priority level first (row → step → mission → global). First non-null match wins.",
    "substitution": "{placeholder} syntax in step text. resolve() + substitute() methods.",
    "dictCompat": true,
    "methods": [
      "resolve(name) -> str | None",
      "resolve_level(name) -> tuple[str | None, str | None]",
      "as_flat_dict() -> dict[str, str]",
      "substitute(text) -> str",
      "set(name, value, level)",
      "set_many(mapping, level)",
      "clear_level(level)",
      "clear_runtime()",
      "clear_all()",
      "dump() -> str"
    ]
  },

  "environmentVariables": {
    "description": "All MANUL_* env vars override the corresponding JSON config key. Additional runtime-only env vars:",
    "runtimeOnly": [
      {
        "var": "MANUL_GLOBAL_VARS",
        "type": "JSON string",
        "description": "Serialised GlobalContext.variables dict for passing @before_all results to parallel worker subprocesses."
      },
      {
        "var": "MANUL_WORKER_TIMEOUT",
        "type": "integer (seconds)",
        "default": 600,
        "description": "Subprocess worker timeout. Workers killed after this duration."
      },
      {
        "var": "MANUL_REPORT_SESSION_TTL_SEC",
        "type": "integer (seconds)",
        "default": 1800,
        "description": "TTL for HTML report session state merging. Older sessions start fresh."
      }
    ]
  }
}
```
