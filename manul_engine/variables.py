# manul_engine/variables.py
"""
Strict scoped variable state management for ManulEngine.

Implements a four-level precedence hierarchy (highest → lowest):
  Level 1 — Row Vars:     Injected per-iteration from @data CSV/JSON.
  Level 2 — Step Vars:    Created mid-flight via EXTRACT or CALL PYTHON into {var}.
  Level 3 — Mission Vars: Declared in the file header via @var:.
  Level 4 — Global Vars:  Passed via CLI, env, or @before_all lifecycle hooks.

resolve() strictly respects this order: a higher-level variable always
shadows a lower-level one with the same name.
"""

from __future__ import annotations


class ScopedVariables:
    """Four-level variable store with strict precedence resolution.

    Each level is a plain dict.  ``resolve(name)`` checks levels top-down;
    ``substitute(text)`` replaces all ``{var}`` placeholders using the
    resolved values.  ``set()`` writes to a specific level.
    """

    LEVEL_ROW = "row"
    LEVEL_STEP = "step"
    LEVEL_MISSION = "mission"
    LEVEL_GLOBAL = "global"

    _LEVELS = (LEVEL_ROW, LEVEL_STEP, LEVEL_MISSION, LEVEL_GLOBAL)

    def __init__(self) -> None:
        self._stores: dict[str, dict[str, str]] = {
            self.LEVEL_ROW: {},
            self.LEVEL_STEP: {},
            self.LEVEL_MISSION: {},
            self.LEVEL_GLOBAL: {},
        }

    # ── Read ──────────────────────────────────────────────────────────────

    def resolve(self, name: str) -> str | None:
        """Return the value for *name* at the highest-priority level, or None."""
        for level in self._LEVELS:
            store = self._stores[level]
            if name in store:
                return store[name]
        return None

    def resolve_level(self, name: str) -> tuple[str | None, str | None]:
        """Return ``(value, level_name)`` for *name*, or ``(None, None)``."""
        for level in self._LEVELS:
            store = self._stores[level]
            if name in store:
                return store[name], level
        return None, None

    def as_flat_dict(self) -> dict[str, str]:
        """Return a merged dict respecting precedence (lowest first, highest overwrites)."""
        merged: dict[str, str] = {}
        for level in reversed(self._LEVELS):
            merged.update(self._stores[level])
        return merged

    def substitute(self, text: str) -> str:
        """Replace all ``{var}`` placeholders with resolved values."""
        flat = self.as_flat_dict()
        for k, v in flat.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text

    # ── Write ─────────────────────────────────────────────────────────────

    def set(self, name: str, value: str, level: str) -> None:
        """Set a variable at a specific level."""
        if level not in self._LEVELS:
            raise ValueError(f"Unknown variable level: {level!r}")
        self._stores[level][name] = str(value)

    def set_many(self, mapping: dict[str, str], level: str) -> None:
        """Bulk-set variables at a specific level."""
        if level not in self._LEVELS:
            raise ValueError(f"Unknown variable level: {level!r}")
        self._stores[level].update({k: str(v) for k, v in mapping.items()})

    # ── Clear / reset ─────────────────────────────────────────────────────

    def clear_level(self, level: str) -> None:
        """Remove all variables at a given level."""
        if level in self._stores:
            self._stores[level].clear()

    def clear_runtime(self) -> None:
        """Clear row and step vars (used between @data iterations)."""
        self._stores[self.LEVEL_ROW].clear()
        self._stores[self.LEVEL_STEP].clear()

    def clear_all(self) -> None:
        """Clear every level."""
        for store in self._stores.values():
            store.clear()

    # ── Introspection (DEBUG VARS) ────────────────────────────────────────

    def dump(self) -> str:
        """Return a formatted multi-line string showing all levels."""
        lines: list[str] = []
        labels = {
            self.LEVEL_ROW: "Level 1 — Row Vars (@data)",
            self.LEVEL_STEP: "Level 2 — Step Vars (EXTRACT / CALL PYTHON into)",
            self.LEVEL_MISSION: "Level 3 — Mission Vars (@var:)",
            self.LEVEL_GLOBAL: "Level 4 — Global Vars (CLI / env / @before_all)",
        }
        for level in self._LEVELS:
            store = self._stores[level]
            label = labels[level]
            lines.append(f"  ┌─ {label}")
            if store:
                for k, v in store.items():
                    lines.append(f"  │  {{{k}}} = {v}")
            else:
                lines.append(f"  │  (empty)")
            lines.append(f"  └{'─' * 50}")
        return "\n".join(lines)

    # ── dict-like compatibility layer ─────────────────────────────────────
    # ManulEngine historically uses self.memory as a plain dict.
    # These methods let ScopedVariables be used in place of self.memory
    # while existing code that reads via dict[key] or .get() still works.

    def __contains__(self, name: str) -> bool:
        return self.resolve(name) is not None

    def __getitem__(self, name: str) -> str:
        val = self.resolve(name)
        if val is None:
            raise KeyError(name)
        return val

    def __setitem__(self, name: str, value: str) -> None:
        # Default write target: step level (runtime assignments)
        self._stores[self.LEVEL_STEP][name] = str(value)

    def get(self, name: str, default: str | None = None) -> str | None:
        val = self.resolve(name)
        return val if val is not None else default

    def items(self):
        return self.as_flat_dict().items()

    def keys(self):
        return self.as_flat_dict().keys()

    def values(self):
        return self.as_flat_dict().values()

    def update(self, mapping) -> None:
        # Default update goes to step level for backward compat.
        if isinstance(mapping, dict):
            self._stores[self.LEVEL_STEP].update({k: str(v) for k, v in mapping.items()})

    def clear(self) -> None:
        self.clear_all()

    def __eq__(self, other) -> bool:
        if isinstance(other, ScopedVariables):
            return self._stores == other._stores
        if isinstance(other, dict):
            return self.as_flat_dict() == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"ScopedVariables({self.as_flat_dict()!r})"
