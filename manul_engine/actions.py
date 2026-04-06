# manul_engine/actions.py
import asyncio
import hashlib
import os
import re
from typing import TYPE_CHECKING

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

if TYPE_CHECKING:
    from playwright.async_api import Page  # noqa: F401

from .helpers import (
    ACTION_WAIT,
    NAV_WAIT,
    SCROLL_WAIT,
    compact_log_field,
    detect_mode,
    extract_quoted,
    parse_contextual_hint,
    parse_explicit_wait,
    parse_verify_strict_assertion,
)
from .js_scripts import (
    DEEP_TEXT_JS,
    EXTRACT_DATA_JS,
    FILTER_CONTAINER_DESCENDANT_XPATHS_JS,
    FIND_CONTAINER_XPATH_JS,
    SCAN_JS,
    STATE_CHECK_JS,
    VISIBLE_TEXT_JS,
)
from .logging_config import logger

_log = logger.getChild("actions")

class _ActionsMixin:
    _EXPLICIT_WAIT_TIMEOUT_MS = 15_000

    def _fmt_el_name(self, name: object) -> str:
        return compact_log_field(name, "MANUL_LOG_NAME_MAXLEN")

    def _pick_near_anchor_candidate(self, scored_candidates: list[dict], anchor_text: str) -> dict | None:
        """Choose the most useful resolved anchor for a NEAR qualifier.

        Plain text anchors often appear multiple times in modern UIs: as an
        image alt text, as the visible title link, and sometimes as container
        text. For NEAR, a textual/title anchor is usually a better geometric
        reference than an image because neighbouring cards can place their CTA
        buttons closer to the image than the button inside the correct card.

        Strategy:
        - keep the highest-scoring candidates only;
        - among near-ties, prefer non-image candidates whose visible name still
          contains the requested anchor text;
        - otherwise fall back to the original top-ranked candidate.
        """
        if not scored_candidates:
            return None

        top = scored_candidates[0]
        top_score = int(top.get("score", 0) or 0)
        anchor_norm = str(anchor_text or "").strip().lower()
        shortlist = [
            el for el in scored_candidates[:8]
            if int(el.get("score", 0) or 0) >= max(0, top_score - 5_000)
        ]
        textual = [
            el for el in shortlist
            if str(el.get("tag_name", "") or "").lower() != "img"
            and anchor_norm in str(el.get("name", "") or "").lower()
        ]
        if textual:
            return max(
                textual,
                key=lambda el: (
                    int(el.get("score", 0) or 0),
                    str(el.get("tag_name", "") or "").lower() == "a",
                    str(el.get("tag_name", "") or "").lower() in {"a", "button", "label", "span", "div", "p", "h1", "h2", "h3"},
                ),
            )
        return top

    def _remember_resolved_control(
        self,
        *,
        page,
        cache_key: tuple,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        contextual_hint=None,
        element: dict,
    ) -> None:
        if getattr(self, '_semantic_cache_enabled', True):
            self.learned_elements[cache_key] = {
                "name": str(element.get("name", "")),
                "tag": str(element.get("tag_name", "")),
            }
        persist = getattr(self, "_persist_control_cache_entry", None)
        if callable(persist):
            try:
                persist(
                    page=page,
                    mode=mode,
                    search_texts=search_texts,
                    target_field=target_field,
                    contextual_hint=contextual_hint,
                    element=element,
                )
            except (OSError, ValueError, TypeError) as exc:
                print(f"    ⚠️  CONTROL CACHE: persist skipped ({type(exc).__name__})")

    async def _handle_navigate(self, page, step: str) -> bool:
        url = re.search(r'(https?://[^\s\'"<>]+)', step)
        if not url: return False
        await page.goto(url.group(1), wait_until="domcontentloaded", timeout=self.nav_timeout)
        self.last_xpath = None
        await asyncio.sleep(NAV_WAIT)
        return True

    async def _handle_open_app(self, page, ctx) -> "tuple[bool, object]":
        """Attach to an Electron/Desktop app's default window.

        Instead of navigating to a URL, waits for the application to open
        its first window, assigns that page, and waits for DOM settlement.
        Returns ``(success, resolved_page)``.
        """
        try:
            if ctx.pages:
                # Filter out initial about:blank pages created by ctx.new_page()
                real = [p for p in ctx.pages if getattr(p, "url", None) not in ("", "about:blank")]
                if real:
                    page = real[-1]
                elif len(ctx.pages) == 1:
                    page = await ctx.wait_for_event("page", timeout=self.nav_timeout)
                else:
                    page = ctx.pages[-1]
            else:
                page = await ctx.wait_for_event("page", timeout=self.nav_timeout)
            await page.wait_for_load_state("domcontentloaded", timeout=self.nav_timeout)
            self.last_xpath = None
            await asyncio.sleep(NAV_WAIT)
            print(f"    \U0001f4e6 Attached to app window: {page.url or '(no URL)'}")
            return True, page
        except Exception as exc:
            print(f"    \u274c OPEN APP failed: {exc}")
            return False, page

    async def _handle_scroll(self, page, step: str):
        step_l = step.lower()
        if "inside" in step_l or "list" in step_l:
            await page.evaluate("const d=document.querySelector('#dropdown')||document.querySelector('[class*=\"dropdown\"]');if(d)d.scrollTop=d.scrollHeight;")
        else:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(SCROLL_WAIT)

    async def _handle_wait_for_element(self, page, step: str) -> tuple[bool, str]:
        """Handle ``Wait for 'Target' to be visible/hidden/disappear``."""
        target_element, desired_state = parse_explicit_wait(step)
        if not target_element or not desired_state:
            return False, "Malformed explicit wait command"

        state_mapped = "hidden" if desired_state in ("hidden", "disappear") else "visible"
        locator = page.get_by_text(target_element, exact=False).first

        try:
            await locator.wait_for(state=state_mapped, timeout=self._EXPLICIT_WAIT_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            timeout_s = self._EXPLICIT_WAIT_TIMEOUT_MS // 1000
            return False, f"Timeout waiting {timeout_s}s for element to be {state_mapped}"
        except Exception as exc:
            return False, f"Explicit wait failed: {exc}"

        return True, f"Element is now {state_mapped}"

    async def _handle_press_enter(self, page) -> bool:
        """Press the Enter key on the currently focused element.

        Useful for submitting search forms or other inputs where no visible
        submit button is present. Always returns True — keyboard events do
        not produce a recoverable failure state.
        """
        await page.keyboard.press("Enter")
        await asyncio.sleep(ACTION_WAIT)
        print("    ↩️  Pressed Enter")
        return True

    async def _handle_press(self, page, step: str, strategic_context: str = "", step_idx: int = 0) -> bool:
        """Handle PRESS [Key] and PRESS [Key] on 'Target'.

        Global form: `PRESS Escape`, `PRESS Control+A`
        Targeted form: `PRESS ArrowDown on 'Search Input'`
        """
        # Strip leading step number
        clean = re.sub(r'^\s*\d+\.\s*', '', step).strip()
        # Remove the keyword PRESS (case-insensitive)
        after_press = re.sub(r'^PRESS\s*', '', clean, flags=re.IGNORECASE).strip()
        if not after_press:
            print("    ❌ PRESS: no key specified")
            return False

        # Check for targeted form: "Key on 'Target'"
        m_on = re.search(r'^(.+?)\s+on\s+(.+)$', after_press, re.IGNORECASE)
        if m_on:
            key_combo = m_on.group(1).strip()
            if not key_combo:
                print("    ❌ PRESS: no key specified before 'on'")
                return False
            # Target is in the remainder — resolve element then press on it
            el = await self._resolve_element(
                page, step, "locate",
                extract_quoted(step, preserve_case=False),
                None, strategic_context, failed_ids=set(),
            )
            if el is None:
                print("    ❌ PRESS: could not resolve target element")
                return False
            frame = self._frame_for(page, el)
            loc = frame.locator(f"xpath={el['xpath']}").first
            await loc.press(key_combo, timeout=self.timeout)
            print(f"    ⌨️  Pressed '{key_combo}' on '{self._fmt_el_name(el['name'])}'")
        else:
            key_combo = after_press
            await page.keyboard.press(key_combo)
            print(f"    ⌨️  Pressed '{key_combo}'")

        await asyncio.sleep(ACTION_WAIT)
        return True

    async def _handle_right_click(self, page, step: str, strategic_context: str = "", step_idx: int = 0) -> bool:
        """Handle RIGHT CLICK 'Target'.

        Resolves the target element via heuristics/LLM, then performs
        a right-click using ``locator.click(button='right')``.
        """
        el = await self._resolve_element(
            page, step, "clickable",
            extract_quoted(step, preserve_case=False),
            None, strategic_context, failed_ids=set(),
        )
        if el is None:
            print("    ❌ RIGHT CLICK: could not resolve target element")
            return False
        frame = self._frame_for(page, el)
        loc = frame.locator(f"xpath={el['xpath']}").first
        is_shad = el.get("is_shadow")
        try:
            if not is_shad:
                await loc.scroll_into_view_if_needed(timeout=2000)
                await self._highlight(page, loc)
            else:
                await self._highlight(page, el["id"], by_js_id=True, frame=frame)
        except Exception as exc:
            _log.debug("Right-click scroll/highlight failed: %s", exc)
        if is_shad:
            await frame.evaluate(
                f"window.manulElements[{el['id']}].dispatchEvent("
                f"new MouseEvent('contextmenu',{{bubbles:true,cancelable:true,button:2,view:window}}))"
            )
        else:
            await loc.click(button="right", force=True, timeout=self.timeout)
        print(f"    🖱️  Right-clicked '{self._fmt_el_name(el['name'])}'")
        await asyncio.sleep(ACTION_WAIT)
        return True

    async def _handle_upload(self, page, step: str, strategic_context: str = "",
                             step_idx: int = 0, hunt_dir: str | None = None) -> bool:
        """Handle UPLOAD 'file.pdf' to 'Target'.

        Resolves the file path relative to the hunt file's directory (or CWD)
        and the target element via heuristics, then calls ``set_input_files()``.
        """
        quoted = extract_quoted(step, preserve_case=True)
        if len(quoted) < 2:
            print("    ❌ UPLOAD: expected UPLOAD 'file' to 'Target'")
            return False
        file_path_raw = quoted[0]
        # Resolve file path relative to hunt dir, then CWD
        from pathlib import Path as _Path
        if hunt_dir:
            candidate = _Path(hunt_dir) / file_path_raw
            if candidate.exists():
                file_path = str(candidate.resolve())
            else:
                fallback = _Path.cwd() / file_path_raw
                if fallback.exists():
                    file_path = str(fallback.resolve())
                else:
                    print(f"    ❌ UPLOAD: file not found — tried '{candidate}' and '{fallback}'")
                    return False
        else:
            cwd_path = _Path.cwd() / file_path_raw
            if cwd_path.exists():
                file_path = str(cwd_path.resolve())
            else:
                print(f"    ❌ UPLOAD: file not found — tried '{cwd_path}'")
                return False

        search_texts = [quoted[1].lower()]
        el = await self._resolve_element(
            page, step, "clickable", search_texts,
            None, strategic_context, failed_ids=set(),
        )
        if el is None:
            print("    ❌ UPLOAD: could not resolve target element")
            return False
        frame = self._frame_for(page, el)
        loc = frame.locator(f"xpath={el['xpath']}").first
        try:
            if not el.get("is_shadow"):
                await loc.scroll_into_view_if_needed(timeout=2000)
                await self._highlight(page, loc)
            else:
                await self._highlight(page, el["id"], by_js_id=True, frame=frame)
        except Exception as exc:
            _log.debug("Upload scroll/highlight failed: %s", exc)
        tag = str(el.get("tag_name", "")).lower()
        itype = str(el.get("input_type", "")).lower()
        if tag == "label":
            linked_id = str(el.get("html_id", ""))
            if linked_id:
                linked_loc = frame.locator(f"#{linked_id}").first
                try:
                    linked_tag = await linked_loc.evaluate("e => e.tagName.toLowerCase()")
                    linked_type = await linked_loc.evaluate("e => (e.type || '').toLowerCase()")
                except Exception as exc:
                    _log.debug("Upload label introspection failed: %s", exc)
                    linked_tag, linked_type = "", ""
                if linked_tag == "input" and linked_type == "file":
                    loc = linked_loc
                    tag, itype = linked_tag, linked_type
                    print(f"    🏷️  UPLOAD: followed <label for='{linked_id}'> → <input type='file'>")
        if tag != "input" or itype != "file":
            print(f"    ❌ UPLOAD: resolved element is <{tag} type='{itype}'>, expected <input type='file'>")
            return False
        await loc.set_input_files(file_path, timeout=self.timeout)
        print(f"    📎 Uploaded '{file_path_raw}' → '{self._fmt_el_name(el['name'])}'")
        await asyncio.sleep(ACTION_WAIT)
        return True

    async def _handle_extract(self, page, step: str) -> bool:
        var_m  = re.search(r'\{(.*?)\}', step)
        target = (extract_quoted(step) or [""])[0].replace("'", "")
        print("    ⚙️  DOM HEURISTICS: Extracting data via JS…")

        step_lower = step.lower()
        hint = ""
        m_hint = re.search(r'extract\s+(.+?)\s+into\b', step_lower)
        if m_hint:
            raw = m_hint.group(1)
            raw = re.sub(r"'[^']*'", "", raw).strip()
            for w in ("the", "of", "from", "a", "an", "text", "value"):
                raw = re.sub(rf'\b{w}\b', '', raw).strip()
            hint = raw.strip()

        currency_hint = ""
        curr_m = re.search(r'([$€£₴¥₹])', step)
        if curr_m:
            currency_hint = curr_m.group(1)
        for cw, cs in [("uah", "UAH"), ("pln", "PLN"), ("eur", "€"), ("gbp", "£"), ("usd", "$")]:
            if cw in step_lower.split():
                currency_hint = cs
                break

        val = await page.evaluate(EXTRACT_DATA_JS, [target.lower(), hint, currency_hint])

        if val and var_m:
            val = val.strip()
            if hint and ':' in val:
                m_lbl = re.match(r'^([A-Za-z][A-Za-z0-9 ]+?)\s*:\s+(.+)$', val)
                if m_lbl:
                    label_part = m_lbl.group(1).lower()
                    value_part = m_lbl.group(2).strip()
                    hint_ws = set(re.findall(r'[a-z]{3,}', hint.lower()))
                    label_ws = set(re.findall(r'[a-z]{3,}', label_part))
                    if hint_ws & label_ws:
                        val = value_part

            self.memory[var_m.group(1)] = val
            print(f"    📦 COLLECTED: {val}")
            return True
        return False

    @staticmethod
    def _strict_verify_mode_for(element_type: str) -> str:
        if element_type == "button":
            return "clickable"
        if element_type in ("field", "input"):
            return "input"
        return "locate"

    def _strict_verify_failure(self, *, kind: str, locator_text: str, expected: object, actual: object) -> AssertionError:
        if kind == "text":
            label = "text"
        elif kind == "placeholder":
            label = "placeholder"
        else:
            label = "value"
        return AssertionError(
            f"Strict {label} verification failed\n"
            f"Element locator: {locator_text}\n"
            f"Expected: {expected!r}\n"
            f"Actual: {actual!r}"
        )

    async def _resolve_strict_verify_locator(self, page, step: str, target: str, element_type: str, kind: str):
        mode = self._strict_verify_mode_for(element_type)
        target_field = target.lower() if element_type in ("field", "input") else None
        el = await self._resolve_element(
            page,
            step,
            mode,
            [target],
            target_field,
            "",
            failed_ids=set(),
        )
        if el is None:
            locator_text = f"{element_type} '{target}'"
            raise self._strict_verify_failure(
                kind=kind,
                locator_text=locator_text,
                expected="<resolved element>",
                actual="<element not found>",
            )

        frame = self._frame_for(page, el)
        loc = frame.locator(f"xpath={el['xpath']}").first
        locator_text = f"{element_type} '{target}' -> xpath={el['xpath']}"
        return loc, locator_text

    async def _execute_verify_text(self, page, step: str, target: str, element_type: str, expected_text: str) -> bool:
        loc, locator_text = await self._resolve_strict_verify_locator(page, step, target, element_type, "text")
        actual_text = (await loc.inner_text(timeout=2000)).strip()
        if actual_text != expected_text:
            raise self._strict_verify_failure(
                kind="text",
                locator_text=locator_text,
                expected=expected_text,
                actual=actual_text,
            )
        print(f"    ✅ Strict text verified for {locator_text}")
        return True

    async def _execute_verify_placeholder(self, page, step: str, target: str, element_type: str, expected_placeholder: str) -> bool:
        loc, locator_text = await self._resolve_strict_verify_locator(page, step, target, element_type, "placeholder")
        actual_placeholder = await loc.get_attribute("placeholder", timeout=2000)
        if actual_placeholder != expected_placeholder:
            raise self._strict_verify_failure(
                kind="placeholder",
                locator_text=locator_text,
                expected=expected_placeholder,
                actual=actual_placeholder,
            )
        print(f"    ✅ Strict placeholder verified for {locator_text}")
        return True

    async def _execute_verify_value(self, page, step: str, target: str, element_type: str, expected_value: str) -> bool:
        loc, locator_text = await self._resolve_strict_verify_locator(page, step, target, element_type, "value")
        try:
            actual_value = await loc.input_value(timeout=2000)
        except Exception as exc:
            _log.debug("input_value() failed, falling back to get_attribute: %s", exc)
            actual_value = await loc.get_attribute("value", timeout=2000)
        if actual_value is None:
            actual_value = ""
        if actual_value != expected_value:
            raise self._strict_verify_failure(
                kind="value",
                locator_text=locator_text,
                expected=expected_value,
                actual=actual_value,
            )
        print(f"    ✅ Strict value verified for {locator_text}")
        return True

    # ── Verify retry helpers ────────────────────────────────────────────────

    @property
    def _VERIFY_MAX_RETRIES(self) -> int:
        return self._verify_max_retries

    async def _verify_checked(self, page, step: str, expected: list[str],
                               is_negative: bool, _in_debug: bool, step_idx: int) -> bool:
        """Retry loop for VERIFY ... checked / NOT checked."""
        _debug_paused = False
        for retry in range(self._VERIFY_MAX_RETRIES):
            raw_els = await self._snapshot(page, "clickable", [t.lower() for t in expected])
            scored  = self._score_elements(raw_els, step, "clickable", expected, None, False)
            if scored:
                best   = scored[0]
                xpath  = best["xpath"]
                _cf    = self._frame_for(page, best)
                loc    = _cf.locator(f"xpath={xpath}").first
                if _in_debug and not _debug_paused:
                    try:
                        if not best.get("is_shadow"):
                            await loc.scroll_into_view_if_needed(timeout=2000)
                            await self._debug_highlight(page, loc)
                        else:
                            await self._debug_highlight(page, best["id"], by_js_id=True, frame=_cf)
                    except Exception as exc:
                        _log.debug("Verify-checked scroll/highlight failed: %s", exc)
                    await self._debug_prompt(page, step, step_idx)
                    await self._clear_debug_highlight(page)
                    _debug_paused = True
                try: checked = await loc.is_checked(timeout=2000)
                except Exception as exc:
                    _log.debug("is_checked() not supported on element: %s", exc)
                    checked = None  # not a checkable element — retry
                if checked is None:
                    pass  # unresolved/invalid target — fall through to retry
                elif is_negative:
                    ok = not checked
                    if ok:
                        print(f"    {'✅' if ok else '❌'} Checkbox not-checked={ok}")
                        return ok
                else:
                    if checked:
                        print(f"    {'✅' if checked else '❌'} Checkbox checked={checked}")
                        return checked
            if retry < self._VERIFY_MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
            return False
        return False

    async def _verify_state(self, page, step: str, expected: list[str],
                             state_check: str) -> bool:
        """Retry loop for VERIFY ... ENABLED / DISABLED."""
        search_text = expected[0] if expected else ""
        for retry in range(self._VERIFY_MAX_RETRIES):
            disabled_result = await page.evaluate(STATE_CHECK_JS, [search_text, state_check])
            if disabled_result is True:
                print(f"    ✅ Element {state_check}=True")
                return True
            if disabled_result is False:
                print(f"    ❌ Element {state_check}=False")
            if retry < self._VERIFY_MAX_RETRIES - 1:
                await asyncio.sleep(1)
                continue
            return False
        return False

    async def _verify_text_presence(self, page, expected: list[str],
                                     is_negative: bool) -> bool:
        """Retry loop for VERIFY that 'text' is present / is NOT present."""
        for retry in range(self._VERIFY_MAX_RETRIES):
            text = await page.evaluate(VISIBLE_TEXT_JS)
            found = all(t.lower() in text for t in expected) if expected else bool(text)

            if not found and not is_negative:
                text2 = await page.evaluate(DEEP_TEXT_JS)
                found = all(t.lower() in text2 for t in expected) if expected else bool(text2)

            if is_negative:
                if not found:
                    print("    ✅ Verified ABSENT — OK")
                    return True
                if retry < self._VERIFY_MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                    continue
                print("    ❌ Text still present after retries")
                return False
            else:
                if found:
                    print("    ✅ Verified — OK")
                    return True
                if retry < self._VERIFY_MAX_RETRIES - 1:
                    await asyncio.sleep(1.5)
                    continue
                print(f"    ❌ Not found after retries: {expected}")
                return False
        return False

    async def _handle_verify(self, page, step: str, step_idx: int = 0) -> bool:
        strict_verify = parse_verify_strict_assertion(step)
        if strict_verify is not None:
            if strict_verify.kind == "text":
                return await self._execute_verify_text(
                    page,
                    step,
                    strict_verify.target,
                    strict_verify.element_type,
                    strict_verify.expected,
                )
            if strict_verify.kind == "value":
                return await self._execute_verify_value(
                    page,
                    step,
                    strict_verify.target,
                    strict_verify.element_type,
                    strict_verify.expected,
                )
            return await self._execute_verify_placeholder(
                page,
                step,
                strict_verify.target,
                strict_verify.element_type,
                strict_verify.expected,
            )

        expected = extract_quoted(step)
        step_no_quotes = re.sub(r"'[^']*'", "", step)
        is_negative = bool(re.search(r'\b(NOT|HIDDEN|ABSENT)\b', step_no_quotes.upper()))
        state_check = "disabled" if re.search(r'\bDISABLED\b', step.upper()) else "enabled" if re.search(r'\bENABLED\b', step.upper()) else None
        is_checked_verify = bool(re.search(r'\bchecked\b', step.lower()))
        _in_debug = getattr(self, "debug_mode", False) or step_idx in getattr(self, "break_steps", set())

        msg = f"    ⚙️  DOM HEURISTICS: Scanning for {expected}"
        if is_negative: msg += " [MUST BE ABSENT]"
        if state_check: msg += f" [{state_check.upper()}]"
        if is_checked_verify: msg += " [CHECKED]"
        print(msg)

        # ── Debug pause before verify ─────────────────────────────────────
        if _in_debug and not is_checked_verify:
            if expected:
                if state_check:
                    raw_els = await self._snapshot(page, "clickable", [t.lower() for t in expected])
                    scored  = self._score_elements(raw_els, step, "clickable", expected, None, False)
                    if scored:
                        best = scored[0]
                        _vf = self._frame_for(page, best)
                        loc  = _vf.locator(f"xpath={best['xpath']}").first
                        try:
                            if not best.get("is_shadow"):
                                await loc.scroll_into_view_if_needed(timeout=2000)
                                await self._debug_highlight(page, loc)
                            else:
                                await self._debug_highlight(page, best["id"], by_js_id=True, frame=_vf)
                        except Exception as exc:
                            _log.debug("Verify state scroll/highlight failed: %s", exc)
                else:
                    for t in expected:
                        try:
                            loc = page.get_by_text(t, exact=False).first
                            await loc.scroll_into_view_if_needed(timeout=2000)
                            await self._debug_highlight(page, loc)
                            break
                        except Exception as exc:
                            _log.debug("Verify text scroll/highlight failed for '%s': %s", t, exc)
            await self._debug_prompt(page, step, step_idx)
            await self._clear_debug_highlight(page)

        # ── Dispatch to specialised retry helpers ─────────────────────────
        if is_checked_verify:
            return await self._verify_checked(page, step, expected, is_negative, _in_debug, step_idx)
        if state_check:
            return await self._verify_state(page, step, expected, state_check)
        return await self._verify_text_presence(page, expected, is_negative)

    async def _do_drag(self, page, step: str, expected: list[str], source_el: dict) -> bool:
        step_l = step.lower()
        target_text = ""
        m_to = re.search(r"to\s+['\"](.+?)['\"]", step_l)
        if m_to: target_text = m_to.group(1)
        elif len(expected) >= 2: target_text = expected[-1]

        _src_key = (source_el.get("frame_index", 0), source_el["id"])
        raw_els = await self._snapshot(page, "drag", [target_text])
        dest = next((el for el in raw_els if (el.get("frame_index", 0), el["id"]) != _src_key and target_text.lower() in el["name"].lower()), None)
        if not dest: return False

        src_snap = next((el for el in raw_els if (el.get("frame_index", 0), el["id"]) == _src_key), raw_els[0])
        src_frame  = self._frame_for(page, src_snap)
        dest_frame = self._frame_for(page, dest)
        src_loc  = src_frame.locator(f"xpath={src_snap['xpath']}").first
        dest_loc = dest_frame.locator(f"xpath={dest['xpath']}").first

        try:
            await src_loc.drag_to(dest_loc, timeout=5000)
        except Exception as exc:
            _log.debug("drag_to() failed, falling back to mouse move: %s", exc)
            sb = await src_loc.bounding_box()
            db = await dest_loc.bounding_box()
            if sb and db:
                await page.mouse.move(sb["x"] + sb["width"]/2, sb["y"] + sb["height"]/2)
                await page.mouse.down()
                await asyncio.sleep(0.3)
                await page.mouse.move(db["x"] + db["width"]/2, db["y"] + db["height"]/2, steps=20)
                await page.mouse.up()

        print(f"    🖱️  Dragged → '{self._fmt_el_name(dest.get('name', ''))}'")
        await asyncio.sleep(ACTION_WAIT)
        return True

    async def _execute_step(self, page, step: str, strategic_context: str = "", step_idx: int = 0) -> bool:
        # ── Parse contextual proximity hint (NEAR / ON HEADER / ON FOOTER / INSIDE) ──
        ctx_hint, cleaned_step = parse_contextual_hint(step)

        step_l = cleaned_step.lower()
        mode   = detect_mode(cleaned_step)

        preserve = mode in ("input", "select")
        expected = extract_quoted(cleaned_step, preserve_case=preserve)

        target_field = None
        txt_to_type  = ""
        search_texts = []

        if mode == "input" and expected:
            # Determine value vs target order from DSL structure:
            #   "Type 'VALUE' into 'TARGET'"  — 'into' comes AFTER first quoted → value is first
            #   "Fill 'TARGET' field with 'VALUE'" — 'with' comes AFTER first quoted → value is last
            # Detect 'into' only in the unquoted DSL structure so quoted values like
            # "Fill 'Notes' field with 'go into settings'" do not flip target/value order.
            # "Fill ... with" and bare "enter" treat last quoted as value (original behaviour).
            step_l_unquoted = re.sub(r"""(['"])(?:\\.|(?!\1).)*\1""", " ", step_l)
            if re.search(r"\binto\b", step_l_unquoted):
                txt_to_type  = expected[0]   # value is first
                search_texts = expected[1:]  # remaining quoted strings are the target
            else:
                txt_to_type  = expected[-1]  # Fill/generic: value is last
                search_texts = expected[:-1]
            m = re.search(r'(?:into\s+the\s+|into\s+)([a-zA-Z0-9_]+)\s*field', step_l)
            if m and m.group(1) not in ("that", "the", "a", "an"): target_field = m.group(1).lower()
        else:
            search_texts = expected

        if search_texts or target_field:
            self.last_xpath = None

        # ── Resolve contextual anchor / container ────────────────────────
        anchor_rect: dict | None = None
        container_elements: list[dict] | None = None
        viewport_height: int = 0

        if ctx_hint.kind == "near" and ctx_hint.anchor:
            anchor_search_texts = [ctx_hint.anchor.lower()]
            anchor_candidates = await self._snapshot(page, "locate", anchor_search_texts)
            scored_anchor_candidates = self._score_elements(
                anchor_candidates,
                f"Locate {ctx_hint.anchor}",
                "locate",
                anchor_search_texts,
                None,
                False,
            ) if anchor_candidates else []
            anchor_el = self._pick_near_anchor_candidate(scored_anchor_candidates, ctx_hint.anchor)
            if anchor_el:
                anchor_rect = {
                    "rect_top": anchor_el.get("rect_top", 0),
                    "rect_left": anchor_el.get("rect_left", 0),
                    "rect_bottom": anchor_el.get("rect_bottom", 0),
                    "rect_right": anchor_el.get("rect_right", 0),
                    "frame_index": anchor_el.get("frame_index", 0),
                    "xpath": anchor_el.get("xpath", ""),
                }
                print(f"    📐 NEAR anchor: '{self._fmt_el_name(ctx_hint.anchor)}' at ({anchor_rect['rect_left']}, {anchor_rect['rect_top']})")

        elif ctx_hint.kind == "inside" and ctx_hint.row_text:
            # Resolve the row-identifying text, find its container, then
            # snapshot all elements inside that container's xpath subtree.
            row_el = await self._resolve_element(
                page, f"Locate {ctx_hint.row_text}", "locate",
                [ctx_hint.row_text.lower()], None, strategic_context,
            )
            if row_el:
                row_xpath = row_el.get("xpath", "")
                # Walk up to find the container row (tr, li, div[role=row], or any table row ancestor).
                container_xpath = await self._frame_for(page, row_el).evaluate(
                    FIND_CONTAINER_XPATH_JS,
                    row_xpath,
                )
                if container_xpath:
                    # Re-snapshot and keep only real DOM descendants of the resolved
                    # container. Prefix checks on snapshot xpaths are brittle because
                    # SNAPSHOT_JS may emit id-based xpaths like //*[@id="..."] for
                    # descendants, which do not share the container's absolute prefix.
                    all_els = await self._snapshot(page, mode, [t.lower() for t in search_texts])
                    container_frame_index = row_el.get("frame_index", 0)
                    frame_candidates = [
                        e for e in all_els
                        if e.get("frame_index", 0) == container_frame_index and e.get("xpath")
                    ]
                    candidate_xpaths = list(dict.fromkeys(
                        str(e.get("xpath", "")) for e in frame_candidates if e.get("xpath")
                    ))
                    try:
                        contained_xpaths = await self._frame_for(page, row_el).evaluate(
                            FILTER_CONTAINER_DESCENDANT_XPATHS_JS,
                            {
                                "containerXPath": container_xpath,
                                "candidateXPaths": candidate_xpaths,
                            },
                        )
                        contained_xpath_set = set(contained_xpaths or [])
                        container_elements = [
                            e for e in frame_candidates
                            if e.get("xpath", "") in contained_xpath_set
                        ]
                    except Exception as exc:
                        _log.debug("INSIDE JS containment check failed, using prefix fallback: %s", exc)
                        container_elements = [
                            e for e in frame_candidates
                            if e.get("xpath", "").startswith(container_xpath)
                        ]
                    print(f"    📦 INSIDE container: {len(container_elements)} elements in row containing '{ctx_hint.row_text}'")

        if ctx_hint.kind in ("on_header", "on_footer"):
            try:
                viewport_height = await page.evaluate("() => window.innerHeight || document.documentElement.clientHeight || 900")
            except Exception as exc:
                _log.debug("Viewport height query failed, using default: %s", exc)
                viewport_height = 900
            print(f"    🏷️  {ctx_hint.kind.upper().replace('_', ' ')}: viewport height = {viewport_height}px")

        is_optional = bool(re.search(r'\bif\s+exists\b|\boptional\b', re.sub(r'''["'][^"']*["']''', '', step_l)))
        context_qualifier = None
        if ctx_hint.kind:
            context_qualifier = (
                ctx_hint.kind,
                str(ctx_hint.anchor or "").lower().strip() or None,
                str(ctx_hint.row_text or "").lower().strip() or None,
            )
        cache_key = (mode, tuple(t.lower() for t in search_texts), target_field, context_qualifier)
        failed_ids = set()

        for attempt in range(3):
            try:
                el = await self._resolve_element(
                    page, cleaned_step, mode, search_texts, target_field, strategic_context,
                    failed_ids=failed_ids,
                    contextual_hint=ctx_hint,
                    anchor_rect=anchor_rect,
                    container_elements=container_elements,
                    viewport_height=viewport_height,
                )
            except Exception as exc:
                _log.debug("_resolve_element failed for optional step: %s", exc)
                if is_optional: return True
                raise

            if el is None:
                if is_optional: return True
                if attempt < 2:
                    print("    🔄 Target not found or rejected by AI. Scrolling and retrying...")
                    await page.evaluate("window.scrollBy(0, window.innerHeight / 2)")
                    await asyncio.sleep(1)
                    continue
                else:
                    if mode != "locate":
                        print("    💀 SELF-HEALING FAILED: No valid elements found after retries.")
                    return False

            _ek = (el.get("frame_index", 0), el["id"])
            if _ek in failed_ids: continue

            self.last_xpath = el["xpath"]
            name, xpath, is_sel, is_shad, el_id, tag, itype = el["name"], el["xpath"], el.get("is_select"), el.get("is_shadow"), el["id"], el.get("tag_name", ""), el.get("input_type", "")
            frame = self._frame_for(page, el)

            if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
                failed_ids.add(_ek)
                self.last_xpath = None
                continue

            if mode == "locate":
                try:
                    loc = frame.locator(f"xpath={xpath}").first
                    if not is_shad:
                        await loc.scroll_into_view_if_needed(timeout=2000)
                        await self._highlight(page, loc)
                    else:
                        await self._highlight(page, el_id, by_js_id=True, frame=frame)
                except Exception as exc:
                    _log.debug("Locate scroll/highlight failed: %s", exc)
                print(f"    🔍 Located '{self._fmt_el_name(name)}'")
                return True

            if mode == "drag": return await self._do_drag(page, step, expected, el)

            loc = frame.locator(f"xpath={xpath}").first
            _in_debug = getattr(self, "debug_mode", False) or step_idx in getattr(self, "break_steps", set())
            try:
                if not is_shad:
                    await loc.scroll_into_view_if_needed(timeout=2000)
                    await self._highlight(page, loc)
                else:
                    await self._highlight(page, el_id, by_js_id=True, frame=frame)
                if _in_debug:
                    if not is_shad:
                        await self._debug_highlight(page, loc)
                    else:
                        await self._debug_highlight(page, el_id, by_js_id=True, frame=frame)
            except Exception as exc:
                _log.debug("Scroll/highlight/debug-highlight failed: %s", exc)

            if _in_debug:
                await self._debug_prompt(page, step, step_idx)
                await self._clear_debug_highlight(page)

            try:
                if mode == "input":
                    print(f"    ⌨️  Typed '{txt_to_type}' → '{self._fmt_el_name(name)}'")
                    if is_shad: await frame.evaluate("([id, val]) => window.manulType(id, val)", [el_id, txt_to_type])
                    else:
                        is_readonly = await loc.evaluate("el => el.readOnly || el.hasAttribute('readonly')")
                        if is_readonly:
                            await loc.evaluate("(el, val) => { el.removeAttribute('readonly'); el.value = val; el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }", txt_to_type)
                        else:
                            await loc.fill("", timeout=3000)
                            await loc.type(txt_to_type, delay=50, timeout=3000)
                    if "enter" in step_l:
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(4)
                    self.last_xpath = None

                elif mode == "select":
                    if is_sel:
                        if expected:
                            opts = [expected[0]]
                        else:
                            _tokens = list(dict.fromkeys(re.findall(r'\b[a-z0-9]{3,}\b', step_l)))
                            if not _tokens:
                                raise ValueError(
                                    "Native <select> step could not infer an option from the step text; "
                                    "provide an explicit expected option in quotes."
                                )
                            opts = [_tokens[0]]
                        try: await loc.select_option(label=opts, timeout=3000)
                        except Exception as exc:
                            _log.debug("select_option(label=) failed, trying value: %s", exc)
                            await loc.select_option(value=[o.lower() for o in opts], timeout=3000)
                    else:
                        print(f"    🖱️  Clicked (Custom Select) '{self._fmt_el_name(name)}'")
                        try:
                            await loc.click(force=True, timeout=3000)
                        except Exception as exc:
                            _log.debug("Custom select click failed, using JS fallback: %s", exc)
                            await frame.evaluate("id => window.manulClick(id)", el_id)

                        if expected:
                            await asyncio.sleep(0.5)
                            option_text = expected[0]
                            print(f"    🖱️  Selecting option '{option_text}'")
                            try:
                                opt_loc = frame.locator(f"[role='option']:has-text('{option_text}'), [role='menuitem']:has-text('{option_text}')").first
                                await opt_loc.click(timeout=3000)
                            except Exception:
                                try:
                                    opt_loc = frame.locator(f"text='{option_text}'").last
                                    await opt_loc.click(timeout=3000)
                                except Exception as exc2:
                                    _log.debug("Option click fallback also failed: %s", exc2)
                    await asyncio.sleep(ACTION_WAIT)

                elif mode == "hover":
                    print(f"    🚁  Hovered '{self._fmt_el_name(name)}'")
                    if is_shad: await frame.evaluate("id => window.manulElements[id].dispatchEvent(new MouseEvent('mouseover',{bubbles:true,cancelable:true,view:window}))", el_id)
                    else: await loc.hover(force=True, timeout=3000)
                    await asyncio.sleep(ACTION_WAIT)

                else:
                    print(f"    🖱️  Clicked '{self._fmt_el_name(name)}'")
                    if is_shad:
                        fn = "manulDoubleClick" if "double" in step_l else "manulClick"
                        await frame.evaluate(f"id => window.{fn}(id)", el_id)
                    else:
                        if "double" in step_l:
                            await loc.dblclick(force=True, timeout=3000)
                        elif itype in ("checkbox", "radio", "file"):
                            await loc.evaluate("el => el.click()")
                        else:
                            await loc.click(force=True, timeout=3000)
                            if itype == "submit" or (tag == "button" and itype in ("", "submit")):
                                try: await page.wait_for_load_state("networkidle", timeout=10_000)
                                except PlaywrightTimeoutError: await asyncio.sleep(3.0)
                    await asyncio.sleep(ACTION_WAIT)

                # ── Common post-action: cache resolved control ────────────
                self._remember_resolved_control(
                    page=page,
                    cache_key=cache_key,
                    mode=mode,
                    search_texts=search_texts,
                    target_field=target_field,
                    contextual_hint=ctx_hint,
                    element=el,
                )
                return True

            except Exception:
                print(f"    ⚠️  Element not actionable (attempt {attempt+1}/3), trying next candidate...")
                failed_ids.add(_ek)
                self.last_xpath = None
                await asyncio.sleep(1)

        return False

    # ── SCAN PAGE ─────────────────────────────────────────────────────────────

    async def _handle_scan_page(self, page, step: str) -> bool:
        """
        Handle:  SCAN PAGE                   → print draft steps to console
                 SCAN PAGE into {filename}   → also write to file
        """
        import json
        import os

        from .scanner import build_hunt

        # Detect optional output filename: "into {filename}" or "into 'filename'"
        m = re.search(r'\binto\s+[\{\'"]?([\w./\\-]+\.hunt)[\}\'"]?', step, re.IGNORECASE)
        output_file = m.group(1) if m else None

        print("    🔍 SCAN PAGE: collecting interactive elements …")
        try:
            raw = await page.evaluate(SCAN_JS)
            elements = json.loads(raw)
        except Exception as exc:
            print(f"    ❌ SCAN PAGE: JS evaluation failed: {exc}")
            return False

        print(f"    📊 SCAN PAGE: found {len(elements)} element(s) before filter/dedup")

        url = page.url
        hunt_text = build_hunt(url, elements)

        # Always print to console
        print("\n" + "─" * 60)
        print(hunt_text)
        print("─" * 60)

        if output_file:
            from .scanner import _default_output
            # Bare filename → resolve via tests_home from config; path with dir → resolve from CWD.
            # Check both / and \ so Windows-style paths work on POSIX too.
            if "/" in output_file or "\\" in output_file:
                output_abs = os.path.abspath(output_file)
            else:
                output_abs = _default_output(output_file)
            try:
                os.makedirs(os.path.dirname(output_abs) or ".", exist_ok=True)
                with open(output_abs, "w", encoding="utf-8") as fh:
                    fh.write(hunt_text)
                print(f"    ✅ SCAN PAGE: draft saved → {output_abs}")
            except OSError as exc:
                print(f"    ⚠️  SCAN PAGE: could not write '{output_abs}': {exc}")
        return True

    # ── MOCK GET/POST/… handler ───────────────────────────────────────────────
    async def _handle_mock(self, page, step: str, hunt_dir: str | None = None) -> bool:
        """Handle ``MOCK GET "/api/path" with 'mocks/data.json'``.

        Uses Playwright ``page.route()`` to intercept matching requests and
        fulfill them with the content of a local JSON file.
        """
        m = re.match(
            r'^\s*(?:\d+\.\s*)?MOCK\s+(GET|POST|PUT|PATCH|DELETE)\s+'
            r'["\']([^"\']+)["\']\s+with\s+["\']([^"\']+)["\']',
            step, re.IGNORECASE,
        )
        if not m:
            print("    ❌ MOCK: invalid syntax — expected MOCK <METHOD> \"<path>\" with '<file>'")
            return False

        method = m.group(1).upper()
        url_pattern = m.group(2)
        mock_file = m.group(3)

        # Resolve mock file path: hunt dir → CWD
        candidates = []
        if hunt_dir:
            candidates.append(os.path.join(hunt_dir, mock_file))
        candidates.append(os.path.join(os.getcwd(), mock_file))
        resolved: str | None = None
        for c in candidates:
            if os.path.isfile(c):
                resolved = c
                break
        if resolved is None:
            print(f"    ❌ MOCK: file not found: {mock_file}")
            return False

        try:
            with open(resolved, encoding="utf-8") as f:
                body = f.read()
        except (OSError, UnicodeError) as e:
            print(f"    ❌ MOCK: failed to read mock file {mock_file}: {e}")
            return False
        # Detect content type
        content_type = "application/json" if resolved.endswith(".json") else "text/plain"

        # Maintain a single Playwright route handler per URL pattern so that
        # multiple MOCK steps for the same path but different methods coexist.
        pattern_key = f"**{url_pattern}"
        mock_routes: dict = getattr(page, "_manul_mock_routes", None) or {}
        if not hasattr(page, "_manul_mock_routes"):
            page._manul_mock_routes = mock_routes

        if pattern_key not in mock_routes:
            mock_routes[pattern_key] = {}

            async def _route_handler(route, _pk=pattern_key):
                routes = getattr(page, "_manul_mock_routes", {})
                method_map = routes.get(_pk, {})
                mock = method_map.get(route.request.method.upper())
                if mock:
                    await route.fulfill(status=200, content_type=mock[0], body=mock[1])
                else:
                    await route.continue_()

            await page.route(pattern_key, _route_handler)

        mock_routes[pattern_key][method] = (content_type, body)
        print(f"    🔀 MOCK {method} *{url_pattern} → {mock_file}")
        return True

    # ── WAIT FOR RESPONSE handler ─────────────────────────────────────────────
    async def _handle_wait_for_response(self, page, step: str) -> bool:
        """Handle ``WAIT FOR RESPONSE "/api/path"``.

        Uses Playwright ``page.wait_for_response()`` with a wildcard match.
        """
        m = re.search(r'WAIT\s+FOR\s+RESPONSE\s+["\']([^"\']+)["\']', step, re.IGNORECASE)
        if not m:
            print("    ❌ WAIT FOR RESPONSE: no URL pattern found")
            return False

        url_pattern = m.group(1)
        timeout_ms = self.nav_timeout  # reuse navigation timeout

        print(f"    ⏳ Waiting for response matching *{url_pattern}...")
        try:
            await page.wait_for_response(
                lambda resp: url_pattern in resp.url,
                timeout=timeout_ms,
            )
            print(f"    ✅ Response received for *{url_pattern}")
            return True
        except Exception as exc:
            print(f"    ❌ WAIT FOR RESPONSE timed out: {exc}")
            return False

    # ── VERIFY VISUAL handler ─────────────────────────────────────────────────
    async def _handle_verify_visual(self, page, step: str, strategic_context: str = "",
                                     step_idx: int = 0, hunt_dir: str | None = None) -> bool:
        """Handle ``VERIFY VISUAL 'Element Name'``.

        Takes an element screenshot and compares it against a baseline in
        ``visual_baselines/``. If no baseline exists, saves it and passes.
        Uses pixel comparison with a configurable threshold.
        """
        expected = extract_quoted(step)
        if not expected:
            print("    ❌ VERIFY VISUAL: no element name specified in quotes")
            return False

        target_name = expected[0]
        # Resolve element via heuristics
        el = await self._resolve_element(
            page, step, "locate",
            [t.lower() for t in expected],
            None, strategic_context, failed_ids=set(),
        )
        if el is None:
            print(f"    ❌ VERIFY VISUAL: could not find element '{target_name}'")
            return False

        frame = self._frame_for(page, el)
        loc = frame.locator(f"xpath={el['xpath']}").first

        # Take element screenshot
        try:
            screenshot_bytes = await loc.screenshot(type="png")
        except Exception as exc:
            print(f"    ❌ VERIFY VISUAL: screenshot failed: {exc}")
            return False

        # Determine baseline directory and filename
        baseline_dir = os.path.join(hunt_dir or os.getcwd(), "visual_baselines")
        os.makedirs(baseline_dir, exist_ok=True)
        # Sanitise element name for filename; include step hash to avoid collisions
        safe_name = re.sub(r'[^\w\-]', '_', target_name.lower()).strip('_')
        hash_suffix = hashlib.sha1(step.encode('utf-8')).hexdigest()[:8]
        baseline_path = os.path.join(baseline_dir, f"{safe_name}_{hash_suffix}.png")

        if not os.path.exists(baseline_path):
            # First run — save baseline and pass
            with open(baseline_path, "wb") as f:
                f.write(screenshot_bytes)
            print(f"    📸 VERIFY VISUAL: baseline saved → {baseline_path}")
            return True

        # Compare against baseline
        return self._compare_images(baseline_path, screenshot_bytes, target_name)

    @staticmethod
    def _compare_images(baseline_path: str, actual_bytes: bytes, label: str,
                        threshold: float = 0.01) -> bool:
        """Compare a baseline PNG with actual screenshot bytes.

        Uses PIL if available, falls back to raw byte comparison.
        Returns True if images match within threshold.
        """
        try:
            import io

            from PIL import Image, ImageChops  # type: ignore
            baseline_img = Image.open(baseline_path).convert("RGBA")
            actual_img = Image.open(io.BytesIO(actual_bytes)).convert("RGBA")

            if baseline_img.size != actual_img.size:
                print(f"    ❌ VERIFY VISUAL '{label}': size mismatch "
                      f"(baseline={baseline_img.size}, actual={actual_img.size})")
                return False

            diff = ImageChops.difference(baseline_img, actual_img)
            # Calculate the fraction of differing pixels
            diff_data = diff.getdata()
            total_pixels = len(diff_data)
            diff_pixels = sum(1 for px in diff_data if sum(px) > 0)
            diff_ratio = diff_pixels / total_pixels if total_pixels else 0

            if diff_ratio > threshold:
                print(f"    ❌ VERIFY VISUAL '{label}': {diff_ratio:.2%} pixels differ "
                      f"(threshold: {threshold:.2%})")
                return False

            print(f"    ✅ VERIFY VISUAL '{label}': match ({diff_ratio:.2%} diff)")
            return True
        except ImportError:
            # PIL not available — fall back to raw byte comparison
            with open(baseline_path, "rb") as f:
                baseline_bytes = f.read()
            if baseline_bytes == actual_bytes:
                print(f"    ✅ VERIFY VISUAL '{label}': exact byte match")
                return True
            else:
                print(f"    ❌ VERIFY VISUAL '{label}': bytes differ (install Pillow for threshold comparison)")
                return False

    # ── VERIFY SOFTLY handler ─────────────────────────────────────────────────
    async def _handle_verify_softly(self, page, step: str, step_idx: int = 0) -> bool:
        """Handle ``VERIFY SOFTLY that 'Element' is present/absent/enabled/disabled``.

        Delegates to ``_handle_verify`` but strips the ``SOFTLY`` keyword first.
        Returns the verification result without raising or breaking.
        """
        # Transform "VERIFY SOFTLY that ..." → "VERIFY that ..."
        clean_step = re.sub(r'\bVERIFY\s+SOFTLY\b', 'VERIFY', step, flags=re.IGNORECASE)
        return await self._handle_verify(page, clean_step, step_idx=step_idx)
