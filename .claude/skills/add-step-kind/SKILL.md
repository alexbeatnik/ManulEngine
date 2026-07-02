---
name: add-step-kind
description: Add a new DSL step kind (e.g. WAIT FOR DOWNLOAD, EXTRACT TABLE, …) to ManulEngine end-to-end. Wires classify_step + dispatch in BOTH the main run_mission loop AND the conditional-branch _dispatch_step executor, then adds a synthetic-DOM test. Invoke when the user says "add step", "new DSL keyword", "support a new action".
---

# add-step-kind

`ManulEngine` has **two** parallel step executors that must stay in sync:

1. `core.py:run_mission` — the main mission loop (top-level steps).
2. `core.py:_dispatch_step` — the executor invoked from inside `IF / ELIF / ELSE` and `LOOP` bodies.

Adding a step kind in only one of them is the most common silent regression in this repo. The conditional-branch path quietly falls back to "Action failed" or runs the wrong handler.

## When to invoke

- User says "add a step kind", "new DSL command", "support `WAIT FOR <X>`", "add `EXTRACT TABLE`", or asks to extend the hunt-file vocabulary.

## Inputs

- `args` form: `<KEYWORD>` plus a one-line behavior description.
  Example: `/add-step-kind WAIT FOR DOWNLOAD — block until a download finishes and bind the saved path to {download_path}`.
- If the keyword conflicts with an existing one (`grep -n '"<keyword>"' manul_engine/helpers.py`), surface the conflict and ask before proceeding.

## Execution order

1. **Classifier.** Add the new branch in `manul_engine/helpers.py:classify_step` so `step_kind == "<your_kind>"` returns for matching lines. Add the regex (if any) next to the existing `RE_*` patterns in that module.
2. **Handler.** Implement `async def _handle_<your_kind>(self, page, step, …) -> bool` (or appropriate return) in the most relevant module — usually `actions.py:_ActionsMixin` (DOM/page actions) or `core.py` (control-flow / meta). Keep it consistent with sibling handlers' return-shape.
3. **Main loop dispatch.** Add an `elif step_kind == "<your_kind>":` branch in `core.py:run_mission` (large `try/except` block, the one with all the `step_kind ==` arms — currently around line ~1770).
4. **Conditional-branch dispatch.** Add the **same** branch in `core.py:_dispatch_step` (the parallel executor used inside `IF` / `LOOP` blocks — currently around line ~1300). Keep the implementation identical; if behavior must differ inside conditionals, document why with a one-line comment.
5. **DSL contract.** Add the keyword and grammar to `contracts/MANUL_DSL_CONTRACT.md`. Frozen public surface — must be kept in sync.
6. **README.** Add the keyword to the DSL keyword table in `README.md` and to `README_DEV.md` if it has implementation notes worth surfacing.
7. **Test.** Create `manul_engine/test/test_NN_<your_kind>.py` (use the next free `NN`). Cover at minimum: a happy-path mission, a failing-condition mission, and the conditional-branch path (run the keyword inside an `IF / END IF`).
8. **Bump version.** New DSL surface = bump via the `bump-version` skill.

## Common mistakes to avoid

- Wiring the keyword into `run_mission` but forgetting `_dispatch_step` — symptom: the keyword works at top level but silently fails or no-ops inside `IF` blocks. The repo had at least one regression from this exact omission.
- Forgetting to update `MANUL_DSL_CONTRACT.md` — contracts are the source of truth for the public surface; CI / future Claude sessions consult them.
- Returning `None` from the handler instead of a `bool` — the dispatch arms compare with `if not await self._handle_…` and treat `None` as failure.
- Putting handler state on `self.<attr>` without resetting it in `reset_session_state`. Per-mission state must be cleared there.
- Skipping the conditional-branch test. The two-executor split is the highest-yield place to test.

## Reference

- Step classification: `manul_engine/helpers.py:classify_step`
- Main loop dispatch: `manul_engine/core.py:run_mission` (search for `elif step_kind ==`)
- Conditional-branch dispatch: `manul_engine/core.py:_dispatch_step`
- Action handlers: `manul_engine/actions.py:_ActionsMixin`
- DSL contract: `contracts/MANUL_DSL_CONTRACT.md`
- Test conventions: `manul_engine/test/test_26_logical_steps.py` is a good template for control-flow keywords; `test_37_open_app.py` for action keywords.
