import asyncio
from engine import ManulEngine

async def main():
    manul = ManulEngine()

    mission = (
        "1. NAVIGATE to https://rahulshettyacademy.com/AutomationPractice/\n"

        # ── Radio buttons ─────────────────────────────────────────────────
        "2. Click the radio button for 'Radio1'\n"
        "3. VERIFY that 'Radio1' is checked.\n"
        "4. Click the radio button for 'Radio3'\n"
        "5. VERIFY that 'Radio3' is checked.\n"

        # ── Autocomplete / suggestion field ───────────────────────────────
        "6. Fill 'Suggession Class' field with 'Ukra'\n" 
        "7. Click 'Ukraine' in the suggestion list\n"   
        "8. VERIFY that 'Ukraine' is present.\n"    

        # ── Dropdown ──────────────────────────────────────────────────────
        "9. Select 'Option1' from the 'Dropdown' list\n"
        "10. Select 'Option2' from the 'Dropdown' list\n"
        "11. Select 'Option3' from the 'Dropdown' list\n"

        # ── Checkboxes ────────────────────────────────────────────────────
        "12. Click the checkbox for 'Option1'\n"
        "13. VERIFY that 'Option1' is checked.\n"
        "14. Click the checkbox for 'Option2'\n"
        "15. VERIFY that 'Option2' is checked.\n"
        "16. Click the checkbox for 'Option3'\n"
        "17. VERIFY that 'Option3' is checked.\n"
        "18. Click the checkbox for 'Option1'\n"
        "19. VERIFY that 'Option1' is not checked.\n"

        # ── Name field + alert confirm ─────────────────────────────────────
        "20. Fill 'Enter Your Name' field with 'Cyber Manul'\n"
        "21. VERIFY that 'Cyber Manul' is present.\n"
        "22. Click the 'Confirm' button\n"
        "23. VERIFY that 'Cyber Manul' is NOT present.\n"

        # ── SCROLL + data extraction from table ───────────────────────────
        "24. SCROLL DOWN\n"
        "25. EXTRACT the Price of 'Selenium' into {selenium_price}\n"
        "26. EXTRACT the Price of 'Appium' into {appium_price}\n"
        "27. EXTRACT the Price of 'Learn SQL' into {sql_price}\n"
        "28. VERIFY that '25' is present.\n"

        # ── Hide / Show ───────────────────────────────────────────────────
        "29. Fill 'Hide/Show Example' field with 'Ghost Mode'\n"
        "30. VERIFY that 'Ghost Mode' is present.\n"
        "31. Click the 'Hide' button\n"
        "32. VERIFY that 'Ghost Mode' is NOT present.\n"
        "33. Click the 'Show' button\n"
        "34. VERIFY that 'Ghost Mode' is present.\n"

        # ── Dynamic table ──────────────────────────────────────────────────
        "35. SCROLL DOWN\n"
        "36. EXTRACT the Amount of 'Jack' into {jack_amount}\n"
        "37. EXTRACT the Amount of 'Joe' into {john_amount}\n"
        "38. VERIFY that '32' is present.\n"

        # ── Mouse hover ────────────────────────────────────────────────────
        "39. HOVER over the 'Mouse Hover' button\n"
        "40. VERIFY that 'Reload' is present.\n"
        "41. VERIFY that 'Top' is present.\n"

        # ── Back to top ────────────────────────────────────────────────────
        "42. Click the 'Top' link in the menu\n"
        "43. VERIFY that 'Practice Page' is present.\n"

        "44. DONE."
    )

    print("🐾 Running RAHUL SHETTY HUNT: The Real Inspector Challenge")
    success = await manul.run_mission(
        mission,
        strategic_context=(
            "Rahul Shetty Academy practice page. "
            "Contains: radio buttons, autocomplete input ('Suggession Class' is the label "
            "for the country autocomplete field), dropdowns, checkboxes, hide/show toggle, "
            "dynamic table with prices, mouse hover menu."
        ),
    )

    if success:
        print("\n🏆 FATALITY! Manul flawlessly inspected all UI states! 🏆")
        print(f"📊 Collected Data: {manul.memory}")
    else:
        print("\n🙀 Mission Failed. The prey escaped.")

    return success

if __name__ == "__main__":
    asyncio.run(main())