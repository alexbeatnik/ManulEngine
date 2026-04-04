# ManulEngine — CLI Contract

> **Machine-readable contract for the `manul` CLI interface.**
> Consumed by Manul Studio, VS Code extension, CI/CD integrations, and other downstream tooling.

```json
{
  "version": "0.0.9.21",
  "generatedFrom": "manul_engine/cli.py :: main(), _run_hunt_file(), parse_hunt_file(), sync_main(); manul_engine/prompts.py :: _KEY_MAP, global config constants; manul_engine/scanner.py :: scan_main(); manul_engine/recorder.py :: record_main(); manul_engine/scheduler.py :: daemon_main()",
  "entryPoints": {
    "console_script": "manul",
    "module": "python -m manul_engine",
    "devCli": "python manul.py"
  },
  "subcommands": [
    {
      "id": "run",
      "syntax": "manul <path>",
      "description": "Run .hunt files. Accepts a single .hunt file, a directory of .hunt files, or '.' for CWD.",
      "positionalArgs": [
        {
          "name": "path",
          "required": true,
          "description": "Path to a .hunt file, a directory containing .hunt files, or '.' for the current directory."
        }
      ],
      "isDefault": true
    },
    {
      "id": "scan",
      "syntax": "manul scan <URL> [--output <file>]",
      "description": "Scan a URL for interactive elements and generate a draft .hunt file.",
      "positionalArgs": [
        {
          "name": "url",
          "required": true,
          "description": "URL to scan for interactive elements."
        }
      ],
      "specificFlags": ["--output"]
    },
    {
      "id": "record",
      "syntax": "manul record <URL> [output_file]",
      "description": "Record browser interactions and generate a .hunt file.",
      "positionalArgs": [
        {
          "name": "url",
          "required": true,
          "description": "URL to open for recording."
        },
        {
          "name": "output_file",
          "required": false,
          "default": "tests/recorded_mission.hunt",
          "description": "Output file path for the recorded hunt."
        }
      ],
      "specificFlags": ["--output", "--browser"]
    },
    {
      "id": "daemon",
      "syntax": "manul daemon <directory>",
      "description": "Run scheduled .hunt files (those with @schedule: headers) as a long-running daemon.",
      "positionalArgs": [
        {
          "name": "directory",
          "required": true,
          "description": "Directory to scan for scheduled .hunt files."
        }
      ],
      "specificFlags": ["--headless", "--browser", "--screenshot"]
    },
    {
      "id": "test",
      "syntax": "python manul.py test",
      "description": "Dev-only: runs the synthetic DOM test suite. Only available via the dev CLI entry point (manul.py), not the installed console_scripts command.",
      "devOnly": true
    }
  ],
  "flags": [
    {
      "id": "headless",
      "flag": "--headless",
      "type": "boolean",
      "default": false,
      "configKey": "headless",
      "envVar": "MANUL_HEADLESS",
      "description": "Run browser in headless mode.",
      "appliesTo": ["run", "scan", "record", "daemon"]
    },
    {
      "id": "browser",
      "flag": "--browser",
      "type": "string",
      "default": "chromium",
      "configKey": "browser",
      "envVar": "MANUL_BROWSER",
      "allowedValues": ["chromium", "firefox", "webkit"],
      "description": "Browser engine to use.",
      "appliesTo": ["run", "scan", "record", "daemon"]
    },
    {
      "id": "workers",
      "flag": "--workers",
      "type": "integer",
      "default": 1,
      "minimum": 1,
      "configKey": "workers",
      "envVar": "MANUL_WORKERS",
      "description": "Max hunt files to run in parallel. Each worker spawns a separate subprocess with its own browser instance. Forced to 1 when --debug or --break-lines is active.",
      "appliesTo": ["run"]
    },
    {
      "id": "tags",
      "flag": "--tags",
      "type": "string",
      "default": null,
      "description": "Comma-separated tag filter. Only run .hunt files whose @tags: header contains at least one matching tag.",
      "example": "--tags smoke,regression",
      "appliesTo": ["run"]
    },
    {
      "id": "debug",
      "flag": "--debug",
      "type": "boolean",
      "default": false,
      "description": "Interactive step-by-step mode with visual element highlighting. Pauses before every step. Forces --workers 1. Mutually exclusive with --break-lines in practice.",
      "appliesTo": ["run"]
    },
    {
      "id": "break_lines",
      "flag": "--break-lines",
      "type": "string",
      "default": null,
      "description": "Comma-separated list of .hunt file line numbers to pause at. Used by the VS Code extension gutter breakpoint runner. Forces --workers 1.",
      "example": "--break-lines 5,10,15",
      "appliesTo": ["run"]
    },
    {
      "id": "retries",
      "flag": "--retries",
      "type": "integer",
      "default": 0,
      "minimum": 0,
      "configKey": "retries",
      "envVar": "MANUL_RETRIES",
      "description": "Retry failed hunt files up to N times. Pass on retry marks the result as 'flaky'.",
      "appliesTo": ["run"]
    },
    {
      "id": "screenshot",
      "flag": "--screenshot",
      "type": "string",
      "default": "on-fail",
      "configKey": "screenshot",
      "envVar": "MANUL_SCREENSHOT",
      "allowedValues": ["on-fail", "always", "none"],
      "description": "Screenshot capture mode. Screenshots are stored as base64 PNGs in step results and the HTML report.",
      "appliesTo": ["run", "daemon"]
    },
    {
      "id": "html_report",
      "flag": "--html-report",
      "type": "boolean",
      "default": false,
      "configKey": "html_report",
      "envVar": "MANUL_HTML_REPORT",
      "description": "Generate a self-contained HTML report after the run (reports/manul_report.html). Recent invocations within the same report session are merged.",
      "appliesTo": ["run"]
    },
    {
      "id": "explain",
      "flag": "--explain",
      "type": "boolean",
      "default": false,
      "configKey": "explain_mode",
      "envVar": "MANUL_EXPLAIN",
      "description": "Print detailed heuristic score breakdown for each element resolution.",
      "appliesTo": ["run"]
    },
    {
      "id": "executable_path",
      "flag": "--executable-path",
      "type": "string",
      "default": null,
      "configKey": "executable_path",
      "envVar": "MANUL_EXECUTABLE_PATH",
      "description": "Absolute path to a custom browser or Electron app executable. Use with OPEN APP command in .hunt files for desktop automation.",
      "appliesTo": ["run"]
    },
    {
      "id": "output",
      "flag": "--output",
      "type": "string",
      "default": null,
      "description": "Output file path for scan and record subcommands.",
      "appliesTo": ["scan", "record"]
    },
    {
      "id": "help",
      "flag": "--help",
      "aliases": ["-h"],
      "type": "boolean",
      "description": "Print usage information and exit.",
      "appliesTo": ["run", "scan", "record", "daemon"]
    }
  ],
  "configPriority": [
    "CLI flag (highest)",
    "Environment variable (MANUL_*)",
    "manul_engine_configuration.json",
    "Built-in default (lowest)"
  ],
  "configFile": {
    "filename": "manul_engine_configuration.json",
    "resolution": "CWD first, then package root fallback",
    "overrideSetting": "manulEngine.configFile (VS Code extension setting)",
    "keys": [
      { "key": "model",                  "envVar": "MANUL_MODEL",                  "type": "string | null", "default": "null" },
      { "key": "headless",               "envVar": "MANUL_HEADLESS",               "type": "boolean",       "default": "false" },
      { "key": "browser",                "envVar": "MANUL_BROWSER",                "type": "string",        "default": "chromium" },
      { "key": "browser_args",           "envVar": "MANUL_BROWSER_ARGS",           "type": "string[]",      "default": "[]" },
      { "key": "timeout",                "envVar": "MANUL_TIMEOUT",                "type": "integer",       "default": "5000" },
      { "key": "nav_timeout",            "envVar": "MANUL_NAV_TIMEOUT",            "type": "integer",       "default": "30000" },
      { "key": "ai_threshold",           "envVar": "MANUL_AI_THRESHOLD",           "type": "integer | null","default": "auto" },
      { "key": "ai_always",              "envVar": "MANUL_AI_ALWAYS",              "type": "boolean",       "default": "false" },
      { "key": "ai_policy",              "envVar": "MANUL_AI_POLICY",              "type": "string",        "default": "prior" },
      { "key": "controls_cache_enabled", "envVar": "MANUL_CONTROLS_CACHE_ENABLED", "type": "boolean",       "default": "true" },
      { "key": "controls_cache_dir",     "envVar": "MANUL_CONTROLS_CACHE_DIR",     "type": "string",        "default": "cache" },
      { "key": "semantic_cache_enabled",  "envVar": "MANUL_SEMANTIC_CACHE_ENABLED", "type": "boolean",       "default": "true" },
      { "key": "custom_controls_dirs",   "envVar": "MANUL_CUSTOM_CONTROLS_DIRS",   "type": "string[]",      "default": "[\"controls\"]" },
      { "key": "log_name_maxlen",        "envVar": "MANUL_LOG_NAME_MAXLEN",        "type": "integer",       "default": "0" },
      { "key": "log_thought_maxlen",     "envVar": "MANUL_LOG_THOUGHT_MAXLEN",     "type": "integer",       "default": "0" },
      { "key": "workers",                "envVar": "MANUL_WORKERS",                "type": "integer",       "default": "1" },
      { "key": "tests_home",             "envVar": null,                           "type": "string",        "default": "tests" },
      { "key": "auto_annotate",          "envVar": "MANUL_AUTO_ANNOTATE",          "type": "boolean",       "default": "false" },
      { "key": "channel",                "envVar": "MANUL_CHANNEL",                "type": "string | null", "default": "null" },
      { "key": "executable_path",        "envVar": "MANUL_EXECUTABLE_PATH",        "type": "string | null", "default": "null" },
      { "key": "retries",                "envVar": "MANUL_RETRIES",                "type": "integer",       "default": "0" },
      { "key": "screenshot",             "envVar": "MANUL_SCREENSHOT",             "type": "string",        "default": "on-fail" },
      { "key": "html_report",            "envVar": "MANUL_HTML_REPORT",            "type": "boolean",       "default": "false" },
      { "key": "explain_mode",           "envVar": "MANUL_EXPLAIN",                "type": "boolean",       "default": "false" }
    ]
  },
  "exitCodes": {
    "0": "All hunts passed (includes flaky and warning statuses)",
    "1": "One or more hunts failed or are broken"
  },
  "outputArtifacts": [
    {
      "id": "log",
      "path": "reports/last_run.log",
      "description": "Full stdout log of the most recent run. Overwritten on each invocation.",
      "alwaysGenerated": true
    },
    {
      "id": "run_history",
      "path": "reports/run_history.json",
      "format": "JSON Lines",
      "description": "Append-only history of all mission results. Each line is a JSON object with file, name, timestamp, status, duration_ms.",
      "alwaysGenerated": true
    },
    {
      "id": "html_report",
      "path": "reports/manul_report.html",
      "description": "Self-contained dark-themed HTML report with dashboard stats, accordions, screenshots, tag filters, and merged session history.",
      "alwaysGenerated": false,
      "trigger": "--html-report flag or html_report config key"
    },
    {
      "id": "report_state",
      "path": "reports/manul_report_state.json",
      "description": "Persisted report session state for cross-invocation HTML report merging. TTL controlled by MANUL_REPORT_SESSION_TTL_SEC (default: 1800s).",
      "alwaysGenerated": false,
      "trigger": "--html-report flag"
    }
  ],
  "missionStatuses": [
    {
      "id": "pass",
      "label": "PASS",
      "icon": "✅",
      "description": "All steps succeeded on the first attempt.",
      "exitCode": 0
    },
    {
      "id": "fail",
      "label": "FAIL",
      "icon": "❌",
      "description": "One or more steps failed and all retries (if any) also failed.",
      "exitCode": 1
    },
    {
      "id": "broken",
      "label": "BROKEN",
      "icon": "💥",
      "description": "The [SETUP] hook failed before any browser step ran, or @before_all / @before_group failed.",
      "exitCode": 1
    },
    {
      "id": "flaky",
      "label": "FLAKY",
      "icon": "⚠️",
      "description": "Failed on first attempt but passed on a retry. Counted as passed for exit code purposes.",
      "exitCode": 0
    },
    {
      "id": "warning",
      "label": "WARNING",
      "icon": "⚠️",
      "description": "All steps passed but one or more VERIFY SOFTLY assertions failed. Counted as passed for exit code.",
      "exitCode": 0
    }
  ],
  "parallelModel": {
    "mechanism": "Subprocess per hunt file via asyncio.create_subprocess_exec",
    "command": "[sys.executable, '-m', 'manul_engine', '--workers', '1', ...flags, hunt_file]",
    "concurrency": "asyncio.Semaphore(workers)",
    "timeout": "600s default (configurable via MANUL_WORKER_TIMEOUT env var)",
    "stdout": "Captured per worker, printed in submission order after all complete",
    "htmlReport": "Parent generates consolidated report; --html-report is NOT forwarded to children",
    "runHistory": "Children write their own run_history.json entries; parent skips to avoid duplicates",
    "globalVars": "Serialised via MANUL_GLOBAL_VARS env var so workers inherit @before_all context",
    "restrictions": [
      "--debug and --break-lines force --workers 1 (sequential)",
      "Lifecycle hooks run independently per worker — not once-per-suite"
    ]
  },
  "parsedHuntFile": {
    "type": "ParsedHunt (NamedTuple, 10 fields)",
    "fields": [
      { "name": "mission",         "type": "str",            "description": "Concatenated mission body (non-header, non-hook, non-comment lines)" },
      { "name": "context",         "type": "str",            "description": "@context: value" },
      { "name": "title",           "type": "str",            "description": "@title: value (or @blueprint:)" },
      { "name": "step_file_lines", "type": "list[int]",      "description": "1-based file line numbers for each mission line, for breakpoint mapping" },
      { "name": "setup_lines",     "type": "list[str]",      "description": "Extracted [SETUP] block instruction strings" },
      { "name": "teardown_lines",  "type": "list[str]",      "description": "Extracted [TEARDOWN] block instruction strings" },
      { "name": "parsed_vars",     "type": "dict[str, str]", "description": "Key/value pairs from @var: headers (keys stored without braces)" },
      { "name": "tags",            "type": "list[str]",      "description": "Tags from @tags: header (empty list if absent)" },
      { "name": "data_file",       "type": "str",            "description": "@data: file path (empty string if absent)" },
      { "name": "schedule",        "type": "str",            "description": "@schedule: expression (empty string if absent)" }
    ],
    "scriptAliasRewriting": "@script: aliases are resolved and rewritten to real dotted paths in mission lines and hook lines before returning"
  },
  "debugProtocol": {
    "description": "Stdin/stdout protocol between the CLI runner and VS Code extension for gutter breakpoint debugging.",
    "pauseMarker": "\\x00MANUL_DEBUG_PAUSE\\x00{\"step\":\"...\",\"idx\":N}\\n",
    "stdinCommands": [
      { "command": "next\\n",       "effect": "Advance one step then pause again" },
      { "command": "continue\\n",   "effect": "Run until the next gutter breakpoint or end" },
      { "command": "debug-stop\\n", "effect": "Clear all breakpoints; run to completion without pausing" },
      { "command": "abort\\n",      "effect": "Force-kill the process (extension sends this + kills after 500ms)" },
      { "command": "explain\\n",    "effect": "Trigger DOMScorer explain output for the current step" }
    ],
    "ttyDetection": "_Tee.isatty() delegates to the underlying terminal so --debug TTY prompts work correctly even when stdout is tee'd to a log file"
  }
}
```
