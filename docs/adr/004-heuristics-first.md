# ADR-004: Heuristics-first, LLM-last resolution

**Status:** Accepted
**Date:** 2026-04

## Context

Element resolution must be deterministic, fast, and reproducible in CI.
Relying on an LLM for every action is non-deterministic, slow (~200 ms+
per call even locally), and requires Ollama to be installed.

## Decision

The default resolution path is **heuristics-only** (`model: null`):

1. Exact-match pass — quick filter by `name`, `aria-label`, `data-qa`.
2. `DOMScorer.score_all()` — normalised 0.0–1.0 float scoring across
   five weighted channels (cache 2.0, semantics 0.60, text 0.45,
   attributes 0.25, proximity 0.10).  Final integer score =
   weighted sum × `SCALE` (177 778).
3. The engine picks the highest-scoring element.  If the score exceeds
   `200 000` (semantic cache hit) or `10 000` (context reuse), it
   short-circuits immediately.
4. Only when the best score falls below `ai_threshold` **and** a model
   is configured does the engine call the LLM as a fallback.

## Consequences

- **Pro:** 100 % deterministic out of the box — no external dependency.
- **Pro:** Scoring is transparent (explain mode prints per-channel
  breakdowns).
- **Pro:** The LLM path is still available as a safety net for genuinely
  ambiguous elements on unfamiliar pages.
- **Con:** Some edge-case elements (canvas widgets, deeply nested custom
  components) may not score well without custom controls.
- **Con:** The threshold auto-calculation by model size is a heuristic
  itself and may need tuning for new model families.

## Mitigations

- Persistent per-site controls cache amplifies successful resolutions
  across runs (+200 000 score boost via cache channel).
- Custom Controls (`@custom_control`) provide an escape hatch for any
  element the heuristic pipeline cannot handle.
- Contextual qualifiers (`NEAR`, `ON HEADER`, `ON FOOTER`, `INSIDE`)
  raise the proximity channel weight to 1.5 for disambiguation.
