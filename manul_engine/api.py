# manul_engine/api.py
"""
ManulSession — Public Python API for ManulEngine.

Provides a high-level async context manager that owns the Playwright
lifecycle and exposes clean methods (``navigate``, ``click``, ``fill``,
``verify``, ``extract``, etc.) for use in pure Python scripts.

Each method internally routes through the full ManulEngine smart-resolution
pipeline: Controls Cache → DOM Heuristics → optional LLM fallback.

Usage::

    from manul_engine import ManulSession

    async with ManulSession(headless=True) as session:
        await session.navigate("https://example.com")
        await session.click("Log in button")
        await session.fill("Username field", "admin")
        await session.verify("Welcome")
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .core import ManulEngine
from .helpers import classify_step, substitute_memory
from .reporting import MissionResult, StepResult
from .variables import ScopedVariables


def _quote_for_dsl(text: str) -> str:
    """Safely wrap *text* in quotes for Manul DSL steps.

    Uses single quotes by default, but switches to double quotes when the
    string contains a single quote.  If both quote types are present, a
    ``ValueError`` is raised.
    """
    if "'" in text and '"' in text:
        raise ValueError(
            "ManulSession step text cannot contain both single and double "
            "quotes; please simplify the target/text."
        )
    if "'" in text:
        return f'"{text}"'
    return f"'{text}'"


class ManulSession:
    """High-level async context manager for programmatic browser automation.

    Manages its own Playwright browser lifecycle.  All element-resolution
    calls go through the full ManulEngine pipeline (cache → heuristics →
    optional LLM fallback) — callers never need to think about selectors.

    Parameters match :class:`ManulEngine`'s constructor for consistency.
    """

    def __init__(
        self,
        model: str | None = None,
        headless: bool | None = None,
        browser: str | None = None,
        browser_args: list[str] | None = None,
        ai_threshold: int | None = None,
        disable_cache: bool = False,
        semantic_cache: bool | None = None,
        channel: str | None = None,
        executable_path: str | None = None,
    ) -> None:
        self._engine = ManulEngine(
            model=model,
            headless=headless,
            browser=browser,
            browser_args=browser_args,
            ai_threshold=ai_threshold,
            disable_cache=disable_cache,
            semantic_cache=semantic_cache,
            channel=channel,
            executable_path=executable_path,
        )
        # Playwright objects — initialised by ``start()`` / ``__aenter__``.
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._pw_cm: Any = None  # async_playwright() context manager

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> ManulSession:
        """Launch the browser and open a page.  Called by ``__aenter__``."""
        eng = self._engine
        self._pw_cm = async_playwright()
        self._pw = await self._pw_cm.__aenter__()
        p = self._pw

        # Playwright 'channel' is only supported for Chromium.
        if eng.channel and eng.browser != "chromium":
            raise ValueError(
                f"Playwright 'channel' is only supported for browser='chromium'; "
                f"got browser={eng.browser!r}"
            )

        if eng.browser == "electron":
            _cdp_port = os.environ.get("MANUL_CDP_PORT", "9222")
            _cdp_url = f"http://localhost:{_cdp_port}"
            try:
                self._browser = await p.chromium.connect_over_cdp(_cdp_url)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to connect to Electron app over CDP at {_cdp_url}. "
                    f"Ensure the target app is running with "
                    f"'--remote-debugging-port={_cdp_port}' enabled and that "
                    f"the port is accessible. Original error: {exc}"
                ) from exc
            if self._browser.contexts:
                self._context = self._browser.contexts[0]
                self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            else:
                self._context = await self._browser.new_context()
                self._page = await self._context.new_page()
        else:
            _launch_args = (
                ["--no-sandbox", "--start-maximized"]
                if eng.browser == "chromium"
                else []
            )
            _launch_args = _launch_args + [
                a for a in eng.browser_args if a not in _launch_args
            ]
            _launch_opts: dict[str, Any] = dict(
                headless=eng.headless,
                args=_launch_args,
            )
            if eng.channel:
                _launch_opts["channel"] = eng.channel
            if eng.executable_path:
                _launch_opts["executable_path"] = eng.executable_path

            self._browser = await getattr(p, eng.browser).launch(**_launch_opts)
            if eng.headless:
                self._context = await self._browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                )
            else:
                self._context = await self._browser.new_context(no_viewport=True)
            self._page = await self._context.new_page()

        return self

    async def close(self) -> None:
        """Close the browser and tear down Playwright."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw_cm:
            try:
                await self._pw_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._pw = None
            self._pw_cm = None
        self._context = None
        self._page = None

    async def __aenter__(self) -> ManulSession:
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def page(self) -> Page:
        """The active Playwright ``Page``.  Useful for advanced one-offs."""
        if self._page is None:
            raise RuntimeError(
                "ManulSession has no active page.  "
                "Use 'async with ManulSession() as s:' or call start() first."
            )
        return self._page

    @property
    def engine(self) -> ManulEngine:
        """The underlying :class:`ManulEngine` instance (read-only)."""
        return self._engine

    @property
    def memory(self) -> ScopedVariables:
        """Shortcut to the engine's scoped variable store."""
        return self._engine.memory

    # ── Navigation ────────────────────────────────────────────────────────

    async def navigate(self, url: str) -> None:
        """Navigate to *url* and wait for DOM settlement."""
        page = self.page
        await page.goto(url, wait_until="domcontentloaded", timeout=self._engine.nav_timeout)
        self._engine.last_xpath = None
        await asyncio.sleep(2.0)

    # ── Core actions (route through the full smart pipeline) ──────────────

    async def click(self, target: str, *, double: bool = False) -> bool:
        """Click an element described in plain English.

        Internally runs: Controls Cache → DOM Heuristics → LLM fallback.

        Args:
            target: Plain-English description (e.g. ``"Log in button"``).
            double: If *True*, double-click instead of single-click.

        Returns:
            ``True`` if the action succeeded.
        """
        verb = "DOUBLE CLICK" if double else "Click"
        step = f"{verb} the {_quote_for_dsl(target)}"
        return await self._engine._execute_step(self.page, step, step_idx=0)

    async def fill(self, target: str, text: str) -> bool:
        """Type *text* into the element described by *target*.

        Args:
            target: Plain-English field description (e.g. ``"Username field"``).
            text:   The text to type.

        Returns:
            ``True`` if the action succeeded.
        """
        step = f"Fill {_quote_for_dsl(target)} with {_quote_for_dsl(text)}"
        return await self._engine._execute_step(self.page, step, step_idx=0)

    async def select(self, option: str, target: str) -> bool:
        """Select *option* from a dropdown described by *target*.

        Args:
            option: The visible option text (e.g. ``"Express Shipping"``).
            target: The dropdown description (e.g. ``"Shipping Method"``).

        Returns:
            ``True`` if the action succeeded.
        """
        step = f"Select {_quote_for_dsl(option)} from the {_quote_for_dsl(target)} dropdown"
        return await self._engine._execute_step(self.page, step, step_idx=0)

    async def hover(self, target: str) -> bool:
        """Hover over the element described by *target*.

        Returns:
            ``True`` if the action succeeded.
        """
        step = f"HOVER over the {_quote_for_dsl(target)}"
        return await self._engine._execute_step(self.page, step, step_idx=0)

    async def drag(self, source: str, destination: str) -> bool:
        """Drag *source* and drop it onto *destination*.

        Returns:
            ``True`` if the action succeeded.
        """
        step = f"Drag the {_quote_for_dsl(source)} and drop it into {_quote_for_dsl(destination)}"
        return await self._engine._execute_step(self.page, step, step_idx=0)

    async def right_click(self, target: str) -> bool:
        """Right-click on the element described by *target*.

        Returns:
            ``True`` if the action succeeded.
        """
        step = f"RIGHT CLICK {_quote_for_dsl(target)}"
        return await self._engine._handle_right_click(self.page, step)

    async def press(self, key: str, target: str | None = None) -> bool:
        """Press a key or key combination, optionally on a specific element.

        Args:
            key:    Key name (e.g. ``"Enter"``, ``"Control+A"``, ``"Escape"``).
            target: If provided, press the key on this element.

        Returns:
            ``True`` if the action succeeded.
        """
        if target:
            step = f"PRESS {key} on {_quote_for_dsl(target)}"
        else:
            step = f"PRESS {key}"
        return await self._engine._handle_press(self.page, step)

    async def upload(self, file_path: str, target: str) -> bool:
        """Upload a file to a file-input element.

        Args:
            file_path: Path to the file (relative to CWD or absolute).
            target:    File input description (e.g. ``"Profile Picture"``).

        Returns:
            ``True`` if the action succeeded.
        """
        step = f"UPLOAD {_quote_for_dsl(file_path)} to {_quote_for_dsl(target)}"
        return await self._engine._handle_upload(self.page, step)

    async def scroll(self, target: str | None = None) -> None:
        """Scroll down, optionally inside a specific container.

        Args:
            target: If provided, scroll inside the named container
                    (e.g. ``"the dropdown list"``).
        """
        step = f"SCROLL DOWN inside {target}" if target else "SCROLL DOWN"
        await self._engine._handle_scroll(self.page, step)

    # ── Verification ──────────────────────────────────────────────────────

    async def verify(
        self,
        target: str,
        *,
        present: bool = True,
        enabled: bool | None = None,
        checked: bool | None = None,
    ) -> bool:
        """Assert a condition on the page.

        Args:
            target:  The text or element to verify.
            present: ``True`` = must be present; ``False`` = must be absent.
            enabled: If set, verify the element is enabled (``True``) or
                     disabled (``False``).
            checked: If set, verify a checkbox is checked (``True``) or
                     not checked (``False``).

        Returns:
            ``True`` if the condition holds.
        """
        if checked is not None:
            neg = "NOT " if not checked else ""
            step = f"VERIFY that {_quote_for_dsl(target)} is {neg}checked"
        elif enabled is not None:
            state = "ENABLED" if enabled else "DISABLED"
            step = f"VERIFY that {_quote_for_dsl(target)} is {state}"
        elif not present:
            step = f"VERIFY that {_quote_for_dsl(target)} is NOT present"
        else:
            step = f"VERIFY that {_quote_for_dsl(target)} is present"
        return await self._engine._handle_verify(self.page, step)

    # ── Data extraction ───────────────────────────────────────────────────

    async def extract(self, target: str, variable: str | None = None) -> str | None:
        """Extract visible text matching *target* from the page.

        Args:
            target:   Quoted target description for the engine.
            variable: Optional variable name to store the result in
                      ``session.memory``.

        Returns:
            The extracted text, or ``None`` on failure.
        """
        var_name = variable or "_api_extract"
        step = f"EXTRACT the {_quote_for_dsl(target)} into {{{var_name}}}"
        ok = await self._engine._handle_extract(self.page, step)
        if ok:
            return str(self._engine.memory.get(var_name, ""))
        return None

    # ── Wait ──────────────────────────────────────────────────────────────

    async def wait(self, seconds: float) -> None:
        """Pause execution for *seconds*."""
        await asyncio.sleep(seconds)

    # ── Convenience: run raw DSL steps ────────────────────────────────────

    async def run_steps(self, steps: str, context: str = "") -> MissionResult:
        """Execute raw Hunt DSL steps against the current page.

        This helper runs a multi-line string of DSL steps through the same
        resolution engine as :meth:`ManulEngine.run_mission`, but using an
        inline runner that reuses the already-open browser session and page
        instead of launching a new browser or parsing a full ``.hunt`` file.

        Unlike ``run_mission()``, this method:

        * Does **not** parse file-level headers (``@context``, ``@title``,
          ``@tags``, ``@data``, ``@schedule``).
        * Does **not** execute ``[SETUP]`` / ``[TEARDOWN]`` hook blocks.
        * Does **not** apply CLI/config features like retries, automatic
          screenshots, or HTML report generation.
        * Comment lines (``#``) and metadata headers (``@``) in *steps*
          are silently filtered out.

        .. warning::
            Because the browser is already open, any ``NAVIGATE`` step
            inside *steps* will navigate the current page in this session
            — it will not open a new browser or context.
        """
        return await self._run_steps_on_page(steps, context)

    # ── Internal step execution (reuses open page) ────────────────────────

    async def _run_steps_on_page(self, task: str, strategic_context: str = "") -> MissionResult:
        """Execute parsed steps against the already-open page.

        Mirrors the step-dispatch loop in ``ManulEngine.run_mission`` but
        skips browser launch/teardown — the session already owns the page.
        """
        import time

        from .hooks import execute_hook_line

        eng = self._engine
        page = self.page

        _has_step_markers = bool(
            re.search(r'^\s*STEP\s*\d*\s*:', task, re.MULTILINE | re.IGNORECASE)
        )
        _is_numbered = bool(re.match(r'^\s*\d+\.', task))
        from .helpers import RE_SYSTEM_STEP
        _has_action_keywords = bool(RE_SYSTEM_STEP.search(task))

        # Strip comments, metadata headers, and hook blocks
        # (aligned with parse_hunt_file() behaviour).
        def _extract_executable(text: str) -> list[str]:
            result: list[str] = []
            in_hook = False
            for line in text.splitlines():
                s = line.strip()
                if not s:
                    continue
                upper = s.upper()
                if upper in ("[SETUP]", "[TEARDOWN]"):
                    in_hook = True
                    continue
                if upper in ("[END SETUP]", "[END TEARDOWN]"):
                    in_hook = False
                    continue
                if in_hook:
                    continue
                if s.startswith("#") or s.startswith("@"):
                    continue
                result.append(s)
            return result

        if _has_step_markers or (_has_action_keywords and not _is_numbered):
            plan = _extract_executable(task)
        elif _is_numbered:
            plan = _extract_executable(task)
        else:
            plan = _extract_executable(task)

        if not plan:
            return MissionResult(file="", name="<api>", status="pass")

        ok = True
        done = False
        _step_results: list[StepResult] = []
        _block_results = []
        _soft_errors: list[str] = []
        from .helpers import parse_hunt_blocks
        from .reporting import BlockResult

        blocks = parse_hunt_blocks("\n".join(plan))
        if not blocks:
            return MissionResult(file="", name="<api>", status="pass")

        action_index = 0
        for block in blocks:
            block_started_perf = time.perf_counter()
            block_steps: list[StepResult] = []
            block_status = "pass"
            block_error: str | None = None

            for raw_step in block.actions:
                action_index += 1
                step = substitute_memory(raw_step, eng.memory)
                started_perf = time.perf_counter()
                step_kind = classify_step(step)

                _step_ok = True
                _step_error: str | None = None
                try:
                    if step_kind == "navigate":
                        if not await eng._handle_navigate(page, step):
                            _step_error = "Navigation failed"
                            _step_ok = False

                    elif step_kind == "wait_for_element":
                        _wait_ok, _wait_msg = await eng._handle_wait_for_element(page, step)
                        if not _wait_ok:
                            _step_error = _wait_msg
                            _step_ok = False

                    elif step_kind == "wait":
                        n = re.search(r'(\d+)', step)
                        await asyncio.sleep(int(n.group(1)) if n else 2)

                    elif step_kind == "scroll":
                        await eng._handle_scroll(page, step)

                    elif step_kind == "extract":
                        if not await eng._handle_extract(page, step):
                            _step_error = "Extract failed"
                            _step_ok = False

                    elif step_kind == "verify":
                        if not await eng._handle_verify(page, step):
                            _step_error = "Verification failed"
                            _step_ok = False

                    elif step_kind == "verify_softly":
                        _soft_ok = await eng._handle_verify_softly(page, step)
                        if not _soft_ok:
                            _soft_msg = f"Soft assertion failed at action {action_index}: {step}"
                            _soft_errors.append(_soft_msg)
                            _step_error = _soft_msg
                            _step_ok = False

                    elif step_kind == "press_enter":
                        await eng._handle_press_enter(page)

                    elif step_kind == "press":
                        if not await eng._handle_press(page, step):
                            _step_error = "PRESS command failed"
                            _step_ok = False

                    elif step_kind == "right_click":
                        if not await eng._handle_right_click(page, step):
                            _step_error = "RIGHT CLICK command failed"
                            _step_ok = False

                    elif step_kind == "upload":
                        if not await eng._handle_upload(page, step):
                            _step_error = "UPLOAD command failed"
                            _step_ok = False

                    elif step_kind == "call_python":
                        instruction = re.sub(r'^\s*\d+\.\s*', '', step).strip()
                        if re.match(r'CALL\s+PYTHON\b', instruction.upper()):
                            raw_instr = re.sub(r'^\s*\d+\.\s*', '', raw_step).strip()
                            result = execute_hook_line(raw_instr, variables=eng.memory)
                            if not result.success:
                                _step_error = result.message
                                _step_ok = False
                            elif result.var_name and result.return_value is not None:
                                eng.memory[result.var_name] = result.return_value
                        elif not await eng._execute_step(page, step):
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
                            eng.memory[_sv_name] = _sv_raw

                    elif step_kind == "done":
                        done = True

                    else:
                        if not await eng._execute_step(page, step):
                            _step_error = "Action failed"
                            _step_ok = False

                except Exception:
                    _step_ok = False
                    _step_error = __import__("traceback").format_exc()

                finally:
                    duration_ms = (time.perf_counter() - started_perf) * 1000
                    _sr_status = "pass" if _step_ok else (
                        "warning" if step_kind == "verify_softly" else "fail"
                    )
                    _step_result = StepResult(
                        index=action_index,
                        text=re.sub(r'^\s*\d+\.\s*', '', step),
                        status=_sr_status,
                        duration_ms=duration_ms,
                        error=_step_error,
                        logical_step=block.block_name,
                    )
                    _step_results.append(_step_result)
                    block_steps.append(_step_result)
                    if _sr_status == "fail":
                        ok = False
                        block_status = "fail"
                        block_error = _step_error
                    elif _sr_status == "warning" and block_status == "pass":
                        block_status = "warning"

                if block_status == "fail" or done:
                    break

            _block_results.append(BlockResult(
                name=block.block_name,
                status=block_status,
                duration_ms=(time.perf_counter() - block_started_perf) * 1000,
                error=block_error,
                actions=list(block_steps),
            ))
            if block_status == "fail" or done:
                break

        _status = "pass" if (done or ok) else "fail"
        if _status == "pass" and _soft_errors:
            _status = "warning"
        return MissionResult(
            file="",
            name="<api>",
            status=_status,
            steps=_step_results,
            blocks=_block_results,
            error=_step_results[-1].error if _step_results and _status == "fail" else None,
            soft_errors=_soft_errors,
        )
