import asyncio
from engine import ManulEngine


async def main():
    manul = ManulEngine()

    mission = (
        "1. NAVIGATE to https://testautomationpractice.blogspot.com/\n"

        # ── Text inputs ────────────────────────────────────────────────────
        "2. Fill \"Name\" field with \"Mega Manul\"\n"
        "3. Fill \"Email\" field with \"mega@manul.ai\"\n"
        "4. Fill \"Phone\" field with \"9876543210\"\n"
        "5. Fill \"Address\" textarea with \"Selenium Avenue, 42, AI City\"\n"
        "6. VERIFY that 'Mega Manul' is present.\n"

        # ── Radio button ───────────────────────────────────────────────────
        "7. Click the radio button for \"Male\"\n"
        "8. VERIFY that 'Male' is checked.\n"

        # ── Checkboxes ─────────────────────────────────────────────────────
        "9. Click the checkbox for \"Monday\"\n"
        "10. VERIFY that 'Monday' is checked.\n"
        "11. Click the checkbox for \"Tuesday\"\n"
        "12. VERIFY that 'Tuesday' is checked.\n"
        "13. Click the checkbox for \"Thursday\"\n"
        "14. VERIFY that 'Thursday' is checked.\n"

        # ── Country dropdown ───────────────────────────────────────────────
        "15. Select \"Japan\" from the \"Country\" dropdown\n"
        "16. VERIFY that 'Japan' is present.\n"

        # ── Colors multi-select ────────────────────────────────────────────
        "17. Select \"Blue\" from the \"Colors\" list\n"

        # ── Date picker ────────────────────────────────────────────────────
        "18. Fill \"Date Picker 1\" field with \"12/31/2026\"\n"

        # ── Scroll + alert button ──────────────────────────────────────────
        "19. SCROLL DOWN\n"
        "20. Click the \"START\" button\n"

        # ── Double click ────────────────────────────────────────────────────
        "21. DOUBLE CLICK the button that says \"Copy Text\"\n"
        "22. VERIFY that 'Hello World!' is present.\n"

        # ── Drag and drop ──────────────────────────────────────────────────
        "23. Drag the element \"Drag me to my target\" and drop it into \"Drop here\"\n"
        "24. VERIFY that 'Dropped!' is present.\n"

        # ── Data extraction from web table ─────────────────────────────────
        "25. SCROLL DOWN\n"
        "26. EXTRACT the CPU of \"Chrome\" into {chrome_cpu}\n"
        "27. EXTRACT the CPU of \"Firefox\" into {firefox_cpu}\n"
        "28. EXTRACT the Price of \"Master In Selenium\" into {book_price}\n"
        "29. EXTRACT the Price of \"Selenium\" into {selenium_price}\n"
        "30. VERIFY that '3000' is present.\n"

        # ── Pagination table ────────────────────────────────────────────────
        "31. SCROLL DOWN\n"
        "32. Click on page \"2\" in the pagination list\n"
        "33. Select the checkbox for the product with ID \"7\"\n"
        "34. Click on page \"4\" in the pagination list\n"
        "35. Select the checkbox for the product with ID \"17\"\n"

        # ── Scrolling dropdown ──────────────────────────────────────────────
        "36. SCROLL DOWN\n"
        "37. Click the \"Scrolling DropDown\" input field\n"
        "38. SCROLL DOWN inside the list\n"
        "39. Click \"Item 100\"\n"
        "40. VERIFY that 'Item 100' is present.\n"

        # ── Shadow DOM ──────────────────────────────────────────────────────
        "41. SCROLL DOWN to the very bottom\n"
        "42. Locate the text input inside the Shadow Root\n"
        "43. Type \"Shadow Boss\" into that field\n"
        "44. VERIFY that 'Shadow Boss' is present.\n"

        # ── Final mega verify ───────────────────────────────────────────────
        "45. VERIFY that \"Mega Manul\" and \"Japan\" and \"Dropped!\" "
        "and \"Item 100\" and \"Shadow Boss\" are present.\n"

        "46. DONE."
    )

    print("🐾 Running THE MEGA HUNT: Ultimate Automation Challenge")
    success = await manul.run_mission(
        mission,
        strategic_context=(
            "testautomationpractice.blogspot.com — the main practice page. "
            "Contains: text inputs, radio buttons, checkboxes for days of week, "
            "Country dropdown, Colors multi-select, date picker, START button (alert), "
            "Copy Text double-click button, drag-and-drop, two data tables (browser stats "
            "and book prices), pagination table, scrolling dropdown (100 items), "
            "Shadow DOM text input at the very bottom."
        ),
    )

    if success:
        print("\n🏆 FATALITY! Manul completely dominated the test page! 🏆")
        print(f"📊 Collected Data: {manul.memory}")
    else:
        print("\n🙀 Mission Failed. The prey escaped.")

    return success


if __name__ == "__main__":
    asyncio.run(main())