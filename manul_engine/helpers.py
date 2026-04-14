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
    ("if_block", re.compile(r"^\s*(?:\d+\.\s*)?IF\b.+:\s*$", re.IGNORECASE)),
    ("elif_block", re.compile(r"^\s*(?:\d+\.\s*)?ELIF\b.+:\s*$", re.IGNORECASE)),
    ("else_block", re.compile(r"^\s*(?:\d+\.\s*)?ELSE\s*:\s*$", re.IGNORECASE)),
    ("repeat_loop", re.compile(r"^\s*(?:\d+\.\s*)?REPEAT\s+\d+\s+TIMES\s*:\s*$", re.IGNORECASE)),
    ("for_each_loop", re.compile(r"^\s*(?:\d+\.\s*)?FOR\s+EACH\b.+\bIN\b.+:\s*$", re.IGNORECASE)),
    ("while_loop", re.compile(r"^\s*(?:\d+\.\s*)?WHILE\b.+:\s*$", re.IGNORECASE)),
]

# Legacy pre-compiled system-step pattern kept for backwards compatibility.
# Prefer classify_step() for step classification.
RE_SYSTEM_STEP = re.compile(
    r"""\b(?:STEP\s*\d*\s*:|WAIT\s+FOR\s+(?:"[^"]+"|'[^']+')\s+TO\s+(?:BE\s+(?:VISIBLE|HIDDEN)|DISAPPEAR)|NAVIGATE|OPEN\s+APP|MOCK\s+(?:GET|POST|PUT|PATCH|DELETE)|WAIT\s+FOR\s+RESPONSE|WAIT|SCROLL|EXTRACT|VERIFY\s+VISUAL|VERIFY\s+SOFTLY|VERIFY|PRESS|RIGHT\s+CLICK|UPLOAD|SCAN\s+PAGE|CALL\s+PYTHON|SET|DEBUG\s+VARS|DEBUG|PAUSE|DONE|USE|IF\b.+:|ELIF\b.+:|ELSE\s*:|REPEAT\s+\d+\s+TIMES\s*:|FOR\s+EACH\b.+\bIN\b.+:|WHILE\b.+:)(?:\b|$)""",
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
    actions: "list[str | IfBlock | LoopBlock]" = field(default_factory=list)
    block_line: int | None = None
    action_lines: list[int] = field(default_factory=list)
    synthetic: bool = False


@dataclass(slots=True)
class ConditionalBranch:
    """A single branch (if / elif / else) in a conditional block."""

    kind: str  # "if", "elif", or "else"
    condition: str  # raw condition text; empty string for else
    actions: "list[str | IfBlock | LoopBlock]" = field(default_factory=list)
    action_lines: list[int] = field(default_factory=list)
    raw_actions: list[str] = field(default_factory=list)
    branch_line: int = 0


@dataclass(slots=True)
class IfBlock:
    """AST node for an if/elif/else conditional block."""

    branches: list[ConditionalBranch] = field(default_factory=list)


@dataclass(slots=True)
class LoopBlock:
    """AST node for a loop construct (REPEAT / FOR EACH / WHILE)."""

    kind: str  # "repeat", "for_each", or "while"
    # REPEAT N TIMES: count=N, var_name="i" (implicit counter)
    # FOR EACH {item} IN {collection}: var_name="item", collection_expr="collection"
    # WHILE condition: condition_text="..."
    count: int | None = None
    var_name: str | None = None
    collection_expr: str | None = None
    condition_text: str | None = None
    actions: "list[str | IfBlock | LoopBlock]" = field(default_factory=list)
    action_lines: list[int] = field(default_factory=list)
    raw_actions: list[str] = field(default_factory=list)
    loop_line: int = 0


def collect_loopblock_lines(loop_block: "LoopBlock") -> list[int]:
    """Recursively collect all action line numbers from a LoopBlock."""
    lines: list[int] = []
    for action, line_no in zip(loop_block.actions, loop_block.action_lines):
        if isinstance(action, IfBlock):
            lines.extend(collect_ifblock_lines(action))
        elif isinstance(action, LoopBlock):
            lines.extend(collect_loopblock_lines(action))
        else:
            lines.append(line_no)
    return lines


def collect_ifblock_lines(if_block: "IfBlock") -> list[int]:
    """Recursively collect all action line numbers from an IfBlock.

    Returns file line numbers from every branch (including nested
    conditionals) so that breakpoints can target inner conditional actions.
    """
    lines: list[int] = []
    for branch in if_block.branches:
        # Skip branch header lines (IF/ELIF/ELSE) — the runtime does not
        # assign action indices to conditional headers.
        for action, line_no in zip(branch.actions, branch.action_lines):
            if isinstance(action, IfBlock):
                lines.extend(collect_ifblock_lines(action))
            elif isinstance(action, LoopBlock):
                lines.extend(collect_loopblock_lines(action))
            else:
                lines.append(line_no)
    return lines


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

    ``if``/``elif``/``else:`` conditional blocks are collapsed into
    :class:`IfBlock` AST nodes, and ``REPEAT``/``FOR EACH``/``WHILE`` loop
    blocks are collapsed into :class:`LoopBlock` AST nodes — both attached
    inline inside each block's ``actions`` list.
    """
    raw_lines = [line.rstrip("\n") for line in task.splitlines() if line.strip()]
    if not raw_lines:
        return []

    resolved_lines = file_lines if file_lines and len(file_lines) == len(raw_lines) else [0] * len(raw_lines)
    # Keep both raw (with indentation) and stripped versions.
    mission_lines = [(raw.strip(), raw) for raw in raw_lines]

    # ── First pass: split into STEP blocks with raw lines ──
    raw_block_lines: list[tuple[list[str], list[str], list[int], str, int | None, bool]] = []
    _cur_stripped: list[str] = []
    _cur_raw: list[str] = []
    _cur_lines: list[int] = []
    _cur_name: str = "STEP: Default"
    _cur_line: int | None = None
    _cur_synthetic: bool = True

    for (stripped, raw), line_no in zip(mission_lines, resolved_lines):
        if classify_step(stripped) == "logical_step":
            if _cur_stripped or not _cur_synthetic:
                raw_block_lines.append((_cur_stripped, _cur_raw, _cur_lines, _cur_name, _cur_line, _cur_synthetic))
            _cur_stripped = []
            _cur_raw = []
            _cur_lines = []
            _cur_name = normalize_logical_step(stripped)
            _cur_line = line_no or None
            _cur_synthetic = False
            continue

        if not _cur_stripped and _cur_synthetic and not raw_block_lines:
            _cur_line = line_no or None

        _cur_stripped.append(stripped)
        _cur_raw.append(raw)
        _cur_lines.append(line_no or 0)

    if _cur_stripped or not _cur_synthetic:
        raw_block_lines.append((_cur_stripped, _cur_raw, _cur_lines, _cur_name, _cur_line, _cur_synthetic))

    # ── Second pass: parse conditional and loop blocks inside each STEP ──
    blocks: list[HuntBlock] = []
    for stripped_actions, raw_actions, action_lines, block_name, block_line, synthetic in raw_block_lines:
        parsed_actions, parsed_lines = _parse_conditionals(stripped_actions, raw_actions, action_lines)
        blk = HuntBlock(
            block_name=block_name,
            actions=parsed_actions,
            block_line=block_line,
            action_lines=parsed_lines,
            synthetic=synthetic,
        )
        blocks.append(blk)

    return [block for block in blocks if block.actions or not block.synthetic]


# ── Conditional block regexes ─────────────────────────────────────────────────

_RE_IF_LINE = re.compile(r"^(?:\d+\.\s*)?IF\s+(.+?):\s*$", re.IGNORECASE)
_RE_ELIF_LINE = re.compile(r"^(?:\d+\.\s*)?ELIF\s+(.+?):\s*$", re.IGNORECASE)
_RE_ELSE_LINE = re.compile(r"^(?:\d+\.\s*)?ELSE\s*:\s*$", re.IGNORECASE)

# ── Loop block regexes ────────────────────────────────────────────────────────

_RE_REPEAT_LINE = re.compile(r"^(?:\d+\.\s*)?REPEAT\s+(\d+)\s+TIMES\s*:\s*$", re.IGNORECASE)
_RE_FOR_EACH_LINE = re.compile(
    r"^(?:\d+\.\s*)?FOR\s+EACH\s+\{?(\w+)\}?\s+IN\s+\{?(\w+)\}?\s*:\s*$",
    re.IGNORECASE,
)
_RE_WHILE_LINE = re.compile(r"^(?:\d+\.\s*)?WHILE\s+(.+?):\s*$", re.IGNORECASE)


def _indent_level(raw_line: str) -> int:
    """Return the number of leading spaces in a raw line."""
    return len(raw_line) - len(raw_line.lstrip())


def _parse_conditionals(
    actions: list[str], raw_actions: list[str], action_lines: list[int]
) -> "tuple[list[str | IfBlock | LoopBlock], list[int]]":
    """Consume a flat action list and group if/elif/else and loop lines into AST nodes.

    Uses indentation from *raw_actions* to determine block body boundaries.
    Returns ``(parsed_actions, parsed_lines)`` where conditional blocks are
    replaced by a single :class:`IfBlock` entry and loop blocks by a
    :class:`LoopBlock` entry (with line number from the opening line).
    """
    result_actions: list[str | IfBlock | LoopBlock] = []
    result_lines: list[int] = []
    i = 0

    while i < len(actions):
        line = actions[i]
        line_no = action_lines[i] if i < len(action_lines) else 0

        m_if = _RE_IF_LINE.match(line)
        if m_if:
            if_block, consumed = _consume_if_block(actions, raw_actions, action_lines, i)
            result_actions.append(if_block)
            result_lines.append(line_no)
            i += consumed
            continue

        # Loop blocks
        m_repeat = _RE_REPEAT_LINE.match(line)
        m_for_each = _RE_FOR_EACH_LINE.match(line)
        m_while = _RE_WHILE_LINE.match(line)
        if m_repeat or m_for_each or m_while:
            loop_block, consumed = _consume_loop_block(actions, raw_actions, action_lines, i)
            result_actions.append(loop_block)
            result_lines.append(line_no)
            i += consumed
            continue

        # Stray elif/else outside an if block — error
        if _RE_ELIF_LINE.match(line):
            from .exceptions import ConditionalSyntaxError

            raise ConditionalSyntaxError(f"'ELIF' without a preceding 'IF' at line {line_no}: {line}")
        if _RE_ELSE_LINE.match(line):
            from .exceptions import ConditionalSyntaxError

            raise ConditionalSyntaxError(f"'ELSE' without a preceding 'IF' at line {line_no}: {line}")

        result_actions.append(line)
        result_lines.append(line_no)
        i += 1

    return result_actions, result_lines


def _consume_if_block(
    actions: list[str], raw_actions: list[str], action_lines: list[int], start: int
) -> "tuple[IfBlock, int]":
    """Parse an if/elif/else block starting at *start*.

    Uses indentation of the ``if`` header line to determine where branch
    bodies end (any line at or below the header's indentation level that is
    not an elif/else terminates the conditional block).

    Returns ``(IfBlock, number_of_lines_consumed)``.
    Raises :class:`ConditionalSyntaxError` on invalid syntax.
    """
    from .exceptions import ConditionalSyntaxError

    branches: list[ConditionalBranch] = []
    i = start
    has_else = False

    # Determine the indentation level of the opening if line.
    header_indent = _indent_level(raw_actions[start] if start < len(raw_actions) else "")

    while i < len(actions):
        line = actions[i]
        raw_line = raw_actions[i] if i < len(raw_actions) else line
        line_no = action_lines[i] if i < len(action_lines) else 0

        m_if = _RE_IF_LINE.match(line)
        m_elif = _RE_ELIF_LINE.match(line)
        m_else = _RE_ELSE_LINE.match(line)

        if m_if and i == start:
            # Opening 'if'
            condition = m_if.group(1).strip()
            branch = ConditionalBranch(kind="if", condition=condition, branch_line=line_no)
            i += 1
            i = _collect_branch_body(actions, raw_actions, action_lines, i, branch, header_indent)
            branches.append(branch)
        elif m_elif and _indent_level(raw_line) <= header_indent:
            if has_else:
                raise ConditionalSyntaxError(f"'ELIF' after 'ELSE' is not allowed at line {line_no}: {line}")
            if not branches:
                raise ConditionalSyntaxError(f"'ELIF' without a preceding 'IF' at line {line_no}: {line}")
            condition = m_elif.group(1).strip()
            branch = ConditionalBranch(kind="elif", condition=condition, branch_line=line_no)
            i += 1
            i = _collect_branch_body(actions, raw_actions, action_lines, i, branch, header_indent)
            branches.append(branch)
        elif m_else and _indent_level(raw_line) <= header_indent:
            if has_else:
                raise ConditionalSyntaxError(f"Multiple 'ELSE' blocks at line {line_no}: {line}")
            if not branches:
                raise ConditionalSyntaxError(f"'ELSE' without a preceding 'IF' at line {line_no}: {line}")
            has_else = True
            branch = ConditionalBranch(kind="else", condition="", branch_line=line_no)
            i += 1
            i = _collect_branch_body(actions, raw_actions, action_lines, i, branch, header_indent)
            branches.append(branch)
        elif i == start:
            # Must start with 'if'
            raise ConditionalSyntaxError(f"Expected 'IF' at line {line_no}: {line}")
        else:
            # Line is at header indent but not elif/else — end of block.
            break

    consumed = i - start
    if not branches:
        raise ConditionalSyntaxError("Empty conditional block")

    # Recursively parse nested conditionals inside each branch.
    # Use the real raw lines collected by _collect_branch_body() so that
    # the indentation hierarchy is preserved for arbitrarily deep nesting.
    for branch in branches:
        str_actions = [a for a in branch.actions if isinstance(a, str)]
        # Pair raw_actions with actions — only keep entries for str actions.
        str_raw = [r for a, r in zip(branch.actions, branch.raw_actions) if isinstance(a, str)]
        branch.actions, branch.action_lines = _parse_conditionals(
            str_actions,
            str_raw,
            list(branch.action_lines),
        )

    return IfBlock(branches=branches), consumed


def _collect_branch_body(
    actions: list[str],
    raw_actions: list[str],
    action_lines: list[int],
    i: int,
    branch: ConditionalBranch,
    header_indent: int,
) -> int:
    """Collect action lines belonging to a branch body.

    A line belongs to the body if its indentation is greater than
    *header_indent*. Stops when encountering a line at or below the
    header indentation level.
    """
    while i < len(actions):
        line = actions[i]
        raw_line = raw_actions[i] if i < len(raw_actions) else line
        line_no = action_lines[i] if i < len(action_lines) else 0
        line_indent = _indent_level(raw_line)

        # If the line is at or below the header indentation, it belongs
        # to the parent scope (might be elif/else or the next action).
        if line_indent <= header_indent:
            break

        branch.actions.append(line)
        branch.raw_actions.append(raw_line)
        branch.action_lines.append(line_no)
        i += 1

    return i


# ── Loop block parsing ────────────────────────────────────────────────────────

# Safety limit: maximum iterations for WHILE loops to prevent infinite loops.
MAX_LOOP_ITERATIONS = 100


def _consume_loop_block(
    actions: list[str], raw_actions: list[str], action_lines: list[int], start: int
) -> "tuple[LoopBlock, int]":
    """Parse a REPEAT/FOR EACH/WHILE loop block starting at *start*.

    Uses indentation of the loop header line to determine where the loop
    body ends (any line at or below the header's indentation level
    terminates the loop block).

    Returns ``(LoopBlock, number_of_lines_consumed)``.
    """
    line = actions[start]
    line_no = action_lines[start] if start < len(action_lines) else 0
    header_indent = _indent_level(raw_actions[start] if start < len(raw_actions) else "")

    m_repeat = _RE_REPEAT_LINE.match(line)
    m_for_each = _RE_FOR_EACH_LINE.match(line)
    m_while = _RE_WHILE_LINE.match(line)

    from .exceptions import ConditionalSyntaxError

    if m_repeat:
        count = int(m_repeat.group(1))
        if count < 1:
            raise ConditionalSyntaxError(
                f"Invalid REPEAT count at line {line_no}: {count}. REPEAT requires a positive integer (>= 1)."
            )
        loop = LoopBlock(kind="repeat", count=count, loop_line=line_no)
    elif m_for_each:
        var_name = m_for_each.group(1)
        if var_name.lower() == "i":
            raise ConditionalSyntaxError(
                f"Invalid FOR EACH loop variable at line {line_no}: "
                "{{i}} is reserved for the engine's automatic loop counter."
            )
        loop = LoopBlock(
            kind="for_each",
            var_name=var_name,
            collection_expr=m_for_each.group(2),
            loop_line=line_no,
        )
    elif m_while:
        loop = LoopBlock(kind="while", condition_text=m_while.group(1).strip(), loop_line=line_no)
    else:
        raise ConditionalSyntaxError(f"Unrecognized loop syntax at line {line_no}: {line}")

    # Collect body lines (indentation > header)
    i = start + 1
    body_stripped: list[str] = []
    body_raw: list[str] = []
    body_lines: list[int] = []

    while i < len(actions):
        raw_line = raw_actions[i] if i < len(raw_actions) else actions[i]
        if _indent_level(raw_line) <= header_indent:
            break
        body_stripped.append(actions[i])
        body_raw.append(raw_line)
        body_lines.append(action_lines[i] if i < len(action_lines) else 0)
        i += 1

    consumed = i - start

    if not body_stripped:
        from .exceptions import ConditionalSyntaxError

        raise ConditionalSyntaxError(f"Empty loop body at line {line_no}: {line.strip()}")

    # Recursively parse nested conditionals and loops inside the body.
    loop.actions, loop.action_lines = _parse_conditionals(body_stripped, body_raw, body_lines)
    loop.raw_actions = body_raw

    return loop, consumed


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
    ``"debug_vars"``, ``"debug"``, ``"done"``, ``"use_import"``,
    ``"if_block"``, ``"elif_block"``, ``"else_block"``,
    ``"repeat_loop"``, ``"for_each_loop"``, ``"while_loop"``,
    or ``"action"``.
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
