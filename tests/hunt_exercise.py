import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    # 📜 МІСІЯ: Automation Exercise - The Shopping Marathon
    mission = (
        "1. NAVIGATE to https://automationexercise.com/\n"
        "2. VERIFY that 'Automation' and 'Exercise' are present.\n"
        "3. Click on the 'Signup / Login' link in the header\n"
        "4. Fill 'Name' field in signup section with 'Predator Manul'\n"
        "5. Fill 'Email Address' field in signup section with 'predator@manul.ai'\n"
        "6. Click the 'Signup' button\n"
        "7. Click on the 'Products' link in the header\n"
        "8. SCROLL DOWN\n"
        "9. Click 'View Product' for 'Blue Top'\n"
        "10. VERIFY that 'Availability:' and 'Condition:' are present.\n"
        "11. Click the 'Add to cart' button\n"
        "12. Click on the 'View Cart' link in the modal popup\n"
        "13. VERIFY that 'Blue Top' is present in the cart.\n"
        "14. SCROLL DOWN to the footer\n"
        "15. Fill 'Your email address' subscription field with 'hunter@manul.ai'\n"
        "16. Click the arrow button next to the subscription field\n"
        "17. VERIFY that 'successfully subscribed' is present.\n"
        "18. DONE."
    )
    
    print("🐾 Running AUTOMATION EXERCISE HUNT: The Full Cycle Challenge")
    success = await manul.run_mission(mission)
    
    if success:
        print("\n🏆 FATALITY! Manul successfully completed the shopping cycle! 🏆")
    else:
        print("\n💀 Mission Failed. The predator lost the trail.")
        
    return success

if __name__ == "__main__":
    asyncio.run(main())