import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    # ❗️Використовуємо ПОДВІЙНІ лапки для тексту❗️
    mission = (
        '1. Navigate to https://en.wikipedia.org/ '
        '2. Type "Pallas\'s cat" into search '
        '3. Verify that the main heading (H1) is "Pallas\'s cat" '
        '4. Verify that the page contains "Otocolobus manul" '
        '5. Done.'
    )
    
    context = "Heading verification: 'Pallas's cat' contains 'Pallas'. Scientific name is in the article body."
    
    print("Testing Wikipedia search for 'Pallas cat' and content verification")
    await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())