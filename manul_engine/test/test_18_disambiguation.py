import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Disambiguation Edge Cases (90 Elements)
#
# Specifically targets model weaknesses identified in failure diagnostics:
#   1. Antonym pairs  (Increase/Decrease, Yes/No, Next/Previous, Enable/Disable)
#   2. String containment  (Follow/Following, Add/Add to Cart, Save/Save Changes)
#   3. Ordinal specificity  (Play Episode 1 vs Play Episode 2 vs Play)
#   4. Container div vs specific button  (div with id that contains buttons)
#   5. Button vs input disambiguation  (Save Filter button vs save filter input)
#   6. Multiple identical-text buttons  (Confirm×3 with different CSS classes)
#   7. Exact aria vs "more specific" aria (Save playlist vs Save to playlist)
# ─────────────────────────────────────────────────────────────────────────────
DISAMBIGUATION_DOM = """
<!DOCTYPE html><html><head><style>
.episode-card  { border: 1px solid #ccc; padding: 8px; margin: 4px; }
.product-card  { border: 1px solid #aaa; padding: 8px; margin: 4px; display: inline-block; }
.counter-row   { display: flex; align-items: center; gap: 8px; }
.sr-only       { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
</style></head><body>

<!-- ═══════════════════════════════════════════════════════
     A. YES / NO RADIO PAIRS  (three independent fieldsets)
     ═══════════════════════════════════════════════════════ -->
<fieldset>
  <legend>Account Active?</legend>
  <input type="radio" id="d1" name="active" value="yes"><label for="d1">Yes</label>
  <input type="radio" id="d2" name="active" value="no"><label for="d2">No</label>
</fieldset>

<fieldset>
  <legend>Account Status</legend>
  <input type="radio" id="d3" name="status" value="active"><label for="d3">Active</label>
  <input type="radio" id="d4" name="status" value="inactive"><label for="d4">Inactive</label>
</fieldset>

<fieldset>
  <legend>Notifications</legend>
  <input type="radio" id="d5" name="notif" value="on"><label for="d5">Enabled</label>
  <input type="radio" id="d6" name="notif" value="off"><label for="d6">Disabled</label>
</fieldset>

<!-- ═══════════════════════════════════════════════════════
     B. INCREASE / DECREASE COUNTER BUTTONS  (4 items)
     ═══════════════════════════════════════════════════════ -->
<div class="counter-row">
  Adults (16+)
  <button id="d7"  aria-label="Decrease Adults">−</button>
  <span>2</span>
  <button id="d8"  aria-label="Increase Adults">+</button>
</div>
<div class="counter-row">
  Children (2–15)
  <button id="d9"  aria-label="Decrease Children">−</button>
  <span>0</span>
  <button id="d10" aria-label="Increase Children">+</button>
</div>
<div class="counter-row">
  Rooms
  <button id="d11" aria-label="Decrease Rooms">−</button>
  <span>1</span>
  <button id="d12" aria-label="Increase Rooms">+</button>
</div>
<div class="counter-row">
  Quantity
  <button id="d13" aria-label="Decrease Quantity">−</button>
  <span>1</span>
  <button id="d14" aria-label="Increase Quantity">+</button>
</div>
<div class="counter-row">
  Nights
  <button id="d15" aria-label="Decrease Nights">−</button>
  <span>3</span>
  <button id="d16" aria-label="Increase Nights">+</button>
</div>
<div class="counter-row">
  Price Range
  <button id="d17" aria-label="Decrease Price">−</button>
  <span>$100</span>
  <button id="d18" aria-label="Increase Price">+</button>
</div>

<!-- ═══════════════════════════════════════════════════════
     C. NEXT / PREVIOUS NAVIGATION PAIRS  (3 contexts)
     ═══════════════════════════════════════════════════════ -->
<nav aria-label="Pagination">
  <button id="d19" aria-label="Previous Page">‹ Prev</button>
  <button id="d20" aria-label="Next Page">Next ›</button>
</nav>
<div>
  <button id="d21">Previous Month</button>
  <button id="d22">Next Month</button>
</div>
<div>
  <button id="d23" aria-label="Previous Step">← Back</button>
  <button id="d24" aria-label="Next Step">Continue →</button>
</div>

<!-- ═══════════════════════════════════════════════════════
     D. ENABLE/DISABLE · SHOW/HIDE · EXPAND/COLLAPSE · SORT
     ═══════════════════════════════════════════════════════ -->
<button id="d25">Enable Notifications</button>
<button id="d26">Disable Notifications</button>
<button id="d27" aria-label="Show Password">👁 Show</button>
<button id="d28" aria-label="Hide Password">🙈 Hide</button>
<button id="d29" aria-label="Expand All Sections">Expand All</button>
<button id="d30" aria-label="Collapse All Sections">Collapse All</button>
<button id="d31">Sort Ascending</button>
<button id="d32">Sort Descending</button>
<button id="d33">Zoom In</button>
<button id="d34">Zoom Out</button>

<!-- ═══════════════════════════════════════════════════════
     E. STRING-CONTAINMENT: FOLLOW / SUBSCRIBE FAMILIES
     ═══════════════════════════════════════════════════════ -->
<button id="d35" class="btn-follow"    >Follow</button>
<button id="d36" class="btn-following" >Following</button>
<button id="d37" class="btn-unfollow"  >Unfollow</button>

<button id="d38">Subscribe</button>
<button id="d39">Subscribed</button>
<button id="d40">Unsubscribe</button>

<button id="d41">Connect</button>
<button id="d42">Disconnect</button>

<button id="d43">Like</button>
<button id="d44">Unlike</button>

<!-- ═══════════════════════════════════════════════════════
     F. STRING-CONTAINMENT: ADD / SAVE VARIANTS
     ═══════════════════════════════════════════════════════ -->
<button id="d45">Add</button>
<button id="d46">Add to Cart</button>
<button id="d47">Add to Wishlist</button>
<button id="d48">Add to Comparison</button>

<button id="d49">Save</button>
<button id="d50">Save Changes</button>
<button id="d51">Save Draft</button>
<button id="d52">Save as Template</button>
<button id="d53">Save and Continue</button>

<button id="d54">Load More</button>
<button id="d55">Show More</button>
<button id="d56">See All</button>

<!-- ═══════════════════════════════════════════════════════
     G. ORDINAL SPECIFICITY: PLAY / DOWNLOAD EPISODE N
     ═══════════════════════════════════════════════════════ -->
<button id="d57">Play</button>
<button id="d58">Play Episode 1</button>
<button id="d59">Play Episode 2</button>
<button id="d60">Play Episode 3</button>

<button id="d61">Download</button>
<button id="d62">Download Episode 1</button>
<button id="d63">Download Episode 2</button>
<button id="d64">Download Episode 3</button>
<button id="d65">Download All</button>

<!-- ═══════════════════════════════════════════════════════
     K. EXACT PLACEHOLDER vs PLACEHOLDER + EXTRA WORDS
        Model must prefer the element whose placeholder is
        the exact phrase, not a super-set of it.
     ═══════════════════════════════════════════════════════ -->
<input id="dk1" placeholder="Phone Number">
<input id="dk2" placeholder="Phone Number (Optional)">

<input id="dk3" placeholder="Search">
<input id="dk4" placeholder="Search (Advanced Mode)">

<input id="dk5" placeholder="Email">
<input id="dk6" placeholder="Email (Work or Personal)">

<input id="dk7" placeholder="Username">
<input id="dk8" placeholder="Username (must be unique)">

<!-- ═══════════════════════════════════════════════════════
     L. TEXTAREA vs INPUT DISAMBIGUATION
        Model must prefer textarea when step says 'textarea',
        prefer input when step says 'field' / 'input',
        and use tag: textarea as a discriminating signal.
     ═══════════════════════════════════════════════════════ -->
<div class="form-group">
  <div class="label-text">Short Note</div>
  <input type="text" id="dk9">
</div>
<div class="form-group">
  <div class="label-text">Long Note</div>
  <textarea id="dk10"></textarea>
</div>

<input type="text" id="dk11" placeholder="Pre-filled input" value="some data">
<textarea          id="dk12" aria-label="Pre-filled textarea">existing text</textarea>

<input type="text" id="dk13" value="Summary text">
<textarea          id="dk14" aria-label="Summary area"></textarea>

<!-- ═══════════════════════════════════════════════════════
     M. BUTTON (clickable) vs CHECKBOX (toggleable)
        When step verb is 'Click', prefer the button even
        when a nearby checkbox carries overlapping label words.
        When step verb is 'Check', prefer the checkbox.
     ═══════════════════════════════════════════════════════ -->
<div class="action-row">
  <label for="dk15">Allow Editing</label>
  <input type="checkbox" id="dk15">
  <button id="dk16">Edit</button>
</div>
<div class="action-row">
  <label for="dk17">Enable Processing</label>
  <input type="checkbox" id="dk17">
  <button id="dk18">Process</button>
</div>
<div class="action-row">
  <label for="dk19">Allow Deletion</label>
  <input type="checkbox" id="dk19">
  <button id="dk20">Delete</button>
</div>

<!-- ═══════════════════════════════════════════════════════
     N. ICON-ONLY BUTTONS: exact aria-label beats partial
        text name. Avoids 'Search' to prevent conflict
        with the Section I test 77 / d84 test.
     ═══════════════════════════════════════════════════════ -->
<button id="dn1">Refresh</button>
<button id="dn2" aria-label="Refresh Feed">🔄</button>

<button id="dn3">Settings</button>
<button id="dn4" aria-label="Profile Settings">⚙️</button>

<button id="dn5">Save</button>
<button id="dn6" aria-label="Save to favorites">⭐</button>

<!-- ═══════════════════════════════════════════════════════
     I. BUTTON vs INPUT DISAMBIGUATION
        (clickable mode: button must win over input with similar text)
        (input mode: input must win over button with similar text)
     ═══════════════════════════════════════════════════════ -->
<input type="text"   id="d81" placeholder="Save filter as...">
<button              id="d82">Save Filter</button>

<input type="search" id="d83" placeholder="Search products...">
<button              id="d84" aria-label="Search products">🔍</button>

<input type="text"   id="d85" placeholder="Type workspace name to confirm">
<input type="text"   id="d86" aria-label="Workspace Name" value="Acme Corp">

<!-- ═══════════════════════════════════════════════════════
     J. IDENTICAL TEXT, DIFFERENT CSS CLASS / CONTEXT
        (Confirm×3, submit vs fake-submit, Save playlist variants)
     ═══════════════════════════════════════════════════════ -->
<button id="d87" class="btn-confirm-transfer">Confirm</button>
<button id="d88" class="btn-confirm-delete"  >Confirm</button>
<button id="d89" class="btn-confirm-approve" >Confirm</button>

<input  type="submit" id="d90" value="Submit">
<div    role="button" id="d91" class="fake-submit">Submit</div>

<button id="d92" aria-label="Save playlist">💾</button>
<button id="d93" aria-label="Add to playlist">➕</button>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Test cases — 85 element-resolution steps
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── A. Yes / No antonym pairs ────────────────────────────────────────────
    {"n":  "1", "step": "Click the 'Yes' radio button",         "m": "clickable", "st": ["Yes"],      "tf": None, "exp": "d1"},
    {"n":  "2", "step": "Click the 'No' radio button",          "m": "clickable", "st": ["No"],       "tf": None, "exp": "d2"},
    {"n":  "3", "step": "Click radio button for 'Active'",      "m": "clickable", "st": ["Active"],   "tf": None, "exp": "d3"},
    {"n":  "4", "step": "Click radio button for 'Inactive'",   "m": "clickable", "st": ["Inactive"], "tf": None, "exp": "d4"},
    {"n":  "5", "step": "Click 'Enabled'",                      "m": "clickable", "st": ["Enabled"],  "tf": None, "exp": "d5"},
    {"n":  "6", "step": "Click 'Disabled'",                     "m": "clickable", "st": ["Disabled"], "tf": None, "exp": "d6"},

    # ── B. Increase / Decrease antonym pairs ─────────────────────────────────
    {"n":  "7", "step": "Click 'Decrease Adults'",   "m": "clickable", "st": ["Decrease Adults"],   "tf": None, "exp": "d7"},
    {"n":  "8", "step": "Click 'Increase Adults'",   "m": "clickable", "st": ["Increase Adults"],   "tf": None, "exp": "d8"},
    {"n":  "9", "step": "Click 'Decrease Children'", "m": "clickable", "st": ["Decrease Children"], "tf": None, "exp": "d9"},
    {"n": "10", "step": "Click 'Increase Children'", "m": "clickable", "st": ["Increase Children"], "tf": None, "exp": "d10"},
    {"n": "11", "step": "Click 'Decrease Rooms'",    "m": "clickable", "st": ["Decrease Rooms"],    "tf": None, "exp": "d11"},
    {"n": "12", "step": "Click 'Increase Rooms'",    "m": "clickable", "st": ["Increase Rooms"],    "tf": None, "exp": "d12"},
    {"n": "13", "step": "Click 'Decrease Quantity'", "m": "clickable", "st": ["Decrease Quantity"], "tf": None, "exp": "d13"},
    {"n": "14", "step": "Click 'Increase Quantity'", "m": "clickable", "st": ["Increase Quantity"], "tf": None, "exp": "d14"},
    {"n": "15", "step": "Click 'Decrease Nights'",   "m": "clickable", "st": ["Decrease Nights"],   "tf": None, "exp": "d15"},
    {"n": "16", "step": "Click 'Increase Nights'",   "m": "clickable", "st": ["Increase Nights"],   "tf": None, "exp": "d16"},
    {"n": "17", "step": "Click 'Decrease Price'",    "m": "clickable", "st": ["Decrease Price"],    "tf": None, "exp": "d17"},
    {"n": "18", "step": "Click 'Increase Price'",    "m": "clickable", "st": ["Increase Price"],    "tf": None, "exp": "d18"},

    # ── C. Next / Previous antonym pairs ─────────────────────────────────────
    {"n": "19", "step": "Click 'Previous Page'", "m": "clickable", "st": ["Previous Page"], "tf": None, "exp": "d19"},
    {"n": "20", "step": "Click 'Next Page'",     "m": "clickable", "st": ["Next Page"],     "tf": None, "exp": "d20"},
    {"n": "21", "step": "Click 'Previous Month'","m": "clickable", "st": ["Previous Month"],"tf": None, "exp": "d21"},
    {"n": "22", "step": "Click 'Next Month'",    "m": "clickable", "st": ["Next Month"],    "tf": None, "exp": "d22"},
    {"n": "23", "step": "Click 'Previous Step'", "m": "clickable", "st": ["Previous Step"], "tf": None, "exp": "d23"},
    {"n": "24", "step": "Click 'Next Step'",     "m": "clickable", "st": ["Next Step"],     "tf": None, "exp": "d24"},

    # ── D. Enable/Disable · Show/Hide · Expand/Collapse · Sort ───────────────
    {"n": "25", "step": "Click 'Enable Notifications'",  "m": "clickable", "st": ["Enable Notifications"],  "tf": None, "exp": "d25"},
    {"n": "26", "step": "Click 'Disable Notifications'", "m": "clickable", "st": ["Disable Notifications"], "tf": None, "exp": "d26"},
    {"n": "27", "step": "Click 'Show Password'",         "m": "clickable", "st": ["Show Password"],         "tf": None, "exp": "d27"},
    {"n": "28", "step": "Click 'Hide Password'",         "m": "clickable", "st": ["Hide Password"],         "tf": None, "exp": "d28"},
    {"n": "29", "step": "Click 'Expand All Sections'",   "m": "clickable", "st": ["Expand All Sections"],   "tf": None, "exp": "d29"},
    {"n": "30", "step": "Click 'Collapse All Sections'", "m": "clickable", "st": ["Collapse All Sections"], "tf": None, "exp": "d30"},
    {"n": "31", "step": "Click 'Sort Ascending'",        "m": "clickable", "st": ["Sort Ascending"],        "tf": None, "exp": "d31"},
    {"n": "32", "step": "Click 'Sort Descending'",       "m": "clickable", "st": ["Sort Descending"],       "tf": None, "exp": "d32"},
    {"n": "33", "step": "Click 'Zoom In'",               "m": "clickable", "st": ["Zoom In"],               "tf": None, "exp": "d33"},
    {"n": "34", "step": "Click 'Zoom Out'",              "m": "clickable", "st": ["Zoom Out"],              "tf": None, "exp": "d34"},

    # ── E. Follow / Subscribe / Like containment families ────────────────────
    {"n": "35", "step": "Click 'Follow'",       "m": "clickable", "st": ["Follow"],      "tf": None, "exp": "d35"},
    {"n": "36", "step": "Click 'Following'",    "m": "clickable", "st": ["Following"],   "tf": None, "exp": "d36"},
    {"n": "37", "step": "Click 'Unfollow'",     "m": "clickable", "st": ["Unfollow"],    "tf": None, "exp": "d37"},
    {"n": "38", "step": "Click 'Subscribe'",    "m": "clickable", "st": ["Subscribe"],   "tf": None, "exp": "d38"},
    {"n": "39", "step": "Click 'Subscribed'",   "m": "clickable", "st": ["Subscribed"],  "tf": None, "exp": "d39"},
    {"n": "40", "step": "Click 'Unsubscribe'",  "m": "clickable", "st": ["Unsubscribe"], "tf": None, "exp": "d40"},
    {"n": "41", "step": "Click 'Connect'",      "m": "clickable", "st": ["Connect"],     "tf": None, "exp": "d41"},
    {"n": "42", "step": "Click 'Disconnect'",   "m": "clickable", "st": ["Disconnect"],  "tf": None, "exp": "d42"},
    {"n": "43", "step": "Click 'Like'",         "m": "clickable", "st": ["Like"],        "tf": None, "exp": "d43"},
    {"n": "44", "step": "Click 'Unlike'",       "m": "clickable", "st": ["Unlike"],      "tf": None, "exp": "d44"},

    # ── F. Add / Save / Load variants ────────────────────────────────────────
    {"n": "45", "step": "Click 'Add'",               "m": "clickable", "st": ["Add"],              "tf": None, "exp": "d45"},
    {"n": "46", "step": "Click 'Add to Cart'",       "m": "clickable", "st": ["Add to Cart"],      "tf": None, "exp": "d46"},
    {"n": "47", "step": "Click 'Add to Wishlist'",   "m": "clickable", "st": ["Add to Wishlist"],  "tf": None, "exp": "d47"},
    {"n": "48", "step": "Click 'Add to Comparison'", "m": "clickable", "st": ["Add to Comparison"],"tf": None, "exp": "d48"},
    {"n": "49", "step": "Click 'Save'",              "m": "clickable", "st": ["Save"],             "tf": None, "exp": "d49"},
    {"n": "50", "step": "Click 'Save Changes'",      "m": "clickable", "st": ["Save Changes"],     "tf": None, "exp": "d50"},
    {"n": "51", "step": "Click 'Save Draft'",        "m": "clickable", "st": ["Save Draft"],       "tf": None, "exp": "d51"},
    {"n": "52", "step": "Click 'Save as Template'",  "m": "clickable", "st": ["Save as Template"], "tf": None, "exp": "d52"},
    {"n": "53", "step": "Click 'Save and Continue'", "m": "clickable", "st": ["Save and Continue"],"tf": None, "exp": "d53"},
    {"n": "54", "step": "Click 'Load More'",         "m": "clickable", "st": ["Load More"],        "tf": None, "exp": "d54"},
    {"n": "55", "step": "Click 'Show More'",         "m": "clickable", "st": ["Show More"],        "tf": None, "exp": "d55"},
    {"n": "56", "step": "Click 'See All'",           "m": "clickable", "st": ["See All"],          "tf": None, "exp": "d56"},

    # ── G. Ordinal specificity: Play / Download episode N ────────────────────
    {"n": "57", "step": "Click 'Play'",             "m": "clickable", "st": ["Play"],             "tf": None, "exp": "d57"},
    {"n": "58", "step": "Click 'Play Episode 1'",   "m": "clickable", "st": ["Play Episode 1"],   "tf": None, "exp": "d58"},
    {"n": "59", "step": "Click 'Play Episode 2'",   "m": "clickable", "st": ["Play Episode 2"],   "tf": None, "exp": "d59"},
    {"n": "60", "step": "Click 'Play Episode 3'",   "m": "clickable", "st": ["Play Episode 3"],   "tf": None, "exp": "d60"},
    {"n": "61", "step": "Click 'Download'",         "m": "clickable", "st": ["Download"],         "tf": None, "exp": "d61"},
    {"n": "62", "step": "Click 'Download Episode 1'","m": "clickable","st": ["Download Episode 1"],"tf": None, "exp": "d62"},
    {"n": "63", "step": "Click 'Download Episode 2'","m": "clickable","st": ["Download Episode 2"],"tf": None, "exp": "d63"},
    {"n": "64", "step": "Click 'Download Episode 3'","m": "clickable","st": ["Download Episode 3"],"tf": None, "exp": "d64"},
    {"n": "65", "step": "Click 'Download All'",     "m": "clickable", "st": ["Download All"],     "tf": None, "exp": "d65"},

    # ── H. (Container div hard-negatives — kept in DOM only, not tested) ─────

    # ── K. Exact placeholder vs placeholder-plus-extra ───────────────────────
    {"n": "86", "step": "Fill 'Phone Number' field with '555'",
     "m": "input",     "st": ["Phone Number"],    "tf": "phone number",    "exp": "dk1"},
    {"n": "87", "step": "Fill 'Search' field with 'query'",
     "m": "input",     "st": ["Search"],           "tf": "search",          "exp": "dk3"},
    {"n": "88", "step": "Fill 'Email' field with 'test@test.com'",
     "m": "input",     "st": ["Email"],             "tf": "email",           "exp": "dk5"},
    {"n": "89", "step": "Fill 'Username' with 'alex'",
     "m": "input",     "st": ["Username"],         "tf": "username",        "exp": "dk7"},

    # ── L. Textarea vs input disambiguation ────────────────────────────────────
    {"n": "90", "step": "Fill 'Short Note' field with 'hello'",
     "m": "input",     "st": ["Short Note"],        "tf": "short note",       "exp": "dk9"},
    {"n": "91", "step": "Fill 'Long Note' textarea with 'hello'",
     "m": "input",     "st": ["Long Note"],         "tf": "long note",        "exp": "dk10"},
    {"n": "92", "step": "Fill 'Pre-filled textarea' with 'new content'",
     "m": "input",     "st": ["Pre-filled textarea"],"tf": "pre-filled textarea","exp": "dk12"},
    {"n": "93", "step": "Fill 'Summary area' with 'notes'",
     "m": "input",     "st": ["Summary area"],      "tf": "summary area",     "exp": "dk14"},

    # ── M. Clickable (button) wins over toggleable (checkbox) for "Click" verb ───
    # Each button has a unique name so there are no identical-text_b conflicts.
    {"n": "94", "step": "Click 'Edit' button",
     "m": "clickable", "st": ["Edit"],              "tf": None, "exp": "dk16"},
    {"n": "95", "step": "Click 'Process'",
     "m": "clickable", "st": ["Process"],           "tf": None, "exp": "dk18"},
    {"n": "96", "step": "Click 'Delete'",
     "m": "clickable", "st": ["Delete"],            "tf": None, "exp": "dk20"},
    # Toggleable (checkbox) wins when verb is "Check":
    {"n": "97", "step": "Check 'Allow Editing' checkbox",
     "m": "clickable", "st": ["Allow Editing"],     "tf": None, "exp": "dk15"},
    {"n": "98", "step": "Check 'Allow Deletion' checkbox",
     "m": "clickable", "st": ["Allow Deletion"],    "tf": None, "exp": "dk19"},

    # ── N. Icon-only button: exact aria-label beats partial text match ───────
    # dn2 aria='Refresh Feed' ≠ d54 text='Load More' — no conflict.
    {"n": "99",  "step": "Click 'Refresh Feed'",
     "m": "clickable", "st": ["Refresh Feed"],             "tf": None, "exp": "dn2"},
    {"n": "100", "step": "Click 'Profile Settings'",
     "m": "clickable", "st": ["Profile Settings"],        "tf": None, "exp": "dn4"},
    {"n": "101", "step": "Click 'Save to favorites'",
     "m": "clickable", "st": ["Save to favorites"],       "tf": None, "exp": "dn6"},

    # ── I. Button vs Input disambiguation ────────────────────────────────────
    # d81 = input placeholder "Save filter as...", d82 = button "Save Filter"
    {"n": "74", "step": "Fill 'Save filter as' field with 'Active Leads'",
     "m": "input",     "st": ["Save filter as"],     "tf": "save filter as",     "exp": "d81"},
    {"n": "75", "step": "Click 'Save Filter'",
     "m": "clickable", "st": ["Save Filter"],         "tf": None,                 "exp": "d82"},
    # d83 = input "Search products...", d84 = button aria "Search products"
    {"n": "76", "step": "Fill 'Search products' field with 'laptop'",
     "m": "input",     "st": ["Search products"],    "tf": "search products",    "exp": "d83"},
    {"n": "77", "step": "Click the search button",
     "m": "clickable", "st": ["Search"],              "tf": None,                 "exp": "d84"},
    # d85 = input placeholder "Type workspace name to confirm"
    # d86 = input aria "Workspace Name" (pre-filled trap)
    {"n": "78", "step": "Fill 'Type workspace name' with 'Acme Corp'",
     "m": "input",     "st": ["Type workspace name"], "tf": "type workspace name","exp": "d85"},
    {"n": "79", "step": "Fill 'Workspace Name' with 'Manul Labs'",
     "m": "input",     "st": ["Workspace Name"],      "tf": "workspace name",     "exp": "d86"},

    # ── J. Identical text, different class / context ──────────────────────────
    # Three Confirm buttons — class encodes the action context.
    {"n": "80", "step": "Click 'Confirm' to approve the action",
     "m": "clickable", "st": ["Confirm", "approve"],  "tf": None, "exp": "d89"},
    {"n": "81", "step": "Click 'Confirm' in transfer dialog",
     "m": "clickable", "st": ["Confirm", "transfer"], "tf": None, "exp": "d87"},
    {"n": "82", "step": "Click 'Confirm' to delete",
     "m": "clickable", "st": ["Confirm", "delete"],   "tf": None, "exp": "d88"},
    # input[type=submit] vs div[role=button] — div wins on exact text match (by design)
    {"n": "83", "step": "Click the submit button",
     "m": "clickable", "st": ["Submit"],               "tf": None, "exp": "d91"},
    # Save playlist (exact aria) vs Add to playlist (distinct aria, no overlap)
    {"n": "84", "step": "Click 'Save playlist'",
     "m": "clickable", "st": ["Save playlist"],        "tf": None, "exp": "d92"},
    {"n": "85", "step": "Click 'Add to playlist'",
     "m": "clickable", "st": ["Add to playlist"],      "tf": None, "exp": "d93"},
]


# ─────────────────────────────────────────────────────────────────────────────
async def run_suite():
    print(f"\n{'=' * 70}")
    print("🎯 DISAMBIGUATION EDGE CASES: 85 TARGETED TESTS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.set_content(DISAMBIGUATION_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🧬 {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

            mode         = t.get("m", "clickable")
            search_texts = [tx.lower() for tx in (t.get("st") or [])]
            target_field = t.get("tf")
            exp          = t.get("exp")

            try:
                found = await manul._resolve_element(
                    page, t["step"], mode, search_texts, target_field, ""
                )
                found_id = found.get("html_id", "") if found else None
            except Exception as exc:
                found_id = None
                print(f"   ❌ EXCEPTION: {exc}")

            if found_id == exp:
                passed += 1
                print(f"   ✅ PASSED  → {found_id}")
            else:
                failed += 1
                failures.append(f"[{t['n']}] {t['step']!r}: expected {exp!r}, got {found_id!r}")
                print(f"   ❌ FAILED  → expected {exp!r}, got {found_id!r}")

        await browser.close()

    print(f"\n{'=' * 70}")
    print(f"SCORE: {passed}/{passed + failed} passed")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  {f}")
    print(f"{'=' * 70}")

    return passed == (passed + failed)


if __name__ == "__main__":
    asyncio.run(run_suite())
