# manul_engine/core.py
"""
ManulEngine — the main browser automation class.

Orchestrates the full automation pipeline:
  1. Parse mission into steps (LLM planner, numbered list, or unnumbered action lines)
  2. For each step, detect interaction mode and resolve the target element
  3. Delegate action execution to the _ActionsMixin (engine/actions.py)

Element resolution uses a multi-stage pipeline:
  DOM snapshot (JS) → heuristic scoring → optional LLM fallback → anti-phantom guard

Inherits action handlers from _ActionsMixin (navigate, scroll, extract, verify,
drag-and-drop, click/type/select/hover via _execute_step).
"""

import asyncio
import base64
import inspect
import os
import re
import sys
import time
import traceback
from os import environ as _environ
from pathlib import Path
from typing import TYPE_CHECKING

from .cdp import CDPBrowser

if TYPE_CHECKING:
    from ._types import ElementSnapshot  # noqa: F401
    from .cdp import CDPBrowser as BrowserContext
    from .cdp import CDPFrame as Frame  # noqa: F401 — name kept for annotations
    from .cdp import CDPPage as Page


class _AsyncNull:
    """Trivial async context manager (replaces the old async_playwright scope)."""

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_exc: object) -> bool:
        return False


from . import prompts
from . import prompts as _prompts_mod  # alias for CUSTOM_CONTROLS_DIRS access
from .actions import _ActionsMixin
from .config import EngineConfig
from .controls import ControlContext, diagnose_custom_control_miss, get_custom_control, load_custom_controls
from .debug import _DebugMixin
from .exceptions import ConfigurationError
from .helpers import (
    MAX_LOOP_ITERATIONS,
    RE_SYSTEM_STEP,
    ContextualHint,
    IfBlock,
    LoopBlock,
    classify_step,
    compact_log_field,
    detect_mode,
    extract_print_message,
    extract_quoted,
    parse_explicit_wait,
    parse_hunt_blocks,
    substitute_memory,
)
from .hooks import bind_hook_result, execute_hook_line
from .js_scripts import SNAPSHOT_JS
from .logging_config import logger
from .reporting import BlockResult, MissionResult, StepResult
from .scoring import SCALE, score_elements
from .variables import ScopedVariables

_log = logger.getChild("core")

# ── Pre-compiled patterns ─────────────────────────────────────────────────────
_RE_NUMBERED_PREFIX = re.compile(r"^\s*\d+\.\s*")

# ── Score confidence thresholds (normalised 0.0–1.0 floats) ──────────────────
# Compared against best_score / SCALE.  Values > 1.0 are possible because the
# cache channel weight (2.0) allows the weighted sum to exceed 1.0.
THRESHOLD_SEMANTIC_CACHE = 1.125  # semantic cache reuse (~200k scaled)
THRESHOLD_HIGH_CONFIDENCE = 0.112  # strong heuristic match (~20k scaled)
THRESHOLD_CONTEXT_REUSE = 0.056  # blind/context reuse from previous step


def _confidence(score: int) -> float:
    """Convert a scaled integer score to the normalized weighted-score ratio."""
    return score / SCALE


