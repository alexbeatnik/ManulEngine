import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: FRONTEND HELL & ANTI-PATTERN GAUNTLET (30 Traps)
# ─────────────────────────────────────────────────────────────────────────────
HELL_DOM = """
<!DOCTYPE html><html><head><title>Frontend Hell</title>
<style>
    .hidden-offscreen { position: absolute; left: -9999px; }
    .uppercase { text-transform: uppercase; }
    .zero-size { width: 0; height: 0; overflow: hidden; display: inline-block; }
</style>
</head><body>

<div role="button" id="t1"><span>Con</span><b>firm</b> <i>Action</i></div>

<button id="fake2" style="display:none;">Settings</button>
<button id="t2" style="display:block;">Settings</button>

<button id="t3" aria-label="Notifications"><svg><path d="M10..."></path></svg></button>

<div class="form-group">
    <div class="label-text">Delivery Address</div>
    <input type="text" id="t4">
</div>

<button id="t5" class="uppercase">proceed</button>

<input id="t6" placeholder="Promo Code">

<input id="t7" aria-label="Credit Card Number">

<input type="submit" id="t8" value="Pay Now">

<div id="t9" role="button" tabindex="0">
    <div><span><em>Finalize Order</em></span></div>
</div>

<label for="t10">Agree to Terms</label>
<input type="checkbox" id="t10">

<div id="t11" title="Download Invoice">⬇️ PDF</div>

<input id="t12" placeholder="  First   Name  &#10;">

<button id="fake13">Update Profile Info</button>
<button id="t13">Update Profile</button>

<button id="fake14" style="opacity: 0;">Logout</button>
<button id="t14" style="opacity: 1;">Logout</button>

<button id="fake15" style="visibility: hidden;">Delete Account</button>
<button id="t15" style="visibility: visible;">Delete Account</button>

<button id="t16"><svg>🔍</svg> Search Items</button>

<button id="t17">Upload<br>Avatar</button>

<p>Please enter your <b>Date of Birth</b> below:</p>
<input id="t18" type="date">

<div id="t19" role="textbox" contenteditable="true" aria-label="Biography"></div>

<button id="fake20" class="hidden-offscreen">Subscribe</button>
<button id="t20">Subscribe</button>

<button id="fake21" aria-hidden="true">Connect Wallet</button>
<button id="t21" aria-hidden="false">Connect Wallet</button>

<input id="t22" name="security_pin" type="password">

<a href="/checkout" id="t23" class="btn-primary">Go to Checkout</a>

<button id="fake24" class="zero-size">Refresh Page</button>
<button id="t24">Refresh Page</button>

<img src="scan.png" alt="Scan QR Code" id="t25" onclick="scan()">

<span id="lbl26">Secret Token</span>
<input id="t26" aria-labelledby="lbl26">

<div role="menuitem" id="t27">Dark Theme</div>

<button id="t28">  Send   &nbsp;&nbsp; Message  </button>

<input id="fake29" placeholder="Phone Number (Optional)">
<input id="t29" placeholder="Phone Number">

<custom-btn id="t30">Launch Rocket</custom-btn>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    {"n": "1", "step": "Click 'Confirm Action'", "m": "clickable", "st": ["Confirm Action"], "tf": None, "exp": "t1"},
    {"n": "2", "step": "Click 'Settings'", "m": "clickable", "st": ["Settings"], "tf": None, "exp": "t2"},
    {"n": "3", "step": "Click 'Notifications'", "m": "clickable", "st": ["Notifications"], "tf": None, "exp": "t3"},
    {
        "n": "4",
        "step": "Fill 'Delivery Address' with 'Kyiv'",
        "m": "input",
        "st": ["Delivery Address"],
        "tf": "delivery address",
        "exp": "t4",
    },
    {"n": "5", "step": "Click 'Proceed'", "m": "clickable", "st": ["Proceed"], "tf": None, "exp": "t5"},
    {
        "n": "6",
        "step": "Fill 'Promo Code' with 'MANUL'",
        "m": "input",
        "st": ["Promo Code"],
        "tf": "promo code",
        "exp": "t6",
    },
    {
        "n": "7",
        "step": "Fill 'Credit Card Number' with '1234'",
        "m": "input",
        "st": ["Credit Card Number"],
        "tf": "credit card number",
        "exp": "t7",
    },
    {"n": "8", "step": "Click 'Pay Now'", "m": "clickable", "st": ["Pay Now"], "tf": None, "exp": "t8"},
    {"n": "9", "step": "Click 'Finalize Order'", "m": "clickable", "st": ["Finalize Order"], "tf": None, "exp": "t9"},
    {"n": "10", "step": "Check 'Agree to Terms'", "m": "clickable", "st": ["Agree to Terms"], "tf": None, "exp": "t10"},
    {
        "n": "11",
        "step": "Click 'Download Invoice'",
        "m": "clickable",
        "st": ["Download Invoice"],
        "tf": None,
        "exp": "t11",
    },
    {
        "n": "12",
        "step": "Fill 'First Name' with 'Alex'",
        "m": "input",
        "st": ["First Name"],
        "tf": "first name",
        "exp": "t12",
    },
    {"n": "13", "step": "Click 'Update Profile'", "m": "clickable", "st": ["Update Profile"], "tf": None, "exp": "t13"},
    {"n": "14", "step": "Click 'Logout'", "m": "clickable", "st": ["Logout"], "tf": None, "exp": "t14"},
    {"n": "15", "step": "Click 'Delete Account'", "m": "clickable", "st": ["Delete Account"], "tf": None, "exp": "t15"},
    {"n": "16", "step": "Click 'Search Items'", "m": "clickable", "st": ["Search Items"], "tf": None, "exp": "t16"},
    {"n": "17", "step": "Click 'Upload Avatar'", "m": "clickable", "st": ["Upload Avatar"], "tf": None, "exp": "t17"},
    {
        "n": "18",
        "step": "Fill 'Date of Birth' with '2000-01-01'",
        "m": "input",
        "st": ["Date of Birth"],
        "tf": "date of birth",
        "exp": "t18",
    },
    {
        "n": "19",
        "step": "Fill 'Biography' with 'QA'",
        "m": "input",
        "st": ["Biography"],
        "tf": "biography",
        "exp": "t19",
    },
    {"n": "20", "step": "Click 'Subscribe'", "m": "clickable", "st": ["Subscribe"], "tf": None, "exp": "t20"},
    {"n": "21", "step": "Click 'Connect Wallet'", "m": "clickable", "st": ["Connect Wallet"], "tf": None, "exp": "t21"},
    {
        "n": "22",
        "step": "Fill 'security_pin' with '0000'",
        "m": "input",
        "st": ["security_pin"],
        "tf": "security pin",
        "exp": "t22",
    },
    {"n": "23", "step": "Click 'Go to Checkout'", "m": "clickable", "st": ["Go to Checkout"], "tf": None, "exp": "t23"},
    {"n": "24", "step": "Click 'Refresh Page'", "m": "clickable", "st": ["Refresh Page"], "tf": None, "exp": "t24"},
    {"n": "25", "step": "Click 'Scan QR Code'", "m": "clickable", "st": ["Scan QR Code"], "tf": None, "exp": "t25"},
    {
        "n": "26",
        "step": "Fill 'Secret Token' with 'XYZ'",
        "m": "input",
        "st": ["Secret Token"],
        "tf": "secret token",
        "exp": "t26",
    },
    {"n": "27", "step": "Click 'Dark Theme'", "m": "clickable", "st": ["Dark Theme"], "tf": None, "exp": "t27"},
    {"n": "28", "step": "Click 'Send Message'", "m": "clickable", "st": ["Send Message"], "tf": None, "exp": "t28"},
    {
        "n": "29",
        "step": "Fill 'Phone Number' with '555'",
        "m": "input",
        "st": ["Phone Number"],
        "tf": "phone number",
        "exp": "t29",
    },
    {"n": "30", "step": "Click 'Launch Rocket'", "m": "clickable", "st": ["Launch Rocket"], "tf": None, "exp": "t30"},
]


async def run_suite():
    print(f"\n{'=' * 70}")
    print("🔥  FRONTEND HELL: 30 ANTI-PATTERN TRAPS FOR HEURISTICS")
    print(f"{'=' * 70}")

    # Headless=True, debug_mode=False — testing algorithm speed and accuracy
    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(HELL_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🪤 Trap {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

            # Call the heart of your heuristics
            el = await manul._resolve_element(page, t["step"], t["m"], t["st"], t["tf"], "", set())
            found = el.get("html_id") if el else None

            if found == t["exp"]:
                print(f"   ✅ PASSED  → Found the correct element: '{found}'")
                passed += 1
            else:
                msg = f"FAILED — got '{found}', expected '{t['exp']}'"
                print(f"   ❌ {msg}")
                failed += 1
                failures.append(f"Trap {t['n']} ({t['step']}): {msg}")

        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {passed}/{len(TESTS)} passed")

        if failures:
            print("\n🙀 Heuristics stumbled on these traps:")
            for f in failures:
                print(f"   • {f}")
            print("\n💡 Tip: check your JS code to ensure you account for getComputedStyle().display, ")
            print("   aria-label, placeholder, and the 'for' attribute in labels.")

        if passed == len(TESTS):
            print("\n👑 30/30 PERFECT! YOUR HEURISTICS ARE OFFICIALLY UNBREAKABLE! 👑")

        print(f"{'=' * 70}")
        await browser.close()

    return passed == len(TESTS)


if __name__ == "__main__":
    asyncio.run(run_suite())
