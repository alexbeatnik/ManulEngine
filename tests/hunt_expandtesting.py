import asyncio
from engine import ManulEngine

async def main():
    manul = ManulEngine(headless=False)
    
    mission = (
        "1. NAVIGATE to https://practice.expandtesting.com/login\n"
        "2. Fill 'Username' field with 'practice'\n"
        "3. Fill 'Password' field with 'SuperSecretPassword!'\n"
        "4. Click the 'Login' button\n"
        "5. VERIFY that 'You logged into a secure area!' is present.\n"
        
        "6. NAVIGATE to https://practice.expandtesting.com/inputs\n"
        "7. Fill 'Input Number' field with '4242'\n"
        "8. Fill 'Input Text' field with 'Cyber Manul'\n"
        "9. Fill 'Input Password' field with 'ManulSecret'\n"
        "10. Fill 'Input Date' field with '12/31/2026'\n"
        "11. Click the 'Display Inputs' button\n"
        "12. VERIFY that 'Cyber Manul' is present.\n"
        "13. VERIFY that '4242' is present.\n"
        
        "14. NAVIGATE to https://practice.expandtesting.com/checkboxes\n"
        "15. Check the checkbox for 'Checkbox 1'\n"
        "16. Uncheck the checkbox for 'Checkbox 2'\n"
        "17. VERIFY that 'Checkbox 1' is checked.\n"
        "18. VERIFY that 'Checkbox 2' is not checked.\n"
        
        "19. NAVIGATE to https://practice.expandtesting.com/radio-buttons\n"
        "20. Click the radio button for 'Black'\n"
        "21. VERIFY that 'Black' is checked.\n"
        "22. Click the radio button for 'Basketball'\n"
        "23. VERIFY that 'Basketball' is checked.\n"
        
        "24. NAVIGATE to https://practice.expandtesting.com/dropdown\n"
        "25. Select 'Option 2' from the 'Simple dropdown' list\n"
        "26. VERIFY that 'Option 2' is present.\n"
        "27. Select '100' from the 'Elements per page' dropdown\n"
        
        "28. NAVIGATE to https://practice.expandtesting.com/dynamic-table\n"
        "29. EXTRACT the CPU of 'Chrome' into {chrome_cpu}\n"
        "30. EXTRACT the Memory of 'Firefox' into {firefox_memory}\n"
        "31. EXTRACT the Network of 'Internet Explorer' into {internet_explorer_network}\n"
        
        "32. DONE."
    )
    
    print("🐾 Running EXPAND TESTING GAUNTLET: The Ultimate Playground...")
    success = await manul.run_mission(mission)
    
    if success:
        print("\n🏆 EPIC FATALITY! Manul dominated ExpandTesting!")
        print(f"📊 Collected Data: {manul.memory}")
    else:
        print("\n🙀 Mission Failed. The prey escaped.")
    return success

if __name__ == "__main__":
    asyncio.run(main())