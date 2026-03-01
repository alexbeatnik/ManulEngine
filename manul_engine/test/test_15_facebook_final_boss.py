import sys
import os
import asyncio
import datetime
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine import ManulEngine
from manul_engine import prompts

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Facebook Comet UI (Real patterns extracted from provided HTML)
# ─────────────────────────────────────────────────────────────────────────────
FB_EXTREME_DOM = """
<!DOCTYPE html>
<html>
<body class="_6s5d _71pn system-fonts--body">
    <div role="main">
        <form id="login_form">
            <div class="xjhjgkd">
                <input id="_R_1h6kqsqppb6amH1_" type="text" name="email">
                <label for="_R_1h6kqsqppb6amH1_">Email or mobile number</label>
            </div>
            <div class="xjhjgkd">
                <input id="_R_1hmkqsqppb6amH1_" type="password" name="pass">
                <label for="_R_1hmkqsqppb6amH1_">Password</label>
            </div>
            <div role="button" aria-label="Log In" tabindex="0" id="login_btn_click">
                <span>Log in</span>
            </div>
        </form>
    </div>

    <hr>

    <div role="main">
        <span>Get started on Facebook</span>
        
        <div class="xjhjgkd">
            <input id="_R_1cl2p4jikacppb6amH1_" type="text">
            <label for="_R_1cl2p4jikacppb6amH1_">First name</label>
        </div>
        <div class="xjhjgkd">
            <input id="_R_1kl2p4jikacppb6amH1_" type="text">
            <label for="_R_1kl2p4jikacppb6amH1_">Last name</label>
        </div>

        <div aria-label="Select Month" id="_r_3_" role="combobox" tabindex="0"><span>Month</span></div>
        <div aria-label="Select Day" id="_r_9_" role="combobox" tabindex="0"><span>Day</span></div>
        <div aria-label="Select Year" id="_r_f_" role="combobox" tabindex="0"><span>Year</span></div>

        <div aria-label="Select your gender" id="_R_mad6p4jikacppb6amH2_" role="combobox" tabindex="0">
            <span>Select your gender</span>
        </div>

        <div class="xjhjgkd">
            <input id="_R_6ad8p4jikacppb6amH1_" type="text">
            <label for="_R_6ad8p4jikacppb6amH1_">Mobile number or email</label>
        </div>
        <div class="xjhjgkd">
            <input id="_R_clap4jikacppb6amH1_" type="password">
            <label for="_R_clap4jikacppb6amH1_">Password</label>
        </div>

        <div role="button" tabindex="0" id="reg_submit_click">
            <span>Submit</span>
        </div>
    </div>
</body>
</html>
"""

async def run_suite() -> bool:
    print(f"\n{'=' * 70}")
    print("🧬 FACEBOOK FINAL BOSS — Integration Test (Resolver Path)")
    print(f"{'=' * 70}")

    passed = 0
    failures: list[str] = []

    TESTS =  [
        {"n": "1", "step": "Fill 'Email or mobile number'", "m": "input", "st": ["Email or mobile number"], "exp": "_R_1h6"},
        {"n": "2", "step": "Click 'Log in'", "m": "clickable", "st": ["Log in"], "exp": "login_btn_click"},
        {"n": "3", "step": "Fill 'First name'", "m": "input", "st": ["First name"], "exp": "_R_1cl"},
        {"n": "4", "step": "Fill 'Last name'", "m": "input", "st": ["Last name"], "exp": "_R_1kl"},
        {"n": "5", "step": "Select 'Month'", "m": "select", "st": ["Month"], "exp": "_r_3"},
        {"n": "6", "step": "Select 'Day'", "m": "select", "st": ["Day"], "exp": "_r_9"},
        {"n": "7", "step": "Select 'Year'", "m": "select", "st": ["Year"], "exp": "_r_f"},
        {"n": "8", "step": "Select 'Select your gender'", "m": "select", "st": ["Select your gender"], "exp": "_R_mad"},
        {"n": "9", "step": "Fill 'Mobile number or email'", "m": "input", "st": ["Mobile number or email"], "exp": "_R_6ad"},
        {"n": "10", "step": "Fill 'Password'", "m": "input", "st": ["Password"], "exp": "_R_cla"},
        {"n": "11", "step": "Click 'Submit'", "m": "clickable", "st": ["Submit"], "exp": "reg_submit_click"},
    ]

    total = len(TESTS)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(no_viewport=True)
            page = await ctx.new_page()
            await page.set_content(FB_EXTREME_DOM)

            manul = ManulEngine(headless=True)
            prompts.AI_ALWAYS = True 

            # Mock LLM for CI environment where Ollama is not present
            async def _mock_llm_select_element(step, mode, candidates, strategic_context):
                print(f"    🧠 AI AGENT MOCK: Always-AI enabled, analysing {len(candidates)} candidates…")
                # For step 10 (Password), return the index of the second password field (Registration)
                if "Password" in step:
                    for i, c in enumerate(candidates):
                        if c.get("html_id") and c["html_id"].startswith("_R_cla"):
                            print(f"    🎯 AI DECISION MOCK: Selected '{c['name']}' — Registration password")
                            return i
                # Otherwise, return the index of the highest scored element (or the first one)
                if candidates:
                    return 0
                return None
                
            manul._llm_select_element = _mock_llm_select_element

            for t in TESTS:
                print(f"\n🐾 Step {t['n']}: {t['step']}")
                
                resolved = await manul._resolve_element(
                    page=page,
                    step=t['step'],
                    mode=t['m'],
                    search_texts=t['st'],
                    target_field=t['st'][0].lower(),
                    strategic_context="Facebook Integration Test",
                    failed_ids=set()
                )

                found_id = resolved.get("html_id") if resolved else "NOT_FOUND"

                if found_id and found_id.startswith(t['exp']):
                    print(f"   ✅ PASSED  → Found '{found_id}'")
                    passed += 1
                else:
                    msg = f"FAILED — got '{found_id}', expected prefix '{t['exp']}'"
                    print(f"   ❌ {msg}")
                    failures.append(f"Case {t['n']}: {msg}")

            await browser.close()

    except Exception as e:
        print(f"   ⚠️  Test Runtime Error: {e}")
        return False

    print(f"\n{'=' * 70}")
    print(f"📊 SCORE: {passed}/{total} passed")
    if failures:
        print("\n🙀 Failures:")
        for f in failures:
            print(f"   • {f}")
    if passed == total:
        print("\n🏆 FLAWLESS VICTORY! Manul conquered Facebook Comet UI! 🏆")
    print(f"{'=' * 70}")

    return passed == total


if __name__ == "__main__":
    asyncio.run(run_suite())