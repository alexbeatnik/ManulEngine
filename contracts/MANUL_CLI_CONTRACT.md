# ManulEngine — CLI Contract

> **Machine-readable contract for the `manul` CLI interface.**
> Consumed by Manul Studio, VS Code extension, CI/CD integrations, and other downstream tooling.

```json
{
  "version": "0.1.0",
  "generatedFrom": "manul_engine/cli.py :: main(), _run_hunt_file(), parse_hunt_file(), sync_main(); manul_engine/prompts.py :: _KEY_MAP, global config constants; manul_engine/scanner.py :: scan_main(); manul_engine/recorder.py :: record_main(); manul_engine/scheduler.py :: daemon_main(); manul_engine/packager.py :: pack(), install()",
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
      "syntax": "python run_tests.py",
      "description": "Dev-only: runs the synthetic DOM test suite via run_tests.py. This workflow is not exposed through the installed console_scripts `manul` command.",
      "devOnly": true
    },
    {
      "id": "pack",
      "syntax": "manul pack <directory> [--output <dir>]",
      "description": "Pack a .hunt library directory into a distributable .huntlib archive. Requires a huntlib.json manifest with 'name' and 'version' fields.",
      "positionalArgs": [
        {
          "name": "directory",
          "required": true,
          "description": "Path to the library source directory containing huntlib.json and .hunt files."
        }
      ],
      "specificFlags": ["--output"]
    },
    {
      "id": "install",
      "syntax": "manul install <source> [--global]",
      "description": "Install a .huntlib archive or a directory into hunt_libs/ (local) or ~/.manul/hunt_libs/ (global).",
      "positionalArgs": [
        {
          "name": "source",
          "required": true,
          "description": "Path to a .huntlib archive file or a library directory containing huntlib.json."
        }
      ],
      "specificFlags": ["--global"]
    },
    {
      "id": "controls",
      "syntax": "manul controls list",
      "description": "List all @custom_control handlers discovered under the configured custom_controls_dirs (default: controls/) in the current working directory. Prints a fixed-width table with PAGE / TARGET / HANDLER / SOURCE columns. Eagerly imports every non-underscore .py file in each scan dir, then calls list_custom_controls().",
      "positionalArgs": [
        {
          "name": "subcommand",
          "required": false,
          "default": "list",
          "description": "Currently only 'list' is supported. Any other value exits 1."
        }
      ]
    },
    {
      "id": "pages",
      "syntax": "manul pages [list|migrate]",
      "description": "Inspect and migrate the per-site page registry. `list` prints every site → pattern → label mapping discovered under pages/. `migrate` splits a legacy pre-0.0.9.30 pages.json into pages/<safe_netloc>.json fragments and renames the original to pages.json.bak.",
      "positionalArgs": [
        {
          "name": "subcommand",
          "required": false,
          "default": "list",
          "description": "Either 'list' (default) or 'migrate'. Any other value exits 1."
        }
      ]
    },
    {
      "id": "schema",
      "syntax": "manul schema [--json]",
      "description": "Agent command. Emits the DSL grammar + agent JSON shapes (verbs, hunt_rules, step_outcome, page_map, failure_reasons, agent_commands) as a compact JSON contract for an external LLM driver. No browser needed; payload on stdout, logs on stderr. --json is accepted for symmetry (output is always JSON).",
      "positionalArgs": []
    },
    {
      "id": "map",
      "syntax": "manul map [--cdp <url>] [--tab <url-substr>] [--max-per-group <n>] [--include-unlabeled]",
      "description": "Agent command. Attaches to an already-running Chrome over CDP (default http://127.0.0.1:9222) and emits a compact, landmark-grouped JSON map of the open page ({url, groups:[{name, elements:[{label, role, editable?}], truncated?}]}), deduped and per-group capped (default 8). Groups are ordered Page → content landmarks → chrome.",
      "positionalArgs": []
    },
    {
      "id": "read",
      "syntax": "manul read '<label>' [--cdp <url>] [--tab <url-substr>] [--selector '<css>'] [--max-chars <n>]",
      "description": "Agent command. Attaches over CDP and reads off the open page without a full scan. Targeted form resolves a human label and extracts its value → {value, found, reason}. With --selector, returns the sanitized visible text of that CSS region → {text, selector}, optionally truncated to --max-chars.",
      "positionalArgs": [
        {
          "name": "label",
          "required": false,
          "description": "Human-visible label to read; omit when using --selector."
        }
      ]
    },
    {
      "id": "run-step",
      "syntax": "manul run-step '<instruction>' [--cdp <url>] [--tab <url-substr>] [--compact]",
      "description": "Agent command. Attaches over CDP and runs one plain-English DSL instruction against the open page, emitting a compact step-outcome JSON {ok, step, action, value?, url?, reason, error?, score?, near?}. Exit code is non-zero when ok is false. 'near' lists top candidates on failure or a low-confidence (<0.35) match.",
      "positionalArgs": [
        {
          "name": "instruction",
          "required": true,
          "description": "One DSL line, e.g. \"Click the 'Login' button\"."
        }
      ]
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
      "allowedValues": ["chromium", "electron"],
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
      "id": "json",
      "flag": "--json",
      "type": "boolean",
      "default": false,
      "configKey": null,
      "envVar": null,
      "description": "Print the final RunSummary as indented JSON to stdout; human logs are routed to stderr. Base64 screenshots are stripped. Mirrors ManulHeart's --json.",
      "appliesTo": ["run"]
    },
    {
      "id": "jsonl",
      "flag": "--jsonl",
      "type": "boolean",
      "default": false,
      "configKey": null,
      "envVar": null,
      "description": "Stream per-step JSON Lines (one object per step, type=step) followed by a final type=summary line to stdout; human logs are routed to stderr. Mirrors ManulHeart's --jsonl.",
      "appliesTo": ["run"]
    },
    {
      "id": "disable_cache",
      "flag": "--disable-cache",
      "type": "boolean",
      "default": false,
      "configKey": "semantic_cache_enabled",
      "envVar": "MANUL_SEMANTIC_CACHE_ENABLED",
      "description": "Disable the in-session semantic cache (learned_elements) for a fully cold, deterministic run. Mirrors ManulHeart's --disable-cache. Inverse of semantic_cache_enabled.",
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
      "id": "cdp_endpoint",
      "flag": "--cdp",
      "type": "string",
      "default": null,
      "configKey": "cdp_endpoint",
      "envVar": "MANUL_CDP_ENDPOINT",
      "description": "Attach to a running browser at this CDP HTTP endpoint (e.g. http://127.0.0.1:9222) instead of launching Chrome. Mirrors ManulHeart's --cdp.",
      "appliesTo": ["run"]
    },
    {
      "id": "target",
      "flag": "--target",
      "type": "string",
      "default": null,
      "configKey": null,
      "envVar": "MANUL_CDP_TAB",
      "description": "With --cdp, select the page whose URL contains the given substring (form: url=<substr>; the url= prefix is optional). Falls back to the first page. Mirrors ManulHeart's --target.",
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
      { "key": "headless",               "envVar": "MANUL_HEADLESS",               "type": "boolean",       "default": "false" },
      { "key": "browser",                "envVar": "MANUL_BROWSER",                "type": "string",        "default": "chromium" },
      { "key": "browser_args",           "envVar": "MANUL_BROWSER_ARGS",           "type": "string[]",      "default": "[]" },
      { "key": "timeout",                "envVar": "MANUL_TIMEOUT",                "type": "integer",       "default": "5000" },
      { "key": "nav_timeout",            "envVar": "MANUL_NAV_TIMEOUT",            "type": "integer",       "default": "30000" },
      { "key": "semantic_cache_enabled",  "envVar": "MANUL_SEMANTIC_CACHE_ENABLED", "type": "boolean",       "default": "true" },
      { "key": "custom_controls_dirs",   "envVar": "MANUL_CUSTOM_CONTROLS_DIRS",   "type": "string[]",      "default": "[\"controls\"]" },
      { "key": "log_name_maxlen",        "envVar": "MANUL_LOG_NAME_MAXLEN",        "type": "integer",       "default": "0" },
      { "key": "log_thought_maxlen",     "envVar": "MANUL_LOG_THOUGHT_MAXLEN",     "type": "integer",       "default": "0" },
      { "key": "workers",                "envVar": "MANUL_WORKERS",                "type": "integer",       "default": "1" },
      { "key": "tests_home",             "envVar": null,                           "type": "string",        "default": "tests" },
      { "key": "auto_annotate",          "envVar": "MANUL_AUTO_ANNOTATE",          "type": "boolean",       "default": "false" },
      { "key": "channel",                "envVar": "MANUL_CHANNEL",                "type": "string | null", "default": "null" },
      { "key": "executable_path",        "envVar": "MANUL_EXECUTABLE_PATH",        "type": "string | null", "default": "null" },
      { "key": "cdp_endpoint",           "envVar": "MANUL_CDP_ENDPOINT",           "type": "string | null", "default": "null" },
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
    "type": "ParsedHunt (NamedTuple, 12 fields)",
    "fields": [
      { "name": "mission",         "type": "str",                     "description": "Concatenated mission body (non-header, non-hook, non-comment lines). USE directives are expanded inline." },
      { "name": "context",         "type": "str",                     "description": "@context: value" },
      { "name": "title",           "type": "str",                     "description": "@title: value (or @blueprint:)" },
      { "name": "step_file_lines", "type": "list[int]",               "description": "1-based file line numbers for each mission line, for breakpoint mapping. Expanded USE actions get synthetic line 0." },
      { "name": "setup_lines",     "type": "list[str]",               "description": "Extracted [SETUP] block instruction strings" },
      { "name": "teardown_lines",  "type": "list[str]",               "description": "Extracted [TEARDOWN] block instruction strings" },
      { "name": "parsed_vars",     "type": "dict[str, str]",          "description": "Key/value pairs from @var: headers (keys stored without braces)" },
      { "name": "tags",            "type": "list[str]",               "description": "Tags from @tags: header (empty list if absent)" },
      { "name": "data_file",       "type": "str",                     "description": "@data: file path (empty string if absent)" },
      { "name": "schedule",        "type": "str",                     "description": "@schedule: expression (empty string if absent)" },
      { "name": "exports",         "type": "list[str]",               "description": "Block names from @export: headers (empty list if absent). ['*'] for wildcard export." },
      { "name": "imports",         "type": "list[ImportDirective]",   "description": "Parsed @import: directives (empty list if absent). Each has block_names, source, aliases." }
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
