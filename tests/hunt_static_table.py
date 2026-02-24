import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Scroll down to find the 'BookTable'. "
        "3. Locate the row where the BookName is 'Learn Selenium'. "
        "4. EXTRACT the Price of 'Learn Selenium' into {price_val}. "
        "5. VERIFY that {price_val} contains '300'. "
        "6. Done."
    )
    print("🐾 Running: Static Table Data Extraction")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())