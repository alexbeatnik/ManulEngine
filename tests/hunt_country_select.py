import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Scroll to the 'Country' dropdown list. "
        "3. Select 'United Kingdom' from the dropdown. "
        "4. VERIFY that the selected country is 'United Kingdom'. "
        "5. Done."
    )
    print("🐾 Running: Dropdown Selection Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())