import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Social Media & Messengers (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
SOCIAL_DOM = """
<!DOCTYPE html><html><head><style>
.svg-icon { width: 24px; height: 24px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
.toggle-switch { display: inline-block; width: 40px; height: 20px; background: #ccc; border-radius: 10px; }
.chat-input { min-height: 40px; border: 1px solid #ddd; padding: 5px; }
</style></head><body>

<button id="s1" aria-label="Like Post"><svg class="svg-icon"><path d="heart"/></svg></button>
<div role="button" id="s2" aria-label="Unlike">❤️</div>
<button id="s3" class="repost-btn">Repost</button>
<button id="s4"><span class="sr-only">Share via Direct Message</span>📤</button>
<div role="button" id="s5" aria-label="Save to Bookmarks">🔖</div>
<a href="/post/123/report" id="s6">Report this post</a>
<button id="s7">Hide</button>
<span role="button" id="s8" aria-label="More Options">•••</span>
<button id="s9" data-testid="translate-tweet">Translate post</button>
<div id="s10">View 15 hidden replies</div>

<div id="s11" contenteditable="true" aria-label="Write a comment..." class="chat-input"></div>
<button id="s12" disabled>Post Comment</button>
<button id="s13">Reply</button>
<input type="text" id="s14" placeholder="Mention someone (@)">
<div role="listbox" id="mention_list">
    <div role="option" id="s15">@alex_dev</div>
    <div role="option" id="s16">@manul_qa</div>
</div>
<button id="s17" aria-label="Insert Emoji">😀</button>
<label for="s18_upload"><span class="sr-only">Attach Photo</span>📷</label>
<input type="file" id="s18_upload" style="display:none;">
<button id="s19">Sort by: Top</button>
<div role="button" id="s20">Load more comments</div>

<input type="text" id="s21" placeholder="Search chats">
<div role="button" id="s22" aria-label="New Message">📝</div>
<div id="s23" role="textbox" contenteditable="true" aria-multiline="true" data-placeholder="Type a message"></div>
<button id="s24" aria-label="Send Message"><svg><path d="paper-plane"/></svg></button>
<button id="s25" aria-label="Record Voice Memo">🎤</button>
<div role="button" id="s26" aria-label="Video Call">📹</div>
<div role="button" id="s27" aria-label="Audio Call">📞</div>
<button id="s28">Mute Chat</button>
<button id="s29">Block User</button>
<a href="/inbox/requests" id="s30">Message Requests</a>

<button id="s31" class="btn-primary">Follow</button>
<button id="s32" class="btn-secondary">Following</button>
<button id="s33">Unfollow</button>
<button id="s34" aria-label="Remove follower">Remove</button>
<button id="s35">Connect</button>
<button id="s36">Accept Request</button>
<button id="s37">Decline</button>
<a href="/alex/followers" id="s38">Followers <span id="ext_followers">1,200</span></a>
<a href="/alex/following" id="s39">Following <span id="ext_following">350</span></a>
<button id="s40" data-action="subscribe">Subscribe</button>

<button id="s41">Edit Profile</button>
<input type="text" id="s42" value="Manul QA" aria-label="Display Name">
<textarea id="s43" aria-label="Bio">Automating the web.</textarea>
<input type="text" id="s44" placeholder="Add Location">
<input type="url" id="s45" placeholder="Website link">
<select id="s46" aria-label="Pronouns"><option>They/Them</option><option>He/Him</option></select>
<button id="s47" aria-label="Change Avatar">🖼️</button>
<button id="s48" aria-label="Change Cover Photo">🌄</button>
<button id="s49" class="save-profile">Save Changes</button>
<button id="s50">Cancel</button>

<div role="switch" id="s51" aria-checked="true" aria-label="Private Account" class="toggle-switch"></div>
<div role="switch" id="s52" aria-checked="false" aria-label="Show Activity Status" class="toggle-switch"></div>
<fieldset>
    <legend>Who can tag you?</legend>
    <input type="radio" id="s53" name="tags" value="everyone"><label for="s53">Everyone</label>
    <input type="radio" id="s54" name="tags" value="friends"><label for="s54">Friends Only</label>
    <input type="radio" id="s55" name="tags" value="nobody"><label for="s55">Nobody</label>
</fieldset>
<button id="s56">Change Password</button>
<button id="s57">Enable 2FA</button>
<a href="/settings/sessions" id="s58">Active Sessions</a>
<button id="s59" style="color:red;">Deactivate Account</button>
<button id="s60" style="color:darkred; font-weight:bold;">Delete Account Permanently</button>

<button id="s61" aria-label="Notifications">🔔 <span id="ext_notif">5</span></button>
<button id="s62">Mark all as read</button>
<button id="s63">Filter by Mentions</button>
<div role="button" id="s64" aria-label="Notification Settings">⚙️</div>
<div class="notif-item"><a href="/post/1" id="s65" data-qa="notif-alex">Alex liked your photo</a></div>
<div class="notif-item"><button id="s66" data-qa="notif-mute">Turn off notifications for this post</button></div>
<div class="tab" id="s67">All</div>
<div class="tab" id="s68">Verified</div>
<div class="tab" id="s69">Mentions</div>
<button id="s70" aria-label="Clear Notifications">Clear</button>

<input type="search" id="s71" placeholder="Search Twitter" aria-label="Search query">
<button id="s72" aria-label="Clear search">✖</button>
<div role="button" id="s73">Trending</div>
<div role="button" id="s74">News</div>
<div role="button" id="s75">Sports</div>
<a href="/hashtag/Manul" id="s76">#Manul</a>
<button id="s77" aria-label="Search Settings">⚙️</button>
<div role="button" id="s78">Clear recent searches</div>
<button id="s79">Show more trends</button>
<input type="text" id="s80" placeholder="Search messages...">

<button id="s81">Join Group</button>
<button id="s82">Leave Group</button>
<button id="s83">Invite Friends</button>
<fieldset>
    <legend>RSVP</legend>
    <button id="s84">Going</button>
    <button id="s85">Maybe</button>
    <button id="s86">Can't Go</button>
</fieldset>
<a href="/events/create" id="s87">Create Event</a>
<input type="text" id="s88" placeholder="Event Name">
<textarea id="s89" placeholder="Event Description"></textarea>
<button id="s90">Publish Event</button>

<div role="button" id="s91" aria-label="Next Story">▶</div>
<div role="button" id="s92" aria-label="Previous Story">◀</div>
<div role="button" id="s93" aria-label="Pause Story">⏸</div>
<input type="text" id="s94" placeholder="Reply to story...">
<button id="s95" aria-label="Send Reaction 💖">💖</button>
<button id="s96" aria-label="Send Reaction 🔥">🔥</button>
<button id="s97" aria-label="Close Modal">Close</button>
<button id="s98">Copy Link to Tweet</button>
<button id="s99">Pin to profile</button>
<button id="s100">Log Out</button>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Feed Interactions
    {"n": "1", "step": "Click 'Like Post'", "m": "clickable", "st": ["Like Post"], "tf": None, "exp": "s1"},
    {"n": "2", "step": "Click 'Unlike'", "m": "clickable", "st": ["Unlike"], "tf": None, "exp": "s2"},
    {"n": "3", "step": "Click 'Repost'", "m": "clickable", "st": ["Repost"], "tf": None, "exp": "s3"},
    {"n": "4", "step": "Click 'Share via Direct Message'", "m": "clickable", "st": ["Share via Direct Message"], "tf": None, "exp": "s4"},
    {"n": "5", "step": "Click 'Save to Bookmarks'", "m": "clickable", "st": ["Save to Bookmarks"], "tf": None, "exp": "s5"},
    {"n": "6", "step": "Click the 'Report this post' link", "m": "clickable", "st": ["Report this post"], "tf": None, "exp": "s6"},
    {"n": "7", "step": "Click 'Hide'", "m": "clickable", "st": ["Hide"], "tf": None, "exp": "s7"},
    {"n": "8", "step": "Click 'More Options'", "m": "clickable", "st": ["More Options"], "tf": None, "exp": "s8"},
    {"n": "9", "step": "Click 'Translate post'", "m": "clickable", "st": ["Translate post"], "tf": None, "exp": "s9"},
    {"n": "10", "step": "Click 'View 15 hidden replies'", "m": "clickable", "st": ["View 15 hidden replies"], "tf": None, "exp": "s10"},

    # Commenting & Mentions
    {"n": "11", "step": "Fill 'Write a comment...' with 'Nice post!'", "m": "input", "st": ["Write a comment..."], "tf": "write a comment...", "exp": "s11"},
    {"n": "12", "step": "Click 'Reply'", "m": "clickable", "st": ["Reply"], "tf": None, "exp": "s13"}, # Skip disabled s12
    {"n": "13", "step": "Click 'Reply'", "m": "clickable", "st": ["Reply"], "tf": None, "exp": "s13"},
    {"n": "14", "step": "Fill 'Mention someone' with 'alex'", "m": "input", "st": ["Mention someone"], "tf": "mention someone", "exp": "s14"},
    {"n": "15", "step": "Click '@alex_dev'", "m": "clickable", "st": ["@alex_dev"], "tf": None, "exp": "s15"},
    {"n": "16", "step": "Click '@manul_qa'", "m": "clickable", "st": ["@manul_qa"], "tf": None, "exp": "s16"},
    {"n": "17", "step": "Click 'Insert Emoji'", "m": "clickable", "st": ["Insert Emoji"], "tf": None, "exp": "s17"},
    {"n": "18", "step": "Click 'Attach Photo'", "m": "clickable", "st": ["Attach Photo"], "tf": None, "exp": "s18_upload"},
    {"n": "19", "step": "Click 'Sort by: Top'", "m": "clickable", "st": ["Sort by: Top"], "tf": None, "exp": "s19"},
    {"n": "20", "step": "Click 'Load more comments'", "m": "clickable", "st": ["Load more comments"], "tf": None, "exp": "s20"},

    # Direct Messages
    {"n": "21", "step": "Fill 'Search chats' with 'Bob'", "m": "input", "st": ["Search chats"], "tf": "search chats", "exp": "s21"},
    {"n": "22", "step": "Click 'New Message'", "m": "clickable", "st": ["New Message"], "tf": None, "exp": "s22"},
    {"n": "23", "step": "Fill 'Type a message' with 'Hello!'", "m": "input", "st": ["Type a message"], "tf": "type a message", "exp": "s23"},
    {"n": "24", "step": "Click 'Send Message'", "m": "clickable", "st": ["Send Message"], "tf": None, "exp": "s24"},
    {"n": "25", "step": "Click 'Record Voice Memo'", "m": "clickable", "st": ["Record Voice Memo"], "tf": None, "exp": "s25"},
    {"n": "26", "step": "Click 'Video Call'", "m": "clickable", "st": ["Video Call"], "tf": None, "exp": "s26"},
    {"n": "27", "step": "Click 'Audio Call'", "m": "clickable", "st": ["Audio Call"], "tf": None, "exp": "s27"},
    {"n": "28", "step": "Click 'Mute Chat'", "m": "clickable", "st": ["Mute Chat"], "tf": None, "exp": "s28"},
    {"n": "29", "step": "Click 'Block User'", "m": "clickable", "st": ["Block User"], "tf": None, "exp": "s29"},
    {"n": "30", "step": "Click 'Message Requests'", "m": "clickable", "st": ["Message Requests"], "tf": None, "exp": "s30"},

    # Network
    {"n": "31", "step": "Click 'Follow'", "m": "clickable", "st": ["Follow"], "tf": None, "exp": "s31"},
    {"n": "32", "step": "Click 'Following'", "m": "clickable", "st": ["Following"], "tf": None, "exp": "s32"},
    {"n": "33", "step": "Click 'Unfollow'", "m": "clickable", "st": ["Unfollow"], "tf": None, "exp": "s33"},
    {"n": "34", "step": "Click 'Remove follower'", "m": "clickable", "st": ["Remove follower"], "tf": None, "exp": "s34"},
    {"n": "35", "step": "Click 'Connect'", "m": "clickable", "st": ["Connect"], "tf": None, "exp": "s35"},
    {"n": "36", "step": "Click 'Accept Request'", "m": "clickable", "st": ["Accept Request"], "tf": None, "exp": "s36"},
    {"n": "37", "step": "Click 'Decline'", "m": "clickable", "st": ["Decline"], "tf": None, "exp": "s37"},
    {"n": "38", "step": "EXTRACT Followers count into {f1}", "ex": True, "var": "f1", "val": "1,200"},
    {"n": "39", "step": "EXTRACT Following count into {f2}", "ex": True, "var": "f2", "val": "350"},
    {"n": "40", "step": "Click 'Subscribe'", "m": "clickable", "st": ["Subscribe"], "tf": None, "exp": "s40"},

    # Profile Editing
    {"n": "41", "step": "Click 'Edit Profile'", "m": "clickable", "st": ["Edit Profile"], "tf": None, "exp": "s41"},
    {"n": "42", "step": "Fill 'Display Name' with 'Admin'", "m": "input", "st": ["Display Name"], "tf": "display name", "exp": "s42"},
    {"n": "43", "step": "Fill 'Bio' with 'Hello world'", "m": "input", "st": ["Bio"], "tf": "bio", "exp": "s43"},
    {"n": "44", "step": "Fill 'Add Location' with 'Kyiv'", "m": "input", "st": ["Add Location"], "tf": "add location", "exp": "s44"},
    {"n": "45", "step": "Fill 'Website link' with 'x.com'", "m": "input", "st": ["Website link"], "tf": "website link", "exp": "s45"},
    {"n": "46", "step": "Select 'He/Him' from 'Pronouns'", "m": "select", "st": ["He/Him", "Pronouns"], "tf": None, "exp": "s46"},
    {"n": "47", "step": "Click 'Change Avatar'", "m": "clickable", "st": ["Change Avatar"], "tf": None, "exp": "s47"},
    {"n": "48", "step": "Click 'Change Cover Photo'", "m": "clickable", "st": ["Change Cover Photo"], "tf": None, "exp": "s48"},
    {"n": "49", "step": "Click 'Save Changes'", "m": "clickable", "st": ["Save Changes"], "tf": None, "exp": "s49"},
    {"n": "50", "step": "Click 'Cancel'", "m": "clickable", "st": ["Cancel"], "tf": None, "exp": "s50"},

    # Privacy & Settings
    {"n": "51", "step": "Click 'Private Account' switch", "m": "clickable", "st": ["Private Account"], "tf": None, "exp": "s51"},
    {"n": "52", "step": "Click 'Show Activity Status'", "m": "clickable", "st": ["Show Activity Status"], "tf": None, "exp": "s52"},
    {"n": "53", "step": "Click the radio button for 'Everyone'", "m": "clickable", "st": ["Everyone"], "tf": None, "exp": "s53"},
    {"n": "54", "step": "Click the radio button for 'Friends Only'", "m": "clickable", "st": ["Friends Only"], "tf": None, "exp": "s54"},
    {"n": "55", "step": "Click the radio button for 'Nobody'", "m": "clickable", "st": ["Nobody"], "tf": None, "exp": "s55"},
    {"n": "56", "step": "Click 'Change Password'", "m": "clickable", "st": ["Change Password"], "tf": None, "exp": "s56"},
    {"n": "57", "step": "Click 'Enable 2FA'", "m": "clickable", "st": ["Enable 2FA"], "tf": None, "exp": "s57"},
    {"n": "58", "step": "Click 'Active Sessions'", "m": "clickable", "st": ["Active Sessions"], "tf": None, "exp": "s58"},
    {"n": "59", "step": "Click 'Deactivate Account'", "m": "clickable", "st": ["Deactivate Account"], "tf": None, "exp": "s59"},
    {"n": "60", "step": "Click 'Delete Account Permanently'", "m": "clickable", "st": ["Delete Account Permanently"], "tf": None, "exp": "s60"},

    # Notifications
    {"n": "61", "step": "Click 'Notifications'", "m": "clickable", "st": ["Notifications"], "tf": None, "exp": "s61"},
    {"n": "62", "step": "EXTRACT Notification count into {n}", "ex": True, "var": "n", "val": "5"},
    {"n": "63", "step": "Click 'Mark all as read'", "m": "clickable", "st": ["Mark all as read"], "tf": None, "exp": "s62"},
    {"n": "64", "step": "Click 'Filter by Mentions'", "m": "clickable", "st": ["Filter by Mentions"], "tf": None, "exp": "s63"},
    {"n": "65", "step": "Click 'Notification Settings'", "m": "clickable", "st": ["Notification Settings"], "tf": None, "exp": "s64"},
    {"n": "66", "step": "Click 'Alex liked your photo'", "m": "clickable", "st": ["Alex liked your photo"], "tf": None, "exp": "s65"},
    {"n": "67", "step": "Click 'Turn off notifications for this post'", "m": "clickable", "st": ["Turn off notifications for this post"], "tf": None, "exp": "s66"},
    {"n": "68", "step": "Click 'Verified' tab", "m": "clickable", "st": ["Verified"], "tf": None, "exp": "s68"},
    {"n": "69", "step": "Click 'Mentions' tab", "m": "clickable", "st": ["Mentions"], "tf": None, "exp": "s69"},
    {"n": "70", "step": "Click 'Clear Notifications'", "m": "clickable", "st": ["Clear Notifications"], "tf": None, "exp": "s70"},

    # Search & Explore
    {"n": "71", "step": "Fill 'Search query' with 'Python'", "m": "input", "st": ["Search query"], "tf": "search query", "exp": "s71"},
    {"n": "72", "step": "Click 'Clear search'", "m": "clickable", "st": ["Clear search"], "tf": None, "exp": "s72"},
    {"n": "73", "step": "Click 'Trending'", "m": "clickable", "st": ["Trending"], "tf": None, "exp": "s73"},
    {"n": "74", "step": "Click 'News'", "m": "clickable", "st": ["News"], "tf": None, "exp": "s74"},
    {"n": "75", "step": "Click 'Sports'", "m": "clickable", "st": ["Sports"], "tf": None, "exp": "s75"},
    {"n": "76", "step": "Click '#Manul'", "m": "clickable", "st": ["#Manul"], "tf": None, "exp": "s76"},
    {"n": "77", "step": "Click 'Search Settings'", "m": "clickable", "st": ["Search Settings"], "tf": None, "exp": "s77"},
    {"n": "78", "step": "Click 'Clear recent searches'", "m": "clickable", "st": ["Clear recent searches"], "tf": None, "exp": "s78"},
    {"n": "79", "step": "Click 'Show more trends'", "m": "clickable", "st": ["Show more trends"], "tf": None, "exp": "s79"},
    {"n": "80", "step": "Fill 'Search messages...' with 'meeting'", "m": "input", "st": ["Search messages..."], "tf": "search messages...", "exp": "s80"},

    # Groups & Events
    {"n": "81", "step": "Click 'Join Group'", "m": "clickable", "st": ["Join Group"], "tf": None, "exp": "s81"},
    {"n": "82", "step": "Click 'Leave Group'", "m": "clickable", "st": ["Leave Group"], "tf": None, "exp": "s82"},
    {"n": "83", "step": "Click 'Invite Friends'", "m": "clickable", "st": ["Invite Friends"], "tf": None, "exp": "s83"},
    {"n": "84", "step": "Click 'Going'", "m": "clickable", "st": ["Going"], "tf": None, "exp": "s84"},
    {"n": "85", "step": "Click 'Maybe'", "m": "clickable", "st": ["Maybe"], "tf": None, "exp": "s85"},
    {"n": "86", "step": "Click 'Can\\'t Go'", "m": "clickable", "st": ["Can't Go"], "tf": None, "exp": "s86"},
    {"n": "87", "step": "Click 'Create Event'", "m": "clickable", "st": ["Create Event"], "tf": None, "exp": "s87"},
    {"n": "88", "step": "Fill 'Event Name' with 'Party'", "m": "input", "st": ["Event Name"], "tf": "event name", "exp": "s88"},
    {"n": "89", "step": "Fill 'Event Description' with 'Fun'", "m": "input", "st": ["Event Description"], "tf": "event description", "exp": "s89"},
    {"n": "90", "step": "Click 'Publish Event'", "m": "clickable", "st": ["Publish Event"], "tf": None, "exp": "s90"},

    # Stories & Modals
    {"n": "91", "step": "Click 'Next Story'", "m": "clickable", "st": ["Next Story"], "tf": None, "exp": "s91"},
    {"n": "92", "step": "Click 'Previous Story'", "m": "clickable", "st": ["Previous Story"], "tf": None, "exp": "s92"},
    {"n": "93", "step": "Click 'Pause Story'", "m": "clickable", "st": ["Pause Story"], "tf": None, "exp": "s93"},
    {"n": "94", "step": "Fill 'Reply to story' with 'Cool!'", "m": "input", "st": ["Reply to story"], "tf": "reply to story", "exp": "s94"},
    {"n": "95", "step": "Click 'Send Reaction 💖'", "m": "clickable", "st": ["Send Reaction 💖"], "tf": None, "exp": "s95"},
    {"n": "96", "step": "Click 'Send Reaction 🔥'", "m": "clickable", "st": ["Send Reaction 🔥"], "tf": None, "exp": "s96"},
    {"n": "97", "step": "Click 'Close Modal'", "m": "clickable", "st": ["Close Modal"], "tf": None, "exp": "s97"},
    {"n": "98", "step": "Click 'Copy Link to Tweet'", "m": "clickable", "st": ["Copy Link to Tweet"], "tf": None, "exp": "s98"},
    {"n": "99", "step": "Click 'Pin to profile'", "m": "clickable", "st": ["Pin to profile"], "tf": None, "exp": "s99"},
    {"n": "100", "step": "Click 'Log Out'", "m": "clickable", "st": ["Log Out"], "tf": None, "exp": "s100"},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("💬 SOCIAL MEDIA HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(SOCIAL_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🧬 {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.last_xpath = None

            if t.get("ex"):
                manul.memory.clear()
                res = await manul._handle_extract(page, t["step"])
                actual = manul.memory.get(t["var"], None)
                if res and actual == t["val"]:
                    print(f"   ✅ PASSED  → {{{t['var']}}} = '{actual}'")
                    passed += 1
                else:
                    msg = f"FAILED — got '{actual}', expected '{t['val']}'"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            elif t.get("ver"):
                result = await manul._handle_verify(page, t["step"])
                if result == t["res"]:
                    print(f"   ✅ PASSED  → VERIFY returned {result}")
                    passed += 1
                else:
                    msg = f"FAILED — VERIFY returned {result}, expected {t['res']}"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            elif "if exists" in t["step"]:
                result = await manul._execute_step(page, t["step"], "")
                if result is True:
                    print("   ✅ PASSED  → Optional handled")
                    passed += 1
                else:
                    msg = "FAILED — optional step did not pass"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            else:
                el = await manul._resolve_element(page, t["step"], t["m"], t["st"], t["tf"], "", set())
                found = el.get("html_id") if el else None
                if found == t["exp"]:
                    print(f"   ✅ PASSED  → '{found}'")
                    passed += 1
                else:
                    msg = f"FAILED — got '{found}', expected '{t['exp']}'"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {passed}/{len(TESTS)} passed")
        if failures:
            print("\n💀 Failures:")
            for f in failures:
                print(f"   • {f}")
        if passed == len(TESTS):
            print("\n🏆 FLAWLESS VICTORY!")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == len(TESTS)

if __name__ == "__main__":
    asyncio.run(run_suite())