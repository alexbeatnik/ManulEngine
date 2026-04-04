# ManulEngine — Configuration Contract

> **Machine-readable contract for the ManulEngine configuration surface.**
> Consumed by VS Code extension config panel, Manul Studio, CI/CD integrations, and downstream tooling.

```json
{
  "version": "0.0.9.22",
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
      "key": "model",
      "envVar": "MANUL_MODEL",
      "type": "string | null",
      "default": null,
      "description": "Ollama model name for LLM fallback. null = heuristics-only mode (AI fully disabled, threshold forced to 0). No Ollama dependency needed when null.",
      "examples": [null, "qwen2.5:0.5b", "llama3.2:1b"],
      "validation": "Free-form string or null. Model must be pulled locally via `ollama pull <model>` before use."
    },
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
      "allowedValues": ["chromium", "firefox", "webkit", "electron"],
      "description": "Playwright browser engine. `electron` is a legacy/runtime-config-only value still accepted via JSON config or MANUL_BROWSER for CDP/Electron compatibility, but the CLI `--browser` flag remains limited to `chromium`, `firefox`, or `webkit`. For Electron/desktop automation, prefer `executable_path` with the OPEN APP command.",
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
      "description": "Playwright browser channel — use an installed browser instead of the bundled one.",
      "examples": [null, "chrome", "chrome-beta", "msedge"],
      "validation": "Must be a valid Playwright channel identifier or null."
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
      "key": "ai_threshold",
      "envVar": "MANUL_AI_THRESHOLD",
      "type": "integer | null",
      "default": null,
      "description": "Score threshold (scaled integer) below which the LLM fallback is triggered. null = auto-derive from model size. Ignored when model is null.",
      "autoCalculation": {
        "function": "_threshold_for_model(model_name)",
        "rules": [
          { "modelSize": "null (no model)",      "threshold": 0 },
          { "modelSize": "< 1B parameters",      "threshold": 500 },
          { "modelSize": "1B – 4B parameters",   "threshold": 750 },
          { "modelSize": "5B – 9B parameters",   "threshold": 1000 },
          { "modelSize": "10B – 19B parameters",  "threshold": 1500 },
          { "modelSize": "20B+ parameters",       "threshold": 2000 }
        ],
        "sizeExtraction": "Regex on model name — extracts first number before 'b' (e.g., qwen2.5:0.5b → 0.5)"
      },
      "resolutionOrder": [
        "Explicit ManulEngine constructor parameter (custom_threshold)",
        "MANUL_AI_THRESHOLD env var or config key",
        "Auto-calculated from model name",
        "0 when model is null"
      ]
    },
    {
      "key": "ai_always",
      "envVar": "MANUL_AI_ALWAYS",
      "type": "boolean",
      "default": false,
      "description": "Force LLM picker for every element resolution (bypasses heuristic short-circuits). Has no effect and is forced to false when model is null.",
      "guard": "VS Code config panel forces false when model field is empty."
    },
    {
      "key": "ai_policy",
      "envVar": "MANUL_AI_POLICY",
      "type": "string",
      "default": "prior",
      "allowedValues": ["prior", "strict"],
      "description": "How to treat heuristic score in the LLM picker. 'prior' = score as a hint. 'strict' = force max-score element."
    },
    {
      "key": "controls_cache_enabled",
      "envVar": "MANUL_CONTROLS_CACHE_ENABLED",
      "type": "boolean",
      "default": true,
      "description": "Enable persistent per-site controls cache. File-based, survives between runs. Stored in controls_cache_dir.",
      "uiLabel": "Persistent Controls Cache"
    },
    {
      "key": "controls_cache_dir",
      "envVar": "MANUL_CONTROLS_CACHE_DIR",
      "type": "string",
      "default": "cache",
      "description": "Directory for persistent controls cache files. Relative to CWD or absolute path.",
      "structure": "cache/<site_hash>/<page_hash>/controls.json"
    },
    {
      "key": "semantic_cache_enabled",
      "envVar": "MANUL_SEMANTIC_CACHE_ENABLED",
      "type": "boolean",
      "default": true,
      "description": "Enable in-session semantic cache (learned_elements). Provides +200,000 scaled score boost within a single run. Resets when ManulEngine instance is destroyed.",
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
      "description": "If > 0, truncates LLM 'thought' strings in console log output.",
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
    "filename": "pages.json",
    "format": "JSON — nested per-site",
    "resolution": [
      "CWD (./pages.json) — writable, auto-created if absent",
      "Package root fallback — read-only"
    ],
    "schema": {
      "<site_root_url>": {
        "Domain": "<display_name>",
        "<regex_or_exact_url>": "<page_name>"
      }
    },
    "example": {
      "https://example.com/": {
        "Domain": "Example Site",
        ".*/login": "Login Page",
        "https://example.com/dashboard": "Dashboard"
      }
    },
    "lookupFunction": "lookup_page_name(url: str) -> str",
    "lookupBehavior": [
      "Re-reads from disk on every call (live edits picked up instantly)",
      "Finds best-matching site block (longest-prefix wins)",
      "Within site block: exact URL → regex/substring patterns (skipping 'Domain' key) → 'Domain' fallback",
      "Auto-populates new URLs with placeholder 'Auto: domain/path'"
    ]
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
