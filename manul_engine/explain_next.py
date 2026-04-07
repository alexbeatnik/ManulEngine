# manul_engine/explain_next.py
"""
ExplainNextDebugger — interactive What-If Analysis REPL for ManulEngine.

When a test hits a breakpoint or a failure, this module drops the user
into an interactive REPL that allows *hypothetical* step evaluation
against the live browser state **without mutating** the page.

The REPL captures a read-only DOM snapshot plus visible-text context,
sends the hypothetical step to the configured LLM with a specialised
"Score and Explain" prompt, and returns a confidence score (0–10) plus
a human-readable explanation of the expected outcome.

Usage (hooked into the debug pause loop):

    debugger = ExplainNextDebugger(engine)
    # During a debug pause, with the browser still alive:
    await debugger.run_repl(page, current_step="Click the 'Login' button")

Architecture:
    - ``PageContext``     — frozen snapshot of the current page state
    - ``WhatIfResult``    — structured dry-run result (score + explanation)
    - ``ExplainNextDebugger`` — the REPL controller (async, Playwright-safe)
"""

from __future__ import annotations

import asyncio
import re
import textwrap
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .helpers import classify_step, detect_mode, extract_quoted
from .js_scripts import SNAPSHOT_JS
from .llm import LLMProvider
from .logging_config import logger
from .scoring import SCALE, score_elements

if TYPE_CHECKING:
    from playwright.async_api import Page

_log = logger.getChild("explain_next")


# ── LLM prompt template ──────────────────────────────────────────────────────

WHAT_IF_SYSTEM_PROMPT: str = textwrap.dedent("""\
    You are an expert Web Automation Analyst for the ManulEngine framework.
    Your task is to evaluate a HYPOTHETICAL browser action WITHOUT executing it.

    You will receive:
    1. The current page URL.
    2. A simplified DOM snapshot listing visible, interactive elements
       (tag, text, aria-label, placeholder, id, data-qa, role, disabled state).
    3. The last successfully executed step (for context continuity).
    4. A hypothetical next step the user wants to evaluate.

    Your job:
    - Determine whether the hypothetical step CAN be performed on the
      current page state (is a matching target element present and enabled?).
    - Estimate the CONFIDENCE that this step would succeed (0–10 scale):
        0  = impossible (target element does not exist on the page)
        1–3 = low confidence (ambiguous target, multiple candidates, or
               the element is likely disabled/hidden)
        4–6 = moderate (plausible target exists, but there is some
               ambiguity or the action might have side effects)
        7–9 = high confidence (clear, unique target element found,
               action type matches element type)
        10 = certain (exact unique match, no ambiguity at all)
    - Explain what would LIKELY happen if the step were executed:
      page navigation, form state change, modal appearance, error, etc.
    - If the step would fail, explain WHY and suggest a corrected step.

    Respond ONLY with a JSON object (no markdown fences, no extra text):
    {
      "score": <int 0–10>,
      "target_found": <bool>,
      "target_element": "<brief description of the matched element or null>",
      "explanation": "<what would happen if this step executes>",
      "risk": "<potential side effects or failure modes>",
      "suggestion": "<improved step phrasing if score < 7, else null>"
    }
""")


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PageContext:
    """Read-only snapshot of the current browser page state."""

    url: str
    title: str
    elements: list[dict] = field(default_factory=list)
    visible_text_snippet: str = ""

    def to_prompt_text(self, max_elements: int = 60) -> str:
        """Format the page context as a concise prompt section."""
        lines: list[str] = [
            f"URL: {self.url}",
            f"Title: {self.title}",
            f"Visible text (truncated): {self.visible_text_snippet[:500]}",
            "",
            f"Interactive elements ({min(len(self.elements), max_elements)} of {len(self.elements)} shown):",
        ]
        for el in self.elements[:max_elements]:
            tag = el.get("tag_name", "?")
            name = el.get("name", "")[:80]
            aria = el.get("aria_label", "")
            ph = el.get("placeholder", "")
            dqa = el.get("data_qa", "")
            hid = el.get("html_id", "")
            role = el.get("role", "")
            disabled = el.get("disabled", False)
            inp_type = el.get("input_type", "")
            parts = [f"<{tag}"]
            if inp_type:
                parts.append(f' type="{inp_type}"')
            if hid:
                parts.append(f' id="{hid}"')
            if dqa:
                parts.append(f' data-qa="{dqa}"')
            if role:
                parts.append(f' role="{role}"')
            if aria:
                parts.append(f' aria-label="{aria}"')
            if ph:
                parts.append(f' placeholder="{ph}"')
            if disabled:
                parts.append(" disabled")
            parts.append(f"> {name}")
            lines.append("  " + "".join(parts))
        return "\n".join(lines)


