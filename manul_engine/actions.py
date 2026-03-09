# manul_engine/actions.py
import asyncio
import re
from .helpers import extract_quoted, compact_log_field, SCROLL_WAIT, ACTION_WAIT, NAV_WAIT
from .js_scripts import VISIBLE_TEXT_JS, EXTRACT_DATA_JS, DEEP_TEXT_JS, STATE_CHECK_JS, SCAN_JS
from . import prompts

class _ActionsMixin:
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
        if getattr(self, '_controls_cache_enabled', True):
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

    async def _handle_scroll(self, page, step: str):
        step_l = step.lower()
        if "inside" in step_l or "list" in step_l:
            await page.evaluate("const d=document.querySelector('#dropdown')||document.querySelector('[class*=\"dropdown\"]');if(d)d.scrollTop=d.scrollHeight;")
        else:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(SCROLL_WAIT)

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

    async def _handle_verify(self, page, step: str) -> bool:
        expected = extract_quoted(step)
        step_no_quotes = re.sub(r"'[^']*'", "", step)
        is_negative = bool(re.search(r'\b(NOT|HIDDEN|ABSENT)\b', step_no_quotes.upper()))
        state_check = "disabled" if re.search(r'\bDISABLED\b', step.upper()) else "enabled" if re.search(r'\bENABLED\b', step.upper()) else None
        is_checked_verify = bool(re.search(r'\bchecked\b', step.lower()))

        msg = f"    ⚙️  DOM HEURISTICS: Scanning for {expected}"
        if is_negative: msg += " [MUST BE ABSENT]"
        if state_check: msg += f" [{state_check.upper()}]"
        if is_checked_verify: msg += " [CHECKED]"
        print(msg)

        for retry in range(15):
            if is_checked_verify:
                raw_els = await self._snapshot(page, "clickable", [t.lower() for t in expected])
                scored  = self._score_elements(raw_els, step, "clickable", expected, None, False)
                if scored:
                    best   = scored[0]
                    xpath  = best["xpath"]
                    loc    = page.locator(f"xpath={xpath}").first
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

    async def _do_drag(self, page, step: str, expected: list[str], source_id: int) -> bool:
        step_l = step.lower()
        target_text = ""
        m_to = re.search(r"to\s+['\"](.+?)['\"]", step_l)
        if m_to: target_text = m_to.group(1)
        elif len(expected) >= 2: target_text = expected[-1]

        raw_els = await self._snapshot(page, "drag", [target_text])
        dest = next((el for el in raw_els if el["id"] != source_id and target_text.lower() in el["name"].lower()), None)
        if not dest: return False

        src_el = next((el for el in raw_els if el["id"] == source_id), raw_els[0])
        src_loc  = page.locator(f"xpath={src_el['xpath']}").first
        dest_loc = page.locator(f"xpath={dest['xpath']}").first

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

    async def _execute_step(self, page, step: str, strategic_context: str = "") -> bool:
        step_l = step.lower()
        words  = set(re.findall(r'\b[a-z]+\b', step_l))

        if   "drag" in words and "drop" in words:              mode = "drag"
        elif "select" in words or "choose" in words:           mode = "select"
        elif any(w in words for w in ("type","fill","enter")): mode = "input"
        elif any(w in words for w in ("click","double","check","uncheck")): mode = "clickable"
        elif "hover" in words:                                  mode = "hover"
        else:                                                   mode = "locate"

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

            if el["id"] in failed_ids: continue

            self.last_xpath = el["xpath"]
            name, xpath, is_sel, is_shad, el_id, tag, itype = el["name"], el["xpath"], el.get("is_select"), el.get("is_shadow"), el["id"], el.get("tag_name", ""), el.get("input_type", "")

            if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
                failed_ids.add(el_id)
                self.last_xpath = None
                continue

            if mode == "locate":
                try:
                    loc = page.locator(f"xpath={xpath}").first
                    if not is_shad: 
                        await loc.scroll_into_view_if_needed(timeout=2000)
                        await self._highlight(page, loc)
                    else:
                        await self._highlight(page, el_id, by_js_id=True)
                except Exception: pass
                print(f"    🔍 Located '{self._fmt_el_name(name)}'")
                return True

            if mode == "drag": return await self._do_drag(page, step, expected, el_id)

            loc = page.locator(f"xpath={xpath}").first
            try:
                if not is_shad:
                    await loc.scroll_into_view_if_needed(timeout=2000)
                    await self._highlight(page, loc)
                else:
                    await self._highlight(page, el_id, by_js_id=True)
                if getattr(self, "debug_mode", False):
                    if not is_shad:
                        await self._debug_highlight(page, loc)
                    else:
                        await self._debug_highlight(page, el_id, by_js_id=True)
            except Exception: pass

            try:
                if mode == "input":
                    print(f"    ⌨️  Typed '{txt_to_type}' → '{self._fmt_el_name(name)}'")
                    if is_shad: await page.evaluate(f"window.manulType({el_id}, '{txt_to_type}')")
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
                            await page.evaluate(f"window.manulClick({el_id})")
                        
                        if expected:
                            await asyncio.sleep(0.5) 
                            option_text = expected[0]
                            print(f"    🖱️  Selecting option '{option_text}'")
                            try:
                                opt_loc = page.locator(f"[role='option']:has-text('{option_text}'), [role='menuitem']:has-text('{option_text}')").first
                                await opt_loc.click(timeout=3000)
                            except Exception:
                                try:
                                    opt_loc = page.locator(f"text='{option_text}'").last
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
                    if is_shad: await page.evaluate(f"window.manulElements[{el_id}].dispatchEvent(new MouseEvent('mouseover',{{bubbles:true,cancelable:true,view:window}}))")
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
                        await page.evaluate(f"window.{fn}({el_id})")
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
                failed_ids.add(el_id)
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