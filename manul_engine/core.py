# manul_engine/core.py
"""
ManulEngine — the main browser automation class.

Orchestrates the full automation pipeline:
  1. Parse mission into steps (LLM planner or numbered list)
  2. For each step, detect interaction mode and resolve the target element
  3. Delegate action execution to the _ActionsMixin (engine/actions.py)

Element resolution uses a multi-stage pipeline:
  DOM snapshot (JS) → heuristic scoring → optional LLM fallback → anti-phantom guard

Inherits action handlers from _ActionsMixin (navigate, scroll, extract, verify,
drag-and-drop, click/type/select/hover via _execute_step).
"""

import asyncio
import datetime
import inspect
import json
import re
import time
import traceback
from pathlib import Path
from playwright.async_api import async_playwright

try:
    import ollama  # type: ignore
except Exception:  # pragma: no cover
    ollama = None

from . import prompts
from .helpers import substitute_memory, compact_log_field, extract_quoted
from .hooks import execute_hook_line
from .js_scripts import SNAPSHOT_JS
from .scoring import score_elements
from .actions import _ActionsMixin
from .cache import _ControlsCacheMixin
from .controls import load_custom_controls, get_custom_control


class ManulEngine(_ControlsCacheMixin, _ActionsMixin):
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
        **_kwargs,
    ):
        # None model → heuristics-only mode (AI fully disabled)
        self.model    = model    if model    is not None else prompts.DEFAULT_MODEL
        self.headless = headless if headless is not None else prompts.HEADLESS_MODE
        _VALID_BROWSERS = ("chromium", "firefox", "webkit")
        _b = (browser or prompts.BROWSER).strip().lower()
        self.browser: str = _b if _b in _VALID_BROWSERS else "chromium"
        self.browser_args: list[str] = list(browser_args) if browser_args is not None else list(prompts.BROWSER_ARGS)
        self.memory:          dict = {}
        self.last_xpath:      "str | None" = None
        self.learned_elements: dict = {}        # semantic cache: cache_key → {name, tag}
        
        if disable_cache:
            self._controls_cache_enabled = False
        else:
            self._controls_cache_enabled = bool(getattr(prompts, "CONTROLS_CACHE_ENABLED", True))

        if semantic_cache is not None:
            self._semantic_cache_enabled = semantic_cache
        elif disable_cache:
            self._semantic_cache_enabled = False
        else:
            self._semantic_cache_enabled = bool(getattr(prompts, "SEMANTIC_CACHE_ENABLED", True))
            
        self._controls_cache_root = Path(str(getattr(prompts, "CONTROLS_CACHE_DIR", str(Path(__file__).resolve().parents[1] / "cache"))))
        self._controls_cache_site: str | None = None
        self._controls_cache_url: str | None = None
        self._controls_cache_path: Path | None = None
        self._controls_cache_data: dict[str, dict] = {}
        # Resolve model-specific settings once at construction time.
        # get_threshold returns 0 when self.model is None → AI is disabled.
        self._threshold       = prompts.get_threshold(self.model, ai_threshold)
        self._executor_prompt = prompts.get_executor_prompt(self.model)
        self.debug_mode = debug_mode
        self._debug_continue = False   # set to True by 'Continue All' in debug session
        self._user_break_steps: set[int] = set(break_steps) if break_steps else set()
        self.break_steps: set[int] = set(self._user_break_steps)
        # Tracks how many annotation lines have been inserted into the hunt file
        # during this run, so subsequent NAVIGATE steps can offset their line numbers.
        self._annotate_line_offset: int = 0
        if self.model is None:
            print("    ℹ️  No model configured — running in heuristics-only mode (AI disabled).")
        if self.debug_mode:
            print("    🐛 Debug mode ON — engine will pause before each step.")
        load_custom_controls(str(Path.cwd()))  # idempotent — skips if already loaded for this path

    def reset_session_state(self) -> None:
        """Clear in-memory caches and variables. Useful for synthetic stateless tests."""
        self.memory.clear()
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
        """Send a system+user prompt to the local LLM and parse JSON response."""
        if self.model is None:
            return None  # heuristics-only mode
        if ollama is None:
            print("    ⚠️  LLM unavailable: Python package 'ollama' is not installed.")
            return None
        try:
            resp = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                format="json",
            )
            raw = resp["message"]["content"]
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            return json.loads(m.group(0) if m else raw)
        except Exception as e:
            print(f"    ⚠️  LLM error: {e}")
            return None

    async def _llm_plan(self, task: str) -> list[str]:
        """Ask the LLM to decompose a free-text task into numbered steps."""
        print("    🧠 AI PLANNER: Generating mission steps...")
        obj = await self._llm_json(prompts.PLANNER_SYSTEM_PROMPT, task)
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
            return None if getattr(prompts, "AI_ALWAYS", False) else 0

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
        if getattr(prompts, "AI_ALWAYS", False) and getattr(prompts, "AI_POLICY", "prior") == "strict" and candidates:
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

    # ── Visual feedback ───────────────────────

    async def _highlight(self, page, target, color="red", bg="#ffeb3b", *, by_js_id=False):
        """Flash a coloured border around an element for visual debugging."""
        try:
            if by_js_id:
                await page.evaluate(f"window.manulHighlight({target}, '{color}', '{bg}')")
            else:
                await target.evaluate(f"""el => {{
                    const oB=el.style.border, oBg=el.style.backgroundColor;
                    el.style.border='4px solid {color}'; el.style.backgroundColor='{bg}';
                    setTimeout(()=>{{el.style.border=oB;el.style.backgroundColor=oBg;}},2000);
                }}""")
            await asyncio.sleep(0.4)
        except Exception:
            pass

    async def _debug_highlight(self, page, loc_or_id, *, by_js_id: bool = False) -> None:
        """Apply a persistent magenta highlight on the target element.
        The highlight stays until _clear_debug_highlight() is called.
        Uses a <style id="manul-debug-style"> tag + data-manul-debug-highlight attribute
        so it is safely removable without disturbing any inline styles.
        """
        _STYLE_ID  = "manul-debug-style"
        _STYLE_CSS = ("[data-manul-debug-highlight='true']{"
                      "outline:4px solid #ff00ff !important;"
                      "box-shadow:0 0 15px #ff00ff !important;"
                      "background:rgba(255,0,255,.12) !important;"
                      "z-index:999999 !important;}")
        try:
            if by_js_id:
                await page.evaluate(
                    f"""
                    (id) => {{
                        const el = window.manulElements && window.manulElements[id];
                        if (!el) return;
                        if (!document.getElementById('{_STYLE_ID}')) {{
                            const s = document.createElement('style');
                            s.id = '{_STYLE_ID}';
                            s.textContent = `{_STYLE_CSS}`;
                            document.head.appendChild(s);
                        }}
                        el.setAttribute('data-manul-debug-highlight', 'true');
                        el.scrollIntoView({{behavior:'smooth',block:'center'}});
                    }}
                    """,
                    loc_or_id,
                )
            else:
                await loc_or_id.evaluate(
                    f"""
                    el => {{
                        if (!document.getElementById('{_STYLE_ID}')) {{
                            const s = document.createElement('style');
                            s.id = '{_STYLE_ID}';
                            s.textContent = `{_STYLE_CSS}`;
                            document.head.appendChild(s);
                        }}
                        el.setAttribute('data-manul-debug-highlight', 'true');
                        el.scrollIntoView({{behavior:'smooth',block:'center'}});
                    }}
                    """
                )
        except Exception:
            pass

    async def _clear_debug_highlight(self, page) -> None:
        """Remove the persistent debug highlight from all elements and remove the <style> tag."""
        try:
            await page.evaluate("""
                () => {
                    document.querySelectorAll('[data-manul-debug-highlight]').forEach(
                        el => el.removeAttribute('data-manul-debug-highlight')
                    );
                    const s = document.getElementById('manul-debug-style');
                    if (s) s.remove();
                }
            """)
        except Exception:
            pass

    _DEBUG_PAUSE_MARKER = "\x00MANUL_DEBUG_PAUSE\x00"

    # ── In-browser debug modal ────────────────────────────────────────────────
    # A lightweight floating panel injected into the live page during debug pauses.
    # Shows the step text and an ✕ Abort button that sets window.__manul_debug_action.
    _MODAL_JS: str = """(stepText) => {
        const old = document.getElementById('manul-debug-modal');
        if (old) old.remove();
        window.__manul_debug_action = null;

        const modal = document.createElement('div');
        modal.id = 'manul-debug-modal';
        modal.style.cssText = [
            'position:fixed', 'top:12px', 'right:12px', 'z-index:2147483647',
            'background:#1e1e2e', 'color:#cdd6f4',
            'border:2px solid #89b4fa', 'border-radius:8px',
            'padding:14px 40px 14px 16px',
            'font-family:monospace', 'font-size:13px',
            'max-width:420px', 'word-break:break-all',
            'box-shadow:0 4px 24px rgba(0,0,0,.55)',
            'pointer-events:all', 'user-select:none',
        ].join(';');

        const label = document.createElement('div');
        label.style.cssText = 'font-weight:bold;color:#89b4fa;margin-bottom:6px;font-size:11px;letter-spacing:.06em;';
        label.textContent = '\uD83D\uDC3E MANUL DEBUG PAUSE';

        const text = document.createElement('div');
        text.style.cssText = 'line-height:1.5;';
        text.textContent = stepText;

        const btn = document.createElement('button');
        btn.id = 'manul-debug-abort';
        btn.textContent = '\u2715';
        btn.title = 'Abort test run';
        btn.style.cssText = [
            'position:absolute', 'top:8px', 'right:8px',
            'background:transparent', 'border:none',
            'color:#a6adc8', 'font-size:16px', 'font-weight:bold',
            'cursor:pointer', 'line-height:1', 'padding:2px 6px',
            'border-radius:4px', 'transition:background .15s,color .15s',
        ].join(';');
        btn.onmouseover = () => { btn.style.background='#f38ba8'; btn.style.color='#1e1e2e'; };
        btn.onmouseout  = () => { btn.style.background='transparent'; btn.style.color='#a6adc8'; };
        btn.addEventListener('click', () => { window.__manul_debug_action = 'ABORT'; });

        modal.appendChild(label);
        modal.appendChild(text);
        modal.appendChild(btn);
        document.body.appendChild(modal);
    }"""

    _REMOVE_MODAL_JS: str = """() => {
        const m = document.getElementById('manul-debug-modal');
        if (m) m.remove();
        window.__manul_debug_action = null;
    }"""

    async def _inject_debug_modal(self, page, step: str) -> None:
        """Inject the floating debug panel with an Abort button into the browser."""
        try:
            await page.evaluate(self._MODAL_JS, step)
        except Exception:
            pass

    async def _remove_debug_modal(self, page) -> None:
        """Remove the debug modal and reset the abort signal."""
        try:
            await page.evaluate(self._REMOVE_MODAL_JS)
        except Exception:
            pass

    async def _poll_for_abort(self, page, abort_event: asyncio.Event) -> None:
        """Poll window.__manul_debug_action every 200 ms; set abort_event on ABORT."""
        while not abort_event.is_set():
            try:
                action = await page.evaluate("() => window.__manul_debug_action || null")
                if action == "ABORT":
                    abort_event.set()
                    return
            except Exception:
                pass
            await asyncio.sleep(0.2)

    async def _debug_prompt(self, page, step: str, idx: int) -> None:
        """Interactive prompt used in debug mode.

        Two operating modes, detected automatically:

        1. **Extension protocol mode** (stdin is not a TTY, i.e. piped by the
           VS Code extension): writes a JSON pause marker to stdout, then reads
           tokens from stdin in a loop.  Accepted tokens:
             - 'highlight' : re-scroll to the currently highlighted element, re-emit marker
             - 'continue'  : reset to original gutter breakpoints, proceed
             - 'next'      : also pause at the immediately following step
             - 'abort'     : abort the test immediately

        2. **Terminal mode** (stdin is a TTY): prints a human-readable prompt and
           waits for input.  Typing 'h' re-scrolls to the highlighted element;
           'pause' opens the Playwright Inspector; 'c' / 'continue' disables
           future pauses for this session.

        In both modes the in-browser debug modal (with an ✕ Abort button) is
        injected before waiting and removed afterwards.  Clicking ✕ raises an
        exception that aborts the test immediately.

        If _debug_continue is already True the method returns immediately.
        """
        import sys
        if self._debug_continue:
            return

        await self._inject_debug_modal(page, step)

        abort_event: asyncio.Event = asyncio.Event()
        abort_poll_task = asyncio.create_task(self._poll_for_abort(page, abort_event))

        try:
            if not sys.stdin.isatty():
                # ── Extension protocol mode ───────────────────────────────
                marker = json.dumps({"step": step, "idx": idx})
                while True:
                    sys.stdout.write(f"{self._DEBUG_PAUSE_MARKER}{marker}\n")
                    sys.stdout.flush()
                    try:
                        read_task = asyncio.create_task(asyncio.to_thread(sys.stdin.readline))
                        abort_wait = asyncio.create_task(abort_event.wait())
                        done, pending = await asyncio.wait(
                            [read_task, abort_wait], return_when=asyncio.FIRST_COMPLETED
                        )
                        for t in pending:
                            t.cancel()
                        if abort_event.is_set():
                            raise Exception("Test intentionally aborted by user via debug modal")
                        resp = read_task.result().strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        return
                    if resp == "abort":
                        raise Exception("Test intentionally aborted by user via debug modal")
                    elif resp == "highlight":
                        # Re-scroll to the persistently highlighted element, then
                        # re-emit the pause marker so the QuickPick shows again.
                        try:
                            await page.evaluate("""
                                () => {
                                    const el = document.querySelector('[data-manul-debug-highlight="true"]');
                                    if (el) el.scrollIntoView({behavior:'smooth',block:'center'});
                                }
                            """)
                        except Exception:
                            pass
                        continue  # loop: re-emit the marker
                    elif resp == "debug-stop":
                        # Clear ALL breakpoints (including user-defined gutter ones)
                        # so execution runs to the end without further pauses.
                        self._user_break_steps = set()
                        self.break_steps = set()
                        break
                    elif resp == "continue":
                        # Restore only the user-set breakpoints so execution resumes
                        # until the next gutter breakpoint (or end if none remain).
                        self.break_steps = set(self._user_break_steps)
                        break
                    else:  # "next" (or any unrecognised token)
                        # Pause again at the immediately following step.
                        self.break_steps.add(idx + 1)
                        break
                return

            # ── Terminal mode ─────────────────────────────────────────────
            sys.stdout.flush()
            prompt_text = (
                f"\n[DEBUG] Next step: {step}\n"
                f"        ENTER/n = execute · h = re-highlight · pause = Inspector · c = continue all… "
            )
            while True:
                try:
                    read_task   = asyncio.create_task(asyncio.to_thread(input, prompt_text))
                    abort_wait  = asyncio.create_task(abort_event.wait())
                    done, pending = await asyncio.wait(
                        [read_task, abort_wait], return_when=asyncio.FIRST_COMPLETED
                    )
                    for t in pending:
                        t.cancel()
                    if abort_event.is_set():
                        print()
                        raise Exception("Test intentionally aborted by user via debug modal")
                    user_in = read_task.result().strip().lower()
                    if user_in == "h":
                        try:
                            await page.evaluate("""
                                () => {
                                    const el = document.querySelector('[data-manul-debug-highlight="true"]');
                                    if (el) el.scrollIntoView({behavior:'smooth',block:'center'});
                                }
                            """)
                            print("    👁️  Scrolled to highlighted element.")
                        except Exception:
                            pass
                        continue  # re-show the prompt without advancing
                    elif user_in == "pause":
                        print("    🔎 Opening Playwright Inspector…")
                        await page.pause()
                        continue  # re-show the prompt after closing Inspector
                    elif user_in in ("c", "continue"):
                        self._debug_continue = True
                        print("    ▶ Continuing all steps without further pauses…")
                        break
                    else:  # ENTER / n / anything else → execute the step
                        break
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
        finally:
            abort_event.set()   # stop the poll task whether we return, break, or raise
            abort_poll_task.cancel()
            await self._remove_debug_modal(page)

    # ── DOM snapshot ──────────────────────────

    async def _snapshot(self, page, mode: str, texts: list[str]) -> list[dict]:
        """Inject SNAPSHOT_JS into the page and return a list of interactive elements."""
        for attempt in range(3):
            try:
                return await page.evaluate(SNAPSHOT_JS, [mode, texts or []])
            except Exception as exc:
                if "closed" in str(exc).lower() and attempt < 2:
                    await asyncio.sleep(1.5)
                    continue
                raise

    # ── Scoring (delegates to scoring module) ─

    def _score_elements(
        self,
        els: list[dict],
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        is_blind: bool,
    ) -> list[dict]:
        """Score and rank elements using heuristics from scoring.py."""
        return score_elements(
            els, step, mode, search_texts, target_field, is_blind,
            learned_elements=self.learned_elements if self._semantic_cache_enabled else {},
            last_xpath=self.last_xpath,
        )

    # ── Element resolution ────────────────────

    async def _resolve_element(
        self,
        page,
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        strategic_context: str,
        failed_ids: "set | None" = None,
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
            els = [e for e in raw_els if e["id"] not in _skip]

            if not els:
                if attempt < 4:
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(1)
                continue

            if mode == "drag":
                break

            cached_control = self._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=els,
            )
            if cached_control is not None:
                is_disabled = bool(cached_control.get("disabled"))
                aria_disabled_raw = str(cached_control.get("aria_disabled", "")).strip().lower()
                is_aria_disabled = aria_disabled_raw == "true"
                if not (is_disabled or is_aria_disabled):
                    return cached_control

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
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)

        if not els:
            return None

        scored     = self._score_elements(els, step, mode, search_texts, target_field, is_blind)
        top        = scored[:8]
        best_score = top[0].get("score", 0)

        # Pure-AI mode: usually asks the LLM, but fast-tracks if there is only 1 candidate.
        # Guard: ai_always has no effect without a model — fall through to heuristics.
        if getattr(prompts, "AI_ALWAYS", False) and self.model is not None:
            if len(scored) == 1:
                print("    ⚡ FAST-TRACK: Found exactly 1 candidate, bypassing AI.")
                idx = 0
            else:
                print(f"    🧠 AI AGENT: Always-AI enabled, analysing {len(top)} candidates…")
                idx = await self._llm_select_element(step, mode, top, strategic_context)
                
            if idx is None:
                if failed_ids is not None:
                    for c in top:
                        failed_ids.add(c["id"])
                return None
            ai_choice = top[idx]

            if not self._passes_anti_phantom_guard(
                mode=mode,
                is_blind=is_blind,
                search_texts=search_texts,
                target_field=target_field,
                ai_choice=ai_choice,
            ):
                return None

            return ai_choice

        if best_score >= 200_000:
            print(f"    🧠 SEMANTIC CACHE: Reusing learned element (score {best_score})")
            return top[0]

        if best_score >= 10_000:
            label = "High confidence" if best_score >= 20_000 else "Context reuse"
            print(f"    ⚙️  DOM HEURISTICS: {label} match (score {best_score})")
            return top[0]

        if best_score >= self._threshold:
            label = "High confidence" if best_score >= self._threshold * 2 else "Keyword"
            print(f"    ⚙️  DOM HEURISTICS: {label} match (score {best_score})")
            return top[0]

        # Explicit AI disable switch: threshold <= 0 means "never call the LLM".
        # (Useful for deterministic runs and environments without Ollama.)
        if self._threshold <= 0:
            print(f"    ⚙️  DOM HEURISTICS: AI disabled (threshold {self._threshold}); using best candidate (score {best_score})")
            return top[0]

        # Genuinely ambiguous → ask the LLM, unless there's only 1 candidate left
        if len(scored) == 1:
            print("    ⚡ FAST-TRACK: Found exactly 1 candidate, bypassing AI.")
            idx = 0
        else:
            print(f"    🧠 AI AGENT: Ambiguity detected, analysing {len(top)} candidates…")
            try:
                idx = await self._llm_select_element(step, mode, top, strategic_context)
            except Exception:
                idx = 0
            
        if idx is None:
            if failed_ids is not None:
                for c in top:
                    failed_ids.add(c["id"])
            return None

        ai_choice = top[idx]

        if not self._passes_anti_phantom_guard(
            mode=mode,
            is_blind=is_blind,
            search_texts=search_texts,
            target_field=target_field,
            ai_choice=ai_choice,
        ):
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
                with open(hunt_file, 'r', encoding='utf-8') as _hf:
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

    async def run_mission(self, task: str, strategic_context: str = "", hunt_dir: str | None = None,
                          hunt_file: str | None = None, step_file_lines: "list[int] | None" = None) -> bool:
        """
        Execute a full browser automation mission.

        The task can be either a numbered step list ("1. Navigate to ... 2. Click ...")
        or a free-text description that will be decomposed by the LLM planner.
        """
        mode_label = f"[{self.model}]  — Transparent AI" if self.model else "— Heuristics-only (no AI)"
        print(f"\n🐾 ManulEngine {mode_label}  |  browser: {self.browser}")

        async with async_playwright() as p:
            _launch_args = ["--no-sandbox", "--start-maximized"] if self.browser == "chromium" else []
            _launch_args = _launch_args + [a for a in self.browser_args if a not in _launch_args]
            browser = await getattr(p, self.browser).launch(
                headless=self.headless,
                args=_launch_args,
            )
            ctx  = await browser.new_context(no_viewport=True)
            page = await ctx.new_page()

            if re.match(r'^\s*\d+\.', task):
                plan = [s.strip() for s in re.split(r'(?=\b\d+\.\s)', task) if s.strip()]
            else:
                plan = await self._llm_plan(task)

            if not plan and not re.match(r'^\s*\d+\.', task):
                print("    ❌ No plan produced. If you're running without Ollama, provide a numbered step list.")

            if not plan:
                await browser.close()
                return False

            ok = True
            done = False
            # Cache lookup_page_name() results within this mission.
            # The cache is invalidated when pages.json is modified on disk so live
            # edits made during a long run are still reflected within one step.
            _cc_page_cache: dict[str, str] = {}
            _cc_pages_mtime: float = 0.0
            try:
                for i, raw_step in enumerate(plan, 1):
                    step = substitute_memory(raw_step, self.memory)
                    started_at = datetime.datetime.now()
                    started_perf = time.perf_counter()
                    print(f"\n[🐾 STEP {i} @ {started_at.strftime('%H:%M:%S')}] {step}")
                    s_up = step.upper()

                    # Determine whether this step is a system step (NAVIGATE, SCROLL,
                    # etc.) or an action step (click, fill, select, hover…).
                    # For action steps, the debug pause fires INSIDE _execute_step
                    # after element resolution so the tester sees the highlighted
                    # element before deciding to proceed.
                    _is_system_step = bool(re.search(
                        r'\b(?:NAVIGATE|WAIT|SCROLL|EXTRACT|PRESS\s+ENTER|SCAN\s+PAGE|CALL\s+PYTHON|DEBUG|PAUSE|DONE)\b',
                        s_up
                    ))

                    if self.debug_mode and _is_system_step:
                        await self._debug_prompt(page, step, i)
                    elif not self.debug_mode and self.break_steps and i in self.break_steps and _is_system_step:
                        import sys as _sys
                        if not _sys.stdin.isatty():
                            print(f"    🔴 BREAKPOINT at step {i}")
                            await self._debug_prompt(page, step, i)
                        else:
                            print(f"    🔴 BREAKPOINT at step {i} — opening Playwright Inspector…")
                            await page.pause()

                    # Re-read AUTO_ANNOTATE at runtime so env vars injected after
                    # import time (e.g. by the VS Code extension) are respected.
                    import os as _os_nav
                    _auto_annotate_live = (
                        _os_nav.environ.get("MANUL_AUTO_ANNOTATE", "").strip().lower()
                        in ("1", "true", "yes")
                    ) or prompts.AUTO_ANNOTATE
                    try:
                        url_before = page.url
                    except Exception:
                        url_before = ""

                    try:
                        if re.search(r'\bNAVIGATE\b', s_up):
                            if not await self._handle_navigate(page, step):
                                ok = False; break
                            if _auto_annotate_live and hunt_file and step_file_lines:
                                await self._auto_annotate_navigate(page, hunt_file, step_file_lines, i)

                        elif re.search(r'\bWAIT\b', s_up):
                            n = re.search(r'(\d+)', step)
                            await asyncio.sleep(int(n.group(1)) if n else 2)

                        elif re.search(r'\bSCROLL\b', s_up):
                            await self._handle_scroll(page, step)

                        elif re.search(r'\bEXTRACT\b', s_up):
                            if not await self._handle_extract(page, step):
                                ok = False; break

                        elif re.search(r'\bVERIFY\b', s_up):
                            if not await self._handle_verify(page, step, step_idx=i):
                                ok = False; break

                        elif re.search(r'\bPRESS\s+ENTER\b', s_up):
                            await self._handle_press_enter(page)

                        elif re.search(r'\bSCAN\s+PAGE\b', s_up):
                            if not await self._handle_scan_page(page, step):
                                ok = False; break

                        elif re.search(r'\bCALL\s+PYTHON\b', s_up):
                            # Strip any leading step number, then re-check from
                            # the start to avoid false positives on button labels
                            # that happen to contain the words "CALL PYTHON".
                            instruction = re.sub(r'^\s*\d+\.\s*', '', step).strip()
                            if re.match(r'CALL\s+PYTHON\b', instruction.upper()):
                                result = execute_hook_line(instruction, hunt_dir=hunt_dir)
                                print(f"     {result.message}")
                                if not result.success:
                                    ok = False; break
                            else:
                                # "CALL PYTHON" appears mid-sentence (e.g. a button
                                # label) — route through the normal action executor.
                                if not await self._execute_step(page, step, strategic_context, step_idx=i):
                                    print("    ❌ ACTION FAILED")
                                    ok = False; break

                        elif re.search(r'\b(?:DEBUG|PAUSE)\b', s_up):
                            # In debug_mode the pre-step _debug_prompt() above already
                            # paused execution; treat this step as a no-op to avoid a
                            # double-pause for the same step.
                            if not self.debug_mode:
                                import sys as _sys
                                if not _sys.stdin.isatty():
                                    # Piped mode (VS Code extension): use the marker protocol
                                    # so the panel can show the pause overlay.
                                    print("    \U0001f50e DEBUG/PAUSE step")
                                    await self._debug_prompt(page, step, i)
                                else:
                                    # Terminal mode: open the Playwright Inspector.
                                    print("    \U0001f50e DEBUG/PAUSE step \u2014 opening Playwright Inspector\u2026")
                                    await page.pause()

                        elif re.search(r'\bDONE\b', s_up):
                            print("    🏁 MISSION ACCOMPLISHED")
                            done = True
                            break

                        else:
                            # ── Custom controls interception ───────────────────────────────
                            _cc_step_l = step.lower()
                            _cc_words = set(re.findall(r'\b[a-z]+\b', _cc_step_l))
                            if "drag" in _cc_words and "drop" in _cc_words:
                                _cc_mode = "drag"
                            elif "select" in _cc_words or "choose" in _cc_words:
                                _cc_mode = "select"
                            elif any(w in _cc_words for w in ("type", "fill", "enter")):
                                _cc_mode = "input"
                            elif any(w in _cc_words for w in ("click", "double", "check", "uncheck")):
                                _cc_mode = "clickable"
                            elif "hover" in _cc_words:
                                _cc_mode = "hover"
                            else:
                                _cc_mode = "locate"
                            _cc_quoted = extract_quoted(step, preserve_case=True)
                            if _cc_mode == "input" and len(_cc_quoted) >= 2:
                                # target = field/control name, value = text to type
                                _cc_target, _cc_value = _cc_quoted[0], _cc_quoted[-1]
                            elif _cc_mode == "select" and len(_cc_quoted) >= 2:
                                # target = dropdown/control name (last quoted), value = option (first quoted)
                                # e.g. Select 'Express' from the 'Shipping Method' dropdown
                                _cc_target, _cc_value = _cc_quoted[-1], _cc_quoted[0]
                            elif _cc_mode == "drag" and len(_cc_quoted) >= 2:
                                # target = drag source, value = drop destination
                                _cc_target, _cc_value = _cc_quoted[0], _cc_quoted[-1]
                            elif _cc_quoted:
                                # click/hover/locate: first quoted token is the target, no value
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
                                except Exception as _cc_exc:
                                    print(
                                        f"    ❌ Custom control error on "
                                        f"'{_cc_target}' (page='{_cc_page}'): {_cc_exc}\n"
                                        + traceback.format_exc()
                                    )
                                    ok = False; break
                            # ── End custom controls interception ──────────────────────────
                            elif not await self._execute_step(page, step, strategic_context, step_idx=i):
                                print("    ❌ ACTION FAILED")
                                ok = False; break
                    finally:
                        ended_at = datetime.datetime.now()
                        duration_s = time.perf_counter() - started_perf
                        print(
                            f"    ⏱️  STEP END @ {ended_at.strftime('%H:%M:%S')} — duration {duration_s:.2f}s"
                        )
                        # After non-NAVIGATE steps, check if the URL changed and
                        # annotate the next step with the new landing URL.
                        if _auto_annotate_live and hunt_file and step_file_lines \
                                and not re.search(r'\bNAVIGATE\b', s_up):
                            try:
                                url_after = page.url
                                if url_after != url_before and i < len(step_file_lines):
                                    await self._auto_annotate_navigate(
                                        page, hunt_file, step_file_lines, i + 1
                                    )
                            except Exception:
                                pass

            finally:
                await browser.close()

        return True if done else ok