import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: IFRAME ROUTING — Cross-Frame Element Resolution (20 Tests)
#
# Tests that _snapshot() iterates page.frames, tags elements with frame_index,
# and _frame_for() routes actions to the correct Playwright Frame.
# ─────────────────────────────────────────────────────────────────────────────
IFRAME_DOM = """
<!DOCTYPE html><html><head><title>iFrame Routing Lab</title></head><body>

<!-- Main frame elements -->
<button id="main_submit">Submit Order</button>
<input  id="main_email" placeholder="Email Address" type="text">
<a      id="main_help" href="/help">Help Center</a>
<select id="main_lang"><option>English</option><option>French</option></select>
<input  id="main_search" type="text" aria-label="Search Products">
<button id="main_logout" aria-label="Logout">🚪</button>

<!-- Same-origin iframe: login form -->
<iframe id="frame_login" srcdoc='
    <button id="iframe_login_btn">Login</button>
    <input  id="iframe_user" placeholder="Username" type="text">
    <input  id="iframe_pass" placeholder="Password" type="password">
    <input  id="iframe_remember" type="checkbox"> <label for="iframe_remember">Remember Me</label>
    <a      id="iframe_forgot" href="/forgot">Forgot Password?</a>
    <button id="iframe_signup" data-qa="signup-button">Sign Up Free</button>
'></iframe>

<!-- Same-origin iframe: embedded widget -->
<iframe id="frame_widget" srcdoc='
    <button id="widget_save" aria-label="Save Changes">💾 Save</button>
    <input  id="widget_note" placeholder="Add a note" type="text">
    <select id="widget_priority">
        <option>Low</option>
        <option>Medium</option>
        <option>High</option>
    </select>
    <button id="widget_cancel">Cancel</button>
    <input  id="widget_tag" type="text" data-qa="tag-input" placeholder="Tag">
    <div role="checkbox" id="widget_urgent" aria-label="Mark as Urgent" tabindex="0">☐</div>
    <button id="widget_delete" title="Delete Item">🗑️</button>
    <input  id="widget_due" type="date" aria-label="Due Date">
'></iframe>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── Main frame elements (frame_index=0) ──────────────────────────────
    {"n": "1. Main: Submit button",
     "step": "Click the 'Submit Order' button",
     "m": "clickable", "st": ["Submit Order"], "tf": None,
     "exp_id": "main_submit", "exp_frame": 0},

    {"n": "2. Main: Email input",
     "step": "Fill 'Email Address' field with 'ghost@manul.ai'",
     "m": "input", "st": ["Email Address"], "tf": "email address",
     "exp_id": "main_email", "exp_frame": 0},

    {"n": "3. Main: Help link",
     "step": "Click the 'Help Center' link",
     "m": "clickable", "st": ["Help Center"], "tf": None,
     "exp_id": "main_help", "exp_frame": 0},

    {"n": "4. Main: Language dropdown",
     "step": "Select 'French' from the 'Language' dropdown",
     "m": "select", "st": ["French", "Language"], "tf": None,
     "exp_id": "main_lang", "exp_frame": 0},

    {"n": "5. Main: Search by aria",
     "step": "Fill 'Search Products' field with 'manul'",
     "m": "input", "st": ["Search Products"], "tf": "search products",
     "exp_id": "main_search", "exp_frame": 0},

    {"n": "6. Main: Logout aria-only",
     "step": "Click the 'Logout' button",
     "m": "clickable", "st": ["Logout"], "tf": None,
     "exp_id": "main_logout", "exp_frame": 0},

    # ── Login iframe elements (frame_index=1) ────────────────────────────
    {"n": "7. iFrame Login: Login button",
     "step": "Click the 'Login' button",
     "m": "clickable", "st": ["Login"], "tf": None,
     "exp_id": "iframe_login_btn", "exp_frame": 1},

    {"n": "8. iFrame Login: Username",
     "step": "Fill 'Username' field with 'admin'",
     "m": "input", "st": ["Username"], "tf": "username",
     "exp_id": "iframe_user", "exp_frame": 1},

    {"n": "9. iFrame Login: Password",
     "step": "Fill 'Password' field with 'secret'",
     "m": "input", "st": ["Password"], "tf": "password",
     "exp_id": "iframe_pass", "exp_frame": 1},

    {"n": "10. iFrame Login: Remember checkbox",
     "step": "Check the 'Remember Me' checkbox",
     "m": "clickable", "st": ["Remember Me"], "tf": None,
     "exp_id": "iframe_remember", "exp_frame": 1},

    {"n": "11. iFrame Login: Forgot link",
     "step": "Click the 'Forgot Password?' link",
     "m": "clickable", "st": ["Forgot Password?"], "tf": None,
     "exp_id": "iframe_forgot", "exp_frame": 1},

    {"n": "12. iFrame Login: data-qa signup",
     "step": "Click the 'Sign Up Free' button",
     "m": "clickable", "st": ["Sign Up Free"], "tf": None,
     "exp_id": "iframe_signup", "exp_frame": 1},

    # ── Widget iframe elements (frame_index=2) ──────────────────────────
    {"n": "13. iFrame Widget: Save by aria",
     "step": "Click the 'Save Changes' button",
     "m": "clickable", "st": ["Save Changes"], "tf": None,
     "exp_id": "widget_save", "exp_frame": 2},

    {"n": "14. iFrame Widget: Note input",
     "step": "Fill 'Add a note' field with 'important'",
     "m": "input", "st": ["Add a note"], "tf": "add a note",
     "exp_id": "widget_note", "exp_frame": 2},

    {"n": "15. iFrame Widget: Priority select",
     "step": "Select 'High' from the 'Priority' dropdown",
     "m": "select", "st": ["High", "Priority"], "tf": None,
     "exp_id": "widget_priority", "exp_frame": 2},

    {"n": "16. iFrame Widget: Cancel button",
     "step": "Click the 'Cancel' button",
     "m": "clickable", "st": ["Cancel"], "tf": None,
     "exp_id": "widget_cancel", "exp_frame": 2},

    {"n": "17. iFrame Widget: data-qa tag input",
     "step": "Fill 'Tag' field with 'urgent'",
     "m": "input", "st": ["Tag"], "tf": "tag",
     "exp_id": "widget_tag", "exp_frame": 2},

    {"n": "18. iFrame Widget: role checkbox",
     "step": "Click the 'Mark as Urgent' checkbox",
     "m": "clickable", "st": ["Mark as Urgent"], "tf": None,
     "exp_id": "widget_urgent", "exp_frame": 2},

    {"n": "19. iFrame Widget: title-based delete",
     "step": "Click the 'Delete Item' button",
     "m": "clickable", "st": ["Delete Item"], "tf": None,
     "exp_id": "widget_delete", "exp_frame": 2},

    {"n": "20. iFrame Widget: Due Date",
     "step": "Fill 'Due Date' field with '2026-06-15'",
     "m": "input", "st": ["Due Date"], "tf": "due date",
     "exp_id": "widget_due", "exp_frame": 2},
]


async def run_suite():
    print(f"\n{'=' * 70}")
    print("🖼️   IFRAME ROUTING LAB — Cross-Frame Element Resolution (20 tests)")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(IFRAME_DOM)
        # Wait for iframes to load their srcdoc content
        await page.wait_for_timeout(500)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🖼️  {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

            el = await manul._resolve_element(
                page, t["step"], t["m"], t["st"], t["tf"], "", set()
            )

            if el is None:
                msg = f"FAILED — element not found (None)"
                print(f"   ❌ {msg}")
                failed += 1
                failures.append(f"{t['n']}: {msg}")
                continue

            found_id = el.get("html_id", "")
            found_frame = el.get("frame_index", -1)

            id_ok = found_id == t["exp_id"]
            frame_ok = found_frame == t["exp_frame"]

            if id_ok and frame_ok:
                print(f"   ✅ PASSED  → '{found_id}' in frame {found_frame}")
                passed += 1
            else:
                parts = []
                if not id_ok:
                    parts.append(f"id='{found_id}' expected '{t['exp_id']}'")
                if not frame_ok:
                    parts.append(f"frame={found_frame} expected {t['exp_frame']}")
                msg = f"FAILED — {', '.join(parts)}"
                print(f"   ❌ {msg}")
                failed += 1
                failures.append(f"{t['n']}: {msg}")

        # ── Structural assertion: frame_for routing ──────────────────────
        print(f"\n{'─' * 70}")
        print("🔧 Structural: _frame_for() routing")
        struct_pass = 0
        struct_total = 3

        # Verify _frame_for returns correct frame objects
        frames = page.frames
        for idx in range(min(3, len(frames))):
            dummy_el = {"frame_index": idx}
            frame = manul._frame_for(page, dummy_el)
            if frame == frames[idx]:
                print(f"   ✅ _frame_for(frame_index={idx}) → correct frame")
                struct_pass += 1
            else:
                print(f"   ❌ _frame_for(frame_index={idx}) → wrong frame")
                failures.append(f"_frame_for routing: index {idx}")

        # Verify stale index fallback
        stale_el = {"frame_index": 999}
        fallback = manul._frame_for(page, stale_el)
        if fallback == page:
            print(f"   ✅ _frame_for(frame_index=999) → fallback to main page")
            struct_pass += 1
            struct_total += 1
        else:
            print(f"   ❌ _frame_for(frame_index=999) → did NOT fall back")
            struct_total += 1
            failures.append("_frame_for stale fallback")

        # Verify missing frame_index defaults to 0
        no_idx_el = {}
        default_frame = manul._frame_for(page, no_idx_el)
        if default_frame == frames[0]:
            print(f"   ✅ _frame_for(no frame_index) → main frame (index 0)")
            struct_pass += 1
            struct_total += 1
        else:
            print(f"   ❌ _frame_for(no frame_index) → wrong frame")
            struct_total += 1
            failures.append("_frame_for missing key")

        total = len(TESTS) + struct_total
        total_passed = passed + struct_pass
        total_failed = failed + (struct_total - struct_pass)

        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {total_passed}/{total} passed")
        if failures:
            print("\n🙀 Failures:")
            for f in failures:
                print(f"   • {f}")
        if total_passed == total:
            print("\n🏆 IFRAME ROUTING FLAWLESS — Cross-frame resolution is rock-solid!")
        print(f"{'=' * 70}")
        await browser.close()

    return total_passed == total


if __name__ == "__main__":
    asyncio.run(run_suite())
