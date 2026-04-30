---
name: sync-contracts
description: Verify and reconcile the frozen public-surface contracts under contracts/MANUL_*_CONTRACT.md against the current code. Invoke when the user says "check contracts", "are contracts up to date", "sync contracts", or after any change that touches the DSL grammar, CLI flags, ManulEngine/ManulSession ctor, EngineConfig fields, hooks, reporter JSON, or scoring weights.
---

# sync-contracts

The eight files under `contracts/` describe the **frozen public surface** of ManulEngine. They are the single source of truth that AI assistants, downstream users, and CI consult. Code drift away from these contracts is a silent regression.

| Contract | Covers |
| --- | --- |
| `MANUL_API_CONTRACT.md` | `ManulSession`, `ManulEngine` ctor kwargs, public methods, `__all__` exports |
| `MANUL_CLI_CONTRACT.md` | `manul` CLI subcommands and flags |
| `MANUL_CONFIG_CONTRACT.md` | `EngineConfig` fields, env vars, `manul_engine_configuration.json` schema |
| `MANUL_DEBUG_CONTRACT.md` | Debug protocol (markers, tokens, extension JSON shape) |
| `MANUL_DSL_CONTRACT.md` | `.hunt` file grammar — keywords, headers, blocks |
| `MANUL_HOOKS_CONTRACT.md` | `@before_all` / `@after_group` / `CALL PYTHON` |
| `MANUL_REPORTING_CONTRACT.md` | `MissionResult` / `BlockResult` / `StepResult` JSON shape |
| `MANUL_SCORING_CONTRACT.md` | Heuristic scoring channels and weights |

## When to invoke

- User says "check contracts", "sync contracts", "are docs in sync", "перевір контракти".
- After any of these code changes:
  - Adding/removing/renaming a kwarg on `ManulEngine.__init__` or `ManulSession.__init__`.
  - Adding/removing an entry in `manul_engine/__init__.py:__all__`.
  - Adding/removing/renaming an `EngineConfig` field.
  - Adding/removing a CLI flag in `manul_engine/cli.py`.
  - Adding/removing/renaming a step kind (combine with the `add-step-kind` skill).
  - Editing `manul_engine/scoring.py` weights or thresholds.
  - Editing `manul_engine/reporting.py` dataclasses.
  - Editing the debug-protocol markers in `manul_engine/debug.py`.

## Execution order

1. **Detect what changed.** `git diff --name-only main…HEAD` (or vs the branch the user names). Map each changed file to the contract(s) it potentially impacts using the table above.
2. **For each impacted contract**, read the contract and the corresponding source. Diff the **list of names** (kwargs, fields, keywords, flags) — not implementation. Surface every addition/removal/rename to the user.
3. **Update the contract** to mirror the code. Keep the contract style — these files use a tight reference-doc tone, not tutorials. Don't add narrative.
4. **Cross-file mirrors.** `.github/copilot-instructions.md` and `custom-instructions/repo/.github/copilot-instructions.md` reference contract names; spot-check them with `grep`.
5. **Version bump.** Any contract change is a public-surface change → invoke the `bump-version` skill before the PR is opened.
6. **Report.** Output a short table: `<contract> | <change> | <line>` so the user can verify nothing slipped in.

## What is NOT a contract change

- Internal helpers in `helpers.py`, `cache.py`, `scoring.py` private functions, `_DebugMixin` private methods (anything `_underscore`-prefixed).
- Refactors that preserve public names and behavior.
- Bug fixes that align code with what the contract already says — the contract was right, the code was wrong.

## Common mistakes to avoid

- "Updating the contract to match a bug" — if the contract is correct and the code drifted, fix the code, not the contract.
- Skipping the version bump after a contract change. Public surface change without a version bump is invisible to downstream users.
- Editing only one of the mirrored copilot-instructions files. Always touch both, or use `bump_version.py` which knows about both.
- Adding marketing prose. These contracts are reference material — terse, factual, exhaustive.

## Reference

- Contracts: `/home/alexbeatnik/Documents/ManulEngine/contracts/MANUL_*_CONTRACT.md`
- Public API mirror: `manul_engine/__init__.py:__all__`
- Mirrored AI instructions: `.github/copilot-instructions.md`, `custom-instructions/repo/.github/copilot-instructions.md`, `.cursorrules`
