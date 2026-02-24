import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. Navigate to https://www.openstreetmap.org/ "
        "2. Type 'Kyiv' into the search input and press Enter. "
        "3. Wait for the results to appear in the left sidebar. "
        "4. Find a result that contains 'Kyiv' or 'Київ' and verify it. "
        "5. Done."
    )
    
    print("Testing OpenStreetMap search functionality for 'Kyiv'")
    await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())