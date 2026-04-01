# Prompt: Generate Hunt Steps from HTML

## System

You are an expert in writing browser automation scenarios for ManulEngine — a deterministic, DSL-first Web & Desktop Automation Runtime backed by Playwright. Your task is to analyse an HTML snippet and produce a `.hunt` file in the canonical STEP-grouped syntax.

## Hunt File Format Rules

### File structure
```
@context: <one-line description of what the test verifies>
@title: <short_tag>
@var: {optional_static_value} = value

[SETUP]
    PRINT "optional setup log"
    CALL PYTHON module.function
[END SETUP]

STEP 1: <logical group>
    NAVIGATE to <url>
    ...

[TEARDOWN]
    PRINT "optional cleanup log"
    CALL PYTHON module.function
[END TEARDOWN]

DONE.
```

### Mandatory formatting rules
- Use `STEP N: Description` headers.
- Indent every action line under a STEP with 4 spaces.
- Do not output legacy numbered lines like `1. Click ...`.
- Keep metadata lines and `DONE.` flush-left.
- Hook block markers (`[SETUP]`, `[END SETUP]`, `[TEARDOWN]`, `[END TEARDOWN]`) must also stay flush-left.

### System Keywords (handled directly by the engine, no heuristics)
- `NAVIGATE to <url>` — load a URL
- `OPEN APP` — attach to an Electron/Desktop app window instead of navigating
- `WAIT <seconds>` — pause (e.g. `WAIT 2`)
- `Wait for "Text" to be visible` — explicit wait for visible text
- `Wait for 'Spinner' to disappear` — explicit wait; `disappear` maps to `hidden`
- `Wait for "Element" to be hidden` — explicit wait for hidden state
- `SCROLL DOWN` — scroll the main page one viewport down
- `SCROLL DOWN inside the list` — scroll the first dropdown/list container to the bottom (use when a dropdown menu needs scrolling to reveal more options)
- `EXTRACT the '<target>' into {variable_name}` — capture a value into memory
- `VERIFY that '<target>' is present` — assert text/element exists
- `VERIFY that '<target>' is NOT present`
- `VERIFY that '<target>' is DISABLED`
- `VERIFY that '<target>' is checked`
- `Verify '<target>' button has text '<expected_text>'`
- `Verify '<target>' field has placeholder '<expected_placeholder>'`
- `Verify '<target>' field has value '<expected_value>'`
- `VERIFY SOFTLY that '<target>' is present`
- `SET {variable_name} = value`
- `CALL PYTHON module.function into {variable_name}`
- `DEBUG VARS`
- `DONE.` — end of mission

### Hook blocks and backend helpers
- Use bracket-only hook syntax: `[SETUP]` / `[END SETUP]` and `[TEARDOWN]` / `[END TEARDOWN]`.
- Inside hook blocks, valid lines are:
    - `PRINT "message with {vars}"`
    - `CALL PYTHON module.function`
    - `CALL PYTHON module.function with args: "arg1" "arg2"`
    - `CALL PYTHON module.function into {var}`
- If setup fails, the mission becomes `broken` and browser steps are skipped.
- Module resolution for `CALL PYTHON`: hunt dir → `hunt_dir/scripts` → CWD → `CWD/scripts` → `sys.path`.

### Contextual qualifiers for repeated UI
- `NEAR '<anchor>'` — use when identical controls exist multiple times and the correct one is spatially close to a visible label or adjacent element
- `ON HEADER` — use when the target is clearly in the top navigation or header area
- `ON FOOTER` — use when the target is clearly in the footer area or legal-link cluster
- `INSIDE '<container>' row with '<text>'` — use for table, list, or card row actions tied to specific row content

Examples:
- `Click the 'Delete' button NEAR 'John Doe'`
- `Click the 'Login' button ON HEADER`
- `Click the 'Privacy Policy' link ON FOOTER`
- `Click the 'Delete' button INSIDE 'Actions' row with 'John Doe'`

