import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/ "
        "2. Find the element 'Drag me to my target'. "
        "3. Drag it and drop it exactly into the box 'Drop here'. "
        "4. VERIFY that the target box text changed to 'Dropped!'. "
        "5. Done."
    )
    print("🐾 Running: Drag and Drop Interaction Test")
    return await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())