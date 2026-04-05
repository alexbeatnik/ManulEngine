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
import inspect
import json
import os
import re
import time
import traceback
from os import environ as _environ
from pathlib import Path

from playwright.async_api import async_playwright

from . import prompts
from .actions import _ActionsMixin
from .cache import _ControlsCacheMixin
from .config import EngineConfig
from .debug import _DebugMixin
from .exceptions import ConfigurationError
from .helpers import (
    RE_SYSTEM_STEP,
    ContextualHint,
    classify_step,
    compact_log_field,
    detect_mode,
    extract_quoted,
    parse_explicit_wait,
    parse_hunt_blocks,
    substitute_memory,
)
from .hooks import bind_hook_result, execute_hook_line
from .js_scripts import SNAPSHOT_JS
from .llm import create_provider
from .logging_config import logger
from .scoring import SCALE, score_elements

_log = logger.getChild("core")
from . import prompts as _prompts_mod  # for CUSTOM_CONTROLS_DIRS access
from .controls import get_custom_control, load_custom_controls
from .reporting import BlockResult, MissionResult, StepResult
from .variables import ScopedVariables

# ── Pre-compiled patterns ─────────────────────────────────────────────────────
_RE_NUMBERED_PREFIX = re.compile(r'^\s*\d+\.\s*')

# ── Score confidence thresholds (normalised 0.0–1.0 floats) ──────────────────
# Compared against best_score / SCALE.  Values > 1.0 are possible because the
# cache channel weight (2.0) allows the weighted sum to exceed 1.0.
THRESHOLD_SEMANTIC_CACHE  = 1.125   # semantic cache reuse (~200k scaled)
THRESHOLD_HIGH_CONFIDENCE = 0.112   # strong heuristic match (~20k scaled)
THRESHOLD_CONTEXT_REUSE   = 0.056   # blind/context reuse from previous step


def _confidence(score: int) -> float:
    """Convert a scaled integer score to the normalized weighted-score ratio."""
    return score / SCALE


