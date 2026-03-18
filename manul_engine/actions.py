# manul_engine/actions.py
import asyncio
import hashlib
import os
import re
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .helpers import extract_quoted, compact_log_field, SCROLL_WAIT, ACTION_WAIT, NAV_WAIT, detect_mode, parse_explicit_wait
from .js_scripts import VISIBLE_TEXT_JS, EXTRACT_DATA_JS, DEEP_TEXT_JS, STATE_CHECK_JS, SCAN_JS
from . import prompts

class _ActionsMixin:
    _EXPLICIT_WAIT_TIMEOUT_MS = 15_000

    def _fmt_el_name(self, name: object) -> str:
        return compact_log_field(name, "MANUL_LOG_NAME_MAXLEN")

    def _remember_resolved_control(
        self,
        *,
        page,
        cache_key: tuple,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
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
                    element=element,
                )
            except (OSError, ValueError, TypeError) as exc:
                print(f"    ⚠️  CONTROL CACHE: persist skipped ({type(exc).__name__})")

    async def _handle_navigate(self, page, step: str) -> bool:
        url = re.search(r'(https?://[^\s\'"<>]+)', step)
        if not url: return False
        await page.goto(url.group(1), wait_until="domcontentloaded", timeout=prompts.NAV_TIMEOUT)
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
                    page = await ctx.wait_for_event("page", timeout=prompts.NAV_TIMEOUT)
                else:
                    page = ctx.pages[-1]
            else:
                page = await ctx.wait_for_event("page", timeout=prompts.NAV_TIMEOUT)
            await page.wait_for_load_state("domcontentloaded", timeout=prompts.NAV_TIMEOUT)
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
                print(f"    ❌ PRESS: could not resolve target element")
                return False
            frame = self._frame_for(page, el)
            loc = frame.locator(f"xpath={el['xpath']}").first
            await loc.press(key_combo, timeout=prompts.TIMEOUT)
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
        except Exception:
            pass
        if is_shad:
            await frame.evaluate(
                f"window.manulElements[{el['id']}].dispatchEvent("
                f"new MouseEvent('contextmenu',{{bubbles:true,cancelable:true,button:2,view:window}}))"
            )
        else:
            await loc.click(button="right", force=True, timeout=prompts.TIMEOUT)
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
        except Exception:
            pass
        tag = str(el.get("tag_name", "")).lower()
        itype = str(el.get("input_type", "")).lower()
        if tag == "label":
            linked_id = str(el.get("html_id", ""))
            if linked_id:
                linked_loc = frame.locator(f"#{linked_id}").first
                try:
                    linked_tag = await linked_loc.evaluate("e => e.tagName.toLowerCase()")
                    linked_type = await linked_loc.evaluate("e => (e.type || '').toLowerCase()")
                except Exception:
                    linked_tag, linked_type = "", ""
                if linked_tag == "input" and linked_type == "file":
                    loc = linked_loc
                    tag, itype = linked_tag, linked_type
                    print(f"    🏷️  UPLOAD: followed <label for='{linked_id}'> → <input type='file'>")
        if tag != "input" or itype != "file":
            print(f"    ❌ UPLOAD: resolved element is <{tag} type='{itype}'>, expected <input type='file'>")
            return False
        await loc.set_input_files(file_path, timeout=prompts.TIMEOUT)
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

    async def _handle_verify(self, page, step: str, step_idx: int = 0) -> bool:
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
        # For is_checked_verify the highlight fires after element resolution
        # (inside the retry loop on first find). For all other VERIFY variants
        # we try to resolve the target element for highlighting; if none is
        # found we still pause — just without a highlight.
        if _in_debug and not is_checked_verify:
            if expected:
                if state_check:
                    # Disabled/enabled check — resolve via interactive element snapshot
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
                        except Exception:
                            pass
                else:
                    # Text presence verify — target is often a non-interactive element
                    # (h1, p, span) that SNAPSHOT_JS skips. Use get_by_text() instead.
                    for t in expected:
                        try:
                            loc = page.get_by_text(t, exact=False).first
                            await loc.scroll_into_view_if_needed(timeout=2000)
                            await self._debug_highlight(page, loc)
                            break
                        except Exception:
                            pass
            await self._debug_prompt(page, step, step_idx)
            await self._clear_debug_highlight(page)
        _debug_paused = not is_checked_verify  # is_checked pauses after element resolves

        for retry in range(15):
            if is_checked_verify:
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
                        except Exception:
                            pass
                        await self._debug_prompt(page, step, step_idx)
                        await self._clear_debug_highlight(page)
                        _debug_paused = True
                    try: checked = await loc.is_checked(timeout=2000)
                    except Exception: checked = False
                    if is_negative:
                        ok = not checked
                        if ok:
                            print(f"    {'✅' if ok else '❌'} Checkbox not-checked={ok}")
                            return ok
                    else:
                        if checked:
                            print(f"    {'✅' if checked else '❌'} Checkbox checked={checked}")
                            return checked
                if retry < 14:
                    await asyncio.sleep(1)
                    continue
                return False

            if state_check:
                search_text = expected[0] if expected else ""
                disabled_result = await page.evaluate(STATE_CHECK_JS, [search_text, state_check])
                
                if disabled_result is not None:
                    icon = '✅' if disabled_result else '❌'
                    print(f"    {icon} Element {state_check}={disabled_result}")
                    return disabled_result
                if retry < 14:
                    await asyncio.sleep(1)
                    continue
                return False

            text = await page.evaluate(VISIBLE_TEXT_JS)
            found = all(t.lower() in text for t in expected) if expected else bool(text)
            
            if not found and not is_negative:
                text2 = await page.evaluate(DEEP_TEXT_JS)
                found = all(t.lower() in text2 for t in expected) if expected else bool(text2)
                
            if is_negative:
                if not found:
                    print(f"    ✅ Verified ABSENT — OK")
                    return True
                if retry < 14:
                    await asyncio.sleep(1)
                    continue
                print(f"    ❌ Text still present after retries")
                return False
            else:
                if found:
                    print(f"    ✅ Verified — OK")
                    return True
                if retry < 14:
                    await asyncio.sleep(1.5)
                    continue
                print(f"    ❌ Not found after retries: {expected}")
                return False
        return False

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
        except Exception:
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
        step_l = step.lower()
        mode   = detect_mode(step)

        preserve = mode in ("input", "select")
        expected = extract_quoted(step, preserve_case=preserve)

        target_field = None
        txt_to_type  = ""
        search_texts = []

        if mode == "input" and expected:
            txt_to_type  = expected[-1]
            search_texts = expected[:-1]
            m = re.search(r'(?:into\s+the\s+|into\s+)([a-zA-Z0-9_]+)\s*field', step_l)
            if m and m.group(1) not in ("that", "the", "a", "an"): target_field = m.group(1).lower()
        else:
            search_texts = expected

        if search_texts or target_field:
            self.last_xpath = None

        is_optional = bool(re.search(r'\bif\s+exists\b|\boptional\b', re.sub(r'''["'][^"']*["']''', '', step_l)))
        cache_key = (mode, tuple(t.lower() for t in search_texts), target_field)
        failed_ids = set()

        for attempt in range(3):
            try:
                el = await self._resolve_element(page, step, mode, search_texts, target_field, strategic_context, failed_ids=failed_ids)
            except Exception:
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
                except Exception: pass
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
            except Exception: pass

            if _in_debug:
                await self._debug_prompt(page, step, step_idx)
                await self._clear_debug_highlight(page)

            try:
                if mode == "input":
                    print(f"    ⌨️  Typed '{txt_to_type}' → '{self._fmt_el_name(name)}'")
                    if is_shad: await frame.evaluate(f"window.manulType({el_id}, '{txt_to_type}')")
                    else:
                        is_readonly = await loc.evaluate("el => el.readOnly || el.hasAttribute('readonly')")
                        if is_readonly:
                            escaped = txt_to_type.replace("'", "\\'")
                            await page.evaluate(f"el => {{ el.removeAttribute('readonly'); el.value = '{escaped}'; el.dispatchEvent(new Event('input', {{bubbles:true}})); el.dispatchEvent(new Event('change', {{bubbles:true}})); }}", await loc.element_handle())
                        else:
                            await loc.fill("", timeout=3000)
                            await loc.type(txt_to_type, delay=50, timeout=3000)
                    if "enter" in step_l:
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(4)
                    self._remember_resolved_control(
                        page=page,
                        cache_key=cache_key,
                        mode=mode,
                        search_texts=search_texts,
                        target_field=target_field,
                        element=el,
                    )
                    self.last_xpath = None
                    return True

                elif mode == "select":
                    if is_sel:
                        opts = [expected[0]] if expected else [list(set(re.findall(r'\b[a-z0-9]{3,}\b', step_l)))[0]]
                        try: await loc.select_option(label=opts, timeout=3000)
                        except Exception: await loc.select_option(value=[o.lower() for o in opts], timeout=3000)
                    else: 
                        print(f"    🖱️  Clicked (Custom Select) '{self._fmt_el_name(name)}'")
                        try:
                            await loc.click(force=True, timeout=3000)
                        except Exception:
                            await frame.evaluate(f"window.manulClick({el_id})")
                        
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
                                except Exception: pass
                                
                    self._remember_resolved_control(
                        page=page,
                        cache_key=cache_key,
                        mode=mode,
                        search_texts=search_texts,
                        target_field=target_field,
                        element=el,
                    )
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                elif mode == "hover":
                    print(f"    🚁  Hovered '{self._fmt_el_name(name)}'")
                    if is_shad: await frame.evaluate(f"window.manulElements[{el_id}].dispatchEvent(new MouseEvent('mouseover',{{bubbles:true,cancelable:true,view:window}}))")
                    else: await loc.hover(force=True, timeout=3000)
                    self._remember_resolved_control(
                        page=page,
                        cache_key=cache_key,
                        mode=mode,
                        search_texts=search_texts,
                        target_field=target_field,
                        element=el,
                    )
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                else:
                    print(f"    🖱️  Clicked '{self._fmt_el_name(name)}'")
                    if is_shad:
                        fn = "manulDoubleClick" if "double" in step_l else "manulClick"
                        await frame.evaluate(f"window.{fn}({el_id})")
                        await asyncio.sleep(ACTION_WAIT)
                    else:
                        if "double" in step_l:
                            await loc.dblclick(force=True, timeout=3000)
                        elif itype in ("checkbox", "radio", "file"):
                            await loc.evaluate("el => el.click()")
                        else:
                            await loc.click(force=True, timeout=3000)
                            if itype == "submit" or (tag == "button" and itype in ("", "submit")):
                                try: await page.wait_for_load_state("networkidle", timeout=10_000)
                                except Exception: await asyncio.sleep(3.0)
                        await asyncio.sleep(ACTION_WAIT)
                    self._remember_resolved_control(
                        page=page,
                        cache_key=cache_key,
                        mode=mode,
                        search_texts=search_texts,
                        target_field=target_field,
                        element=el,
                    )
                    return True

            except Exception as ex:
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
        import json, os
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
            with open(resolved, "r", encoding="utf-8") as f:
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
            setattr(page, "_manul_mock_routes", mock_routes)

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
        timeout_ms = prompts.NAV_TIMEOUT  # reuse navigation timeout

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
            from PIL import Image, ImageChops  # type: ignore
            import io
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