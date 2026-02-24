import asyncio
from framework.engine import ManulEngine

async def main():
    manul = ManulEngine()
    
    mission = (
        "1. Navigate to https://duckduckgo.com/. "
        "2. Type 'Rust programming language' into the search input and press Enter. "
        "3. Wait 2 seconds for results to load. "
        "4. SCROLL DOWN to see the search results. "
        "5. Find a link that contains 'rust-lang.org'. "
        "6. VERIFY that the result content contains 'rust-lang.org'. "
        "7. Done."
    )
    
    context = (
        "1. INPUT: Use the main search box. Enter will trigger the search automatically. "
        "2. RESULTS: DDG results are links with titles. Look for the 'rust-lang.org' substring. "
        "3. VERIFICATION: You must find the actual text 'rust-lang.org' in a link or description."
    )
    
    print("Testing DuckDuckGo search for 'Rust programming language'")
    return await manul.run_mission(mission, strategic_context=context)

if __name__ == "__main__":
    asyncio.run(main())