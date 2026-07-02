# ManulEngine DSL — LLM Cheat-Sheet

A compact, copy-pasteable contract for an LLM that **authors `.hunt` files** or
**drives the engine over the agent CLI**. This is the human mirror of
`manul schema` (which emits the same facts as JSON). Pin one of these in a
prompt instead of dumping the full docs. The Go engine
([ManulEngineGo](https://github.com/alexbeatnik/ManulEngineGo)) shares the same
grammar and the same JSON shapes; the only differences are noted inline.

## Targeting model

Elements are resolved by their **human-visible label** via a deterministic
scorer — **never** CSS/XPath. Always quote labels: `Click the 'Login' button`.

## `.hunt` rules

1. `STEP` headers are numbered; action lines under them are **not**.
2. 4-space indent under each `STEP`.
3. Never hardcode data — declare `@var: {key} = value`, reference as `{key}`.
4. Always follow `FILL`/`TYPE` with `VERIFY '<label>' has value "<expected>"`.

## Verbs

| Verb | Syntax |
|------|--------|
| `NAVIGATE` | `NAVIGATE to <url>` (http/https/file) |
| `CLICK` | `Click the '<label>' button` / `link` |
| `DOUBLE CLICK` | `Double-click the '<label>'` |
| `RIGHT CLICK` | `Right-click the '<label>'` |
| `FILL` | `Fill '<label>' with '<value>'` |
| `TYPE` | `Type '<value>' into '<label>'` |
| `SELECT` | `Select '<option>' from the '<label>' dropdown` |
| `CHECK` / `UNCHECK` | `Check the checkbox for '<label>'` |
| `HOVER` | `Hover over the '<label>'` |
| `DRAG` | `Drag the '<label>' and drop it into '<target>'` |
| `PRESS` | `Press <key>` (e.g. `Press Enter`) |
| `SCROLL` | `Scroll down` / `up` (`inside '<container>'`) |
| `UPLOAD` | `Upload '<path>' to '<label>'` |
| `VERIFY` | `VERIFY '<label>' has value\|text\|placeholder "<expected>"` |
| `VERIFY SOFTLY` | non-fatal `VERIFY` |
| `EXTRACT` | `EXTRACT the '<label>' into {var}` |
| `WAIT` | `WAIT <seconds>` |
| `WAIT FOR` | `WAIT FOR '<label>' to be visible\|hidden` / `to disappear` |
| `WAIT FOR SELECTOR` | `WAIT FOR SELECTOR '<css>'` *(Python engine only)* |
| `WAIT FOR RESPONSE` | `WAIT FOR RESPONSE '<url-substr>'` |
| `SET` | `SET {var} = <value>` |
| `MOCK` | `MOCK <METHOD> '<path>' with '<file>'` |
| `PRINT` | `PRINT "<message with {vars}>"` |
| `SCREENSHOT` | `SCREENSHOT ["<name>"]` |
| `CALL PYTHON` | `CALL PYTHON <module.func> [args] [into {var}]` *(Go engine uses `CALL GO`)* |
| `FULL SCAN` / `SCAN PAGE` | landmark-grouped control table / draft hunt *(Python engine only)* |

### Control flow

| Block | Syntax | End | Notes |
|-------|--------|-----|-------|
| `REPEAT` | `REPEAT N TIMES:` | `END REPEAT` | `{i}` is a 0-based counter |
| `FOR EACH` | `FOR EACH {x} IN {list}:` | `END FOR` | `{list}` is comma-separated |
| `WHILE` | `WHILE <condition>:` | `END WHILE` | capped at 100 iterations |
| `IF` | `IF <condition>:` + `ELIF`/`ELSE` | `END IF` | same grammar as `WHILE` |
| `USE` | `USE <block>` | — | expand an `@import:`-ed STEP block |

## Agent CLI result shapes

`run-step` (compact by default; `--compact` accepted) → **step_outcome**:

```json
{ "ok": true, "action": "click", "value": "", "url": "https://…",
  "reason": "ok", "score": 0.82,
  "near": [{ "text": "Log In", "score": 0.18 }] }
```

- `url` is **omitted when unchanged** from the previous step.
- `near` (top candidates) appears only on **failure** or a **low-confidence**
  match (`score < 0.35`) — use it to retarget without a follow-up scan.
- `reason` ∈ `ok` · `not_found` · `ambiguous` · `timeout` · `verify_failed` ·
  `action_failed`.

`map` → **page_map** (compact, budgeted):

```json
{ "url": "https://…",
  "groups": [ { "name": "Page",
                "elements": [ { "label": "Email", "role": "textbox", "editable": true },
                              { "label": "Login", "role": "button" } ],
                "truncated": 3 } ] }
```

`editable` marks inputs an agent can `FILL` (omitted when false). Groups are
ordered for an agent: `Page` first, then content landmarks (main / forms /
results), then chrome (header / nav / footer). Bound the size with
`--max-per-group`.

`read` → `{ "value": "...", "found": true, "reason": "ok" }`.
Read uses a dedicated extraction probe (zero-scan), so it carries no `near`
candidates — use `map` or `run-step` to retarget after a miss. `read --selector
<css> --max-chars N` returns sanitized region text as `{ "text": "...",
"selector": "<css>" }`.

## Get the machine-readable version

```bash
manul schema   # same contract as JSON, version-stamped
```
