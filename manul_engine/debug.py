# manul_engine/debug.py
"""
Debug session mixin for ManulEngine.

Extracts all interactive debugging, element highlighting, and debug
protocol logic into a single cohesive module.  The mixin is inherited
by ``ManulEngine`` in ``core.py`` and contributes the following methods:

  _highlight          — flash border (non-persistent, 2 s)
  _debug_highlight    — persistent magenta outline + glow
  _clear_debug_highlight — remove persistent highlight
  _inject_debug_modal — inject ✕ Abort button into browser
  _remove_debug_modal — remove the Abort modal
  _poll_for_abort     — background task polling for modal click
  _debug_prompt       — interactive pause (terminal / extension protocol)
"""

import asyncio
import json
import sys

from .js_scripts import DEBUG_MODAL_JS, DEBUG_REMOVE_MODAL_JS
from .logging_config import logger
from .explain_next import ExplainNextDebugger

_log = logger.getChild("debug")


class _DebugMixin:
    """Mixin providing interactive debugging capabilities for ManulEngine."""

    _explain_next_debugger: ExplainNextDebugger | None = None

    def _get_explain_next(self) -> ExplainNextDebugger:
        """Lazily create the ExplainNextDebugger for what-if analysis."""
        if self._explain_next_debugger is None:
            self._explain_next_debugger = ExplainNextDebugger(
                llm=self._llm,  # type: ignore[attr-defined]
                learned_elements=getattr(self, "learned_elements", None),
                last_xpath=getattr(self, "last_xpath", None),
                engine=self,
            )
        return self._explain_next_debugger

    # ── Visual feedback ───────────────────────

    async def _highlight(self, page, target, color="red", bg="#ffeb3b", *, by_js_id=False, frame=None):
        """Flash a coloured border around an element for visual debugging."""
        try:
            if by_js_id:
                ctx = frame or page
                await ctx.evaluate("([id, c, b]) => window.manulHighlight(id, c, b)", [target, color, bg])
            else:
                await target.evaluate(
                    """(el, args) => {
                    const [color, bg] = args;
                    const oB=el.style.border, oBg=el.style.backgroundColor;
                    el.style.border='4px solid '+color; el.style.backgroundColor=bg;
                    setTimeout(()=>{el.style.border=oB;el.style.backgroundColor=oBg;},2000);
                }""",
                    [color, bg],
                )
            await asyncio.sleep(0.4)
        except (OSError, RuntimeError):
            _log.debug("highlight failed — page or element already destroyed")

    async def _debug_highlight(self, page, loc_or_id, *, by_js_id: bool = False, frame=None) -> None:
        """Apply a persistent magenta highlight on the target element.

        The highlight stays until ``_clear_debug_highlight()`` is called.
        Uses ``<style id="manul-debug-style">`` + ``data-manul-debug-highlight``
        so it is safely removable without disturbing inline styles.
        """
        _STYLE_ID = "manul-debug-style"
        _STYLE_CSS = (
            "[data-manul-debug-highlight='true']{"
            "outline:4px solid #ff00ff !important;"
            "box-shadow:0 0 15px #ff00ff !important;"
            "background:rgba(255,0,255,.12) !important;"
            "z-index:999999 !important;}"
        )
        try:
            if by_js_id:
                ctx = frame or page
                await ctx.evaluate(
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
        except (OSError, RuntimeError):
            _log.debug("debug_highlight failed — page or element already destroyed")

    async def _clear_debug_highlight(self, page) -> None:
        """Remove the persistent debug highlight from all elements and remove the ``<style>`` tag."""
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
        except (OSError, RuntimeError):
            _log.debug("clear_debug_highlight failed — page already destroyed")

    _DEBUG_PAUSE_MARKER = "\x00MANUL_DEBUG_PAUSE\x00"

    async def _inject_debug_modal(self, page, step: str) -> None:
        """Inject the floating debug panel with an Abort button into the browser."""
        try:
            await page.evaluate(DEBUG_MODAL_JS, step)
        except (OSError, RuntimeError):
            _log.debug("inject_debug_modal failed — page already destroyed")

    async def _remove_debug_modal(self, page) -> None:
        """Remove the debug modal and reset the abort signal."""
        try:
            await page.evaluate(DEBUG_REMOVE_MODAL_JS)
        except (OSError, RuntimeError):
            _log.debug("remove_debug_modal failed — page already destroyed")

    async def _poll_for_abort(self, page, abort_event: asyncio.Event) -> None:
        """Poll ``window.__manul_debug_action`` every 200 ms; set *abort_event* on ABORT."""
        while not abort_event.is_set():
            try:
                action = await page.evaluate("() => window.__manul_debug_action || null")
                if action == "ABORT":
                    abort_event.set()
                    return
            except (OSError, RuntimeError):
                _log.debug("poll_for_abort: page context lost, stopping poll")
                return
            await asyncio.sleep(0.2)

    async def _debug_prompt(self, page, step: str, idx: int) -> None:
        """Interactive prompt used in debug mode.

        Two operating modes, detected automatically:

        1. **Extension protocol mode** (stdin is not a TTY, i.e. piped by the
           VS Code extension): writes a JSON pause marker to stdout, then reads
           tokens from stdin in a loop.  Accepted tokens:
             - ``'highlight'`` : re-scroll to the currently highlighted element
             - ``'explain'``   : print heuristic score breakdown
             - ``'what-if'``   : enter the Explain Next what-if REPL
             - ``'continue'``  : reset to original gutter breakpoints, proceed
             - ``'next'``      : also pause at the immediately following step
             - ``'debug-stop'``: clear all breakpoints, run to end
             - ``'abort'``     : abort the test immediately

        2. **Terminal mode** (stdin is a TTY): prints a human-readable prompt and
           waits for input.

        In both modes the in-browser debug modal (with an ✕ Abort button) is
        injected before waiting and removed afterwards.
        """
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
                        _done, pending = await asyncio.wait(
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
                        try:
                            await page.evaluate("""
                                () => {
                                    const el = document.querySelector('[data-manul-debug-highlight="true"]');
                                    if (el) el.scrollIntoView({behavior:'smooth',block:'center'});
                                }
                            """)
                        except (OSError, RuntimeError):
                            pass
                        continue  # loop: re-emit the marker
                    elif resp == "explain":
                        if self._last_explain_data:
                            _es, _et, _etop = self._last_explain_data
                            self._print_explain(_es, _et, _etop)
                        else:
                            print("    ℹ️  No element resolution data for this step.")
                        continue  # loop: re-emit the marker
                    elif resp == "what-if":
                        dbg = self._get_explain_next()
                        chosen = await dbg.run_repl(page, current_step=step)
                        if chosen is not None:
                            self._what_if_execute_step = chosen
                        break
                    elif resp == "debug-stop":
                        self._user_break_steps = set()
                        self.break_steps = set()
                        break
                    elif resp == "continue":
                        self.break_steps = set(self._user_break_steps)
                        break
                    else:  # "next" (or any unrecognised token)
                        self.break_steps.add(idx + 1)
                        break
                return

            # ── Terminal mode ─────────────────────────────────────────────
            sys.stdout.flush()
            prompt_text = (
                f"\n[DEBUG] Next step: {step}\n"
                f"        ENTER/n = execute · h = re-highlight · w = what-if · pause = Inspector · c = continue all… "
            )
            while True:
                try:
                    read_task = asyncio.create_task(asyncio.to_thread(input, prompt_text))
                    abort_wait = asyncio.create_task(abort_event.wait())
                    _done, pending = await asyncio.wait([read_task, abort_wait], return_when=asyncio.FIRST_COMPLETED)
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
                        except (OSError, RuntimeError):
                            pass
                        continue  # re-show the prompt without advancing
                    elif user_in == "pause":
                        print("    🔎 Opening Playwright Inspector…")
                        await page.pause()
                        continue  # re-show the prompt after closing Inspector
                    elif user_in in ("w", "what-if"):
                        dbg = self._get_explain_next()
                        chosen = await dbg.run_repl(page, current_step=step)
                        if chosen is not None:
                            self._what_if_execute_step = chosen
                            break
                        continue  # user quit REPL, back to debug prompt
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
            abort_event.set()
            abort_poll_task.cancel()
            await self._remove_debug_modal(page)
