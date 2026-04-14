# ManulEngine — DSL Contract

> **Machine-readable contract for every `.hunt` DSL command recognised by the engine parser.**
> Generated from the Python source code of ManulEngine.
> Consumed by Manul Studio and other downstream tooling.

```json
{
  "version": "0.0.9.29",
  "generatedFrom": "manul_engine/helpers.py :: classify_step(), detect_mode(), parse_contextual_hint(); manul_engine/core.py :: run_mission(); manul_engine/cli.py :: parse_hunt_file(); manul_engine/actions.py :: _ActionsMixin; manul_engine/scoring.py :: DOMScorer contextual proximity rules; manul_engine/js_scripts.py :: SNAPSHOT_JS geometry export; manul_engine/imports.py :: parse_import_directive(), resolve_imports(), expand_use_directives()",
  "casePolicy": {
    "canonical": "ALL_UPPERCASE",
    "runtime": "case-insensitive",
    "note": "All DSL keywords are case-insensitive at runtime. classify_step() converts step text to uppercase before pattern matching; detect_mode() converts to lowercase for verb detection. Any mix of cases is accepted (e.g. 'navigate', 'Navigate', 'NAVIGATE' all work). The canonical form shown in labels and examples is ALL UPPERCASE."
  },
  "elementTypeHint": {
    "rule": "optional_but_recommended",
    "note": "Element type hints (button, link, field, dropdown, checkbox, radio, element, input) placed outside quotes after the target name are optional. Including them provides a strong heuristic signal that boosts scoring accuracy. Examples: CLICK the 'Login' button (with hint) vs CLICK the 'Login' (without hint — still works).",
    "validHints": ["button", "link", "field", "dropdown", "checkbox", "radio", "element", "input"]
  },
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
      "label": "CLICK",
      "uiText": "CLICK the ''",
      "snippet": "CLICK the '${1:target}'${2: button}",
      "regex": null,
      "description": "Clicks a resolved element. Detected by the 'click' verb (case-insensitive). Element type hint (button, link, element) after the target is optional but recommended for scoring accuracy. Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "double_click",
      "label": "DOUBLE CLICK",
      "uiText": "DOUBLE CLICK the ''",
      "snippet": "DOUBLE CLICK the '${1:target}'",
      "regex": null,
      "description": "Double-clicks a resolved element. Detected by the 'double' + 'click' verbs (case-insensitive). Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "check",
      "label": "CHECK",
      "uiText": "CHECK the checkbox for ''",
      "snippet": "CHECK the checkbox for '${1:target}'",
      "regex": null,
      "description": "Checks a checkbox element. Detected by the 'check' verb (case-insensitive). Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "uncheck",
      "label": "UNCHECK",
      "uiText": "UNCHECK the checkbox for ''",
      "snippet": "UNCHECK the checkbox for '${1:target}'",
      "regex": null,
      "description": "Unchecks a checkbox element. Detected by the 'uncheck' verb (case-insensitive). Interaction mode: clickable.",
      "category": "interaction",
      "interactionMode": "clickable"
    },
    {
      "id": "fill",
      "label": "FILL",
      "uiText": "FILL '' field with ''",
      "snippet": "FILL '${1:target}' field with '${2:value}'",
      "regex": null,
      "description": "Types text into a resolved input/textarea element. Detected by the 'fill' verb (case-insensitive). Element type hint (field, input) is optional but recommended. Interaction mode: input.",
      "category": "interaction",
      "interactionMode": "input"
    },
    {
      "id": "type",
      "label": "TYPE",
      "uiText": "TYPE '' into ''",
      "snippet": "TYPE '${1:value}' into '${2:target}'",
      "regex": null,
      "description": "Types text into a resolved element. Detected by the 'type' verb (case-insensitive). Interaction mode: input.",
      "category": "interaction",
      "interactionMode": "input"
    },
    {
      "id": "select",
      "label": "SELECT",
      "uiText": "SELECT '' from the '' dropdown",
      "snippet": "SELECT '${1:option}' from the '${2:target}' dropdown",
      "regex": null,
      "description": "Selects an option from a native <select> or custom dropdown. Detected by the 'select' or 'choose' verbs (case-insensitive). Element type hint (dropdown) is optional but recommended. Interaction mode: select.",
      "category": "interaction",
      "interactionMode": "select"
    },
    {
      "id": "hover",
      "label": "HOVER",
      "uiText": "HOVER over the ''",
      "snippet": "HOVER over the '${1:target}'",
      "regex": null,
      "description": "Hovers over a resolved element. Detected by the 'hover' verb (case-insensitive). Interaction mode: hover.",
      "category": "interaction",
      "interactionMode": "hover"
    },
    {
      "id": "drag",
      "label": "DRAG",
      "uiText": "DRAG '' and drop it into ''",
      "snippet": "DRAG '${1:source}' and drop it into '${2:destination}'",
      "regex": null,
      "description": "Drags one element and drops it onto another. Detected by the 'drag' + 'drop' verbs (case-insensitive). Interaction mode: drag.",
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
      "label": "WAIT FOR element",
      "uiText": "WAIT FOR '' to be visible",
      "snippet": "WAIT FOR '${1:target}' to ${2|be visible,be hidden,disappear|}",
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
      "id": "verify_text_strict",
      "label": "VERIFY strict text",
      "uiText": "VERIFY '' element has text ''",
      "snippet": "VERIFY '${1:element_name}' ${2|button,field,element,input|} has text '${3:Expected Text}'",
      "regex": "^\\s*(?:\\d+\\.\\s*)?VERIFY\\s+(?P<target_quote>[\"'])(?P<target>.+?)(?P=target_quote)\\s+(?P<element_type>button|field|element|input)\\s+HAS\\s+TEXT\\s+(?P<expected_quote>[\"'])(?P<expected>.*?)(?P=expected_quote)\\s*\\.?\\s*$",
      "description": "Strict text verification. Resolves the element via heuristics, reads locator.inner_text().strip(), and asserts exact equality against the expected text.",
      "category": "assertion"
    },
    {
      "id": "verify_placeholder_strict",
      "label": "VERIFY strict placeholder",
      "uiText": "VERIFY '' field has placeholder ''",
      "snippet": "VERIFY '${1:element_name}' ${2|button,field,element,input|} has placeholder '${3:Expected Placeholder}'",
      "regex": "^\\s*(?:\\d+\\.\\s*)?VERIFY\\s+(?P<target_quote>[\"'])(?P<target>.+?)(?P=target_quote)\\s+(?P<element_type>button|field|element|input)\\s+HAS\\s+PLACEHOLDER\\s+(?P<expected_quote>[\"'])(?P<expected>.*?)(?P=expected_quote)\\s*\\.?\\s*$",
      "description": "Strict placeholder verification. Resolves the element via heuristics, reads its placeholder attribute, and asserts exact equality against the expected placeholder.",
      "category": "assertion"
    },
    {
      "id": "verify_value_strict",
      "label": "VERIFY strict value",
      "uiText": "VERIFY '' field has value ''",
      "snippet": "VERIFY '${1:element_name}' ${2|button,field,element,input|} has value '${3:Expected Value}'",
      "regex": "^\\s*(?:\\d+\\.\\s*)?VERIFY\\s+(?P<target_quote>[\"'])(?P<target>.+?)(?P=target_quote)\\s+(?P<element_type>button|field|element|input)\\s+HAS\\s+VALUE\\s+(?P<expected_quote>[\"'])(?P<expected>.*?)(?P=expected_quote)\\s*\\.?\\s*$",
      "description": "Strict value verification. Resolves the element via heuristics, reads its current value via locator.input_value() with a value-attribute fallback, normalizes missing values to an empty string, and asserts exact equality against the expected value.",
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
      "description": "Executes a synchronous Python function inline. Supports positional arguments (including optional 'with args:' sugar), optional 'into {var}' / 'to {var}' capture, and parser-level @script alias rewriting for CALL PYTHON {alias}.func syntax. Module resolution order: hunt dir → CWD → sys.path.",
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
    },
    {
      "id": "use_import",
      "label": "USE",
      "uiText": "USE Login",
      "snippet": "USE ${1:BlockName}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?USE\\b",
      "description": "Expands an imported STEP block inline at parse time. The block must have been imported via @import:. Aliased names (from 'as' clause) are supported. Case-insensitive matching.",
      "category": "structure"
    },
    {
      "id": "if_block",
      "label": "IF",
      "uiText": "IF button 'Save' exists:",
      "snippet": "IF ${1:condition}:\n        ${2:action}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?IF\\b.+:\\s*$",
      "description": "Block-style conditional branching. Body lines are indented by 4 extra spaces. Supports ELIF and ELSE branches. Nesting supported. Conditions: element exists, text present, variable comparison/contains/truthy.",
      "category": "control_flow"
    },
    {
      "id": "elif_block",
      "label": "ELIF",
      "uiText": "ELIF text 'Error' is present:",
      "snippet": "ELIF ${1:condition}:\n        ${2:action}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?ELIF\\b.+:\\s*$",
      "description": "Alternative branch in an IF block. Multiple ELIF branches are allowed. Must follow IF or another ELIF. Cannot appear after ELSE.",
      "category": "control_flow"
    },
    {
      "id": "else_block",
      "label": "ELSE",
      "uiText": "ELSE:",
      "snippet": "ELSE:\n        ${1:action}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?ELSE\\s*:\\s*$",
      "description": "Default branch in an IF block. Only one ELSE is allowed and must be the last branch.",
      "category": "control_flow"
    },
    {
      "id": "repeat_loop",
      "label": "REPEAT",
      "uiText": "REPEAT 3 TIMES:",
      "snippet": "REPEAT ${1:N} TIMES:\n        ${2:action}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?REPEAT\\s+\\d+\\s+TIMES\\s*:\\s*$",
      "description": "Fixed-count loop. Body lines are indented by 4 extra spaces. {i} counter variable is auto-set (1-based). Nesting supported.",
      "category": "control_flow"
    },
    {
      "id": "for_each_loop",
      "label": "FOR EACH",
      "uiText": "FOR EACH {item} IN {items}:",
      "snippet": "FOR EACH {${1:var}} IN {${2:collection}}:\n        ${3:action}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?FOR\\s+EACH\\s+\\{?\\w+\\}?\\s+IN\\s+\\{?\\w+\\}?\\s*:\\s*$",
      "description": "Iterate over comma-separated values from a variable. On each iteration, the loop variable and {i} counter are set. Nesting supported.",
      "category": "control_flow"
    },
    {
      "id": "while_loop",
      "label": "WHILE",
      "uiText": "WHILE button 'Next' exists:",
      "snippet": "WHILE ${1:condition}:\n        ${2:action}",
      "regex": "^\\s*(?:\\d+\\.\\s*)?WHILE\\b.+:\\s*$",
      "description": "Repeat while condition is true. Uses same conditions as IF blocks. Safety limit: 100 iterations. {i} counter auto-set. Nesting supported.",
      "category": "control_flow"
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
      "id": "script",
      "label": "@script:",
      "uiText": "@script: {alias} = scripts.helpers",
      "snippet": "@script: {${1:alias}} = ${2:scripts.helpers}",
      "description": "Declares a file-local Python helper alias for later CALL PYTHON usage. Supported forms: module alias (`@script: {auth} = scripts.auth_helpers` -> `CALL PYTHON {auth}.issue_token`) and callable alias (`@script: {issue_token} = scripts.auth_helpers.issue_token` -> `CALL PYTHON {issue_token}`). Alias names must match placeholder identifiers (`^[A-Za-z_]\\w*$`). Targets must be dotted Python import paths only: no '/' , no '\\', and no '.py' suffix."
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
    },
    {
      "id": "import",
      "label": "@import:",
      "uiText": "@import: Login, Logout from lib/auth.hunt",
      "snippet": "@import: ${1:BlockName} from ${2:source.hunt}",
      "description": "Imports named STEP blocks from another .hunt file. Supports named imports (@import: Login, Logout from lib.hunt), wildcard (@import: * from lib.hunt), aliases (@import: Login as AuthLogin from lib.hunt), and package-style sources (@import: Login from @my-lib). Imported blocks are available for USE directives. @var: declarations from the source file are inherited at LEVEL_IMPORT (lowest priority)."
    },
    {
      "id": "export",
      "label": "@export:",
      "uiText": "@export: Login, Logout",
      "snippet": "@export: ${1:BlockName}",
      "description": "Declares which STEP blocks are importable by other .hunt files. Multiple @export: lines are allowed. @export: * makes all blocks available. When no @export: is declared and a wildcard @import: * is used, all blocks are available (open by default)."
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
