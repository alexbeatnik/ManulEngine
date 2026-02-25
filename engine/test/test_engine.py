import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import asyncio
import re
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# MONSTER DOM  —  Each trap section is labelled clearly.
# Original 24 traps + 4 optional + 6 bug-fix + 12 hunt-site + 14 normal = 60.
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

<!-- ── TRAPS 35-46: Patterns from real hunt-site tests ─────────────── -->

<!-- 35. Textarea vs Input (Mega: Address) -->
<div>
    <label for="trap_addr_textarea">Address</label>
    <input type="text" id="trap_addr_text_decoy" placeholder="City name">
    <textarea id="trap_addr_textarea" placeholder="Full address"></textarea>
</div>

<!-- 36-37. Double Click Me vs Click Me (DemoQA) -->
<div>
    <button id="trap_dblclick_btn" ondblclick="this.dataset.clicked='double'">Double Click Me</button>
    <button id="trap_singleclick_btn">Click Me</button>
</div>

<!-- 38. Date input type priority (DemoQA/ExpandTesting) -->
<div>
    <label for="trap_date_input">Start Date</label>
    <input type="date" id="trap_date_input">
    <label for="trap_date_notes">Start Date Notes</label>
    <input type="text" id="trap_date_notes">
</div>

<!-- 39. Search input (Wikipedia: Search Wikipedia) -->
<div>
    <input type="search" id="trap_search_input" placeholder="Search Articles" aria-label="Search Articles">
    <button id="trap_search_btn">Search</button>
</div>

<!-- 40. Pagination links (Mega: Click on page 3) -->
<nav>
    <a href="#" id="trap_page_1">1</a>
    <a href="#" id="trap_page_2">2</a>
    <a href="#" id="trap_page_3">3</a>
    <a href="#" id="trap_page_next">Next</a>
</nav>

<!-- 41. Day-of-week checkboxes (Mega/Rahul: Monday/Wednesday) -->
<div>
    <label for="trap_day_mon">Monday</label>
    <input type="checkbox" id="trap_day_mon">
    <label for="trap_day_tue">Tuesday</label>
    <input type="checkbox" id="trap_day_tue">
    <label for="trap_day_wed">Wednesday</label>
    <input type="checkbox" id="trap_day_wed">
    <label for="trap_day_thu">Thursday</label>
    <input type="checkbox" id="trap_day_thu">
</div>

<!-- 42. Country dropdown (Mega: Select Japan from Country) -->
<div>
    <label for="trap_country_select">Country</label>
    <select id="trap_country_select">
        <option>Select Country</option>
        <option>India</option>
        <option>Japan</option>
        <option>United States</option>
    </select>
</div>

<!-- 43. Hover button (Rahul: Mouse Hover) -->
<div>
    <button id="trap_hover_btn" onmouseover="this.dataset.hovered='yes'">Mouse Hover</button>
</div>

<!-- 44-45. Checkbox toggle — check then uncheck (Rahul) -->
<div>
    <label for="trap_toggle_chk">Accept Marketing</label>
    <input type="checkbox" id="trap_toggle_chk">
</div>

<!-- 46. Fill + Enter (Wikipedia: Fill search and press Enter) -->
<div>
    <input type="search" id="trap_enter_input" placeholder="Wiki Search" aria-label="Wiki Search"
           onkeydown="if(event.key==='Enter') this.dataset.entered='yes'">
</div>

<!-- ══════════════════════════════════════════════════════════════════ -->
<!-- NORMAL ELEMENTS 47-60: No tricks, pure functionality checks       -->
<!-- ══════════════════════════════════════════════════════════════════ -->

<!-- 47. Simple text input -->
<div>
    <label for="norm_fullname">Full Name</label>
    <input type="text" id="norm_fullname">
</div>

<!-- 48. Simple email input -->
<div>
    <label for="norm_email">Work Email</label>
    <input type="email" id="norm_email" placeholder="your@email.com">
</div>

<!-- 49. Simple text input (another variant) -->
<div>
    <label for="norm_token">API Token</label>
    <input type="text" id="norm_token">
</div>

<!-- 50. Simple textarea -->
<div>
    <label for="norm_comment">Comment</label>
    <textarea id="norm_comment" rows="3"></textarea>