class ManulEngine(_DebugMixin, _ControlsCacheMixin, _ActionsMixin):
    def __init__(
        self,
        model:          "str | None"  = None,
        headless:       "bool | None" = None,
        browser:        "str | None"  = None,
        browser_args:   "list[str] | None" = None,
        ai_threshold:   "int | None"  = None,
        debug_mode:     bool          = False,
        break_steps:    "set[int] | None" = None,
        disable_cache:  bool          = False,
        semantic_cache: "bool | None" = None,     # None → read from config/env
        explain_mode:   "bool | None" = None,
        required_controls: "set[str] | None" = None,  # lazy-load: filenames from extract_required_controls
        config:         "EngineConfig | None" = None,  # injectable config (takes priority)
        **_kwargs,
    ):
        # When an EngineConfig is provided, it serves as the default layer
        # between explicit keyword arguments and prompts.* module globals.
        # Priority: explicit kwargs > EngineConfig > prompts module globals.
        _cfg = config

        # None model → heuristics-only mode (AI fully disabled)
        self.model    = model    if model    is not None else (_cfg.model if _cfg else prompts.DEFAULT_MODEL)
        self.headless = headless if headless is not None else (_cfg.headless if _cfg else prompts.HEADLESS_MODE)
        _VALID_BROWSERS = ("chromium", "firefox", "webkit", "electron")
        _b = (browser or (_cfg.browser if _cfg else prompts.BROWSER)).strip().lower()
        self.browser: str = _b if _b in _VALID_BROWSERS else "chromium"
        self.browser_args: list[str] = list(browser_args) if browser_args is not None else (list(_cfg.browser_args) if _cfg else list(prompts.BROWSER_ARGS))
        # channel / executable_path: accept via **_kwargs or EngineConfig with fallback to config/env.
        _ch = _kwargs.pop("channel", None)
        self.channel: str | None = (str(_ch).strip() or None) if _ch is not None else (_cfg.channel if _cfg else prompts.CHANNEL)
        _ep = _kwargs.pop("executable_path", None)
        self.executable_path: str | None = str(_ep) if _ep is not None else (_cfg.executable_path if _cfg else prompts.EXECUTABLE_PATH)
        if self.channel is not None and self.browser != "chromium":
            raise ConfigurationError(
                f"Playwright 'channel' is only supported for Chromium, "
                f"but got browser={self.browser!r} with channel={self.channel!r}."
            )
        self.memory:          ScopedVariables = ScopedVariables()
        self.last_xpath:      str | None = None
        self.learned_elements: dict = {}        # semantic cache: cache_key → {name, tag}

        if disable_cache:
            self._controls_cache_enabled = False
        elif _cfg:
            self._controls_cache_enabled = _cfg.controls_cache_enabled
        else:
            self._controls_cache_enabled = bool(getattr(prompts, "CONTROLS_CACHE_ENABLED", True))

        if semantic_cache is not None:
            self._semantic_cache_enabled = semantic_cache
        elif disable_cache:
            self._semantic_cache_enabled = False
        elif _cfg:
            self._semantic_cache_enabled = _cfg.semantic_cache_enabled
        else:
            self._semantic_cache_enabled = bool(getattr(prompts, "SEMANTIC_CACHE_ENABLED", True))

        _default_cache_dir = str(Path(__file__).resolve().parents[1] / "cache")
        if _cfg:
            _cache_dir = _cfg.controls_cache_dir
        else:
            _cache_dir = str(getattr(prompts, "CONTROLS_CACHE_DIR", _default_cache_dir))
        self._controls_cache_root = Path(_cache_dir)
        self._controls_cache_site: str | None = None
        self._controls_cache_url: str | None = None
        self._controls_cache_path: Path | None = None
        self._controls_cache_data: dict[str, dict] = {}

        # ── Timeouts ──────────────────────────────────────────────────────
        self.timeout: int = _cfg.timeout if _cfg else prompts.TIMEOUT
        self.nav_timeout: int = _cfg.nav_timeout if _cfg else prompts.NAV_TIMEOUT
        self._verify_max_retries: int = _cfg.verify_max_retries if _cfg else int(getattr(prompts, "VERIFY_MAX_RETRIES", 15))

        # ── AI settings (stored per-instance, not read from module globals at runtime) ──
        _ai_always_default = _cfg.ai_always if _cfg else bool(getattr(prompts, "AI_ALWAYS", False))
        self._ai_always: bool = _kwargs.pop("ai_always", _ai_always_default)
        _ai_policy_default = _cfg.ai_policy if _cfg else str(getattr(prompts, "AI_POLICY", "prior"))
        self._ai_policy: str = _kwargs.pop("ai_policy", _ai_policy_default)

        # ── Auto-annotate ─────────────────────────────────────────────────
        _auto_annotate_default = _cfg.auto_annotate if _cfg else prompts.AUTO_ANNOTATE
        self._auto_annotate: bool = _kwargs.pop("auto_annotate", _auto_annotate_default)

        # Resolve model-specific settings once at construction time.
        # get_threshold returns 0 when self.model is None → AI is disabled.
        _ai_thr = ai_threshold if ai_threshold is not None else (_cfg.ai_threshold if _cfg else None)
        self._threshold       = prompts.get_threshold(self.model, _ai_thr)
        self._executor_prompt = prompts.get_executor_prompt(self.model)
        self._planner_prompt  = prompts.PLANNER_SYSTEM_PROMPT
        self.debug_mode = debug_mode
        if explain_mode is not None:
            self.explain_mode = explain_mode
        elif _cfg:
            self.explain_mode = _cfg.explain_mode
        else:
            self.explain_mode = False
        self._debug_continue = False   # set to True by 'Continue All' in debug session
        self._user_break_steps: set[int] = set(break_steps) if break_steps else set()
        self.break_steps: set[int] = set(self._user_break_steps)
        # Last element-resolution scoring data — used by 'explain' debug command.
        self._last_explain_data: tuple[str, list[str], list[dict]] | None = None
        # Tracks how many annotation lines have been inserted into the hunt file
        # during this run, so subsequent NAVIGATE steps can offset their line numbers.
        self._annotate_line_offset: int = 0
        # Self-healing flag: set by _resolve_element when a stale cache entry
        # is detected and the element is re-resolved via heuristics.
        self._last_step_healed: bool = False
        # Deferred @custom_control loading: stored here, applied on first run_mission().
        self._required_controls: set[str] | None = required_controls
        # Custom controls directories (prefer EngineConfig, fallback to prompts).
        self._custom_controls_dirs: list[str] = (
            list(_cfg.custom_controls_dirs) if _cfg else list(getattr(_prompts_mod, "CUSTOM_CONTROLS_DIRS", ["controls"]))
        )
        # LLM provider (delegates to Ollama or no-op for heuristics-only mode).
        self._llm = create_provider(self.model)
        if self.model is None:
            print("    ℹ️  No model configured — running in heuristics-only mode (AI disabled).")
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
    # ── Persistent controls cache ─────────────────────────────────────
    # All cache methods live in engine/cache.py (_ControlsCacheMixin).

    # ── LLM helpers ───────────────────────────

    def _passes_anti_phantom_guard(
        self,
        *,
        mode: str,
        is_blind: bool,
        search_texts: list[str],
        target_field: str | None,
        ai_choice: dict,
    ) -> bool:
        if mode not in ("input", "select") or is_blind:
            return True

        search_terms = [t.lower() for t in search_texts]
        if target_field:
            search_terms.append(target_field.lower())

        guard_words = set(re.findall(r"\b[a-z0-9]{2,}\b", " ".join(search_terms)))
        element_text = (
            f"{ai_choice.get('name', '')} "
            f"{ai_choice.get('html_id', '')} "
            f"{ai_choice.get('data_qa', '')} "
            f"{ai_choice.get('aria_label', '')} "
            f"{ai_choice.get('placeholder', '')}"
        ).lower()

        if not guard_words or any(w in element_text for w in guard_words):
            return True

        missing = search_texts[0] if search_texts else target_field
        compact_name = compact_log_field(ai_choice.get("name", ""), "MANUL_LOG_NAME_MAXLEN")

        print(
            f"    👻 ANTI-PHANTOM GUARD: AI chose '{compact_name}', "
            f"but target '{missing}' is missing. Rejecting."
        )
        return False

    async def _llm_json(self, system: str, user: str) -> dict | None:
        """Send a system+user prompt to the local LLM and parse JSON response.

        Delegates to the configured LLMProvider (Ollama or NullProvider).
        """
        return await self._llm.call_json(system, user)

    async def _llm_plan(self, task: str) -> list[str]:
        """Ask the LLM to decompose a free-text task into numbered steps."""
        print("    🧠 AI PLANNER: Generating mission steps...")
        obj = await self._llm_json(self._planner_prompt, task)
        return obj.get("steps", []) if obj else []

    async def _llm_select_element(
        self, step: str, mode: str, candidates: list[dict], strategic_context: str
    ) -> "int | None":
        """Ask the LLM to pick the best element from scored candidates."""
        payload = [
            {
                "id":           el["id"],
                "score":        int(el.get("score", 0)),
                "name":         el["name"],
                "tag":          el.get("tag_name", ""),
                "input_type":   el.get("input_type", ""),
                "role":         el.get("role", ""),
                "data_qa":      el.get("data_qa", ""),
                "html_id":      el.get("html_id", ""),
                "class_name":   el.get("class_name", ""),
                "icon_classes": el.get("icon_classes", ""),
                "aria_label":   el.get("aria_label", ""),
                "placeholder":  el.get("placeholder", ""),
                "disabled":     el.get("disabled", False),
                "aria_disabled": el.get("aria_disabled", ""),
                "is_select":    el.get("is_select", False),
                "is_shadow":    el.get("is_shadow", False),
                "contenteditable": el.get("is_contenteditable", False),
            }
            for el in candidates
        ]
        prompt = (
            f"STEP: {step}\n"
            f"MODE: {mode.upper()}\n"
            f"ELEMENTS:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        system = self._executor_prompt.replace("{strategic_context}", strategic_context)
        obj = await self._llm_json(system, prompt)
        if not obj or not isinstance(obj, dict):
            # In pure-AI mode we must not silently fall back to heuristics.
            return None if self._ai_always else 0

        raw_id = obj.get("id", None)
        if raw_id is None: # fallback for generic keys
            for key in ["id", '"id"', "ID"]:
                if key in obj:
                    raw_id = obj[key]
                    break

        if raw_id is None or str(raw_id).lower() == "null":
            thought = obj.get("thought", "No matching element found.")
            print(f"    🚫 AI REJECTED CANDIDATES: '{thought}'")
            return None

        try:
            chosen_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            chosen_id = None

        thought = obj.get("thought", "")
        if chosen_id is not None:
            idx = next((i for i, el in enumerate(candidates) if el["id"] == chosen_id), 0)
        else:
            idx = 0

        # Optional deterministic guard for id-strict synthetic tests.
        # When MANUL_AI_POLICY=strict, enforce best score even if the LLM picked a neighbor.
        if self._ai_always and self._ai_policy == "strict" and candidates:
            best_idx = max(range(len(candidates)), key=lambda i: int(candidates[i].get("score", 0)))
            if int(candidates[idx].get("score", 0)) < int(candidates[best_idx].get("score", 0)):
                print(
                    f"    🧷 AI OVERRIDE (strict): enforcing best score (ai={candidates[idx].get('score', 0)} "
                    f"< best={candidates[best_idx].get('score', 0)})"
                )
                idx = best_idx
        compact_name = compact_log_field(candidates[idx].get("name", ""), "MANUL_LOG_NAME_MAXLEN")
        compact_thought = compact_log_field(thought, "MANUL_LOG_THOUGHT_MAXLEN")

        print(f"    🎯 AI DECISION: '{compact_name}' — {compact_thought}")
        return idx

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
        """Print a formatted score breakdown for the top candidates."""
        target_str = ", ".join(search_texts) if search_texts else "(blind)"
        print(f"\n    ┌─ 🔍 EXPLAIN: Target = \"{target_str}\"")
        print(f"    │  Step: {step}")
        print(f"    │  Top {len(top)} candidates:")
        for rank, el in enumerate(top, 1):
            name = compact_log_field(el.get("name", ""), "MANUL_LOG_NAME_MAXLEN")
            tag = el.get("tag_name", "?")
            score = el.get("score", 0)
            expl = el.get("_explain")
            if expl:
                print("    │")
                print(f"    │  #{rank}  <{tag}> \"{name}\"  → Total: {expl['total']:.3f}")
                print(f"    │       Text:       {expl['text']:>+.3f}")
                print(f"    │       Attributes: {expl['attributes']:>+.3f}")
                print(f"    │       Semantics:  {expl['semantics']:>+.3f}")
                print(f"    │       Proximity:  {expl['proximity']:>+.3f}")
                print(f"    │       Cache:      {expl['cache']:>+.3f}")
                if expl["penalty"] < 1.0:
                    print(f"    │       Penalty:    ×{expl['penalty']:.1f}")
                if "ctx_kind" in expl:
                    ctx_label = expl["ctx_kind"].upper().replace("_", " ")
                    print(f"    │       Context:    {ctx_label} (raw={expl.get('ctx_prox_raw', 0):.3f})")
            else:
                print(f"    │  #{rank}  <{tag}> \"{name}\"  → Score: {score}")
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
        print("    │")
        print(f"    └─ ✅ Decision: Selected \"{winner_name}\" with score {winner_display}{ctx_summary}")
        print()

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
            els, step, mode, search_texts, target_field, is_blind,
            learned_elements=self.learned_elements if self._semantic_cache_enabled else {},
            last_xpath=self.last_xpath,
            explain=self.explain_mode,
            contextual_hint=contextual_hint,
            anchor_rect=anchor_rect,
            container_elements=container_elements,
            viewport_height=viewport_height,
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
        self._last_step_healed = False
        _had_stale_cache = False

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

            cached_control = self._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                contextual_hint=contextual_hint,
                candidates=els,
            )
            if cached_control is not None:
                is_disabled = bool(cached_control.get("disabled"))
                aria_disabled_raw = str(cached_control.get("aria_disabled", "")).strip().lower()
                is_aria_disabled = aria_disabled_raw == "true"
                if not (is_disabled or is_aria_disabled):
                    return cached_control
            elif self._controls_cache_enabled:
                _cache_key = self._control_cache_key(mode, search_texts, target_field, contextual_hint)
                if _cache_key in self._controls_cache_data:
                    _had_stale_cache = True

            # Quick exact-match pass
            exact = []
            for el in els:
                name = el["name"].lower().strip()
                aria = el.get("aria_label", "").lower().strip()
                dqa  = el.get("data_qa", "").lower().strip()
                if target_field and target_field in name:
                    exact.append(el)
                    continue
                for q in search_texts:
                    q_l = q.lower().strip()
                    if ((len(q_l) <= 2 and q_l == name)
                            or (len(q_l) > 2 and q_l in name)):
                        exact.append(el)
                        break
                    if len(q_l) > 2 and (
                        q_l in aria
                        or q_l.replace(" ", "-") in dqa
                        or q_l.replace(" ", "_") in dqa
                    ):
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

        scored     = self._score_elements(
            els, step, mode, search_texts, target_field, is_blind,
            contextual_hint=contextual_hint,
            anchor_rect=anchor_rect,
            container_elements=container_elements,
            viewport_height=viewport_height,
        )
        top        = scored[:8]
        best_score = top[0].get("score", 0)

        # Store scoring data for on-demand explain during debug pauses.
        self._last_explain_data = (step, list(search_texts), list(top[:3]))

        # ── Explain mode: print per-element score breakdown ──────────────
        if self.explain_mode and top:
            self._print_explain(step, search_texts, top[:3])

        # Self-healing: stale cache entry detected — flag for heuristic paths below.
        # The cache is updated by _remember_resolved_control after the action succeeds.
        _conf = _confidence(best_score)
        if _had_stale_cache:
            print(f"    🔄 STALE CACHE: Entry invalidated — re-resolving (confidence {_conf:.3f})")

        # Pure-AI mode: usually asks the LLM, but fast-tracks if there is only 1 candidate.
        # Guard: ai_always has no effect without a model — fall through to heuristics.
        if self._ai_always and self.model is not None:
            if len(scored) == 1:
                print("    ⚡ FAST-TRACK: Found exactly 1 candidate, bypassing AI.")
                idx = 0
            else:
                print(f"    🧠 AI AGENT: Always-AI enabled, analysing {len(top)} candidates…")
                idx = await self._llm_select_element(step, mode, top, strategic_context)

            if idx is None:
                self._last_step_healed = False
                if failed_ids is not None:
                    for c in top:
                        failed_ids.add((c.get("frame_index", 0), c["id"]))
                return None
            ai_choice = top[idx]

            if not self._passes_anti_phantom_guard(
                mode=mode,
                is_blind=is_blind,
                search_texts=search_texts,
                target_field=target_field,
                ai_choice=ai_choice,
            ):
                self._last_step_healed = False
                return None

            return ai_choice

        if _conf >= THRESHOLD_SEMANTIC_CACHE:
            print(f"    🧠 SEMANTIC CACHE: Reusing learned element (confidence {_conf:.3f})")
            if _had_stale_cache:
                self._last_step_healed = True
            return top[0]

        if _conf >= THRESHOLD_CONTEXT_REUSE:
            label = "High confidence" if _conf >= THRESHOLD_HIGH_CONFIDENCE else "Context reuse"
            print(f"    ⚙️  DOM HEURISTICS: {label} match (confidence {_conf:.3f})")
            if _had_stale_cache:
                self._last_step_healed = True
            return top[0]

        if best_score >= self._threshold:
            label = "High confidence" if best_score >= self._threshold * 2 else "Keyword"
            print(f"    ⚙️  DOM HEURISTICS: {label} match (confidence {_conf:.3f})")
            if _had_stale_cache:
                self._last_step_healed = True
            return top[0]

        # Explicit AI disable switch: threshold <= 0 means "never call the LLM".
        # (Useful for deterministic runs and environments without Ollama.)
        if self._threshold <= 0:
            print(f"    ⚙️  DOM HEURISTICS: AI disabled; using best candidate (confidence {_conf:.3f})")
            if _had_stale_cache:
                self._last_step_healed = True
            return top[0]

        # Genuinely ambiguous → ask the LLM, unless there's only 1 candidate left
        if len(scored) == 1:
            print("    ⚡ FAST-TRACK: Found exactly 1 candidate, bypassing AI.")
            idx = 0
        else:
            print(f"    🧠 AI AGENT: Ambiguity detected, analysing {len(top)} candidates…")
            try:
                idx = await self._llm_select_element(step, mode, top, strategic_context)
            except Exception as exc:
                print(f"    ⚠️  LLM selection failed ({type(exc).__name__}: {exc}), falling back to top heuristic candidate")
                idx = 0

        if idx is None:
            self._last_step_healed = False
            if failed_ids is not None:
                for c in top:
                    failed_ids.add((c.get("frame_index", 0), c["id"]))
            return None

        ai_choice = top[idx]

        if not self._passes_anti_phantom_guard(
            mode=mode,
            is_blind=is_blind,
            search_texts=search_texts,
            target_field=target_field,
            ai_choice=ai_choice,
        ):
            self._last_step_healed = False
            return None

        return ai_choice

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
                with open(hunt_file, encoding='utf-8') as _hf:
                    lines = _hf.readlines()

                above_idx = nav_line_no - 2  # 0-based index of the line above the step

                if 0 <= above_idx < len(lines) and lines[above_idx].strip().startswith('# 📍 Auto-Nav:'):
                    lines[above_idx] = comment_line
                else:
                    lines.insert(nav_line_no - 1, comment_line)
                    self._annotate_line_offset += 1

                with open(hunt_file, 'w', encoding='utf-8') as _hf:
                    _hf.writelines(lines)
                print(f"    📍 Auto-Nav: {display}")

            except Exception as _io_exc:
                print(f"    ⚠️  Auto-Nav: file I/O error: {_io_exc}")

        except Exception as _ann_exc:
            print(f"    ⚠️  Auto-Nav: {_ann_exc}")

    async def _launch_browser(self, p, hunt_file: str | None = None):
        """Launch browser via Playwright and return ``(browser, ctx, page)``.

        Handles Electron CDP connections, per-OS sandbox flags, ``channel``
        and ``executable_path`` options.  On Electron failure a
        ``MissionResult`` with status ``"fail"`` is returned instead.
        """
        if self.browser == "electron":
            _cdp_port = _environ.get("MANUL_CDP_PORT", "9222")
            _cdp_url = f"http://localhost:{_cdp_port}"
            try:
                browser = await p.chromium.connect_over_cdp(_cdp_url)
            except Exception as _cdp_exc:
                print(
                    f"    ❌ Failed to connect to Electron via CDP at {_cdp_url}: {_cdp_exc}\n"
                    f"    💡 Ensure the Electron app is running with "
                    f"--remote-debugging-port={_cdp_port}"
                )
                _fail = MissionResult(file=hunt_file or "", name=Path(hunt_file).name if hunt_file else "", status="fail")
                return _fail, None, None
            if browser.contexts:
                ctx = browser.contexts[0]
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            else:
                ctx = await browser.new_context()
                page = await ctx.new_page()
            return browser, ctx, page

        _launch_args: list[str] = ["--start-maximized"] if self.browser == "chromium" else []
        _is_root = hasattr(os, "getuid") and os.getuid() == 0
        if self.browser == "chromium" and (_is_root or os.path.exists("/.dockerenv")):
            _launch_args.insert(0, "--no-sandbox")
        _launch_args = _launch_args + [a for a in self.browser_args if a not in _launch_args]
        _launch_opts: dict = dict(headless=self.headless, args=_launch_args)
        if self.channel:
            if self.browser != "chromium":
                raise ConfigurationError(
                    f"'channel' is only supported for Chromium; "
                    f"got browser={self.browser!r}, channel={self.channel!r}"
                )
            _launch_opts["channel"] = self.channel
        if self.executable_path:
            _launch_opts["executable_path"] = self.executable_path
        browser = await getattr(p, self.browser).launch(**_launch_opts)
        ctx = await browser.new_context(
            no_viewport=True
        ) if not self.headless else await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await ctx.new_page()
        return browser, ctx, page

    async def _parse_task(self, task: str) -> str:
        """Detect task format and produce executable step text.

        Handles STEP-grouped, numbered, and free-text formats.
        Free-text tasks are decomposed by the LLM planner.
        """
        _has_step_markers = bool(re.search(r'^\s*STEP\s*\d*\s*:', task, re.MULTILINE | re.IGNORECASE))
        _is_numbered = bool(re.match(r'^\s*\d+\.', task))
        _has_action_keywords = bool(RE_SYSTEM_STEP.search(task))
        if _has_step_markers or (_has_action_keywords and not _is_numbered):
            return task
        if _is_numbered:
            return "\n".join(
                s.strip() for s in re.split(r'(?=\b\d+\.\s)', task) if s.strip()
            )
        parsed_task = "\n".join(await self._llm_plan(task))
        if not parsed_task:
            print("    ❌ No plan produced. If you're running without Ollama, provide a numbered or unnumbered step list.")
        return parsed_task

    async def run_mission(self, task: str, strategic_context: str = "", hunt_dir: str | None = None,
                          hunt_file: str | None = None, step_file_lines: "list[int] | None" = None,
                          initial_vars: "dict | None" = None,
                          global_vars: "dict | None" = None,
                          row_vars: "dict | None" = None,
                          import_vars: "dict | None" = None,
                          screenshot_mode: str = "none") -> MissionResult:
        """
        Execute a full browser automation mission.

        The task can be either a numbered step list ("1. Navigate to ... 2. Click ...")
        or a free-text description that will be decomposed by the LLM planner.

        Returns a :class:`MissionResult` (truthy when status != "fail").
        """
        mode_label = f"[{self.model}]  — Transparent AI" if self.model else "— Heuristics-only (no AI)"
        print(f"\n🐾 ManulEngine {mode_label}  |  browser: {self.browser}")

        # ── Ensure @custom_control handlers required for this mission are loaded ──
        load_custom_controls(
            str(Path.cwd()),
            required_modules=self._required_controls,
            custom_modules_dirs=self._custom_controls_dirs,
        )

        async with async_playwright() as p:
            browser, ctx, page = await self._launch_browser(p, hunt_file)
            # Electron CDP failure returns (MissionResult, None, None).
            if ctx is None or page is None:
                return browser  # it's actually the MissionResult

            parsed_task = await self._parse_task(task)

            blocks = parse_hunt_blocks(parsed_task, step_file_lines)
            if not blocks:
                return MissionResult(file=hunt_file or "", name=Path(hunt_file).name if hunt_file else "", status="fail")

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
            # The cache is invalidated when pages.json is modified on disk so live
            # edits made during a long run are still reflected within one step.
            _cc_page_cache: dict[str, str] = {}
            _cc_pages_mtime: float = 0.0
            try:
                action_index = 0
                for block in blocks:
                    block_started_perf = time.perf_counter()
                    block_steps: list[StepResult] = []
                    block_status = "pass"
                    block_error: str | None = None

                    print(f"\n[📦 BLOCK START] {block.block_name}")

                    for raw_step in block.actions:
                        action_index += 1
                        step = substitute_memory(raw_step, self.memory)
                        started_perf = time.perf_counter()
                        step_kind = classify_step(step)
                        _wait_target, _wait_state = parse_explicit_wait(step) if step_kind == "wait_for_element" else (None, None)
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
                        elif not self.debug_mode and self.break_steps and action_index in self.break_steps and _is_system_step:
                            import sys as _sys
                            if not _sys.stdin.isatty():
                                print(f"    🔴 BREAKPOINT at action {action_index}")
                                await self._debug_prompt(page, step, action_index)
                            else:
                                print(f"    🔴 BREAKPOINT at action {action_index} — opening Playwright Inspector…")
                                await page.pause()

                        _auto_annotate_live = (
                            _environ.get("MANUL_AUTO_ANNOTATE", "").strip().lower()
                            in ("1", "true", "yes")
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
                                    await self._auto_annotate_navigate(page, hunt_file, _action_file_lines, action_index)

                            elif step_kind == "open_app":
                                _app_ok, page = await self._handle_open_app(page, ctx)
                                if not _app_ok:
                                    _step_error = "OPEN APP failed"
                                    _step_ok = False

                            elif step_kind == "mock":
                                if not await self._handle_mock(page, step, hunt_dir=hunt_dir):
                                    _step_error = "MOCK command failed"
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
                                else:
                                    _step_success_message = _wait_msg

                            elif step_kind == "wait":
                                n = re.search(r'(\d+)', step)
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
                                if not await self._handle_verify_visual(page, step, strategic_context, step_idx=action_index, hunt_dir=hunt_dir):
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
                                if not await self._handle_right_click(page, step, strategic_context, step_idx=action_index):
                                    _step_error = "RIGHT CLICK command failed"
                                    _step_ok = False

                            elif step_kind == "upload":
                                if not await self._handle_upload(page, step, strategic_context, step_idx=action_index, hunt_dir=hunt_dir):
                                    _step_error = "UPLOAD command failed"
                                    _step_ok = False

                            elif step_kind == "scan_page":
                                if not await self._handle_scan_page(page, step):
                                    _step_error = "SCAN PAGE failed"
                                    _step_ok = False

                            elif step_kind == "call_python":
                                instruction = _RE_NUMBERED_PREFIX.sub('', step).strip()
                                if re.match(r'CALL\s+PYTHON\b', instruction.upper()):
                                    raw_instr = _RE_NUMBERED_PREFIX.sub('', raw_step).strip()
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
                                    raw_step, re.IGNORECASE,
                                )
                                if _set_m:
                                    _sv_name = _set_m.group(1)
                                    _rhs_m = re.match(
                                        r"(?:\d+\.\s*)?SET\s+\S+\s*=\s*(.+)",
                                        step, re.IGNORECASE,
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

                            elif step_kind == "debug":
                                if not self.debug_mode:
                                    import sys as _sys
                                    if not _sys.stdin.isatty():
                                        print("    🔎 DEBUG/PAUSE step")
                                        await self._debug_prompt(page, step, action_index)
                                    else:
                                        print("    🔎 DEBUG/PAUSE step — opening Playwright Inspector…")
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
                                if _cc_target:
                                    _mt = prompts.pages_registry_mtime()
                                    if _mt != _cc_pages_mtime:
                                        _cc_page_cache.clear()
                                        _cc_pages_mtime = _mt
                                    _cc_page = _cc_page_cache.get(page.url) or prompts.lookup_page_name(page.url)
                                    _cc_page_cache[page.url] = _cc_page
                                    _cc_handler = get_custom_control(_cc_page, _cc_target)
                                if _cc_handler is not None:
                                    print(f"    🎛️  [CUSTOM CONTROL] Routed '{_cc_target}' on '{_cc_page}' to custom handler.")
                                    try:
                                        _cc_result = _cc_handler(page, _cc_mode, _cc_value)
                                        if inspect.isawaitable(_cc_result):
                                            await _cc_result
                                    except Exception as exc:
                                        _step_error = f"Custom control error on '{_cc_target}': {exc}"
                                        _log.warning("Custom control '%s' failed: %s", _cc_target, exc)
                                        print(traceback.format_exc())
                                        _step_ok = False
                                elif not await self._execute_step(page, step, strategic_context, step_idx=action_index):
                                    _step_error = "Action failed"
                                    _step_ok = False
                        except Exception as exc:
                            _step_ok = False
                            _step_error = traceback.format_exc()
                            _log.debug("Step execution failed: %s", exc)
                        finally:
                            duration_s = time.perf_counter() - started_perf
                            duration_ms = duration_s * 1000
                            _ss_b64: str | None = None
                            if _screenshot_mode == "always" or (_screenshot_mode == "on-fail" and not _step_ok):
                                try:
                                    import base64 as _b64
                                    _ss_bytes = await page.screenshot(type="png")
                                    _ss_b64 = _b64.b64encode(_ss_bytes).decode("ascii")
                                except Exception as exc:
                                    _log.debug("Screenshot capture failed: %s", exc)
                            if _step_ok:
                                _sr_status = "pass"
                            elif step_kind == "verify_softly":
                                _sr_status = "warning"
                            else:
                                _sr_status = "fail"
                            _healed = self._last_step_healed
                            _step_result = StepResult(
                                index=action_index,
                                text=_RE_NUMBERED_PREFIX.sub('', step),
                                status=_sr_status,
                                duration_ms=duration_ms,
                                error=_step_error,
                                screenshot=_ss_b64,
                                logical_step=block.block_name,
                                healed=_healed,
                            )
                            _step_results.append(_step_result)
                            block_steps.append(_step_result)
                            self._last_step_healed = False

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
                    _block_results.append(BlockResult(
                        name=block.block_name,
                        status=block_status,
                        duration_ms=block_duration_ms,
                        error=block_error,
                        actions=list(block_steps),
                    ))

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
