# DSL Syntax Reference

> **ManulEngine v0.0.9.29**

This is the complete reference for the `.hunt` DSL — ManulEngine's plain-English automation language.

## Table of Contents

- [File Structure](#file-structure)
- [Metadata Headers](#metadata-headers)
- [Step Format](#step-format)
- [Navigation](#navigation)
- [Clicking](#clicking)
- [Input / Typing](#input--typing)
- [Dropdowns](#dropdowns)
- [Checkboxes and Radios](#checkboxes-and-radios)
- [Hover and Drag](#hover-and-drag)
- [Scrolling](#scrolling)
- [Key Presses](#key-presses)
- [Verification](#verification)
- [Explicit Waits](#explicit-waits)
- [Extraction](#extraction)
- [Variables and Substitution](#variables-and-substitution)
- [File-Level Variables (`@var:`)](#file-level-variables-var)
  - [Cross-File Global Variables (`@before_all`)](#cross-file-global-variables-before_all)
  - [Variable Priority](#variable-priority-lowest--highest)
- [Data-Driven Testing (`@data:`)](#data-driven-testing-data)
- [Python Hooks (`[SETUP]` / `[TEARDOWN]`)](#python-hooks-setup--teardown)
- [Inline CALL PYTHON](#inline-call-python)
- [Script Aliases (`@script:`)](#script-aliases-script)
- [Conditional Blocks (IF / ELIF / ELSE)](#conditional-blocks-if--elif--else)
- [Loops (REPEAT / FOR EACH / WHILE)](#loops-repeat--for-each--while)
- [Contextual Qualifiers](#contextual-qualifiers)
- [Page Object Model (`@import` / `@export` / `USE`)](#page-object-model-import--export--use)
- [Custom Controls](#custom-controls)
- [Smart Page Scanner](#smart-page-scanner)
- [Scheduling (`@schedule:`)](#scheduling-schedule)
- [Tags (`@tags:`)](#tags-tags)
- [Desktop / Electron Apps](#desktop--electron-apps)
- [Network Mocking](#network-mocking)
- [File Upload](#file-upload)
- [Debug and Pause](#debug-and-pause)
- [Configuration Reference](#configuration-reference)

---

## File Structure

Hunt files are plain text with the `.hunt` extension. The canonical structure:

```text
@context: Strategic context description
@title: Short suite name
@var: {key} = value
@tags: tag1, tag2

[SETUP]
    CALL PYTHON helpers.seed_data
[END SETUP]

STEP 1: Description of the first logical group
    ACTION line 1
    ACTION line 2
    VERIFY that 'expected result' is present

STEP 2: Description of the second group
    ACTION line 3
    VERIFY that 'outcome' is present

[TEARDOWN]
    CALL PYTHON helpers.cleanup
[END TEARDOWN]

DONE.
```

### Formatting Rules

- **STEP headers** are flush-left: `STEP 1: Description`
- **Action lines** inside a STEP use 4-space indentation
- **Metadata lines** (`@context:`, `@var:`, `@tags:`, etc.) are flush-left
- **Hook block markers** (`[SETUP]`, `[END SETUP]`, `[TEARDOWN]`, `[END TEARDOWN]`) are flush-left
- **`DONE.`** is flush-left
- **Comments** start with `#` at the beginning of a line. Inside STEP blocks, comments use the same 4-space indentation
- **Blank lines** between STEPs are allowed and ignored
- **All keywords are case-insensitive** — `CLICK`, `Click`, and `click` all work. The canonical form is ALL UPPERCASE

---

## Metadata Headers

Placed at the top of the file before any STEP or hook block.

| Header | Required | Description |
|--------|----------|-------------|
| `@context:` | No | Strategic context passed to the engine for logging and (if AI is enabled) LLM context |
| `@title:` | No | Short title for the test suite. Appears in reports and console output |
| `@var: {key} = value` | No | Static variable declarations (repeatable). See [Global Variables](#global-variables-var) |
| `@script: {alias} = module.path` | No | Python helper alias. See [Script Aliases](#script-aliases-script) |
| `@tags: tag1, tag2` | No | Comma-separated run tags for filtering with `manul --tags` |
| `@data: path/to/file.json` | No | Data-driven testing. See [Data-Driven Testing](#data-driven-testing-data) |
| `@schedule: expression` | No | Schedule for daemon mode. See [Scheduling](#scheduling-schedule) |
| `@import: blocks from source` | No | Import STEP blocks from another `.hunt` file. See [Page Object Model](#page-object-model-import--export--use) |
| `@export: Block1, Block2` | No | Declare which blocks are importable. See [Page Object Model](#page-object-model-import--export--use) |

---

## Step Format

**STEP-grouped format is mandatory for all new files.** Steps are atomic browser instructions grouped under STEP headers.

```text
STEP 1: Navigate to the login page
    NAVIGATE to https://example.com/login
    VERIFY that 'Sign In' is present

STEP 2: Fill credentials
    FILL 'Username' field with 'admin'
    FILL 'Password' field with 'secret'
    CLICK the 'Login' button
    VERIFY that 'Welcome' is present

DONE.
```

- The STEP number is optional — `STEP: label` is also valid.
- Each STEP block executes with fail-fast semantics: if an action fails, remaining actions in that block are skipped.
- `DONE.` explicitly ends the mission.

### Element Type Hints

Words like `button`, `link`, `field`, `dropdown`, `checkbox`, `radio`, `element`, `input` placed after the target name outside quotes are **optional but recommended**. They provide a heuristic signal that improves scoring accuracy.

```text
CLICK the 'Login' button       # recommended — gives the scorer a mode hint
CLICK the 'Login'              # also works — hint is inferred from context
```

---

## Navigation

```text
NAVIGATE to https://example.com
NAVIGATE to https://example.com/login
```

Loads the URL and waits for DOM settlement. Always follow with a `VERIFY` to confirm the page loaded.

---

## Clicking

```text
CLICK the 'Login' button
CLICK the 'Home' link
CLICK the 'Menu Item' element
CLICK on the 'Submit' button
DOUBLE CLICK the 'Image'
RIGHT CLICK 'Context Menu Area'
```

- Single-quoted or double-quoted target names.
- `DOUBLE CLICK` triggers a double-click.
- `RIGHT CLICK` opens a context menu.

---

## Input / Typing

Two syntaxes are supported with different argument order:

### FILL — target first, value last

```text
FILL 'Email' field with 'test@example.com'
FILL 'Password' field with 'secret123'
FILL 'Search' with 'ManulEngine'
```

### TYPE — value first, target last

```text
TYPE 'hello world' into 'Search' field
TYPE 'admin@example.com' into the 'Email' input
```

The keyword `into` marks the boundary between value and target.

> **Important:** The engine clears the field before typing to prevent appending to pre-filled values.

### Post-Input Verification

Always verify the typed value immediately after filling:

```text
FILL 'Email' field with '{email}'
VERIFY "Email" field has value "{email}"
```

---

## Dropdowns

```text
SELECT 'Option 1' from the 'Menu' dropdown
SELECT 'United States' from the 'Country' dropdown
```

For native `<select>` elements, uses Playwright's `select_option()`. For custom div/span dropdowns, falls back to click-based selection.

---

## Checkboxes and Radios

```text
CHECK the checkbox for 'Terms and Conditions'
UNCHECK the checkbox for 'Promotional Emails'
CLICK the radio button for 'Male'
```

The heuristic scorer aggressively penalizes non-checkbox elements when the step uses `CHECK` / `UNCHECK`, preventing accidental clicks on nearby text.

---

## Hover and Drag

```text
HOVER over the 'Menu'
DRAG the element 'Item' and drop it into 'Box'
```

---

## Scrolling

```text
SCROLL DOWN                            # scroll main page by one viewport
SCROLL DOWN inside the 'dropdown'      # scroll a specific container
```

---

## Key Presses

```text
PRESS ENTER                            # press Enter on the focused element
PRESS Escape                           # press any key globally
PRESS Control+A                        # key combinations
PRESS ArrowDown on 'Search Input'      # press a key on a specific element
```

---

## Verification

### Presence checks

```text
VERIFY that 'Welcome' is present
VERIFY that 'Error message' is NOT present
```

### State checks

```text
VERIFY that 'Submit' is ENABLED
VERIFY that 'Submit' is DISABLED
VERIFY that 'Terms' is checked
VERIFY that 'Newsletter' is NOT checked
```

### Strict value assertions

```text
VERIFY "Email" field has value "admin@example.com"
VERIFY "Save" button has text "Save Changes"
VERIFY "Search" input has placeholder "Type to search..."
```

These resolve the target via heuristics and compare with strict `==` equality.

### Soft verification

```text
VERIFY SOFTLY that 'Optional Banner' is present
```

Soft verification does **not** stop execution on failure. Failures are collected as warnings and surfaced in reports.

### Visual verification

```text
VERIFY VISUAL 'Logo'
```

Takes an element screenshot and compares against a baseline in `visual_baselines/`. Saves the baseline on first run. Uses PIL/Pillow threshold comparison (default 1%).

---

## Explicit Waits

```text
Wait for 'Submit' to be visible
Wait for 'Loading...' to disappear
Wait for 'Spinner' to be hidden
WAIT 2                                  # hard sleep (seconds)
WAIT FOR RESPONSE "api/data"            # wait for a network response
```

Explicit waits use Playwright's `locator.wait_for()` — always prefer these over hard sleeps.

---

## Extraction

```text
EXTRACT the 'Product Price' into {price}
EXTRACT the 'Order ID' into {order_id}
```

Stores the element's text into a variable. Use the variable in later steps:

```text
VERIFY that '{price}' is present
FILL 'Coupon' field with '{order_id}'
```

---

## Variables and Substitution

Variables can come from several sources:

| Source | Syntax | Scope |
|--------|--------|-------|
| `@var:` header | `@var: {key} = value` | File-scoped — available from mission start |
| `EXTRACT` | `EXTRACT 'X' into {var}` | Available after the extract step |
| `SET` | `SET {var} = value` | Available after the set step |
| `CALL PYTHON ... into {var}` | Return value captured | Available after the call |
| `@data:` row | Auto-injected from CSV/JSON | Per data row iteration (highest priority) |
| `@before_all` / lifecycle | `ctx.variables["key"]` | Cross-file global — all `.hunt` files |
| `@import` source vars | `@var:` from imported file | Lowest priority (import level) |

All variables use `{placeholder}` syntax for substitution:

```text
@var: {email} = admin@example.com

FILL 'Email' field with '{email}'
VERIFY "Email" field has value "{email}"
```

### SET command (mid-flight variables)

```text
SET {status} = active
SET {count} = 42
```

Both `{braced}` and bare key forms are accepted. Quoted values are auto-unquoted.

---

## File-Level Variables (`@var:`)

Declare static test data at the top of a `.hunt` file:

```text
@var: {email} = admin@example.com
@var: {password} = secret123
@var: {base_url} = https://example.com
```

**Rules:**
- Both `@var: {key} = value` and `@var: key = value` are accepted (keys stored without braces).
- Values may contain spaces and are stripped of leading/trailing whitespace.
- Variables are pre-populated into runtime memory before any step runs.
- `@var:` is **scoped to the file** where it is declared — other `.hunt` files do not see these variables.
- **Never hardcode test data inside steps** — always use `@var:` declarations.

```text
# CORRECT
@var: {email} = admin@example.com
FILL 'Email' field with '{email}'

# WRONG — do not hardcode
FILL 'Email' field with 'admin@example.com'
```

### Cross-File Global Variables (`@before_all`)

To share variables across **all** `.hunt` files in a directory, use lifecycle hooks in `manul_hooks.py`:

```python
# tests/manul_hooks.py
from manul_engine import before_all, after_all, GlobalContext

@before_all
def setup(ctx: GlobalContext) -> None:
    ctx.variables["TOKEN"] = auth_service.get_token()
    ctx.variables["BASE_URL"] = "https://staging.example.com"

@after_all
def teardown(ctx: GlobalContext) -> None:
    auth_service.revoke_token(ctx.variables["TOKEN"])
```

Variables set via `ctx.variables` are available as `{TOKEN}` and `{BASE_URL}` in every `.hunt` file — no per-file `@var:` needed. Place `manul_hooks.py` in the same directory as your `.hunt` files; the engine discovers it automatically.

**Using global variables in a `.hunt` file:**

```text
@context: Uses global TOKEN and BASE_URL from manul_hooks.py
@title: Dashboard Check

STEP 1: Open dashboard
    NAVIGATE to {BASE_URL}/dashboard
    VERIFY that 'Dashboard' is present

STEP 2: Use API token
    CALL PYTHON api.set_auth_header "{TOKEN}"
    CLICK the 'Refresh Data' button
    VERIFY that 'Data loaded' is present

DONE.
```

No `@var:` declaration is needed — `{TOKEN}` and `{BASE_URL}` are injected by the `@before_all` hook before any `.hunt` file runs. If the same key is also declared as `@var:` in the file, the file-level value wins (higher priority).

You can also scope global variables to tagged file groups:

```python
from manul_engine import before_group, GlobalContext

@before_group(tag="smoke")
def smoke_setup(ctx: GlobalContext) -> None:
    ctx.variables["ENV"] = "smoke"
```

See [Integration — Global Lifecycle Hooks](integration.md#global-lifecycle-hooks) for full details.

### Variable priority (lowest → highest)

1. `@import` source `@var:` declarations (import level)
2. `@before_all` / `@before_group` `ctx.variables` (global level)
3. File-level `@var:` declarations (mission level)
4. `SET`, `EXTRACT`, `CALL PYTHON ... into` (step level)
5. `@data:` row values (row level — wins over everything)

---

## Data-Driven Testing (`@data:`)

Point to a JSON or CSV file to run the same mission for each data row:

```text
@data: users.csv
@var: {base_url} = https://example.com

STEP 1: Login with data row
    NAVIGATE to {base_url}/login
    FILL 'Email' field with '{email}'
    FILL 'Password' field with '{password}'
    CLICK the 'Login' button
    VERIFY that 'Welcome, {name}' is present

DONE.
```

**`users.csv`:**
```csv
email,password,name
alice@example.com,pass1,Alice
bob@example.com,pass2,Bob
```

**JSON format** (array of objects):
```json
[
  {"email": "alice@example.com", "password": "pass1", "name": "Alice"},
  {"email": "bob@example.com", "password": "pass2", "name": "Bob"}
]
```

The path is resolved relative to the `.hunt` file's directory, then CWD.

---

## Python Hooks (`[SETUP]` / `[TEARDOWN]`)

Hook blocks run synchronous Python functions **outside the browser** — before the browser launches and after the mission completes.

```text
[SETUP]
    PRINT "Seeding test data..."
    CALL PYTHON db_helpers.seed_user "{email}" "{password}"
[END SETUP]

STEP 1: Login
    NAVIGATE to https://example.com/login
    FILL 'Email' field with '{email}'
    CLICK the 'Login' button

[TEARDOWN]
    PRINT "Cleaning up..."
    CALL PYTHON db_helpers.clean_database "{email}"
[END TEARDOWN]
```

**Rules:**
- Inside hook blocks, only `PRINT "..."` and `CALL PYTHON ...` are valid.
- `[SETUP]` failure marks the mission as `broken` (browser steps are skipped).
- `[TEARDOWN]` runs whether the mission passed or failed.
- Target functions **must be synchronous**. Async callables are rejected.
- Module resolution: hunt file's directory → CWD → `sys.path`.

---

## Inline CALL PYTHON

`CALL PYTHON` is also valid as a standard step inside the main mission body:

```text
STEP 2: Fetch OTP
    CLICK the 'Send OTP' button
    CALL PYTHON api_helpers.fetch_otp "{email}" into {otp}
    FILL 'OTP' field with '{otp}'
    CLICK the 'Verify' button
    VERIFY that 'Verified' is present
```

### Full syntax variants

```text
CALL PYTHON module.function
CALL PYTHON module.function "arg1" 'arg2' {var}
CALL PYTHON module.function into {result}
CALL PYTHON module.function "arg1" {var} into {result}
CALL PYTHON {alias}.function
CALL PYTHON {callable_alias}
```

- Positional arguments are tokenised with `shlex.split()`.
- `{var}` placeholders in arguments are resolved from runtime memory.
- `into {var}` (or `to {var}`) captures the function's return value as a string.

---

## Script Aliases (`@script:`)

Declare Python helper aliases in the file header:

```text
@script: {db} = scripts.db_helpers
@script: {issue_token} = scripts.auth_helpers.issue_token

STEP 1: Setup
    CALL PYTHON {db}.seed_user "{email}"
    CALL PYTHON {issue_token} into {token}
```

- Module aliases: `@script: {alias} = package.module` → use as `CALL PYTHON {alias}.function`
- Callable aliases: `@script: {alias} = package.module.function` → use as `CALL PYTHON {alias}`
- Values must be valid dotted Python import paths (no slashes, no `.py`).

---

## Conditional Blocks (IF / ELIF / ELSE)

Branch test logic based on element presence, text state, or variable comparisons:

```text
STEP 1: Adaptive login
    IF button 'SSO Login' exists:
        CLICK the 'SSO Login' button
        VERIFY that 'SSO Portal' is present
    ELIF text 'Sign In' is present:
        FILL 'Username' field with '{username}'
        CLICK the 'Sign In' button
    ELSE:
        CLICK the 'Create Account' link
```

### Syntax

- `IF`, `ELIF`, `ELSE` headers end with `:` and are at the same indent level as sibling action lines (4 spaces inside a STEP).
- Body lines inside each branch use an additional 4-space indent (8 spaces inside a STEP).
- `ELIF` and `ELSE` are optional. Multiple `ELIF` branches are allowed.
- Only one `ELSE` allowed, and it must be last.
- Nesting is supported.

### Supported Conditions

| Pattern | Example | What it checks |
|---------|---------|----------------|
| Element exists | `button 'Save' exists` | Playwright locator probe |
| Element not exists | `link 'Home' not exists` | Inverse locator probe |
| Text present | `text 'Welcome' is present` | Visible text on page |
| Text not present | `text 'Error' is not present` | Inverse text check |
| Variable comparison | `{role} == 'admin'` | String equality |
| Variable inequality | `{status} != 'active'` | String inequality |
| Variable contains | `{message} contains 'success'` | Substring check |
| Variable truthy | `{token}` | Non-empty, non-"false", non-"0" |

### Nested Example

```text
STEP 2: Nested conditional
    IF button 'Save' exists:
        CLICK the 'Save' button
        IF text 'Are you sure?' is present:
            CLICK the 'Confirm' button
        ELSE:
            VERIFY that 'Saved' is present
    ELIF button 'Submit' exists:
        CLICK the 'Submit' button
    ELSE:
        CLICK the 'Cancel' button
```

---

## Loops (REPEAT / FOR EACH / WHILE)

Loop constructs repeat a block of actions multiple times. All three follow the same indentation rules as conditional blocks — the loop header ends with `:`, and body lines are indented by an additional 4 spaces.

A `{i}` counter variable (1-based) is automatically set on every iteration of any loop type.

### REPEAT N TIMES

Execute a fixed number of iterations:

```text
STEP 1: Paginate through results
    REPEAT 5 TIMES:
        CLICK the 'Next' button
        WAIT 1
        VERIFY that 'Page' is present
```

**Retry pattern** — click a button, check for success, repeat if needed:

```text
STEP 2: Retry on failure
    REPEAT 3 TIMES:
        CLICK the 'Submit' button
        WAIT 2
        IF text 'Success' is present:
            VERIFY that 'Success' is present
```

**Scroll to load content:**

```text
STEP 3: Scroll to reveal lazy-loaded items
    REPEAT 10 TIMES:
        SCROLL DOWN
        WAIT 1
```

### FOR EACH

Iterate over a comma-separated collection stored in a variable:

```text
@var: {colors} = red, green, blue

STEP 1: Test each color filter
    FOR EACH {color} IN {colors}:
        CLICK the '{color}' button
        VERIFY that '{color}' is present
```

The collection variable must hold a comma-separated string. On each iteration, `{color}` is set to the current item (trimmed) and `{i}` to the 1-based index.

Both `{braced}` and bare-key forms are accepted: `FOR EACH {item} IN {items}:` and `FOR EACH item IN items:` are equivalent.

**Form testing with multiple inputs:**

```text
@var: {usernames} = alice, bob, charlie
@var: {password} = Test1234!

STEP 2: Verify login for each user
    FOR EACH {user} IN {usernames}:
        NAVIGATE to 'https://example.com/login'
        FILL 'Username' field with '{user}'
        FILL 'Password' field with '{password}'
        CLICK the 'Sign In' button
        VERIFY that 'Dashboard' is present
        CLICK the 'Logout' link
```

**Search across multiple queries:**

```text
@var: {queries} = laptop, headphones, keyboard, mouse

STEP 3: Search store inventory
    FOR EACH {query} IN {queries}:
        FILL 'Search' field with '{query}'
        PRESS Enter
        VERIFY that 'results' is present
```

**Navigation menu walkthrough:**

```text
@var: {pages} = Home, Products, About, Contact

STEP 4: Verify all nav links work
    FOR EACH {page} IN {pages}:
        CLICK the '{page}' link ON HEADER
        VERIFY that '{page}' is present
```

### WHILE

Repeat while a condition is true. Uses the same condition syntax as `IF` blocks:

```text
STEP 1: Load all results
    WHILE button 'Load More' exists:
        CLICK the 'Load More' button
        WAIT 2
```

WHILE loops have a safety limit of **100 iterations** to prevent infinite loops. If the limit is reached, the loop aborts and the step fails.

**Dismiss multiple overlays:**

```text
STEP 2: Close all popups
    WHILE button 'Close' exists:
        CLICK the 'Close' button
        WAIT 1
```

**Paginate through all pages:**

```text
STEP 3: Export all pages
    WHILE button 'Next Page' exists:
        EXTRACT the 'Total Items' into {count}
        CLICK the 'Next Page' button
        WAIT 2
    VERIFY that 'Last Page' is present
```

**Wait for a process to complete (variable-based):**

```text
STEP 4: Poll until ready
    WHILE text 'Processing' is present:
        WAIT 3
    VERIFY that 'Complete' is present
```

**Supported WHILE conditions** — same as [conditional blocks](#supported-conditions):

| Pattern | Example |
|---------|---------|
| Element exists | `WHILE button 'Next' exists:` |
| Text present | `WHILE text 'Loading' is present:` |
| Variable comparison | `WHILE {counter} != '0':` |
| Variable contains | `WHILE {message} contains 'loading':` |
| Variable truthy | `WHILE {running}:` |

### Nesting

Loops can be nested inside conditionals, conditionals inside loops, and loops inside loops.

**Conditional inside a loop — retry with fallback:**

```text
STEP 1: Retry with adaptive strategy
    REPEAT 3 TIMES:
        IF text 'Error' is present:
            CLICK the 'Retry' button
        ELSE:
            CLICK the 'Next' button
```

**Loop inside a conditional — load more only when available:**

```text
STEP 2: Conditional pagination
    IF button 'Load More' exists:
        REPEAT 3 TIMES:
            CLICK the 'Load More' button
            WAIT 1
    ELSE:
        VERIFY that 'All items loaded' is present
```

**Loop inside a loop — table interaction:**

```text
@var: {sections} = Electronics, Clothing, Books

STEP 3: Expand and check all sections
    FOR EACH {section} IN {sections}:
        CLICK the '{section}' element
        REPEAT 2 TIMES:
            SCROLL DOWN
            WAIT 1
        VERIFY that '{section}' is present
```

**Deep nesting — conditional pagination with validation:**

```text
STEP 4: Smart pagination
    WHILE button 'Next' exists:
        CLICK the 'Next' button
        WAIT 1
        IF text 'Error' is present:
            CLICK the 'Retry' button
            WAIT 2
        ELSE:
            VERIFY that 'Page' is present
```

**FOR EACH with conditional skip:**

```text
@var: {features} = Dark Mode, Notifications, Auto-Save, Beta Features

STEP 5: Enable selected features
    FOR EACH {feature} IN {features}:
        IF checkbox '{feature}' is checked:
            VERIFY that '{feature}' is present
        ELSE:
            Check the checkbox for '{feature}'
            VERIFY that '{feature}' is present
```

### Real-World Examples

**E-commerce: add multiple products to cart**

```text
@context: Verify cart functionality for multiple products
@title: Multi-product cart test

@var: {products} = Laptop, Headphones, Mouse

STEP 1: Navigate to store
    NAVIGATE to 'https://example.com/products'
    VERIFY that 'Products' is present

STEP 2: Add each product to cart
    FOR EACH {product} IN {products}:
        FILL 'Search' field with '{product}'
        PRESS Enter
        CLICK the 'Add to Cart' button NEAR '{product}'
        VERIFY that 'Added to cart' is present
        WAIT 1

STEP 3: Verify cart contents
    CLICK the 'Cart' link ON HEADER
    VERIFY that 'Laptop' is present
    VERIFY that 'Headphones' is present
    VERIFY that 'Mouse' is present
    DONE.
```

**Admin panel: bulk user management**

```text
@context: Test bulk operations on user management page
@title: Bulk user operations

@var: {users} = alice@test.com, bob@test.com, charlie@test.com

STEP 1: Navigate to admin panel
    NAVIGATE to 'https://admin.example.com/users'
    VERIFY that 'User Management' is present

STEP 2: Select all target users
    FOR EACH {user} IN {users}:
        Check the checkbox for '{user}'
        VERIFY that '{user}' is present

STEP 3: Apply bulk action
    SELECT 'Deactivate' from 'Bulk Actions' dropdown
    CLICK the 'Apply' button
    VERIFY that 'successfully updated' is present
    DONE.
```

**Infinite scroll: load all items**

```text
@context: Verify infinite scroll loads all content
@title: Infinite scroll test

STEP 1: Open feed
    NAVIGATE to 'https://example.com/feed'
    VERIFY that 'Feed' is present

STEP 2: Scroll until all loaded
    WHILE text 'Loading more' is present:
        SCROLL DOWN
        WAIT 2

STEP 3: Verify final state
    VERIFY that 'No more items' is present
    DONE.
```

### Best Practices

- Prefer `REPEAT` when the number of iterations is known in advance.
- Prefer `FOR EACH` for iterating over data.
- Prefer `WHILE` for waiting on dynamic conditions (pagination, loading states).
- Always add a `WAIT` inside `WHILE` loops to avoid tight-looping.
- Keep loop bodies short — complex logic should use nested `IF` blocks.

---

## Contextual Qualifiers

When a page has repeated elements — multiple "Edit" buttons, "Delete" links in every row — use qualifiers to disambiguate:

### NEAR — pixel distance

```text
CLICK the 'Edit' button NEAR 'John Doe'
FILL 'Quantity' field with '3' NEAR 'Laptop'
```

Resolves `John Doe` as an anchor element, then ranks candidates by Euclidean pixel distance.

### ON HEADER / ON FOOTER — viewport zones

```text
CLICK the 'Login' button ON HEADER
CLICK the 'Privacy Policy' link ON FOOTER
```

Restricts scoring to `header`/`nav` ancestry or top 15% of the viewport (`ON HEADER`) or `footer` ancestry / bottom 15% (`ON FOOTER`).

### INSIDE — subtree containment

```text
CLICK the 'Delete' button INSIDE 'Actions' row with 'John Doe'
SELECT 'Admin' from 'Role' dropdown INSIDE 'Users' row with 'Alice'
```

Resolves the row or container matching the text, then restricts candidates to that subtree.

---

## Page Object Model (`@import` / `@export` / `USE`)

Share and reuse STEP blocks across `.hunt` files.

### Exporting blocks

**`lib/auth.hunt`:**
```text
@context: Shared authentication flows
@title: Auth Library
@export: Login, Logout

@var: {default_user} = admin@example.com

STEP Login: Authenticate
    FILL 'Email' field with '{email}'
    FILL 'Password' field with '{password}'
    CLICK the 'Login' button
    VERIFY that 'Dashboard' is present

STEP Logout: Sign out
    CLICK the 'Profile' menu
    CLICK the 'Logout' link
    VERIFY that 'Sign In' is present
```

- `@export: Login, Logout` declares which blocks are importable.
- `@export: *` makes all blocks available.
- When no `@export:` is declared, all blocks are available by default (open access).

### Importing and using blocks

**`tests/checkout.hunt`:**
```text
@context: Checkout flow
@title: Checkout
@import: Login, Logout from lib/auth.hunt

@var: {email} = buyer@example.com
@var: {password} = secret

STEP 1: Setup
    NAVIGATE to https://example.com
    USE Login

STEP 2: Purchase
    CLICK the 'Buy Now' button
    VERIFY that 'Order Confirmed' is present

STEP 3: Cleanup
    USE Logout

DONE.
```

### Import syntax variants

```text
@import: Login from lib/auth.hunt                   # named import
@import: Login, Logout from lib/auth.hunt            # multiple named
@import: Login as AuthLogin from lib/auth.hunt       # alias
@import: * from lib/auth.hunt                        # wildcard
@import: Login from @my-lib                          # package-style
```

- `USE BlockName` expands the imported block inline at parse time.
- Aliased names (`as` clause) are supported: `USE AuthLogin`.
- Import depth is capped at 10 to prevent circular imports.
- `@var:` declarations from the source file are inherited at the lowest priority level.

### Package-style imports

For reusable libraries distributed as `.huntlib` archives:

```bash
manul pack lib/auth.hunt                           # create auth.huntlib
manul install auth.huntlib                         # install to hunt_libs/
```

Then import by package name:

```text
@import: Login from @auth
```

---

## Custom Controls

For complex or non-standard UI elements (datepickers, virtual tables, canvas widgets), define custom Python handlers instead of forcing DSL workarounds.

### Defining a custom control

Create a Python file in the `controls/` directory:

```python
# controls/datepicker.py
from manul_engine import custom_control

@custom_control(page="Booking Page", target="Check-in Date")
async def handle_checkin(page, action_type: str, value: str | None) -> None:
    loc = page.locator(".react-datepicker__input-container input").first
    if action_type == "input" and value:
        await loc.click()
        await loc.fill(value)
```

### Using it in a hunt file

```text
FILL 'Check-in Date' with '2026-12-25'
```

The engine intercepts the step before DOM scoring — if a custom control matches `(page_name, target)`, it calls the handler directly with the Playwright `page` object.

### Handler signature

```python
async def handler(page, action_type: str, value: str | None) -> None:
    ...
```

- `page` — live Playwright `Page` object.
- `action_type` — detected mode: `"input"`, `"clickable"`, `"select"`, `"hover"`, `"drag"`, `"locate"`.
- `value` — for `"input"` steps, the text to type; for `"select"`, the option; `None` for clicks and hovers.

Both sync and async handlers are supported.

### Page name matching

The `page` parameter in `@custom_control(page="...")` must match the value returned by `lookup_page_name(page.url)` — the mapping defined in `pages.json`:

```json
{
  "https://booking.example.com": {
    "Domain": "Booking App",
    "/reservations": "Booking Page"
  }
}
```

### Automatic scanning and discovery

Use the scanner to detect interactive elements on a page:

```bash
manul scan https://booking.example.com/reservations
```

Review the generated draft. For complex widgets that produce messy or unreliable steps, replace them with a custom control. The engine auto-loads all Python files in `controls/` (configurable via `custom_controls_dirs`).

### Configuration

```json
{
  "custom_controls_dirs": ["controls", "shared/controls"]
}
```

Multiple directories are supported. Resolved relative to CWD.

---

## Smart Page Scanner

Generate draft `.hunt` files from live pages:

```bash
manul scan https://example.com                    # → tests/draft.hunt
manul scan https://example.com output.hunt        # custom output
manul scan https://example.com --headless          # headless
```

Or use `SCAN PAGE` as a step inside a hunt file:

```text
STEP 1: Navigate and scan
    NAVIGATE to https://example.com
    SCAN PAGE
    # or: SCAN PAGE into {filename}
```

The scanner injects JavaScript, detects interactive elements, and generates a hunt file with appropriate action steps.

---

## Scheduling (`@schedule:`)

Turn any hunt file into a recurring automation with the `@schedule:` header:

```text
@schedule: every 5 minutes
@title: Health Check

STEP 1: Verify homepage
    NAVIGATE to https://example.com
    VERIFY that 'Welcome' is present

DONE.
```

### Supported expressions

```text
@schedule: every 30 seconds
@schedule: every 1 minute
@schedule: every 5 minutes
@schedule: every hour
@schedule: daily at 09:00
@schedule: every monday
@schedule: every friday at 14:30
```

### Running the daemon

```bash
manul daemon tests/ --headless
```

The daemon scans for `.hunt` files with `@schedule:` headers and runs them on their declared schedules. Files without `@schedule:` are ignored.

---

## Tags (`@tags:`)

Annotate hunt files for selective execution:

```text
@tags: smoke, auth, critical

STEP 1: ...
```

Run only tagged files:

```bash
manul --tags smoke tests/               # files tagged 'smoke'
manul --tags smoke,regression tests/    # files tagged 'smoke' OR 'regression'
```

Tags also appear as filter chips in the HTML report.

---

## Desktop / Electron Apps

Set `executable_path` in the configuration and use `OPEN APP` instead of `NAVIGATE`:

**`manul_engine_configuration.json`:**
```json
{
  "model": null,
  "browser": "chromium",
  "executable_path": "/path/to/electron-app"
}
```

**`tests/desktop.hunt`:**
```text
@context: Testing an Electron desktop application
@title: Desktop App Smoke Test

STEP 1: Attach to the app window
    OPEN APP
    VERIFY that 'Welcome' is present

STEP 2: Interact with the UI
    CLICK the 'Settings' button
    VERIFY that 'Preferences' is present

DONE.
```

`OPEN APP` attaches to the Electron app's default window, waits for DOM settlement, and then all standard DSL commands work identically.

---

## Network Mocking

Intercept and mock network requests:

```text
MOCK GET "api/users" with 'mocks/users.json'
MOCK POST "api/login" with 'mocks/login_response.json'
```

- Supported methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
- Mock file resolved relative to hunt file directory → CWD.
- Uses Playwright's `page.route()` under the hood.

Wait for a specific network response:

```text
WAIT FOR RESPONSE "api/data"
```

Blocks until a response matching the URL substring arrives.

---

## File Upload

```text
UPLOAD 'avatar.png' to 'Profile Picture'
```

- Both file path and target must be quoted.
- File path is resolved relative to the `.hunt` file's directory first, then CWD.
- Mapped to Playwright's `locator.set_input_files()`.

---

## Debug and Pause

### DEBUG / PAUSE step

```text
STEP 2: Debug point
    FILL 'Email' field with '{email}'
    DEBUG
    CLICK the 'Submit' button
```

Pauses execution at that point. In `--debug` mode, highlights the resolved element and prompts for input.

### Runtime debug modes

| Mode | How | Effect |
|------|-----|--------|
| `--debug` | Terminal | Pauses before every step, shows element highlight |
| `--break-lines 5,10,15` | VS Code extension | Pauses at specified file lines only |

---

## Configuration Reference

`manul_engine_configuration.json` at the project root. All keys are optional.

| Key | Default | Description |
|-----|---------|-------------|
| `model` | `null` | Ollama model name. `null` = heuristics-only (no AI). |
| `headless` | `false` | Hide the browser window. |
| `browser` | `"chromium"` | Browser engine: `chromium`, `firefox`, or `webkit`. |
| `browser_args` | `[]` | Extra launch flags (array of strings). |
| `channel` | `null` | Installed browser channel: `"chrome"`, `"chrome-beta"`, `"msedge"`. |
| `executable_path` | `null` | Path to Electron or custom browser executable. |
| `timeout` | `5000` | Default action timeout (ms). |
| `nav_timeout` | `30000` | Navigation timeout (ms). |
| `ai_threshold` | auto | Score threshold before LLM fallback. |
| `ai_always` | `false` | Always invoke the LLM picker (requires `model`). |
| `ai_policy` | `"prior"` | Heuristic score treatment: `"prior"` (hint) or `"strict"` (force). |
| `controls_cache_enabled` | `true` | Persistent per-site controls cache (file-based). |
| `controls_cache_dir` | `"cache"` | Cache directory (relative or absolute). |
| `semantic_cache_enabled` | `true` | In-session semantic cache (+200k score boost). |
| `custom_controls_dirs` | `["controls"]` | Directories scanned for `@custom_control` modules. |
| `tests_home` | `"tests"` | Default directory for new hunts and scans. |
| `auto_annotate` | `false` | Insert `# 📍 Auto-Nav:` comments on URL changes. |
| `retries` | `0` | Retry failed hunts N times. |
| `screenshot` | `"on-fail"` | `"none"`, `"on-fail"`, or `"always"`. |
| `html_report` | `false` | Generate `reports/manul_report.html`. |
| `explain_mode` | `false` | Per-channel scoring breakdown in output. |
| `log_name_maxlen` | `0` | Truncate element names in logs (0 = no limit). |
| `log_thought_maxlen` | `0` | Truncate LLM thought strings (0 = no limit). |

### Environment Variable Overrides

Environment variables (`MANUL_*`) always override JSON values:

| Variable | Overrides |
|----------|-----------|
| `MANUL_MODEL` | `model` |
| `MANUL_HEADLESS` | `headless` |
| `MANUL_BROWSER` | `browser` |
| `MANUL_BROWSER_ARGS` | `browser_args` (comma/space-separated) |
| `MANUL_CHANNEL` | `channel` |
| `MANUL_EXECUTABLE_PATH` | `executable_path` |
| `MANUL_AUTO_ANNOTATE` | `auto_annotate` |
| `MANUL_EXPLAIN` | `explain_mode` |
| `MANUL_CUSTOM_CONTROLS_DIRS` | `custom_controls_dirs` (comma-separated) |
| `MANUL_LOG_LEVEL` | Logging verbosity |

### AI threshold auto-calculation

When `model` is set but `ai_threshold` is not:

| Model size | Threshold |
|------------|-----------|
| < 1B params | 500 |
| 1–4B | 750 |
| 5–9B | 1000 |
| 10–19B | 1500 |
| 20B+ | 2000 |
| `null` (no model) | 0 |

---

## CLI Quick Reference

```bash
manul tests/                                  # run all hunts in directory
manul tests/login.hunt                        # single file
manul --headless tests/                       # headless
manul --tags smoke tests/                     # filter by tags
manul --html-report tests/                    # generate HTML report
manul --screenshot always tests/              # screenshot every step
manul --retries 2 tests/                      # retry failures
manul --explain tests/login.hunt              # scoring breakdown
manul --debug tests/login.hunt                # interactive debug
manul --break-lines 5,10 tests/login.hunt     # breakpoint debug
manul --workers 4 tests/                      # parallel execution
manul --browser firefox tests/                # use Firefox
manul scan https://example.com                # scan → draft hunt
manul daemon tests/ --headless                # scheduled daemon
```
