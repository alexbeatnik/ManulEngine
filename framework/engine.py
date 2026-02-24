# framework/engine.py
import asyncio, json, re, ollama, os
from playwright.async_api import async_playwright
from . import config

class ManulEngine:
    def __init__(self, model: str = "qwen2.5:0.5b", headless: bool = False, strict: bool = True):
        self.model, self.headless, self.strict, self.memory = model, headless, strict, {}

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
        print(f"\n🐾 Manul v2.51 [The Patient Hunter] - Patient but precise...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--no-sandbox"])
            page = await browser.new_page()
            plan = [s.strip() for s in re.split(r'(?=\b\d+\.\s)', task) if s.strip()] if re.match(r'^\s*\d+\.', task) else []
            if not plan:
                obj = await self._ollama_chat_json(config.PLANNER_SYSTEM_PROMPT, task)
                plan = obj.get("steps", []) if obj else []

            if not plan: return False
            ok = True
            try:
                for i, step in enumerate(plan, 1):
                    for k, v in self.memory.items(): step = step.replace(f"{{{k}}}", str(v))
                    print(f"\n[🚀 STEP {i}] {step}")
                    s_up = step.upper()
                    
                    if "NAVIGATE" in s_up:
                        u = re.search(r'(https?://[^\s\'"<>]+)', step)
                        if u: await page.goto(u.group(1), wait_until="domcontentloaded"); continue
                    if "WAIT" in s_up:
                        sec = re.search(r"(\d+)", step); await asyncio.sleep(int(sec.group(1)) if sec else 2); continue
                    if "SCROLL" in s_up:
                        await page.evaluate("window.scrollBy(0, 600)"); await asyncio.sleep(1.5); continue
                    if "EXTRACT" in s_up:
                        var = re.search(r'\{(.*?)\}', step)
                        target = (self._extract_text(step) or [""])[0].replace("’", "")
                        val = await page.evaluate(f"""() => {{
                            const r = Array.from(document.querySelectorAll('tr, .tr, [role="row"]')).find(x => x.innerText.toLowerCase().includes('{target}'));
                            if(!r) return null;
                            const c = Array.from(r.querySelectorAll('td, .td, [role="gridcell"]')).find(x => x.innerText.includes('%'));
                            return c ? c.innerText : null;
                        }}""")
                        if val and var: self.memory[var.group(1)] = val.strip(); print(f"    📦 COLLECTED: {val}"); continue
                        else: ok = False; break
                    if "VERIFY" in s_up or "CHECK" in s_up:
                        exp = self._extract_text(step)
                        found = False
                        for _ in range(6): # More retries for verification
                            try:
                                txt = await page.evaluate("document.body ? document.body.innerText.toLowerCase() : ''")
                                clean = " ".join(txt.replace("'", "’").split())
                                if any(e in clean for e in exp): found = True; break
                            except: pass
                            await asyncio.sleep(2)
                        if found: print("    ✅ VERIFIED"); continue
                        else: print("    ❌ NOT FOUND"); ok = False; break
                    if "DONE" in s_up:
                        if not os.path.exists("results"): os.makedirs("results")
                        path = f"results/final_report.png"
                        await page.screenshot(path=path); print(f"    📸 SAVED: {path}")
                        return True
                    if not await self._execute_step(page, step, strategic_context):
                        print("    ❌ ACTION FAILED")
                        ok = False; break
                return ok
            except Exception as e:
                print(f"    🚨 ERROR: {str(e)[:50]}"); return False
            finally: await browser.close()

    async def _execute_step(self, page, step, strategic_context):
        for k, v in self.memory.items(): step = step.replace(f"{{{k}}}", str(v))
        mode = "input" if any(x in step.lower() for x in ["type", "fill", "enter", "search"]) else "clickable"
        expected = self._extract_text(step, preserve_case=(mode=="input"))
        
        # 🕵️‍♂️ PATIENT SEARCH: Try multiple times to find ANY elements before asking AI
        els = []
        for _ in range(4):
            els = await self.get_snapshot(page, mode, [q.lower() for q in expected])
            if els: break
            await asyncio.sleep(2)
        
        if not els: return False
        
        obj = await self._ollama_chat_json(config.EXECUTOR_SYSTEM_PROMPT.format(extracted_context="", strategic_context=strategic_context), f"STEP: {step}\nMODE: {mode.upper()}\nELEMENTS: {json.dumps(els)}")
        tid = min(obj.get("id", 0), len(els)-1) if obj else 0
        
        # Smart Target Override
        words = set(re.findall(r'\b[a-z]{3,}\b', step.lower().replace("’", "").replace("'", "")))
        for idx, el in enumerate(els):
            if any(w in el["name"].lower() for w in words): tid = idx; break
        
        try:
            loc = page.locator(f"xpath={els[tid]['xpath']}").first
            if mode == "input":
                await loc.click(timeout=5000)
                await loc.fill("")
                await page.keyboard.insert_text(expected[-1] if expected else "data")
                print(f"    ⌨️  Entered data into '{els[tid]['name']}'")
                if "enter" in step.lower(): 
                    await page.keyboard.press("Enter")
                    await page.wait_for_load_state("networkidle", timeout=5000).catch(lambda e: None)
                return True
            else:
                print(f"    🖱️  Clicked '{els[tid]['name']}'")
                await loc.click(force=True, timeout=5000)
                # Wait specifically after clicks that might cause navigation
                await asyncio.sleep(2) 
                return True
        except: return False

    async def get_snapshot(self, page, mode, expected_texts=None):
        return await page.evaluate(r"""([mode, expected_texts]) => {
            const getEls = (sel) => Array.from(document.querySelectorAll(sel)).filter(el => {
                const r = el.getBoundingClientRect();
                const isVisible = r.width > 0 && r.height > 0;
                return isVisible && !el.closest('footer');
            });
            function getXPath(el) {
                if (el.id) return `//*[@id="${el.id}"]`;
                const parts = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let idx = Array.from(el.parentNode.children).filter(s => s.tagName === el.tagName).indexOf(el) + 1;
                    parts.unshift(`${el.tagName.toLowerCase()}[${idx}]`);
                    el = el.parentNode;
                }
                return `/${parts.join('/')}`;
            }
            let tags = (mode === 'input') ? 'input, textarea' : 'button, a, [role="button"], span, i, summary';
            let els = getEls(tags);
            els.sort((a, b) => {
                const tA = (a.innerText || a.name || a.id || a.placeholder || "").toLowerCase();
                const tB = (b.innerText || b.value || b.name || b.id || b.placeholder || "").toLowerCase();
                return expected_texts.some(t => tB.includes(t)) - expected_texts.some(t => tA.includes(t));
            });
            return els.slice(0, 15).map((el, i) => ({ 
                id: i, 
                name: (el.innerText || el.name || el.id || el.placeholder || "item").trim().substring(0, 20), 
                xpath: getXPath(el) 
            }));
        }""", [mode, expected_texts])