@dataclass(frozen=True)
class WhatIfResult:
    """Structured result of a hypothetical step evaluation."""

    step: str
    score: int  # 0–10 confidence
    target_found: bool
    target_element: str | None
    explanation: str
    risk: str
    suggestion: str | None
    heuristic_score: int | None = None  # DOMScorer best score (scaled int)
    heuristic_match: str | None = None  # DOMScorer best candidate name

    @property
    def confidence_label(self) -> str:
        if self.score >= 8:
            return "HIGH"
        if self.score >= 5:
            return "MODERATE"
        if self.score >= 1:
            return "LOW"
        return "IMPOSSIBLE"

    def format_report(self) -> str:
        """Return a human-readable multi-line report."""
        lines = [
            "",
            f'    ┌─ 🔮 WHAT-IF ANALYSIS: "{self.step}"',
            f"    │  Confidence: {self.score}/10 ({self.confidence_label})",
        ]
        if self.heuristic_score is not None:
            norm = self.heuristic_score / SCALE
            lines.append(f"    │  Heuristic Score: {norm:.3f} (raw {self.heuristic_score})")
        if self.heuristic_match:
            lines.append(f'    │  Best Heuristic Match: "{self.heuristic_match}"')
        if self.target_element:
            lines.append(f"    │  Target Element: {self.target_element}")
        lines.append(f"    │  Explanation: {self.explanation}")
        if self.risk:
            lines.append(f"    │  Risk: {self.risk}")
        if self.suggestion:
            lines.append(f"    │  Suggestion: {self.suggestion}")
        lines.append("    └─ 🔮 END")
        lines.append("")
        return "\n".join(lines)


# ── Context extraction (read-only) ───────────────────────────────────────────

_VISIBLE_TEXT_JS: str = """
() => {
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        { acceptNode: (n) => {
            const p = n.parentElement;
            if (!p) return NodeFilter.FILTER_REJECT;
            const tag = p.tagName;
            if (['SCRIPT','STYLE','NOSCRIPT','TEMPLATE'].includes(tag))
                return NodeFilter.FILTER_REJECT;
            try { if (!p.checkVisibility()) return NodeFilter.FILTER_REJECT; }
            catch(e) {}
            return NodeFilter.FILTER_ACCEPT;
        }}
    );
    const parts = [];
    let node;
    while ((node = walker.nextNode()) && parts.length < 200) {
        const t = node.textContent.trim();
        if (t) parts.push(t);
    }
    return parts.join(' ').substring(0, 2000);
}
"""


async def capture_page_context(page: Page) -> PageContext:
    """Capture a read-only snapshot of the page for LLM context.

    This function does NOT mutate the page state in any way.
    It captures the URL, title, visible text, and a DOM snapshot
    of interactive elements using the same SNAPSHOT_JS used by the engine.
    """
    url = page.url
    try:
        title = await page.title()
    except (OSError, RuntimeError):
        title = ""

    # Grab visible text — lightweight TreeWalker (read-only)
    try:
        visible_text = await page.evaluate(_VISIBLE_TEXT_JS)
    except (OSError, RuntimeError):
        visible_text = ""

    # DOM snapshot — identical to what the engine uses for element resolution.
    # mode="locate" + empty texts → captures everything without filtering.
    elements: list[dict] = []
    try:
        for idx, frame in enumerate(page.frames):
            try:
                frame_els = await frame.evaluate(SNAPSHOT_JS, ["locate", []])
                for el in frame_els:
                    el["frame_index"] = idx
                elements.extend(frame_els)
            except Exception:
                if idx == 0:
                    raise
                continue  # skip unreachable/cross-origin child frames
    except (OSError, RuntimeError):
        _log.debug("capture_page_context: page context lost during snapshot")

    return PageContext(
        url=url,
        title=title,
        elements=elements,
        visible_text_snippet=str(visible_text)[:2000],
    )


