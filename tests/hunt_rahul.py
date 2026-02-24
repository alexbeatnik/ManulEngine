import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. NAVIGATE to https://rahulshettyacademy.com/AutomationPractice/\n"
        "2. Click the radio button for 'Radio3'\n"
        "3. Fill 'Suggession Class' field with 'Ukraine'\n"
        "4. Select 'Option2' from the 'Dropdown' list\n"
        "5. Click the checkbox for 'Option1'\n"
        "6. Click the checkbox for 'Option3'\n"
        "7. Fill 'Enter Your Name' field with 'Cyber Manul'\n"
        "8. VERIFY that 'Cyber Manul' is present.\n"
        "9. Click the 'Confirm' button\n"
        "10. VERIFY that 'Cyber Manul' is NOT present.\n"
        "11. SCROLL DOWN\n"
        "12. EXTRACT the Price of 'Appium' into {appium_price}\n"
        "13. EXTRACT the Price of 'Learn SQL' into {sql_price}\n"
        "14. Fill 'Hide/Show Example' field with 'Ghost Mode'\n"
        "15. Click the 'Hide' button\n"
        "16. VERIFY that 'Ghost Mode' is NOT present.\n"
        "17. Click the 'Show' button\n"
        "18. VERIFY that 'Ghost Mode' is present.\n" 
        "19. SCROLL DOWN\n"
        "20. EXTRACT the Amount of 'Jack' into {jack_amount}\n"
        "21. HOVER over the 'Mouse Hover' button\n"
        "22. VERIFY that 'Reload' is present.\n"
        "23. Click the 'Top' link in the menu\n"
        "24. DONE."
    )
    
    print("🐾 Running RAHUL SHETTY HUNT: The Real Inspector Challenge")
    success = await manul.run_mission(mission)
    
    if success:
        print("\n🏆 FATALITY! Manul flawlessly inspected all UI states! 🏆")
        print(f"📊 Collected Data: {manul.memory}")
    else:
        print("\n💀 Mission Failed. The prey escaped.")
        
    return success

if __name__ == "__main__":
    asyncio.run(main())