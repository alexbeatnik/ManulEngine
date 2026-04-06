# ADR-003: TreeWalker-based DOM snapshot

**Status:** Accepted
**Date:** 2024-12

## Context

The engine needs a performant, reliable way to extract interactive
elements from arbitrarily complex pages — including Shadow DOM, iframes,
and sites with thousands of nodes.

## Decision

Use `document.createTreeWalker()` (injected as `SNAPSHOT_JS` from
`js_scripts.py`) with a `PRUNE` set to skip non-interactive subtrees
(`SCRIPT, STYLE, SVG, NOSCRIPT, TEMPLATE, META, PATH, G, BR, HR`).

Visibility is checked via `checkVisibility({ checkOpacity: true,
checkVisibilityCSS: true })` with an `offsetWidth/offsetHeight` fallback
for older engines.  Hidden `<input type="checkbox|radio|file">` elements
are kept (special-input exception).

## Consequences

- **Pro:** TreeWalker visits only relevant nodes — typically 100–500
  elements on a complex page — versus 10 000+ from `querySelectorAll("*")`.
- **Pro:** Pruning is declarative (a `Set` of tag names) and easy to
  extend.
- **Pro:** `checkVisibility()` is natively async-safe and avoids
  `getComputedStyle` in the hot loop.
- **Con:** The PRUNE set is a heuristic; edge cases (e.g. interactive SVG
  triggers) need explicit exceptions.
- **Con:** Cross-origin iframes are silently skipped, which may confuse
  users who expect actions inside them.

## Mitigations

- The PRUNE set was tuned across 50+ real-world sites and 15+ synthetic
  test suites (~2 800 assertions).
- `_snapshot()` iterates `page.frames` and tags each element with
  `frame_index` for cross-frame routing.
- Cross-origin frame skipping uses a 3-retry, 1.5s backoff on `closed`
  errors before giving up.
