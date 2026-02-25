# engine/actions.py
"""
Action execution mixin for ManulEngine.

Contains all browser-interaction handlers that perform real actions on the page:
navigation, scrolling, data extraction, verification, drag-and-drop,
and the main _execute_step dispatcher with self-healing retry logic.

Used as a mixin class — ManulEngine inherits from _ActionsMixin so that
these methods are available as `self._handle_navigate(...)` etc.
"""

import asyncio
import re

from .helpers import extract_quoted, SCROLL_WAIT, ACTION_WAIT, NAV_WAIT
from .js_scripts import VISIBLE_TEXT_JS
from . import prompts


class _ActionsMixin:
    """Mixin providing step handlers and the main action dispatcher."""

    # ── Navigation ────────────────────────────

    async def _handle_navigate(self, page, step: str) -> bool:
        url = re.search(r'(https?://[^\s\'"<>]+)', step)
        if not url:
            print("    ❌ Invalid URL")
            return False
        await page.goto(
            url.group(1), wait_until="domcontentloaded", timeout=prompts.NAV_TIMEOUT
        )
        self.last_xpath = None
        await asyncio.sleep(NAV_WAIT)
        return True

    # ── Scroll ────────────────────────────────

    async def _handle_scroll(self, page, step: str):
        step_l = step.lower()
        if "inside" in step_l or "list" in step_l:
            await page.evaluate(
                "const d=document.querySelector('#dropdown')||"
                "document.querySelector('[class*=\"dropdown\"]');"
                "if(d)d.scrollTop=d.scrollHeight;"
            )
        else:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(SCROLL_WAIT)

    # ── Data extraction ───────────────────────

    async def _handle_extract(self, page, step: str) -> bool:
        var_m  = re.search(r'\{(.*?)\}', step)
        target = (extract_quoted(step) or [""])[0].replace("'", "")
        print("    ⚙️  DOM HEURISTICS: Extracting data via JS…")

        val = await page.evaluate(f"""() => {{
            const t = "{target.lower()}";
            const row = Array.from(document.querySelectorAll('tr, [role="row"]'))
                             .find(r => r.innerText.toLowerCase().includes(t));
            if (row) {{
                const tds = Array.from(row.querySelectorAll('td'));
                if (tds.length > 0) {{
                    const numTd = tds.find(c =>
                        c.innerText.includes('%') || c.innerText.includes('$') ||
                        c.innerText.includes('Rs.') ||
                        !isNaN(parseFloat(c.innerText.trim()))
                    );
                    if (numTd) return numTd.innerText.trim();
                    return tds[tds.length - 1].innerText.trim();
                }}
                return row.innerText.trim();
            }}
            return null;
        }}""")

        if val and var_m:
            self.memory[var_m.group(1)] = val.strip()
            print(f"    📦 COLLECTED: {val.strip()}")
            return True
        return False

    # ── Verification ──────────────────────────

    async def _handle_verify(self, page, step: str) -> bool:
        expected          = extract_quoted(step)
        is_negative       = bool(re.search(r'\b(NOT|HIDDEN|ABSENT)\b', step.upper()))
        state_check       = (
            "disabled" if re.search(r'\bDISABLED\b', step.upper()) else
            "enabled"  if re.search(r'\bENABLED\b',  step.upper()) else None
        )
        is_checked_verify = bool(re.search(r'\bchecked\b', step.lower()))

        msg = f"    ⚙️  DOM HEURISTICS: Scanning for {expected}"
        if is_negative:       msg += " [MUST BE ABSENT]"
        if state_check:       msg += f" [{state_check.upper()}]"
        if is_checked_verify: msg += " [CHECKED]"
        print(msg)

        for retry in range(12):
            if is_checked_verify:
                raw_els = await self._snapshot(page, "clickable", [t.lower() for t in expected])
                scored  = self._score_elements(
                    raw_els, step, "clickable", expected, None, False
                )
                if scored:
                    best   = scored[0]
                    xpath  = best["xpath"]
                    loc    = page.locator(f"xpath={xpath}").first
                    try:
                        checked = await loc.is_checked(timeout=2000)
                    except Exception:
                        checked = False
                    if is_negative:
                        ok = not checked
                        print(f"    {'✅' if ok else '❌'} Checkbox not-checked={ok}")
                        return ok
                    print(f"    {'✅' if checked else '❌'} Checkbox checked={checked}")
                    return checked
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                return False

            if state_check:
                raw_els = await self._snapshot(page, "clickable", [t.lower() for t in expected])
                scored  = self._score_elements(
                    raw_els, step, "clickable", expected, None, False
                )
                if scored:
                    best   = scored[0]
                    loc    = page.locator(f"xpath={best['xpath']}").first
                    try:
                        disabled = await loc.is_disabled(timeout=2000)
                    except Exception:
                        disabled = False
                    is_ok = disabled if state_check == "disabled" else not disabled
                    print(f"    {'✅' if is_ok else '❌'} Element {state_check}={is_ok}")
                    return is_ok
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                return False

            text = await page.evaluate(VISIBLE_TEXT_JS)
            found = all(t.lower() in text for t in expected) if expected else bool(text)
            if is_negative:
                if not found:
                    print(f"    ✅ Verified ABSENT — OK")
                    return True
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                print(f"    ❌ Text still present after retries")
                return False
            else:
                if found:
                    print(f"    ✅ Verified — OK")
                    return True
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                print(f"    ❌ Not found after retries: {expected}")
                return False

        return False

    # ── Drag & drop ───────────────────────────

    async def _do_drag(self, page, step: str, expected: list[str], source_id: int) -> bool:
        step_l = step.lower()
        target_text = ""
        m_to = re.search(r"to\s+['\"](.+?)['\"]", step_l)
        if m_to:
            target_text = m_to.group(1)
        elif len(expected) >= 2:
            target_text = expected[-1]

        raw_els = await self._snapshot(page, "drag", [target_text])
        dest = None
        for el in raw_els:
            if el["id"] != source_id and target_text.lower() in el["name"].lower():
                dest = el
                break

        if not dest:
            print(f"    ❌ Drop target '{target_text}' not found")
            return False

        src_el = next((el for el in raw_els if el["id"] == source_id), raw_els[0])
        src_loc  = page.locator(f"xpath={src_el['xpath']}").first
        dest_loc = page.locator(f"xpath={dest['xpath']}").first

        try:
            await src_loc.drag_to(dest_loc, timeout=5000)
        except Exception:
            sb = await src_loc.bounding_box()
            db = await dest_loc.bounding_box()
            if sb and db:
                await page.mouse.move(sb["x"] + sb["width"]/2,
                                      sb["y"] + sb["height"]/2)
                await page.mouse.down()
                await asyncio.sleep(0.3)
                await page.mouse.move(db["x"] + db["width"]/2,
                                      db["y"] + db["height"]/2,
                                      steps=20)
                await page.mouse.up()

        print(f"    🖱️  Dragged → '{dest['name'][:30]}'")
        await asyncio.sleep(ACTION_WAIT)
        return True

    # ── Main action dispatcher ────────────────

    async def _execute_step(self, page, step: str, strategic_context: str = "") -> bool:
        """
        Parse a natural-language step, detect interaction mode, resolve the
        target element, and perform the action.  Includes self-healing: if an
        action fails, the candidate is blacklisted and the next-best is tried.
        """
        step_l = step.lower()
        words  = set(re.findall(r'\b[a-z]+\b', step_l))

        if   "drag" in words and "drop" in words:              mode = "drag"
        elif "select" in words or "choose" in words:           mode = "select"
        elif any(w in words for w in ("type","fill","enter")): mode = "input"
        elif any(w in words for w in ("click","double","check","uncheck")): mode = "clickable"
        elif "hover" in words:                                  mode = "hover"
        else:                                                    mode = "locate"

        preserve    = mode in ("input", "select")
        expected    = extract_quoted(step, preserve_case=preserve)

        target_field: str | None = None
        txt_to_type  = ""
        search_texts: list[str] = []

        if mode == "input" and expected:
            txt_to_type  = expected[-1]
            search_texts = expected[:-1]
            m = re.search(r'(?:into\s+the\s+|into\s+)([a-zA-Z0-9_]+)\s*field', step_l)
            if m and m.group(1) not in ("that", "the", "a", "an"):
                target_field = m.group(1).lower()
        else:
            search_texts = expected

        # Clear context memory when we have explicit targets
        if search_texts or target_field:
            self.last_xpath = None

        # ── Optional step detection ──────────────────────────────────
        _stripped = re.sub(r'''["'][^"']*["']''', '', step_l)
        is_optional = bool(re.search(r'\bif\s+exists\b|\boptional\b', _stripped))

        cache_key       = (mode, tuple(t.lower() for t in search_texts), target_field)
        failed_ids: set = set()
        MAX_ATTEMPTS    = 3

        for attempt in range(MAX_ATTEMPTS):
            try:
                el = await self._resolve_element(
                    page, step, mode, search_texts, target_field, strategic_context,
                    failed_ids=failed_ids,
                )
            except Exception:
                if is_optional:
                    return True
                raise

            if el is None:
                if mode == "locate":
                    return True
                if is_optional:
                    return True
                if attempt > 0:
                    print("    💀 SELF-HEALING FAILED: No more candidates.")
                return False

            # ── Optional step guard: require exact text match ────────────
            if is_optional and search_texts:
                el_name  = el["name"].lower()
                el_aria  = el.get("aria_label", "").lower()
                el_dqa   = el.get("data_qa", "").lower()
                el_haystack = f"{el_name} {el_aria} {el_dqa}"
                if not any(t.lower() in el_haystack for t in search_texts):
                    return True

            if el["id"] in failed_ids:
                continue

            self.last_xpath = el["xpath"]
            name    = el["name"]
            xpath   = el["xpath"]
            is_sel  = el.get("is_select",  False)
            is_shad = el.get("is_shadow",  False)
            el_id   = el["id"]
            tag     = el.get("tag_name",   "")
            itype   = el.get("input_type", "")

            # Guard: never type into non-typeable controls
            if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
                print(f"    👻 ANTI-PHANTOM GUARD: Rejecting '{name}' "
                      f"(cannot type into {itype}).")
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
                except Exception:
                    pass
                print(f"    🔍 Located '{name[:40]}'")
                return True

            if mode == "drag":
                return await self._do_drag(page, step, expected, el_id)

            loc = page.locator(f"xpath={xpath}").first
            try:
                if not is_shad:
                    await loc.scroll_into_view_if_needed(timeout=2000)
                    await self._highlight(page, loc)
                else:
                    await self._highlight(page, el_id, by_js_id=True)
            except Exception:
                pass

            act_timeout = 3000
            try:
                # ── Input ─────────────────────────────────────────────────
                if mode == "input":
                    print(f"    ⌨️  Typed '{txt_to_type}' → '{name[:30]}'")
                    if is_shad:
                        await page.evaluate(f"window.manulType({el_id}, '{txt_to_type}')")
                    else:
                        is_readonly = await loc.evaluate(
                            "el => el.readOnly || el.hasAttribute('readonly')"
                        )
                        if is_readonly:
                            escaped = txt_to_type.replace("'", "\\'")
                            await page.evaluate(f"""el => {{
                                el.removeAttribute('readonly');
                                el.value = '{escaped}';
                                el.dispatchEvent(new Event('input',  {{bubbles:true}}));
                                el.dispatchEvent(new Event('change', {{bubbles:true}}));
                                el.dispatchEvent(
                                    new KeyboardEvent('keydown', {{bubbles:true}})
                                );
                            }}""", await loc.element_handle())
                        else:
                            await loc.fill("",          timeout=act_timeout)
                            await loc.type(txt_to_type, delay=50, timeout=act_timeout)
                    if "enter" in step_l:
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(4)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    self.last_xpath = None
                    return True

                # ── Select ────────────────────────────────────────────────
                elif mode == "select":
                    if is_sel:
                        valid = await loc.evaluate(
                            """(sel, exp) => exp.filter(e =>
                                Array.from(sel.options).some(o =>
                                    o.text.trim().toLowerCase()  === e.toLowerCase() ||
                                    o.value.trim().toLowerCase() === e.toLowerCase()
                                ))""",
                            expected,
                        )
                        opts = (valid or expected
                                or [list(set(
                                    re.findall(r'\b[a-z0-9]{3,}\b', step_l)
                                ))[0]])
                        print(f"    🗂️  Selected {opts} from '{name[:30]}'")
                        try:
                            await loc.select_option(label=opts, timeout=act_timeout)
                        except Exception:
                            await loc.select_option(
                                value=[o.lower() for o in opts], timeout=act_timeout
                            )
                    else:
                        await loc.click(force=True, timeout=act_timeout)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                # ── Hover ─────────────────────────────────────────────────
                elif mode == "hover":
                    print(f"    🚁  Hovered '{name[:30]}'")
                    if is_shad:
                        await page.evaluate(
                            f"window.manulElements[{el_id}].dispatchEvent("
                            "new MouseEvent('mouseover',{bubbles:true,cancelable:true,"
                            "view:window}))"
                        )
                    else:
                        await loc.hover(force=True, timeout=act_timeout)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                # ── Click / double-click ───────────────────────────────────
                else:
                    print(f"    🖱️  Clicked '{name[:30]}'")
                    if is_shad:
                        fn = "manulDoubleClick" if "double" in step_l else "manulClick"
                        await page.evaluate(f"window.{fn}({el_id})")
                        await asyncio.sleep(ACTION_WAIT)
                    else:
                        if "double" in step_l:
                            await loc.dblclick(timeout=act_timeout)
                            await asyncio.sleep(ACTION_WAIT)
                        elif itype in ("checkbox", "radio"):
                            await loc.evaluate("el => el.click()")
                            await asyncio.sleep(ACTION_WAIT)
                        else:
                            is_submit = (
                                itype == "submit"
                                or (tag == "button" and itype in ("", "submit"))
                            )
                            if is_submit:
                                await loc.click(force=True, timeout=act_timeout)
                                try:
                                    await page.wait_for_load_state(
                                        "networkidle", timeout=10_000
                                    )
                                except Exception:
                                    await asyncio.sleep(3.0)
                            else:
                                await loc.click(force=True, timeout=act_timeout)
                                await asyncio.sleep(ACTION_WAIT)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    return True

            except Exception as ex:
                err = str(ex).split('\n')[0][:80]
                print(f"    ❌ Action error: {err}…")
                print(f"    🚑 SELF-HEALING: Rejecting candidate {el_id} and retrying…")
                failed_ids.add(el_id)
                self.last_xpath = None
                await asyncio.sleep(1)

        return False
