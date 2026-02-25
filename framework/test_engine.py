import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import re
from playwright.async_api import async_playwright
from framework.engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# MONSTER DOM  —  Each trap section is labelled clearly.
# Original 24 traps + 4 optional traps + 6 integration-battle traps = 34.
# ─────────────────────────────────────────────────────────────────────────────
MONSTER_DOM = """
<!DOCTYPE html>
<html>
<head><title>Monster DOM</title></head>
<body>

<fieldset>
    <legend>Suggession Class</legend>
    <input type="text" id="trap_legend_input" placeholder="Type here">
</fieldset>

<div>
    <label for="trap_phantom_chk">Option 1</label>
    <input type="checkbox" id="trap_phantom_chk">

    <label for="trap_phantom_select">Dropdown</label>
    <select id="trap_phantom_select">
        <option>Select...</option>
        <option>Option 1</option>
    </select>
</div>

<div>
    <button id="trap_hidden_btn" style="display: none;">Submit Login</button>
    <div id="trap_fake_btn" class="button" role="button">Submit Login</div>
    <input type="submit" id="trap_real_btn" value="Submit Login">
</div>

<div id="host"></div>
<script>
    const host   = document.getElementById('host');
    const shadow = host.attachShadow({mode: 'open'});
    const label  = document.createElement('label');
    label.textContent = 'Cyber Password';
    const input  = document.createElement('input');
    input.type   = 'password';
    input.id     = 'trap_shadow_input';
    shadow.appendChild(label);
    shadow.appendChild(input);
</script>

<div>
    <button id="trap_aria_btn" aria-label="Close Window">X</button>
    <div id="trap_wrong_aria" role="button">Close Window</div>
</div>

<div>
    <button id="trap_btn_partial1">Save and Continue</button>
    <button id="trap_btn_exact">Save</button>
    <button id="trap_btn_partial2">Save Draft</button>
</div>

<div>
    <label for="trap_opacity_chk">Accept Terms</label>
    <input type="checkbox" id="trap_opacity_chk" style="opacity: 0.01;">
</div>

<div>
    <input type="text" id="trap_placeholder_input" placeholder="Secret Token">
    <div id="trap_placeholder_div">Secret Token</div>
</div>

<fieldset>
    <legend>Subscribe?</legend>
    <input type="radio" id="trap_radio_yes" name="sub" value="yes">
    <label for="trap_radio_yes">Yes</label>
    <input type="radio" id="trap_radio_no" name="sub" value="no">
    <label for="trap_radio_no">No</label>
</fieldset>

<div>
    <div id="trap_role_chk" role="checkbox" aria-checked="false" aria-label="Remember Me" style="display:inline-block; width:20px; height:20px; border:1px solid #000;"></div>
    <input type="text" id="trap_wrong_input" aria-label="Remember Me">
</div>

<div>
    <button id="trap_text_btn">Confirm Order</button>
    <button id="trap_qa_btn" data-qa="confirm-order">Click Here</button>
</div>

<div>
    <button id="trap_btn_login">Register Portal</button>
    <a href="/login" id="trap_link_login">Register Portal</a>
</div>

<section id="login-form-section">
    <h3>Login Form</h3>
    <label for="trap_section_login">Email</label>
    <input type="email" id="trap_section_login" placeholder="Login email">
</section>
<section id="signup-form-section">
    <h3>Signup Form</h3>
    <label for="trap_section_signup">Email</label>
    <input type="email" id="trap_section_signup" placeholder="Signup email">
</section>

<div>
    <button id="trap_icon_wrong">Filter</button>
    <button id="trap_icon_search"><i class="fa fa-search"></i></button>
    <button id="trap_icon_close"><i class="fa fa-times"></i></button>
</div>

<div>
    <button id="trap_disabled_btn" disabled>Submit</button>
    <button id="trap_enabled_btn">Submit</button>
</div>

<div>
    <button id="trap_qty_btn">Quantity</button>
    <label for="trap_qty_input">Quantity</label>
    <input type="number" id="trap_qty_input" min="1">
</div>

<div>
    <label id="trap_newsletter_label">
        <input type="checkbox" id="trap_newsletter_chk">
        Newsletter
    </label>
    <div id="trap_newsletter_div">Newsletter</div>
</div>

<div>
    <button id="trap_delete_all" data-qa="delete-all">Delete</button>
    <button id="trap_delete_selected" data-qa="delete-selected">Delete</button>
</div>

<div>
    <label for="trap_readonly_input">Promo Code</label>
    <input type="text" id="trap_readonly_input" readonly value="PLACEHOLDER">
    <button id="trap_readonly_btn">Promo Code</button>
</div>

<div>
    <button id="trap_title_wrong">Options</button>
    <button id="trap_title_btn" title="Settings">⚙</button>
</div>

<div>
    <a href="/download" id="trap_download_link">Download</a>
    <button id="trap_download_btn">Download</button>
</div>

<div>
    <input type="text"     id="trap_pw_text"  placeholder="password">
    <input type="password" id="trap_pw_pass"  placeholder="password">
</div>

<div class="floating-field">
    <span id="trap_float_label" class="float-label">Card Number</span>
    <input type="text" id="trap_float_input" data-qa="card-number">
</div>

<table>
    <tr>
        <td><input type="checkbox" id="trap_chk_phone"></td>
        <td>Phone</td>
        <td>$699</td>
    </tr>
    <tr>
        <td><input type="checkbox" id="trap_chk_laptop"></td>
        <td>Laptop</td>
        <td>$1299</td>
    </tr>
</table>

<div id="cookie_banner" style="display: none;">
    <button id="trap_cookie_btn">Accept Cookies</button>
</div>

<div>
    <button id="trap_zero_pixel_btn" style="width: 0; height: 0; padding: 0; border: none; overflow: hidden;">Close Ad if exists</button>
</div>

<div>
    <label for="trap_promo_optional_input">Promotion Code if exists</label>
    <input type="text" id="trap_promo_optional_input">
</div>

<!-- ── TRAPS 29-34: Real bugs from integration test battles ──────────── -->

<div>
    <label for="trap_check_agree_chk">Agree to Terms</label>
    <input type="checkbox" id="trap_check_agree_chk">
    <label for="trap_check_agree_input">Agree to Terms</label>
    <input type="text" id="trap_check_agree_input" placeholder="signature">
</div>

<div>
    <label for="trap_uncheck_renew_chk">Auto-Renew</label>
    <input type="checkbox" id="trap_uncheck_renew_chk" checked>
    <button id="trap_uncheck_renew_btn">Auto-Renew Settings</button>
</div>

<div>
    <label for="trap_priority_chk">Priority</label>
    <input type="checkbox" id="trap_priority_chk">
    <input type="radio" id="trap_priority_radio" name="prio" value="urgent">
    <label for="trap_priority_radio">Urgent</label>
    <label for="trap_priority_select">Priority</label>
    <select id="trap_priority_select">
        <option>--</option>
        <option>Low</option>
        <option>Medium</option>
        <option>Urgent</option>
    </select>
</div>

<div>
    <button id="trap_partial_decoy_btn">Ad Settings</button>
</div>

<div>
    <input type="text" id="trap_addr_decoy" placeholder="Enter your address">
    <input type="text" id="trap_dqa_ship" data-qa="shipping-address">
</div>

<div>
    <label for="trap_jsclick_chk">Enable Notifications</label>
    <input type="checkbox" id="trap_jsclick_chk">
</div>

</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Test catalogue
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── ORIGINAL 24 ────────────────────────────────────────────────────────
    {
        "name": "1. Legend Form Extraction",
        "desc": "fieldset/legend used as input label — must find the actual <input>, not the <legend>",
        "step": "Fill 'Suggession Class' field with 'Ukraine'",
        "mode": "input", "search_texts": ["Suggession Class"], "target_field": "suggession class",
        "expected": "trap_legend_input",
    },
    {
        "name": "2. Phantom Guard — Select vs Checkbox",
        "desc": "select mode must reject checkbox even though 'Option 1' text matches checkbox label",
        "step": "Select 'Option 1' from the 'Dropdown' list",
        "mode": "select", "search_texts": ["Option 1", "Dropdown"], "target_field": None,
        "expected": "trap_phantom_select",
    },
    {
        "name": "3. Native Button Priority",
        "desc": "hidden button and role=button div must lose to real <input type=submit>",
        "step": "Click the 'Submit Login' button",
        "mode": "clickable", "search_texts": ["Submit Login"], "target_field": None,
        "expected": "trap_real_btn",
    },
    {
        "name": "4. Shadow DOM Penetration",
        "desc": "target input lives inside a shadow root — must pierce it",
        "step": "Fill 'Cyber Password' field with 'secret'",
        "mode": "input", "search_texts": ["Cyber Password"], "target_field": "cyber password",
        "expected": "trap_shadow_input",
    },
    {
        "name": "5. ARIA Label Recognition",
        "desc": "real <button> with aria-label must beat role=button div with matching visible text",
        "step": "Click the 'Close Window' button",
        "mode": "clickable", "search_texts": ["Close Window"], "target_field": None,
        "expected": "trap_aria_btn",
    },
    {
        "name": "6. Exact Match Tiebreaker",
        "desc": "three buttons share the word 'Save'; the one with exactly 'Save' wins",
        "step": "Click the 'Save' button",
        "mode": "clickable", "search_texts": ["Save"], "target_field": None,
        "expected": "trap_btn_exact",
    },
    {
        "name": "7. Ghost Opacity Detection",
        "desc": "checkbox at opacity:0.01 is technically visible — must still be targeted",
        "step": "Click the checkbox for 'Accept Terms'",
        "mode": "clickable", "search_texts": ["Accept Terms"], "target_field": None,
        "expected": "trap_opacity_chk",
    },
    {
        "name": "8. Placeholder Extraction",
        "desc": "prefer <input placeholder='Secret Token'> over a <div> with the same text",
        "step": "Fill 'Secret Token' field with '123'",
        "mode": "input", "search_texts": ["Secret Token"], "target_field": "secret token",
        "expected": "trap_placeholder_input",
    },
    {
        "name": "9. Radio Button Grouping",
        "desc": "two radios share a fieldset; 'No' label must resolve to the correct one",
        "step": "Click the radio button for 'No'",
        "mode": "clickable", "search_texts": ["No"], "target_field": None,
        "expected": "trap_radio_no",
    },
    {
        "name": "10. Custom Role Checkbox",
        "desc": "role=checkbox div must beat type=text input that happens to share the aria-label",
        "step": "Click the checkbox for 'Remember Me'",
        "mode": "clickable", "search_texts": ["Remember Me"], "target_field": None,
        "expected": "trap_role_chk",
    },
    {
        "name": "11. Data-QA Attribute Supremacy",
        "desc": "data-qa='confirm-order' must beat the button that literally says 'Confirm Order'",
        "step": "Click the 'Confirm Order' button",
        "mode": "clickable", "search_texts": ["Confirm Order"], "target_field": None,
        "expected": "trap_qa_btn",
    },
    {
        "name": "12. Link vs Button — step says 'link'",
        "desc": "when step says 'link', must pick <a> and not the <button> with same text",
        "step": "Click the 'Register Portal' link",
        "mode": "clickable", "search_texts": ["Register Portal"], "target_field": None,
        "expected": "trap_link_login",
    },
    {
        "name": "13. Section Context Disambiguation",
        "desc": "'Email' field appears in two sections; step mentions 'Login Form' — must pick login one",
        "step": "Fill 'Email' field in the Login Form section with 'ghost@manul.ai'",
        "mode": "input", "search_texts": ["Email", "Login Form"], "target_field": "email",
        "expected": "trap_section_login",
    },
    {
        "name": "14. Icon-Only Button",
        "desc": "button has no text — correct one identified only by fa-search icon class",
        "step": "Click the search button",
        "mode": "clickable", "search_texts": [], "target_field": None,
        "expected": "trap_icon_search",
    },
    {
        "name": "15. Disabled Element Avoidance",
        "desc": "two buttons both say 'Submit'; disabled one must be skipped",
        "step": "Click the 'Submit' button",
        "mode": "clickable", "search_texts": ["Submit"], "target_field": None,
        "expected": "trap_enabled_btn",
    },
    {
        "name": "16. Number Input Priority",
        "desc": "button and number input share label 'Quantity'; input wins for fill mode",
        "step": "Fill 'Quantity' field with '5'",
        "mode": "input", "search_texts": ["Quantity"], "target_field": "quantity",
        "expected": "trap_qty_input",
    },
    {
        "name": "17. Wrapping Label Checkbox",
        "desc": "checkbox is wrapped inside its own <label> — label click must resolve to the input",
        "step": "Click the checkbox for 'Newsletter'",
        "mode": "clickable", "search_texts": ["Newsletter"], "target_field": None,
        "expected": "trap_newsletter_chk",
    },
    {
        "name": "18. Homonym Buttons — data-qa Wins",
        "desc": "two 'Delete' buttons; data-qa='delete-selected' matches step context",
        "step": "Click the 'Delete' button for the selected item",
        "mode": "clickable", "search_texts": ["Delete"], "target_field": None,
        "expected": "trap_delete_selected",
    },
    {
        "name": "19. Readonly Input Targeting",
        "desc": "readonly input has same label as a nearby button; input wins for fill mode",
        "step": "Fill 'Promo Code' field with 'MANUL2025'",
        "mode": "input", "search_texts": ["Promo Code"], "target_field": "promo code",
        "expected": "trap_readonly_input",
    },
    {
        "name": "20. Title Attribute as Label",
        "desc": "button has only title='Settings' and a glyph '⚙'; must beat nearby 'Options' button",
        "step": "Click the 'Settings' button",
        "mode": "clickable", "search_texts": ["Settings"], "target_field": None,
        "expected": "trap_title_btn",
    },
    {
        "name": "21. Button vs Link — step says 'button'",
        "desc": "both <a> and <button> say 'Download'; step says 'button' → must pick button",
        "step": "Click the 'Download' button",
        "mode": "clickable", "search_texts": ["Download"], "target_field": None,
        "expected": "trap_download_btn",
    },
    {
        "name": "22. Password Field Type Priority",
        "desc": "two inputs share placeholder 'password'; type=password must win for password fill",
        "step": "Fill the 'password' field with 'hunter2'",
        "mode": "input", "search_texts": ["password"], "target_field": "password",
        "expected": "trap_pw_pass",
    },
    {
        "name": "23. Floating Label Input",
        "desc": "a <span> acts as floating label — real input is nearby but has only data-qa",
        "step": "Fill 'Card Number' field with '4242 4242 4242 4242'",
        "mode": "input", "search_texts": ["Card Number"], "target_field": "card number",
        "expected": "trap_float_input",
    },
    {
        "name": "24. Table Row Checkbox Disambiguation",
        "desc": "two identical checkboxes; row text 'Laptop' distinguishes the correct one",
        "step": "Select the checkbox for product 'Laptop'",
        "mode": "clickable", "search_texts": ["Laptop"], "target_field": None,
        "expected": "trap_chk_laptop",
    },

    # ── NEW EXTREME TRAPS (Testing "if exists" logic) ──────────────────────
    {
        "name": "25. The Ghost of Cookies Past (Display None + Optional)",
        "desc": "Button is display: none. Step has 'if exists'. Resolver must return None, execute_step must catch and return True.",
        "step": "Click the 'Accept Cookies' button if exists",
        "mode": "clickable", "search_texts": ["Accept Cookies"], "target_field": None,
        "expected": None,  # We EXPECT the resolver to fail to find it, and execute_step to handle it.
    },
    {
        "name": "26. Zero-Pixel Sabotage (Optional)",
        "desc": "Button exists in DOM but is 0x0. JS scraper ignores it. Step has 'if exists'. Should skip.",
        "step": "Click the 'Close Ad' button if exists",
        "mode": "clickable", "search_texts": ["Close Ad"], "target_field": None,
        "expected": None,
    },
    {
        "name": "27. The Decoy 'If Exists' text",
        "desc": "The target label LITERALLY contains the text 'if exists'. The engine should NOT skip it, but successfully fill it.",
        "step": "Fill 'Promotion Code if exists' field with 'DISCOUNT'",
        "mode": "input", "search_texts": ["Promotion Code if exists"], "target_field": "promotion code if exists",
        "expected": "trap_promo_optional_input",
    },
    {
        "name": "28. Missing Target with 'Optional' keyword",
        "desc": "Element completely absent from DOM. Step has keyword 'optional'. Should skip gracefully.",
        "step": "Click the 'Dismiss Popup' button optional",
        "mode": "clickable", "search_texts": ["Dismiss Popup"], "target_field": None,
        "expected": None,
    },

    # ── TRAPS 29-34: Real Bugs from Integration Test Battles ───────────
    {
        "name": "29. Check Mode — Checkbox Priority",
        "desc": "Bug: 'check' didn't trigger clickable mode. Checkbox must beat same-named text input when step says 'checkbox'.",
        "step": "Check the 'Agree to Terms' checkbox",
        "mode": "clickable", "search_texts": ["Agree to Terms"], "target_field": None,
        "expected": "trap_check_agree_chk",
    },
    {
        "name": "30. Uncheck Mode — Checkbox over Button",
        "desc": "Bug: 'uncheck' didn't trigger clickable mode. Checkbox must beat button with similar text.",
        "step": "Uncheck the 'Auto-Renew' checkbox",
        "mode": "clickable", "search_texts": ["Auto-Renew"], "target_field": None,
        "expected": "trap_uncheck_renew_chk",
    },
    {
        "name": "31. Select Triple Collision (select > checkbox + radio)",
        "desc": "Bug: checkbox outscored <select> in select mode. Select must beat BOTH checkbox AND radio.",
        "step": "Select 'Urgent' from the 'Priority' dropdown",
        "mode": "select", "search_texts": ["Urgent", "Priority"], "target_field": None,
        "expected": "trap_priority_select",
    },
    {
        "name": "32. Optional Partial-Match Decoy (must skip)",
        "desc": "Bug: optional steps clicked partial-match elements. 'Banner Ad' not in 'Ad Settings' — must skip.",
        "step": "Click the 'Banner Ad' button if exists",
        "mode": "clickable", "search_texts": ["Banner Ad"], "target_field": None,
        "expected": None,
    },
    {
        "name": "33. data-qa Hyphen-Space Mapping",
        "desc": "data-qa='shipping-address' must match search text 'Shipping Address' via hyphen-space conversion.",
        "step": "Fill 'Shipping Address' field with '456 Oak Ave'",
        "mode": "input", "search_texts": ["Shipping Address"], "target_field": "shipping address",
        "expected": "trap_dqa_ship",
    },
    {
        "name": "34. Native Checkbox JS Click (full _execute_step)",
        "desc": "Bug: loc.click(force=True) failed on native checkboxes. Full flow must toggle via JS el.click().",
        "step": "Check the 'Enable Notifications' checkbox",
        "mode": "clickable", "search_texts": ["Enable Notifications"], "target_field": None,
        "expected": "trap_jsclick_chk",
        "execute_step": True,
        "verify_checked": True,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Guard logic (mirrors _execute_step guards in engine.py)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_guards(el: dict, mode: str, search_texts: list[str]) -> str | None:
    """Return a rejection reason string, or None if element passes."""
    if el is None: return None # Optional targets will be None, skip guard check
    tag   = el.get("tag_name", "")
    itype = el.get("input_type", "")
    role  = el.get("role", "")
    name  = el.get("name", "")

    if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
        return f"cannot type into {itype}"

    if mode == "select":
        valid = (
            tag == "select"
            or role in ("option", "menuitem")
            or "item" in name.lower()
            or "dropdown" in name.lower()
        )
        if not valid:
            return f"not a SELECT (tag={tag})"

    return None

# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────
async def run_laboratory():
    print("\n" + "=" * 60)
    print("🧪  MANUL ENGINE LABORATORY — The Chaos Chamber (34 traps)")
    print("=" * 60)

    # Note: we test using execute_step directly for optional traps to see the full flow
    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.set_content(MONSTER_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🧬 {t['name']}")
            print(f"   📋 {t['desc']}")
            print(f"   🐾 Step : {t['step']}")

            # Clear context memory between steps to avoid false positives from previous traps
            manul.last_xpath = None 

            if t.get("execute_step"):
                # Full _execute_step flow — tests mode detection + scoring + action
                result = await manul._execute_step(page, t["step"], "")
                if not result:
                    msg = "FAILED — _execute_step returned False"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")
                elif t.get("verify_checked") is not None:
                    actual = await page.locator(f"#{t['expected']}").is_checked()
                    if actual == t["verify_checked"]:
                        print(f"   ✅ PASSED  → '{t['expected']}' checked={actual} via _execute_step")
                        passed += 1
                    else:
                        msg = f"FAILED — '{t['expected']}' checked={actual}, expected {t['verify_checked']}"
                        print(f"   ❌ {msg}")
                        failed += 1
                        failures.append(f"{t['name']}: {msg}")
                else:
                    print(f"   ✅ PASSED  → via _execute_step")
                    passed += 1

            elif "if exists" in t["step"].lower() or "optional" in t["step"].lower():
                # For optional traps, we must test the FULL _execute_step logic, 
                # because the skipping logic lives there, not in _resolve_element.
                result = await manul._execute_step(page, t["step"], "")
                
                # If expected is None, it means we WANTED it to skip gracefully (return True)
                if t["expected"] is None:
                    if result is True:
                        print("   ✅ PASSED  → Optional element skipped gracefully")
                        passed += 1
                    else:
                        print("   ❌ FAILED — Engine crashed or returned False instead of skipping")
                        failed += 1
                        failures.append(f"{t['name']}: Failed to skip optional element")
                else:
                    # Decoy trap (Trap 27) - it has "if exists" in name, but we EXPECT it to find it
                    el = await manul._resolve_element(page, t["step"], t["mode"], t["search_texts"], t["target_field"], "", set())
                    found_id = el.get("html_id", "") if el else None
                    if found_id == t["expected"]:
                         print(f"   ✅ PASSED  → '{found_id}' via Heuristics (Decoy bypass successful)")
                         passed += 1
                    else:
                         print(f"   ❌ FAILED — expected '{t['expected']}', got '{found_id}'")
                         failed += 1
                         failures.append(f"{t['name']}: Decoy logic failed")

            else:
                # Standard resolve testing for normal traps
                failed_ids: set[int] = set()
                el = await manul._resolve_element(
                    page              = page,
                    step              = t["step"],
                    mode              = t["mode"],
                    search_texts      = t["search_texts"],
                    target_field      = t["target_field"],
                    strategic_context = "",
                    failed_ids        = failed_ids,
                )

                if el is None:
                    msg = "FAILED — resolver returned None"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")
                    print("   " + "─" * 56)
                    continue

                rejection = _apply_guards(el, t["mode"], t["search_texts"])
                if rejection:
                    msg = f"FAILED — guard rejected '{el.get('html_id')}' ({rejection})"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")
                    print("   " + "─" * 56)
                    continue

                found_id  = el.get("html_id", "")
                score     = el.get("score", 0)
                resolver  = (
                    "SEMANTIC CACHE"  if score >= 20_000 else
                    "CONTEXT MEMORY"  if score >= 10_000 else
                    f"HEURISTICS (score {score})" if score >= 500 else
                    "AI AGENT"
                )

                if found_id == t["expected"]:
                    print(f"   ✅ PASSED  → '{found_id}'  via {resolver}")
                    passed += 1
                else:
                    msg = f"FAILED — got '{found_id}', expected '{t['expected']}' (score {score})"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")

            print("   " + "─" * 56)

        # ── Summary ──────────────────────────────────────────────────────
        print(f"\n{'=' * 60}")
        print(f"📊 SCORE: {passed}/{len(TESTS)} passed")

        if failures:
            print("\n💀 Failures:")
            for f in failures:
                print(f"   • {f}")

        if passed == len(TESTS):
            print("\n🏆 FLAWLESS VICTORY! The Manul engine is unbreakable!")
        elif passed >= len(TESTS) * 0.75:
            print("\n🐾 Good hunt — a few prey escaped.")
        else:
            print("\n💀 The chaos chamber won this round.")

        print("=" * 60)
        await browser.close()

    return passed == len(TESTS)

if __name__ == "__main__":
    asyncio.run(run_laboratory())