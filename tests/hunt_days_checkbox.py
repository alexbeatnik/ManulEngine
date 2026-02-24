import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Click the checkboxes for 'Monday', 'Wednesday' and 'Friday'. "
        "3. VERIFY that 'Monday' is checked. "
        "4. VERIFY that 'Sunday' is not checked. "
        "5. Done."
    )
    print("🐾 Running: Checkbox Multi-selection Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())