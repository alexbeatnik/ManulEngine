import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Locate the 'Colors' multi-selection box. "
        "3. Select both 'Red' and 'Blue'. "
        "4. VERIFY that 'Red' and 'Blue' are selected. "
        "5. Done."
    )
    print("🐾 Running: Multi-select Box Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())