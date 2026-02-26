import asyncio, sys
sys.path.insert(0, '.')
from playwright.async_api import async_playwright
from engine import ManulEngine
from engine.test.test_10_mess import MESS_DOM, TESTS

async def test():
    manul = ManulEngine(headless=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(MESS_DOM)
        
        for t in TESTS[:30]:
            manul.last_xpath = None
            
            if t.get("ex"):
                manul.memory.clear()
                try:
                    res = await manul._handle_extract(page, t["step"])
                    actual = manul.memory.get(t["var"], None)
                    status = "PASS" if res and actual == t["val"] else f"FAIL got '{actual}' exp '{t['val']}'"
                except Exception as e:
                    status = f"ERROR: {e}"
                    
            elif t.get("ver"):
                try:
                    result = await manul._handle_verify(page, t["step"])
                    status = "PASS" if result == t["res"] else f"FAIL verify={result}"
                except Exception as e:
                    status = f"ERROR: {e}"
                    
            elif "if exists" in t["step"] or "optional" in t["step"]:
                try:
                    result = await manul._execute_step(page, t["step"], "")
                    status = "PASS" if result else "FAIL optional"
                except Exception as e:
                    status = f"ERROR: {e}"
                    
            else:
                try:
                    el = await manul._resolve_element(page, t["step"], t["m"], t["st"], t["tf"], "", set())
                    found = el.get('html_id') if el else None
                    status = "PASS" if found == t["exp"] else f"FAIL got '{found}' exp '{t['exp']}'"
                except Exception as e:
                    status = f"ERROR: {e}"
            
            print(f"Test {t['n']}: {status}")
            
            # Check if page is still valid
            try:
                url = page.url
            except:
                print("  PAGE IS DEAD!")
                break
        
        await browser.close()

asyncio.run(test())
