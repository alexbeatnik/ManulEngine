import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Find the radio button for 'Male' and click it. "
        "3. VERIFY that 'Male' is selected. "
        "4. Done."
    )
    print("🐾 Running: Gender Radio Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())