---
name: add-custom-control
description: Author a @custom_control handler that overrides ManulEngine's element resolution for a specific (page, target) pair — for widgets the heuristics can't drive (React date pickers, canvas, custom web components). Wires the handler into a controls/ module, aligns the page label with pages/*.json, and adds a test. Invoke when the user says "add a custom control", "override resolution for X", "the heuristics can't click this widget", "handle this React/canvas component", "додай кастомний контрол".
---

# add-custom-control

A `@custom_control` handler is an escape hatch: when a target on a given page needs bespoke Playwright code (a widget no scorer can resolve), you register a Python function for that exact `(page_name, target)` pair. At dispatch the engine matches the pair and calls your handler **instead of** heuristic resolution.

This skill is about *authoring a handler* (user-space code in a `controls/` module), not modifying the engine's dispatch.

## When to invoke

- A step like `CLICK the 'React Datepicker'` can't be resolved by heuristics and needs hand-written Playwright (drag, canvas coordinates, shadow-DOM traversal, multi-step interaction).
- User says "override how X is clicked/filled on page Y", "add a custom control for <widget>".

## The handler contract

```python
# controls/login_controls.py   (any .py under a custom_controls_dir, default ./controls)
from manul_engine import ControlContext, custom_control

@custom_control(page="Login Page", target="Username")
async def handle_username(ctx: ControlContext) -> None:
    # ctx.page   — live Playwright Page (use ctx.page.locator(...), .evaluate(...), …)
    # ctx.action — "input" | "clickable" | "select" | "hover" | "drag" | "locate"
    # ctx.value  — value for input/select (None for click/hover/locate)
    # ctx.target — the quoted target string ("Username")
    # ctx.page_name — resolved page label (matches page= on the decorator)
    # ctx.url    — page.url at dispatch
    # ctx.step   — original step text with {variables} already substituted
    await ctx.page.fill("#react-username input", ctx.value or "")
```

- The handler takes **one** argument, a `ControlContext`. The old `(page, action, value)` signature is gone — never use it (registration raises on a wrong arity).
- It may be `async` or sync; both are dispatched correctly. Prefer `async` for any Playwright `await`.
- Branch on `ctx.action` if the same target supports multiple modes (fill vs click vs locate).

## Execution order

1. **Find the page label.** The `page=` argument must equal what `prompts.lookup_page_name(url)` returns for the live page — i.e. a label defined in `pages/<site>.json`. Check the fragment (`manul pages list`) or run the mission once and read the page banner. If the URL resolves to an `Auto: …` placeholder, add a real label to `pages/<site>.json` first, otherwise the handler never matches.
2. **Write the module.** Create/extend a `.py` file under a custom-controls directory (default `controls/`, configurable via `custom_controls_dirs` / `MANUL_CUSTOM_CONTROLS_DIRS`). Decorate the handler with `@custom_control(page=…, target=…)`. Matching is **case-insensitive** on both page and target.
3. **Keep it idempotent & self-contained.** Modules are JIT-loaded once per directory (`_LOADED_DIRS`/`_LOADED_FILES`); import side effects run at load. Don't rely on engine internals — use only `ctx`.
4. **Return shape.** Returning `None` is fine (success unless it raises). If your widget interaction can fail, raise — the engine records the step failure. Don't swallow exceptions silently.
5. **Test.** Add to `manul_engine/test/test_17_custom_controls.py` (the canonical template): register a handler against a synthetic DOM, assert `get_custom_control(page, target)` resolves (case-insensitive), drive a mission/step through it, and assert a deliberate **miss** produces a hint via `diagnose_custom_control_miss`.

## Common pitfalls

- **Page-label mismatch** — the single most common failure. `@custom_control(page="Login")` won't fire if `lookup_page_name(url)` returns `"Login Page"`. Align the decorator with the `pages/*.json` label exactly (case aside). When a control "isn't being called", run with `--debug` and read the dispatch log + the `diagnose_custom_control_miss` hint.
- Using the legacy `(page, action_type, value)` signature — registration enforces the single `ControlContext` arg.
- Putting the module outside the scanned dirs — it must live under a `custom_controls_dir` (default `controls/`), or be on a path listed in `MANUL_CUSTOM_CONTROLS_DIRS`.
- Forgetting `await` on Playwright calls in an `async` handler — silent no-op coroutines.
- Hardcoding a value the step passes — read `ctx.value`, don't re-derive it.

## Reference

- API + registry + diagnostics: `manul_engine/controls.py` (`ControlContext`, `custom_control`, `get_custom_control`, `diagnose_custom_control_miss`, `list_custom_controls`)
- Public exports: `manul_engine/__init__.py:__all__` (`ControlContext`, `custom_control`, `list_custom_controls`)
- Engine dispatch (reference only — don't edit): `core.py` resolves a handler via `get_custom_control` in **both** the main loop (~L1483) and the conditional-branch `_dispatch_step` (~L1992).
- Page labels: `pages/<site>.json` + `prompts.lookup_page_name()`; inspect with `manul pages list`.
- Test template: `manul_engine/test/test_17_custom_controls.py`.
- Contract: custom controls are referenced in `contracts/MANUL_API_CONTRACT.md` — keep the `ControlContext` surface in sync if you change it (changing it is "Ask first").
