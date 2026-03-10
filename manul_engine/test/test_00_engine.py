import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import asyncio
import re
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# MONSTER DOM  —  80 TESTS (Traps + Integration Bugs + Real World Frameworks)
# ─────────────────────────────────────────────────────────────────────────────
MONSTER_DOM = """
<!DOCTYPE html>
<html>
<head>
    <title>Monster DOM 80</title>
    <style>
        /* Real-world utility classes simulation */
        .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
        .hidden-file { display: none; }
        .custom-switch { width: 40px; height: 20px; background: #ccc; border-radius: 10px; display: inline-block; cursor: pointer; }
    </style>
</head>
<body>

<fieldset>
    <legend>Suggession Class</legend>
    <input type="text" id="trap_legend_input" placeholder="Type here">
</fieldset>

<div>
    <label for="trap_phantom_chk">Option 1</label>
    <input type="checkbox" id="trap_phantom_chk">
    <label for="trap_phantom_select">Dropdown</label>
    <select id="trap_phantom_select"><option>Select...</option><option>Option 1</option></select>
</div>

<div>
    <button id="trap_hidden_btn" style="display: none;">Submit Login</button>
    <div id="trap_fake_btn" class="button" role="button">Submit Login</div>
    <input type="submit" id="trap_real_btn" value="Submit Login" aria-label="Submit Login">
</div>

<div id="host"></div>
<script>
    const host = document.getElementById('host');
    const shadow = host.attachShadow({mode: 'open'});
    const label = document.createElement('label'); label.textContent = 'Cyber Password';
    const input = document.createElement('input'); input.type = 'password'; input.id = 'trap_shadow_input';
    shadow.appendChild(label); shadow.appendChild(input);
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
    <input type="radio" id="trap_radio_yes" name="sub" value="yes"><label for="trap_radio_yes">Yes</label>
    <input type="radio" id="trap_radio_no" name="sub" value="no"><label for="trap_radio_no">No</label>
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
    <h3>Login Form</h3><label for="trap_section_login">Email</label><input type="email" id="trap_section_login">
</section>
<section id="signup-form-section">
    <h3>Signup Form</h3><label for="trap_section_signup">Email</label><input type="email" id="trap_section_signup">
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
    <button id="trap_qty_btn">Quantity</button><label for="trap_qty_input">Quantity</label><input type="number" id="trap_qty_input">
</div>

<div>
    <label id="trap_newsletter_label"><input type="checkbox" id="trap_newsletter_chk"> Newsletter</label>
    <div id="trap_newsletter_div">Newsletter</div>
</div>

<div>
    <button id="trap_delete_all" data-qa="delete-all">Delete</button>
    <button id="trap_delete_selected" data-qa="delete-selected">Delete</button>
</div>

<div>
    <label for="trap_readonly_input">Promo Code</label><input type="text" id="trap_readonly_input" readonly value="PLACEHOLDER">
    <button id="trap_readonly_btn">Promo Code</button>
</div>

<div>
    <button id="trap_title_wrong">Options</button><button id="trap_title_btn" title="Settings">⚙</button>
</div>

<div>
    <a href="/download" id="trap_download_link">Download</a><button id="trap_download_btn">Download</button>
</div>

<div>
    <input type="text" id="trap_pw_text" placeholder="password">
    <input type="password" id="trap_pw_pass" placeholder="password">
</div>

<div class="floating-field">
    <span id="trap_float_label" class="float-label">Card Number</span><input type="text" id="trap_float_input" data-qa="card-number">
</div>

<table>
    <tr><td><input type="checkbox" id="trap_chk_phone"></td><td>Phone</td><td>$699</td></tr>
    <tr><td><input type="checkbox" id="trap_chk_laptop"></td><td>Laptop</td><td>$1299</td></tr>
</table>

<div id="cookie_banner" style="display: none;"><button id="trap_cookie_btn">Accept Cookies</button></div>
<div><button id="trap_zero_pixel_btn" style="width: 0; height: 0; padding: 0; border: none; overflow: hidden;">Close Ad if exists</button></div>
<div><label for="trap_promo_optional_input">Promotion Code if exists</label><input type="text" id="trap_promo_optional_input"></div>

<div>
    <label for="trap_check_agree_chk">Agree to Terms</label><input type="checkbox" id="trap_check_agree_chk">
    <label for="trap_check_agree_input">Agree to Terms</label><input type="text" id="trap_check_agree_input">
</div>
<div>
    <label for="trap_uncheck_renew_chk">Auto-Renew</label><input type="checkbox" id="trap_uncheck_renew_chk" checked>
    <button id="trap_uncheck_renew_btn">Auto-Renew Settings</button>
</div>
<div>
    <label for="trap_priority_chk">Priority</label><input type="checkbox" id="trap_priority_chk">
    <input type="radio" id="trap_priority_radio" name="prio" value="urgent"><label for="trap_priority_radio">Urgent</label>
    <label for="trap_priority_select">Priority</label><select id="trap_priority_select"><option>Low</option><option>Urgent</option></select>
</div>
<div><button id="trap_partial_decoy_btn">Ad Settings</button></div>
<div>
    <input type="text" id="trap_addr_decoy" placeholder="Enter your address">
    <input type="text" id="trap_dqa_ship" data-qa="shipping-address">
</div>
<div><label for="trap_jsclick_chk">Enable Notifications</label><input type="checkbox" id="trap_jsclick_chk"></div>
<div>
    <label for="trap_addr_textarea">Address</label><input type="text" id="trap_addr_text_decoy">
    <textarea id="trap_addr_textarea"></textarea>
</div>
<div><button id="trap_dblclick_btn" ondblclick="this.dataset.clicked='double'">Double Click Me</button><button id="trap_singleclick_btn">Click Me</button></div>
<div>
    <label for="trap_date_input">Start Date</label><input type="date" id="trap_date_input">
    <label for="trap_date_notes">Start Date Notes</label><input type="text" id="trap_date_notes">
</div>
<div><input type="search" id="trap_search_input" placeholder="Search Articles" aria-label="Search Articles"><button id="trap_search_btn">Search</button></div>
<nav><a href="#" id="trap_page_1">1</a><a href="#" id="trap_page_2">2</a><a href="#" id="trap_page_3">3</a><a href="#" id="trap_page_next">Next</a></nav>
<div><label for="trap_day_wed">Wednesday</label><input type="checkbox" id="trap_day_wed"></div>
<div><label for="trap_country_select">Country</label><select id="trap_country_select"><option>India</option><option>Japan</option></select></div>
<div><button id="trap_hover_btn" onmouseover="this.dataset.hovered='yes'">Mouse Hover</button></div>
<div><label for="trap_toggle_chk">Accept Marketing</label><input type="checkbox" id="trap_toggle_chk"></div>
<div><input type="search" id="trap_enter_input" placeholder="Wiki Search" onkeydown="if(event.key==='Enter') this.dataset.entered='yes'"></div>

<div><label for="norm_fullname">Full Name</label><input type="text" id="norm_fullname"></div>
<div><label for="norm_email">Work Email</label><input type="email" id="norm_email"></div>
<div><label for="norm_token">API Token</label><input type="text" id="norm_token"></div>
<div><label for="norm_comment">Comment</label><textarea id="norm_comment" rows="3"></textarea></div>
<div><button id="norm_submit_btn" onclick="this.dataset.done='yes'">Send Message</button></div>
<div><a href="#about" id="norm_about_link">About Us</a></div>
<div><label for="norm_readonly">Coupon Code</label><input type="text" id="norm_readonly" readonly value="OLD"></div>
<div><label for="norm_login_user">Username</label><input type="text" id="norm_login_user" onkeydown="if(event.key==='Enter') this.dataset.submitted='yes'"></div>
<fieldset><input type="radio" id="norm_radio_female" name="gender"><label for="norm_radio_female">Female</label></fieldset>
<div><label for="norm_agree_chk">I Agree</label><input type="checkbox" id="norm_agree_chk"></div>
<div><label for="norm_color_select">Color</label><select id="norm_color_select"><option>Red</option><option>Blue</option></select></div>
<div id="norm_message_box">Operation completed successfully</div><div id="norm_hidden_error" style="display:none">Critical failure</div>
<table id="norm_price_table"><tr><td>Monitor</td><td>$299</td></tr></table>

<button id="rw_tw_btn" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline transition duration-150 ease-in-out">Deploy Application</button>

<button id="rw_svg_profile" aria-label="User Profile" style="width:40px; height:40px;">
    <svg viewBox="0 0 24 24" width="24" height="24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
</button>

<button id="rw_sr_bell" style="padding: 10px;">
    <span class="sr-only">View Notifications</span>
    🔔
</button>

<div style="display:flex; align-items:center;">
    <span id="rw_switch_label">Dark Mode</span>
    <div id="rw_custom_switch" role="switch" aria-checked="false" aria-labelledby="rw_switch_label" class="custom-switch"></div>
</div>

<div>
    <label id="rw_wysiwyg_label">Message Body</label>
    <div id="rw_wysiwyg" contenteditable="true" aria-labelledby="rw_wysiwyg_label" style="min-height: 50px; border: 1px solid #ccc;"></div>
</div>

<div>
    <label for="rw_file_input" id="rw_file_label" data-qa="upload-resume" style="cursor:pointer; background:#eee; padding:5px;">Upload Resume</label>
    <input type="file" id="rw_file_input" class="hidden-file" style="display:none;">
</div>

<table id="rw_users">
    <tr>
        <td>Alice</td>
        <td><button id="rw_edit_profile" data-testid="edit-user-btn">Edit Profile</button></td>
    </tr>
</table>

<div class="card" style="border:1px solid #ccc; padding:10px; width:200px;">
    <h2 id="rw_prod_title">Gaming Mouse</h2>
    <p>High DPI, RGB</p>
    <span class="price">$59.99</span>
    <button>Add</button>
</div>

<div class="modal" style="position:fixed; top:10px; right:10px; border:1px solid #000;">
    <button id="rw_modal_close" aria-label="Close dialog">✖</button>
    <p>Welcome to our site!</p>
</div>

<button id="rw_hamburger" aria-expanded="false" aria-label="Open Navigation" style="font-size:24px;">☰</button>

<button id="rw_google_btn" class="social-login">
    <img src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" alt="G" style="width:16px;"> 
    Continue with Google
</button>

<p>
    By checking this, I agree to the 
    <a href="/terms" id="rw_terms_link">Terms of Service</a> and Privacy Policy.
</p>

<button id="rw_next_step">Next: Shipping Details &rarr;</button>

<div role="radiogroup" aria-label="Rating">
    <div role="radio" aria-label="1 star" id="rw_star_1">⭐</div>
    <div role="radio" aria-label="5 stars" id="rw_star_5">⭐⭐⭐⭐⭐</div>
</div>

<button id="rw_load_more" class="btn-ghost" style="width:100%; padding:20px;">Load More Articles</button>

<div>
    <input type="text" value="manul_hater">
    <div id="rw_error_msg" class="text-red-500" style="color: red;">Username is already taken.</div>
</div>

<button id="rw_fab_create" title="Create New Post" style="position:fixed; bottom:20px; right:20px; border-radius:50%; width:50px; height:50px;">+</button>

<button id="rw_complex_btn">
    <span>Submit</span>
    <span>
        <span>Order</span>
    </span>
</button>

<div id="rw_cart_widget">
    Cart <span id="rw_cart_count" class="badge">3</span>
</div>

<div class="video-container">
    <button id="rw_play_btn" aria-label="Play Video">▶️</button>
</div>

</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Test catalogue
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── ORIGINAL 24 ────────────────────────────────────────────────────────
    {"name": "1", "step": "Fill 'Suggession Class' field with 'Ukraine'", "mode": "input", "search_texts": ["Suggession Class"], "target_field": "suggession class", "expected": "trap_legend_input"},
    {"name": "2", "step": "Select 'Option 1' from the 'Dropdown' list", "mode": "select", "search_texts": ["Option 1", "Dropdown"], "target_field": None, "expected": "trap_phantom_select"},
    {"name": "3", "step": "Click the 'Submit Login' button", "mode": "clickable", "search_texts": ["Submit Login"], "target_field": None, "expected": "trap_real_btn"},
    {"name": "4", "step": "Fill 'Cyber Password' field with 'secret'", "mode": "input", "search_texts": ["Cyber Password"], "target_field": "cyber password", "expected": "trap_shadow_input"},
    {"name": "5", "step": "Click the 'Close Window' button", "mode": "clickable", "search_texts": ["Close Window"], "target_field": None, "expected": "trap_aria_btn"},
    {"name": "6", "step": "Click the 'Save' button", "mode": "clickable", "search_texts": ["Save"], "target_field": None, "expected": "trap_btn_exact"},
    {"name": "7", "step": "Click the checkbox for 'Accept Terms'", "mode": "clickable", "search_texts": ["Accept Terms"], "target_field": None, "expected": "trap_opacity_chk"},
    {"name": "8", "step": "Fill 'Secret Token' field with '123'", "mode": "input", "search_texts": ["Secret Token"], "target_field": "secret token", "expected": "trap_placeholder_input"},
    {"name": "9", "step": "Click the radio button for 'No'", "mode": "clickable", "search_texts": ["No"], "target_field": None, "expected": "trap_radio_no"},
    {"name": "10", "step": "Click the checkbox for 'Remember Me'", "mode": "clickable", "search_texts": ["Remember Me"], "target_field": None, "expected": "trap_role_chk"},
    {"name": "11", "step": "Click the 'Confirm Order' button", "mode": "clickable", "search_texts": ["Confirm Order"], "target_field": None, "expected": "trap_qa_btn"},
    {"name": "12", "step": "Click the 'Register Portal' link", "mode": "clickable", "search_texts": ["Register Portal"], "target_field": None, "expected": "trap_link_login"},
    {"name": "13", "step": "Fill 'Email' field in the Login Form section with 'ghost@manul.ai'", "mode": "input", "search_texts": ["Email", "Login Form"], "target_field": "email", "expected": "trap_section_login"},
    {"name": "14", "step": "Click the search button", "mode": "clickable", "search_texts": [], "target_field": None, "expected": "trap_icon_search"},
    {"name": "15", "step": "Click the 'Submit' button", "mode": "clickable", "search_texts": ["Submit"], "target_field": None, "expected": "trap_enabled_btn"},
    {"name": "16", "step": "Fill 'Quantity' field with '5'", "mode": "input", "search_texts": ["Quantity"], "target_field": "quantity", "expected": "trap_qty_input"},
    {"name": "17", "step": "Click the checkbox for 'Newsletter'", "mode": "clickable", "search_texts": ["Newsletter"], "target_field": None, "expected": "trap_newsletter_chk"},
    {"name": "18", "step": "Click the 'Delete' button for the selected item", "mode": "clickable", "search_texts": ["Delete"], "target_field": None, "expected": "trap_delete_selected"},
    {"name": "19", "step": "Fill 'Promo Code' field with 'MANUL2025'", "mode": "input", "search_texts": ["Promo Code"], "target_field": "promo code", "expected": "trap_readonly_input"},
    {"name": "20", "step": "Click the 'Settings' button", "mode": "clickable", "search_texts": ["Settings"], "target_field": None, "expected": "trap_title_btn"},
    {"name": "21", "step": "Click the 'Download' button", "mode": "clickable", "search_texts": ["Download"], "target_field": None, "expected": "trap_download_btn"},
    {"name": "22", "step": "Fill the 'password' field with 'hunter2'", "mode": "input", "search_texts": ["password"], "target_field": "password", "expected": "trap_pw_pass"},
    {"name": "23", "step": "Fill 'Card Number' field with '4242 4242 4242 4242'", "mode": "input", "search_texts": ["Card Number"], "target_field": "card number", "expected": "trap_float_input"},
    {"name": "24", "step": "Select the checkbox for product 'Laptop'", "mode": "clickable", "search_texts": ["Laptop"], "target_field": None, "expected": "trap_chk_laptop"},

    # ── OPTIONAL TRAPS 25-28 ─────────────────────────────────────────────
    {"name": "25. Optional hidden", "step": "Click the 'Accept Cookies' button if exists", "mode": "clickable", "search_texts": ["Accept Cookies"], "target_field": None, "expected": None},
    {"name": "26. Optional 0x0", "step": "Click the 'Close Ad' button if exists", "mode": "clickable", "search_texts": ["Close Ad"], "target_field": None, "expected": None},
    {"name": "27. Decoy optional", "step": "Fill 'Promotion Code if exists' field with 'DISCOUNT'", "mode": "input", "search_texts": ["Promotion Code if exists"], "target_field": "promotion code if exists", "expected": "trap_promo_optional_input"},
    {"name": "28. Optional missing", "step": "Click the 'Dismiss Popup' button optional", "mode": "clickable", "search_texts": ["Dismiss Popup"], "target_field": None, "expected": None},

    # ── INTEGRATION BUGS 29-34 ──────────────────────────────────────────
    {"name": "29", "step": "Check the 'Agree to Terms' checkbox", "mode": "clickable", "search_texts": ["Agree to Terms"], "target_field": None, "expected": "trap_check_agree_chk"},
    {"name": "30", "step": "Uncheck the 'Auto-Renew' checkbox", "mode": "clickable", "search_texts": ["Auto-Renew"], "target_field": None, "expected": "trap_uncheck_renew_chk"},
    {"name": "31", "step": "Select 'Urgent' from the 'Priority' dropdown", "mode": "select", "search_texts": ["Urgent", "Priority"], "target_field": None, "expected": "trap_priority_select"},
    {"name": "32", "step": "Click the 'Banner Ad' button if exists", "mode": "clickable", "search_texts": ["Banner Ad"], "target_field": None, "expected": None},
    {"name": "33", "step": "Fill 'Shipping Address' field with '456 Oak Ave'", "mode": "input", "search_texts": ["Shipping Address"], "target_field": "shipping address", "expected": "trap_dqa_ship"},
    {"name": "34. JS Toggle", "step": "Check the 'Enable Notifications' checkbox", "mode": "clickable", "search_texts": ["Enable Notifications"], "target_field": None, "expected": "trap_jsclick_chk", "execute_step": True, "verify_checked": True},

    # ── DEMOQA/MEGA 35-46 ───────────────────────────────────────────────
    {"name": "35. Textarea", "step": "Fill 'Address' textarea with 'Selenium Avenue, 42'", "mode": "input", "search_texts": ["Address"], "target_field": "address", "expected": "trap_addr_textarea"},
    {"name": "36. Exact match", "step": "Click the 'Click Me' button", "mode": "clickable", "search_texts": ["Click Me"], "target_field": None, "expected": "trap_singleclick_btn"},
    {"name": "37. Date", "step": "Fill 'Start Date' field with '2026-01-01'", "mode": "input", "search_texts": ["Start Date"], "target_field": "start date", "expected": "trap_date_input"},
    {"name": "38. Search", "step": "Fill 'Search Articles' field with 'Pallas cat'", "mode": "input", "search_texts": ["Search Articles"], "target_field": "search articles", "expected": "trap_search_input"},
    {"name": "39. Paginator", "step": "Click on page '3' in the pagination list", "mode": "clickable", "search_texts": ["3"], "target_field": None, "expected": "trap_page_3"},
    {"name": "40. Days", "step": "Click the checkbox for 'Wednesday'", "mode": "clickable", "search_texts": ["Wednesday"], "target_field": None, "expected": "trap_day_wed"},
    {"name": "41. Select", "step": "Select 'Japan' from the 'Country' dropdown", "mode": "select", "search_texts": ["Japan", "Country"], "target_field": None, "expected": "trap_country_select"},
    {"name": "42. DblClick", "step": "DOUBLE CLICK the 'Double Click Me' button", "mode": "clickable", "search_texts": ["Double Click Me"], "target_field": None, "expected": "trap_dblclick_btn", "execute_step": True, "verify_attr": {"selector": "#trap_dblclick_btn", "attr": "data-clicked", "value": "double"}},
    {"name": "43. Hover", "step": "HOVER over the 'Mouse Hover' button", "mode": "hover", "search_texts": ["Mouse Hover"], "target_field": None, "expected": "trap_hover_btn", "execute_step": True, "verify_attr": {"selector": "#trap_hover_btn", "attr": "data-hovered", "value": "yes"}},
    {"name": "44. Select flow", "step": "Select 'Japan' from the 'Country' dropdown", "mode": "select", "search_texts": ["Japan", "Country"], "target_field": None, "expected": "trap_country_select", "execute_step": True, "verify_select": {"selector": "#trap_country_select", "value": "Japan"}},
    {"name": "45. Check", "step": "Check the 'Accept Marketing' checkbox", "mode": "clickable", "search_texts": ["Accept Marketing"], "target_field": None, "expected": "trap_toggle_chk", "execute_step": True, "verify_checked": True},
    {"name": "46. Uncheck", "step": "Click the checkbox for 'Accept Marketing'", "mode": "clickable", "search_texts": ["Accept Marketing"], "target_field": None, "expected": "trap_toggle_chk", "execute_step": True, "verify_checked": False},

    # ── NORMAL ELEMENTS 47-60 ────────────────────────────────────────────
    {"name": "47", "step": "Fill 'Full Name' field with 'Ghost Manul'", "mode": "input", "search_texts": ["Full Name"], "target_field": "full name", "expected": "norm_fullname", "execute_step": True, "verify_value": {"selector": "#norm_fullname", "value": "Ghost Manul"}},
    {"name": "48", "step": "Fill 'Work Email' field with 'ghost@manul.ai'", "mode": "input", "search_texts": ["Work Email"], "target_field": "work email", "expected": "norm_email", "execute_step": True, "verify_value": {"selector": "#norm_email", "value": "ghost@manul.ai"}},
    {"name": "49", "step": "Fill 'API Token' field with 'SuperSecret123'", "mode": "input", "search_texts": ["API Token"], "target_field": "api token", "expected": "norm_token", "execute_step": True, "verify_value": {"selector": "#norm_token", "value": "SuperSecret123"}},
    {"name": "50", "step": "Fill 'Comment' field with 'Great product, highly recommended'", "mode": "input", "search_texts": ["Comment"], "target_field": "comment", "expected": "norm_comment", "execute_step": True, "verify_value": {"selector": "#norm_comment", "value": "Great product, highly recommended"}},
    {"name": "51", "step": "Click the 'Send Message' button", "mode": "clickable", "search_texts": ["Send Message"], "target_field": None, "expected": "norm_submit_btn", "execute_step": True, "verify_attr": {"selector": "#norm_submit_btn", "attr": "data-done", "value": "yes"}},
    {"name": "52", "step": "Click the 'About Us' link", "mode": "clickable", "search_texts": ["About Us"], "target_field": None, "expected": "norm_about_link"},
    {"name": "53", "step": "Fill 'Coupon Code' field with 'MANUL2026'", "mode": "input", "search_texts": ["Coupon Code"], "target_field": "coupon code", "expected": "norm_readonly", "execute_step": True, "verify_value": {"selector": "#norm_readonly", "value": "MANUL2026"}},
    {"name": "54", "step": "Fill 'Username' field with 'admin' and press Enter", "mode": "input", "search_texts": ["Username"], "target_field": "username", "expected": "norm_login_user", "execute_step": True, "verify_attr": {"selector": "#norm_login_user", "attr": "data-submitted", "value": "yes"}},
    {"name": "55", "step": "Click the radio button for 'Female'", "mode": "clickable", "search_texts": ["Female"], "target_field": None, "expected": "norm_radio_female", "execute_step": True, "verify_checked": True},
    {"name": "56", "step": "Check the 'I Agree' checkbox", "mode": "clickable", "search_texts": ["I Agree"], "target_field": None, "expected": "norm_agree_chk", "execute_step": True, "verify_checked": True},
    {"name": "57. Verify checked", "verify_step": True, "step": "VERIFY that 'I Agree' is checked.", "expected_result": True},
    {"name": "58", "step": "Select 'Blue' from the 'Favorite Color' dropdown", "mode": "select", "search_texts": ["Blue", "Favorite Color"], "target_field": None, "expected": "norm_color_select", "execute_step": True, "verify_select": {"selector": "#norm_color_select", "value": "Blue"}},
    {"name": "59. Verify Texts", "verify_step": True, "step": "VERIFY that 'Operation completed successfully' is present.", "expected_result": True, "followup": {"step": "VERIFY that 'Critical failure' is NOT present.", "expected_result": True}},
    {"name": "60. Extract Table", "step": "EXTRACT the Price of 'Monitor' into {monitor_price}", "extract_step": True, "expected_var": "monitor_price", "expected_value": "$299"},

    # ── REAL WORLD ELEMENTS 61-80 ──────────────────────────────────────────
    {
        "name": "61. Tailwind Button",
        "desc": "Messy Tailwind utility classes on a standard button.",
        "step": "Click the 'Deploy Application' button",
        "mode": "clickable", "search_texts": ["Deploy Application"], "target_field": None,
        "expected": "rw_tw_btn",
    },
    {
        "name": "62. SVG Profile (ARIA)",
        "desc": "Button has no text, only an SVG icon and aria-label. Very common in modern navbars.",
        "step": "Click the 'User Profile' button",
        "mode": "clickable", "search_texts": ["User Profile"], "target_field": None,
        "expected": "rw_svg_profile",
    },
    {
        "name": "63. Screen Reader Only Text",
        "desc": "Text is visually hidden via CSS (sr-only), but engine should still find and associate it.",
        "step": "Click the 'View Notifications' button",
        "mode": "clickable", "search_texts": ["View Notifications"], "target_field": None,
        "expected": "rw_sr_bell",
    },
    {
        "name": "64. Custom Switch Role",
        "desc": "Div acting as a switch via role='switch'. Engine must recognize it as a valid toggle.",
        "step": "Click the 'Dark Mode' switch",
        "mode": "clickable", "search_texts": ["Dark Mode"], "target_field": None,
        "expected": "rw_custom_switch",
    },
    {
        "name": "65. ContentEditable Field",
        "desc": "Rich text editor div with contenteditable='true'. Must be detected as an input field.",
        "step": "Fill 'Message Body' field with 'Hello from Manul'",
        "mode": "input", "search_texts": ["Message Body"], "target_field": "message body",
        "expected": "rw_wysiwyg",
    },
    {
        "name": "66. Hidden File Upload Label",
        "desc": "Real input is hidden. User asks to click 'Upload Resume'. Should target the label.",
        "step": "Click the 'Upload Resume' button",
        "mode": "clickable", "search_texts": ["Upload Resume"], "target_field": None,
        "expected": "rw_file_label",
    },
    {
        "name": "67. Table Action by Test-ID",
        "desc": "Disambiguate a generic 'Edit' action inside a table using a specific data-testid.",
        "step": "Click the 'Edit Profile' button",
        "mode": "clickable", "search_texts": ["Edit Profile"], "target_field": None,
        "expected": "rw_edit_profile",
    },
    {
        "name": "68. E-commerce Card Data Extraction",
        "desc": "Extract specific data from a div-based layout (not a <table>), relying on text proximity.",
        "step": "EXTRACT the price of 'Gaming Mouse' into {mouse_price}",
        "extract_step": True, "expected_var": "mouse_price", "expected_value": "$59.99"
    },
    {
        "name": "69. Modal Close 'X'",
        "desc": "Common modal close button marked only with an 'X' symbol and aria-label.",
        "step": "Click the 'Close dialog' button",
        "mode": "clickable", "search_texts": ["Close dialog"], "target_field": None,
        "expected": "rw_modal_close",
    },
    {
        "name": "70. Hamburger Menu",
        "desc": "Mobile menu trigger. Text is a unicode symbol, meaning comes from aria.",
        "step": "Click the 'Open Navigation' menu",
        "mode": "clickable", "search_texts": ["Open Navigation"], "target_field": None,
        "expected": "rw_hamburger",
    },
    {
        "name": "71. Social Login Image Button",
        "desc": "Button containing both an image (logo) and text.",
        "step": "Click 'Continue with Google'",
        "mode": "clickable", "search_texts": ["Continue with Google"], "target_field": None,
        "expected": "rw_google_btn",
    },
    {
        "name": "72. Inline Link within Paragraph",
        "desc": "Find and click a specific link embedded deeply inside a paragraph of text.",
        "step": "Click the 'Terms of Service' link",
        "mode": "clickable", "search_texts": ["Terms of Service"], "target_field": None,
        "expected": "rw_terms_link",
    },
    {
        "name": "73. Wizard Next Step",
        "desc": "Button with an arrow symbol and compound text.",
        "step": "Click 'Next: Shipping Details'",
        "mode": "clickable", "search_texts": ["Next: Shipping Details"], "target_field": None,
        "expected": "rw_next_step",
    },
    {
        "name": "74. Div-based Radio Group (Star Rating)",
        "desc": "Clicking a specific star in a custom rating widget built with divs and roles.",
        "step": "Click the '5 stars' rating",
        "mode": "clickable", "search_texts": ["5 stars"], "target_field": None,
        "expected": "rw_star_5",
    },
    {
        "name": "75. Load More Banner",
        "desc": "Wide button standard for infinite scroll loading.",
        "step": "Click 'Load More Articles'",
        "mode": "clickable", "search_texts": ["Load More Articles"], "target_field": None,
        "expected": "rw_load_more",
    },
    {
        "name": "76. Verify Form Error",
        "desc": "Verify that a dynamic inline error message appears correctly.",
        "verify_step": True, "step": "VERIFY that 'Username is already taken.' is present.", "expected_result": True,
    },
    {
        "name": "77. Floating Action Button (FAB)",
        "desc": "Click a purely visual FAB that only relies on a title attribute.",
        "step": "Click the 'Create New Post' button",
        "mode": "clickable", "search_texts": ["Create New Post"], "target_field": None,
        "expected": "rw_fab_create",
    },
    {
        "name": "78. Multi-layered Span Button",
        "desc": "Button where the text is nested multiple levels deep in spans (React pattern).",
        "step": "Click the 'Submit Order' button",
        "mode": "clickable", "search_texts": ["Submit Order"], "target_field": None,
        "expected": "rw_complex_btn",
    },
    {
        "name": "79. Extract Cart Badge",
        "desc": "Extract a specific number from a cart widget badge.",
        "step": "EXTRACT the Cart count into {cart_count}",
        "extract_step": True, "expected_var": "cart_count", "expected_value": "3"
    },
    {
        "name": "80. Video Play Button",
        "desc": "Find a button based on aria-label where visible text is an emoji.",
        "step": "Click the 'Play Video' button",
        "mode": "clickable", "search_texts": ["Play Video"], "target_field": None,
        "expected": "rw_play_btn",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Guard logic (mirrors _execute_step guards in engine.py)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_guards(el: dict, mode: str, search_texts: list[str]) -> str | None:
    if el is None: return None
    tag   = el.get("tag_name", "")
    itype = el.get("input_type", "")
    role  = el.get("role", "")
    name  = el.get("name", "")

    if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
        return f"cannot type into {itype}"

    if mode == "select":
        valid = (tag == "select" or role in ("option", "menuitem") or "item" in name.lower() or "dropdown" in name.lower())
        if not valid: return f"not a SELECT (tag={tag})"

    return None

# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────
async def run_laboratory():
    print("\n" + "=" * 70)
    print("🧪  MANUL ENGINE LABORATORY — The Chaos Chamber (80 tests)")
    print("=" * 70)

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.set_content(MONSTER_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🧬 {t['name']}")
            if t.get('desc'): print(f"   📋 {t['desc']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

            if t.get("extract_step"):
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
                result = await manul._handle_verify(page, t["step"])
                if result == t["expected_result"]:
                    print(f"   ✅ PASSED  → VERIFY returned {result}")
                    passed += 1
                else:
                    msg = f"FAILED — VERIFY returned {result}, expected {t['expected_result']}"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['name']}: {msg}")
                if t.get("followup") and result == t["expected_result"]:
                    fu = t["followup"]
                    fu_result = await manul._handle_verify(page, fu["step"])
                    if fu_result == fu["expected_result"]:
                        print(f"   ✅ FOLLOWUP  → VERIFY NOT returned {fu_result}")
                    else:
                        print(f"   ❌ FOLLOWUP FAILED")

            elif t.get("execute_step"):
                result = await manul._execute_step(page, t["step"], "")
                if not result:
                    print("   ❌ FAILED — _execute_step returned False")
                    failed += 1
                    failures.append(f"{t['name']}: execute_step failed")
                else:
                    verify_ok = True; verify_detail = ""
                    if t.get("verify_checked") is not None:
                        actual = await page.locator(f"#{t['expected']}").is_checked()
                        if actual != t["verify_checked"]: verify_ok = False
                        verify_detail = f"checked={actual}"
                    elif t.get("verify_attr"):
                        va = t["verify_attr"]
                        actual = await page.locator(va["selector"]).get_attribute(va["attr"])
                        if actual != va["value"]: verify_ok = False
                        verify_detail = f"{va['attr']}='{actual}'"
                    elif t.get("verify_select"):
                        vs = t["verify_select"]
                        actual = await page.locator(vs["selector"]).evaluate("sel => sel.options[sel.selectedIndex].text.trim()")
                        if actual != vs["value"]: verify_ok = False
                        verify_detail = f"selected='{actual}'"
                    elif t.get("verify_value"):
                        vv = t["verify_value"]
                        actual = await page.locator(vv["selector"]).input_value()
                        if actual != vv["value"]: verify_ok = False
                        verify_detail = f"value='{actual}'"

                    if verify_ok:
                        print(f"   ✅ PASSED  → '{t['expected']}' {verify_detail}")
                        passed += 1
                    else:
                        print(f"   ❌ FAILED — validation failed {verify_detail}")
                        failed += 1
                        failures.append(t['name'])

            elif "if exists" in t["step"].lower() or "optional" in t["step"].lower():
                result = await manul._execute_step(page, t["step"], "")
                if t["expected"] is None:
                    if result is True:
                        print("   ✅ PASSED  → Optional skipped")
                        passed += 1
                    else:
                        print("   ❌ FAILED")
                        failed += 1
                        failures.append(t['name'])
                else:
                    el = await manul._resolve_element(page, t["step"], t["mode"], t["search_texts"], t["target_field"], "", set())
                    found_id = el.get("html_id", "") if el else None
                    if found_id == t["expected"]:
                         print(f"   ✅ PASSED  → '{found_id}' (Decoy bypass)")
                         passed += 1
                    else:
                         print(f"   ❌ FAILED")
                         failed += 1
                         failures.append(t['name'])
            else:
                el = await manul._resolve_element(page, t["step"], t["mode"], t["search_texts"], t["target_field"], "", set())
                if el is None:
                    print("   ❌ FAILED — None")
                    failed += 1; failures.append(t['name']); continue
                rej = _apply_guards(el, t["mode"], t["search_texts"])
                if rej:
                    print(f"   ❌ FAILED — rejected: {rej}")
                    failed += 1; failures.append(t['name']); continue
                
                found_id = el.get("html_id", "")
                if found_id == t["expected"]:
                    print(f"   ✅ PASSED  → '{found_id}'")
                    passed += 1
                else:
                    print(f"   ❌ FAILED — got '{found_id}', expected '{t['expected']}'")
                    failed += 1
                    failures.append(t['name'])

        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {passed}/{len(TESTS)} passed")
        if failures: print("\n🙀 Failures:"); [print(f"   • {f}") for f in failures]
        if passed == len(TESTS): print("\n🏆 FLAWLESS VICTORY! The Manul engine is unbreakable!")
        print("=" * 70)
        await browser.close()

    return passed == len(TESTS)

if __name__ == "__main__":
    asyncio.run(run_laboratory())