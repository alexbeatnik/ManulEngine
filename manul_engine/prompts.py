# manul_engine/prompts.py
"""
ManulEngine configuration, thresholds, and LLM prompts.

Reads settings from manul_engine_configuration.json (repo root) or environment
variables. Environment variables (MANUL_* prefix) always win over the JSON file.
All values can also be overridden in code via ManulEngine(model=..., ai_threshold=...).

Exports:
    DEFAULT_MODEL, HEADLESS_MODE, TIMEOUT, NAV_TIMEOUT — core settings
    get_threshold()       — model-aware confidence threshold
    get_executor_prompt() — model-size-aware executor prompt
    PLANNER_SYSTEM_PROMPT — planner system prompt
"""

import json
import os
from pathlib import Path
import re as _re

from .helpers import env_bool

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ── JSON config loading ───────────────────────────────────────────────────────
# Look for manul_engine_configuration.json first in the current working
# directory (user's project root), then fall back to the package source root
# (useful when running directly from the ManulEngine dev repo).
# Environment variables (MANUL_*) always override JSON values.
_CONFIG_PATH = Path.cwd() / "manul_engine_configuration.json"
if not _CONFIG_PATH.exists():
    _CONFIG_PATH = _REPO_ROOT / "manul_engine_configuration.json"

# Maps JSON config keys → corresponding MANUL_* environment variable names.
_KEY_MAP: dict[str, str] = {
    "model":                  "MANUL_MODEL",
    "headless":               "MANUL_HEADLESS",
    "timeout":                "MANUL_TIMEOUT",
    "nav_timeout":            "MANUL_NAV_TIMEOUT",
    "ai_threshold":           "MANUL_AI_THRESHOLD",
    "ai_always":              "MANUL_AI_ALWAYS",
    "ai_policy":              "MANUL_AI_POLICY",
    "controls_cache_enabled": "MANUL_CONTROLS_CACHE_ENABLED",
    "controls_cache_dir":     "MANUL_CONTROLS_CACHE_DIR",
    "log_name_maxlen":        "MANUL_LOG_NAME_MAXLEN",
    "log_thought_maxlen":     "MANUL_LOG_THOUGHT_MAXLEN",
}

if _CONFIG_PATH.exists():
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as _f:
            _json_cfg: dict = json.load(_f)
        for _jk, _ek in _KEY_MAP.items():
            # Skip keys starting with "_" (comments/notes) and skip if env already set.
            if _jk in _json_cfg and _ek not in os.environ:
                _val = _json_cfg[_jk]
                if _val is not None:
                    # Python booleans → lowercase strings so env_bool() parses them correctly.
                    os.environ[_ek] = str(_val).lower() if isinstance(_val, bool) else str(_val)
    except (json.JSONDecodeError, OSError) as _cfg_err:
        import warnings
        warnings.warn(f"ManulEngine: could not load config file '{_CONFIG_PATH}': {_cfg_err}")

# ── Core ──────────────────────────────────────────────────────────────────────
# If MANUL_MODEL is unset or empty, DEFAULT_MODEL is None — AI is fully disabled.
DEFAULT_MODEL: "str | None" = os.getenv("MANUL_MODEL") or None
HEADLESS_MODE = env_bool("MANUL_HEADLESS")
TIMEOUT       = int(os.getenv("MANUL_TIMEOUT",     "5000"))
NAV_TIMEOUT   = int(os.getenv("MANUL_NAV_TIMEOUT", "30000"))

# ── Persistent controls cache ────────────────────────────────────────────────
CONTROLS_CACHE_ENABLED = env_bool("MANUL_CONTROLS_CACHE_ENABLED", "True")
_cache_dir_raw = os.getenv("MANUL_CONTROLS_CACHE_DIR", "cache")
_cache_dir_path = Path(_cache_dir_raw)
# Relative paths are always resolved against CWD (the user's project root),
# not against the package installation directory.
if not _cache_dir_path.is_absolute():
    _cache_dir_path = Path.cwd() / _cache_dir_path
CONTROLS_CACHE_DIR = str(_cache_dir_path.resolve())

# ── AI control switches ──────────────────────────────────────────────────────
# When enabled, ALL element resolution decisions go through the LLM picker.
AI_ALWAYS = env_bool("MANUL_AI_ALWAYS")

# Policy for how the LLM should treat heuristic scores when selecting.
# - prior  (default): score is a hint/prior; model may override with a clear reason.
# - strict          : enforce best score deterministically (useful for synthetic/id-strict tests).
AI_POLICY = os.getenv("MANUL_AI_POLICY", "prior").strip().lower()
if AI_POLICY not in ("prior", "strict"):
    AI_POLICY = "prior"

