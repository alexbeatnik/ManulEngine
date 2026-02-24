import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Scroll to the very bottom to find the ShadowDOM section. "
        "3. Locate the text input inside the Shadow Root. "
        "4. Type 'Manul Ghost Warrior' into that field. "
        "5. VERIFY that the field contains 'Manul Ghost Warrior'. "
        "6. Done."
    )
    print("🐾 Running: Shadow DOM Penetration Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())