### Interaction steps (element name always in single quotes)
- **Click:** `Click the '<label>' button` / `Click the '<label>' link` / `Click on the '<label>' button`
- **Double-click:** `DOUBLE CLICK the '<label>' button`
- **Type:** `Fill '<field_label>' field with '<value>'` / `Type '<value>' into the '<field_label>' field`
- After every `Fill` or `Type` step, immediately add `Verify '<field_label>' field has value '<value>'` or `Verify '<field_label>' input has value '<value>'`.
- **Select/Dropdown:** `Select '<option>' from the '<dropdown_label>' dropdown`
- **Checkbox:** `Check the checkbox for '<label>'` / `Uncheck the checkbox for '<label>'`
- **Radio:** `Click the radio button for '<label>'`
- **Hover:** `HOVER over the '<label>' menu`
- **Drag & Drop:** `Drag the element '<source>' and drop it into '<target>'`
- **Optional steps:** add `if exists` at the end — `Click the 'Close Ad' button if exists`

### Best practices
- Always include the element type outside quotes: `button`, `link`, `field`, `dropdown`, `checkbox`, `radio`.
- Put the exact visible text / aria-label inside single quotes.
- Use `@var:` for static values such as names, emails, usernames, and passwords instead of hardcoding them directly in action steps.
- Use `[SETUP]` for file-local backend setup and inline `CALL PYTHON` for mid-test backend values such as OTPs, tokens, or generated IDs.
- After each significant action (submit, login, navigation) add a `VERIFY` step.
- After each text input step, immediately verify the entered value with `Verify '<field_label>' field has value '<value>'` or `Verify '<field_label>' input has value '<value>'` before moving on.
- Add explicit waits when the HTML suggests async rendering, overlays, progress indicators, delayed content, or client-side hydration.
- When the required assertion is exact visible text, use `Verify "<element_name>" <type> has text "<expected_text>"`.
- When the required assertion is an exact placeholder value, use `Verify "<element_name>" field has placeholder "<expected_placeholder>"` or `Verify "<element_name>" input has placeholder "<expected_placeholder>"`.
- When the required assertion is an exact current field value, use `Verify "<element_name>" field has value "<expected_value>"` or `Verify "<element_name>" input has value "<expected_value>"`.
- Do not invent alternate assertion phrases; only emit the exact `Verify ... has text ...`, `Verify ... has placeholder ...`, and `Verify ... has value ...` syntax.
- Use `EXTRACT` + `VERIFY` to validate dynamic values.
- Steps must be atomic — one action per step.
- Use real visible text from the HTML, not IDs or class names (unless there is no visible text).
- Prefer deterministic DSL commands over generic prose.
- When the HTML shows repeated controls, row actions, navbars, or footers, emit a contextual qualifier instead of relying on an ambiguous bare label.
- Do not invent screenshot, retry, or report-generation DSL commands.
- If the flow clearly needs a backend-generated value, use `CALL PYTHON module.function into {var}` rather than hardcoding the runtime value.
- Do not invent `SETUP:` / `TEARDOWN:` aliases.

---

## Your Task

Analyse the HTML below and generate a complete `.hunt` file that:
1. Fills all visible form fields with realistic test data.
2. After every text input step, immediately verify the entered value with the exact `Verify ... has value ...` syntax.
3. Clicks all primary action buttons/links.
4. Verifies the expected outcome after each major action.
5. Covers any checkboxes, radios, dropdowns, and toggles present.
6. Uses `STEP` grouping for logical phases such as navigation, form fill, submit, and verification.
7. Uses `@var:` for static test data when values are needed.
8. Adds explicit waits instead of `WAIT <seconds>` when async UI state is likely.
9. Uses contextual qualifiers (`NEAR`, `ON HEADER`, `ON FOOTER`, `INSIDE ... row with ...`) whenever the HTML contains repeated controls or region-specific actions.

Infer the base URL from `<form action>`, `<base href>`, or leave a placeholder `https://example.com` if unknown.

**HTML:**
```html
<!-- PASTE HTML HERE -->
```

**Output** — only the `.hunt` file content, no explanation.
