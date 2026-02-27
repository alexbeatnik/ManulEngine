# engine/prompts.py
"""
ManulEngine configuration, thresholds, and LLM prompts.

Reads settings from .env (via python-dotenv) or environment variables.
All values can be overridden in code via ManulEngine(model=..., ai_threshold=...).

Exports:
    DEFAULT_MODEL, HEADLESS_MODE, TIMEOUT, NAV_TIMEOUT — core settings
    get_threshold()       — model-aware confidence threshold
    get_executor_prompt() — model-size-aware executor prompt
    PLANNER_SYSTEM_PROMPT — planner system prompt
"""

import os
from pathlib import Path
import re as _re

_REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv
    # Load from a stable path (repo root) so this works even if CWD differs.
    #
    # Precedence:
    # - By default, process environment variables win (override=False).
    # - For local prompt tuning you may prefer the repo's .env to override the
    #   shell environment; set MANUL_DOTENV_OVERRIDE=true to enable that.
    _dotenv_path = _REPO_ROOT / ".env"
    if _dotenv_path.exists():
        _override = os.getenv("MANUL_DOTENV_OVERRIDE", "False").lower() in ("true", "1", "yes", "t")
        load_dotenv(dotenv_path=_dotenv_path, override=_override)
except ImportError:
    pass  # dotenv optional — fall back to os.environ

# ── Core ──────────────────────────────────────────────────────────────────────
DEFAULT_MODEL = os.getenv("MANUL_MODEL", "qwen2.5:0.5b")
HEADLESS_MODE = os.getenv("MANUL_HEADLESS", "False").lower() in ("true", "1", "yes", "t")
TIMEOUT       = int(os.getenv("MANUL_TIMEOUT",     "5000"))
NAV_TIMEOUT   = int(os.getenv("MANUL_NAV_TIMEOUT", "30000"))

# ── Persistent controls cache ────────────────────────────────────────────────
CONTROLS_CACHE_ENABLED = os.getenv("MANUL_CONTROLS_CACHE_ENABLED", "True").lower() in ("true", "1", "yes", "t")
_default_cache_dir = _REPO_ROOT / "cache"
_cache_dir_raw = os.getenv(
    "MANUL_CONTROLS_CACHE_DIR",
    str(_default_cache_dir)
)
_cache_dir_path = Path(_cache_dir_raw)
if not _cache_dir_path.is_absolute():
    _resolved_cache_dir = (_REPO_ROOT / _cache_dir_path).resolve()
    try:
        _inside_repo = _resolved_cache_dir.is_relative_to(_REPO_ROOT)
    except AttributeError:
        _inside_repo = (_resolved_cache_dir == _REPO_ROOT) or (_REPO_ROOT in _resolved_cache_dir.parents)
    _cache_dir_path = _resolved_cache_dir if _inside_repo else _default_cache_dir
CONTROLS_CACHE_DIR = str(_cache_dir_path)

# ── AI control switches ──────────────────────────────────────────────────────
# When enabled, ALL element resolution decisions go through the LLM picker.
AI_ALWAYS = os.getenv("MANUL_AI_ALWAYS", "False").lower() in ("true", "1", "yes", "t")

# Policy for how the LLM should treat heuristic scores when selecting.
# - prior  (default): score is a hint/prior; model may override with a clear reason.
# - strict          : enforce best score deterministically (useful for synthetic/id-strict tests).
AI_POLICY = os.getenv("MANUL_AI_POLICY", "prior").strip().lower()
if AI_POLICY not in ("prior", "strict"):
    AI_POLICY = "prior"

# ── Confidence threshold ───────────────────────────────────────────────────────

_env_threshold  = os.getenv("MANUL_AI_THRESHOLD")
ENV_AI_THRESHOLD: "int | None" = int(_env_threshold) if _env_threshold else None


def _threshold_for_model(model_name: str) -> int:
    """
    Auto-derive LLM confidence threshold from model parameter count.
    Larger models can handle more ambiguity → higher threshold before calling AI.

        < 1 b   →  500
        1–4 b   →  750
        5–9 b   → 1 000
       10–19 b  → 1 500
       20 b+    → 2 000
    """
    m = _re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    if not m:
        return 500
    size = float(m.group(1))
    if   size < 1:    return 500
    elif size < 5:    return 750
    elif size < 10:   return 1_000
    elif size < 20:   return 1_500
    else:             return 2_000


def get_threshold(model_name: str, custom_threshold: "int | None" = None) -> int:
    """
    Priority:
      1. custom_threshold  (passed directly to ManulEngine)
      2. MANUL_AI_THRESHOLD in .env
      3. Auto-calculated from model size
    """
    if custom_threshold is not None:
        return custom_threshold
    if ENV_AI_THRESHOLD is not None:
        return ENV_AI_THRESHOLD
    return _threshold_for_model(model_name)


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

def get_executor_prompt(model_name: str) -> str:
    """Return executor prompt sized for the model's parameter count."""
    m = _re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    size = float(m.group(1)) if m else 0.5
    if   size < 1:  return EXECUTOR_PROMPT_TINY
    elif size < 7:  return EXECUTOR_PROMPT_SMALL
    else:           return EXECUTOR_PROMPT_LARGE


# Legacy alias
EXECUTOR_SYSTEM_PROMPT = EXECUTOR_PROMPT_SMALL
