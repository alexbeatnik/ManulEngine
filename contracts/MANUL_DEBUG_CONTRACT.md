# ManulEngine — Debug & What-If Analysis Contract

> **Machine-readable contract for the debug session mixin and ExplainNextDebugger.**
> Consumed by IDE extensions (VS Code debug panel), terminal-mode debuggers, and downstream tooling integrating with the ManulEngine breakpoint protocol.

```json
{
  "version": "0.0.9.28",
  "generatedFrom": "manul_engine/debug.py :: _DebugMixin; manul_engine/explain_next.py :: ExplainNextDebugger, PageContext, WhatIfResult, capture_page_context, _heuristic_pre_check, _HeuristicHit",

  "modules": {
    "debug": {
      "file": "manul_engine/debug.py",
      "class": "_DebugMixin",
      "description": "Mixin inherited by ManulEngine providing interactive debugging, element highlighting, abort modal, and the debug pause protocol for both terminal and extension modes.",
      "mro": "ManulEngine(_DebugMixin, _ControlsCacheMixin, _ActionsMixin)",
      "imports": ["manul_engine.js_scripts.DEBUG_MODAL_JS", "manul_engine.js_scripts.DEBUG_REMOVE_MODAL_JS", "manul_engine.explain_next.ExplainNextDebugger"]
    },
    "explain_next": {
      "file": "manul_engine/explain_next.py",
      "class": "ExplainNextDebugger",
      "description": "Interactive What-If Analysis REPL for hypothetical step evaluation during debug pauses. Combines DOMScorer heuristic scoring with optional LLM analysis against a read-only page snapshot.",
      "publicExports": ["ExplainNextDebugger", "WhatIfResult", "PageContext", "capture_page_context", "WHAT_IF_SYSTEM_PROMPT"],
      "reExportedFrom": "manul_engine.__init__ (ExplainNextDebugger, WhatIfResult)"
    }
  },

  "debugMixin": {
    "classAttributes": [
      { "name": "_explain_next_debugger", "type": "ExplainNextDebugger | None", "default": "None", "description": "Lazily created ExplainNextDebugger instance." },
      { "name": "_debug_continue",        "type": "bool",                       "default": false,   "description": "When True, skip all further debug pauses (set by 'continue all')." },
      { "name": "_what_if_execute_step",   "type": "str | None",                "default": "None",  "description": "Step string injected by the What-If REPL's !execute command. core.py checks this after _debug_prompt returns and replaces the current action." },
      { "name": "_user_break_steps",       "type": "set[int]",                  "default": "set()", "description": "Original gutter breakpoint line numbers (immutable reference set)." },
      { "name": "break_steps",             "type": "set[int]",                  "default": "set()", "description": "Mutable active breakpoint set. Modified by 'next' (add idx+1) and 'continue' (reset to _user_break_steps)." },
      { "name": "_last_explain_data",      "type": "tuple | None",              "default": "None",  "description": "Cached (scored_elements, execution_time, top_elements) for the 'explain' command." }
    ],

    "methods": {
      "highlight": {
        "name": "_highlight",
        "signature": "(page, target, color='red', bg='#ffeb3b', *, by_js_id=False, frame=None) -> None",
        "async": true,
        "description": "Flash a coloured border around an element for 2 seconds (non-persistent). Used for non-debug visual feedback.",
        "sideEffects": "Injects inline style on the element, auto-removed via setTimeout(2000)."
      },
      "debugHighlight": {
        "name": "_debug_highlight",
        "signature": "(page, loc_or_id, *, by_js_id=False, frame=None) -> None",
        "async": true,
        "description": "Apply a persistent magenta outline + glow on the target element. Stays until _clear_debug_highlight() is called.",
        "sideEffects": "Injects <style id='manul-debug-style'> (once) and sets data-manul-debug-highlight='true' attribute. Scrolls element into view.",
        "css": "outline: 4px solid #ff00ff; box-shadow: 0 0 15px #ff00ff; background: rgba(255,0,255,.12); z-index: 999999",
        "usedBy": ["_debug_prompt (before pause)", "ExplainNextDebugger._highlight_match (what-if best candidate)"]
      },
      "clearDebugHighlight": {
        "name": "_clear_debug_highlight",
        "signature": "(page) -> None",
        "async": true,
        "description": "Remove the persistent debug highlight from all elements and remove the <style> tag.",
        "sideEffects": "Removes data-manul-debug-highlight attribute from all elements, removes #manul-debug-style."
      },
      "injectDebugModal": {
        "name": "_inject_debug_modal",
        "signature": "(page, step: str) -> None",
        "async": true,
        "description": "Inject the floating debug panel with an Abort button into the browser.",
        "sideEffects": "Evaluates DEBUG_MODAL_JS, sets window.__manul_debug_action."
      },
      "removeDebugModal": {
        "name": "_remove_debug_modal",
        "signature": "(page) -> None",
        "async": true,
        "description": "Remove the debug modal and reset the abort signal.",
        "sideEffects": "Evaluates DEBUG_REMOVE_MODAL_JS."
      },
      "pollForAbort": {
        "name": "_poll_for_abort",
        "signature": "(page, abort_event: asyncio.Event) -> None",
        "async": true,
        "description": "Poll window.__manul_debug_action every 200ms; set abort_event on ABORT.",
        "pollingInterval": "200ms"
      },
      "getExplainNext": {
        "name": "_get_explain_next",
        "signature": "() -> ExplainNextDebugger",
        "async": false,
        "description": "Lazy factory for ExplainNextDebugger. Passes self._llm, self.learned_elements, self.last_xpath, and engine=self.",
        "returns": "ExplainNextDebugger (cached after first call)"
      },
      "debugPrompt": {
        "name": "_debug_prompt",
        "signature": "(page, step: str, idx: int) -> None",
        "async": true,
        "description": "Interactive pause during debug mode. Detects operating mode automatically."
      }
    }
  },

  "debugPromptProtocol": {
    "description": "Two operating modes detected by sys.stdin.isatty().",

    "extensionProtocolMode": {
      "condition": "stdin is NOT a TTY (piped by VS Code extension)",
      "pauseMarker": "\\x00MANUL_DEBUG_PAUSE\\x00{\"step\":\"...\",\"idx\":N}\\n",
      "stdinTokens": [
        { "token": "highlight",     "action": "Re-scroll to currently highlighted element via data-manul-debug-highlight attribute.", "continues": true },
        { "token": "explain",       "action": "Print heuristic score breakdown from _last_explain_data.", "continues": true },
        { "token": "explain-next",  "action": "Evaluate upcoming step via ExplainNextDebugger.evaluate(). Emits \\x00MANUL_EXPLAIN_NEXT\\x00{json}\\n marker to stdout with serialized WhatIfResult (via _result_to_dict). Accepts optional JSON payload: explain-next {\"step\":\"...\"} to evaluate overridden step text.", "continues": true },
        { "token": "what-if",       "action": "Disabled in extension protocol mode (stdin reserved for debug control tokens). Prints informational message and stays paused.", "continues": true },
        { "token": "continue",      "action": "Reset break_steps to _user_break_steps (original gutter breakpoints). Proceeds.", "continues": false },
        { "token": "next",          "action": "Add idx+1 to break_steps (pause at immediately following step). Proceeds.", "continues": false },
        { "token": "debug-stop",    "action": "Clear both _user_break_steps and break_steps. Run to end without any further pauses.", "continues": false },
        { "token": "abort",         "action": "Raise Exception('Test intentionally aborted by user via debug modal').", "continues": false }
      ],
      "explainNextMarker": {
        "format": "\\x00MANUL_EXPLAIN_NEXT\\x00{json}\\n",
        "json": "Serialized WhatIfResult via _result_to_dict(): step, score, confidence_label, target_found, target_element, explanation, risk, suggestion, heuristic_score, heuristic_match"
      }
    },

    "terminalMode": {
      "condition": "stdin IS a TTY (interactive terminal)",
      "prompt": "[DEBUG] Next step: {step}\\n        ENTER/n = execute \u00b7 e = explain-next \u00b7 h = re-highlight \u00b7 w = what-if \u00b7 pause = Inspector \u00b7 c = continue all\u2026",
      "inputCommands": [
        { "input": "ENTER or n or any",  "action": "Execute the current step." },
        { "input": "e or explain-next",  "action": "One-shot What-If evaluation of the current step (prints format_report, stays paused)." },
        { "input": "h",                  "action": "Re-scroll to highlighted element." },
        { "input": "w or what-if",       "action": "Enter ExplainNextDebugger REPL." },
        { "input": "pause",              "action": "Open Playwright Inspector (page.pause())." },
        { "input": "c or continue",      "action": "Set _debug_continue=True, skip all future pauses." }
      ]
    },

    "abortModal": {
      "description": "In both modes, a floating modal with an Abort button is injected into the browser before waiting.",
      "injection": "_inject_debug_modal(page, step)",
      "cleanup": "_remove_debug_modal(page) in a finally block",
      "polling": "_poll_for_abort checks window.__manul_debug_action every 200ms"
    }
  },

  "whatIfExecuteStepInjection": {
    "location": "manul_engine/core.py :: run_mission() main loop",
    "attribute": "_what_if_execute_step",
    "mechanism": "After _debug_prompt returns, if _what_if_execute_step is not None, the injected step is run through substitute_memory() to resolve {var} placeholders, the action text is replaced, and the attribute is reset to None.",
    "flow": [
      "1. _debug_prompt pauses execution",
      "2. User enters 'w' (terminal) to open the What-If REPL",
      "3. ExplainNextDebugger.run_repl() opens",
      "4. User evaluates hypothetical steps, then types '!execute [N]'",
      "5. run_repl() returns the chosen step string",
      "6. _debug_prompt sets self._what_if_execute_step = chosen",
      "7. core.py detects non-None value, runs substitute_memory(), replaces current action, resets to None",
      "8. Execution continues with the substituted step"
    ]
  },

  "explainNextDebugger": {
    "class": "ExplainNextDebugger",
    "importPath": "from manul_engine import ExplainNextDebugger",

    "constructor": {
      "parameters": [
        { "name": "llm",               "type": "LLMProvider",    "description": "LLM provider (OllamaProvider or NullProvider for heuristics-only)." },
        { "name": "learned_elements",   "type": "dict | None",   "default": "None", "description": "Engine's semantic cache (read-only for scoring context)." },
        { "name": "last_xpath",         "type": "str | None",    "default": "None", "description": "Most recently resolved xpath for context-reuse scoring." },
        { "name": "engine",             "type": "object | None",  "default": "None", "description": "Reference to _DebugMixin (for highlight calls). Optional — highlighting is skipped when None." }
      ]
    },

    "properties": [
      { "name": "history", "type": "list[WhatIfResult]", "description": "All what-if evaluations performed in this session (copy)." }
    ],

    "methods": {
      "evaluate": {
        "signature": "(page: Page, hypothetical_step: str, *, last_step: str = '') -> WhatIfResult",
        "async": true,
        "description": "Evaluate a hypothetical step against the current page state. Guaranteed read-only — never mutates the page.",
        "pipeline": [
          "1. capture_page_context(page) — read-only DOM snapshot + visible text",
          "2. extract_quoted(step) — extract quoted target strings",
          "3. classify_step(step) — determine step type (navigate, click, etc.)",
          "4. _heuristic_pre_check(elements, step, search_texts, target_field) — DOMScorer scoring",
          "5. Build LLM user prompt with page context + heuristic results",
          "6. llm.call_json(WHAT_IF_SYSTEM_PROMPT, user_prompt) — LLM analysis",
          "7. If LLM unavailable: _heuristic_only_result() fallback",
          "8. _highlight_match(page, hit) — highlight best candidate on live page",
          "9. Append WhatIfResult to history"
        ],
        "readOnlyGuarantee": "Only page.url, page.title(), page.frames[].evaluate(SNAPSHOT_JS) and page.evaluate(_VISIBLE_TEXT_JS) are called. No clicks, fills, navigations, or DOM mutations."
      },
      "highlightMatch": {
        "signature": "(page: Page, hit: _HeuristicHit | None) -> None",
        "async": true,
        "description": "Highlight the best heuristic match using engine._debug_highlight(). Clears previous highlight first.",
        "requires": "self._engine to be a _DebugMixin instance (skipped when None)."
      },
      "heuristicOnlyResult": {
        "signature": "(step, step_class, ctx, search_texts, h_score, h_match) -> WhatIfResult",
        "async": false,
        "description": "Build a WhatIfResult from heuristic data alone when LLM is unavailable.",
        "scoreMappingTable": [
          { "normalizedScore": ">= 1.0",  "confidence": 10 },
          { "normalizedScore": ">= 0.5",  "confidence": 9 },
          { "normalizedScore": ">= 0.1",  "confidence": 7 },
          { "normalizedScore": ">= 0.05", "confidence": 5 },
          { "normalizedScore": ">= 0.01", "confidence": 3 },
          { "normalizedScore": "> 0",     "confidence": 1 },
          { "normalizedScore": "0 or None","confidence": 0 }
        ],
        "systemStepOverride": "System commands (navigate, wait, scroll, press_enter, done, logical_step, set_variable, scan_page) are boosted to confidence >= 8."
      },
      "runRepl": {
        "signature": "(page: Page, *, current_step: str = '') -> str | None",
        "async": true,
        "description": "Run the interactive What-If REPL. Returns the step string chosen via !execute, or None if user quits.",
        "replCommands": [
          { "command": "<any step text>", "description": "Evaluate a hypothetical step (calls evaluate())." },
          { "command": "!history",        "description": "Show all evaluations from this session with index, score, and label." },
          { "command": "!execute",        "description": "Accept the last evaluated step and return it for execution." },
          { "command": "!execute N",      "description": "Accept evaluation #N from history and return it for execution." },
          { "command": "!context",        "description": "Show current page URL and title." },
          { "command": "!help",           "description": "Show REPL help text." },
          { "command": "!quit",           "description": "Exit REPL without executing anything (returns None)." }
        ]
      }
    }
  },

  "dataClasses": {
    "PageContext": {
      "file": "manul_engine/explain_next.py",
      "frozen": true,
      "fields": [
        { "name": "url",                  "type": "str",        "description": "Current page URL." },
        { "name": "title",                "type": "str",        "description": "Current page title." },
        { "name": "elements",             "type": "list[dict]", "description": "DOM snapshot (same shape as SNAPSHOT_JS output).", "default": "[]" },
        { "name": "visible_text_snippet", "type": "str",        "description": "First 2000 chars of visible text from TreeWalker.", "default": "''" }
      ],
      "methods": [
        { "name": "to_prompt_text", "signature": "(max_elements: int = 60) -> str", "description": "Format page context as a concise LLM prompt section." }
      ]
    },
    "WhatIfResult": {
      "file": "manul_engine/explain_next.py",
      "frozen": true,
      "importPath": "from manul_engine import WhatIfResult",
      "fields": [
        { "name": "step",             "type": "str",          "description": "The hypothetical step that was evaluated." },
        { "name": "score",            "type": "int",          "description": "Confidence score 0–10." },
        { "name": "target_found",     "type": "bool",         "description": "Whether a matching target element was found." },
        { "name": "target_element",   "type": "str | None",   "description": "Description of the matched element or None." },
        { "name": "explanation",      "type": "str",          "description": "What would happen if the step executes." },
        { "name": "risk",             "type": "str",          "description": "Potential side effects or failure modes." },
        { "name": "suggestion",       "type": "str | None",   "description": "Improved step phrasing if score < 7, else None." },
        { "name": "heuristic_score",  "type": "int | None",   "description": "DOMScorer best score (scaled integer) or None.", "default": "None" },
        { "name": "heuristic_match",  "type": "str | None",   "description": "DOMScorer best candidate element name or None.", "default": "None" }
      ],
      "properties": [
        { "name": "confidence_label", "type": "str", "description": "Human-readable label: HIGH (>=8), MODERATE (>=5), LOW (>=1), IMPOSSIBLE (0)." }
      ],
      "methods": [
        { "name": "format_report", "signature": "() -> str", "description": "Multi-line box-drawing report suitable for terminal output." }
      ],
      "formatReportTemplate": [
        "┌─ 🔮 WHAT-IF ANALYSIS: \"{step}\"",
        "│  Confidence: {score}/10 ({confidence_label})",
        "│  Heuristic Score: {norm:.3f} (raw {heuristic_score})  [if present]",
        "│  Best Heuristic Match: \"{heuristic_match}\"  [if present]",
        "│  Target Element: {target_element}  [if present]",
        "│  Explanation: {explanation}",
        "│  Risk: {risk}  [if present]",
        "│  Suggestion: {suggestion}  [if present]",
        "└─ 🔮 END"
      ]
    },
    "_HeuristicHit": {
      "file": "manul_engine/explain_next.py",
      "frozen": true,
      "internal": true,
      "fields": [
        { "name": "score",       "type": "int", "description": "DOMScorer best score (scaled integer)." },
        { "name": "name",        "type": "str", "description": "Best candidate element name." },
        { "name": "xpath",       "type": "str", "description": "Best candidate xpath (for highlight routing)." },
        { "name": "frame_index", "type": "int", "description": "Frame index into page.frames." }
      ]
    }
  },

  "helperFunctions": {
    "capturePageContext": {
      "file": "manul_engine/explain_next.py",
      "signature": "(page: Page) -> PageContext",
      "async": true,
      "description": "Capture a read-only snapshot of the page. Iterates page.frames, evaluates SNAPSHOT_JS per frame, collects visible text via TreeWalker. Strictly read-only — no page mutations.",
      "readOnlyCalls": ["page.url", "page.title()", "page.evaluate(_VISIBLE_TEXT_JS)", "frame.evaluate(SNAPSHOT_JS, ['locate', []])"],
      "frameHandling": "Cross-origin child frames are silently skipped (only idx=0 failure is re-raised)."
    },
    "heuristicPreCheck": {
      "file": "manul_engine/explain_next.py",
      "signature": "(elements, step, search_texts, target_field) -> _HeuristicHit | None",
      "async": false,
      "description": "Run DOMScorer against the snapshot to find the best candidate. Strictly read-only — no Playwright calls. Returns None when no elements available.",
      "scoringCall": "score_elements(elements, step, mode, search_texts, target_field, is_blind, learned_elements={}, last_xpath=None, explain=False)"
    }
  },

  "llmIntegration": {
    "systemPrompt": "WHAT_IF_SYSTEM_PROMPT",
    "description": "Score-and-Explain prompt that receives page context, last executed step, and hypothetical step. LLM returns JSON with score (0–10), target_found, target_element, explanation, risk, suggestion.",
    "responseSchema": {
      "score": "int 0–10",
      "target_found": "bool",
      "target_element": "string | null",
      "explanation": "string",
      "risk": "string",
      "suggestion": "string | null"
    },
    "fallback": "When LLM is NullProvider or call_json returns None, _heuristic_only_result() produces a deterministic WhatIfResult from DOMScorer data alone."
  },

  "safetyGuarantees": {
    "readOnly": "evaluate() never mutates page state. Only read-only Playwright calls (url, title, evaluate for snapshot/text) are used.",
    "noNavigation": "No page.goto(), page.click(), page.fill(), or any navigation-triggering calls.",
    "highlightOnly": "The only visual side effect is _debug_highlight (CSS attribute + style tag) which is cleanly removable via _clear_debug_highlight.",
    "exceptionSafety": "All page interactions are wrapped in try/except (OSError, RuntimeError) to handle page destruction gracefully.",
    "sessionIsolation": "ExplainNextDebugger._history accumulates within a debug session but does not persist across engine restarts."
  },

  "testCoverage": {
    "file": "manul_engine/test/test_53_explain_next.py",
    "assertions": 112,
    "testCount": 36,
    "categories": [
      "PageContext construction and to_prompt_text()",
      "WhatIfResult confidence_label property",
      "WhatIfResult format_report() output",
      "_heuristic_pre_check scoring pipeline",
      "ExplainNextDebugger.evaluate() with NullProvider (heuristics-only)",
      "ExplainNextDebugger._heuristic_only_result() score mapping",
      "System step type overrides",
      "ExplainNextDebugger.history accumulation",
      "_HeuristicHit dataclass",
      "WHAT_IF_SYSTEM_PROMPT content validation",
      "_DebugMixin._EXPLAIN_NEXT_MARKER wire format",
      "_DebugMixin._result_to_dict() serialization",
      "Extension protocol explain-next token (current step, overridden step, malformed JSON, multiple calls)",
      "Terminal mode explain-next (e command)"
    ]
  }
}
```

