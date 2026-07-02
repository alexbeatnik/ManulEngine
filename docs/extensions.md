# Extensions — `CALL PYTHON`, Custom Controls & Lifecycle Hooks

> *How to extend ManulEngine with native Python code.*
> The Go engine ([ManulEngineGo](https://github.com/alexbeatnik/ManulEngineGo)) exposes the same
> `.hunt`-level surface with `CALL GO` + `RegisterGoCall`/`RegisterCustomControl` — see its
> [docs/extensions.md](https://github.com/alexbeatnik/ManulEngineGo/blob/main/docs/extensions.md).

There are three extension mechanisms:

1. **`CALL PYTHON`** — invoke a Python function by dotted path from a `.hunt` file (inline step or `[SETUP]`/`[TEARDOWN]` hook)
2. **`@custom_control`** — intercept a specific *page + target* action and handle it entirely in Python, bypassing DOM resolution
3. **Lifecycle hooks** — `@before_all` / `@after_all` / `@before_group` / `@after_group` in `manul_hooks.py` for suite-wide setup/teardown

---

## `CALL PYTHON`

From a `.hunt` file:

```hunt
@script: {helpers} = mypackage.helpers

[SETUP]
    CALL PYTHON {helpers}.seed_user "{email}" "{password}"
[END SETUP]

STEP 1:
    CALL PYTHON {helpers}.generate_token "admin" into {token}
    CALL PYTHON api_helpers.fetch_otp "{email}" into {otp}
```

The `@script:` directive maps `{helpers}` to `mypackage.helpers`; the parser rewrites the alias
before execution. A callable alias is also supported:
`@script: {issue_token} = scripts.auth.issue_token` → `CALL PYTHON {issue_token}`.

### Writing a handler

Any **synchronous** Python function works — no registration step:

```python
# scripts/auth_helpers.py
def generate_token(role: str) -> str:
    return f"tok_{role}_{int(time.time())}"

def seed_user(email: str, password: str) -> dict:
    ...
    return {"user_id": uid}      # a dict sets multiple variables at once
```

### Module resolution order

1. The hunt file's directory
2. The current working directory
3. Standard `sys.path` / installed packages

File-based modules are executed in an **isolated module sandbox** (never inserted into
`sys.modules`), so tests can't contaminate each other.

### Return values

| Return type | Behavior |
|-------------|----------|
| `str` / scalar | Bound to the variable declared in `into {var}` (alias: `to {var}`) |
| `dict` | Each key→value pair is written into runtime memory |
| raising | The step (or hook line) fails; `[SETUP]` failure marks the mission `broken` |

Arguments are shell-tokenized (single/double quotes respected) and `{var}`-interpolated at call
time. `with args:` sugar is accepted. **Async callables are rejected** with a descriptive error.

---

## Custom Controls

Custom controls intercept a specific **page + target** combination before DOM resolution runs.
Use them for complex UI components (date pickers, rich text editors, canvas widgets) where
heuristic targeting is insufficient.

```python
# controls/checkout.py
from manul_engine import custom_control

@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_datepicker(ctx):
    # ctx.page      – the live CDPPage (evaluate / click_xpath / …)
    # ctx.action    – "click" | "input" | "select" | …
    # ctx.value     – the fill/select value, when applicable
    # ctx.target    – the resolved target label
    # ctx.page_name – registry page label; ctx.url; ctx.step – raw step text
    await ctx.page.evaluate(
        "(v) => document.querySelector('.react-datepicker__input-container input').value = v",
        ctx.value,
    )
```

- Handlers live in the directories listed by `custom_controls_dirs` (default: `controls/`),
  scanned at startup.
- `page="*"` registers an any-page control; the page label is resolved via `document.title`,
  then the `pages/` registry (see [loops-and-pages.md](loops-and-pages.md)), then a URL fallback.
- `manul controls list` prints the registry (PAGE / TARGET / HANDLER / SOURCE); a miss against a
  sibling page prints a one-line hint.
- The hunt file keeps a single readable step — `CLICK the 'React Datepicker'` — while the handler
  owns the messy interaction.

---

## Lifecycle hooks (`manul_hooks.py`)

Suite-level hooks are auto-discovered from `manul_hooks.py` in the run directory:

```python
# manul_hooks.py
from manul_engine import before_all, after_all, before_group, after_group

@before_all
def start_stack(ctx):          # ctx: GlobalContext
    ctx.variables["base_url"] = spin_up_env()   # exposed as {base_url} in every hunt

@after_group(tag="smoke")
def collect_smoke_metrics(ctx):
    ...

@after_all
def teardown(ctx):
    tear_down_env()
```

| Hook | Timing | Failure behavior |
|---|---|---|
| `@before_all` | once before the whole suite | abort — nothing runs |
| `@after_all` | once after all missions (always) | logged only |
| `@before_group(tag=…)` | before each mission carrying the tag | tagged mission skipped |
| `@after_group(tag=…)` | after each mission carrying the tag | logged only |

With `--workers > 1`, `@before_all` results reach the worker subprocesses via the
`MANUL_GLOBAL_VARS` env variable (JSON-serialized `ctx.variables`).

> **Go engine note:** ManulEngine (Go) has no decorator lifecycle — it covers the same needs with
> process-init registration (`RegisterGoCall`) plus `[SETUP]`/`[TEARDOWN]` blocks.
