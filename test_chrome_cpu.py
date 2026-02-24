import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. Navigate to https://testautomationpractice.blogspot.com/. "
        "2. Fill 'Name' field with 'Manul Predator'. "
        "3. Fill 'Email' field with 'hunter@manul.ai'. "
        "4. SCROLL DOWN to the 'Dynamic Web Table' section. "
        "5. Identify the cell with CPU percentage (e.g. 1.5%) in the row that starts with 'Chrome' and EXTRACT it into {cpu_val}. "
        "6. Fill 'Address' textarea with: 'System Audit. Chrome CPU is {cpu_val}'. "
        "7. Done."
    )
    
    context = (
        "1. TABLE: The Dynamic Web Table changes values every few seconds. "
        "2. EXTRACTION: When you find 'Chrome', the CPU is usually in the second or third column of that row. "
        "3. VARIABLE: You MUST save the value so it can be used in the Address field."
    )
    
    print("Testing dynamic web table data extraction for Chrome CPU usage")
    await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())