---

## Quick Reference

### Entering What-If mode

| Mode | Trigger | Protocol |
|------|---------|----------|
| Terminal (one-shot) | Type `e` or `explain-next` at the debug prompt | Prints format_report(), stays paused |
| Terminal (REPL) | Type `w` or `what-if` at the debug prompt | stdin/stdout (TTY) |
| Extension (one-shot) | Send `explain-next\n` on stdin | Emits `\x00MANUL_EXPLAIN_NEXT\x00{json}\n` marker, stays paused |
| Extension (REPL) | N/A — disabled in extension protocol mode | stdin reserved for control tokens |

### REPL Commands

| Command | Description |
|---------|-------------|
| `<step text>` | Evaluate a hypothetical step (dry-run) |
| `!history` | Show all evaluations with index, score, and label |
| `!execute` | Accept the last evaluated step for execution |
| `!execute N` | Accept evaluation #N from history |
| `!context` | Show current page URL and title |
| `!help` | Show help text |
| `!quit` | Exit without executing anything |

### Confidence Scale

| Score | Label | Meaning |
|-------|-------|---------|
| 0 | IMPOSSIBLE | Target element does not exist |
| 1–4 | LOW | Ambiguous target or disabled/hidden |
| 5–7 | MODERATE | Plausible target, some ambiguity |
| 8–10 | HIGH | Clear, unique target element found |

### Highlight Lifecycle

1. Debug pause → `_debug_highlight(page, locator)` — magenta outline on current step's target
2. What-If REPL entered → `_clear_debug_highlight(page)` before each evaluation
3. Heuristic match found → `_debug_highlight(page, new_locator)` — highlight best candidate
4. REPL exited → `_clear_debug_highlight(page)` cleanup
5. Debug resumes → `_clear_debug_highlight(page)` before action execution
