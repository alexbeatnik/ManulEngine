import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine(strict=True)
    
    mission = (
        '1. Navigate to "https://the-internet.herokuapp.com/login" '
        '2. Type "tomsmith" into the username field. '
        '3. Type "SuperSecretPassword!" into the password field. '
        '4. Click the button that says "Login". '
        '5. VERIFY that the page contains "You logged into a secure area!". '
        '6. Done.'
    )
    
    context = (
        "1. INPUTS: There are two input fields. Look at the 'name' attribute in the JSON (username vs password). "
        "2. CLICK: The login button has an icon and the text 'Login'. "
        "3. VERIFY: A green banner appears if the login is successful."
    )
    
    print("Testing Authorization: The Infiltrator Mission 🕵️‍♂️")
    return await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())