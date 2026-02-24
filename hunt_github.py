import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. Navigate to https://github.com/microsoft/playwright "
        "2. Find the link named 'README.md' in the file list and click it. "
        "3. Wait 2 seconds for the file content to load. "
        "4. Scroll down until you see the 'Installation' header. "
        "5. Verify that the text 'Installation' is present on the screen. "
        "6. Done."
    )
    
    print("Testing GitHub repository file navigation and content verification")
    await manul.run_mission(mission)

if __name__ == "__main__":
    asyncio.run(main())