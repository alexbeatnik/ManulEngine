import asyncio
import json
import re
import ollama
from playwright.async_api import async_playwright
from . import config


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _substitute_memory(text: str, memory: dict) -> str:
    """Replace all {var} placeholders with values from memory."""
    for k, v in memory.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


def _extract_quoted(step: str, preserve_case: bool = False) -> list[str]:
    """Return all quoted strings from a step, preserving their order."""
    step = step.replace("\u2019", "'").replace("\u2018", "'")
    step = step.replace("\u201c", '"').replace("\u201d", '"')
    
    # 🚀 ФІКС: Знаходимо і подвійні, і одинарні лапки за один прохід
    matches = re.findall(r'"([^"]*)"|\'([^\']*)\'', step)
    found = [m[0] if m[0] else m[1] for m in matches]
    
    return [x if preserve_case else x.lower() for x in found if x]


SCROLL_WAIT = 1.5
ACTION_WAIT = 2.0
NAV_WAIT = 2.0


# ─────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────

class ManulEngine:
    def __init__(self, model: str = config.DEFAULT_MODEL, headless: bool = False, **_kwargs):
        self.model = model
        self.headless = headless
        self.memory: dict = {}
        self.last_xpath: str | None = None
        self.learned_elements: dict = {}  # 🚀 СЕМАНТИЧНИЙ КЕШ

    # ── LLM ──────────────────────────────────

    async def _llm_json(self, system: str, user: str) -> dict | None:
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
        print("    🧠 AI PLANNER: Generating mission steps...")
        obj = await self._llm_json(config.PLANNER_SYSTEM_PROMPT, task)
        return obj.get("steps", []) if obj else []

    async def _llm_select_element(
        self, step: str, mode: str, candidates: list[dict], strategic_context: str
    ) -> int:
        payload = [
            {
                "id":          el["id"],
                "name":        el["name"],
                "tag":         el.get("tag_name", ""),
                "role":        el.get("role", ""),
                "data_qa":     el.get("data_qa", ""),
                "html_id":     el.get("html_id", ""),
                "icon_classes": el.get("icon_classes", ""),
            }
            for el in candidates
        ]
        prompt = (
            f"STEP: {step}\n"
            f"MODE: {mode.upper()}\n"
            f"ELEMENTS:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        system = config.EXECUTOR_SYSTEM_PROMPT.format(strategic_context=strategic_context)
        obj = await self._llm_json(system, prompt)
        if not obj:
            return 0

        raw_id = obj.get("id", None)
        chosen_id: int | None = None
        try:
            chosen_id = int(raw_id)
        except (TypeError, ValueError):
            chosen_id = None

        thought = obj.get("thought", "")
        if chosen_id is not None:
            idx = next((i for i, el in enumerate(candidates) if el["id"] == chosen_id), 0)
        else:
            idx = 0
        print(f"    🎯 AI DECISION: '{candidates[idx]['name'][:40]}' — {thought}")
        return idx

    # ── Visual feedback ───────────────────────

    async def _highlight(self, page, target, color="red", bg="#ffeb3b", *, by_js_id=False):
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

    # ── DOM snapshot ──────────────────────────

    async def _snapshot(self, page, mode: str, texts: list[str]) -> list[dict]:
        return await page.evaluate(_SNAPSHOT_JS, [mode, texts or []])

    # ── Element selection ─────────────────────

    def _score_elements(
        self,
        els: list[dict],
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        is_blind: bool,
    ) -> list[dict]:
        step_l = step.lower()
        target_words = set(re.findall(r'\b[a-z0-9]{3,}\b', step_l))

        wants_button = bool(re.search(r'\bbutton\b', step_l))
        wants_link   = bool(re.search(r'\blink\b', step_l))
        wants_input  = bool(re.search(r'\bfield\b|\binput\b|\btextarea\b|\btype\b|\bfill\b', step_l))

        cache_key = (mode, tuple([t.lower() for t in search_texts]), target_field)
        learned = self.learned_elements.get(cache_key)

        for el in els:
            name      = el["name"].lower()
            tag       = el.get("tag_name", "")
            itype     = el.get("input_type", "")
            data_qa   = el.get("data_qa", "").lower()
            html_id   = el.get("html_id", "").lower()
            icons     = el.get("icon_classes", "").lower()
            aria      = el.get("aria_label", "").lower()
            role      = el.get("role", "").lower()
            score = 0

            # ── Learned Memory ──
            if learned and el["name"] == learned["name"] and tag == learned["tag"]:
                score += 20_000

            # ── Context Memory ──
            if is_blind and self.last_xpath and el["xpath"] == self.last_xpath:
                score += 10_000

            if target_field and target_field in name:
                score += 2_000

            name_core = name.split(" -> ")[-1].strip() if " -> " in name else name

            for t in search_texts:
                tl = t.lower().strip()
                if not tl:
                    continue

                if name_core == tl or name == tl:
                    score += 3_000
                elif name_core.startswith(tl) or name_core.endswith(tl):
                    score += 2_000
                elif tl in name_core:
                    extra_words = max(0, len(name_core.split()) - len(tl.split()))
                    score += max(200, 1_000 - extra_words * 150)
                elif tl in name:
                    extra_words = max(0, len(name.split()) - len(tl.split()))
                    score += max(100, 800 - extra_words * 100)

                if tl in aria:        score += 800
                if tl in html_id:     score += 600
                if any(w in icons for w in tl.split() if len(w) > 3):
                    score += 700

            score += sum(10 for w in target_words if w in name)
            score += sum(8  for w in target_words if len(w) > 3 and w in icons)
            score += sum(15 for w in target_words if len(w) > 3 and w in html_id)
            score += sum(12 for w in target_words if len(w) > 3 and w in aria)

            for t in search_texts:
                t_l = t.lower().replace(" ", "-").replace("_", "-")
                if t_l and t_l in data_qa:
                    score += 5_000

            is_real_button = tag == "button" or role == "button" \
                          or (tag == "input" and itype in ("submit", "button", "image"))
            is_real_link   = tag == "a"
            is_real_input  = (tag in ("input", "textarea") and itype not in
                              ("submit", "button", "image", "radio", "checkbox")) \
                          or role in ("textbox", "searchbox", "spinbutton")
            is_real_checkbox = (tag == "input" and itype == "checkbox") or role == "checkbox"
            is_real_radio    = (tag == "input" and itype == "radio")    or role == "radio"

            if wants_button:
                if is_real_button:   score += 300
                if is_real_link:     score -= 300

            if wants_link:
                if is_real_link:     score += 300
                if is_real_button:   score -= 300

            if wants_input:
                if is_real_input:    score += 300
                if is_real_button:   score -= 300

            if "checkbox" in step_l:
                if is_real_checkbox: score += 400
                elif "checkbox" in name: score += 200
            if "radio" in step_l:
                if is_real_radio:    score += 400
                elif "radio" in name: score += 200

            if not search_texts:
                if "dropdown" in step_l and "combobox" in name:    score += 5_000
                elif "shadow" in step_l and "shadow"   in name:    score += 5_000
                elif "input"  in step_l and is_real_input \
                        and "wikipedia" not in name:                score += 500
                elif "list"   in step_l and ("dropdown" in name or "combo" in name):
                    score += 500

            el["score"] = score

        return sorted(els, key=lambda x: x.get("score", 0), reverse=True)

    async def _resolve_element(
        self,
        page,
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        strategic_context: str,
        failed_ids: set,
    ) -> dict | None:
        is_blind = not search_texts and not target_field

        for attempt in range(5):
            raw_els = await self._snapshot(page, mode, [t.lower() for t in search_texts])
            els = [e for e in raw_els if e["id"] not in failed_ids]

            if not els:
                if attempt < 4:
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(1)
                continue

            if mode == "drag":
                break

            exact = []
            for el in els:
                name = el["name"].lower().strip()
                if target_field and target_field in name:
                    exact.append(el)
                    continue
                for q in search_texts:
                    q_l = q.lower().strip()
                    if (len(q_l) <= 2 and q_l == name) or (len(q_l) > 2 and q_l in name):
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

        scored = self._score_elements(els, step, mode, search_texts, target_field, is_blind)
        top = scored[:8]
        best_score = top[0].get("score", 0)

        if best_score >= 20_000:
            print(f"    🧠 SEMANTIC CACHE: Reusing learned element (score {best_score})")
            return top[0]

        if best_score >= 10_000:
            print(f"    ⚡ CONTEXT MEMORY: Reusing last element (score {best_score})")
            return top[0]

        if best_score >= 500:
            label = "High confidence" if best_score >= 1_000 else "Keyword"
            print(f"    ⚙️  DOM HEURISTICS: {label} match (score {best_score})")
            return top[0]

        # 🚀 ШІ отримує шанс подумати
        print(f"    🧠 AI AGENT: Ambiguity detected, analysing {len(top)} candidates…")
        idx = await self._llm_select_element(step, mode, top, strategic_context)
        ai_choice = top[idx]

        # 🚀 SMART ANTI-PHANTOM GUARD: Перевіряємо рішення ШІ
        if not is_blind:
            search_terms = [t.lower() for t in search_texts]
            if target_field: search_terms.append(target_field.lower())
            
            # Чи є хоч одне слово з пошуку в атрибутах вибраного елемента?
            target_words = set(re.findall(r'\b[a-z0-9]{3,}\b', " ".join(search_terms)))
            element_text = f"{ai_choice['name']} {ai_choice.get('html_id', '')} {ai_choice.get('data_qa', '')}".lower()
            
            if target_words:
                is_match_found = any(w in element_text for w in target_words)
                
                # Дозволяємо пропускати, якщо це кнопка, або якщо слово знайдено
                if not is_match_found and mode != "clickable":
                     missing_term = search_texts[0] if search_texts else target_field
                     print(f"    👻 ANTI-PHANTOM GUARD: AI chose '{ai_choice['name']}', but target '{missing_term}' is missing from it. Rejecting.")
                     return None

        return ai_choice

    # ── High-level step handlers ──────────────

    async def _handle_navigate(self, page, step: str) -> bool:
        u = re.search(r'((?:https?|file)://[^\s\'"<>]+)', step)
        if not u:
            print("    ❌ Invalid URL")
            return False
        await page.goto(u.group(1), wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT)
        self.last_xpath = None
        await asyncio.sleep(NAV_WAIT)
        return True

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

    async def _handle_extract(self, page, step: str) -> bool:
        var_m = re.search(r'\{(.*?)\}', step)
        target = (_extract_quoted(step) or [""])[0].replace("'", "")
        print("    ⚙️  DOM HEURISTICS: Extracting data via JS…")
        
        val = await page.evaluate(f"""() => {{
            const t = "{target.lower()}";
            const row = Array.from(document.querySelectorAll('tr, [role="row"]'))
                             .find(r => r.innerText.toLowerCase().includes(t));
            
            if (row) {{
                const tds = Array.from(row.querySelectorAll('td'));
                if (tds.length > 0) {{
                    const numTd = tds.find(c => c.innerText.includes('%') || c.innerText.includes('$') || c.innerText.includes('Rs.') || !isNaN(parseFloat(c.innerText.trim())));
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

    async def _handle_verify(self, page, step: str) -> bool:
        expected = _extract_quoted(step)
        is_negative = bool(re.search(r'\b(NOT|HIDDEN|ABSENT)\b', step.upper()))
        state_check = (
            "disabled" if re.search(r'\bDISABLED\b', step.upper()) else
            "enabled"  if re.search(r'\bENABLED\b',  step.upper()) else None
        )

        is_checked_verify = bool(re.search(r'\bchecked\b', step.lower()))

        msg = f"    ⚙️  DOM HEURISTICS: Scanning for {expected}"
        if is_negative:        msg += " [MUST BE ABSENT]"
        if is_checked_verify:  msg += " [CHECK STATE]"
        if state_check:        msg += f" [MUST BE {state_check.upper()}]"
        print(msg)

        for _ in range(12):
            try:
                if is_checked_verify and expected:
                    snapshot = await self._snapshot(page, "locate", [expected[0].lower()])
                    for el in snapshot:
                        if expected[0].lower() in el["name"].lower():
                            loc = page.locator(f"xpath={el['xpath']}").first
                            is_checked = await loc.is_checked()
                            ok = (not is_checked) if is_negative else is_checked
                            if ok:
                                print("    ✅ VERIFIED")
                                return True
                            break

                elif state_check and expected:
                    els = await self._snapshot(page, "locate", expected)
                    if els:
                        loc = page.locator(f"xpath={els[0]['xpath']}").first
                        disabled = await loc.is_disabled()
                        ok = (state_check == "disabled" and disabled) \
                          or (state_check == "enabled"  and not disabled)
                        if ok:
                            print("    ✅ VERIFIED")
                            return True

                else:
                    text = await page.evaluate(_VISIBLE_TEXT_JS)
                    clean = " ".join(text.replace("\u2019", "'").split())
                    matched = all(e.lower() in clean for e in expected) if expected else False
                    success = (not matched) if is_negative else matched
                    if success:
                        print("    ✅ VERIFIED")
                        return True

            except Exception:
                pass
            await asyncio.sleep(1)

        print("    ❌ VERIFICATION FAILED")
        return False

    async def _do_drag(self, page, step: str, expected: list[str], _hint_id: int) -> bool:
        all_els = await self._snapshot(page, "drag", [])
        if not all_els:
            return False

        src_idx = tgt_idx = -1
        if len(expected) >= 2:
            for i, el in enumerate(all_els):
                n = el["name"].lower()
                if expected[0].lower() in n and src_idx == -1: src_idx = i
                if expected[1].lower() in n: tgt_idx = i
        else:
            for i, el in enumerate(all_els):
                n  = el["name"].lower()
                cl = el.get("class_name", "").lower()
                if ("drag" in n or "draggable" in cl) and src_idx == -1: src_idx = i
                if expected and expected[0].lower() in n: tgt_idx = i

        if src_idx < 0: src_idx = 0
        if tgt_idx < 0: tgt_idx = len(all_els) - 1 if len(all_els) > 1 else 0

        try:
            src_loc = page.locator(f"xpath={all_els[src_idx]['xpath']}").first
            tgt_loc = page.locator(f"xpath={all_els[tgt_idx]['xpath']}").first
            await src_loc.scroll_into_view_if_needed()
            await self._highlight(page, all_els[src_idx]["id"], "red",   "#ffcccc", by_js_id=True)
            await self._highlight(page, all_els[tgt_idx]["id"], "green", "#ccffcc", by_js_id=True)
            print(f"    🔄 Dragging '{all_els[src_idx]['name'][:25]}'"
                  f" → '{all_els[tgt_idx]['name'][:25]}'")
            await src_loc.drag_to(tgt_loc, timeout=3000)
            await asyncio.sleep(ACTION_WAIT)
            return True
        except Exception as ex:
            print(f"    ❌ Drag error: {ex}")
            return False

    # ── Action dispatcher ─────────────────────

    async def _execute_step(self, page, step: str, strategic_context: str) -> bool:
        step_l = step.lower()
        words = set(re.findall(r'\b[a-z0-9]+\b', step_l))

        if "drag" in words and "drop" in words:  mode = "drag"
        elif "select" in words or "choose" in words: mode = "select"
        elif any(w in words for w in ("type", "fill", "enter")): mode = "input"
        elif "click" in words or "double" in words: mode = "clickable"
        elif "hover" in words: mode = "hover"
        else: mode = "locate"

        preserve = mode in ("input", "select")
        expected = _extract_quoted(step, preserve_case=preserve)

        target_field: str | None = None
        txt_to_type = ""
        search_texts: list[str] = []

        if mode == "input" and expected:
            txt_to_type = expected[-1]
            search_texts = expected[:-1]
            m = re.search(r'(?:into\s+the\s+|into\s+)([a-zA-Z0-9_]+)\s*field', step_l)
            if m and m.group(1) not in ("that", "the", "a", "an"):
                target_field = m.group(1).lower()
        else:
            search_texts = expected

        if search_texts or target_field:
            self.last_xpath = None

        cache_key = (mode, tuple([t.lower() for t in search_texts]), target_field)
        failed_ids = set()
        MAX_HEALING_ATTEMPTS = 3

        for attempt in range(MAX_HEALING_ATTEMPTS):
            el = await self._resolve_element(
                page, step, mode, search_texts, target_field, strategic_context, failed_ids
            )
            
            if el is None:
                if attempt > 0:
                    print("    💀 SELF-HEALING FAILED: No more candidates found.")
                return False

            self.last_xpath = el["xpath"]
            name     = el["name"]
            xpath    = el["xpath"]
            is_sel   = el.get("is_select", False)
            is_shad  = el.get("is_shadow", False)
            el_id    = el["id"]
            tag      = el.get("tag_name", "")
            itype    = el.get("input_type", "")

            # 🚀 Жорсткий захист від галюцинацій типу "Input radio" для вводу тексту
            if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
                print(f"    👻 ANTI-PHANTOM GUARD: Rejecting '{name}' because it is a {itype} (cannot type).")
                failed_ids.add(el_id)
                self.last_xpath = None
                continue 

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

            try:
                act_timeout = 3000

                if mode == "input":
                    print(f"    ⌨️  Typed '{txt_to_type}' → '{name[:30]}'")
                    if is_shad:
                        await page.evaluate(f"window.manulType({el_id}, '{txt_to_type}')")
                    else:
                        is_readonly = await loc.evaluate("el => el.readOnly || el.hasAttribute('readonly')")
                        if is_readonly:
                            escaped = txt_to_type.replace("'", "\\'")
                            await page.evaluate(f"""el => {{
                                el.removeAttribute('readonly');
                                el.value = '{escaped}';
                                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                                el.dispatchEvent(new KeyboardEvent('keydown', {{bubbles: true}}));
                            }}""", await loc.element_handle())
                        else:
                            await loc.fill("", timeout=act_timeout)
                            await loc.type(txt_to_type, delay=50, timeout=act_timeout)
                    if "enter" in step_l:
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(4)
                    
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    self.last_xpath = None
                    return True

                elif mode == "select":
                    if is_sel:
                        valid = await loc.evaluate(
                            """(sel, exp) => exp.filter(e =>
                                Array.from(sel.options).some(o =>
                                    o.text.trim().toLowerCase() === e.toLowerCase() ||
                                    o.value.trim().toLowerCase() === e.toLowerCase()
                                ))""",
                            expected,
                        )
                        opts = valid or expected or [list(set(re.findall(r'\b[a-z0-9]{3,}\b', step_l)))[0]]
                        print(f"    🗂️  Selected {opts} from '{name[:30]}'")
                        try:
                            await loc.select_option(label=opts, timeout=act_timeout)
                        except Exception:
                            await loc.select_option(value=[o.lower() for o in opts], timeout=act_timeout)
                    else:
                        await loc.click(force=True, timeout=act_timeout)
                    
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                elif mode == "hover":
                    print(f"    🚁  Hovered '{name[:30]}'")
                    if is_shad:
                        await page.evaluate(
                            f"window.manulElements[{el_id}].dispatchEvent("
                            "new MouseEvent('mouseover',{bubbles:true,cancelable:true,view:window}))"
                        )
                    else:
                        await loc.hover(force=True, timeout=act_timeout)
                    
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

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
                        else:
                            is_submit = (
                                itype == "submit"
                                or (tag == "button" and itype in ("", "submit"))
                            )
                            if is_submit:
                                await loc.click(force=True, timeout=act_timeout)
                                try:
                                    await page.wait_for_load_state("networkidle", timeout=10_000)
                                except Exception:
                                    await asyncio.sleep(3.0)
                            else:
                                await loc.click(force=True, timeout=act_timeout)
                                await asyncio.sleep(ACTION_WAIT)
                    
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    return True

            except Exception as ex:
                err_msg = str(ex).split('\n')[0][:80]
                print(f"    ❌ Action error: {err_msg}...")
                print(f"    🚑 SELF-HEALING: Rejecting candidate {el_id} and retrying...")
                failed_ids.add(el_id)
                self.last_xpath = None
                await asyncio.sleep(1)

        return False

    # ── Mission runner ────────────────────────

    async def run_mission(self, task: str, strategic_context: str = "") -> bool:
        print(f"\n🐱 ManulEngine v0.01 [{self.model}] — Manul went hunting...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--start-maximized"],
            )
            ctx  = await browser.new_context(no_viewport=True)
            page = await ctx.new_page()

            if re.match(r'^\s*\d+\.', task):
                plan = [s.strip() for s in re.split(r'(?=\b\d+\.\s)', task) if s.strip()]
            else:
                plan = await self._llm_plan(task)

            if not plan:
                await browser.close()
                return False

            ok = True
            try:
                for i, raw_step in enumerate(plan, 1):
                    step = _substitute_memory(raw_step, self.memory)
                    print(f"\n[🐾 STEP {i}] {step}")
                    s_up = step.upper()

                    if re.search(r'\bNAVIGATE\b', s_up):
                        if not await self._handle_navigate(page, step):
                            ok = False; break

                    elif re.search(r'\bWAIT\b', s_up):
                        n = re.search(r'(\d+)', step)
                        await asyncio.sleep(int(n.group(1)) if n else 2)

                    elif re.search(r'\bSCROLL\b', s_up):
                        await self._handle_scroll(page, step)

                    elif re.search(r'\bEXTRACT\b', s_up):
                        if not await self._handle_extract(page, step):
                            ok = False; break

                    elif re.search(r'\b(VERIFY|CHECK)\b', s_up):
                        if not await self._handle_verify(page, step):
                            ok = False; break

                    elif re.search(r'\bDONE\b', s_up):
                        print("    🏁 HUNT SUCCESSFUL")
                        return True

                    else:
                        if not await self._execute_step(page, step, strategic_context):
                            print("    ❌ HUNT FAILED")
                            ok = False; break

            finally:
                await browser.close()

        return ok


# ─────────────────────────────────────────────
# JavaScript constants (kept out of Python logic)
# ─────────────────────────────────────────────

_VISIBLE_TEXT_JS = """() => {
    let t = (document.body.innerText || "") + " ";
    document.querySelectorAll('*').forEach(el => {
        const st = window.getComputedStyle(el);
        const isHidden = st.display === 'none'
                      || st.visibility === 'hidden'
                      || st.opacity === '0';

        const isAlert = el.classList && (
            el.classList.contains('alert') ||
            el.classList.contains('success') ||
            el.classList.contains('notification') ||
            el.classList.contains('message') ||
            el.getAttribute('role') === 'alert'
        );

        if (isHidden && !isAlert) return;

        if (el.title)       t += el.title + " ";
        if (el.value && typeof el.value === 'string') t += el.value + " ";
        if (el.placeholder) t += el.placeholder + " ";
        if (el.shadowRoot)
            t += Array.from(el.shadowRoot.querySelectorAll('*'))
                      .map(e => e.innerText || e.value || '').join(' ');
    });
    return t.toLowerCase();
}"""

_SNAPSHOT_JS = r"""([mode, expected_texts]) => {
    if (!window.manulElements)  { window.manulElements = {}; window.manulIdCounter = 0; }

    window.manulHighlight = (id, color, bg) => {
        const el = window.manulElements[id]; if (!el) return;
        el.scrollIntoView({ behavior:'smooth', block:'center' });
        const oB=el.style.border, oBg=el.style.backgroundColor;
        el.style.border=`4px solid ${color}`; el.style.backgroundColor=bg;
        setTimeout(()=>{el.style.border=oB;el.style.backgroundColor=oBg;},2000);
    };
    window.manulClick = id => {
        const el=window.manulElements[id];
        if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.click();}
    };
    window.manulDoubleClick = id => {
        const el=window.manulElements[id];
        if(el) el.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));
    };
    window.manulType = (id, text) => {
        const el=window.manulElements[id];
        if(!el) return;
        el.scrollIntoView({behavior:'smooth',block:'center'});
        el.value=text;
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
    };

    const INTERACTIVE_INPUT = "input,textarea,[contenteditable='true']";
    const INTERACTIVE_CLICK = [
        "button","a","input[type='radio']","input[type='checkbox']",
        "select",".dropbtn","summary",
        ".ui-draggable",".ui-droppable",".option","input",
        "label",
        "[role='button']","[role='checkbox']","[role='radio']",
        "[role='tab']","[role='option']","[role='menuitem']","[role='switch']",
        "[class*='rct-node-clickable']","[class*='rct-title']",
        "[class*='checkbox']","[class*='check-box']",
        "[onclick]",
    ].join(",");

    const INTERACTIVE = (mode==="input"||mode==="locate")
        ? INTERACTIVE_INPUT
        : INTERACTIVE_CLICK;

    const seen = new Set();
    const results = [];
    const collect = (root, inShadow=false) => {
        root.querySelectorAll(INTERACTIVE).forEach(el => {
            if (seen.has(el)) return;
            seen.add(el);

            const r=el.getBoundingClientRect();
            if (r.width<2||r.height<2) return;
            const st = window.getComputedStyle(el);
            if (st.visibility==='hidden'||st.display==='none') return;

            if (el.tagName==='LABEL') {
                const linked = el.htmlFor
                    ? document.getElementById(el.htmlFor)
                    : el.querySelector('input');
                if (linked) {
                    const lr = linked.getBoundingClientRect();
                    if (lr.width > 2 && lr.height > 2
                        && window.getComputedStyle(linked).display !== 'none') {
                        return;
                    }
                }
            }

            if (!el.dataset.manulId) {
                const id=window.manulIdCounter++;
                el.dataset.manulId=id;
                window.manulElements[id]=el;
            }
            results.push({el, inShadow});
        });
        root.querySelectorAll('*').forEach(el=>{
            if(el.shadowRoot) collect(el.shadowRoot,true);
        });
    };
    collect(document);

    results.sort((a,b)=>a.el.getBoundingClientRect().top-b.el.getBoundingClientRect().top);

    const getXPath = el => {
        if(el.id) return `//*[@id="${el.id}"]`;
        const parts=[];
        while(el&&el.nodeType===Node.ELEMENT_NODE){
            const idx=Array.from(el.parentNode?.children||[])
                           .filter(s=>s.tagName===el.tagName).indexOf(el)+1;
            parts.unshift(`${el.tagName.toLowerCase()}[${idx}]`);
            el=el.parentNode;
        }
        return `/${parts.join('/')}`;
    };

    const labelFor = el => {
        if (el.tagName==='INPUT' && (el.type==='checkbox' || el.type==='radio')) {
            const tr = el.closest('tr');
            if (tr) return tr.innerText.trim().replace(/\s+/g,' ');
            const lbl = el.closest('label') || document.querySelector(`label[for="${el.id}"]`);
            if (lbl) return lbl.innerText.trim();
        }

        if (['INPUT','SELECT','TEXTAREA'].includes(el.tagName)) {
            const lbl = document.querySelector(`label[for="${el.id}"]`);
            if (lbl) return lbl.innerText.trim();
            let curr = el;
            while (curr && curr.tagName !== 'BODY') {
                let prev = curr.previousElementSibling;
                while (prev) {
                    if (/^H[1-6]$/.test(prev.tagName) || prev.classList.contains('title'))
                        return prev.innerText.trim();
                    prev = prev.previousElementSibling;
                }
                curr = curr.parentElement;
            }
        }

        const role = el.getAttribute('role') || '';
        if (role === 'checkbox' || role === 'radio' ||
            (el.className && typeof el.className === 'string' &&
             (el.className.includes('rct-') || el.className.includes('checkbox')))) {
            const title = el.querySelector('[class*="title"],[class*="label"]')
                       || el.closest('[class*="node"],[class*="item"],[class*="tree-item"]')
                             ?.querySelector('[class*="title"],[class*="label"]');
            if (title) return title.innerText.trim();
        }

        return '';
    };

    return results.map(({el,inShadow})=>{
        let name, isSelect=false;

        const iconClasses = Array.from(el.querySelectorAll('i,svg,span[class*="icon"]'))
            .map(i => i.className || i.getAttribute('class') || '')
            .join(' ')
            .replace(/[-_]/g, ' ')
            .toLowerCase();

        const htmlId    = el.id || '';
        const ariaLabel = el.getAttribute('aria-label') || el.getAttribute('title') || '';

        if(el.tagName==='SELECT'){
            isSelect=true;
            name='dropdown ['+Array.from(el.options).map(o=>o.text.trim()).join(' | ')+']';
        } else {
            const rawText = el.innerText ? el.innerText.trim() : '';
            name = rawText
                || ariaLabel
                || el.placeholder
                || el.getAttribute('value')
                || htmlId
                || el.name
                || el.className
                || 'item';
            name = name.trim();
        }

        if(el.tagName==='INPUT') name+=` input ${el.type||''}`;

        const ctx=labelFor(el);
        if(ctx)    name=`${ctx} -> ${name}`;
        if(inShadow) name+=' [SHADOW_DOM]';

        return {
            id:          parseInt(el.dataset.manulId),
            name:        name.substring(0,150).replace(/\n/g,' '),
            xpath:       getXPath(el),
            is_select:   isSelect,
            is_shadow:   inShadow,
            class_name:  el.className||'',
            tag_name:    el.tagName.toLowerCase(),
            input_type:  el.type ? el.type.toLowerCase() : '',
            data_qa:     el.getAttribute('data-qa') || el.getAttribute('data-testid') || '',
            html_id:     htmlId,
            icon_classes: iconClasses,
            aria_label:  ariaLabel,
            role:        el.getAttribute('role') || '',
        };
    });
}"""