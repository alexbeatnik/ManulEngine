import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: VERIFY ENABLED / DISABLED — State Verification Gauntlet (20 Tests)
#
# Validates:
# 1. VERIFY ... is ENABLED  → returns True for interactable elements
# 2. VERIFY ... is DISABLED → returns True for disabled elements
# 3. Mixed element types: button, input, select, textarea, anchor, ARIA roles
# 4. aria-disabled="true" recognised as disabled
# 5. CSS class "disabled" recognised as disabled
# 6. <label> with associated disabled control
# 7. Substring matching fallback for long target texts
# ─────────────────────────────────────────────────────────────────────────────
ENABLED_DOM = """
<!DOCTYPE html><html><head><title>Enabled/Disabled Lab</title></head><body>

<!-- Group 1: simple buttons -->
<button id="btn_active">Active Button</button>
<button id="btn_inactive" disabled>Inactive Button</button>

<!-- Group 2: inputs -->
<input id="inp_active" type="text" placeholder="Active Input" aria-label="Active Input">
<input id="inp_inactive" type="text" placeholder="Inactive Input" aria-label="Inactive Input" disabled>

<!-- Group 3: select -->
<select id="sel_active" aria-label="Active Select"><option>A</option></select>
<select id="sel_inactive" aria-label="Inactive Select" disabled><option>B</option></select>

<!-- Group 4: textarea -->
<textarea id="ta_active" aria-label="Active Textarea"></textarea>
<textarea id="ta_inactive" aria-label="Inactive Textarea" disabled></textarea>

<!-- Group 5: anchor with aria-disabled -->
<a href="#" id="link_active" role="button">Active Link</a>
<a href="#" id="link_inactive" role="button" aria-disabled="true">Inactive Link</a>

<!-- Group 6: div role="button" with disabled class -->
<div role="button" id="div_active">Active Action</div>
<div role="button" id="div_inactive" class="disabled">Inactive Action</div>

<!-- Group 7: label with associated disabled control -->
<label id="lbl_active" for="ctrl_active">Active Control</label>
<input id="ctrl_active" type="text">
<label id="lbl_inactive" for="ctrl_inactive">Inactive Control</label>
<input id="ctrl_inactive" type="text" disabled>

<!-- Group 8: button with aria-disabled attribute (no native disabled) -->
<button id="btn_aria_active">Aria Active</button>
<button id="btn_aria_inactive" aria-disabled="true">Aria Inactive</button>

<!-- Group 9: enabled button with disabled attribute explicitly set to empty string -->
<button id="btn_attr_disabled" disabled="">Attr Disabled</button>
<button id="btn_no_attr">No Attr</button>

<!-- Group 10: role="menuitem" and role="tab" -->
<div role="menuitem" id="mi_active">Active Menu Item</div>
<div role="menuitem" id="mi_inactive" aria-disabled="true">Inactive Menu Item</div>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests — 20 assertions
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── Group 1: simple buttons ──────────────────────────────────────
    {"n": "1. Active button is ENABLED", "step": "VERIFY that 'Active Button' is ENABLED", "res": True},
    {"n": "2. Inactive button is DISABLED", "step": "VERIFY that 'Inactive Button' is DISABLED", "res": True},
    # ── Group 2: inputs ──────────────────────────────────────────────
    {"n": "3. Active input is ENABLED", "step": "VERIFY that 'Active Input' is ENABLED", "res": True},
    {"n": "4. Inactive input is DISABLED", "step": "VERIFY that 'Inactive Input' is DISABLED", "res": True},
    # ── Group 3: select ──────────────────────────────────────────────
    {"n": "5. Active select is ENABLED", "step": "VERIFY that 'Active Select' is ENABLED", "res": True},
    {"n": "6. Inactive select is DISABLED", "step": "VERIFY that 'Inactive Select' is DISABLED", "res": True},
    # ── Group 4: textarea ────────────────────────────────────────────
    {"n": "7. Active textarea is ENABLED", "step": "VERIFY that 'Active Textarea' is ENABLED", "res": True},
    {"n": "8. Inactive textarea is DISABLED", "step": "VERIFY that 'Inactive Textarea' is DISABLED", "res": True},
    # ── Group 5: anchor with aria-disabled ───────────────────────────
    {"n": "9. Active link is ENABLED", "step": "VERIFY that 'Active Link' is ENABLED", "res": True},
    {
        "n": "10. Inactive link is DISABLED (aria-disabled)",
        "step": "VERIFY that 'Inactive Link' is DISABLED",
        "res": True,
    },
    # ── Group 6: div role=button with CSS disabled class ─────────────
    {"n": "11. Active div-button is ENABLED", "step": "VERIFY that 'Active Action' is ENABLED", "res": True},
    {
        "n": "12. Inactive div-button is DISABLED (class)",
        "step": "VERIFY that 'Inactive Action' is DISABLED",
        "res": True,
    },
    # ── Group 7: label with associated control ───────────────────────
    {"n": "13. Label with enabled control is ENABLED", "step": "VERIFY that 'Active Control' is ENABLED", "res": True},
    {
        "n": "14. Label with disabled control is DISABLED",
        "step": "VERIFY that 'Inactive Control' is DISABLED",
        "res": True,
    },
    # ── Group 8: aria-disabled attribute (no native disabled) ────────
    {"n": "15. Aria active button is ENABLED", "step": "VERIFY that 'Aria Active' is ENABLED", "res": True},
    {"n": "16. Aria-disabled button is DISABLED", "step": "VERIFY that 'Aria Inactive' is DISABLED", "res": True},
    # ── Group 9: disabled="" attribute ───────────────────────────────
    {
        "n": "17. disabled='' attribute counts as DISABLED",
        "step": "VERIFY that 'Attr Disabled' is DISABLED",
        "res": True,
    },
    {"n": "18. No disabled attr counts as ENABLED", "step": "VERIFY that 'No Attr' is ENABLED", "res": True},
    # ── Group 10: role=menuitem / tab ────────────────────────────────
    {"n": "19. Active menu item is ENABLED", "step": "VERIFY that 'Active Menu Item' is ENABLED", "res": True},
    {
        "n": "20. Inactive menu item is DISABLED (aria-disabled)",
        "step": "VERIFY that 'Inactive Menu Item' is DISABLED",
        "res": True,
    },
]


async def run_suite():
    print(f"\n{'=' * 70}")
    print("✅/🚫 VERIFY ENABLED/DISABLED LAB — State Verification Gauntlet")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(ENABLED_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🔬 {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            result = await manul._handle_verify(page, t["step"])
            if result == t["res"]:
                print(f"   ✅ PASSED  → VERIFY returned {result}")
                passed += 1
            else:
                msg = f"FAILED — VERIFY returned {result}, expected {t['res']}"
                print(f"   ❌ {msg}")
                failed += 1
                failures.append(f"{t['n']}: {msg}")

        total = passed + failed
        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {passed}/{total} passed")
        if failures:
            print("\n🙀 Failures:")
            for f in failures:
                print(f"   • {f}")
        if passed == total:
            print("\n🏆 ENABLED/DISABLED STATE VERIFICATION FLAWLESS!")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == total


if __name__ == "__main__":
    asyncio.run(run_suite())
