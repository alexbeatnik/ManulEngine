import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. Navigate to https://archive.org/. "
        "2. Fill the Wayback Machine search box with 'google' and press Enter. "
        "3. SCROLL TO the calendar section. "
        "4. Verify that the page content contains 'Calendar'. "
        "5. Done."
    )
    
    context = (
        "1. WAYBACK MACHINE: The input field is usually at the top with a placeholder like 'http://'. "
        "2. LOADING: Archive.org can be slow. If you don't see the calendar immediately, use 'scroll' to trigger loading. "
        "3. VERIFICATION: The word 'Calendar' or a year grid (2026, 2025) indicates success."
    )
    
    print(context)
    await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())