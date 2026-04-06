# manul_engine/helpers.py
"""
Shared helper functions and timing constants used across the engine.
"""

import os
import re
from dataclasses import dataclass, field
from typing import NamedTuple

# ── Timing constants ──────────────────────────────────────────────────────────
SCROLL_WAIT = 1.5
ACTION_WAIT = 2.0
NAV_WAIT = 2.0


# ── Mode detection ────────────────────────────────────────────────────────────


def detect_mode(step: str) -> str:
    """Detect the interaction mode from a step's verb keywords.

    Returns one of: ``"drag"``, ``"select"``, ``"input"``,
    ``"clickable"``, ``"hover"``, or ``"locate"`` (fallback).
    """
    words = set(re.findall(r"\b[a-z]+\b", step.lower()))
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
    ("logical_step", re.compile(r"^\s*(?:\d+\.\s*)?STEP\s*\d*\s*:")),
    ("navigate", re.compile(r"\bNAVIGATE\b")),
    ("open_app", re.compile(r"\bOPEN\s+APP\b")),
    ("mock", re.compile(r"\bMOCK\s+(?:GET|POST|PUT|PATCH|DELETE)\b")),
    ("wait_for_response", re.compile(r"\bWAIT\s+FOR\s+RESPONSE\b")),
    ("wait", re.compile(r"\bWAIT\b")),
    ("scroll", re.compile(r"\bSCROLL\b")),
    ("extract", re.compile(r"\bEXTRACT\b")),
    ("verify_visual", re.compile(r"\bVERIFY\s+VISUAL\b")),
    ("verify_softly", re.compile(r"\bVERIFY\s+SOFTLY\b")),
    ("verify", re.compile(r"\bVERIFY\b")),
    ("press_enter", re.compile(r"^\s*(?:\d+\.\s*)?PRESS\s+ENTER\b")),
    ("press", re.compile(r"^\s*(?:\d+\.\s*)?PRESS\b")),
    ("right_click", re.compile(r"\bRIGHT\s+CLICK\b")),
    ("upload", re.compile(r"\bUPLOAD\b")),
    ("scan_page", re.compile(r"\bSCAN\s+PAGE\b")),
    ("call_python", re.compile(r"\bCALL\s+PYTHON\b")),
    ("set_var", re.compile(r"^\s*(?:\d+\.\s*)?SET\b")),
    ("debug_vars", re.compile(r"\bDEBUG\s+VARS\b")),
    ("debug", re.compile(r"\b(?:DEBUG|PAUSE)\b")),
    ("done", re.compile(r"\bDONE\b")),
    ("use_import", re.compile(r"^\s*(?:\d+\.\s*)?USE\b")),
]

# Legacy pre-compiled system-step pattern kept for backwards compatibility.
# Prefer classify_step() for step classification.
RE_SYSTEM_STEP = re.compile(
    r"""\b(?:STEP\s*\d*\s*:|WAIT\s+FOR\s+(?:"[^"]+"|'[^']+')\s+TO\s+(?:BE\s+(?:VISIBLE|HIDDEN)|DISAPPEAR)|NAVIGATE|OPEN\s+APP|MOCK\s+(?:GET|POST|PUT|PATCH|DELETE)|WAIT\s+FOR\s+RESPONSE|WAIT|SCROLL|EXTRACT|VERIFY\s+VISUAL|VERIFY\s+SOFTLY|VERIFY|PRESS|RIGHT\s+CLICK|UPLOAD|SCAN\s+PAGE|CALL\s+PYTHON|SET|DEBUG\s+VARS|DEBUG|PAUSE|DONE|USE)\b""",
    re.IGNORECASE,
)

# Extracts the description from a STEP marker line.
# Matches: "STEP 1: Description" and "STEP: Description" (case-insensitive).
# The stripped 1-based numbering prefix is handled by the caller.
_RE_LOGICAL_STEP = re.compile(r"\bSTEP\s*(\d*)\s*:\s*(.*)", re.IGNORECASE)
_RE_EXPLICIT_WAIT = re.compile(
    r'^\s*(?:\d+\.\s*)?WAIT\s+FOR\s+(?P<quote>["\'])(?P<target>.+?)(?P=quote)\s+TO\s+'
    r"(?:(?:BE\s+(?P<state_be>VISIBLE|HIDDEN))|(?P<state_disappear>DISAPPEAR))\s*$",
    re.IGNORECASE,
)
_RE_VERIFY_STRICT_TEXT = re.compile(
    r'^\s*(?:\d+\.\s*)?VERIFY\s+(?P<target_quote>["\'])(?P<target>.+?)(?P=target_quote)\s+'
    r"(?P<element_type>button|field|element|input)\s+HAS\s+TEXT\s+"
    r'(?P<expected_quote>["\'])(?P<expected>.*?)(?P=expected_quote)\s*\.?\s*$',
    re.IGNORECASE,
)
_RE_VERIFY_STRICT_PLACEHOLDER = re.compile(
    r'^\s*(?:\d+\.\s*)?VERIFY\s+(?P<target_quote>["\'])(?P<target>.+?)(?P=target_quote)\s+'
    r"(?P<element_type>button|field|element|input)\s+HAS\s+PLACEHOLDER\s+"
    r'(?P<expected_quote>["\'])(?P<expected>.*?)(?P=expected_quote)\s*\.?\s*$',
    re.IGNORECASE,
)
_RE_VERIFY_STRICT_VALUE = re.compile(
    r'^\s*(?:\d+\.\s*)?VERIFY\s+(?P<target_quote>["\'])(?P<target>.+?)(?P=target_quote)\s+'
    r"(?P<element_type>button|field|element|input)\s+HAS\s+VALUE\s+"
    r'(?P<expected_quote>["\'])(?P<expected>.*?)(?P=expected_quote)\s*\.?\s*$',
    re.IGNORECASE,
)


