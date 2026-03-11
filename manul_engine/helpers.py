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
    ("navigate",    re.compile(r'\bNAVIGATE\b')),
    ("wait",        re.compile(r'\bWAIT\b')),
    ("scroll",      re.compile(r'\bSCROLL\b')),
    ("extract",     re.compile(r'\bEXTRACT\b')),
    ("verify",      re.compile(r'\bVERIFY\b')),
    ("press_enter", re.compile(r'\bPRESS\s+ENTER\b')),
    ("scan_page",   re.compile(r'\bSCAN\s+PAGE\b')),
    ("call_python", re.compile(r'\bCALL\s+PYTHON\b')),
    ("debug",       re.compile(r'\b(?:DEBUG|PAUSE)\b')),
    ("done",        re.compile(r'\bDONE\b')),
]

# Pre-compiled pattern used by run_mission to detect system steps for debug
# pause ordering (system steps pause before, action steps pause after resolve).
RE_SYSTEM_STEP = re.compile(
    r'\b(?:NAVIGATE|WAIT|SCROLL|EXTRACT|PRESS\s+ENTER|SCAN\s+PAGE|CALL\s+PYTHON|DEBUG|PAUSE|DONE)\b'
)


def classify_step(step: str) -> str:
    """Return the system keyword type of a step, or ``"action"`` for DOM steps.

    The returned string is one of: ``"navigate"``, ``"wait"``, ``"scroll"``,
    ``"extract"``, ``"verify"``, ``"press_enter"``, ``"scan_page"``,
    ``"call_python"``, ``"debug"``, ``"done"``, or ``"action"``.
    """
    s_up = step.upper()
    for kind, pattern in _STEP_PATTERNS:
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
