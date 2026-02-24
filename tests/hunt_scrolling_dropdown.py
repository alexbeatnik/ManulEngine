import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Find the 'Scrolling DropDown' input field. "
        "3. Click the input to open the large list. "
        "4. SCROLL DOWN inside the list to find 'Item 100'. "
        "5. Select 'Item 100'. "
        "6. VERIFY that the input field shows 'Item 100'. "
        "7. Done."
    )
    print("🐾 Running: Infinite Scroll Dropdown Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())