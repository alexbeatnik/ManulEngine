import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Find 'Field1' and verify it has 'Hello World!'. "
        "3. DOUBLE CLICK the button that says 'Copy Text'. "
        "4. VERIFY that 'Field2' now also contains 'Hello World!'. "
        "5. Done."
    )
    print("🐾 Running: Mouse Double Click Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())