# ── Confidence threshold ───────────────────────────────────────────────────────

_env_threshold  = os.getenv("MANUL_AI_THRESHOLD")
ENV_AI_THRESHOLD: "int | None" = int(_env_threshold) if _env_threshold else None


def _threshold_for_model(model_name: "str | None") -> int:
    """
    Auto-derive LLM confidence threshold from model parameter count.
    Returns 0 (disable AI) when model_name is None.

        None    →    0  (heuristics-only mode)
        < 1 b   →  500
        1–4 b   →  750
        5–9 b   → 1 000
       10–19 b  → 1 500
       20 b+    → 2 000
    """
    if not model_name:
        return 0
    m = _re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    if not m:
        return 500
    size = float(m.group(1))
    if   size < 1:    return 500
    elif size < 5:    return 750
    elif size < 10:   return 1_000
    elif size < 20:   return 1_500
    else:             return 2_000


def get_threshold(model_name: "str | None", custom_threshold: "int | None" = None) -> int:
    """
    Priority:
      1. custom_threshold  (passed directly to ManulEngine)
      2. MANUL_AI_THRESHOLD in config / env
      3. 0 when model_name is None (heuristics-only mode)
      4. Auto-calculated from model size
    """
    if custom_threshold is not None:
        return custom_threshold
    if ENV_AI_THRESHOLD is not None:
        return ENV_AI_THRESHOLD
    return _threshold_for_model(model_name)  # returns 0 when model_name is None


# ── Planner prompt ─────────────────────────────────────────────────────────────
PLANNER_SYSTEM_PROMPT = """\
You are a QA Automation Planner for a browser agent.
Your ONLY job: convert the user's task into a strict, ordered JSON step list.

RULES:
- Copy every step VERBATIM. Do NOT paraphrase, merge, or skip any step.
- Every step must be a single, atomic browser instruction.
- Preserve all quoted values, variable placeholders ({like_this}), and URLs exactly.
- Return ONLY valid JSON — no markdown, no comments, no prose.

OUTPUT FORMAT:
{"steps": ["1. Step one", "2. Step two", "..."]}
"""

# ── Executor prompts (model-size aware) ───────────────────────────────────────