</div>

<!-- 51. Simple button -->
<div>
    <button id="norm_submit_btn" onclick="this.dataset.done='yes'">Send Message</button>
</div>

<!-- 52. Simple link -->
<div>
    <a href="#about" id="norm_about_link">About Us</a>
</div>

<!-- 53. Readonly input (fill via JS) -->
<div>
    <label for="norm_readonly">Coupon Code</label>
    <input type="text" id="norm_readonly" readonly value="OLD-CODE">
</div>

<!-- 54. Input + Enter key -->
<div>
    <label for="norm_login_user">Username</label>
    <input type="text" id="norm_login_user"
           onkeydown="if(event.key==='Enter') this.dataset.submitted='yes'">
</div>

<!-- 55. Simple radio group -->
<fieldset>
    <legend>Gender</legend>
    <input type="radio" id="norm_radio_male" name="gender" value="male">
    <label for="norm_radio_male">Male</label>
    <input type="radio" id="norm_radio_female" name="gender" value="female">
    <label for="norm_radio_female">Female</label>
</fieldset>

<!-- 56-57. Simple checkbox + verify -->
<div>
    <label for="norm_agree_chk">I Agree</label>
    <input type="checkbox" id="norm_agree_chk">
</div>

<!-- 58. Simple native <select> -->
<div>
    <label for="norm_color_select">Favorite Color</label>
    <select id="norm_color_select">
        <option>-- pick --</option>
        <option>Red</option>
        <option>Green</option>
        <option>Blue</option>
    </select>
</div>

<!-- 59. Verify text presence / absence -->
<div id="norm_message_box">Operation completed successfully</div>
<div id="norm_hidden_error" style="display:none">Critical failure</div>

<!-- 60. Extract from table -->
<table id="norm_price_table">
    <thead><tr><th>Product</th><th>Price</th></tr></thead>
    <tbody>
        <tr><td>Keyboard</td><td>$49</td></tr>
        <tr><td>Monitor</td><td>$299</td></tr>
        <tr><td>Mouse</td><td>$25</td></tr>
    </tbody>
