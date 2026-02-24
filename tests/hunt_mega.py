import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. NAVIGATE to https://testautomationpractice.blogspot.com/\n"
        "2. Fill \"Name\" field with \"Mega Manul\"\n"
        "3. Fill \"Email\" field with \"mega@manul.ai\"\n"
        "4. Fill \"Phone\" field with \"9876543210\"\n"
        "5. Fill \"Address\" textarea with \"Selenium Avenue, 42, AI City\"\n"
        "6. Click the radio button for \"Male\"\n"
        "7. Click the checkbox for \"Tuesday\"\n"
        "8. Click the checkbox for \"Thursday\"\n"
        "9. Select \"Japan\" from the \"Country\" dropdown\n"
        "10. Select \"Blue\" from the \"Colors\" list\n"
        "11. Fill \"Date Picker 1\" field with \"12/31/2026\"\n"
        "12. SCROLL DOWN\n"
        "13. Click the \"START\" button\n"
        "14. DOUBLE CLICK the button that says \"Copy Text\"\n"
        "15. Drag the element \"Drag me to my target\" and drop it into \"Drop here\"\n"
        "16. SCROLL DOWN\n"
        "17. EXTRACT the CPU of \"Chrome\" into {chrome_cpu}\n"
        "18. EXTRACT the Price of \"Master In Selenium\" into {book_price}\n"
        "19. SCROLL DOWN\n"
        "20. Click on page \"4\" in the pagination list\n"
        "21. Select the checkbox for the product with ID \"17\"\n"
        "22. SCROLL DOWN\n"
        "23. Click the \"Scrolling DropDown\" input field\n"
        "24. SCROLL DOWN inside the list\n"
        "25. Select \"Item 100\"\n"
        "26. SCROLL DOWN to the very bottom\n"
        "27. Locate the text input inside the Shadow Root\n"
        "28. Type \"Shadow Boss\" into that field\n"
        "29. VERIFY that \"Mega Manul\" and \"Japan\" and \"Dropped!\" and \"Item 100\" and \"Shadow Boss\" are present.\n"
        "30. DONE."
    )
    
    print("🐾 Running THE MEGA HUNT: Ultimate Automation Challenge")
    success = await manul.run_mission(mission)
    
    if success:
        print("\n🏆 FATALITY! Manul completely dominated the test page! 🏆")
        print(f"📊 Collected Data: {manul.memory}")
    else:
        print("\n💀 Mission Failed. The prey escaped.")
     
    return success

if __name__ == "__main__":
    asyncio.run(main())