import asyncio
import json
import re
import ollama
from playwright.async_api import async_playwright
from . import config

class ManulEngine:
    def __init__(self, model="qwen2.5:3b", blueprints=None):
        self.model = model
        self.memory = {}

    async def run_mission(self, task, strategic_context=""):
        print(f"\n🐾 Manul v2.02 [3B Whisperer] is out for the hunt...")
        try:
            resp = ollama.chat(model=self.model, messages=[
                {"role": "system", "content": config.PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": task}
            ], format="json")
            plan = json.loads(resp['message']['content']).get("steps") or []
        except Exception as e:
            print(f"❌ Planning failure: {e}"); return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            for i, step in enumerate(plan, 1):
                step = str(step)
                print(f"\n[🚀 STEP {i}] {step}")
                
                if any(k in step.upper() for k in ["NAVIGATE", "URL", "LINK", "GO TO"]):
                    url_match = re.search(r'(https?://[^\s\'"<>]+)', step)
                    if url_match:
                        try:
                            print(f"   🌐 Navigating to {url_match.group(1)}...")
                            await page.goto(url_match.group(1).strip('"'), wait_until="domcontentloaded", timeout=15000)
                            await asyncio.sleep(1.5) 
                        except:
                            print(f"   ⚠️ Navigation timeout, proceeding anyway...")
                        continue

                if "WAIT" in step.upper() and "UNTIL" not in step.upper():
                    wait_match = re.search(r"(\d+)", step)
                    sec = int(wait_match.group(1)) if wait_match else 2
                    print(f"   ⏳ Waiting for {sec}s...")
                    await asyncio.sleep(sec)
                    continue

                if "DONE" in step.upper(): break
                step_success = False
                error_feedback = ""

                for attempt in range(3):
                    is_heavy = any(k in step.upper() for k in ["VERIFY", "EXTRACT", "TABLE", "H1", "H2"])
                    await asyncio.sleep(2.0 if is_heavy else 0.8)
                    
                    elements = await self.get_snapshot(page, step)
                    
                    exe_resp = ollama.chat(model=self.model, messages=[
                        {"role": "system", "content": config.EXECUTOR_SYSTEM_PROMPT.format(
                            extracted_context=json.dumps(self.memory),
                            strategic_context=strategic_context
                        )},
                        {"role": "user", "content": f"STEP: {step}\nELEMENTS: {json.dumps(elements)}\n{error_feedback}"}
                    ])
                    
                    raw_text = exe_resp['message']['content']
                    decision = self.parse_hybrid(raw_text)
                    
                    action = decision.get("action")
                    tid = decision.get("id")
                    thought = decision.get("thought", raw_text[:60]).lower()
                    print(f"   🤔 Thought: {thought[:120]}...")

                    if tid is not None and not action:
                        if any(k in step.lower() for k in ["type", "fill", "enter"]): action = "type"
                        elif "extract" in step.lower(): action = "extract"
                        elif any(k in step.lower() for k in ["verify", "find", "check"]): action = "verified"
                        elif "scroll" in step.lower(): action = "scroll"
                        else: action = "click"

                    try:
                        target_id = tid if (tid is not None and tid < len(elements)) else 0
                        loc = page.locator(f'[data-manul-id="{target_id}"]').first

                        if action == "type":
                            quotes = re.findall(r"['\"](.*?)['\"]", step)
                            val = quotes[-1] if quotes else "data"
                            for k, v in self.memory.items():
                                val = val.replace(f"{{{k}}}", str(v))
                            
                            await loc.scroll_into_view_if_needed()
                            await loc.click()
                            await loc.fill("") 
                            await loc.type(val, delay=40)
                            
                            if any(k in step.lower() for k in ["search", "enter", "submit"]):
                                search_btn = page.locator('button[type="submit"], button:has-text("Search"), .search-button, i.search-icon').first
                                if await search_btn.is_visible():
                                    await search_btn.click()
                                    print(f"   🖱️  Clicked Search Button")
                                else:
                                    await page.keyboard.press("Enter")
                                    print(f"   ⌨️  Pressed Enter")
                                
                                try: await page.wait_for_load_state("load", timeout=5000)
                                except: await asyncio.sleep(1.5)
                            else:
                                print(f"   ⌨️  Filled '{val}' into ID {target_id}")
                                
                            step_success = True; break
                        
                        elif action == "click":
                            await loc.scroll_into_view_if_needed()
                            await loc.click(force=True, timeout=5000)
                            print(f"   🖱️  Clicked ID {target_id}")
                            step_success = True; break
                        
                        elif action == "scroll":
                            await page.mouse.wheel(0, 600)
                            await asyncio.sleep(1.0)
                            print(f"   📜 SPA-Scrolling...")
                            step_success = True; break
                        
                        elif action == "extract":
                            raw_content = elements[target_id]['current_content']
                            val_match = re.findall(r"[\d\.%]+", raw_content)
                            val = val_match[0] if val_match else raw_content
                            var_name = re.search(r"\{(.*?)\}", step).group(1) if "{" in step else "val"
                            self.memory[var_name] = val
                            print(f"   💾 Saved: '{val}' into {{{var_name}}}")
                            step_success = True; break

                        elif action == "verified" or "verify" in step.lower():
                            expected_match = re.search(r"['\"](.*?)['\"]", step)
                            expected = expected_match.group(1).lower() if expected_match else ""
                            actual = elements[target_id]['current_content'].lower()
                            if expected in actual or not expected:
                                print(f"   ✅ VERIFIED: '{expected}' found in ID {target_id}")
                                step_success = True; break
                            else:
                                error_feedback = f"⚠️ Expected '{expected}' not found. Try scrolling or checking another ID."
                                print(f"   ⚠️ Missed verification for '{expected}'")

                    except Exception as e:
                        error_feedback = f"⚠️ Action Error: {str(e)[:40]}. Pick a different ID."
                        print(f"   {error_feedback}")
                
                if not step_success and "DONE" not in step.upper():
                    print(f"💨 Step failed. Continuing mission...")

            print("\n✨ Mission finished.")
            await browser.close()

    def parse_hybrid(self, text):
        decision = {}
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try: decision = json.loads(json_match.group(0))
            except: pass
        if not decision.get("id"):
            id_res = re.search(r"ID[:\s=]+(\d+)", text, re.I)
            if id_res: decision["id"] = int(id_res.group(1))
        if not decision.get("action"):
            for act in ["click", "type", "scroll", "extract", "verified"]:
                if act in text.lower():
                    decision["action"] = act; break
        return decision

    async def get_snapshot(self, page, step):
        return await page.evaluate("""() => {
            const getEls = (sel) => Array.from(document.querySelectorAll(sel)).filter(el => {
                const r = el.getBoundingClientRect();
                const isNoise = el.closest('.copyright, .layers-ui, .vector-sidebar-container, #repos-sticky-header');
                return r.width > 0 && r.height > 0 && !isNoise;
            });

            const priorityTags = 'h1, input, textarea, button, h2, h3, p';
            const extraTags = 'a, td, th, span, li';
            
            const combined = [...getEls(priorityTags), ...getEls(extraTags)].slice(0, 65);

            return combined.map((el, i) => {
                el.setAttribute('data-manul-id', i);
                
                let metadata = el.name || el.id || el.getAttribute('aria-label') || el.placeholder || "";
                if (el.tagName.toLowerCase() === 'a' && el.href) {
                    metadata += " href:" + el.href.replace(window.location.origin, ''); 
                }
                if (el.tagName.toLowerCase() === 'input' && el.type) {
                    metadata += " type:" + el.type;
                }

                return { 
                    id: i, tag: el.tagName, 
                    name: metadata.trim(),
                    current_content: (el.value || el.innerText || "").replace(/\\s+/g, ' ').trim().substring(0, 100) 
                };
            });
        }""")