class ManulEngine(_DebugMixin, _ActionsMixin):
    def __init__(
        self,
        headless: "bool | None" = None,
        browser: "str | None" = None,
        browser_args: "list[str] | None" = None,
        debug_mode: bool = False,
        break_steps: "set[int] | None" = None,
        break_file_lines: "set[int] | None" = None,
        disable_cache: bool = False,
        semantic_cache: "bool | None" = None,  # None → read from config/env
        explain_mode: "bool | None" = None,
        required_controls: "set[str] | None" = None,  # lazy-load: filenames from extract_required_controls
        config: "EngineConfig | None" = None,  # injectable config (takes priority)
        **_kwargs,
    ):
        # When an EngineConfig is provided, it serves as the default layer
        # between explicit keyword arguments and prompts.* module globals.
        # Priority: explicit kwargs > EngineConfig > prompts module globals.
        _cfg = config

        self.headless = headless if headless is not None else (_cfg.headless if _cfg else prompts.HEADLESS_MODE)
        # The CDP backend always drives Chrome/Chromium; 'electron' attaches to a
        # running Chrome/Electron over CDP instead of launching a fresh browser.
        _VALID_BROWSERS = ("chromium", "electron")
        _b = (browser or (_cfg.browser if _cfg else prompts.BROWSER)).strip().lower()
        self.browser: str = _b if _b in _VALID_BROWSERS else "chromium"
        self.browser_args: list[str] = (
            list(browser_args)
            if browser_args is not None
            else (list(_cfg.browser_args) if _cfg else list(prompts.BROWSER_ARGS))
        )
        # channel / executable_path: accept via **_kwargs or EngineConfig with fallback to config/env.
        _ch = _kwargs.pop("channel", None)
        self.channel: str | None = (
            (str(_ch).strip() or None) if _ch is not None else (_cfg.channel if _cfg else prompts.CHANNEL)
        )
        _ep = _kwargs.pop("executable_path", None)
        self.executable_path: str | None = (
            str(_ep) if _ep is not None else (_cfg.executable_path if _cfg else prompts.EXECUTABLE_PATH)
        )
        # cdp_endpoint: attach to an already-running browser over CDP instead of
        # launching (mirrors ManulHeart's --cdp). Accepted via **_kwargs / config
        # / MANUL_CDP_ENDPOINT env, like channel/executable_path above.
        _cdp = _kwargs.pop("cdp_endpoint", None)
        self._cdp_endpoint: str | None = (
            (str(_cdp).strip() or None)
            if _cdp is not None
            else (_cfg.cdp_endpoint if _cfg else getattr(prompts, "CDP_ENDPOINT", None))
        )
        if self.channel is not None and self.browser != "chromium":
            raise ConfigurationError(
                f"Playwright 'channel' is only supported for Chromium, "
                f"but got browser={self.browser!r} with channel={self.channel!r}."
            )
        self.memory: ScopedVariables = ScopedVariables()
        self.last_xpath: str | None = None
        self.learned_elements: dict = {}  # semantic cache: cache_key → {name, tag}

        # Semantic cache (in-memory, per-session): feeds the scorer as one
        # channel — it never bypasses scoring, so it cannot return a stale
        # element. ``disable_cache`` turns it off.
        if semantic_cache is not None:
            self._semantic_cache_enabled = semantic_cache
        elif disable_cache:
            self._semantic_cache_enabled = False
        elif _cfg:
            self._semantic_cache_enabled = _cfg.semantic_cache_enabled
        else:
            self._semantic_cache_enabled = bool(getattr(prompts, "SEMANTIC_CACHE_ENABLED", True))

        # ── Timeouts ──────────────────────────────────────────────────────
        self.timeout: int = _cfg.timeout if _cfg else prompts.TIMEOUT
        self.nav_timeout: int = _cfg.nav_timeout if _cfg else prompts.NAV_TIMEOUT
        self._verify_max_retries: int = (
            _cfg.verify_max_retries if _cfg else int(getattr(prompts, "VERIFY_MAX_RETRIES", 15))
        )

        # ── Auto-annotate ─────────────────────────────────────────────────
        _auto_annotate_default = _cfg.auto_annotate if _cfg else prompts.AUTO_ANNOTATE
        self._auto_annotate: bool = _kwargs.pop("auto_annotate", _auto_annotate_default)

        self.debug_mode = debug_mode
        if explain_mode is not None:
            self.explain_mode = explain_mode
        elif _cfg:
            self.explain_mode = _cfg.explain_mode
        else:
            self.explain_mode = False
        self._debug_continue = False  # set to True by 'Continue All' in debug session
        self._user_break_steps: set[int] = set(break_steps) if break_steps else set()
        self.break_steps: set[int] = set(self._user_break_steps)
        self._break_file_lines: set[int] = set(break_file_lines) if break_file_lines else set()
        # Last element-resolution scoring data — used by 'explain' debug command.
        self._last_explain_data: tuple[str, list[str], list[dict]] | None = None
        # Tracks how many annotation lines have been inserted into the hunt file
        # during this run, so subsequent NAVIGATE steps can offset their line numbers.
        self._annotate_line_offset: int = 0
        # Deferred @custom_control loading: stored here, applied on first run_mission().
        self._required_controls: set[str] | None = required_controls
        # Custom controls directories (prefer EngineConfig, fallback to prompts).
        self._custom_controls_dirs: list[str] = (
            list(_cfg.custom_controls_dirs)
            if _cfg
            else list(getattr(_prompts_mod, "CUSTOM_CONTROLS_DIRS", ["controls"]))
        )
        # What-if REPL: when the debugger's Explain Next session chooses a step
        # to execute, it is stored here and injected into the mission flow.
        self._what_if_execute_step: str | None = None
        if self.debug_mode:
            print("    🐛 Debug mode ON — engine will pause before each step.")

    def reset_session_state(self) -> None:
        """Clear in-memory caches and runtime (row/step) variables.

        Resets heuristic caches (``learned_elements``, ``last_xpath``)
        and row/step-scoped variables via ``clear_runtime()``.
        Mission- and global-scoped variables are preserved.
        """
        self.memory.clear_runtime()
        self.learned_elements.clear()
        self.last_xpath = None
        self._annotate_line_offset = 0

    # ── Visual feedback & debug prompt ────────
    # All debug methods (_highlight, _debug_highlight, _clear_debug_highlight,
    # _inject_debug_modal, _remove_debug_modal, _poll_for_abort, _debug_prompt)
    # are provided by _DebugMixin from debug.py.

    # ── DOM snapshot ──────────────────────────

    def _frame_for(self, page, el: dict):
        """Return the Playwright Frame that owns *el*.

        Elements discovered in child frames carry a ``frame_index`` key set
        during ``_snapshot``.  Index 0 is always the main frame.  If the
        stored index is stale (frame navigated away) we fall back to the
        main frame so callers never get ``None``.
        """
        idx = el.get("frame_index", 0)
        url = el.get("frame_url")
        name = el.get("frame_name")
        frames = page.frames

        # 1. Try URL and name match (most robust across frame reloads)
        if url is not None and name is not None:
            for f in frames:
                if f.url == url and f.name == name:
                    return f

        # 2. Try blind index fallback (assuming no frame shifting)
        if 0 <= idx < len(frames):
            return frames[idx]

        return page  # main frame fallback

    async def _snapshot(self, page, mode: str, texts: list[str]) -> list[dict]:
        """Inject SNAPSHOT_JS into every reachable frame and merge results.

        Each element dict gets a ``frame_index`` so the action layer can
        route clicks / fills to the correct Playwright Frame object.
        Cross-origin or detached child frames are silently skipped;
        unexpected errors in the main frame are surfaced to aid debugging.
        """
        args = [mode, texts or []]
        all_elements: list[dict] = []

        for idx, frame in enumerate(page.frames):
            for attempt in range(3):
                try:
                    frame_els = await frame.evaluate(SNAPSHOT_JS, args)
                    for el in frame_els:
                        el["frame_index"] = idx
                        el["frame_url"] = frame.url
                        el["frame_name"] = frame.name
                    all_elements.extend(frame_els)
                    break  # success — stop retry loop
                except Exception as exc:
                    err_msg = str(exc).lower()
                    if ("closed" in err_msg or "execution context" in err_msg or "detached" in err_msg) and attempt < 2:
                        await asyncio.sleep(1.5)
                        continue
                    if idx == 0:
                        raise
                    break  # child frame unreachable / cross-origin — skip

        return all_elements

    # ── Explain mode output ─────────────────

    @staticmethod
    def _print_explain(step: str, search_texts: list[str], top: list[dict]) -> None:
        """Print a formatted score breakdown for the top candidates to stderr."""
        target_str = ", ".join(search_texts) if search_texts else "(blind)"
        lines = [
            f'\n    ┌─ 🔍 EXPLAIN: Target = "{target_str}"',
            f"    │  Step: {step}",
            f"    │  Top {len(top)} candidates:",
        ]
        for rank, el in enumerate(top, 1):
            name = compact_log_field(el.get("name", ""), "MANUL_LOG_NAME_MAXLEN")
            tag = el.get("tag_name", "?")
            score = el.get("score", 0)
            expl = el.get("_explain")
            if expl:
                lines.append("    │")
                lines.append(f'    │  #{rank}  <{tag}> "{name}"  → Total: {expl["total"]:.3f}')
                lines.append(f"    │       Text:       {expl['text']:>+.3f}")
                lines.append(f"    │       Attributes: {expl['attributes']:>+.3f}")
                lines.append(f"    │       Semantics:  {expl['semantics']:>+.3f}")
                lines.append(f"    │       Proximity:  {expl['proximity']:>+.3f}")
                lines.append(f"    │       Cache:      {expl['cache']:>+.3f}")
                if expl["penalty"] < 1.0:
                    lines.append(f"    │       Penalty:    ×{expl['penalty']:.1f}")
                if "ctx_kind" in expl:
                    ctx_label = expl["ctx_kind"].upper().replace("_", " ")
                    lines.append(f"    │       Context:    {ctx_label} (raw={expl.get('ctx_prox_raw', 0):.3f})")
            else:
                lines.append(f'    │  #{rank}  <{tag}> "{name}"  → Score: {score}')
        winner = top[0]
        winner_expl = winner.get("_explain")
        winner_name = compact_log_field(winner.get("name", ""), "MANUL_LOG_NAME_MAXLEN")
        winner_display = f"{winner_expl['total']:.3f}" if winner_expl else str(winner.get("score", 0))
        # Contextual explain summary for the winner
        ctx_summary = ""
        if winner_expl and "ctx_kind" in winner_expl:
            rect_top = winner.get("rect_top", 0)
            rect_left = winner.get("rect_left", 0)
            ctx_summary = f" [{winner_expl['ctx_kind'].upper().replace('_', ' ')} at ({rect_left},{rect_top})]"
        lines.append("    │")
        lines.append(f'    └─ ✅ Decision: Selected "{winner_name}" with score {winner_display}{ctx_summary}')
        lines.append("")
        sys.stderr.write("\n".join(lines) + "\n")
        sys.stderr.flush()

    # ── Scoring (delegates to scoring module) ─

    def _score_elements(
        self,
        els: list[dict],
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        is_blind: bool,
        contextual_hint: "ContextualHint | None" = None,
        anchor_rect: "dict | None" = None,
        container_elements: "list[dict] | None" = None,
        viewport_height: int = 0,
    ) -> list[dict]:
        """Score and rank elements using heuristics from scoring.py."""
        return score_elements(
            els,
            step,
            mode,
            search_texts,
            target_field,
            is_blind,
            learned_elements=self.learned_elements if self._semantic_cache_enabled else {},
            last_xpath=self.last_xpath,
            explain=self.explain_mode,
            contextual_hint=contextual_hint,
            anchor_rect=anchor_rect,
            container_elements=container_elements,
            viewport_height=viewport_height,
            early_exit_score=None,
        )

    # ── Element resolution ────────────────────

    @staticmethod
    async def _scroll_and_wait(page) -> None:
        """Scroll down by 500px and wait for new elements to appear."""
        await page.evaluate("window.scrollBy(0, 500)")
        await asyncio.sleep(1)

    async def _resolve_element(
        self,
        page,
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        strategic_context: str,
        failed_ids: "set | None" = None,
        contextual_hint: "ContextualHint | None" = None,
        anchor_rect: "dict | None" = None,
        container_elements: "list[dict] | None" = None,
        viewport_height: int = 0,
    ) -> dict | None:
        """
        Locate the target element with up to 5 scroll-and-retry attempts.
        Uses heuristics first; falls back to LLM only when genuinely ambiguous.
        Returns None if nothing suitable is found.
        """
        _skip = failed_ids or set()
        is_blind = not search_texts and not target_field

        els = []
        for attempt in range(5):
            raw_els = await self._snapshot(page, mode, [t.lower() for t in search_texts])
            els = [e for e in raw_els if (e.get("frame_index", 0), e["id"]) not in _skip]

            if not els:
                if attempt < 4:
                    await self._scroll_and_wait(page)
                continue

            if mode == "drag":
                break

            if contextual_hint is not None and contextual_hint.kind == "inside" and container_elements is not None:
                allowed_ids = {(e.get("frame_index", 0), e["id"]) for e in container_elements}
                els = [e for e in els if (e.get("frame_index", 0), e["id"]) in allowed_ids]
                if not els:
                    if attempt < 4:
                        await self._scroll_and_wait(page)
                    continue

            # Quick exact-match pass
            exact = []
            for el in els:
                name = el["name"].lower().strip()
                aria = el.get("aria_label", "").lower().strip()
                dqa = el.get("data_qa", "").lower().strip()
                if target_field and target_field in name:
                    exact.append(el)
                    continue
                for q in search_texts:
                    q_l = q.lower().strip()
                    if (len(q_l) <= 2 and q_l == name) or (len(q_l) > 2 and q_l in name):
                        exact.append(el)
                        break
                    if len(q_l) > 2 and (q_l in aria or q_l.replace(" ", "-") in dqa or q_l.replace(" ", "_") in dqa):
                        exact.append(el)
                        break

            if exact:
                els = exact
                break

            if els and (is_blind or not search_texts):
                break

            if attempt < 4:
                await self._scroll_and_wait(page)

        if not els:
            return None

        scored = self._score_elements(
            els,
            step,
            mode,
            search_texts,
            target_field,
            is_blind,
            contextual_hint=contextual_hint,
            anchor_rect=anchor_rect,
            container_elements=container_elements,
            viewport_height=viewport_height,
        )
        top = scored[:8]
        best_score = top[0].get("score", 0)

        # Store scoring data for on-demand explain during debug pauses.
        self._last_explain_data = (step, list(search_texts), list(top[:3]))

        # ── Explain mode: print per-element score breakdown ──────────────
        if self.explain_mode and top:
            self._print_explain(step, search_texts, top[:3])

        _conf = _confidence(best_score)

        # ── Deterministic resolution (no LLM in the loop) ────────────────
        # Resolution is purely heuristic: the highest-confidence gate that
        # matches wins; otherwise the top-ranked candidate is used.
        if _conf >= THRESHOLD_SEMANTIC_CACHE:
            print(f"    🧠 SEMANTIC CACHE: Reusing learned element (confidence {_conf:.3f})")
            return top[0]

        if _conf >= THRESHOLD_CONTEXT_REUSE:
            label = "High confidence" if _conf >= THRESHOLD_HIGH_CONFIDENCE else "Context reuse"
            print(f"    ⚙️  DOM HEURISTICS: {label} match (confidence {_conf:.3f})")
            return top[0]

        print(f"    ⚙️  DOM HEURISTICS: best candidate (confidence {_conf:.3f})")
        return top[0]

    # ── Mission runner ────────────────────────

    async def _auto_annotate_navigate(self, page, hunt_file: str, step_file_lines: list[int], step_idx: int) -> None:
        """Insert or overwrite a '# 📍 Auto-Nav:' comment above the NAVIGATE step.

        Reads the hunt file, looks at the line immediately above the NAVIGATE step:
        - If it already contains a '# 📍 Auto-Nav:' comment, replaces it in-situ.
        - Otherwise inserts a new line and increments _annotate_line_offset so that
          subsequent NAVIGATE steps in the same file compute correct positions.
        """
        try:
            url = page.url
            page_name = prompts.lookup_page_name(url)

            # Use the mapped name when available; fall back to the full URL
            # when lookup returned an auto-generated placeholder.
            display = url if page_name.startswith("Auto:") else page_name
            comment_line = f"# 📍 Auto-Nav: {display}\n"

            if step_idx - 1 >= len(step_file_lines):
                return

            # Original 1-based file line of this step, corrected for any lines
            # we have already inserted earlier in this same run.
            nav_line_no = step_file_lines[step_idx - 1] + self._annotate_line_offset

            try:
                with open(hunt_file, encoding="utf-8") as _hf:
                    lines = _hf.readlines()

                above_idx = nav_line_no - 2  # 0-based index of the line above the step

                if 0 <= above_idx < len(lines) and lines[above_idx].strip().startswith("# 📍 Auto-Nav:"):
                    lines[above_idx] = comment_line
                else:
                    lines.insert(nav_line_no - 1, comment_line)
                    self._annotate_line_offset += 1

                with open(hunt_file, "w", encoding="utf-8") as _hf:
                    _hf.writelines(lines)
                print(f"    📍 Auto-Nav: {display}")

            except Exception as _io_exc:
                print(f"    ⚠️  Auto-Nav: file I/O error: {_io_exc}")

        except Exception as _ann_exc:
            print(f"    ⚠️  Auto-Nav: {_ann_exc}")

    async def _launch_browser(self, p, hunt_file: str | None = None):
        """Launch Chrome via the native CDP backend and return ``(browser, page, page)``.

        Handles Electron CDP connections, sandbox flags, ``channel`` and
        ``executable_path`` options.  On Electron failure a ``MissionResult``
        with status ``"fail"`` is returned as the first tuple element instead.
        The ``p`` parameter is unused (kept for call-site compatibility).
        """
        # --cdp / MANUL_CDP_ENDPOINT: attach to a running browser instead of
        # launching one. Generalises the Electron path to any CDP endpoint.
        if self._cdp_endpoint:
            try:
                browser = await CDPBrowser.connect_over_cdp(self._cdp_endpoint)
                page = await browser.first_page()
            except Exception as _cdp_exc:
                print(
                    f"    ❌ Failed to attach over CDP at {self._cdp_endpoint}: {_cdp_exc}\n"
                    f"    💡 Start the browser with --remote-debugging-port and pass --cdp <url>."
                )
                _fail = MissionResult(
                    file=hunt_file or "", name=Path(hunt_file).name if hunt_file else "", status="fail"
                )
                return _fail, None, None
            return browser, browser, page

        if self.browser == "electron":
            _cdp_port = _environ.get("MANUL_CDP_PORT", "9222")
            _cdp_url = f"http://localhost:{_cdp_port}"
            try:
                browser = await CDPBrowser.connect_over_cdp(_cdp_url)
                page = await browser.first_page()
            except Exception as _cdp_exc:
                print(
                    f"    ❌ Failed to connect to Electron via CDP at {_cdp_url}: {_cdp_exc}\n"
                    f"    💡 Ensure the Electron app is running with "
                    f"--remote-debugging-port={_cdp_port}"
                )
                _fail = MissionResult(
                    file=hunt_file or "", name=Path(hunt_file).name if hunt_file else "", status="fail"
                )
                return _fail, None, None
            return browser, browser, page

        if self.channel and self.browser != "chromium":
            raise ConfigurationError(
                f"'channel' is only supported for Chromium; got browser={self.browser!r}, channel={self.channel!r}"
            )
        _extra_args: list[str] = ["--start-maximized"] if self.browser == "chromium" else []
        _is_root = hasattr(os, "getuid") and os.getuid() == 0
        if self.browser == "chromium" and (_is_root or os.path.exists("/.dockerenv")):
            _extra_args.insert(0, "--no-sandbox")
        _extra_args = _extra_args + [a for a in self.browser_args if a not in _extra_args]
        browser = await CDPBrowser.launch(
            headless=self.headless,
            channel=self.channel,
            executable_path=self.executable_path,
            extra_args=_extra_args,
        )
        page = await browser.new_page()
        return browser, browser, page

    async def _parse_task(self, task: str) -> str:
        """Detect task format and produce executable step text.

        Handles STEP-grouped, numbered, and unnumbered action-line formats.
        Free-text natural-language tasks are not decomposed — ManulEngine is
        deterministic and has no planner; author explicit `.hunt` steps (or
        let an external LLM generate them).
        """
        _has_step_markers = bool(re.search(r"^\s*STEP\s*\d*\s*:", task, re.MULTILINE | re.IGNORECASE))
        _is_numbered = bool(re.match(r"^\s*\d+\.", task))
        _has_action_keywords = bool(RE_SYSTEM_STEP.search(task))
        if _has_step_markers or (_has_action_keywords and not _is_numbered):
            return task
        if _is_numbered:
            return "\n".join(s.strip() for s in re.split(r"(?=\b\d+\.\s)", task) if s.strip())
        print(
            "    ❌ No recognizable steps. ManulEngine has no free-text planner — "
            "provide STEP blocks, a numbered list, or unnumbered action lines."
        )
        return ""

    async def _evaluate_conditional(
        self,
        if_block: "IfBlock",
        page: "Page",
    ) -> "tuple[list, list[int]]":
        """Evaluate an if/elif/else block and return the taken branch's data.

        Evaluates conditions in order; returns ``(actions, action_lines)`` of
        the first branch whose condition is ``True``.  If no branch matches
        and there is no ``else``, returns ``([], [])``.
        """
        from .conditionals import evaluate_condition

        for branch in if_block.branches:
            if branch.kind == "else":
                print("    🔀 [CONDITIONAL] Taking 'else' branch (no prior condition matched)")
                return branch.actions, branch.action_lines

            try:
                result = await evaluate_condition(branch.condition, page, self.memory)
            except ValueError as exc:
                from .exceptions import ConditionalSyntaxError

                raise ConditionalSyntaxError(f"Invalid condition '{branch.condition}': {exc}") from exc

            if result:
                print(f"    🔀 [CONDITIONAL] '{branch.kind} {branch.condition}' → True — executing branch")
                return branch.actions, branch.action_lines
            else:
                print(f"    🔀 [CONDITIONAL] '{branch.kind} {branch.condition}' → False — skipping")

        print("    🔀 [CONDITIONAL] No branch taken (all conditions False, no else)")
        return [], []

    async def _execute_conditional(
        self,
        if_block: "IfBlock",
        page: "Page",
        ctx: "BrowserContext",
        strategic_context: str,
        action_index: int,
        hunt_dir: "str | None",
        hunt_file: "str | None",
        _action_file_lines: list,
        block: "object",
        block_steps: list,
        _step_results: list,
        _soft_errors: list,
        _screenshot_mode: str,
    ) -> "tuple[bool, Page, bool, int]":
        """Evaluate a conditional block and execute the taken branch's actions.

        Handles arbitrarily nested IfBlocks via recursion.
        Returns ``(ok, page, done, action_index)`` — ``page`` may differ from
        the input if ``OPEN APP`` reassigned it, ``done`` is ``True`` if a
        ``DONE.`` step was encountered inside the branch, and
        ``action_index`` reflects incrementing per executed branch action.
        """
        branch_actions, branch_lines = await self._evaluate_conditional(if_block, page)
        done = False
        for ba_idx, ba in enumerate(branch_actions):
            ba_line = branch_lines[ba_idx] if ba_idx < len(branch_lines) else 0
            if isinstance(ba, IfBlock):
                ok, page, done, action_index = await self._execute_conditional(
                    ba,
                    page,
                    ctx,
                    strategic_context,
                    action_index,
                    hunt_dir,
                    hunt_file,
                    _action_file_lines,
                    block,
                    block_steps,
                    _step_results,
                    _soft_errors,
                    _screenshot_mode,
                )
                if not ok or done:
                    return ok, page, done, action_index
            elif isinstance(ba, LoopBlock):
                ok, page, done, action_index = await self._execute_loop(
                    ba,
                    page,
                    ctx,
                    strategic_context,
                    action_index,
                    hunt_dir,
                    hunt_file,
                    _action_file_lines,
                    block,
                    block_steps,
                    _step_results,
                    _soft_errors,
                    _screenshot_mode,
                )
                if not ok or done:
                    return ok, page, done, action_index
            elif isinstance(ba, str):
                action_index += 1
                # File-line breakpoint check for conditional body actions.
                _temp_break_added = False
                if self._break_file_lines and ba_line and ba_line in self._break_file_lines:
                    step_kind = classify_step(ba)
                    if step_kind != "action" and not sys.stdin.isatty():
                        print(f"    🔴 BREAKPOINT at line {ba_line}")
                        await self._debug_prompt(page, ba, action_index)
                    elif step_kind != "action":
                        print(f"    🔴 BREAKPOINT at line {ba_line} — pausing (live Chrome stays interactive)…")
                        await page.pause()
                    else:
                        # Action step (click/fill/etc.) — inject into break_steps
                        # so the debug pause inside _execute_step() fires.
                        if self.break_steps is None:
                            self.break_steps = set()
                        if action_index not in self.break_steps:
                            self.break_steps.add(action_index)
                            _temp_break_added = True

                ba = substitute_memory(ba, self.memory)
                try:
                    outcome = await self._dispatch_step(
                        ba,
                        page,
                        ctx,
                        strategic_context,
                        action_index,
                        hunt_dir,
                        hunt_file,
                        _action_file_lines,
                        block,
                        block_steps,
                        _step_results,
                        _soft_errors,
                        _screenshot_mode,
                        raw_step=ba,
                    )
                    page = outcome[1]
                    if outcome[3]:  # done
                        return outcome[0], page, True, action_index
                    if not outcome[0]:
                        return False, page, False, action_index
                finally:
                    if _temp_break_added:
                        self.break_steps.discard(action_index)
        return True, page, done, action_index

    async def _execute_loop(
        self,
        loop_block: "LoopBlock",
        page: "Page",
        ctx: "BrowserContext",
        strategic_context: str,
        action_index: int,
        hunt_dir: "str | None",
        hunt_file: "str | None",
        _action_file_lines: list,
        block: "object",
        block_steps: list,
        _step_results: list,
        _soft_errors: list,
        _screenshot_mode: str,
    ) -> "tuple[bool, Page, bool, int, str | None]":
        """Execute a loop block (REPEAT / FOR EACH / WHILE).

        Returns ``(ok, page, done, action_index, error_msg)`` — same contract as
        ``_execute_conditional`` but with a 5th element carrying the failure
        reason when ``ok`` is ``False``.
        """
        done = False

        if loop_block.kind == "repeat":
            count = loop_block.count or 0
            print(f"    🔁 [LOOP] REPEAT {count} TIMES")
            for iteration in range(1, count + 1):
                self.memory[str(loop_block.var_name or "i")] = str(iteration)
                ok, page, done, action_index = await self._run_loop_body(
                    loop_block,
                    page,
                    ctx,
                    strategic_context,
                    action_index,
                    hunt_dir,
                    hunt_file,
                    _action_file_lines,
                    block,
                    block_steps,
                    _step_results,
                    _soft_errors,
                    _screenshot_mode,
                    iteration=iteration,
                    total=count,
                )
                if not ok or done:
                    return ok, page, done, action_index, None
            return True, page, done, action_index, None

        elif loop_block.kind == "for_each":
            var_name = loop_block.var_name or "item"
            collection_key = loop_block.collection_expr or ""
            raw_collection = self.memory.resolve(collection_key)
            if raw_collection is None:
                if collection_key:
                    msg = (
                        f"FOR EACH loop references undefined collection variable "
                        f"{{{collection_key}}} — "
                        f"populate it before this step with @var: {{{collection_key}}} = ..., "
                        f"SET {{{collection_key}}} = ..., "
                        f"EXTRACT ... into {{{collection_key}}}, or "
                        f"CALL PYTHON ... into {{{collection_key}}}"
                    )
                    print(f"    ❌  [LOOP] {msg}")
                    step_result = StepResult(
                        index=action_index + 1,
                        text=f"FOR EACH {{{var_name}}} IN {{{collection_key}}}",
                        status="fail",
                        error=msg,
                        duration_ms=0,
                        logical_step=getattr(block, "block_name", None),
                    )
                    _step_results.append(step_result)
                    block_steps.append(step_result)
                    return False, page, done, action_index, msg
                raw_collection = ""
            items = [item.strip() for item in str(raw_collection).split(",") if item.strip()]
            print(f"    🔁 [LOOP] FOR EACH {{{var_name}}} IN {{{collection_key}}} ({len(items)} items)")
            for iteration, item in enumerate(items, 1):
                self.memory[var_name] = item
                self.memory["i"] = str(iteration)
                ok, page, done, action_index = await self._run_loop_body(
                    loop_block,
                    page,
                    ctx,
                    strategic_context,
                    action_index,
                    hunt_dir,
                    hunt_file,
                    _action_file_lines,
                    block,
                    block_steps,
                    _step_results,
                    _soft_errors,
                    _screenshot_mode,
                    iteration=iteration,
                    total=len(items),
                )
                if not ok or done:
                    return ok, page, done, action_index, None
            return True, page, done, action_index, None

        elif loop_block.kind == "while":
            from .conditionals import evaluate_condition

            condition_text = loop_block.condition_text or ""
            print(f"    🔁 [LOOP] WHILE {condition_text}")
            iteration = 0
            while iteration < MAX_LOOP_ITERATIONS:
                try:
                    result = await evaluate_condition(condition_text, page, self.memory)
                except ValueError as exc:
                    from .exceptions import ConditionalSyntaxError

                    raise ConditionalSyntaxError(f"Invalid WHILE condition '{condition_text}': {exc}") from exc
                if not result:
                    print(f"    🔁 [LOOP] WHILE condition False after {iteration} iteration(s) — exiting")
                    break
                iteration += 1
                self.memory["i"] = str(iteration)
                ok, page, done, action_index = await self._run_loop_body(
                    loop_block,
                    page,
                    ctx,
                    strategic_context,
                    action_index,
                    hunt_dir,
                    hunt_file,
                    _action_file_lines,
                    block,
                    block_steps,
                    _step_results,
                    _soft_errors,
                    _screenshot_mode,
                    iteration=iteration,
                    total=None,
                )
                if not ok or done:
                    return ok, page, done, action_index, None
            else:
                msg = (
                    f"WHILE loop exceeded safety limit of {MAX_LOOP_ITERATIONS} iterations "
                    f"(condition: {condition_text!r})"
                )
                print(f"    ⚠️  [LOOP] {msg}")
                step_result = StepResult(
                    index=action_index + 1,
                    text=f"WHILE {condition_text}",
                    status="fail",
                    error=msg,
                    duration_ms=0,
                    logical_step=getattr(block, "block_name", None),
                )
                _step_results.append(step_result)
                block_steps.append(step_result)
                return False, page, done, action_index, msg
            return True, page, done, action_index, None

        return True, page, done, action_index, None

    async def _run_loop_body(
        self,
        loop_block: "LoopBlock",
        page: "Page",
        ctx: "BrowserContext",
        strategic_context: str,
        action_index: int,
        hunt_dir: "str | None",
        hunt_file: "str | None",
        _action_file_lines: list,
        block: "object",
        block_steps: list,
        _step_results: list,
        _soft_errors: list,
        _screenshot_mode: str,
        iteration: int = 1,
        total: "int | None" = None,
    ) -> "tuple[bool, Page, bool, int]":
        """Execute a single iteration of a loop body.

        Delegates each action to ``_dispatch_step`` or recurses into
        ``_execute_conditional`` / ``_execute_loop`` for nested blocks.
        """
        total_str = f"/{total}" if total else ""
        print(f"    🔁 [LOOP] iteration {iteration}{total_str}")
        done = False
        for ba_idx, ba in enumerate(loop_block.actions):
            ba_line = loop_block.action_lines[ba_idx] if ba_idx < len(loop_block.action_lines) else 0
            if isinstance(ba, IfBlock):
                ok, page, done, action_index = await self._execute_conditional(
                    ba,
                    page,
                    ctx,
                    strategic_context,
                    action_index,
                    hunt_dir,
                    hunt_file,
                    _action_file_lines,
                    block,
                    block_steps,
                    _step_results,
                    _soft_errors,
                    _screenshot_mode,
                )
                if not ok or done:
                    return ok, page, done, action_index
            elif isinstance(ba, LoopBlock):
                ok, page, done, action_index = await self._execute_loop(
                    ba,
                    page,
                    ctx,
                    strategic_context,
                    action_index,
                    hunt_dir,
                    hunt_file,
                    _action_file_lines,
                    block,
                    block_steps,
                    _step_results,
                    _soft_errors,
                    _screenshot_mode,
                )
                if not ok or done:
                    return ok, page, done, action_index
            elif isinstance(ba, str):
                action_index += 1
                # File-line breakpoint check for loop body actions.
                _temp_break_added = False
                if self._break_file_lines and ba_line and ba_line in self._break_file_lines:
                    step_kind = classify_step(ba)
                    if step_kind != "action" and not sys.stdin.isatty():
                        print(f"    🔴 BREAKPOINT at line {ba_line}")
                        await self._debug_prompt(page, ba, action_index)
                    elif step_kind != "action":
                        print(f"    🔴 BREAKPOINT at line {ba_line} — pausing (live Chrome stays interactive)…")
                        await page.pause()
                    else:
                        if self.break_steps is None:
                            self.break_steps = set()
                        if action_index not in self.break_steps:
                            self.break_steps.add(action_index)
                            _temp_break_added = True

                ba = substitute_memory(ba, self.memory)
                try:
                    outcome = await self._dispatch_step(
                        ba,
                        page,
                        ctx,
                        strategic_context,
                        action_index,
                        hunt_dir,
                        hunt_file,
                        _action_file_lines,
                        block,
                        block_steps,
                        _step_results,
                        _soft_errors,
                        _screenshot_mode,
                        raw_step=ba,
                    )
                    page = outcome[1]
                    if outcome[3]:  # done
                        return outcome[0], page, True, action_index
                    if not outcome[0]:
                        return False, page, False, action_index
                finally:
                    if _temp_break_added:
                        self.break_steps.discard(action_index)
        return True, page, done, action_index

    async def _dispatch_step(
        self,
        step: str,
        page: "Page",
        ctx: "BrowserContext",
        strategic_context: str,
        action_index: int,
        hunt_dir: "str | None",
        hunt_file: "str | None",
        _action_file_lines: list,
        block: "object",
        block_steps: list,
        _step_results: list,
        _soft_errors: list,
        _screenshot_mode: str,
        raw_step: str = "",
    ) -> "tuple[bool, Page, str | None, bool]":
        """Execute a single DSL step inside a conditional branch.

        Full-featured dispatcher that mirrors the main ``run_mission`` loop:
        all step kinds, custom-control interception, screenshot capture,
        proper DEBUG/PAUSE and DONE semantics.

        Returns ``(ok, page, error, done)`` where *page* may be reassigned
        by ``OPEN APP`` and *done* signals mission termination.
        """
        step_kind = classify_step(step)
        started_perf = time.perf_counter()
        _step_ok = True
        _step_error: str | None = None
        _done = False

        print(f"    [▶️ ACTION START] {step}")

        try:
            if step_kind == "navigate":
                if not await self._handle_navigate(page, step):
                    _step_error = "Navigation failed"
                    _step_ok = False

            elif step_kind == "open_app":
                _app_ok, page = await self._handle_open_app(page, ctx)
                if not _app_ok:
                    _step_error = "OPEN APP failed"
                    _step_ok = False

            elif step_kind == "mock":
                if not await self._handle_mock(page, step, hunt_dir=hunt_dir):
                    _step_error = "MOCK command failed"
                    _step_ok = False

            elif step_kind == "wait_for_selector":
                _wait_ok, _wait_msg = await self._handle_wait_for_selector(page, step)
                if not _wait_ok:
                    _step_error = _wait_msg
                    _step_ok = False

            elif step_kind == "wait_for_response":
                if not await self._handle_wait_for_response(page, step):
                    _step_error = "WAIT FOR RESPONSE timed out"
                    _step_ok = False

            elif step_kind == "wait_for_element":
                _wait_ok, _wait_msg = await self._handle_wait_for_element(page, step)
                if not _wait_ok:
                    _step_error = _wait_msg
                    _step_ok = False

            elif step_kind == "wait":
                n = re.search(r"(\d+)", step)
                await asyncio.sleep(int(n.group(1)) if n else 2)

            elif step_kind == "scroll":
                await self._handle_scroll(page, step)

            elif step_kind == "extract":
                if not await self._handle_extract(page, step):
                    _step_error = "Extract failed"
                    _step_ok = False

            elif step_kind == "verify":
                if not await self._handle_verify(page, step, step_idx=action_index):
                    _step_error = "Verification failed"
                    _step_ok = False

            elif step_kind == "verify_visual":
                if not await self._handle_verify_visual(
                    page, step, strategic_context, step_idx=action_index, hunt_dir=hunt_dir
                ):
                    _step_error = "Visual regression check failed"
                    _step_ok = False

            elif step_kind == "verify_softly":
                _soft_ok = await self._handle_verify_softly(page, step, step_idx=action_index)
                if not _soft_ok:
                    _soft_msg = f"Soft assertion failed: {step}"
                    _soft_errors.append(_soft_msg)
                    _step_error = _soft_msg
                    _step_ok = False

            elif step_kind == "press_enter":
                await self._handle_press_enter(page)

            elif step_kind == "press":
                if not await self._handle_press(page, step, strategic_context, step_idx=action_index):
                    _step_error = "PRESS command failed"
                    _step_ok = False

            elif step_kind == "right_click":
                if not await self._handle_right_click(page, step, strategic_context, step_idx=action_index):
                    _step_error = "RIGHT CLICK command failed"
                    _step_ok = False

            elif step_kind == "upload":
                if not await self._handle_upload(
                    page, step, strategic_context, step_idx=action_index, hunt_dir=hunt_dir
                ):
                    _step_error = "UPLOAD command failed"
                    _step_ok = False

            elif step_kind == "full_scan":
                if not await self._handle_full_scan(page):
                    _step_error = "FULL SCAN failed"
                    _step_ok = False

            elif step_kind == "scan_page":
                if not await self._handle_scan_page(page, step):
                    _step_error = "SCAN PAGE failed"
                    _step_ok = False

            elif step_kind == "set_var":
                _set_m = re.match(
                    r"(?:\d+\.\s*)?SET\s+\{?(\w+)\}?\s*=\s*(.+)",
                    raw_step or step,
                    re.IGNORECASE,
                )
                if _set_m:
                    _sv_name = _set_m.group(1)
                    _sv_raw = _set_m.group(2).strip()
                    if len(_sv_raw) >= 2 and _sv_raw[0] in ("'", '"') and _sv_raw[-1] == _sv_raw[0]:
                        _sv_raw = _sv_raw[1:-1]
                    self.memory[_sv_name] = _sv_raw
                    print(f"      📝 SET {{{_sv_name}}} = {_sv_raw}")
                else:
                    _step_error = f"Malformed SET command: {step}"
                    _step_ok = False

            elif step_kind == "debug_vars":
                print("      📋 DEBUG VARS — current variable state:")
                print(self.memory.dump())

            elif step_kind == "print":
                print(f"      📢 PRINT: {extract_print_message(step)}")

            elif step_kind == "debug":
                if not sys.stdin.isatty():
                    print("      🔎 DEBUG/PAUSE step (conditional branch)")
                    await self._debug_prompt(page, step, action_index)
                else:
                    print("      🔎 DEBUG/PAUSE step — pausing (live Chrome stays interactive)…")
                    await page.pause()

            elif step_kind == "done":
                print("      🏁 MISSION ACCOMPLISHED")
                _done = True

            elif step_kind == "use_import":
                raise RuntimeError(
                    f"Unresolved USE directive at runtime: {step!r}. "
                    f"USE blocks must be expanded at parse time via @import: headers."
                )

            elif step_kind == "call_python":
                instruction = re.sub(r"^\s*\d+\.\s*", "", step).strip()
                if re.match(r"CALL\s+PYTHON\b", instruction.upper()):
                    result = execute_hook_line(
                        re.sub(r"^\s*\d+\.\s*", "", raw_step or step).strip(),
                        hunt_dir=hunt_dir,
                        variables=self.memory,
                    )
                    print(f"       {result.message}")
                    if not result.success:
                        _step_error = result.message
                        _step_ok = False
                    else:
                        bind_hook_result(result, self.memory)
                elif not await self._execute_step(page, step, strategic_context, step_idx=action_index):
                    _step_error = "Action failed"
                    _step_ok = False

            else:
                # DOM action (click, fill, select, etc.) — with custom-control interception.
                _cc_mode = detect_mode(step)
                _cc_quoted = extract_quoted(step, preserve_case=True)
                if _cc_mode == "input" and len(_cc_quoted) >= 2:
                    _cc_target, _cc_value = _cc_quoted[0], _cc_quoted[-1]
                elif _cc_mode == "select" and len(_cc_quoted) >= 2:
                    _cc_target, _cc_value = _cc_quoted[-1], _cc_quoted[0]
                elif _cc_mode == "drag" and len(_cc_quoted) >= 2:
                    _cc_target, _cc_value = _cc_quoted[0], _cc_quoted[-1]
                elif _cc_quoted:
                    _cc_target, _cc_value = _cc_quoted[0], None
                else:
                    _cc_target, _cc_value = "", None
                _cc_handler = None
                _cc_page = ""
                if _cc_target:
                    _cc_page = prompts.lookup_page_name(page.url)
                    _cc_handler = get_custom_control(_cc_page, _cc_target)
                if _cc_handler is not None:
                    print(
                        f"      🎛️  [CUSTOM CONTROL] '{_cc_target}' on '{_cc_page}' ({_cc_mode}) "
                        f"→ {getattr(_cc_handler, '__qualname__', _cc_handler.__name__)}"
                    )
                    try:
                        _cc_ctx = ControlContext(
                            page=page,
                            action=_cc_mode,
                            value=_cc_value,
                            target=_cc_target,
                            page_name=_cc_page,
                            url=page.url,
                            step=step,
                        )
                        _cc_result = _cc_handler(_cc_ctx)
                        if inspect.isawaitable(_cc_result):
                            await _cc_result
                    except Exception as exc:
                        _step_error = f"Custom control error on '{_cc_target}': {exc}"
                        _log.warning("Custom control '%s' failed: %s", _cc_target, exc)
                        _step_ok = False
                else:
                    if _cc_target:
                        _miss = diagnose_custom_control_miss(_cc_page, _cc_target)
                        if _miss:
                            print(f"      {_miss}")
                    if not await self._execute_step(page, step, strategic_context, step_idx=action_index):
                        _step_error = "Action failed"
                        _step_ok = False
        except Exception as exc:
            _step_ok = False
            _step_error = str(exc)
            _log.debug("Conditional step execution failed: %s", exc)

        duration_s = time.perf_counter() - started_perf

        # ── Screenshot capture (aligned with main loop) ──
        _ss_b64: str | None = None
        if _screenshot_mode == "always" or (_screenshot_mode == "on-fail" and not _step_ok):
            try:
                _ss_bytes = await page.screenshot(type="png")
                _ss_b64 = base64.b64encode(_ss_bytes).decode("ascii")
            except Exception as exc:
                _log.debug("Screenshot capture failed: %s", exc)

        if _step_ok:
            _sr_status = "pass"
            print(f"    [✅ ACTION PASS] duration: {duration_s:.2f}s")
        elif step_kind == "verify_softly":
            _sr_status = "warning"
            print(f"    [⚠️ ACTION WARN] {_step_error}")
        else:
            _sr_status = "fail"
            print(f"    [❌ ACTION FAIL] {_step_error}")

        _step_result = StepResult(
            index=action_index,
            text=re.sub(r"^\s*\d+\.\s*", "", step),
            status=_sr_status,
            duration_ms=duration_s * 1000,
            error=_step_error,
            screenshot=_ss_b64,
            logical_step=getattr(block, "block_name", ""),
        )
        _step_results.append(_step_result)
        block_steps.append(_step_result)

        return _step_ok, page, _step_error, _done

    async def run_mission(
        self,
        task: str,
        strategic_context: str = "",
        hunt_dir: str | None = None,
        hunt_file: str | None = None,
        step_file_lines: "list[int] | None" = None,
        initial_vars: "dict | None" = None,
        global_vars: "dict | None" = None,
        row_vars: "dict | None" = None,
        import_vars: "dict | None" = None,
        screenshot_mode: str = "none",
    ) -> MissionResult:
        """
        Execute a full browser automation mission.

        The task can be either a numbered step list ("1. Navigate to ... 2. Click ...")
        or a free-text description that will be decomposed by the LLM planner.

        Returns a :class:`MissionResult` (truthy when status != "fail").
        """
        print(f"\n🐾 ManulEngine — deterministic heuristics  |  browser: {self.browser}")

        # ── Ensure @custom_control handlers required for this mission are loaded ──
        load_custom_controls(
            str(Path.cwd()),
            required_modules=self._required_controls,
            custom_modules_dirs=self._custom_controls_dirs,
        )

        async with _AsyncNull() as p:
            browser, ctx, page = await self._launch_browser(p, hunt_file)
            # Electron CDP failure returns (MissionResult, None, None).
            if ctx is None or page is None:
                return browser  # it's actually the MissionResult

            try:
                parsed_task = await self._parse_task(task)

                blocks = parse_hunt_blocks(parsed_task, step_file_lines)
                if not blocks:
                    return MissionResult(
                        file=hunt_file or "", name=Path(hunt_file).name if hunt_file else "", status="fail"
                    )

                ok = True
                done = False
                _step_results: list[StepResult] = []
                _block_results: list[BlockResult] = []
                _soft_errors: list[str] = []
                _screenshot_mode = screenshot_mode
                _action_file_lines = [line for block in blocks for line in block.action_lines]
                # Clear per-mission scopes to avoid stale values leaking between
                # runs of the same ManulEngine instance.
                self.memory.clear_level(ScopedVariables.LEVEL_ROW)
                self.memory.clear_level(ScopedVariables.LEVEL_MISSION)
                self.memory.clear_level(ScopedVariables.LEVEL_IMPORT)
                # Pre-populate scoped variable levels.
                # Level 5 (lowest): Import vars from @import file @var: declarations.
                if import_vars:
                    self.memory.set_many(import_vars, ScopedVariables.LEVEL_IMPORT)
                # Level 4: Global vars from CLI / lifecycle hooks.
                if global_vars:
                    self.memory.set_many(global_vars, ScopedVariables.LEVEL_GLOBAL)
                # Level 3: Mission vars declared via @var: in the hunt file header.
                if initial_vars:
                    self.memory.set_many(initial_vars, ScopedVariables.LEVEL_MISSION)
                # Level 1 (highest): Row vars from @data iteration.
                if row_vars:
                    self.memory.set_many(row_vars, ScopedVariables.LEVEL_ROW)
                # Cache lookup_page_name() results within this mission.
                # The cache is invalidated when any pages/*.json fragment is modified
                # so live edits made during a long run are still reflected within one step.
                _cc_page_cache: dict[str, str] = {}
                _cc_pages_mtime: float = 0.0
                action_index = 0
                for block in blocks:
                    block_started_perf = time.perf_counter()
                    block_steps: list[StepResult] = []
                    block_status = "pass"
                    block_error: str | None = None

                    print(f"\n[📦 BLOCK START] {block.block_name}")

                    for _ba_idx, raw_step in enumerate(block.actions):
                        # ── Conditional block (IfBlock) ──
                        if isinstance(raw_step, IfBlock):
                            started_perf = time.perf_counter()
                            print("  [▶️ ACTION START] if/elif/else conditional")
                            _cond_ok = True
                            _cond_error: str | None = None
                            try:
                                _cond_ok, page, _cond_done, action_index = await self._execute_conditional(
                                    raw_step,
                                    page,
                                    ctx,
                                    strategic_context,
                                    action_index,
                                    hunt_dir,
                                    hunt_file,
                                    _action_file_lines,
                                    block,
                                    block_steps,
                                    _step_results,
                                    _soft_errors,
                                    _screenshot_mode,
                                )
                                if _cond_done:
                                    done = True
                                if not _cond_ok:
                                    _cond_error = "Conditional action failed"
                            except Exception as exc:
                                _cond_ok = False
                                _cond_error = str(exc)
                                _log.debug("Conditional block failed: %s", exc)
                            duration_s = time.perf_counter() - started_perf
                            if _cond_ok:
                                print(f"  [✅ ACTION PASS] conditional block (duration: {duration_s:.2f}s)")
                            else:
                                ok = False
                                block_status = "fail"
                                block_error = _cond_error
                                print(f"  [❌ ACTION FAIL] conditional block: {_cond_error}")
                            if block_status == "fail" or done:
                                break
                            continue

                        # ── Loop block (LoopBlock) ──
                        if isinstance(raw_step, LoopBlock):
                            started_perf = time.perf_counter()
                            _loop_kind_label = raw_step.kind.upper().replace("_", " ")
                            print(f"  [▶️ ACTION START] {_loop_kind_label} loop")
                            _loop_ok = True
                            _loop_error: str | None = None
                            try:
                                _loop_ok, page, _loop_done, action_index, _exec_error = await self._execute_loop(
                                    raw_step,
                                    page,
                                    ctx,
                                    strategic_context,
                                    action_index,
                                    hunt_dir,
                                    hunt_file,
                                    _action_file_lines,
                                    block,
                                    block_steps,
                                    _step_results,
                                    _soft_errors,
                                    _screenshot_mode,
                                )
                                if _loop_done:
                                    done = True
                                if not _loop_ok:
                                    _loop_error = _exec_error or "Loop action failed"
                            except Exception as exc:
                                _loop_ok = False
                                _loop_error = str(exc)
                                _log.debug("Loop block failed: %s", exc)
                            duration_s = time.perf_counter() - started_perf
                            if _loop_ok:
                                print(f"  [✅ ACTION PASS] {_loop_kind_label} loop (duration: {duration_s:.2f}s)")
                            else:
                                ok = False
                                block_status = "fail"
                                block_error = _loop_error
                                print(f"  [❌ ACTION FAIL] {_loop_kind_label} loop: {_loop_error}")
                            if block_status == "fail" or done:
                                break
                            continue

                        action_index += 1
                        # ── File-line breakpoint fallback ──
                        # When the index-based break_steps mapping is stale
                        # (e.g. after a conditional whose branch count differs
                        # from the static estimate), fall back to the file-line
                        # set which always matches.
                        _file_line = block.action_lines[_ba_idx] if _ba_idx < len(block.action_lines) else 0
                        _temp_break_added = False
                        _should_break = (self.break_steps and action_index in self.break_steps) or (
                            self._break_file_lines and _file_line and _file_line in self._break_file_lines
                        )
                        step = substitute_memory(raw_step, self.memory)
                        started_perf = time.perf_counter()
                        step_kind = classify_step(step)
                        _wait_target, _wait_state = (
                            parse_explicit_wait(step) if step_kind == "wait_for_element" else (None, None)
                        )
                        if _wait_target and _wait_state:
                            if _wait_state == "disappear":
                                _action_start_text = f"Wait for '{_wait_target}' to disappear"
                            else:
                                _action_start_text = f"Wait for '{_wait_target}' to be {_wait_state}"
                        else:
                            _action_start_text = step
                        print(f"  [▶️ ACTION START] {_action_start_text}")

                        _is_system_step = step_kind != "action"

                        if self.debug_mode and _is_system_step:
                            await self._debug_prompt(page, step, action_index)
                        elif not self.debug_mode and _should_break and _is_system_step:
                            if not sys.stdin.isatty():
                                print(f"    🔴 BREAKPOINT at action {action_index}")
                                await self._debug_prompt(page, step, action_index)
                            else:
                                print(
                                    f"    🔴 BREAKPOINT at action {action_index} — pausing (live Chrome stays interactive)…"
                                )
                                await page.pause()
                        elif not self.debug_mode and _should_break and not _is_system_step:
                            # Action step (click/fill/etc.) — inject into break_steps
                            # so the debug pause inside _execute_step() fires.
                            if action_index not in self.break_steps:
                                self.break_steps.add(action_index)
                                _temp_break_added = True

                        # What-If REPL: if the debugger chose a step to execute,
                        # replace the current step and re-classify it.
                        # Temporarily suppress debug so the injected step does
                        # not trigger a second pause.
                        _what_if_active = False
                        if self._what_if_execute_step is not None:
                            injected_step = self._what_if_execute_step
                            step = substitute_memory(injected_step, self.memory)
                            step_kind = classify_step(step)
                            self._what_if_execute_step = None
                            _what_if_active = True
                            _saved_debug = self.debug_mode
                            _saved_break = self.break_steps
                            self.debug_mode = False
                            self.break_steps = set()
                            if step != injected_step:
                                print(f"  [🔮 WHAT-IF EXECUTE] {injected_step} -> {step}")
                            else:
                                print(f"  [🔮 WHAT-IF EXECUTE] {step}")

                        _auto_annotate_live = (
                            _environ.get("MANUL_AUTO_ANNOTATE", "").strip().lower() in ("1", "true", "yes")
                        ) or self._auto_annotate
                        try:
                            url_before = page.url
                        except Exception:
                            url_before = ""

                        _step_ok = True
                        _step_error: str | None = None
                        _step_success_message: str | None = None
                        try:
                            if step_kind == "navigate":
                                if not await self._handle_navigate(page, step):
                                    _step_error = "Navigation failed"
                                    _step_ok = False
                                elif _auto_annotate_live and hunt_file and _action_file_lines:
                                    await self._auto_annotate_navigate(
                                        page, hunt_file, _action_file_lines, action_index
                                    )

                            elif step_kind == "open_app":
                                _app_ok, page = await self._handle_open_app(page, ctx)
                                if not _app_ok:
                                    _step_error = "OPEN APP failed"
                                    _step_ok = False

                            elif step_kind == "mock":
                                if not await self._handle_mock(page, step, hunt_dir=hunt_dir):
                                    _step_error = "MOCK command failed"
                                    _step_ok = False

                            elif step_kind == "wait_for_selector":
                                _wait_ok, _wait_msg = await self._handle_wait_for_selector(page, step)
                                if not _wait_ok:
                                    _step_error = _wait_msg
                                    _step_ok = False
                                else:
                                    _step_success_message = _wait_msg

                            elif step_kind == "wait_for_response":
                                if not await self._handle_wait_for_response(page, step):
                                    _step_error = "WAIT FOR RESPONSE timed out"
                                    _step_ok = False

                            elif step_kind == "wait_for_element":
                                _wait_ok, _wait_msg = await self._handle_wait_for_element(page, step)
                                if not _wait_ok:
                                    _step_error = _wait_msg
                                    _step_ok = False
                                else:
                                    _step_success_message = _wait_msg

                            elif step_kind == "wait":
                                n = re.search(r"(\d+)", step)
                                await asyncio.sleep(int(n.group(1)) if n else 2)

                            elif step_kind == "scroll":
                                await self._handle_scroll(page, step)

                            elif step_kind == "extract":
                                if not await self._handle_extract(page, step):
                                    _step_error = "Extract failed"
                                    _step_ok = False

                            elif step_kind == "verify":
                                if not await self._handle_verify(page, step, step_idx=action_index):
                                    _step_error = "Verification failed"
                                    _step_ok = False

                            elif step_kind == "verify_visual":
                                if not await self._handle_verify_visual(
                                    page, step, strategic_context, step_idx=action_index, hunt_dir=hunt_dir
                                ):
                                    _step_error = "Visual regression check failed"
                                    _step_ok = False

                            elif step_kind == "verify_softly":
                                _soft_ok = await self._handle_verify_softly(page, step, step_idx=action_index)
                                if not _soft_ok:
                                    _soft_msg = f"Soft assertion failed at action {action_index}: {step}"
                                    _soft_errors.append(_soft_msg)
                                    _step_error = _soft_msg
                                    _step_ok = False
                                    print("    ⚠️  SOFT ASSERTION FAILED — continuing execution")

                            elif step_kind == "press_enter":
                                await self._handle_press_enter(page)

                            elif step_kind == "press":
                                if not await self._handle_press(page, step, strategic_context, step_idx=action_index):
                                    _step_error = "PRESS command failed"
                                    _step_ok = False

                            elif step_kind == "right_click":
                                if not await self._handle_right_click(
                                    page, step, strategic_context, step_idx=action_index
                                ):
                                    _step_error = "RIGHT CLICK command failed"
                                    _step_ok = False

                            elif step_kind == "upload":
                                if not await self._handle_upload(
                                    page, step, strategic_context, step_idx=action_index, hunt_dir=hunt_dir
                                ):
                                    _step_error = "UPLOAD command failed"
                                    _step_ok = False

                            elif step_kind == "full_scan":
                                if not await self._handle_full_scan(page):
                                    _step_error = "FULL SCAN failed"
                                    _step_ok = False

                            elif step_kind == "scan_page":
                                if not await self._handle_scan_page(page, step):
                                    _step_error = "SCAN PAGE failed"
                                    _step_ok = False

                            elif step_kind == "call_python":
                                instruction = _RE_NUMBERED_PREFIX.sub("", step).strip()
                                if re.match(r"CALL\s+PYTHON\b", instruction.upper()):
                                    raw_instr = _RE_NUMBERED_PREFIX.sub("", raw_step).strip()
                                    result = execute_hook_line(raw_instr, hunt_dir=hunt_dir, variables=self.memory)
                                    print(f"     {result.message}")
                                    if not result.success:
                                        _step_error = result.message
                                        _step_ok = False
                                    else:
                                        bind_hook_result(result, self.memory)
                                elif not await self._execute_step(page, step, strategic_context, step_idx=action_index):
                                    _step_error = "Action failed"
                                    _step_ok = False

                            elif step_kind == "set_var":
                                _set_m = re.match(
                                    r"(?:\d+\.\s*)?SET\s+\{?(\w+)\}?\s*=\s*(.+)",
                                    raw_step,
                                    re.IGNORECASE,
                                )
                                if _set_m:
                                    _sv_name = _set_m.group(1)
                                    _rhs_m = re.match(
                                        r"(?:\d+\.\s*)?SET\s+\S+\s*=\s*(.+)",
                                        step,
                                        re.IGNORECASE,
                                    )
                                    _sv_raw = (_rhs_m.group(1) if _rhs_m else _set_m.group(2)).strip()
                                    if len(_sv_raw) >= 2 and _sv_raw[0] in ("'", '"') and _sv_raw[-1] == _sv_raw[0]:
                                        _sv_raw = _sv_raw[1:-1]
                                    self.memory[_sv_name] = _sv_raw
                                    print(f"    📝 SET {{{_sv_name}}} = {_sv_raw}")
                                else:
                                    _step_error = f"Malformed SET command: {step}"
                                    _step_ok = False

                            elif step_kind == "debug_vars":
                                print("    📋 DEBUG VARS — current variable state:")
                                print(self.memory.dump())

                            elif step_kind == "print":
                                print(f"    📢 PRINT: {extract_print_message(step)}")

                            elif step_kind == "debug":
                                if not self.debug_mode:
                                    if not sys.stdin.isatty():
                                        print("    🔎 DEBUG/PAUSE step")
                                        await self._debug_prompt(page, step, action_index)
                                    else:
                                        print("    🔎 DEBUG/PAUSE step — pausing (live Chrome stays interactive)…")
                                        await page.pause()

                            elif step_kind == "done":
                                print("    🏁 MISSION ACCOMPLISHED")
                                done = True

                            elif step_kind == "use_import":
                                raise RuntimeError(
                                    f"Unresolved USE directive at runtime: {step!r}. "
                                    f"USE blocks must be expanded at parse time via @import: headers."
                                )

                            else:
                                _cc_mode = detect_mode(step)
                                _cc_quoted = extract_quoted(step, preserve_case=True)
                                if _cc_mode == "input" and len(_cc_quoted) >= 2:
                                    _cc_target, _cc_value = _cc_quoted[0], _cc_quoted[-1]
                                elif _cc_mode == "select" and len(_cc_quoted) >= 2:
                                    _cc_target, _cc_value = _cc_quoted[-1], _cc_quoted[0]
                                elif _cc_mode == "drag" and len(_cc_quoted) >= 2:
                                    _cc_target, _cc_value = _cc_quoted[0], _cc_quoted[-1]
                                elif _cc_quoted:
                                    _cc_target, _cc_value = _cc_quoted[0], None
                                else:
                                    _cc_target, _cc_value = "", None
                                _cc_handler = None
                                _cc_page = ""
                                if _cc_target:
                                    _mt = prompts.pages_registry_mtime()
                                    if _mt != _cc_pages_mtime:
                                        _cc_page_cache.clear()
                                        _cc_pages_mtime = _mt
                                    _cc_page = _cc_page_cache.get(page.url) or prompts.lookup_page_name(page.url)
                                    _cc_page_cache[page.url] = _cc_page
                                    _cc_handler = get_custom_control(_cc_page, _cc_target)
                                if _cc_handler is not None:
                                    print(
                                        f"    🎛️  [CUSTOM CONTROL] '{_cc_target}' on '{_cc_page}' ({_cc_mode}) "
                                        f"→ {getattr(_cc_handler, '__qualname__', _cc_handler.__name__)}"
                                    )
                                    try:
                                        _cc_ctx = ControlContext(
                                            page=page,
                                            action=_cc_mode,
                                            value=_cc_value,
                                            target=_cc_target,
                                            page_name=_cc_page,
                                            url=page.url,
                                            step=step,
                                        )
                                        _cc_result = _cc_handler(_cc_ctx)
                                        if inspect.isawaitable(_cc_result):
                                            await _cc_result
                                    except Exception as exc:
                                        _step_error = f"Custom control error on '{_cc_target}': {exc}"
                                        _log.warning("Custom control '%s' failed: %s", _cc_target, exc)
                                        print(traceback.format_exc())
                                        _step_ok = False
                                else:
                                    if _cc_target:
                                        _miss = diagnose_custom_control_miss(_cc_page, _cc_target)
                                        if _miss:
                                            print(f"    {_miss}")
                                    if not await self._execute_step(
                                        page, step, strategic_context, step_idx=action_index
                                    ):
                                        _step_error = "Action failed"
                                        _step_ok = False
                        except Exception as exc:
                            _step_ok = False
                            _step_error = traceback.format_exc()
                            _log.debug("Step execution failed: %s", exc)
                        finally:
                            if _temp_break_added:
                                self.break_steps.discard(action_index)
                            if _what_if_active:
                                self.debug_mode = _saved_debug
                                self.break_steps = _saved_break
                            duration_s = time.perf_counter() - started_perf
                            duration_ms = duration_s * 1000
                            _ss_b64: str | None = None
                            if _screenshot_mode == "always" or (_screenshot_mode == "on-fail" and not _step_ok):
                                try:
                                    _ss_bytes = await page.screenshot(type="png")
                                    _ss_b64 = base64.b64encode(_ss_bytes).decode("ascii")
                                except Exception as exc:
                                    _log.debug("Screenshot capture failed: %s", exc)
                            if _step_ok:
                                _sr_status = "pass"
                            elif step_kind == "verify_softly":
                                _sr_status = "warning"
                            else:
                                _sr_status = "fail"
                            _step_result = StepResult(
                                index=action_index,
                                text=_RE_NUMBERED_PREFIX.sub("", step),
                                status=_sr_status,
                                duration_ms=duration_ms,
                                error=_step_error,
                                screenshot=_ss_b64,
                                logical_step=block.block_name,
                            )
                            _step_results.append(_step_result)
                            block_steps.append(_step_result)

                            if _sr_status == "pass":
                                if _step_success_message is not None:
                                    print(f"  [✅ ACTION PASS] {_step_success_message} (duration: {duration_s:.2f}s)")
                                else:
                                    print(f"  [✅ ACTION PASS] duration: {duration_s:.2f}s")
                            elif _sr_status == "warning":
                                block_status = "warning" if block_status == "pass" else block_status
                                print(f"  [⚠️ ACTION WARN] {_step_error}")
                            else:
                                ok = False
                                block_status = "fail"
                                block_error = _step_error
                                _summary = (_step_error or "Action failed").strip().splitlines()[-1]
                                print(f"  [❌ ACTION FAIL] {_summary}")

                            if _auto_annotate_live and hunt_file and _action_file_lines and step_kind != "navigate":
                                try:
                                    url_after = page.url
                                    if url_after != url_before and action_index < len(_action_file_lines):
                                        await self._auto_annotate_navigate(
                                            page, hunt_file, _action_file_lines, action_index + 1
                                        )
                                except Exception as exc:
                                    _log.debug("Auto-annotate URL check failed: %s", exc)

                        if block_status == "fail" or done:
                            break

                    block_duration_ms = (time.perf_counter() - block_started_perf) * 1000
                    _block_results.append(
                        BlockResult(
                            name=block.block_name,
                            status=block_status,
                            duration_ms=block_duration_ms,
                            error=block_error,
                            actions=list(block_steps),
                        )
                    )

                    if block_status == "fail":
                        print(f"[🟥 BLOCK FAIL] {block.block_name}")
                        break

                    print(f"[🟩 BLOCK PASS] {block.block_name}")
                    if done:
                        break

            finally:
                await browser.close()

        _status = "pass" if (done or ok) else "fail"
        if _status == "pass" and _soft_errors:
            _status = "warning"
        return MissionResult(
            file=hunt_file or "",
            name=Path(hunt_file).name if hunt_file else "",
            status=_status,
            steps=_step_results,
            blocks=_block_results,
            error=_step_results[-1].error if _step_results and _status == "fail" else None,
            soft_errors=_soft_errors,
        )