</table>

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

    # ── TRAPS 35-46: Patterns from Real Hunt-Site Tests ────────────────
    {
        "name": "35. Textarea vs Input — Address (Mega)",
        "desc": "Mega site: 'Fill Address textarea' must pick <textarea>, not nearby <input type=text>.",
        "step": "Fill 'Address' textarea with 'Selenium Avenue, 42'",
        "mode": "input", "search_texts": ["Address"], "target_field": "address",
        "expected": "trap_addr_textarea",
    },
    {
        "name": "36. Exact 'Click Me' vs Partial 'Double Click Me' (DemoQA)",
        "desc": "DemoQA: 'Click Me' must beat 'Double Click Me' — exact match wins over partial.",
        "step": "Click the 'Click Me' button",
        "mode": "clickable", "search_texts": ["Click Me"], "target_field": None,
        "expected": "trap_singleclick_btn",
    },
    {
        "name": "37. Date Input Type Priority (DemoQA/ExpandTesting)",
        "desc": "Two inputs share label 'Start Date'; type=date must beat type=text.",
        "step": "Fill 'Start Date' field with '2026-01-01'",
        "mode": "input", "search_texts": ["Start Date"], "target_field": "start date",
        "expected": "trap_date_input",
    },
    {
        "name": "38. Search Input by Type+ARIA (Wikipedia)",
        "desc": "Wikipedia: input[type=search] with aria-label must be found for fill mode.",
        "step": "Fill 'Search Articles' field with 'Pallas cat'",
        "mode": "input", "search_texts": ["Search Articles"], "target_field": "search articles",
        "expected": "trap_search_input",
    },
    {
        "name": "39. Pagination Link by Number (Mega)",
        "desc": "Mega: 'Click on page 3' must resolve to the <a> with text '3', not 'Next'.",
        "step": "Click on page '3' in the pagination list",
        "mode": "clickable", "search_texts": ["3"], "target_field": None,
        "expected": "trap_page_3",
    },
    {
        "name": "40. Day Checkbox Disambiguation (Mega/Rahul)",
        "desc": "Four day-of-week checkboxes; 'Wednesday' must pick the right one.",
        "step": "Click the checkbox for 'Wednesday'",
        "mode": "clickable", "search_texts": ["Wednesday"], "target_field": None,
        "expected": "trap_day_wed",
    },
    {
        "name": "41. Country Dropdown Resolution (Mega)",
        "desc": "Mega: 'Select Japan from Country dropdown' must resolve to the <select>.",
        "step": "Select 'Japan' from the 'Country' dropdown",
        "mode": "select", "search_texts": ["Japan", "Country"], "target_field": None,
        "expected": "trap_country_select",
    },
    {
        "name": "42. Double-Click Full Flow (DemoQA/Mega)",
        "desc": "'DOUBLE CLICK' must resolve correct button AND fire dblclick event.",
        "step": "DOUBLE CLICK the 'Double Click Me' button",
        "mode": "clickable", "search_texts": ["Double Click Me"], "target_field": None,
        "expected": "trap_dblclick_btn",
        "execute_step": True,
        "verify_attr": {"selector": "#trap_dblclick_btn", "attr": "data-clicked", "value": "double"},
    },
    {
        "name": "43. Hover Full Flow (Rahul)",
        "desc": "'HOVER over the Mouse Hover button' must resolve + fire mouseover event.",
        "step": "HOVER over the 'Mouse Hover' button",
        "mode": "hover", "search_texts": ["Mouse Hover"], "target_field": None,
        "expected": "trap_hover_btn",
        "execute_step": True,
        "verify_attr": {"selector": "#trap_hover_btn", "attr": "data-hovered", "value": "yes"},
    },
    {
        "name": "44. Select Option Full Flow (Mega)",
        "desc": "'Select Japan from Country' must resolve <select> AND pick the right <option>.",
        "step": "Select 'Japan' from the 'Country' dropdown",
        "mode": "select", "search_texts": ["Japan", "Country"], "target_field": None,
        "expected": "trap_country_select",
        "execute_step": True,
        "verify_select": {"selector": "#trap_country_select", "value": "Japan"},
    },
    {
        "name": "45. Checkbox Toggle — Check (Rahul pt1)",
        "desc": "Rahul: 'Check the checkbox' must toggle it ON. Verify checked=True.",
        "step": "Check the 'Accept Marketing' checkbox",
        "mode": "clickable", "search_texts": ["Accept Marketing"], "target_field": None,
        "expected": "trap_toggle_chk",
        "execute_step": True,
        "verify_checked": True,
    },
    {
        "name": "46. Checkbox Toggle — Uncheck (Rahul pt2)",
        "desc": "Rahul: clicking same checkbox again must toggle it OFF. Verify checked=False.",
        "step": "Click the checkbox for 'Accept Marketing'",
        "mode": "clickable", "search_texts": ["Accept Marketing"], "target_field": None,
        "expected": "trap_toggle_chk",
        "execute_step": True,
        "verify_checked": False,
    },

    # ── NORMAL ELEMENTS 47-60: Straightforward Sanity Checks ──────────
    {
        "name": "47. Simple Text Input Fill (DemoQA: Full Name)",
        "desc": "No tricks — label+input pair. Must fill and verify value.",
        "step": "Fill 'Full Name' field with 'Ghost Manul'",
        "mode": "input", "search_texts": ["Full Name"], "target_field": "full name",
        "expected": "norm_fullname",
        "execute_step": True,
        "verify_value": {"selector": "#norm_fullname", "value": "Ghost Manul"},
    },
    {
        "name": "48. Email Input Fill (DemoQA/ExpandTesting)",
        "desc": "type=email input with label. Must fill correctly.",
        "step": "Fill 'Work Email' field with 'ghost@manul.ai'",
        "mode": "input", "search_texts": ["Work Email"], "target_field": "work email",
        "expected": "norm_email",
        "execute_step": True,
        "verify_value": {"selector": "#norm_email", "value": "ghost@manul.ai"},
    },
    {
        "name": "49. Text Input Fill — API Token",
        "desc": "Simple text input with unique label. Must fill correctly.",
        "step": "Fill 'API Token' field with 'SuperSecret123'",
        "mode": "input", "search_texts": ["API Token"], "target_field": "api token",
        "expected": "norm_token",
        "execute_step": True,
        "verify_value": {"selector": "#norm_token", "value": "SuperSecret123"},
    },
    {
        "name": "50. Textarea Fill (Mega: Comment/Address)",
        "desc": "Simple <textarea> fill. Must type multi-word text.",
        "step": "Fill 'Comment' field with 'Great product, highly recommended'",
        "mode": "input", "search_texts": ["Comment"], "target_field": "comment",
        "expected": "norm_comment",
        "execute_step": True,
        "verify_value": {"selector": "#norm_comment", "value": "Great product, highly recommended"},
    },
    {
        "name": "51. Simple Button Click (DemoQA: Submit)",
        "desc": "Single button, no ambiguity. Click must fire onclick handler.",
        "step": "Click the 'Send Message' button",
        "mode": "clickable", "search_texts": ["Send Message"], "target_field": None,
        "expected": "norm_submit_btn",
        "execute_step": True,
        "verify_attr": {"selector": "#norm_submit_btn", "attr": "data-done", "value": "yes"},
    },
    {
        "name": "52. Simple Link Click (DemoQA: About Us)",
        "desc": "Single <a> link. 'Click the link' must resolve to it.",
        "step": "Click the 'About Us' link",
        "mode": "clickable", "search_texts": ["About Us"], "target_field": None,
        "expected": "norm_about_link",
    },
    {
        "name": "53. Readonly Input Fill via JS (Rahul: Coupon Code)",
        "desc": "readonly input must be unlocked and filled via JS injection.",
        "step": "Fill 'Coupon Code' field with 'MANUL2026'",
        "mode": "input", "search_texts": ["Coupon Code"], "target_field": "coupon code",
        "expected": "norm_readonly",
        "execute_step": True,
        "verify_value": {"selector": "#norm_readonly", "value": "MANUL2026"},
    },
    {
        "name": "54. Fill + Press Enter (Wikipedia: Search)",
        "desc": "'Fill Username and press Enter' must type AND send Enter key.",
        "step": "Fill 'Username' field with 'admin' and press Enter",
        "mode": "input", "search_texts": ["Username"], "target_field": "username",
        "expected": "norm_login_user",
        "execute_step": True,
        "verify_attr": {"selector": "#norm_login_user", "attr": "data-submitted", "value": "yes"},
    },
    {
        "name": "55. Simple Radio Select (Mega/Rahul: Gender)",
        "desc": "Gender radio group. 'Female' must resolve to correct radio.",
        "step": "Click the radio button for 'Female'",
        "mode": "clickable", "search_texts": ["Female"], "target_field": None,
        "expected": "norm_radio_female",
        "execute_step": True,
        "verify_checked": True,
    },
    {
        "name": "56. Simple Checkbox Check (ExpandTesting)",
        "desc": "Check 'I Agree' checkbox. Must toggle ON.",
        "step": "Check the 'I Agree' checkbox",
        "mode": "clickable", "search_texts": ["I Agree"], "target_field": None,
        "expected": "norm_agree_chk",
        "execute_step": True,
        "verify_checked": True,
    },
    {
        "name": "57. VERIFY Checked State (ExpandTesting/Mega)",
        "desc": "Engine run_mission calls _handle_verify. Must confirm 'I Agree' is checked.",
        "step": "VERIFY that 'I Agree' is checked.",
        "verify_step": True,
        "expected_result": True,
    },
    {
        "name": "58. Simple Select Option (Mega: Color)",
        "desc": "Pick 'Blue' from a clean <select>. Must select the correct <option>.",
        "step": "Select 'Blue' from the 'Favorite Color' dropdown",
        "mode": "select", "search_texts": ["Blue", "Favorite Color"], "target_field": None,
        "expected": "norm_color_select",
        "execute_step": True,
        "verify_select": {"selector": "#norm_color_select", "value": "Blue"},
    },
    {
        "name": "59. VERIFY Text Present + NOT Present (all sites)",
        "desc": "Must find visible text and confirm hidden text is absent.",
        "verify_step": True,
        "step": "VERIFY that 'Operation completed successfully' is present.",
        "expected_result": True,
        "followup": {
            "step": "VERIFY that 'Critical failure' is NOT present.",
            "expected_result": True,
        },
    },
    {
        "name": "60. EXTRACT from Table (Mega/Rahul/ExpandTesting)",
        "desc": "Extract 'Monitor' price from a standard HTML table. Must return '$299'.",
        "step": "EXTRACT the Price of 'Monitor' into {monitor_price}",
        "extract_step": True,
        "expected_var": "monitor_price",
        "expected_value": "$299",
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
    print("🧪  MANUL ENGINE LABORATORY — The Chaos Chamber (60 tests)")
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

            if t.get("extract_step"):
                # EXTRACT test — calls _handle_extract and checks memory
                manul.memory.clear()
                result = await manul._handle_extract(page, t["step"])
                actual_val = manul.memory.get(t["expected_var"], None)
                if result and actual_val == t["expected_value"]:
                    print(f"   ✅ PASSED  → {{{t['expected_var']}}} = '{actual_val}'")
                    passed += 1
                else:
                    msg = f"FAILED — got '{actual_val}', expected '{t['expected_value']}'"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")

            elif t.get("verify_step"):
                # VERIFY test — calls _handle_verify
                result = await manul._handle_verify(page, t["step"])
                if result == t["expected_result"]:
                    print(f"   ✅ PASSED  → VERIFY returned {result}")
                    passed += 1
                else:
                    msg = f"FAILED — VERIFY returned {result}, expected {t['expected_result']}"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")
                # Handle followup verify (e.g., NOT present check)
                if t.get("followup") and result == t["expected_result"]:
                    fu = t["followup"]
                    fu_result = await manul._handle_verify(page, fu["step"])
                    if fu_result == fu["expected_result"]:
                        print(f"   ✅ FOLLOWUP  → VERIFY NOT returned {fu_result}")
                    else:
                        msg = f"FOLLOWUP FAILED — VERIFY returned {fu_result}, expected {fu['expected_result']}"
                        print(f"   ❌ {msg}")
                        # Don't double-count; the main test already counted

            elif t.get("execute_step"):
                # Full _execute_step flow — tests mode detection + scoring + action
                result = await manul._execute_step(page, t["step"], "")
                if not result:
                    msg = "FAILED — _execute_step returned False"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")
                else:
                    verify_ok = True
                    verify_detail = ""

                    if t.get("verify_checked") is not None:
                        actual = await page.locator(f"#{t['expected']}").is_checked()
                        if actual != t["verify_checked"]:
                            verify_ok = False
                            verify_detail = f"checked={actual}, expected {t['verify_checked']}"
                        else:
                            verify_detail = f"checked={actual}"

                    elif t.get("verify_attr"):
                        va = t["verify_attr"]
                        actual = await page.locator(va["selector"]).get_attribute(va["attr"])
                        if actual != va["value"]:
                            verify_ok = False
                            verify_detail = f"{va['attr']}='{actual}', expected '{va['value']}'"
                        else:
                            verify_detail = f"{va['attr']}='{actual}'"

                    elif t.get("verify_select"):
                        vs = t["verify_select"]
                        actual = await page.locator(vs["selector"]).evaluate(
                            "sel => sel.options[sel.selectedIndex].text.trim()"
                        )
                        if actual != vs["value"]:
                            verify_ok = False
                            verify_detail = f"selected='{actual}', expected '{vs['value']}'"
                        else:
                            verify_detail = f"selected='{actual}'"

                    elif t.get("verify_value"):
                        vv = t["verify_value"]
                        actual = await page.locator(vv["selector"]).input_value()
                        if actual != vv["value"]:
                            verify_ok = False
                            verify_detail = f"value='{actual}', expected '{vv['value']}'"
                        else:
                            verify_detail = f"value='{actual}'"

                    if verify_ok:
                        desc = f"'{t['expected']}' {verify_detail}" if verify_detail else ""
                        print(f"   ✅ PASSED  → {desc} via _execute_step")
                        passed += 1
                    else:
                        msg = f"FAILED — '{t['expected']}' {verify_detail}"
                        print(f"   ❌ {msg}")
                        failed += 1
                        failures.append(f"{t['name']}: {msg}")

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