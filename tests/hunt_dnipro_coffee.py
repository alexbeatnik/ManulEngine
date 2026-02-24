import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. Navigate to https://www.openstreetmap.org/. "
        "2. Type 'Cafe Dnipro' into the search box and press Enter. "
        "3. Wait 3 seconds for the results to load. "
        "4. SCROLL DOWN the sidebar to see more results. "
        "5. Find and VERIFY that the results contain the text 'Cafe' or 'Кафе'. "
        "6. Done."
    )
    
    context = (
        "1. RESULTS: OSM sidebar links often start with the type of place (e.g., 'Cafe: White'). "
        "2. VERIFICATION: If you see 'Cafe' or 'Кафе' in the text, it is 100% SUCCESS. "
        "3. ACTION: You MUST return 'action': 'verified' to finish the hunt."
    )
    
    print("Testing OpenStreetMap search for cafes in Dnipro")
    return await manul.run_mission(mission, strategic_context=context)


if __name__ == "__main__":
    asyncio.run(main())