@dataclass(slots=True)
class HuntBlock:
    """Hierarchical execution block parsed from Hunt DSL."""

    block_name: str
    actions: list[str] = field(default_factory=list)
    block_line: int | None = None
    action_lines: list[int] = field(default_factory=list)
    synthetic: bool = False


class StrictVerifyAssertion(NamedTuple):
    """Parsed strict VERIFY assertion."""

    kind: str
    target: str
    element_type: str
    expected: str


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


def normalize_logical_step(step: str) -> str:
    """Return a canonical STEP label without any leading legacy numbering."""
    num, desc = parse_logical_step(step)
    if desc is None:
        return re.sub(r"^\s*\d+\.\s*", "", step).strip()
    if num is None:
        return f"STEP: {desc}"
    return f"STEP {num}: {desc}"


def parse_explicit_wait(step: str) -> "tuple[str | None, str | None]":
    """Extract ``(target_element, desired_state)`` from an explicit wait step."""
    m = _RE_EXPLICIT_WAIT.match(step.strip())
    if m is None:
        return None, None
    target = m.group("target").strip()
    desired_state = (m.group("state_be") or m.group("state_disappear") or "").strip().lower()
    return target or None, desired_state or None


def parse_verify_strict_assertion(step: str) -> "StrictVerifyAssertion | None":
    """Parse strict VERIFY text/placeholder/value assertions."""
    step = step.strip()

    m_text = _RE_VERIFY_STRICT_TEXT.match(step)
    if m_text is not None:
        return StrictVerifyAssertion(
            kind="text",
            target=m_text.group("target").strip(),
            element_type=m_text.group("element_type").strip().lower(),
            expected=m_text.group("expected"),
        )

    m_placeholder = _RE_VERIFY_STRICT_PLACEHOLDER.match(step)
    if m_placeholder is not None:
        return StrictVerifyAssertion(
            kind="placeholder",
            target=m_placeholder.group("target").strip(),
            element_type=m_placeholder.group("element_type").strip().lower(),
            expected=m_placeholder.group("expected"),
        )

    m_value = _RE_VERIFY_STRICT_VALUE.match(step)
    if m_value is not None:
        return StrictVerifyAssertion(
            kind="value",
            target=m_value.group("target").strip(),
            element_type=m_value.group("element_type").strip().lower(),
            expected=m_value.group("expected"),
        )

    return None


def parse_hunt_blocks(task: str, file_lines: list[int] | None = None) -> list[HuntBlock]:
    """Parse raw Hunt DSL text into hierarchical STEP blocks.

    STEP markers become parent blocks. All executable lines that follow are
    attached to the current block until the next STEP marker. When the mission
    contains no STEP markers, the executable lines are grouped into a single
    synthetic default block to preserve backward compatibility.
    """
    mission_lines = [line.rstrip("\n") for line in task.splitlines() if line.strip()]
    if not mission_lines:
        return []

    resolved_lines = file_lines if file_lines and len(file_lines) == len(mission_lines) else [0] * len(mission_lines)
    blocks: list[HuntBlock] = []
    current_block: HuntBlock | None = None

    for raw_line, line_no in zip(mission_lines, resolved_lines):
        stripped = raw_line.strip()
        if classify_step(stripped) == "logical_step":
            current_block = HuntBlock(
                block_name=normalize_logical_step(stripped),
                block_line=line_no or None,
            )
            blocks.append(current_block)
            continue

        if current_block is None:
            current_block = HuntBlock(
                block_name="STEP: Default",
                block_line=line_no or None,
                synthetic=True,
            )
            blocks.append(current_block)

        current_block.actions.append(stripped)
        current_block.action_lines.append(line_no or 0)

    return [block for block in blocks if block.actions or not block.synthetic]


