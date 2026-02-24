import asyncio
from framework.engine import ManulEngine

async def main():
    # Важливо: ініціалізуємо двигун тут
    manul = ManulEngine(strict=True)
    
    mission = (
        '1. Navigate to "https://testautomationpractice.blogspot.com/" '
        '2. Fill "Name" field with "Manul Predator". '
        '3. Fill "Email" field with "hunter@manul.ai". '
        '4. SCROLL DOWN to find the table. '
        '5. Identify the cell in the row that starts with "Chrome" and EXTRACT it into {cpu_val}. '
        '6. Fill "Address" textarea with "System Audit. Chrome CPU is {cpu_val}". '
        '7. Done.'
    )
    
    context = (
        "1. TABLE: We are looking for the Dynamic Web Table. "
        "2. EXTRACTION: Find 'Chrome' first, then grab the CPU percentage. "
        "3. VARIABLE: The value {cpu_val} will be replaced automatically in Step 6."
    )
    
    print("Testing dynamic web table data extraction: The Collector Mission 📦")
    return await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())