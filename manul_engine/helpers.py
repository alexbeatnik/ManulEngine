# manul_engine/helpers.py
"""
Shared helper functions and timing constants used across the engine.
"""

import os
import re

# ── Timing constants ──────────────────────────────────────────────────────────
SCROLL_WAIT = 1.5
ACTION_WAIT = 2.0
NAV_WAIT    = 2.0


# ── Mode detection ────────────────────────────────────────────────────────────

def detect_mode(step: str) -> str:
    """Detect the interaction mode from a step's verb keywords.

    Returns one of: ``"drag"``, ``"select"``, ``"input"``,
    ``"clickable"``, ``"hover"``, or ``"locate"`` (fallback).
    """
    words = set(re.findall(r'\b[a-z]+\b', step.lower()))
    if "drag" in words and "drop" in words:
        return "drag"
    if "select" in words or "choose" in words:
        return "select"
    if any(w in words for w in ("type", "fill", "enter")):
        return "input"
    if any(w in words for w in ("click", "double", "check", "uncheck")):
        return "clickable"
    if "hover" in words:
        return "hover"
    return "locate"


# ── Step classification ──────────────────────────────────────────────────────

# Compiled patterns for system keyword detection (order matters).
_STEP_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = [
    # STEP must precede other keywords so "STEP 1: NAVIGATE..." is classified correctly.
    # Anchored to line start so that STEP inside quoted labels is not matched.
    ("logical_step", re.compile(r'^\s*(?:\d+\.\s*)?STEP\s*\d*\s*:')),
    ("navigate",    re.compile(r'\bNAVIGATE\b')),
    ("open_app",    re.compile(r'\bOPEN\s+APP\b')),
    ("mock",        re.compile(r'\bMOCK\s+(?:GET|POST|PUT|PATCH|DELETE)\b')),
    ("wait_for_response", re.compile(r'\bWAIT\s+FOR\s+RESPONSE\b')),
    ("wait",        re.compile(r'\bWAIT\b')),
    ("scroll",      re.compile(r'\bSCROLL\b')),
    ("extract",     re.compile(r'\bEXTRACT\b')),
    ("verify_visual",  re.compile(r'\bVERIFY\s+VISUAL\b')),
    ("verify_softly",  re.compile(r'\bVERIFY\s+SOFTLY\b')),
    ("verify",      re.compile(r'\bVERIFY\b')),
    ("press_enter", re.compile(r'^\s*(?:\d+\.\s*)?PRESS\s+ENTER\b')),
    ("press",       re.compile(r'^\s*(?:\d+\.\s*)?PRESS\b')),
    ("right_click", re.compile(r'\bRIGHT\s+CLICK\b')),
    ("upload",      re.compile(r'\bUPLOAD\b')),
    ("scan_page",   re.compile(r'\bSCAN\s+PAGE\b')),
    ("call_python", re.compile(r'\bCALL\s+PYTHON\b')),
    ("set_var",     re.compile(r'^\s*(?:\d+\.\s*)?SET\b')),
    ("debug",       re.compile(r'\b(?:DEBUG|PAUSE)\b')),
    ("done",        re.compile(r'\bDONE\b')),
]

# Legacy pre-compiled system-step pattern kept for backwards compatibility.
# Prefer classify_step() for step classification.
RE_SYSTEM_STEP = re.compile(
    r'\b(?:STEP\s*\d*\s*:|NAVIGATE|OPEN\s+APP|MOCK\s+(?:GET|POST|PUT|PATCH|DELETE)|WAIT\s+FOR\s+RESPONSE|WAIT|SCROLL|EXTRACT|VERIFY\s+VISUAL|VERIFY\s+SOFTLY|VERIFY|PRESS|RIGHT\s+CLICK|UPLOAD|SCAN\s+PAGE|CALL\s+PYTHON|SET|DEBUG|PAUSE|DONE)\b'
)

