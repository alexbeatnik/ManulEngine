# engine/helpers.py
"""
Shared helper functions and timing constants used across the engine.
"""

import os
import re

# ── Timing constants ──────────────────────────────────────────────────────────
SCROLL_WAIT = 1.5
ACTION_WAIT = 2.0
NAV_WAIT    = 2.0


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
