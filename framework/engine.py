# framework/engine.py
import asyncio, json, re, ollama, os
from playwright.async_api import async_playwright
from . import config

class ManulEngine:
    def __init__(self, model: str = config.DEFAULT_MODEL, headless: bool = True, **kwargs):
        self.model, self.headless, self.memory = model, headless, {}

    async def _ollama_chat_json(self, system: str, user: str):
        try:
            resp = await asyncio.to_thread(ollama.chat, model=self.model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], format="json")
            c = resp["message"]["content"]
            m = re.search(r'\{.*\}', c, re.DOTALL)
            return json.loads(m.group(0)) if m else json.loads(c)
        except: return None

    def _extract_text(self, step, preserve_case=False):
        for k, v in self.memory.items(): step = step.replace(f"{{{k}}}", str(v))
        step = step.replace("'", "’")
        q = re.findall(r'["“](.*?)["”]', step) or re.findall(r"(?:^|\s)['’](.*?)['’]", step)
        return [x if preserve_case else x.lower() for x in q if x]

    async def run_mission(self, task: str, strategic_context: str = ""):
        print(f"\n🐾 Manul v3.2 [The Final Peace]")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
            page = await browser.new_page()
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
                        u = re.search(r'(https?://[^\s\'"<>]+)', step); await page.goto(u.group(1), wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT); await asyncio.sleep(2); continue
                    if "WAIT" in s_up:
                        sec = re.search(r"(\d+)", step); await asyncio.sleep(int(sec.group(1)) if sec else 2); continue
                    if "SCROLL" in s_up:
                        await page.evaluate("window.scrollBy(0, window.innerHeight)"); await asyncio.sleep(2); continue
                    if "EXTRACT" in s_up:
                        var = re.search(r'\{(.*?)\}', step); target = (self._extract_text(step) or [""])[0].replace("’", "")
                        val = await page.evaluate(f"""() => {{
                            const row = Array.from(document.querySelectorAll('tr, .tr, [role="row"]')).find(r => r.innerText.toLowerCase().includes('{target}'));
                            const cell = row ? Array.from(row.querySelectorAll('td, .td, [role="gridcell"]')).find(c => c.innerText.includes('%')) : null;
                            return cell ? cell.innerText : null;
                        }}""")
                        if val and var: self.memory[var.group(1)] = val.strip(); print(f"    📦 COLLECTED: {val}"); continue
                        else: mission_ok = False; break

                    if "VERIFY" in s_up or "CHECK" in s_up:
                        exp = self._extract_text(step); found = False; print(f"    🔍 X-Ray scan for: {exp}")
                        for _ in range(12):
                            try:
                                data = await page.evaluate("""() => {
                                    let t = (document.body.innerText || "") + " ";
                                    document.querySelectorAll('*').forEach(el => { if(el.title) t += el.title + " "; if(el.dataset && el.dataset.prefix) t += el.dataset.prefix + " "; });
                                    return t.toLowerCase();
                                }""")
                                if all(e.lower() in " ".join(data.replace("'", "’").split()) for e in exp): found = True; break
                            except: pass
                            await asyncio.sleep(2)
                        if found: print("    ✅ VERIFIED"); continue
                        else: print("    ❌ NOT FOUND"); mission_ok = False; break

                    if "DONE" in s_up:
                        if not os.path.exists("results"): os.makedirs("results")
                        p_name = f"results/pass_{re.sub(r'[^a-zA-Z]', '_', task[:15])}.png"
                        await page.screenshot(path=p_name); print(f"    📸 SAVED: {p_name}"); return True

                    if not await self._execute_step(page, step, strategic_context):
                        print("    ❌ ACTION FAILED"); mission_ok = False; break
                return mission_ok
            finally: await browser.close()

    async def _execute_step(self, page, step, strategic_context):
        step_l = step.lower()
        mode = "input" if any(x in step_l for x in ["type", "fill", "enter", "search"]) else "clickable"
        expected = self._extract_text(step, preserve_case=(mode=="input"))
        els = []
        for _ in range(4):
            els = await self.get_snapshot(page, mode, [q.lower() for q in expected])
            if els: break
            await asyncio.sleep(1.5)
        if not els: return False

        # --- 🕵️‍♂️ СПОГЛЯДАННЯ (LOCATE ONLY) ---
        if ("find" in step_l or "locate" in step_l) and "click" not in step_l:
            print(f"    🔎 Located element: '{els[0]['name']}'")
            return True

        obj = await self._ollama_chat_json(config.EXECUTOR_SYSTEM_PROMPT.format(extracted_context="", strategic_context=strategic_context), f"STEP: {step}\nMODE: {mode.upper()}\nELEMENTS: {json.dumps(els)}")
        tid = min(obj.get("id", 0), len(els)-1) if obj else 0
        words = set(re.findall(r'\b[a-z]{3,}\b', step_l.replace("’", "").replace("'", "")))
        for idx, el in enumerate(els):
            if any(w in el["name"].lower() for w in words): tid = idx; break

        try:
            xpath = els[tid]["xpath"]; loc = page.locator(f"xpath={xpath}").first
            if mode == "input":
                txt = expected[-1] if expected else "data"
                await loc.evaluate(f"(el) => {{ el.focus(); el.scrollIntoView(); }}"); await loc.fill(txt)
                print(f"    ⌨️  Ghost-typed '{txt}' into '{els[tid]['name']}'")
                if "enter" in step_l: await asyncio.sleep(0.5); await page.keyboard.press("Enter"); await asyncio.sleep(5)
                return True
            else:
                print(f"    🖱️  Clicked '{els[tid]['name']}'"); await loc.evaluate("el => el.click()"); await asyncio.sleep(3); return True
        except: return False

    async def get_snapshot(self, page, mode, expected_texts=None):
        return await page.evaluate(r"""([mode, expected_texts]) => {
            const getXPath = (el) => {
                if (el.id) return `//*[@id="${el.id}"]`;
                const parts = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let idx = Array.from(el.parentNode.children).filter(s => s.tagName === el.tagName).indexOf(el) + 1;
                    parts.unshift(`${el.tagName.toLowerCase()}[${idx}]`);
                    el = el.parentNode;
                }
                return `/${parts.join('/')}`;
            };
            let sel = mode === "input" ? "input:not([type='hidden']), textarea, [contenteditable='true']" : "button, a, [role='button'], summary, .search-button, #searchbutton, .search_icon, [type='submit']";
            let els = Array.from(document.querySelectorAll(sel)).filter(el => { const r = el.getBoundingClientRect(); return r.width > 2 && r.height > 2 && window.getComputedStyle(el).display !== 'none'; });
            els.sort((a, b) => {
                const tA = (a.innerText || a.value || a.name || a.id || a.placeholder || "").toLowerCase();
                const tB = (b.innerText || b.value || b.name || b.id || b.placeholder || "").toLowerCase();
                return expected_texts.some(t => tB.includes(t)) - expected_texts.some(t => tA.includes(t));
            });
            return els.slice(0, 20).map((el, i) => ({ id: i, name: (el.innerText || el.placeholder || el.name || el.id || "item").trim().substring(0, 35), xpath: getXPath(el) }));
        }""", [mode, expected_texts or []])