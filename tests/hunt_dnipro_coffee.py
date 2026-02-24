import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. Navigate to https://www.openstreetmap.org/. "
        "2. Find and locate the search input box on the page. " 
        "3. Wait 3 seconds to observe the map. "
        "4. SCROLL DOWN to see the footer area. "
        "5. VERIFY that the page contains 'OpenStreetMap'. "
        "6. Done."
    )
    
    context = (
        "1. OBJECTIVE: We only want to verify the presence of the search UI. "
        "2. ACTION: Do NOT type any search queries. Just locate the element."
    )
    
    print("Testing OpenStreetMap: UI Presence Mission (No Typing)")
    return await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())