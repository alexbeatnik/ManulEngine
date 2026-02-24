import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine(strict=True)
    
    mission = (
        '1. Navigate to "https://github.com/microsoft/playwright-python" '
        '2. Click the file named "README.md" in the list. '
        '3. Wait 5 seconds for the markdown content to load. '
        '4. SCROLL DOWN to read the document. '
        '5. VERIFY that the page contains the text "Playwright is a Python library to automate". '
        '6. Done.'
    )
    
    context = (
        "1. CLICKING: Look for the link with the exact text 'README.md'. "
        "2. VERIFY: We are looking for the python installation command."
    )
    
    print("Testing GitHub: Clicking README.md and verifying pip install command")
    return await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())