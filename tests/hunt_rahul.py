import asyncio
from framework.engine import ManulEngine


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
        "6. Fill 'Suggession Class' field with 'Ukraine'\n"
        "7. VERIFY that 'Ukraine' is present.\n"

        # ── Dropdown ──────────────────────────────────────────────────────
        "8. Select 'Option1' from the 'Dropdown' list\n"
        "9. Select 'Option2' from the 'Dropdown' list\n"
        "10. Select 'Option3' from the 'Dropdown' list\n"

        # ── Checkboxes ────────────────────────────────────────────────────
        "11. Click the checkbox for 'Option1'\n"
        "12. VERIFY that 'Option1' is checked.\n"
        "13. Click the checkbox for 'Option2'\n"
        "14. VERIFY that 'Option2' is checked.\n"
        "15. Click the checkbox for 'Option3'\n"
        "16. VERIFY that 'Option3' is checked.\n"
        "17. Click the checkbox for 'Option1'\n"
        "18. VERIFY that 'Option1' is not checked.\n"

        # ── Name field + alert confirm ─────────────────────────────────────
        "19. Fill 'Enter Your Name' field with 'Cyber Manul'\n"
        "20. VERIFY that 'Cyber Manul' is present.\n"
        "21. Click the 'Confirm' button\n"
        "22. VERIFY that 'Cyber Manul' is NOT present.\n"

        # ── SCROLL + data extraction from table ───────────────────────────
        "23. SCROLL DOWN\n"
        "24. EXTRACT the Price of 'Selenium' into {selenium_price}\n"
        "25. EXTRACT the Price of 'Appium' into {appium_price}\n"
        "26. EXTRACT the Price of 'Learn SQL' into {sql_price}\n"
        "27. VERIFY that '25' is present.\n"

        # ── Hide / Show ───────────────────────────────────────────────────
        "28. Fill 'Hide/Show Example' field with 'Ghost Mode'\n"
        "29. VERIFY that 'Ghost Mode' is present.\n"
        "30. Click the 'Hide' button\n"
        "31. VERIFY that 'Ghost Mode' is NOT present.\n"
        "32. Click the 'Show' button\n"
        "33. VERIFY that 'Ghost Mode' is present.\n"

        # ── Dynamic table ──────────────────────────────────────────────────
        "34. SCROLL DOWN\n"
        "35. EXTRACT the Amount of 'Jack' into {jack_amount}\n"
        "36. EXTRACT the Amount of 'Joe' into {john_amount}\n"
        "37. VERIFY that '32' is present.\n"

        # ── Mouse hover ────────────────────────────────────────────────────
        "38. HOVER over the 'Mouse Hover' button\n"
        "39. VERIFY that 'Reload' is present.\n"
        "40. VERIFY that 'Top' is present.\n"

        # ── Back to top ────────────────────────────────────────────────────
        "41. Click the 'Top' link in the menu\n"
        "42. VERIFY that 'Practice Page' is present.\n"

        "43. DONE."
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
        print("\n💀 Mission Failed. The prey escaped.")

    return success


if __name__ == "__main__":
    asyncio.run(main())