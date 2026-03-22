# ManulEngine — DSL Contract

> **Machine-readable contract for every `.hunt` DSL command recognised by the engine parser.**
> Generated from the Python source code of ManulEngine.
> Consumed by Manul Studio and other downstream tooling.

```json
{
  "version": "0.0.9.15",
  "generatedFrom": "manul_engine/helpers.py :: classify_step(), detect_mode(), parse_contextual_hint(); manul_engine/core.py :: run_mission(); manul_engine/cli.py :: parse_hunt_file(); manul_engine/actions.py :: _ActionsMixin; manul_engine/scoring.py :: DOMScorer contextual proximity rules; manul_engine/js_scripts.py :: SNAPSHOT_JS geometry export",
  "commands": [
    {
      "id": "navigate",
      "label": "NAVIGATE",
      "uiText": "NAVIGATE to ''",
      "snippet": "NAVIGATE to ${1:url}",
      "regex": "\\bNAVIGATE\\b",
      "description": "Navigates the browser to a specific URL and waits for DOM settlement.",
      "category": "navigation"
    },
    {
      "id": "open_app",
      "label": "OPEN APP",
      "uiText": "OPEN APP",
      "snippet": "OPEN APP",
      "regex": "\\bOPEN\\s+APP\\b",
      "description": "Attaches to an Electron/Desktop app window instead of navigating to a URL. Use as the first step for executable_path targets.",
      "category": "navigation"
    },
    {
      "id": "click",
      "label": "Click",
      "uiText": "Click the '' button",
      "snippet": "Click the '${1:target}' button",
      "regex": null,
      "description": "Clicks a resolved element. Detected by the 'click' verb in the step text. Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "double_click",
      "label": "DOUBLE CLICK",
      "uiText": "DOUBLE CLICK the ''",
      "snippet": "DOUBLE CLICK the '${1:target}'",
      "regex": null,
      "description": "Double-clicks a resolved element. Detected by the 'double' + 'click' verbs. Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "check",
      "label": "Check",
      "uiText": "Check the checkbox for ''",
      "snippet": "Check the checkbox for '${1:target}'",
      "regex": null,
      "description": "Checks a checkbox element. Detected by the 'check' verb. Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "uncheck",
      "label": "Uncheck",
      "uiText": "Uncheck the checkbox for ''",
      "snippet": "Uncheck the checkbox for '${1:target}'",
      "regex": null,
      "description": "Unchecks a checkbox element. Detected by the 'uncheck' verb. Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "fill",
      "label": "Fill",
      "uiText": "Fill '' field with ''",
      "snippet": "Fill '${1:target}' field with '${2:value}'",
      "regex": null,
      "description": "Types text into a resolved input/textarea element. Detected by the 'fill' verb. Interaction mode: input.",
      "category": "interaction",
      "interactionMode": "input"
    },
    {
      "id": "type",
      "label": "Type",
      "uiText": "Type '' into ''",
      "snippet": "Type '${1:value}' into '${2:target}'",
      "regex": null,
      "description": "Types text into a resolved element. Detected by the 'type' verb. Interaction mode: input.",
      "category": "interaction",
      "interactionMode": "input"
    },
    {
      "id": "select",
      "label": "Select",
      "uiText": "Select '' from the '' dropdown",
      "snippet": "Select '${1:option}' from the '${2:target}' dropdown",
      "regex": null,
      "description": "Selects an option from a native <select> or custom dropdown. Detected by the 'select' or 'choose' verbs. Interaction mode: select.",
      "category": "interaction",
      "interactionMode": "select"
    },
    {
      "id": "hover",
      "label": "HOVER",
      "uiText": "HOVER over the ''",
      "snippet": "HOVER over the '${1:target}'",
      "regex": null,
      "description": "Hovers over a resolved element. Detected by the 'hover' verb. Interaction mode: hover.",
      "category": "interaction",
      "interactionMode": "hover"
    },
    {
      "id": "drag",
      "label": "Drag",
      "uiText": "Drag '' and drop it into ''",
      "snippet": "Drag '${1:source}' and drop it into '${2:destination}'",
      "regex": null,
      "description": "Drags one element and drops it onto another. Detected by the 'drag' + 'drop' verbs. Interaction mode: drag.",
      "category": "interaction",
      "interactionMode": "drag"
    },
    {
      "id": "scroll",
      "label": "SCROLL DOWN",
      "uiText": "SCROLL DOWN",
      "snippet": "SCROLL DOWN${1: inside the ${2:container}}",
      "regex": "\\bSCROLL\\b",
      "description": "Scrolls the main page down by one viewport height, or scrolls a container to the bottom when 'inside the <container>' is appended.",
      "category": "navigation"
    },
    {
      "id": "wait",
      "label": "WAIT",
      "uiText": "WAIT 2",
      "snippet": "WAIT ${1:seconds}",
      "regex": "\\bWAIT\\b",
      "description": "Hard sleep for N seconds. Only matched when other WAIT variants (WAIT FOR RESPONSE, WAIT FOR element) do not match first.",
      "category": "wait"
    },
    {
      "id": "wait_for_element",
      "label": "Wait for element",
      "uiText": "Wait for '' to be visible",
      "snippet": "Wait for '${1:target}' to ${2|be visible,be hidden,disappear|}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?WAIT\\s+FOR\\s+(?P<quote>[\"'])(?P<target>.+?)(?P=quote)\\s+TO\\s+(?:(?:BE\\s+(?P<state_be>VISIBLE|HIDDEN))|(?P<state_disappear>DISAPPEAR))\\s*$",
      "description": "Explicit wait for a quoted element to reach a desired visibility state (visible, hidden, or disappear). Uses Playwright locator.wait_for(state=...).",
      "category": "wait"
    },
    {
      "id": "wait_for_response",
      "label": "WAIT FOR RESPONSE",
      "uiText": "WAIT FOR RESPONSE \"\"",
      "snippet": "WAIT FOR RESPONSE \"${1:url_pattern}\"",
      "regex": "\\bWAIT\\s+FOR\\s+RESPONSE\\b",
      "description": "Blocks until a network response matching the URL pattern arrives (substring match via page.wait_for_response()).",
      "category": "wait"
    },
    {
      "id": "extract",
      "label": "EXTRACT",
      "uiText": "EXTRACT the '' into {variable}",
      "snippet": "EXTRACT the '${1:target}' into {${2:variable}}",
      "regex": "\\bEXTRACT\\b",
      "description": "Extracts the text content of a resolved element and stores it into a runtime variable for use in subsequent steps.",
      "category": "data"
    },
    {
      "id": "verify",
      "label": "VERIFY",
      "uiText": "VERIFY that '' is present",
      "snippet": "VERIFY that '${1:target}' is ${2|present,NOT present,ENABLED,DISABLED,checked,NOT checked|}",
      "regex": "\\bVERIFY\\b",
      "description": "Asserts that an element or text is present, not present, enabled, disabled, checked, or not checked. Fails the mission on mismatch.",
      "category": "assertion"
    },
    {
      "id": "verify_softly",
      "label": "VERIFY SOFTLY",
      "uiText": "VERIFY SOFTLY that '' is present",
      "snippet": "VERIFY SOFTLY that '${1:target}' is ${2|present,NOT present,ENABLED,DISABLED,checked,NOT checked|}",
      "regex": "\\bVERIFY\\s+SOFTLY\\b",
      "description": "Non-fatal assertion. Same as VERIFY but does not stop execution on failure. Failures are collected as soft errors with 'warning' status.",
      "category": "assertion"
    },
    {
      "id": "verify_visual",
      "label": "VERIFY VISUAL",
      "uiText": "VERIFY VISUAL ''",
      "snippet": "VERIFY VISUAL '${1:element}'",
      "regex": "\\bVERIFY\\s+VISUAL\\b",
      "description": "Takes an element screenshot and compares against a baseline in visual_baselines/. Saves baseline on first run. Uses PIL/Pillow threshold comparison (1%) or raw byte fallback.",
      "category": "assertion"
    },
    {
      "id": "press_enter",
      "label": "PRESS ENTER",
      "uiText": "PRESS ENTER",
      "snippet": "PRESS ENTER",
      "regex": "^\\s*(?:\\d+\\.\\s*)?PRESS\\s+ENTER\\b",
      "description": "Presses the Enter key on the currently focused element. Useful for submitting forms after filling a field.",
      "category": "keyboard"
    },
    {
      "id": "press",
      "label": "PRESS",
      "uiText": "PRESS Escape",
      "snippet": "PRESS ${1:Key}${2: on '${3:target}'}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?PRESS\\b",
      "description": "Presses any key or key combination globally (e.g. PRESS Escape, PRESS Control+A), or on a specific resolved element when 'on <target>' is appended.",
      "category": "keyboard"
    },
    {
      "id": "right_click",
      "label": "RIGHT CLICK",
      "uiText": "RIGHT CLICK ''",
      "snippet": "RIGHT CLICK '${1:target}'",
      "regex": "\\bRIGHT\\s+CLICK\\b",
      "description": "Right-clicks a resolved element to open a context menu.",
      "category": "interaction"
    },
    {
      "id": "upload",
      "label": "UPLOAD",
      "uiText": "UPLOAD '' to ''",
      "snippet": "UPLOAD '${1:file_path}' to '${2:target}'",
      "regex": "\\bUPLOAD\\b",
      "description": "Uploads a file to a file-input element. Both file path and target must be quoted. Path resolved relative to the .hunt file directory, then CWD.",
      "category": "interaction"
    },
    {
      "id": "mock",
      "label": "MOCK",
      "uiText": "MOCK GET \"\" with ''",
      "snippet": "MOCK ${1|GET,POST,PUT,PATCH,DELETE|} \"${2:url_pattern}\" with '${3:mock_file}'",
      "regex": "\\bMOCK\\s+(?:GET|POST|PUT|PATCH|DELETE)\\b",
      "description": "Intercepts matching network requests via page.route() and fulfills from a local mock file. Supported HTTP methods: GET, POST, PUT, PATCH, DELETE.",
      "category": "network"
    },
    {
      "id": "scan_page",
      "label": "SCAN PAGE",
      "uiText": "SCAN PAGE",
      "snippet": "SCAN PAGE${1: into {${2:filename}}}",
      "regex": "\\bSCAN\\s+PAGE\\b",
      "description": "Scans the current page for interactive elements and prints a draft .hunt file to the console. Optionally writes to a file when 'into {filename}' is appended.",
      "category": "utility"
    },
    {
      "id": "call_python",
      "label": "CALL PYTHON",
      "uiText": "CALL PYTHON module.function",
      "snippet": "CALL PYTHON ${1:module}.${2:function}${3: ${4:args}}${5: into {${6:variable}}}",
      "regex": "\\bCALL\\s+PYTHON\\b",
      "description": "Executes a synchronous Python function inline. Supports positional arguments (including optional 'with args:' sugar) and optional 'into {var}' / 'to {var}' capture. Module resolution order: hunt dir → hunt_dir/scripts → CWD → CWD/scripts → sys.path.",
      "category": "python"
    },
    {
      "id": "set_var",
      "label": "SET",
      "uiText": "SET {variable} = value",
      "snippet": "SET {${1:variable}} = ${2:value}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?SET\\b",
      "description": "Sets a runtime variable mid-flight. Both {braced} and bare key forms accepted. Quoted values are auto-unquoted. Available for {placeholder} substitution in all subsequent steps.",
      "category": "data"
    },
    {
      "id": "debug",
      "label": "DEBUG",
      "uiText": "DEBUG",
      "snippet": "DEBUG",
      "regex": "\\b(?:DEBUG|PAUSE)\\b",
      "description": "Pauses execution at this step. In interactive terminal mode (--debug), prompts the user; in VS Code extension mode (--break-lines), emits the debug pause protocol marker. PAUSE is accepted as an alias.",
      "category": "utility"
    },
    {
      "id": "debug_vars",
      "label": "DEBUG VARS",
      "uiText": "DEBUG VARS",
      "snippet": "DEBUG VARS",
      "regex": "\\bDEBUG\\s+VARS\\b",
      "description": "Prints the current state of all runtime variables to the console for diagnostic purposes.",
      "category": "utility"
    },
    {
      "id": "done",
      "label": "DONE",
      "uiText": "DONE.",
      "snippet": "DONE.",
      "regex": "\\bDONE\\b",
      "description": "Explicitly ends the mission. Any steps after DONE are not executed.",
      "category": "control_flow"
    },
    {
      "id": "logical_step",
      "label": "STEP",
      "uiText": "STEP 1: Description",
      "snippet": "STEP ${1:N}: ${2:Description}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?STEP\\s*\\d*\\s*:",
      "description": "Declares a hierarchical STEP block. All action lines following this header belong to this block until the next STEP header. The number is optional. Used for HTML report accordions and console grouping.",
      "category": "structure"
    }
  ],
  "contextualQualifiers": [
    {
      "id": "near",
      "syntax": "<action> NEAR '<anchor>'",
      "regex": "\\bNEAR\\s+(?P<quote>['\"])(?P<anchor>.+?)(?P=quote)",
      "description": "Biases candidate ranking by Euclidean distance to a resolved anchor element. Used for repeated buttons, links, and fields located close to a known label or neighboring control.",
      "scoring": {
        "kind": "euclidean_distance",
        "proximityWeight": 1.5,
        "distanceThresholdPx": 500
      }
    },
    {
      "id": "on_header",
      "syntax": "<action> ON HEADER",
      "regex": "\\bON\\s+HEADER\\b",
      "description": "Prefers candidates inside header or nav ancestry, or within the top 15% of the viewport.",
      "scoring": {
        "kind": "viewport_region",
        "proximityWeight": 1.5,
        "region": "top_15_percent_or_header_nav"
      }
    },
    {
      "id": "on_footer",
      "syntax": "<action> ON FOOTER",
      "regex": "\\bON\\s+FOOTER\\b",
      "description": "Prefers candidates inside footer ancestry, or within the bottom 15% of the viewport.",
      "scoring": {
        "kind": "viewport_region",
        "proximityWeight": 1.5,
        "region": "bottom_15_percent_or_footer"
      }
    },
    {
      "id": "inside_row",
      "syntax": "<action> INSIDE '<container>' row with '<text>'",
      "regex": "\\bINSIDE\\s+(?P<q1>['\"])(?P<target>.+?)(?P=q1)\\s+row\\s+with\\s+(?P<q2>['\"])(?P<row>.+?)(?P=q2)",
      "description": "Resolves the row text first, climbs to a container boundary such as tr, li, or div[role=row], and restricts candidate scoring to that subtree before normal action scoring continues.",
      "scoring": {
        "kind": "subtree_membership",
        "proximityWeight": 1.5,
        "containerScope": "resolved_row_container"
      }
    }
  ],
  "metadata": [
    {
      "id": "context",
      "label": "@context:",
      "uiText": "@context: description",
      "snippet": "@context: ${1:description}",
      "description": "Strategic context passed to the engine and LLM planner. Placed at the top of the file."
    },
    {
      "id": "title",
      "label": "@title:",
      "uiText": "@title: Suite Name",
      "snippet": "@title: ${1:Suite Name}",
      "description": "Short display name for the test suite. @blueprint: is accepted as a backward-compatible alias."
    },
    {
      "id": "tags",
      "label": "@tags:",
      "uiText": "@tags: smoke, regression",
      "snippet": "@tags: ${1:tag1, tag2}",
      "description": "Comma-separated run tags for CLI --tags filtering. Files are selected when at least one tag matches."
    },
    {
      "id": "var",
      "label": "@var:",
      "uiText": "@var: {key} = value",
      "snippet": "@var: {${1:key}} = ${2:value}",
      "description": "Declares a static variable pre-populated into runtime memory before any step runs. Available as {key} placeholder in all steps."
    },
    {
      "id": "data",
      "label": "@data:",
      "uiText": "@data: data/file.json",
      "snippet": "@data: ${1:path/to/file.json}",
      "description": "Points to a JSON (array-of-objects) or CSV file for data-driven testing. The engine reruns the entire mission for each row, injecting values as {placeholders}."
    },
    {
      "id": "schedule",
      "label": "@schedule:",
      "uiText": "@schedule: daily at 09:00",
      "snippet": "@schedule: ${1|every 30 seconds,every 1 minute,every 5 minutes,every 15 minutes,every 1 hour,daily at 09:00,every monday|}",
      "description": "Declares a schedule for daemon mode (manul daemon). Supported: every N seconds/minutes/hours, every minute/hour, daily at HH:MM, every <weekday>, every <weekday> at HH:MM."
    }
  ],
  "hookBlocks": [
    {
      "id": "setup",
      "label": "[SETUP]",
      "openTag": "[SETUP]",
      "closeTag": "[END SETUP]",
      "snippet": "[SETUP]\n    PRINT \"${1:Preparing setup}\"\n    CALL PYTHON ${2:module}.${3:function}${4: with args: \"${5:arg}\"}${6: into {${7:variable}}}\n[END SETUP]",
      "description": "Block of PRINT and CALL PYTHON lines executed BEFORE the browser launches. If any line fails, the mission is marked as broken and browser steps are skipped. Teardown is not called when setup fails. Target functions must be synchronous."
    },
    {
      "id": "teardown",
      "label": "[TEARDOWN]",
      "openTag": "[TEARDOWN]",
      "closeTag": "[END TEARDOWN]",
      "snippet": "[TEARDOWN]\n    PRINT \"${1:Cleaning up}\"\n    CALL PYTHON ${2:module}.${3:function}${4: with args: \"${5:arg}\"}\n[END TEARDOWN]",
      "description": "Cleanup block executed after the mission body in a finally block. It runs only when [SETUP] succeeded. Failure is logged but does not override the mission result."
    }
  ],
  "interactionModes": [
    {
      "id": "drag",
      "triggers": ["drag", "drop"],
      "triggerRule": "Both 'drag' AND 'drop' must be present as word-boundary tokens.",
      "description": "Drag-and-drop interaction via Playwright or manual mouse events."
    },
    {
      "id": "select",
      "triggers": ["select", "choose"],
      "triggerRule": "Either 'select' OR 'choose' present as a word-boundary token.",
      "description": "Native <select> or custom dropdown selection. Falls back to click for non-<select> elements."
    },
    {
      "id": "input",
      "triggers": ["type", "fill", "enter"],
      "triggerRule": "Any of 'type', 'fill', or 'enter' present as a word-boundary token.",
      "description": "Text input with auto-clear before typing."
    },
    {
      "id": "clickable",
      "triggers": ["click", "double", "check", "uncheck"],
      "triggerRule": "Any of 'click', 'double', 'check', or 'uncheck' present as a word-boundary token.",
      "description": "Click, double-click, or checkbox toggle."
    },
    {
      "id": "hover",
      "triggers": ["hover"],
      "triggerRule": "'hover' present as a word-boundary token.",
      "description": "Hover over a resolved element."
    },
    {
      "id": "locate",
      "triggers": [],
      "triggerRule": "Fallback when no other mode is detected.",
      "description": "Highlights the element without performing any action."
    }
  ],
  "comments": {
    "lineComment": "#",
    "rule": "Any line whose trimmed text starts with '#' is ignored. '#' after a step on the same line is treated as step text, not a comment."
  },
  "indentation": {
    "rule": "4-space indent for action lines under STEP headers and lines inside hook blocks. STEP headers, metadata lines, hook block markers, top-level comments, and DONE. are flush-left (zero indentation)."
  }
}
```
