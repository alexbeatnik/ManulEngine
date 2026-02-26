import asyncio
from engine import ManulEngine


async def main():
    manul = ManulEngine()

    mission = (
        # ── 1. Forms ──────────────────────────────────────────────────────────
        "1. NAVIGATE to https://demoqa.com/text-box\n"
        "2. Fill 'Full Name' field with 'Ghost Manul'\n"
        "3. Fill 'Email' field with 'ghost@manul.ai'\n"
        "4. Fill 'Current Address' field with '42 Shadow Lane'\n"
        "5. Fill 'Permanent Address' field with '7 Phantom Street'\n"
        "6. Click the 'Submit' button\n"
        "7. VERIFY that 'Ghost Manul' and 'ghost@manul.ai' are present.\n"

        # ── 2. Checkbox tree ──────────────────────────────────────────────────
        "8. NAVIGATE to https://demoqa.com/checkbox\n"
        # DemoQA tree has a ▶ expand toggle — open it first, then check Home
        "9. Click the expand arrow button\n"
        "10. Click the checkbox for 'Home'\n"
        "11. WAIT 2\n"
        "12. VERIFY that 'You have selected' is present.\n"

        # ── 3. Radio buttons ──────────────────────────────────────────────────
        "13. NAVIGATE to https://demoqa.com/radio-button\n"
        "14. Click the radio button for 'Impressive'\n"
        "15. VERIFY that 'Impressive' is present.\n"

        # ── 4. Web Tables ─────────────────────────────────────────────────────
        "16. NAVIGATE to https://demoqa.com/webtables\n"
        "17. EXTRACT the Salary of 'Alden' into {alden_salary}\n"
        "18. VERIFY that '2000' is present.\n"

        # ── 5. Buttons ────────────────────────────────────────────────────────
        "19. NAVIGATE to https://demoqa.com/buttons\n"
        "20. DOUBLE CLICK the 'Double Click Me' button\n"
        "21. VERIFY that 'You have done a double click' is present.\n"
        "22. Click the 'Click Me' button\n"
        "23. VERIFY that 'You have done a dynamic click' is present.\n"

        # ── 6. Select menu ────────────────────────────────────────────────────
        "24. NAVIGATE to https://demoqa.com/select-menu\n"
        "25. Select 'Purple' from the 'Select Value' dropdown\n"
        "26. VERIFY that 'Purple' is present.\n"

        # ── 7. Date picker ────────────────────────────────────────────────────
        "27. NAVIGATE to https://demoqa.com/date-picker\n"
        "28. Fill 'Date Of Birth' field with '01/15/1990'\n"
        "29. VERIFY that '01/15/1990' is present.\n"

        # ── 8. Slider ─────────────────────────────────────────────────────────
        # (scroll to make it visible, then verify page loaded)
        "30. NAVIGATE to https://demoqa.com/slider\n"
        "31. VERIFY that 'Slider' is present.\n"

        # ── 9. Links (Перенесено сюди) ────────────────────────────────────────
        "32. NAVIGATE to https://demoqa.com/links\n"
        "33. Click on the 'Home' link\n"

        # ── 10. Done ──────────────────────────────────────────────────────────
        "34. DONE."
    )

    print("🐾 Running DEMOQA GAUNTLET: The Full Elements Challenge")
    success = await manul.run_mission(mission)

    if success:
        print("\n🏆 PERFECT HUNT! Manul mastered all DemoQA elements! 🏆")
        print(f"📊 Collected Data: {manul.memory}")
    else:
        print("\n🙀 Mission Failed.")
        print(f"📊 Partial Data: {manul.memory}")

    return success


if __name__ == "__main__":
    asyncio.run(main())