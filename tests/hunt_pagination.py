import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Scroll to the 'Pagination Web Table'. "
        "3. Click on page '3' in the pagination list. "
        "4. Select the checkbox for the product with ID '13'. "
        "5. VERIFY that the product 'Portable Charger' is on the page. "
        "6. Done."
    )
    print("🐾 Running: Table Pagination Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())