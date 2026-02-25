import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()

    mission = (
        "1. NAVIGATE to https://www.facebook.com/\n"
        
        # 🚀 Додали магічну фразу "if exists"
        "2. Click the 'Allow all cookies' button if exists\n"
        
        "3. Fill 'Email or phone number' field with 'random_manul_99@gmail.com'\n"
        "4. Fill 'Password' field with 'WrongPassword123!'\n"
        "5. Click the 'Log In' button\n"
        
        # Якщо пошта не зареєстрована, ФБ зазвичай пише такий текст
        "6. VERIFY that 'isn't connected' is present.\n"
        "7. DONE."
    )

    print("🐾 Running FACEBOOK INFILTRATION: The Invalid Login Hunt")
    success = await manul.run_mission(mission)

    if success:
        print("\n🏆 MISSION ACCOMPLISHED: Error detected. Target is secure.")
    else:
        print("\n💀 MISSION FAILED: Error message not found or blocked.")

    return success

if __name__ == "__main__":
    asyncio.run(main())