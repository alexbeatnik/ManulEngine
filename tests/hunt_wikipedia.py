import asyncio
from engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. NAVIGATE to https://en.wikipedia.org/wiki/Main_Page\n"
        "2. VERIFY that 'Welcome to Wikipedia' is present.\n"
        "3. Fill 'Search Wikipedia' field with \"Pallas's cat\" and press Enter\n"
        "4. VERIFY that 'Otocolobus manul' is present.\n"
        "5. EXTRACT the text of 'Order:' into {manul_order}\n"
        "6. EXTRACT the text of 'Family:' into {manul_family}\n"
        "7. Click on the 'Taxonomy' link\n"
        "8. VERIFY that 'Peter Simon Pallas' is present.\n"
        "9. SCROLL DOWN\n"
        "10. Click on the 'Characteristics' link\n"
        "11. VERIFY that 'rounded ears' is present.\n"
        "12. Click on the 'Distribution and habitat' link\n"
        "13. VERIFY that 'Caucasus' is present.\n"
        "14. SCROLL DOWN\n"
        "15. Fill 'Search Wikipedia' field with \"Software testing\" and press Enter\n"
        "16. VERIFY that 'software quality' is present.\n"
        "17. Click on the 'History' link\n"
        "18. VERIFY that 'Glenford J. Myers' is present.\n"
        "20. VERIFY that 'Black-box' is present.\n"
        "21. SCROLL DOWN\n"
        "22. Fill 'Search Wikipedia' field with \"Selenium (software)\" and press Enter\n"
        "23. VERIFY that 'Jason Huggins' is present.\n"
        "24. EXTRACT the text of 'Stable release' into {selenium_release}\n"
        "25. EXTRACT the text of 'License' into {selenium_license}\n"
        "26. Click on the 'Selenium WebDriver' link\n"
        "27. VERIFY that 'browser automation' is present.\n"
        "28. SCROLL DOWN\n"
        "29. Fill 'Search Wikipedia' field with \"Playwright (software)\" and press Enter\n"
        "30. VERIFY that 'Microsoft' is present.\n"
        "31. EXTRACT the text of 'Initial release' into {playwright_release}\n"
        "32. EXTRACT the text of 'Repository' into {playwright_repo}\n"
        "33. Click on the 'Microsoft' link\n"
        "34. VERIFY that 'Bill Gates' is present.\n"
        "35. EXTRACT the text of 'Traded as' into {msft_stock}\n"
        "36. EXTRACT the text of 'Headquarters' into {msft_hq}\n"
        "37. Click on the 'History' link\n"
        "38. VERIFY that 'Paul Allen' is present.\n"
        "39. SCROLL DOWN\n"
        "40. Click on the 'Corporate affairs' link\n"
        "41. VERIFY that 'Board of directors' is present.\n"
        "42. Fill 'Search Wikipedia' field with \"Python (programming language)\" and press Enter\n"
        "43. VERIFY that 'Guido van Rossum' is present.\n"
        "44. EXTRACT the text of 'Typing discipline' into {python_typing}\n"
        "45. EXTRACT the text of 'OS' into {python_os}\n"
        "46. Click on the 'Syntax and semantics' link\n"
        "47. VERIFY that 'Indentation' is present.\n"
        "48. Click on the 'Main menu' button\n"
        "49. Click on the 'Main page' link\n"
        "50. VERIFY that 'Welcome to Wikipedia' is present.\n"
        "51. DONE."
    )
    
    print("🐾 Running WIKIPEDIA HUNT: The 50-Step Marathon...")
    success = await manul.run_mission(mission)
    
    if success:
        print("\n🏆 EPIC FATALITY! Manul survived the 50-step Wikipedia Marathon! 🏆")
        print("\n📊 🧠 Collected Knowledge:")
        for k, v in manul.memory.items():
            print(f"  • {k.upper()}: {v}")
    else:
        print("\n💀 Mission Failed. Wikipedia was too vast.")
        
    return success

if __name__ == "__main__":
    asyncio.run(main())