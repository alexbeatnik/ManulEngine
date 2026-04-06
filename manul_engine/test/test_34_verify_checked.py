import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: VERIFY ... is checked / is NOT checked — Checkbox & Radio State (20 Tests)
#
# Validates:
# 1. VERIFY ... is checked → True for pre-checked checkboxes
# 2. VERIFY ... is NOT checked → True for unchecked checkboxes
# 3. Radio buttons: checked vs unchecked (native only — is_checked() needs native)
# 4. Checkbox with aria-label only (no visible text)
# 5. data-qa identified checkboxes
# 6. Checkbox inside a form with other elements
# 7. Multiple checkbox/radio groups coexisting
#
# NOTE: Only "succeeds immediately" cases are tested (res=True), matching
#       test_32's pattern.  The engine retries 15× on verification failure,
#       which would hang the suite for res=False cases.
#       ARIA role=checkbox/radio/switch divs are excluded — Playwright's
#       is_checked() only works on native <input type="checkbox|radio">.
# ─────────────────────────────────────────────────────────────────────────────
CHECKED_DOM = """
<!DOCTYPE html><html><head><title>Checked State Lab</title></head><body>

<!-- Group 1: simple checkboxes -->
<label><input id="chk_on"  type="checkbox" checked> Newsletter</label>
<label><input id="chk_off" type="checkbox"> Promotions</label>

<!-- Group 2: radio buttons -->
<label><input id="rad_sel"   type="radio" name="plan" value="pro" checked> Pro Plan</label>
<label><input id="rad_unsel" type="radio" name="plan" value="free"> Free Plan</label>

<!-- Group 3: aria-label only checkboxes (no visible label text wrapper) -->
<input id="chk_aria_on"  type="checkbox" aria-label="Accept Terms" checked>
<input id="chk_aria_off" type="checkbox" aria-label="Subscribe Updates">

<!-- Group 4: data-qa identified checkboxes -->
<input id="chk_dqa_on"  type="checkbox" data-qa="agree-tos" checked>
<label for="chk_dqa_on">Agree to TOS</label>
<input id="chk_dqa_off" type="checkbox" data-qa="opt-marketing">
<label for="chk_dqa_off">Opt-in Marketing</label>

<!-- Group 5: checkbox inside a form with other elements -->
<form>
  <input type="text" placeholder="Username">
  <label><input id="chk_form_on" type="checkbox" checked> Remember Me</label>
  <label><input id="chk_form_off" type="checkbox"> Save Card</label>
  <button type="submit">Login</button>
</form>

<!-- Group 6: second radio group -->
<label><input id="rad2_sel"   type="radio" name="ship" value="express" checked> Express Shipping</label>
<label><input id="rad2_unsel" type="radio" name="ship" value="standard"> Standard Shipping</label>

<!-- Group 7: multiple checkboxes in a fieldset -->
<fieldset><legend>Preferences</legend>
  <label><input id="pref_on1"  type="checkbox" checked> Email Alerts</label>
  <label><input id="pref_off1" type="checkbox"> SMS Alerts</label>
  <label><input id="pref_on2"  type="checkbox" checked> Push Notifications</label>
  <label><input id="pref_off2" type="checkbox"> Weekly Digest</label>
</fieldset>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests — 20 assertions (all res=True for immediate return)
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── Group 1: simple checkboxes ───────────────────────────────────
    {"n": "1. Checked checkbox → is checked = True", "step": "VERIFY that 'Newsletter' is checked", "res": True},
    {
        "n": "2. Unchecked checkbox → is NOT checked = True",
        "step": "VERIFY that 'Promotions' is NOT checked",
        "res": True,
    },
    # ── Group 2: radio buttons ───────────────────────────────────────
    {"n": "3. Selected radio → is checked = True", "step": "VERIFY that 'Pro Plan' is checked", "res": True},
    {"n": "4. Unselected radio → is NOT checked = True", "step": "VERIFY that 'Free Plan' is NOT checked", "res": True},
    # ── Group 3: aria-label only ─────────────────────────────────────
    {
        "n": "5. Aria-label checked checkbox → is checked = True",
        "step": "VERIFY that 'Accept Terms' is checked",
        "res": True,
    },
    {
        "n": "6. Aria-label unchecked checkbox → is NOT checked = True",
        "step": "VERIFY that 'Subscribe Updates' is NOT checked",
        "res": True,
    },
    # ── Group 4: data-qa identified ──────────────────────────────────
    {
        "n": "7. data-qa checked checkbox → is checked = True",
        "step": "VERIFY that 'Agree to TOS' is checked",
        "res": True,
    },
    {
        "n": "8. data-qa unchecked checkbox → is NOT checked = True",
        "step": "VERIFY that 'Opt-in Marketing' is NOT checked",
        "res": True,
    },
    # ── Group 5: checkbox inside form ────────────────────────────────
    {"n": "9. Form checkbox checked → is checked = True", "step": "VERIFY that 'Remember Me' is checked", "res": True},
    {
        "n": "10. Form checkbox unchecked → is NOT checked = True",
        "step": "VERIFY that 'Save Card' is NOT checked",
        "res": True,
    },
    # ── Group 6: second radio group ──────────────────────────────────
    {
        "n": "11. Express radio checked → is checked = True",
        "step": "VERIFY that 'Express Shipping' is checked",
        "res": True,
    },
    {
        "n": "12. Standard radio unchecked → is NOT checked = True",
        "step": "VERIFY that 'Standard Shipping' is NOT checked",
        "res": True,
    },
    # ── Group 7: fieldset preferences ────────────────────────────────
    {"n": "13. Email Alerts checked → is checked = True", "step": "VERIFY that 'Email Alerts' is checked", "res": True},
    {
        "n": "14. SMS Alerts unchecked → is NOT checked = True",
        "step": "VERIFY that 'SMS Alerts' is NOT checked",
        "res": True,
    },
    {
        "n": "15. Push Notifications checked → is checked = True",
        "step": "VERIFY that 'Push Notifications' is checked",
        "res": True,
    },
    {
        "n": "16. Weekly Digest unchecked → is NOT checked = True",
        "step": "VERIFY that 'Weekly Digest' is NOT checked",
        "res": True,
    },
    # ── Cross-validation: positive on checked, negative on same ──────
    {
        "n": "17. Newsletter checked (cross-val) → is checked = True",
        "step": "VERIFY that 'Newsletter' is checked",
        "res": True,
    },
    {
        "n": "18. Pro Plan checked (cross-val) → is checked = True",
        "step": "VERIFY that 'Pro Plan' is checked",
        "res": True,
    },
    {
        "n": "19. Accept Terms checked (cross-val) → is checked = True",
        "step": "VERIFY that 'Accept Terms' is checked",
        "res": True,
    },
    {
        "n": "20. Agree to TOS checked (cross-val) → is checked = True",
        "step": "VERIFY that 'Agree to TOS' is checked",
        "res": True,
    },
]


async def run_suite():
    print(f"\n{'=' * 70}")
    print("☑️   VERIFY CHECKED/NOT CHECKED LAB — Checkbox & Radio State")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(CHECKED_DOM)

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
            print("\n🏆 CHECKBOX & RADIO STATE VERIFICATION FLAWLESS!")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == total


if __name__ == "__main__":
    asyncio.run(run_suite())
