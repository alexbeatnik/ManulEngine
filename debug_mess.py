import asyncio, sys
sys.path.insert(0, '.')
from playwright.async_api import async_playwright
from engine import ManulEngine
from engine.test.test_10_mess import MESS_DOM

async def test():
    manul = ManulEngine(headless=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(MESS_DOM)
        
        # Test 28: EXTRACT time
        manul.memory.clear()
        try:
            res = await manul._handle_extract(page, 'EXTRACT time into {t}')
            print(f'Result: {res}')
            print(f'Memory: {manul.memory}')
        except Exception as e:
            import traceback
            traceback.print_exc()
        
        # Test 29: Click 'Read Terms'
        try:
            el = await manul._resolve_element(page, "Click 'Read Terms'", 'clickable', ['Read Terms'], None, '', set())
            found = el.get('html_id') if el else None
            print(f'Element for Read Terms: {found}')
        except Exception as e:
            import traceback
            traceback.print_exc()
        
        await browser.close()

asyncio.run(test())