_RULES_CORE = """\
Each element candidate has:
    id              – integer (RETURN THIS EXACT ID)
    score           – integer heuristic rank (HIGHER IS BETTER; treat as a PRIOR)
    name            – visible text / aria-label / "Context -> element text"
    tag             – HTML tag (input, button, a, select, textarea, div, etc.)
    input_type      – for <input>, the type (text/password/email/checkbox/radio/submit/...)
    role            – ARIA role (button, checkbox, textbox, combobox, etc.)
    data_qa         – Test IDs (extremely strong signal)
    html_id         – HTML id attribute
    class_name      – HTML classes (important for inferring intent)
    icon_classes    – CSS classes for icons (e.g., "fa search")
    aria_label      – aria-label/title (often the real label for icon buttons)
    placeholder     – placeholder/data-placeholder/aria-placeholder
    disabled        – boolean
    aria_disabled   – string ("true"/"false"/"")
    is_select       – boolean (native <select>)
    contenteditable – boolean
    is_shadow       – boolean

CRITICAL RULES (Apply strictly in this order):
1. JSON ONLY: Return ONLY valid JSON. No markdown, no extra text. Format: {"id": 123, "thought": "reasoning"}
2. EXACT MATCH WINS: An exact match in `name`, `data_qa`, or `aria_label` ALWAYS beats a partial match.
3. USE SCORE AS A PRIOR (NOT A SHACKLE):
    - Prefer higher `score` when candidates are otherwise comparable.
    - You MAY choose a lower-score candidate only if you can state a clear disqualifying reason for the higher-score one
      (wrong element type for the requested mode, disabled/aria-disabled, wrong checkbox/radio alignment, etc.).
    - If scores tie, choose the first one in the list.
    - Note: In strict test mode a separate policy may enforce max-score determinism.
4. MATCH THE ACTION TO THE ELEMENT TYPE:
        - "Fill/Type" -> MUST prefer `tag=input`, `tag=textarea`, or `contenteditable=true`.
            If `tag=input`, prefer the right `input_type` (password/email/search/number/etc.).
        - "Check/Uncheck" -> MUST prefer `input_type=checkbox` or `role=checkbox`. NEVER pick a generic button.
        - "Select from dropdown" -> Prefer `is_select=true` / `tag=select` / `role=combobox`.
            If there is no native select, pick the most dropdown-like candidate (class/id contains drop/select/combo).
        - "Click link" -> MUST prefer `tag=a` or `role=link`.
        - "Click button" -> MUST prefer `tag=button`, `role=button`, or `input_type=submit`.
5. DEV CONVENTIONS (CRITICAL): Read `html_id` and `class_name` to infer the real element type if `tag` is generic (like div/span):
   - `btn` / `button` -> It acts as a button.
   - `chk` / `checkbox` -> It acts as a checkbox.
   - `rad` / `radio` -> It acts as a radio button.
   - `sel` / `drop` / `cmb` -> It acts as a select/dropdown.
   - `inp` / `txt` / `field` -> It acts as an input field.
6. CONTEXT MATTERS: If the step says "in Shipping", pick the element whose `name` contains that context (e.g., "Shipping -> First Name").
7. DATA-QA / TEST-ID: If `data_qa` closely matches the target text, it is almost certainly the correct choice.
8. PASSWORDS: If the step mentions "password" or "secret", heavily prefer `input_type=password`.
9. ICONS AND FORMATTING: For media or text editors (e.g., "Fullscreen", "Theater mode", "Underline"), if there is a button with an empty name or a weird symbol, it is highly likely the correct tool. DO NOT REJECT IT.
10. DISABLED: Avoid `disabled=true` or `aria_disabled="true"` unless the step is about verifying disabled state.
11. SHADOW DOM: If you see `is_shadow=true` or the name contains `[SHADOW_DOM]` and it matches the target, prefer it.
12. BEWARE TRAPS: DO NOT pick elements with "honeypot", "spam", or "hidden" in their names/IDs unless explicitly asked.
13. TIE-BREAKER: If multiple elements look equally correct, pick the one with the lowest `id`.
14. REJECTION (LAST RESORT): Return `null` ONLY if the target is completely missing and there is no plausible element of the correct type.
    WARNING: If the step asks for a formatting tool (like 'Underline') or a player control (like 'Fullscreen') and you see an unlabeled/icon button, ASSUME IT IS THE TARGET AND PICK IT!
"""

# Tiny (< 1 b) — minimal tokens
EXECUTOR_PROMPT_TINY = """\
You are a UI element picker for browser automation.
CONTEXT: {strategic_context}

""" + _RULES_CORE + """
Return ONLY: {"id": <integer or null>, "thought": "<one sentence>"}
"""

# Small (1–6 b)
EXECUTOR_PROMPT_SMALL = """\
You are a precise UI Element Selector for a browser automation agent.
CONTEXT: {strategic_context}

Given a browser STEP and a list of UI ELEMENTS, return the id of the best match.

""" + _RULES_CORE + """
OUTPUT (nothing else): {"id": <integer or null>, "thought": "one sentence"}
"""

# Large (7 b+) — with worked examples
EXECUTOR_PROMPT_LARGE = """\
You are a precise UI Element Selector for a browser automation agent.
CONTEXT: {strategic_context}

Given a browser STEP and a list of UI ELEMENTS, return the `id` of the best match.

""" + _RULES_CORE + """
EXAMPLES:
  Step: "Fill 'Email' in Billing" → Pick element with name "Billing -> Email input text", NOT "Shipping -> Email".
  Step: "Check 'I agree'" → Pick type=checkbox, or class_name containing 'chk'.
  Step: "Click 'Color Red'" → Pick element with aria-label="Color Red" or similar.
  Step: "Select 'Ukraine' from 'Country'" → Pick tag=select containing 'Country'.
  Step: "Fill 'Message Body'" → Pick element with contenteditable=true or tag=textarea.

OUTPUT (strictly valid JSON, no markdown):
{"id": <integer or null>, "thought": "one sentence"}
"""

def get_executor_prompt(model_name: "str | None") -> str:
    """Return executor prompt sized for the model's parameter count."""
    if not model_name:
        return EXECUTOR_PROMPT_TINY  # fallback; won't be called in heuristics-only mode
    m = _re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    size = float(m.group(1)) if m else 0.5
    if   size < 1:  return EXECUTOR_PROMPT_TINY
    elif size < 7:  return EXECUTOR_PROMPT_SMALL
    else:           return EXECUTOR_PROMPT_LARGE


# Legacy alias
EXECUTOR_SYSTEM_PROMPT = EXECUTOR_PROMPT_SMALL