# ── Heuristic pre-check (read-only scoring) ──────────────────────────────────


@dataclass(frozen=True)
class _HeuristicHit:
    """Best candidate from heuristic pre-check (read-only scoring)."""

    score: int
    name: str
    xpath: str
    frame_index: int


def _heuristic_pre_check(
    elements: list[dict],
    step: str,
    search_texts: list[str],
    target_field: str | None,
    *,
    learned_elements: dict | None = None,
    last_xpath: str | None = None,
) -> _HeuristicHit | None:
    """Run the DOMScorer against the snapshot to find the best candidate.

    Returns a ``_HeuristicHit`` or ``None`` when no elements are
    available.  This is strictly read-only — no Playwright calls, no
    page mutations.
    """
    if not elements:
        return None
    mode = detect_mode(step)
    is_blind = not search_texts and not target_field
    scored = score_elements(
        elements,
        step,
        mode,
        search_texts,
        target_field,
        is_blind,
        learned_elements=learned_elements or {},
        last_xpath=last_xpath,
        explain=False,
    )
    if scored:
        best = scored[0]
        return _HeuristicHit(
            score=int(best.get("score", 0)),
            name=best.get("name", ""),
            xpath=best.get("xpath", ""),
            frame_index=best.get("frame_index", 0),
        )
    return None


# ── ExplainNextDebugger ──────────────────────────────────────────────────────