# Pattern to strip quoted text before classification.
_RE_QUOTED = re.compile(r"""(['"]).*?\1""")


def classify_step(step: str) -> str:
    """Return the system keyword type of a step, or ``"action"`` for DOM steps.

    Quoted strings are stripped before matching so that keywords inside
    element labels (e.g. ``Click 'Press Here'``) are not misclassified.

    The returned string is one of: ``"logical_step"``, ``"wait_for_element"``,
    ``"navigate"``, ``"open_app"``, ``"mock"``, ``"wait_for_response"``, ``"wait"``, ``"scroll"``,
    ``"extract"``, ``"verify_visual"``, ``"verify_softly"``,
    ``"verify"``, ``"press_enter"``, ``"press"``, ``"right_click"``,
    ``"upload"``, ``"scan_page"``, ``"call_python"``, ``"set_var"``,
    ``"debug_vars"``, ``"debug"``, ``"done"``, or ``"action"``.
    """
    # Fast-path: STEP markers are checked on the raw text BEFORE quote
    # stripping so that apostrophes in descriptions (e.g. "Pallas's cat")
    # never interfere with classification.  The pattern is anchored to line
    # start so "STEP 1:" inside a quoted label does not trigger a false match.
    if _STEP_PATTERNS[0][1].search(step.upper()):  # logical_step
        return "logical_step"

    if parse_explicit_wait(step)[0] is not None:
        return "wait_for_element"

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


# ── Contextual proximity hints ────────────────────────────────────────────────


class ContextualHint(NamedTuple):
    """Parsed contextual proximity hint from a DSL step.

    Attributes:
        kind: One of ``"near"``, ``"on_header"``, ``"on_footer"``,
              ``"inside"``, or ``None`` if no hint was detected.
    anchor: The quoted anchor text for ``NEAR``, or the INSIDE container
        label for ``INSIDE 'X' row with 'Y'``. ``None`` when the
        hint has no anchor (``ON HEADER``/``ON FOOTER``).
        row_text: For ``INSIDE 'X' row with 'Y'`` — the row-identifying
          text ``'Y'``. ``None`` otherwise.
    """

    kind: "str | None"
    anchor: "str | None"
    row_text: "str | None"


# Regex patterns for contextual hints.
# Order matters — longer / more specific patterns first.
_RE_INSIDE = re.compile(
    r"""\bINSIDE\s+(?P<q1>['"])(?P<target>.+?)(?P=q1)\s+row\s+with\s+(?P<q2>['"])(?P<row>.+?)(?P=q2)""",
    re.IGNORECASE,
)
_RE_NEAR = re.compile(
    r"""\bNEAR\s+(?P<q>['"])(?P<anchor>.+?)(?P=q)""",
    re.IGNORECASE,
)
_RE_ON_HEADER = re.compile(r"\bON\s+HEADER\b", re.IGNORECASE)
_RE_ON_FOOTER = re.compile(r"\bON\s+FOOTER\b", re.IGNORECASE)


def _mask_quoted(text: str) -> str:
    """Replace quoted substrings with spaces while preserving indices."""
    return _RE_QUOTED.sub(lambda m: " " * len(m.group(0)), text)


def parse_contextual_hint(step: str) -> "tuple[ContextualHint, str]":
    """Extract a contextual proximity hint from a DSL step.

    Returns ``(hint, cleaned_step)`` where *cleaned_step* has the hint
    clause removed so downstream parsing sees only the core action.

    Supported clauses (case-insensitive):
    - ``NEAR 'Anchor Text'``
    - ``ON HEADER`` / ``ON FOOTER``
    - ``INSIDE 'Container' row with 'Row Text'``

    If no clause is detected, *hint.kind* is ``None`` and *cleaned_step*
    is the original step unchanged.
    """
    # INSIDE (most specific — must be checked first)
    m = _RE_INSIDE.search(step)
    if m:
        cleaned = step[: m.start()] + step[m.end() :]
        return ContextualHint("inside", m.group("target"), m.group("row")), cleaned.strip()

    # NEAR
    m = _RE_NEAR.search(step)
    if m:
        cleaned = step[: m.start()] + step[m.end() :]
        return ContextualHint("near", m.group("anchor"), None), cleaned.strip()

    masked = _mask_quoted(step)

    # ON HEADER
    m = _RE_ON_HEADER.search(masked)
    if m:
        cleaned = step[: m.start()] + step[m.end() :]
        return ContextualHint("on_header", None, None), cleaned.strip()

    # ON FOOTER
    m = _RE_ON_FOOTER.search(masked)
    if m:
        cleaned = step[: m.start()] + step[m.end() :]
        return ContextualHint("on_footer", None, None), cleaned.strip()

    return ContextualHint(None, None, None), step