# Extracts the description from a STEP marker line.
# Matches: "STEP 1: Description" and "STEP: Description" (case-insensitive).
# The stripped 1-based numbering prefix is handled by the caller.
_RE_LOGICAL_STEP = re.compile(r'\bSTEP\s*(\d*)\s*:\s*(.*)', re.IGNORECASE)


def parse_logical_step(step: str) -> "tuple[str | None, str | None]":
    """Extract (number_or_None, description) from a logical STEP marker.

    Returns (None, None) if the step is not a STEP marker.

    Examples::

        parse_logical_step("1. STEP 2: Navigate")  -> ("2", "Navigate")
        parse_logical_step("3. STEP: Fill form")   -> (None, "Fill form")
        parse_logical_step("1. Click button")       -> (None, None)
    """
    m = _RE_LOGICAL_STEP.search(step)
    if m is None:
        return None, None
    num = m.group(1).strip() or None
    desc = m.group(2).strip()
    return num, desc


# Pattern to strip quoted text before classification.
_RE_QUOTED = re.compile(r"""(['"]).*?\1""")


def classify_step(step: str) -> str:
    """Return the system keyword type of a step, or ``"action"`` for DOM steps.

    Quoted strings are stripped before matching so that keywords inside
    element labels (e.g. ``Click 'Press Here'``) are not misclassified.

    The returned string is one of: ``"logical_step"``, ``"navigate"``,
    ``"open_app"``, ``"mock"``, ``"wait_for_response"``, ``"wait"``, ``"scroll"``,
    ``"extract"``, ``"verify_visual"``, ``"verify_softly"``,
    ``"verify"``, ``"press_enter"``, ``"press"``, ``"right_click"``,
    ``"upload"``, ``"scan_page"``, ``"call_python"``, ``"set_var"``,
    ``"debug"``, ``"done"``, or ``"action"``.
    """
    # Fast-path: STEP markers are checked on the raw text BEFORE quote
    # stripping so that apostrophes in descriptions (e.g. "Pallas's cat")
    # never interfere with classification.  The pattern is anchored to line
    # start so "STEP 1:" inside a quoted label does not trigger a false match.
    if _STEP_PATTERNS[0][1].search(step.upper()):  # logical_step
        return "logical_step"

    # Remove quoted substrings so keywords inside labels are invisible.
    s_up = _RE_QUOTED.sub("", step).upper()
    for kind, pattern in _STEP_PATTERNS[1:]:
        if pattern.search(s_up):
            return kind
    return "action"


# ── Pure helpers ──────────────────────────────────────────────────────────────

def substitute_memory(text: str, memory: dict) -> str:
    """Replace all {var} placeholders with values from memory."""
    for k, v in memory.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


def extract_quoted(step: str, preserve_case: bool = False) -> list[str]:
    """Return all quoted strings from a step, preserving their order."""
    step = step.replace("\u2019", "'").replace("\u2018", "'")
    step = step.replace("\u201c", '"').replace("\u201d", '"')
    matches = re.findall(r'"([^"]*)"|\'([^\']*)\'', step)
    found = [m[0] if m[0] else m[1] for m in matches]
    return [x if preserve_case else x.lower() for x in found if x]


def env_bool(name: str, default: str = "False") -> bool:
    """Read an environment variable as a boolean flag."""
    return os.getenv(name, default).strip().lower() in ("true", "1", "yes", "t")


def compact_log_field(raw_value: object, env_var: str, default_max_len: int = 0) -> str:
    """Collapse whitespace and optionally truncate using an env var max length.

    If env var is missing or invalid, default_max_len is used.
    If max_len <= 0, truncation is disabled.
    """
    value = re.sub(r"\s+", " ", str(raw_value or "")).strip()
    try:
        max_len = int(os.getenv(env_var, str(default_max_len)))
    except ValueError:
        max_len = default_max_len
    if max_len and len(value) > max_len:
        value = value[: max(0, max_len - 1)] + "…"
    return value
