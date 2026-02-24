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
        quotes = re.findall(r'"(.*?)"', step)
        if not quotes:
            quotes = re.findall(r"(?:^|\s)'(.*?)'(?:$|\s|[\.,?!])", step)
        return [q.lower() for q in quotes if q]

    async def run_mission(self, task: str, strategic_context: str = ""):
        print(f"\n🐾 Manul v2.39 [Native Planner] - Bypassing AI Amnesia...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=["--disable-gpu", "--no-sandbox"])
            page = await browser.new_page()
            
            # 🧠 NATIVE PLANNER (No AI)
            plan = []
            if re.match(r'^\s*\d+\.', task):
                # Split mission by pattern "1. ", "2. " etc.
                raw_steps = re.split(r'(?=\b\d+\.\s)', task)
                plan = [s.strip() for s in raw_steps if s.strip()]
            else:
                print("    🤖 Using AI Planner for unstructured task...")
                plan_obj = await self._ollama_chat_json(config.PLANNER_SYSTEM_PROMPT, task)
                if plan_obj and "steps" in plan_obj:
                    plan = plan_obj["steps"]

            if not plan:
                print("❌ PLANNER FAILED: Could not parse steps."); await browser.close(); return
            
            print(f"📋 Plan: {len(plan)} steps loaded flawlessly.")

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
                        print("    📜 Scrolling Down natively...")
                        await page.evaluate("window.scrollBy(0, 1000);")
                        await asyncio.sleep(2); continue

                    if "VERIFY" in step_up or "CHECK" in step_up:
                        expected_quotes = self._extract_text(step)
                        if expected_quotes:
                            print(f"    🕵️ Native Scanner looking for: {expected_quotes}")
                            verified = False
                            raw_page_text = ""
                            
                            # 🛡️ GUARDIAN: Wait if the page is currently navigating/reloading
                            for attempt in range(4):
                                try:
                                    # Wait for DOM readiness first
                                    await page.wait_for_load_state("domcontentloaded", timeout=3000)
                                    raw_page_text = await page.evaluate("document.body.innerText.toLowerCase()")
                                    break
                                except Exception:
                                    print("    🔄 Page is navigating, waiting for DOM to settle...")
                                    await asyncio.sleep(1.5)
                            
                            clean_page_text = " ".join(raw_page_text.split())
                            
                            for exp in expected_quotes:
                                clean_exp = " ".join(exp.split())
                                if clean_exp in clean_page_text:
                                    print(f"    ✅ VERIFIED: Found '{exp}' in normalized DOM!")
                                    verified = True
                                    try:
                                        loc = page.get_by_text(exp, exact=False).first
                                        await loc.evaluate("el => { el.style.border = '4px solid green'; }")
                                    except: pass
                                    break
                            
                            if verified: continue
                            else:
                                print(f"    ⚠️ Text not found anywhere on the page.")
                                print(f"    🩻 X-RAY VISION (first 150 chars): {clean_page_text[:150]}...")
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
        expected_quotes = self._extract_text(step)
        
        for attempt in range(2):
            await asyncio.sleep(2)
            # Protection when taking a snapshot during page navigation
            try:
                elements = await self.get_snapshot(page, mode, expected_quotes)
            except Exception:
                await asyncio.sleep(2)
                continue
                
            if not elements: continue
            
            exe_obj = await self._ollama_chat_json(
                config.EXECUTOR_SYSTEM_PROMPT.format(extracted_context="", strategic_context=strategic_context),
                f"STEP: {step}\nMODE: {mode.upper()}\nELEMENTS: {json.dumps(elements)}"
            )
            if not exe_obj: continue
            
            tid = min(exe_obj.get("id", 0), len(elements) - 1)
            
            if expected_quotes and mode != "input":
                for idx, el in enumerate(elements):
                    if any(q in el["current_content"].lower() for q in expected_quotes):
                        if tid != idx:
                            print(f"    🧠 Smart Override: Engine fixed target to ID {idx}")
                            tid = idx
                        break

            xpath = elements[tid]["xpath"]
            target = f"xpath={xpath}"
            
            try:
                loc = page.locator(target).first
                if mode == "input":
                    val = expected_quotes[-1] if expected_quotes else "data"
                    print(f"    🤔 AI Action: Target ID {tid}")
                    print(f"    ⌨️  Inserting natively: '{val}'")
                    await loc.evaluate("el => { el.focus(); el.select(); el.style.border = '4px solid red'; }")
                    await asyncio.sleep(0.5)
                    await page.keyboard.insert_text(val)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    return True
                
                await loc.evaluate("el => { el.style.border = '4px solid red'; }")
                await loc.click(force=True, timeout=10000)
                print(f"    🖱️  Clicked ID {tid}")
                return True
            except: continue
        return False

    async def get_snapshot(self, page, mode, expected_texts=None):
        if expected_texts is None: expected_texts = []
        return await page.evaluate(r"""([mode, expected_texts]) => {
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
            let allEls = getEls(tags);

            if (expected_texts && expected_texts.length > 0) {
                allEls.sort((a, b) => {
                    const textA = (a.innerText || a.value || a.placeholder || "").toLowerCase();
                    const textB = (b.innerText || b.value || b.placeholder || "").toLowerCase();
                    
                    let aMatch = expected_texts.some(t => textA.includes(t)) ? 1 : 0;
                    let bMatch = expected_texts.some(t => textB.includes(t)) ? 1 : 0;
                    
                    if (aMatch && expected_texts.some(t => textA.trim() === t)) aMatch = 2;
                    if (bMatch && expected_texts.some(t => textB.trim() === t)) bMatch = 2;

                    return bMatch - aMatch;
                });
            }

            return allEls.slice(0, 15).map((el, i) => ({
                id: i, tag: el.tagName,
                name: (el.placeholder || el.id || el.name || "").substring(0, 15),
                current_content: (el.innerText || el.value || "").replace(/\s+/g, ' ').trim().substring(0, 30),
                xpath: getXPath(el)
            }));
        }""", [mode, expected_texts])