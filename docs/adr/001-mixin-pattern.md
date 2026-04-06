# ADR-001: Mixin pattern for ManulEngine

**Status:** Accepted
**Date:** 2026-04

## Context

ManulEngine's core class needs to orchestrate element resolution, action
execution, persistent caching, and interactive debugging.  Placing all of
this in a single file would exceed ~3 000 lines, making navigation and
code review painful.

## Decision

Split ManulEngine into composable mixins:

```
ManulEngine(_DebugMixin, _ControlsCacheMixin, _ActionsMixin)
```

Each mixin lives in its own module (`debug.py`, `cache.py`, `actions.py`)
and owns a well-scoped set of methods.  `core.py` composes them via MRO.

## Consequences

- **Pro:** Each mixin file stays under ~1 200 lines and can be reviewed
  independently.
- **Pro:** Adding a new concern (e.g. a future `_TracingMixin`) requires
  only a new file and one line in the class declaration.
- **Con:** Python MRO can be confusing; contributors must understand that
  `self` is shared across all mixins.
- **Con:** Cross-mixin calls are implicit — the compiler does not enforce
  the interface a mixin expects from `self`.

## Mitigations

- TYPE_CHECKING imports for `Page`, `Frame`, etc. keep type checkers
  informed about the shared surface.
- Each mixin is prefixed with `_` to signal it is not a public API.