class ExplainNextDebugger:
    """Interactive What-If Analysis REPL for debug sessions.

    Evaluates hypothetical steps against the live browser state using
    a combination of deterministic heuristic scoring and LLM analysis —
    all without executing any actions on the page.

    Parameters
    ----------
    llm : LLMProvider
        The LLM provider to use for analysis (``OllamaProvider`` or
        ``NullProvider`` for heuristics-only evaluation).
    learned_elements : dict
        The engine's semantic cache (read-only access for scoring context).
    last_xpath : str | None
        The most recently resolved xpath for context-reuse scoring.
    """

    def __init__(
        self,
        llm: LLMProvider,
        learned_elements: dict | None = None,
        last_xpath: str | None = None,
        engine: object | None = None,
    ) -> None:
        self._llm = llm
        self._learned_elements = learned_elements or {}
        self._last_xpath = last_xpath
        self._engine = engine  # _DebugMixin ref for highlight calls
        self._history: list[WhatIfResult] = []

    @property
    def history(self) -> list[WhatIfResult]:
        """All what-if evaluations performed in this session."""
        return list(self._history)

    # ── Core analysis (read-only) ─────────────────────────────────────

    async def evaluate(
        self,
        page: Page,
        hypothetical_step: str,
        *,
        last_step: str = "",
    ) -> WhatIfResult:
        """Evaluate a hypothetical step against the current page state.

        This method captures a snapshot, runs heuristic scoring
        in-memory, and optionally queries the LLM.  The page is not
        navigated, clicked, or filled — however ``_highlight_match``
        applies a reversible debug highlight and scrolls the best
        candidate into view (cosmetic DOM mutation, cleaned up
        automatically).

        Parameters
        ----------
        page : Page
            The live Playwright page (read-only access).
        hypothetical_step : str
            The step to evaluate (DSL command or natural language).
        last_step : str
            The last successfully executed step (provides continuity context).

        Returns
        -------
        WhatIfResult
            Structured analysis with score, explanation, and suggestions.
        """
        ctx = await capture_page_context(page)

        # Extract quoted targets for heuristic scoring — mirror
        # _ActionsMixin._execute_step so cache keys and scorer inputs match.
        step_class = classify_step(hypothetical_step)
        mode = detect_mode(hypothetical_step)
        preserve = mode in ("input", "select")
        expected = extract_quoted(hypothetical_step, preserve_case=preserve)
        target_field = None
        search_texts = expected

        step_lower = hypothetical_step.lower()
        if mode == "input" and expected:
            # Strip value from search_texts exactly like _execute_step.
            step_l_unquoted = re.sub(
                r"""(['"])(?:\\.|(?!\1).)*\1""",
                " ",
                step_lower,
            )
            if re.search(r"\binto\b", step_l_unquoted):
                search_texts = expected[1:]  # value-first: target is rest
            else:
                search_texts = expected[:-1]  # Fill … with: target is head
        elif mode == "select" and len(expected) >= 2:
            step_l_unquoted = re.sub(
                r"""(['"])(?:\\.|(?!\1).)*\1""",
                " ",
                step_lower,
            )
            if re.search(r"\bfrom\b", step_l_unquoted):
                search_texts = expected[1:]

        target_field = search_texts[0] if search_texts else None

        # Heuristic pre-check (deterministic, no page interaction)
        hit = _heuristic_pre_check(
            ctx.elements,
            hypothetical_step,
            search_texts,
            target_field,
            learned_elements=self._learned_elements,
            last_xpath=self._last_xpath,
        )
        h_score = hit.score if hit else None
        h_match = hit.name if hit else None

        # Build the LLM user prompt
        user_prompt = (
            f"CURRENT PAGE STATE:\n{ctx.to_prompt_text()}\n\n"
            f"LAST EXECUTED STEP: {last_step or '(none)'}\n\n"
            f"HYPOTHETICAL NEXT STEP: {hypothetical_step}\n"
        )

        # Query LLM for analysis
        result = await self._llm.call_json(WHAT_IF_SYSTEM_PROMPT, user_prompt)

        if result and isinstance(result, dict):
            what_if = WhatIfResult(
                step=hypothetical_step,
                score=max(0, min(10, int(result.get("score", 0)))),
                target_found=bool(result.get("target_found", False)),
                target_element=result.get("target_element"),
                explanation=str(result.get("explanation", "")),
                risk=str(result.get("risk", "")),
                suggestion=result.get("suggestion"),
                heuristic_score=h_score,
                heuristic_match=h_match,
            )
        else:
            # LLM unavailable — build result from heuristics alone
            what_if = self._heuristic_only_result(
                hypothetical_step,
                step_class,
                ctx,
                search_texts,
                h_score,
                h_match,
            )

        # Highlight the best-matched element on the live page
        await self._highlight_match(page, hit)

        self._history.append(what_if)
        return what_if

    async def _highlight_match(
        self,
        page: Page,
        hit: _HeuristicHit | None,
    ) -> None:
        """Highlight the best heuristic match on the live page.

        Uses the engine's persistent debug highlight (magenta outline +
        glow) so the element stays visible while the user reads the
        analysis.  The highlight is cleared before the next evaluation
        or when the REPL exits.
        """
        if hit is None or not hit.xpath or self._engine is None:
            return
        eng = self._engine
        try:
            await eng._clear_debug_highlight(page)  # type: ignore[attr-defined]
            frames = page.frames
            frame = frames[hit.frame_index] if 0 <= hit.frame_index < len(frames) else page
            loc = frame.locator(f"xpath={hit.xpath}").first
            await loc.scroll_into_view_if_needed(timeout=2000)
            await eng._debug_highlight(page, loc)  # type: ignore[attr-defined]
        except Exception as exc:
            _log.debug("highlight_match: could not highlight element: %s", exc)

    def _heuristic_only_result(
        self,
        step: str,
        step_class: str,
        ctx: PageContext,
        search_texts: list[str],
        h_score: int | None,
        h_match: str | None,
    ) -> WhatIfResult:
        """Build a WhatIfResult using only deterministic heuristic data."""
        # Derive a confidence score from heuristic score
        if h_score is None or h_score == 0:
            score = 0
            found = False
            explanation = "No matching element found in the DOM snapshot."
        else:
            norm = h_score / SCALE
            if norm >= 1.0:
                score = 10
            elif norm >= 0.5:
                score = 9
            elif norm >= 0.1:
                score = 7
            elif norm >= 0.05:
                score = 5
            elif norm >= 0.01:
                score = 3
            else:
                score = 1
            found = True
            explanation = (
                f"Heuristic scoring found a candidate "
                f'"{h_match}" with normalized score {norm:.3f}. '
                f"The step appears viable based on element matching."
            )

        # System steps (NAVIGATE, WAIT, explicit waits, etc.) don't need
        # element resolution.
        if step_class in (
            "navigate",
            "wait",
            "wait_for_element",
            "scroll",
            "press_enter",
            "done",
            "logical_step",
            "set_var",
            "scan_page",
        ):
            score = max(score, 8)
            found = True
            explanation = f"System command '{step_class}' — does not require element resolution."

        return WhatIfResult(
            step=step,
            score=score,
            target_found=found,
            target_element=h_match,
            explanation=explanation,
            risk="Heuristic-only evaluation — LLM unavailable for deeper analysis.",
            suggestion=None,
            heuristic_score=h_score,
            heuristic_match=h_match,
        )

    # ── Interactive REPL ──────────────────────────────────────────────

    _REPL_HELP: str = textwrap.dedent("""\
        ┌─ 🔮 Explain Next REPL ──────────────────────────────────────
        │  Commands:
        │    <any step>   — evaluate a hypothetical step (dry-run)
        │    !history     — show all evaluations from this session
        │    !execute     — accept the last evaluated step & resume
        │    !execute N   — accept evaluation #N from history & resume
        │    !context     — show current page URL & title
        │    !help        — show this help
        │    !quit        — exit REPL without executing anything
        └──────────────────────────────────────────────────────────────
    """)

    async def run_repl(
        self,
        page: Page,
        *,
        current_step: str = "",
    ) -> str | None:
        """Run the interactive What-If REPL.

        Returns the step string the user chose to execute, or ``None``
        if they quit without selecting a step.

        Parameters
        ----------
        page : Page
            The live Playwright page (kept alive, never mutated).
        current_step : str
            The step that was about to execute when the debugger paused.
        """
        print(self._REPL_HELP)
        if current_step:
            print(f'    ℹ️  Paused before: "{current_step}"\n')

        last_step = current_step

        try:
            while True:
                try:
                    user_input = await asyncio.to_thread(input, "  🔮 explain-next> ")
                except (EOFError, KeyboardInterrupt):
                    print("\n    Exiting Explain Next REPL.")
                    return None

                user_input = user_input.strip()
                if not user_input:
                    continue

                # ── REPL meta-commands ──
                if user_input == "!quit":
                    print("    Exiting Explain Next REPL.")
                    return None

                if user_input == "!help":
                    print(self._REPL_HELP)
                    continue

                if user_input == "!context":
                    try:
                        url = page.url
                        title = await page.title()
                        print(f"    URL:   {url}")
                        print(f"    Title: {title}")
                    except (OSError, RuntimeError):
                        print("    ⚠️  Page context lost.")
                    continue

                if user_input == "!history":
                    if not self._history:
                        print("    (no evaluations yet)")
                    else:
                        for i, r in enumerate(self._history, 1):
                            print(f"    #{i}  [{r.score}/10 {r.confidence_label}] {r.step}")
                    continue

                if user_input.startswith("!execute"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) == 2 and parts[1].isdigit():
                        idx = int(parts[1]) - 1
                        if 0 <= idx < len(self._history):
                            chosen = self._history[idx].step
                            print(f'    ✅ Executing: "{chosen}"')
                            return chosen
                        else:
                            print(f"    ⚠️  Invalid index. History has {len(self._history)} entries.")
                            continue
                    elif self._history:
                        chosen = self._history[-1].step
                        print(f'    ✅ Executing: "{chosen}"')
                        return chosen
                    else:
                        print("    ⚠️  No evaluations in history. Evaluate a step first.")
                        continue

                # ── Evaluate a hypothetical step ──
                print("    ⏳ Analyzing...")
                try:
                    result = await self.evaluate(
                        page,
                        user_input,
                        last_step=last_step,
                    )
                    print(result.format_report())
                except Exception as exc:
                    _log.warning("Explain Next evaluation failed: %s", exc)
                    print(f"    ❌ Evaluation failed: {exc}")
        finally:
            # Clean up highlight when leaving the REPL
            if self._engine is not None:
                try:
                    await self._engine._clear_debug_highlight(page)  # type: ignore[attr-defined]
                except (OSError, RuntimeError):
                    pass
