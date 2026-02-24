import asyncio, json, re, ollama, os
from playwright.async_api import async_playwright
from . import config

class ManulEngine:
    def __init__(self, model: str = config.DEFAULT_MODEL, headless: bool = False, **kwargs):
        self.model, self.headless, self.memory = model, headless, {}

    async def _ollama_chat_json(self, system: str, user: str):
        try:
            resp = await asyncio.to_thread(ollama.chat, model=self.model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], format="json")
            c = resp["message"]["content"]
            m = re.search(r'\{.*\}', c, re.DOTALL)
            return json.loads(m.group(0)) if m else json.loads(c)
        except Exception as e: 
            print(f"    ⚠️ LLM Error: {e}")
            return None

    def _extract_text(self, step, preserve_case=False):
        for k, v in self.memory.items(): step = step.replace(f"{{{k}}}", str(v))
        step = step.replace("'", "’")
        q = re.findall(r'["“](.*?)["”]', step) or re.findall(r"(?:^|\s)['’](.*?)['’]", step)
        return [x if preserve_case else x.lower() for x in q if x]

    async def _highlight(self, page, loc_or_id, color="red", bg="#ffeb3b", is_js_id=False):
        try:
            if is_js_id:
                await page.evaluate(f"window.manulHighlight({loc_or_id}, '{color}', '{bg}')")
            else:
                await loc_or_id.evaluate(f"""(el) => {{ 
                    const oB = el.style.border; const oBg = el.style.backgroundColor;
                    el.style.border = '4px solid {color}'; el.style.backgroundColor = '{bg}'; el.style.transition = 'all 0.3s ease';
                    setTimeout(() => {{ el.style.border = oB; el.style.backgroundColor = oBg; }}, 2000); 
                }}""")
            await asyncio.sleep(0.5)
        except: pass

    async def run_mission(self, task: str, strategic_context: str = ""):
        print(f"\n🐾 Manul v0.020 [The Precision Strike] - Absolute Accuracy ({self.model})")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless, 
                args=["--no-sandbox", "--start-maximized"]
            )
            context = await browser.new_context(no_viewport=True)
            page = await context.new_page()
            
            plan = [s.strip() for s in re.split(r'(?=\b\d+\.\s)', task) if s.strip()] if re.match(r'^\s*\d+\.', task) else []
            if not plan:
                obj = await self._ollama_chat_json(config.PLANNER_SYSTEM_PROMPT, task)
                plan = obj.get("steps", []) if obj else []

            if not plan: return False
            mission_ok = True
            try:
                for i, step in enumerate(plan, 1):
                    for k, v in self.memory.items(): step = step.replace(f"{{{k}}}", str(v))
                    print(f"\n[🚀 STEP {i}] {step}")
                    s_up = step.upper()

                    if "NAVIGATE" in s_up:
                        u = re.search(r'(https?://[^\s\'"<>]+)', step)
                        await page.goto(u.group(1), wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT)
                        await asyncio.sleep(2); continue
                    if "WAIT" in s_up:
                        sec = re.search(r"(\d+)", step); await asyncio.sleep(int(sec.group(1)) if sec else 2); continue
                    if "SCROLL" in s_up:
                        if "inside" in step.lower() or "list" in step.lower():
                            print("    🔄 Scrolling inside element...")
                            await page.evaluate("""() => { 
                                const dropdown = document.querySelector('#dropdown'); 
                                if(dropdown) { dropdown.scrollTop = dropdown.scrollHeight; }
                            }""")
                        else:
                            await page.evaluate("window.scrollBy(0, window.innerHeight)")
                        await asyncio.sleep(2); continue
                    
                    if "EXTRACT" in s_up:
                        var = re.search(r'\{(.*?)\}', step); target = (self._extract_text(step) or [""])[0].replace("’", "")
                        val = await page.evaluate(f"""() => {{
                            const row = Array.from(document.querySelectorAll('tr, .tr, [role="row"]')).find(r => r.innerText.toLowerCase().includes('{target}'));
                            if (!row) return null;
                            const cell = Array.from(row.querySelectorAll('td')).find(c => c.innerText.includes('%')) || Array.from(row.querySelectorAll('td')).find(c => !isNaN(parseFloat(c.innerText)));
                            return cell ? cell.innerText.trim() : null;
                        }}""")
                        if val and var: self.memory[var.group(1)] = val.strip(); print(f"    📦 COLLECTED: {val}"); continue
                        else: mission_ok = False; break

                    if "VERIFY" in s_up or "CHECK" in s_up:
                        exp = self._extract_text(step); found = False; print(f"    🔍 X-Ray scan for: {exp}")
                        for _ in range(12):
                            try:
                                data = await page.evaluate("""() => {
                                    let t = (document.body.innerText || "") + " ";
                                    document.querySelectorAll('*').forEach(el => { 
                                        if(el.title) t += el.title + " "; 
                                        if(el.getAttribute('value')) t += el.getAttribute('value') + " ";
                                        if(el.shadowRoot) {
                                            t += Array.from(el.shadowRoot.querySelectorAll('*')).map(e => e.innerText || e.value || '').join(' ');
                                        }
                                    });
                                    return t.toLowerCase();
                                }""")
                                if all(e.lower() in " ".join(data.replace("'", "’").split()) for e in exp): found = True; break
                            except: pass
                            await asyncio.sleep(2)
                        if found: print("    ✅ VERIFIED"); continue
                        else: print("    ❌ NOT FOUND"); mission_ok = False; break

                    if "DONE" in s_up:
                        print(f"    🏁 MISSION ACCOMPLISHED")
                        return True

                    if not await self._execute_step(page, step, strategic_context):
                        print("    ❌ ACTION FAILED"); mission_ok = False; break
                return mission_ok
            finally: await browser.close()

    async def _execute_step(self, page, step, strategic_context):
        step_l = step.lower()
        
        words = set(re.findall(r'\b[a-z0-9]+\b', step_l))
        if "drag" in words and "drop" in words: mode = "drag"
        elif "select" in words or "choose" in words: mode = "select"
        elif "type" in words or "fill" in words or "enter" in words: mode = "input"
        elif "click" in words or "double" in words: mode = "clickable"
        else: mode = "locate"

        expected = self._extract_text(step, preserve_case=(mode in ["input", "select"]))
        
        target_field_name = None
        if mode == "input" and expected:
            field_match = re.search(r'into\s+the\s+([a-zA-Z0-9_]+)\s+field', step_l) or re.search(r'into\s+([a-zA-Z0-9_]+)', step_l)
            if field_match: target_field_name = field_match.group(1).lower()

        els = []
        for i in range(5):
            els = await self.get_snapshot(page, mode, [q.lower() for q in expected])
            
            if mode != "drag":
                if target_field_name:
                    exact_matches = [el for el in els if target_field_name in el["name"].lower()]
                    if exact_matches: els = exact_matches; break
                elif expected:
                    exact_matches = []
                    for el in els:
                        el_name = el["name"].lower().strip()
                        for q in expected:
                            q_l = q.lower().strip()
                            # 🚀 ФІКС 1: Ультра-жорсткий точний збіг для пагінації (довжина <= 2 символи)
                            if len(q_l) <= 2:
                                if q_l == el_name:
                                    exact_matches.append(el)
                                    break
                            else:
                                if q_l in el_name:
                                    exact_matches.append(el)
                                    break
                    if exact_matches: els = exact_matches; break
            else:
                if els: break 
                
            if els and not expected: break
            
            if i < 4:
                await page.evaluate("window.scrollBy(0, 500)"); await asyncio.sleep(1)
        
        if not els: return False

        if mode == "locate":
            print(f"    🔎 Located: '{els[0]['name']}'")
            return True

        if mode == "drag":
            src_idx, tgt_idx = -1, -1
            if len(expected) >= 2:
                for i, el in enumerate(els):
                    if expected[0].lower() in el["name"].lower() and src_idx == -1: src_idx = i
                    if expected[1].lower() in el["name"].lower(): tgt_idx = i
            elif len(expected) == 1:
                for i, el in enumerate(els):
                    if ("drag" in el["name"].lower() or "source" in el["name"].lower()) and src_idx == -1: src_idx = i
                    if expected[0].lower() in el["name"].lower(): tgt_idx = i
            
            if src_idx == -1: src_idx = 0
            if tgt_idx == -1: tgt_idx = len(els)-1 if len(els)>1 else 0

            try:
                src_loc = page.locator(f"xpath={els[src_idx]['xpath']}").first
                tgt_loc = page.locator(f"xpath={els[tgt_idx]['xpath']}").first
                await src_loc.scroll_into_view_if_needed()
                await self._highlight(page, src_loc, "red", "#ffcccc")
                await self._highlight(page, tgt_loc, "green", "#ccffcc")
                print(f"    🔄 Dragging '{els[src_idx]['name'][:20]}' to '{els[tgt_idx]['name'][:20]}'")
                await src_loc.drag_to(tgt_loc); await asyncio.sleep(2); return True
            except: return False

        target_words = set(re.findall(r'\b[a-z0-9]{3,}\b', step_l.replace("’", "").replace("'", "")))
        for el in els:
            score = 0
            el_name = el["name"].lower()
            if target_field_name and target_field_name in el_name: score += 2000
            for exp in expected:
                if exp.lower() in el_name: score += 1000
            score += sum(10 for word in target_words if word in el_name)
            
            # 🚀 ФІКС 2: Додаємо скоринг для пошуку інпуту Scrolling Dropdown
            if not expected and ("dropdown" in step_l or "combo" in step_l) and "comboBox" in el_name:
                score += 5000
                
            el["score"] = score

        sorted_els = sorted(els, key=lambda x: x.get("score", 0), reverse=True)
        top_els = sorted_els[:8]
        
        if top_els[0].get("score", 0) >= 500:
            tid_short = 0
        else:
            clean_top_els = [{"id": el["id"], "name": el["name"]} for el in top_els]
            print(f"    🧠 LLM Fallback: Analyzing {len(clean_top_els)} ambiguous elements...")
            obj = await self._ollama_chat_json(config.EXECUTOR_SYSTEM_PROMPT.format(extracted_context="", strategic_context=strategic_context), f"STEP: {step}\nMODE: {mode.upper()}\nELEMENTS: {json.dumps(clean_top_els)}")
            chosen_id = obj.get("id", clean_top_els[0]["id"]) if obj else clean_top_els[0]["id"]
            
            tid_short = 0
            for idx, el in enumerate(top_els):
                if el["id"] == chosen_id: tid_short = idx; break
        
        target_id = top_els[tid_short]["id"]
        target_name = top_els[tid_short]["name"]
        is_real_select = top_els[tid_short].get("is_select", False)

        try:
            await self._highlight(page, target_id, is_js_id=True)
            
            if mode == "input":
                txt = expected[-1] if expected else "data"
                await page.evaluate(f"window.manulType({target_id}, '{txt}')")
                print(f"    ⌨️  Typed '{txt}' into '{target_name[:20]}'")
                if "enter" in step_l: await page.keyboard.press("Enter"); await asyncio.sleep(4)
                return True
                
            elif mode == "select" and is_real_select:
                target_xpath = top_els[tid_short]["xpath"]
                loc = page.locator(f"xpath={target_xpath}").first
                texts_to_select = expected if expected else [list(target_words)[0]]
                print(f"    🗂️  Selected {texts_to_select} from '{target_name[:20]}'")
                try: await loc.select_option(label=texts_to_select)
                except: await loc.select_option(value=[x.lower() for x in texts_to_select])
                await asyncio.sleep(2); return True
                
            else:
                print(f"    🖱️  Clicked '{target_name[:20]}'")
                if "double" in step_l: 
                    await page.evaluate(f"window.manulDoubleClick({target_id})")
                else: 
                    await page.evaluate(f"window.manulClick({target_id})")
                await asyncio.sleep(2); return True
        except Exception as ex: 
            print(f"    ❌ Execution Error: {ex}")
            return False

    async def get_snapshot(self, page, mode, expected_texts=None):
        return await page.evaluate(r"""([mode, expected_texts]) => {
            if (!window.manulElements) {
                window.manulElements = {};
                window.manulIdCounter = 0;
            }
            
            window.manulHighlight = (id, color, bg) => {
                const el = window.manulElements[id];
                if (!el) return;
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const oB = el.style.border; const oBg = el.style.backgroundColor;
                el.style.border = `4px solid ${color}`; el.style.backgroundColor = bg; el.style.transition = 'all 0.3s ease';
                setTimeout(() => { el.style.border = oB; el.style.backgroundColor = oBg; }, 2000);
            };
            window.manulClick = (id) => { 
                const el = window.manulElements[id];
                if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.click(); }
            };
            window.manulDoubleClick = (id) => { 
                const el = window.manulElements[id];
                if (el) { const ev = new MouseEvent('dblclick', { bubbles: true }); el.dispatchEvent(ev); }
            };
            window.manulType = (id, text) => { 
                const el = window.manulElements[id];
                if (el) { 
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    el.value = text; 
                    el.dispatchEvent(new Event('input', { bubbles: true })); 
                    el.dispatchEvent(new Event('change', { bubbles: true })); 
                }
            };

            const results = [];
            const collect = (root) => {
                // 🚀 ФІКС 2: Додаємо просто "input" у селектори, щоб знайти кастомні дропдауни
                const sel = mode === "input" || mode === "locate" ? "input, textarea, [contenteditable='true']" : "button, a, [role='button'], input[type='radio'], input[type='checkbox'], select, .dropbtn, summary, .ui-draggable, .ui-droppable, .option, input";
                root.querySelectorAll(sel).forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width > 1 && r.height > 1 && window.getComputedStyle(el).visibility !== 'hidden') {
                        if (!el.dataset.manulId) {
                            const newId = window.manulIdCounter++;
                            el.dataset.manulId = newId;
                            window.manulElements[newId] = el;
                        }
                        results.push(el);
                    }
                });
                root.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) collect(el.shadowRoot);
                });
            };
            collect(document);

            const getXPath = (el) => {
                if (el.id) return `//*[@id="${el.id}"]`;
                let parts = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let idx = Array.from(el.parentNode?.children || []).filter(s => s.tagName === el.tagName).indexOf(el) + 1;
                    parts.unshift(`${el.tagName.toLowerCase()}[${idx}]`);
                    el = el.parentNode;
                }
                return `/${parts.join('/')}`;
            };

            results.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);

            // 🚀 ФІКС 3: БІЛЬШЕ НІЯКОГО ОБРІЗАННЯ ТУТ!
            // Ми повертаємо весь масив, а обрізаємо його (top_els) вже в Python, щоб не збивати ID
            return results.map((el) => {
                let elName = "";
                let isSelect = false;
                if (el.tagName === "SELECT") {
                    isSelect = true;
                    let optionsText = Array.from(el.options).map(o => o.text.trim()).join(' | ');
                    elName = `${el.id || el.name || 'dropdown'} [${optionsText}]`;
                } else {
                    elName = (el.innerText || el.placeholder || el.getAttribute('value') || el.id || el.name || el.className || "item").trim();
                }
                
                // Додаємо id до імені input, щоб евристика легше його знайшла
                if (el.tagName === "INPUT") elName += ` id_${el.id || 'input'}`;
                
                return { 
                    id: parseInt(el.dataset.manulId), 
                    name: elName.substring(0, 150).replace(/\n/g, ' '), 
                    xpath: getXPath(el),
                    is_select: isSelect
                };
            });
        }""", [mode, expected_texts or []])