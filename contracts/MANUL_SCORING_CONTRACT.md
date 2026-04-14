# ManulEngine — Scoring & Heuristics Contract

> **Machine-readable contract for the DOMScorer heuristic pipeline and element snapshot shape.**
> Consumed by explain-mode UIs, custom scoring extensions, benchmark tooling, and downstream analytics.

```json
{
  "version": "0.0.9.29",
  "generatedFrom": "manul_engine/scoring.py :: DOMScorer, WEIGHTS, SCALE, score_elements(); manul_engine/js_scripts.py :: SNAPSHOT_JS",

  "constants": {
    "WEIGHTS": {
      "cache":      2.0,
      "text":       0.45,
      "attributes": 0.25,
      "semantics":  0.60,
      "proximity":  0.10
    },
    "SCALE": 177778,
    "MAX_THEORETICAL_SCORE": 177778,
    "note": "Final integer score = (Σ channel_score × channel_weight) × penalty_multiplier × SCALE. Explain mode normalises back to [0.0, 1.0] by dividing by MAX_THEORETICAL_SCORE."
  },

  "scoringPipeline": {
    "order": [
      "1. _preprocess() — attach normalised strings and type classifications to each element",
      "2. _score_cache_reuse() — semantic cache hit or blind context reuse",
      "3. _score_text_match() — aria, placeholder, data-qa, name, icons, name_attr matching",
      "4. _score_attributes() — target_field, html_id, context words, NEAR anchor affinity",
      "5. _score_semantics() — element-type alignment, mode synergy, cross-mode penalties",
      "6. _score_proximity() — contextual: NEAR (Euclidean), ON HEADER/FOOTER (region), INSIDE (subtree), default (xpath depth)",
      "7. _calculate_penalties() — disabled/hidden multipliers",
      "8. Final = (Σ weighted channels) × penalty × SCALE",
      "9. Sort descending by score"
    ],
    "contextualBoost": "When a contextual qualifier (NEAR/ON HEADER/ON FOOTER/INSIDE) is active AND has effective resolved data, proximity channel weight increases from 0.10 to 1.5."
  },

  "channels": [
    {
      "name": "cache",
      "weight": 2.0,
      "method": "_score_cache_reuse(el)",
      "returnRange": "[0.0, 1.05]",
      "signals": [
        { "signal": "Semantic cache hit (learned_elements)", "boost": 1.0, "scaledApprox": 355000 },
        { "signal": "Blind context reuse (same xpath as last step)", "boost": 0.05, "scaledApprox": 17000 }
      ],
      "shortCircuits": [
        { "threshold": 200000, "condition": "Semantic cache reuse — core.py skips further scoring" },
        { "threshold": 10000,  "condition": "Blind/context reuse — core.py skips further scoring" }
      ]
    },
    {
      "name": "text",
      "weight": 0.45,
      "method": "_score_text_match(el)",
      "returnType": "tuple[float, bool]",
      "returnRange": "[0.0, 1.0+]",
      "signals": [
        { "signal": "Exact data-qa match",              "boost": 1.0,    "scaledApprox": 80000 },
        { "signal": "data-qa substring match",           "boost": 0.375,  "scaledApprox": 30000 },
        { "signal": "Exact aria_label match",            "boost": 0.625,  "scaledApprox": 50000 },
        { "signal": "Exact placeholder match",           "boost": 0.625,  "scaledApprox": 50000 },
        { "signal": "Exact name field text match",       "boost": 0.625,  "scaledApprox": 50000 },
        { "signal": "name_attr exact match",             "boost": 0.0375, "scaledApprox": 3000 },
        { "signal": "name_attr substring match",         "boost": 0.0125, "scaledApprox": 1000 },
        { "signal": "Icon class match",                  "boost": "varies" }
      ],
      "secondReturn": "isPerfect: bool — True when an exact high-confidence match was found (used by semantics channel)"
    },
    {
      "name": "attributes",
      "weight": 0.25,
      "method": "_score_attributes(el)",
      "returnRange": "[0.0, 1.0+]",
      "signals": [
        { "signal": "Exact html_id match",              "boost": 0.6,   "scaledApprox": 26000 },
        { "signal": "target_field exact match",          "boost": "multi-channel (higher via combined text+attr)" },
        { "signal": "Context words in prefix/class",     "boost": "varies" },
        { "signal": "NEAR anchor affinity (dev attrs)",  "boost": "varies (contextual)" }
      ]
    },
    {
      "name": "semantics",
      "weight": 0.60,
      "method": "_score_semantics(el, is_perfect, all_els)",
      "returnRange": "[-1.0, 1.0+]",
      "note": "Can be NEGATIVE for cross-mode penalties.",
      "signals": [
        { "signal": "Element type alignment with mode",  "boost": "0.05–0.30" },
        { "signal": "Checkbox/radio mode match",          "boost": "positive alignment" },
        { "signal": "Checkbox/radio mode mismatch",       "penalty": -0.50, "scaledApprox": -53000, "note": "Ruthless penalty for non-checkbox when step says 'Check'" },
        { "signal": "File upload context alignment",      "boost": "positive" }
      ]
    },
    {
      "name": "proximity",
      "weight": 0.10,
      "contextualWeight": 1.5,
      "method": "_score_proximity(el)",
      "returnRange": "[0.0, 1.0]",
      "modes": [
        { "qualifier": "NEAR",       "scoring": "Euclidean distance to anchor element + DOM depth affinity" },
        { "qualifier": "ON HEADER",  "scoring": "Element in <header>/<nav> ancestry OR top 15% of viewport" },
        { "qualifier": "ON FOOTER",  "scoring": "Element in <footer> ancestry OR bottom 15% of viewport" },
        { "qualifier": "INSIDE",     "scoring": "Container subtree membership (resolved row/container)" },
        { "qualifier": "none",       "scoring": "Default DOM xpath depth reuse" }
      ]
    }
  ],

  "penalties": {
    "disabled": { "multiplier": 0.0, "effect": "Zeroes entire score" },
    "hidden":   { "multiplier": 0.1, "effect": "90% reduction" },
    "normal":   { "multiplier": 1.0, "effect": "No penalty" }
  },

  "domScorer": {
    "constructor": {
      "parameters": [
        { "name": "step",               "type": "str",                         "required": true,  "description": "Raw step text." },
        { "name": "mode",               "type": "str",                         "required": true,  "description": "Interaction mode (input, clickable, select, hover, drag, locate)." },
        { "name": "search_texts",       "type": "list[str]",                   "required": true,  "description": "Quoted target texts extracted from step." },
        { "name": "target_field",       "type": "str | null",                  "required": true,  "description": "Optional target field identifier." },
        { "name": "is_blind",           "type": "bool",                        "required": true,  "description": "No visible text in step." },
        { "name": "learned_elements",   "type": "dict",                        "required": true,  "description": "Semantic cache: {(mode, texts, field, ctx) → {name, tag}}." },
        { "name": "last_xpath",         "type": "str | null",                  "required": true,  "description": "Previous element xpath for context reuse." },
        { "name": "explain",            "type": "bool",                        "default": false,  "description": "Enable per-channel scoring breakdown." },
        { "name": "contextual_hint",    "type": "ContextualHint | null",       "default": null,   "description": "Parsed NEAR/ON HEADER/ON FOOTER/INSIDE qualifier." },
        { "name": "anchor_rect",        "type": "dict | null",                 "default": null,   "description": "Anchor element bounding rect for NEAR scoring." },
        { "name": "container_elements", "type": "list[dict] | null",           "default": null,   "description": "Pre-filtered container subtree for INSIDE scoring." },
        { "name": "viewport_height",    "type": "int",                         "default": 0,      "description": "Viewport height for HEADER/FOOTER region detection." }
      ]
    },
    "publicMethods": [
      {
        "name": "score_all",
        "signature": "(els: list[dict]) -> list[dict]",
        "description": "Pre-processes, scores, and sorts elements descending by score. Adds 'score' (int) key to each element. When explain=True, also adds '_explain' dict with per-channel breakdown."
      }
    ]
  },

  "backwardCompatAPI": {
    "function": "score_elements",
    "signature": "(els, step, mode, search_texts, target_field, is_blind, learned_elements, last_xpath, explain=False, contextual_hint=None, anchor_rect=None, container_elements=None, viewport_height=0) -> list[dict]",
    "description": "Module-level function that delegates to DOMScorer.score_all(). Backward-compatible entry point."
  },

  "elementSnapshotShape": {
    "source": "SNAPSHOT_JS in manul_engine/js_scripts.py",
    "collectionMethod": "document.createTreeWalker() per frame, injected via page.evaluate()",
    "pruneSet": ["SCRIPT", "STYLE", "NOSCRIPT", "SVG", "TEMPLATE", "META", "PATH", "G", "BR", "HR"],
    "visibilityChecks": [
      "element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })",
      "Fallback: offsetWidth > 0 && offsetHeight > 0",
      "Exception: hidden input[type='file|checkbox|radio'] are KEPT"
    ],
    "fields": [
      { "key": "id",                  "type": "int",      "description": "Stable runtime ID (manulIdCounter per page load)." },
      { "key": "name",                "type": "string",   "description": "Display name (max 150 chars). Format: 'context -> core_name [METADATA]'." },
      { "key": "xpath",               "type": "string",   "description": "XPath expression or //*[@id='...']." },
      { "key": "is_select",           "type": "boolean",  "description": "True for <select> elements." },
      { "key": "is_shadow",           "type": "boolean",  "description": "True if inside Shadow DOM." },
      { "key": "is_contenteditable",  "type": "boolean",  "description": "True if element.isContentEditable." },
      { "key": "class_name",          "type": "string",   "description": "className or class attribute (safe for SVG)." },
      { "key": "tag_name",            "type": "string",   "description": "Lowercased HTML tag name." },
      { "key": "input_type",          "type": "string",   "description": "@type for <input>, lowercased." },
      { "key": "data_qa",             "type": "string",   "description": "data-qa or data-testid attribute." },
      { "key": "html_id",             "type": "string",   "description": "id attribute, or 'for' attribute on <label> elements." },
      { "key": "icon_classes",        "type": "string",   "description": "Space-separated icon class names from <i>, <svg>, [class*='icon']." },
      { "key": "aria_label",          "type": "string",   "description": "aria-label, title, or aria-labelledby resolved text." },
      { "key": "placeholder",         "type": "string",   "description": "placeholder / data-placeholder / aria-placeholder (lowercased)." },
      { "key": "role",                "type": "string",   "description": "ARIA role attribute." },
      { "key": "disabled",            "type": "boolean",  "description": "True if @disabled or .disabled." },
      { "key": "aria_disabled",       "type": "string",   "description": "aria-disabled value ('true' | 'false' | '')." },
      { "key": "name_attr",           "type": "string",   "description": "HTML name attribute." },
      { "key": "label_for",           "type": "string",   "description": "For @for attribute on <label> elements." },
      { "key": "rect_top",            "type": "int",      "description": "Math.round(boundingClientRect.top)." },
      { "key": "rect_left",           "type": "int",      "description": "Math.round(boundingClientRect.left)." },
      { "key": "rect_bottom",         "type": "int",      "description": "Math.round(boundingClientRect.bottom)." },
      { "key": "rect_right",          "type": "int",      "description": "Math.round(boundingClientRect.right)." },
      { "key": "ancestors",           "type": "string[]", "description": "Recent ancestor tag names (up to 8 levels)." },
      { "key": "frame_index",         "type": "int",      "description": "Index into page.frames (0 = main). Added by Python _snapshot(), not by JS." },
      { "key": "frame_url",           "type": "string",   "description": "Frame URL captured by Python _snapshot(), not by JS. Used by _frame_for() as a reload-tolerant routing hint." },
      { "key": "frame_name",          "type": "string",   "description": "Frame name captured by Python _snapshot(), not by JS. Used by _frame_for() as an additional reload-tolerant routing hint." }
    ],
    "nameSuffixes": [
      { "suffix": "[HIDDEN]",     "meaning": "Intentionally hidden (aria-hidden, off-screen left < -999, visibility hidden)." },
      { "suffix": "[ABOVE]",      "meaning": "Scrolled above viewport (rect.top < -999). Stripped for text matching." },
      { "suffix": "[SHADOW_DOM]", "meaning": "Element lives inside Shadow DOM." }
    ],
    "selectNameFormat": "dropdown [Option A | Option B | ...]",
    "labelDedup": "Skips <label> when linked <input> is visible and NOT type='file'."
  },

  "interactionModes": {
    "detection": "Keyword-based from step text (helpers.py :: detect_mode())",
    "modes": [
      { "mode": "input",     "keywords": ["type", "fill", "enter"] },
      { "mode": "clickable", "keywords": ["click", "double", "check", "uncheck"] },
      { "mode": "select",    "keywords": ["select", "choose"] },
      { "mode": "hover",     "keywords": ["hover"] },
      { "mode": "drag",      "keywords": ["drag", "drop"] },
      { "mode": "locate",    "keywords": null, "note": "Fallback when no other mode matched." }
    ]
  },

  "contextualQualifiers": {
    "parser": "helpers.py :: parse_contextual_hint()",
    "types": [
      {
        "syntax": "NEAR 'Anchor Text'",
        "scoring": "Euclidean distance between element rect center and anchor rect center. Closer = higher proximity score.",
        "proximityWeight": 1.5
      },
      {
        "syntax": "ON HEADER",
        "scoring": "Membership in <header>/<nav> ancestry OR element in top 15% of viewport.",
        "proximityWeight": 1.5
      },
      {
        "syntax": "ON FOOTER",
        "scoring": "Membership in <footer> ancestry OR element in bottom 15% of viewport.",
        "proximityWeight": 1.5
      },
      {
        "syntax": "INSIDE 'Container' row with 'Text'",
        "scoring": "Resolve container row first; restrict candidate scoring to that subtree.",
        "proximityWeight": 1.5
      }
    ]
  },

  "explainMode": {
    "trigger": "explain=True on DOMScorer or --explain CLI flag",
    "output": "Each scored element gets '_explain' dict with per-channel raw scores, weighted contributions, and final normalised confidence [0.0, 1.0]",
    "stderrFormat": "┌─ 🔍 EXPLAIN ... └─ ✅ Decision block printed to stderr for VS Code hover parsing"
  }
}
```
