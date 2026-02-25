import os
import re
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# ── Environment Configurations ────────────────────────────────────────────────
DEFAULT_MODEL = os.getenv("MANUL_MODEL", "qwen2.5:0.5b")
HEADLESS_MODE = os.getenv("MANUL_HEADLESS", "False").lower() in ("true", "1", "yes", "t")

TIMEOUT     = int(os.getenv("MANUL_TIMEOUT", "5000"))
NAV_TIMEOUT = int(os.getenv("MANUL_NAV_TIMEOUT", "30000"))

# Read custom AI threshold (Standard Points) from .env
_env_threshold = os.getenv("MANUL_AI_THRESHOLD")
ENV_AI_THRESHOLD = int(_env_threshold) if _env_threshold else None

# ── Confidence threshold logic ────────────────────────────────────────────────

def _threshold_for_model(model_name: str) -> int:
    """Auto-derive threshold points based on model parameter count."""
    m = re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    if not m:
        return 500
    size = float(m.group(1))
    if   size < 1:  return 500
    elif size < 5:  return 750
    elif size < 10: return 1_000
    elif size < 20: return 1_500
    else:           return 2_000

def get_threshold(model_name: str, custom_threshold: int | None = None) -> int:
    """
    Determines the final AI threshold score:
    1. Code Priority: If passed directly via ManulEngine(ai_threshold=...).
    2. Env Priority: If MANUL_AI_THRESHOLD is set in .env.
    3. Fallback: Auto-calculated by model size.
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

# ── Executor prompts ───────────────────────────────────────────────────────────
_RULES_CORE = """\
Each element has:
  id           – integer (RETURN THIS)
  name         – visible text / aria-label / "Section -> element text"
  tag          – html tag: input, button, a, select, label, div …
  role         – aria role: button, checkbox, radio, textbox …
  data_qa      – data-qa / data-testid (strongest automation signal)
  html_id      – html id attribute
  icon_classes – icon css classes: "fa arrow circle right"

RULES (apply in order):
① Return INTEGER id only:  {"id": 3, "thought": "one sentence"}
② data_qa exact match  → highest priority, beats everything else.
③ disabled elements    → NEVER pick.
④ Step says "button"   → prefer tag=button; AVOID tag=a / type=radio / type=checkbox.
   Step says "link"    → prefer tag=a; AVOID button.
   Step says "field"   → prefer input[text/email/password/tel] or textarea.
   Step says "dropdown"→ prefer tag=select (name starts "dropdown [").
   Step says "checkbox"→ ONLY type=checkbox or role=checkbox; penalise everything else.
   Step says "radio"   → ONLY type=radio or role=radio.
⑤ password step        → prefer input[type=password] over input[type=text].
⑥ aria-label exact match → strong signal; beats same-text visible elements.
⑦ icon-only buttons    → match icon_classes words against step keywords.
⑧ section context      → "Section -> name"; prefer matching section.
⑨ typo tolerance       → "Suggession" ≈ "Suggestion" (word overlap).
⑩ tie-break            → lower id wins.
"""

EXECUTOR_PROMPT_TINY = """\
You are a UI element picker for browser automation.
CONTEXT: {strategic_context}

""" + _RULES_CORE + """
Return ONLY: {"id": <integer>, "thought": "<one sentence>"}
"""

EXECUTOR_PROMPT_SMALL = """\
You are a precise UI Element Selector for a browser automation agent.
CONTEXT: {strategic_context}

Given a browser STEP and a list of UI ELEMENTS, return the id of the best match.

""" + _RULES_CORE + """
OUTPUT (nothing else): {"id": 0, "thought": "one sentence"}
"""

EXECUTOR_PROMPT_LARGE = """\
You are a precise UI Element Selector for a browser automation agent.
CONTEXT: {strategic_context}

Given a browser STEP and a list of UI ELEMENTS, return the id of the best match.

""" + _RULES_CORE + """
EXAMPLES:
  Step: Fill 'Email' field  →  pick input[type=text/email], NOT radio/button.
  Step: Click 'Close' button + icon_classes "fa times"  →  icon match wins.
  Step: Click 'Delete' for selected + data_qa "delete-selected"  →  data_qa wins.
  Step: Click checkbox 'Remember Me' + role=checkbox div + type=text input  →  role=checkbox wins.
  Step: Fill password field  →  input[type=password] wins over input[type=text].

OUTPUT (nothing else): {"id": 0, "thought": "one sentence"}
"""

def get_executor_prompt(model_name: str) -> str:
    m = re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    size = float(m.group(1)) if m else 0.5
    if   size < 1:  return EXECUTOR_PROMPT_TINY
    elif size < 7:  return EXECUTOR_PROMPT_SMALL
    else:           return EXECUTOR_PROMPT_LARGE