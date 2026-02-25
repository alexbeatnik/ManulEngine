import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import re
from playwright.async_api import async_playwright
from framework.engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# MONSTER DOM  —  Each trap section is labelled clearly.
# Original 12 traps preserved verbatim; 12 new traps appended below.
# ─────────────────────────────────────────────────────────────────────────────
MONSTER_DOM = """
<!DOCTYPE html>
<html>
<head><title>Monster DOM</title></head>
<body>

<!-- ══════════════ ORIGINAL 12 TRAPS ══════════════ -->

<!-- Trap 1 -->
<fieldset>
    <legend>Suggession Class</legend>
    <input type="text" id="trap_legend_input" placeholder="Type here">
</fieldset>

<!-- Trap 2 -->
<div>
    <label for="trap_phantom_chk">Option 1</label>
    <input type="checkbox" id="trap_phantom_chk">

    <label for="trap_phantom_select">Dropdown</label>
    <select id="trap_phantom_select">
        <option>Select...</option>
        <option>Option 1</option>
    </select>
</div>

<!-- Trap 3 -->
<div>
    <button id="trap_hidden_btn" style="display: none;">Submit Login</button>
    <div id="trap_fake_btn" class="button" role="button">Submit Login</div>
    <input type="submit" id="trap_real_btn" value="Submit Login">
</div>

<!-- Trap 4 -->
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

<!-- Trap 5 -->
<div>
    <button id="trap_aria_btn" aria-label="Close Window">X</button>
    <div id="trap_wrong_aria" role="button">Close Window</div>
</div>

<!-- Trap 6 -->
<div>
    <button id="trap_btn_partial1">Save and Continue</button>
    <button id="trap_btn_exact">Save</button>
    <button id="trap_btn_partial2">Save Draft</button>
</div>

<!-- Trap 7 -->
<div>
    <label for="trap_opacity_chk">Accept Terms</label>
    <input type="checkbox" id="trap_opacity_chk" style="opacity: 0.01;">
</div>

<!-- Trap 8 -->
<div>
    <input type="text" id="trap_placeholder_input" placeholder="Secret Token">
    <div id="trap_placeholder_div">Secret Token</div>
</div>

<!-- Trap 9 -->
<fieldset>
    <legend>Subscribe?</legend>
    <input type="radio" id="trap_radio_yes" name="sub" value="yes">
    <label for="trap_radio_yes">Yes</label>
    <input type="radio" id="trap_radio_no" name="sub" value="no">
    <label for="trap_radio_no">No</label>
</fieldset>

<!-- Trap 10 -->
<div>
    <div id="trap_role_chk" role="checkbox" aria-checked="false" aria-label="Remember Me"></div>
    <input type="text" id="trap_wrong_input" aria-label="Remember Me">
</div>

<!-- Trap 11 -->
<div>
    <button id="trap_text_btn">Confirm Order</button>
    <button id="trap_qa_btn" data-qa="confirm-order">Click Here</button>
</div>

<!-- Trap 12 -->
<div>
    <button id="trap_btn_login">Register Portal</button>
    <a href="/login" id="trap_link_login">Register Portal</a>
</div>

<!-- ══════════════ NEW 12 TRAPS ══════════════ -->

<!-- Trap 13: Same field name in two sections — pick the one in correct section.
     Step says "Fill 'Email' field in the Login Form section" →
     must pick trap_section_login, NOT trap_section_signup. -->
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

<!-- Trap 14: Icon-only button — no visible text, action clue lives in icon classes.
     Step says "Click the search button" → must pick the button with fa-search icon. -->
<div>
    <button id="trap_icon_wrong">Filter</button>
    <button id="trap_icon_search"><i class="fa fa-search"></i></button>
    <button id="trap_icon_close"><i class="fa fa-times"></i></button>
</div>

<!-- Trap 15: Disabled element avoidance.
     Step says "Click the 'Submit' button" → must skip the disabled one. -->
<div>
    <button id="trap_disabled_btn" disabled>Submit</button>
    <button id="trap_enabled_btn">Submit</button>
</div>

<!-- Trap 16: Input[type=number] vs input[type=text] — same label.
     Step says "Fill 'Quantity' field with '5'" → prefers text/number input, not button. -->
<div>
    <button id="trap_qty_btn">Quantity</button>
    <label for="trap_qty_input">Quantity</label>
    <input type="number" id="trap_qty_input" min="1">
</div>

<!-- Trap 17: Nested vs flat label association.
     Step says "Click the checkbox for 'Newsletter'" → wrapping label IS the correct target. -->
<div>
    <label id="trap_newsletter_label">
        <input type="checkbox" id="trap_newsletter_chk">
        Newsletter
    </label>
    <div id="trap_newsletter_div">Newsletter</div>
</div>

<!-- Trap 18: Homonyms — "Delete" appears on two buttons; data-qa disambiguates.
     Step says "Click the 'Delete' button for the selected item" →
     data-qa="delete-selected" wins over generic id. -->
<div>
    <button id="trap_delete_all" data-qa="delete-all">Delete</button>
    <button id="trap_delete_selected" data-qa="delete-selected">Delete</button>
</div>

<!-- Trap 19: Readonly input — must remove readonly before typing.
     Step says "Fill 'Promo Code' field with 'MANUL2025'" → only input is readonly. -->
<div>
    <label for="trap_readonly_input">Promo Code</label>
    <input type="text" id="trap_readonly_input" readonly value="PLACEHOLDER">
    <button id="trap_readonly_btn">Promo Code</button>
</div>

<!-- Trap 20: Title attribute as last-resort label.
     Step says "Click the 'Settings' button" → button has only a title, no text. -->
<div>
    <button id="trap_title_wrong">Options</button>
    <button id="trap_title_btn" title="Settings">⚙</button>
</div>

<!-- Trap 21: Link vs button — step explicitly says "button" but both exist with same text.
     Step says "Click the 'Download' button" → must pick button, not <a>. -->
<div>
    <a href="/download" id="trap_download_link">Download</a>
    <button id="trap_download_btn">Download</button>
</div>

<!-- Trap 22: Two inputs with identical placeholder, different types.
     Step says "Fill the 'password' field with 'hunter2'" → must pick type=password, not text. -->
<div>
    <input type="text"     id="trap_pw_text"  placeholder="password">
    <input type="password" id="trap_pw_pass"  placeholder="password">
</div>

<!-- Trap 23: Floating label (label becomes placeholder, is inside the input wrapper).
     Step says "Fill 'Card Number' field with '4242 4242 4242 4242'" →
     must find the actual input, not the floating-label span. -->
<div class="floating-field">
    <span id="trap_float_label" class="float-label">Card Number</span>
    <input type="text" id="trap_float_input" data-qa="card-number">
</div>

<!-- Trap 24: Table row checkbox — pick the checkbox in the row that matches text, not any checkbox.
     Step says "Select the checkbox for product 'Laptop'" →
     must pick trap_chk_laptop, not trap_chk_phone. -->
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

</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Test catalogue
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── ORIGINAL 12 ────────────────────────────────────────────────────────
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

    # ── NEW 12 ──────────────────────────────────────────────────────────────
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
]


# ─────────────────────────────────────────────────────────────────────────────
# Guard logic (mirrors _execute_step guards in engine.py)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_guards(el: dict, mode: str, search_texts: list[str]) -> str | None:
    """Return a rejection reason string, or None if element passes."""
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
    print("🧪  MANUL ENGINE LABORATORY — The Chaos Chamber (24 traps)")
    print("=" * 60)

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

            failed_ids: set[int] = set()
            el = await manul._resolve_element(
                page           = page,
                step           = t["step"],
                mode           = t["mode"],
                search_texts   = t["search_texts"],
                target_field   = t["target_field"],
                strategic_context = "",
                failed_ids     = failed_ids,
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