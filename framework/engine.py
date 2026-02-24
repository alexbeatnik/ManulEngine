# framework/engine.py
import asyncio, json, re, ollama
from playwright.async_api import async_playwright
from . import config

class ManulEngine:
    def __init__(self, model: str = "qwen2.5:0.5b", headless: bool = False, strict: bool = True):
        self.model = model
        self.headless = headless
        self.strict = strict
        self.memory = {}

    async def _ollama_chat_json(self, system: str, user: str, retries: int = 2):
        for attempt in range(retries):
            try:
                resp = await asyncio.to_thread(
                    ollama.chat, model=self.model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    format="json"
                )
                content = resp["message"]["content"]
                match = re.search(r'\{.*\}', content, re.DOTALL)
                result = json.loads(match.group(0)) if match else json.loads(content)
                if result: return result
            except:
                await asyncio.sleep(1)
        return None

    def _extract_text(self, step):
        # 🧠 Розумний парсер: спочатку подвійні лапки, потім безпечні одинарні
        quotes = re.findall(r'"(.*?)"', step)
        if not quotes:
            # Ігноруємо апострофи (напр. Pallas's), шукаємо лапки з пробілами
            quotes = re.findall(r"(?:^|\s)'(.*?)'(?:$|\s|[\.,?!])", step)
        return [q.lower() for q in quotes if q]

    async def run_mission(self, task: str, strategic_context: str = ""):
        print(f"\n🐾 Manul v2.33 [Syntax Master] - Apostrophe-Proof...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--disable-gpu", "--no-sandbox"])
            page = await browser.new_page()
            
            plan_obj = await self._ollama_chat_json(config.PLANNER_SYSTEM_PROMPT, task)
            if not plan_obj or "steps" not in plan_obj:
                print("❌ PLANNER FAILED."); await browser.close(); return
            
            plan = plan_obj["steps"]
            print(f"📋 Plan: {len(plan)} steps loaded.")

            try:
                for i, step in enumerate(plan, 1):
                    step_up = step.upper()
                    print(f"\n[🚀 STEP {i}] {step}")
                    
                    if "NAVIGATE" in step_up:
                        url = re.search(r'(https?://[^\s\'"<>]+)', step)
                        if url:
                            await page.goto(url.group(1), wait_until="domcontentloaded", timeout=60000)
                            await asyncio.sleep(4); continue

                    if "WAIT" in step_up:
                        sec = re.search(r"(\d+)", step)
                        wait_time = int(sec.group(1)) if sec else 2
                        print(f"    ⏳ Waiting: {wait_time}s...")
                        await asyncio.sleep(wait_time); continue

                    if "SCROLL" in step_up:
                        print("    📜 Scrolling Down...")
                        await page.mouse.wheel(0, 600)
                        await asyncio.sleep(2); continue

                    if "VERIFY" in step_up or "CHECK" in step_up:
                        expected_quotes = self._extract_text(step)
                        if expected_quotes:
                            print(f"    🕵️ Native Scanner looking for: {expected_quotes}")
                            verified = False
                            for exp in expected_quotes:
                                try:
                                    loc = page.locator(f"text=/{exp}/i").first
                                    await loc.wait_for(state="attached", timeout=5000)
                                    await loc.scroll_into_view_if_needed(timeout=3000)
                                    await loc.evaluate("el => { el.style.border = '4px solid green'; el.style.backgroundColor = 'lightgreen'; el.style.color = 'black'; }")
                                    print(f"    ✅ VERIFIED: Found '{exp}' on the page!")
                                    verified = True
                                    break
                                except: pass
                            
                            if verified: continue
                            else:
                                print(f"    ⚠️ Text not found anywhere on the page.")
                                print(f"❌ Step {i} FAILED.")
                                if self.strict: break
                                continue

                    if "DONE" in step_up: break

                    if not await self._execute_step(page, step, strategic_context):
                        print(f"❌ Step {i} FAILED.")
                        if self.strict: break 
                
                print("\n✨ Mission finished.")
                await asyncio.sleep(4)
            finally:
                await browser.close()

    async def _execute_step(self, page, step, strategic_context):
        step_l = step.lower()
        mode = "input" if any(x in step_l for x in ["type", "fill", "enter", "search"]) else "clickable"
        
        for attempt in range(2):
            await asyncio.sleep(2)
            elements = await self.get_snapshot(page, mode)
            if not elements: continue
            
            exe_obj = await self._ollama_chat_json(
                config.EXECUTOR_SYSTEM_PROMPT.format(extracted_context="", strategic_context=strategic_context),
                f"STEP: {step}\nMODE: {mode.upper()}\nELEMENTS: {json.dumps(elements)}"
            )
            if not exe_obj: continue
            
            tid = min(exe_obj.get("id", 0), len(elements) - 1)
            expected_quotes = self._extract_text(step)

            if expected_quotes and mode != "input":
                for idx, el in enumerate(elements):
                    if any(q in el["current_content"].lower() for q in expected_quotes):
                        if tid != idx:
                            print(f"    🧠 Smart Override: Target fixed to ID {idx}")
                            tid = idx
                        break

            xpath = elements[tid]["xpath"]
            target = f"xpath={xpath}"
            
            try:
                loc = page.locator(target).first
                if mode == "input":
                    val = expected_quotes[-1] if expected_quotes else "data"
                    print(f"    🤔 AI Action: Target ID {tid} ({elements[tid]['name']})")
                    print(f"    ⌨️  Inserting natively: '{val}'")
                    await loc.evaluate("el => { el.focus(); el.select(); el.style.border = '4px solid red'; }")
                    await asyncio.sleep(0.5)
                    await page.keyboard.insert_text(val)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    return True
                
                await loc.evaluate("el => { el.style.border = '4px solid red'; }")
                await loc.click(force=True, timeout=10000)
                print(f"    🖱️  Clicked ID {tid} ({elements[tid]['current_content'][:15]}...)")
                return True
            except: continue
        return False

    async def get_snapshot(self, page, mode):
        return await page.evaluate(r"""(mode) => {
            const getEls = (sel) => Array.from(document.querySelectorAll(sel)).filter(el => {
                const r = el.getBoundingClientRect();
                const text = (el.innerText || "").toLowerCase();
                const isNoise = el.closest('footer, .copyright, .user-links') || 
                               text.includes('щоденники') || text.includes('diaries') || 
                               text.includes('допомога');
                if (el.tagName === 'INPUT' && ['hidden', 'checkbox', 'radio'].includes(el.type)) return false;
                return r.width > 0 && r.height > 0 && !isNoise;
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
            
            let tags = (mode === 'input') ? 'input, textarea' : 'button, a, .search_results_list a';
            return getEls(tags).slice(0, 15).map((el, i) => ({
                id: i, tag: el.tagName,
                name: (el.placeholder || el.id || el.name || "").substring(0, 15),
                current_content: (el.innerText || el.value || "").replace(/\s+/g, ' ').trim().substring(0, 30),
                xpath: getXPath(el)
            }));
        }""", mode)