# ManulEngine — Reporting Contract

> **Machine-readable contract for the ManulEngine reporting and result pipeline.**
> Consumed by HTML report generator, VS Code extension Test Explorer, CI/CD integrations, and downstream analytics.

```json
{
  "version": "0.0.9.27",
  "generatedFrom": "manul_engine/reporting.py :: StepResult, BlockResult, MissionResult, RunSummary, append_run_history(), load_report_state(), save_report_state(), merge_report_summaries(), recompute_summary(); manul_engine/reporter.py :: generate_report()",

  "statusValues": {
    "step": ["pass", "fail", "skip", "warning"],
    "block": ["pass", "fail", "warning"],
    "mission": ["pass", "fail", "broken", "flaky", "warning"],
    "note": "'broken' = [SETUP] hook failed (browser never launched). 'flaky' = failed initially but passed on retry. 'warning' = VERIFY SOFTLY failures collected."
  },

  "dataclasses": {
    "StepResult": {
      "module": "manul_engine/reporting.py",
      "fields": [
        { "name": "index",        "type": "int",            "default": null, "required": true,  "description": "1-based step number within the mission." },
        { "name": "text",         "type": "str",            "default": null, "required": true,  "description": "Step text after variable substitution." },
        { "name": "status",       "type": "str",            "default": "pass",                   "description": "One of: pass, fail, skip, warning." },
        { "name": "duration_ms",  "type": "float",          "default": 0.0,                      "description": "Execution time in milliseconds." },
        { "name": "error",        "type": "str | null",     "default": null,                     "description": "Error message or traceback on failure." },
        { "name": "screenshot",   "type": "str | null",     "default": null,                     "description": "Base64-encoded PNG screenshot (controlled by screenshot_mode)." },
        { "name": "logical_step", "type": "str | null",     "default": null,                     "description": "Active STEP label when this action ran (e.g. 'STEP 2: Login')." },
        { "name": "healed",       "type": "bool",           "default": false,                    "description": "True when a stale cache entry was re-resolved via self-healing." }
      ]
    },

    "BlockResult": {
      "module": "manul_engine/reporting.py",
      "fields": [
        { "name": "name",        "type": "str",                  "default": null, "required": true,  "description": "STEP label (e.g. 'STEP 2: Login')." },
        { "name": "status",      "type": "str",                  "default": "pass",                   "description": "One of: pass, fail, warning." },
        { "name": "duration_ms", "type": "float",                "default": 0.0,                      "description": "Total duration of all child actions." },
        { "name": "error",       "type": "str | null",           "default": null,                     "description": "First error encountered in block." },
        { "name": "actions",     "type": "list[StepResult]",     "default": [],                       "description": "Ordered child actions within this block." }
      ]
    },

    "MissionResult": {
      "module": "manul_engine/reporting.py",
      "fields": [
        { "name": "file",        "type": "str",                  "default": null, "required": true,  "description": "Absolute path to the .hunt file." },
        { "name": "name",        "type": "str",                  "default": null, "required": true,  "description": "File basename (e.g. 'saucedemo.hunt')." },
        { "name": "status",      "type": "str",                  "default": "pass",                   "description": "One of: pass, fail, broken, flaky, warning." },
        { "name": "attempts",    "type": "int",                  "default": 1,                        "description": "Total attempts including initial run + retries." },
        { "name": "duration_ms", "type": "float",                "default": 0.0,                      "description": "Wall-clock ms for all attempts." },
        { "name": "error",       "type": "str | null",           "default": null,                     "description": "Last error message when status is fail/broken." },
        { "name": "steps",       "type": "list[StepResult]",     "default": [],                       "description": "Flat ordered list of all executed step results." },
        { "name": "blocks",      "type": "list[BlockResult]",    "default": [],                       "description": "Hierarchical block grouping (STEP-based)." },
        { "name": "tags",        "type": "list[str]",            "default": [],                       "description": "Tags from @tags: header in the .hunt file." },
        { "name": "soft_errors", "type": "list[str]",            "default": [],                       "description": "Collected VERIFY SOFTLY failure messages." }
      ],
      "specialMethods": {
        "__bool__": "Returns True when status is NOT in ('fail', 'broken'). Truthy = usable result."
      }
    },

    "RunSummary": {
      "module": "manul_engine/reporting.py",
      "fields": [
        { "name": "session_id",       "type": "str",                  "default": "<ISO timestamp>_<PID>",  "description": "Unique session identifier for report merging." },
        { "name": "invocation_count", "type": "int",                  "default": 1,                         "description": "Number of CLI invocations merged in this session." },
        { "name": "started_at",       "type": "str",                  "default": "",                        "description": "ISO-8601 start timestamp." },
        { "name": "ended_at",         "type": "str",                  "default": "",                        "description": "ISO-8601 end timestamp." },
        { "name": "total",            "type": "int",                  "default": 0,                         "description": "Total number of missions." },
        { "name": "passed",           "type": "int",                  "default": 0,                         "description": "Missions with status 'pass'." },
        { "name": "failed",           "type": "int",                  "default": 0,                         "description": "Missions with status 'fail'." },
        { "name": "broken",           "type": "int",                  "default": 0,                         "description": "Missions with status 'broken'." },
        { "name": "flaky",            "type": "int",                  "default": 0,                         "description": "Missions with status 'flaky'." },
        { "name": "warning",          "type": "int",                  "default": 0,                         "description": "Missions with status 'warning'." },
        { "name": "duration_ms",      "type": "float",                "default": 0.0,                      "description": "Total wall-clock duration." },
        { "name": "missions",         "type": "list[MissionResult]",  "default": [],                       "description": "All mission results in execution order." }
      ]
    }
  },

  "persistenceLayer": {
    "runHistory": {
      "file": "reports/run_history.json",
      "format": "JSON Lines (one JSON object per line, newline-delimited)",
      "writeMethod": "os.open(..., O_APPEND | O_CREAT | O_WRONLY) for concurrent-safe appends",
      "schema": {
        "file":        "str — absolute path to .hunt file",
        "name":        "str — file basename",
        "timestamp":   "str — ISO-8601 datetime",
        "status":      "str — pass | fail | broken | flaky | warning",
        "duration_ms": "float — rounded to 1 decimal"
      },
      "appendedBy": [
        "cli.py — sequential and parallel execution paths",
        "cli.py — failure/retry paths",
        "scheduler.py — _run_scheduled_job()"
      ]
    },

    "reportState": {
      "file": "reports/manul_report_state.json",
      "format": "JSON — full RunSummary as dict",
      "purpose": "Cross-invocation session merging. Repeated CLI or VS Code Test Explorer runs merge into the same HTML report instead of overwriting.",
      "ttl": {
        "default": 1800,
        "envVar": "MANUL_REPORT_SESSION_TTL_SEC",
        "unit": "seconds",
        "behavior": "Sessions older than TTL are discarded; a fresh session starts."
      }
    },

    "htmlReport": {
      "file": "reports/manul_report.html",
      "generator": "reporter.py :: generate_report(summary, output_path)",
      "features": [
        "Self-contained dark-themed HTML (no external dependencies)",
        "Dashboard stats header (total/passed/failed/broken/flaky/warning)",
        "Native <details>/<summary> accordions (collapsed by default, auto-expanded on failure)",
        "Flexbox step layout with step-level status indicators",
        "Inline base64 screenshots",
        "Control panel: 'Show Only Failed' checkbox toggle",
        "Tag filter chips (dynamically collected from all missions' tags)",
        "Run Session / Merged invocations banner",
        "data-status and data-tags attributes on mission divs for JS filtering"
      ]
    },

    "outputDirectory": {
      "path": "reports/",
      "autoCreated": true,
      "gitignored": true
    }
  },

  "functions": {
    "recompute_summary": {
      "signature": "(summary: RunSummary) -> RunSummary",
      "description": "Recalculates aggregate counters (total, passed, failed, etc.) from the missions list. Normalizes the summary in-place and returns it."
    },
    "load_report_state": {
      "signature": "(max_age_seconds: int | None = None) -> RunSummary | None",
      "description": "Loads report state from reports/manul_report_state.json. Returns None if file is missing, stale (exceeds TTL), or malformed."
    },
    "save_report_state": {
      "signature": "(summary: RunSummary) -> str",
      "description": "Writes normalised RunSummary to reports/manul_report_state.json. Creates directory if needed. Returns file path."
    },
    "merge_report_summaries": {
      "signature": "(existing: RunSummary | None, current: RunSummary) -> RunSummary",
      "description": "Merges existing session state with current run results. Replaces duplicate files by name. Preserves session_id from existing when present."
    },
    "append_run_history": {
      "signature": "(mission: MissionResult) -> None",
      "description": "Appends a single JSON Line to reports/run_history.json using O_APPEND for concurrent-safe writes."
    },
    "generate_report": {
      "signature": "(summary: RunSummary, output_path: str) -> None",
      "description": "Writes self-contained HTML report to output_path. Uses RunSummary with all MissionResult/BlockResult/StepResult data."
    }
  }
}
```
