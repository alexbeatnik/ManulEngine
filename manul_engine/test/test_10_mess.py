import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: The Unholy Mess & Final Boss (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
MESS_DOM = """
<!DOCTYPE html><html><head><style>
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
.honeypot { opacity: 0; position: absolute; top: -9999px; left: -9999px; }
.dark-pattern-btn { background: none; border: none; color: #ccc; font-size: 10px; text-decoration: underline; }
.floating-ad { position: fixed; bottom: 10px; right: 10px; z-index: 9999; background: red; }
</style></head><body>

<div class="cookie-banner">
    <h2>We value your privacy (sort of)</h2>
    <button id="x1" style="font-size:24px; background:green; color:white;">ACCEPT ALL COOKIES</button>
    <button id="x2" class="dark-pattern-btn">Manage Preferences</button>
    <button id="x3" class="dark-pattern-btn">Reject All (Takes 5 minutes)</button>
    <div id="pref_modal">
        <input type="checkbox" id="x4" checked disabled><label>Strictly Necessary</label>
        <input type="checkbox" id="x5"><label>Marketing Cookies</label>
        <input type="checkbox" id="x6"><label>Analytics Cookies</label>
    </div>
    <button id="x7" data-qa="save-pref">Save Preferences</button>
    <a href="#" id="x8">Read our 50-page Privacy Policy</a>
    <button id="x9" aria-label="Close Cookie Banner">X</button>
    <div id="x10" role="alert">Consent saved.</div>
</div>

<div class="captcha-box">
    <input type="checkbox" id="x11"><label for="x11">I am human</label>
    <button id="x12" aria-label="Reload Captcha Image">🔄</button>
    <button id="x13" aria-label="Play Audio Challenge">🔊</button>
    <input type="text" id="x14" placeholder="Type the distorted text">
    <input type="text" id="x15_honeypot" class="honeypot" placeholder="Do not fill this">
    <button id="x16_honeypot">Admin bypass</button>
    <img src="traffic_light.jpg" alt="Traffic Light" id="x17" role="button">
    <button id="x18">Verify Images</button>
    <div id="x19">Error: Please try again.</div>
    <button id="x20">Report CAPTCHA issue</button>
</div>

<div class="upsell-modal">
    <h3>Upgrade to Premium!</h3>
    <button id="x21" style="background:green;">Yes, upgrade me now!</button>
    <button id="x22" class="dark-pattern-btn">No thanks, I hate saving money</button>
    <input type="checkbox" id="x23" checked><label for="x23">Subscribe to spam newsletter</label>
    <div style="font-size:8px;">By clicking continue, you agree to sell your soul. <input type="checkbox" id="x24" checked></div>
    <button id="x25" aria-label="Continue without upgrading">Continue</button>
    <div id="x26" style="color:red; display:none;">Wait, don't leave! Take 50% off!</div>
    <button id="x27" style="display:none;">Claim 50% Discount</button>
    <span id="x28" data-qa="sale-timer">Sale ends in 00:59</span>
    <button id="x29">Read Terms</button>
    <button id="x30">Close Upsell</button>
</div>

<div class="floating-ad">
    <button id="x31" aria-label="Close Ad">✖</button>
    <a href="#" id="x32">Click here for free iPad</a>
</div>
<button id="x33" style="position:fixed; bottom:20px; right:80px; border-radius:50%;" title="Chat Support">💬</button>
<div id="x34" role="dialog" aria-labelledby="chat_title">
    <h4 id="chat_title">How can we help?</h4>
    <input type="text" id="x35" placeholder="Type message...">
    <button id="x36" aria-label="Send Message">➤</button>
    <button id="x37">Minimize Chat</button>
    <button id="x38">End Chat Session</button>
</div>
<nav style="position:sticky; top:0; z-index:100;">
    <button id="x39">Sticky Header Menu</button>
    <input type="text" id="x40" placeholder="Global Search">
</nav>

<div class="toolbar">
    <button id="x41" aria-label="Bold (Ctrl+B)">B</button>
    <button id="x42" aria-label="Italic (Ctrl+I)">I</button>
    <button id="x43" aria-label="Underline (Ctrl+U)">U</button>
    <button id="x44" aria-label="Insert Link">🔗</button>
    <button id="x45" aria-label="Insert Image">🖼️</button>
    <select id="x46" aria-label="Font Size"><option>12pt</option><option>14pt</option></select>
    <button id="x47">View Source (HTML)</button>
</div>
<div id="x48" contenteditable="true" aria-label="Rich Text Area">Start typing...</div>
<button id="x49">Publish Post</button>
<button id="x50">Save as Draft</button>

<div class="weird-inputs">
    <label for="x51">Pick a color:</label> <input type="color" id="x51" value="#ff0000">
    <label for="x52">Alarm Time:</label> <input type="time" id="x52">
    <label for="x53">Expiration Month:</label> <input type="month" id="x53">
    <label for="x54">Intensity:</label> <input type="range" id="x54" min="1" max="10">
    <label for="x55">Secret Key:</label> <input type="password" id="x55" readonly value="hidden_key">
    <button id="x56">Unlock Key</button>
    <input type="file" id="x57" accept="image/png, image/jpeg" aria-label="Avatar Upload">
    <button id="x58">Clear File</button>
    <label for="x59">Volume Knob</label><input type="range" id="x59" aria-label="Volume Knob" min="0" max="100" value="75">
    <button id="x60">Reset Defaults</button>
</div>

<div class="tooltip-container">
    <span id="x61" title="This is a native tooltip">Hover me</span>
    <button id="x62" aria-describedby="tip_62">Submit</button>
    <div id="tip_62" role="tooltip" class="sr-only">Double check before submitting!</div>
    <div role="button" id="x63" data-popover="true">Click for more info</div>
    <div id="x64" class="popover-content" style="display:none;">Here is the secret info.</div>
    <button id="x65">Close Popover</button>
    <span class="info-icon" id="x66" aria-label="Help">?</span>
    <input type="text" id="x67" placeholder="Hover to reveal" onmouseover="this.placeholder='Now type'">
    <button id="x68" class="ghost-btn">Ghost Action</button>
    <div id="x69">Dynamic Text: <span id="dyn_val">Loading...</span></div>
    <button id="x70" onclick="document.getElementById('dyn_val').innerText='Loaded!'">Load Data</button>
</div>

<div role="group" aria-label="Social Links">
    <a href="#" id="x71" aria-label="Facebook"><svg><circle cx="5"/></svg></a>
    <a href="#" id="x72" aria-label="Twitter"><svg><rect width="5"/></svg></a>
    <a href="#" id="x73" aria-label="LinkedIn"><svg><polygon points="1"/></svg></a>
</div>
<button id="x74" aria-label="Actual Action">Wrong Visible Text</button>
<div id="x75" role="button" aria-disabled="true">Looks clickable but isn't</div>
<a href="#" id="x76_link"><button id="x76">Go to Target</button></a>
<div role="textbox" contenteditable="true" id="x77" aria-placeholder="Fake Input"></div>
<button id="x78">Clear Fake Input</button>
<div role="alertdialog" id="x79" aria-labelledby="alert_title">
    <h1 id="alert_title">Warning</h1><button id="x80">Dismiss Warning</button>
</div>

<ul id="messy_list">
    <li>Name: <strong id="x81">Manul</strong></li>
    <li>Age: <span id="x82">3 years</span></li>
    <li>Job: <i id="x83">QA Automation</i></li>
</ul>
<table class="headless-table" role="table">
    <div role="row"><span role="cell">Status</span><span role="cell" id="x84">Operational</span></div>
    <div role="row"><span role="cell">Ping</span><span role="cell" id="x85">42ms</span></div>
</table>
<div class="deep-nest">
    <div><div><span id="x86">Deep Text</span></div></div>
</div>
<button id="x87">Extract Everything</button>
<input type="text" id="x88" value="Pre-filled data">
<textarea id="x89">Pre-filled textarea</textarea>
<button id="x90">Wipe Data</button>

<div id="boss_host"></div>
<script>
    const sh = document.getElementById('boss_host').attachShadow({mode: 'open'});
    const b1 = document.createElement('button'); b1.id = 'x91'; b1.textContent = 'Shadow Strike';
    const i1 = document.createElement('input'); i1.id = 'x92'; i1.placeholder = 'Shadow Input';
    sh.appendChild(b1); sh.appendChild(i1);
</script>
<button id="x93" style="width:0;height:0;opacity:0;">Zero Pixel Trap</button>
<div role="button" id="x94" style="clip-path: circle(0%);">Clipped Trap</div>
<span id="x95" role="checkbox" aria-checked="false" tabindex="0">Custom Span Checkbox</span>
<button id="x96" class="generic">Submit</button>
<button id="x97" class="generic" data-context="final">Submit Final</button>
<div id="x98">Test Complete</div>
<div id="hover_zone" onmouseover="document.getElementById('x99').style.display='block'">
    Hover Here
    <button id="x99" style="display:none;">Hidden Hover Button</button>
</div>
<button id="x100" class="celebrate-btn" style="font-size: 50px;">🎉 FINISH LAB 🎉</button>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Cookies & Privacy
    {
        "n": "1",
        "step": "Click 'ACCEPT ALL COOKIES'",
        "m": "clickable",
        "st": ["ACCEPT ALL COOKIES"],
        "tf": None,
        "exp": "x1",
    },
    {
        "n": "2",
        "step": "Click 'Manage Preferences'",
        "m": "clickable",
        "st": ["Manage Preferences"],
        "tf": None,
        "exp": "x2",
    },
    {
        "n": "3",
        "step": "VERIFY that 'Strictly Necessary' is present",
        "ver": True,
        "res": True,
    },  # Move VERIFY *BEFORE* closing modal
    {
        "n": "4",
        "step": "Click 'Reject All'",
        "m": "clickable",
        "st": ["Reject All"],
        "tf": None,
        "exp": "x3",
    },  # Click closes modal
    {
        "n": "5",
        "step": "Check 'Marketing Cookies'",
        "m": "clickable",
        "st": ["Marketing Cookies"],
        "tf": None,
        "exp": "x5",
    },
    {
        "n": "6",
        "step": "Check 'Analytics Cookies'",
        "m": "clickable",
        "st": ["Analytics Cookies"],
        "tf": None,
        "exp": "x6",
    },
    {
        "n": "7",
        "step": "Click 'Save Preferences'",
        "m": "clickable",
        "st": ["Save Preferences"],
        "tf": None,
        "exp": "x7",
    },
    {
        "n": "8",
        "step": "Click the 'Privacy Policy' link",
        "m": "clickable",
        "st": ["Privacy Policy"],
        "tf": None,
        "exp": "x8",
    },
    {
        "n": "9",
        "step": "Click 'Close Cookie Banner'",
        "m": "clickable",
        "st": ["Close Cookie Banner"],
        "tf": None,
        "exp": "x9",
    },
    {"n": "10", "step": "VERIFY 'Consent saved.' is present", "ver": True, "res": True},
    # Captcha & Anti-Bot
    {"n": "11", "step": "Check 'I am human'", "m": "clickable", "st": ["I am human"], "tf": None, "exp": "x11"},
    {
        "n": "12",
        "step": "Click 'Reload Captcha Image'",
        "m": "clickable",
        "st": ["Reload Captcha Image"],
        "tf": None,
        "exp": "x12",
    },
    {
        "n": "13",
        "step": "Click 'Play Audio Challenge'",
        "m": "clickable",
        "st": ["Play Audio Challenge"],
        "tf": None,
        "exp": "x13",
    },
    {
        "n": "14",
        "step": "Fill 'Type the distorted text' with 'smudge'",
        "m": "input",
        "st": ["Type the distorted text"],
        "tf": "type the distorted text",
        "exp": "x14",
    },
    {
        "n": "15",
        "step": "Fill 'Do not fill this' optional",
        "m": "input",
        "st": ["Do not fill this"],
        "tf": "do not fill this",
        "exp": "x15_honeypot",
    },  # Testing ability to hit honeypot if explicitly asked
    {
        "n": "16",
        "step": "Click 'Admin bypass'",
        "m": "clickable",
        "st": ["Admin bypass"],
        "tf": None,
        "exp": "x16_honeypot",
    },
    {
        "n": "17",
        "step": "Click 'Traffic Light' image",
        "m": "clickable",
        "st": ["Traffic Light"],
        "tf": None,
        "exp": "x17",
    },
    {"n": "18", "step": "Click 'Verify Images'", "m": "clickable", "st": ["Verify Images"], "tf": None, "exp": "x18"},
    {"n": "19", "step": "VERIFY 'Please try again.' is present", "ver": True, "res": True},
    {
        "n": "20",
        "step": "Click 'Report CAPTCHA issue'",
        "m": "clickable",
        "st": ["Report CAPTCHA issue"],
        "tf": None,
        "exp": "x20",
    },
    # Dark Patterns
    {
        "n": "21",
        "step": "Click 'Yes, upgrade me now!'",
        "m": "clickable",
        "st": ["Yes, upgrade me now!"],
        "tf": None,
        "exp": "x21",
    },
    {
        "n": "22",
        "step": "Click 'I hate saving money'",
        "m": "clickable",
        "st": ["I hate saving money"],
        "tf": None,
        "exp": "x22",
    },
    {
        "n": "23",
        "step": "Uncheck 'Subscribe to spam newsletter'",
        "m": "clickable",
        "st": ["Subscribe to spam newsletter"],
        "tf": None,
        "exp": "x23",
    },
    {
        "n": "24",
        "step": "Uncheck 'sell your soul'",
        "m": "clickable",
        "st": ["sell your soul"],
        "tf": None,
        "exp": "x24",
    },
    {
        "n": "25",
        "step": "Click 'Continue without upgrading'",
        "m": "clickable",
        "st": ["Continue without upgrading"],
        "tf": None,
        "exp": "x25",
    },
    {"n": "26", "step": "VERIFY that 'Wait, don't leave!' is NOT present", "ver": True, "res": True},
    {
        "n": "27",
        "step": "Click 'Claim 50% Discount' if exists",
        "m": "clickable",
        "st": ["Claim 50% Discount"],
        "tf": None,
        "exp": None,
    },
    {"n": "28", "step": "EXTRACT time into {t}", "ex": True, "var": "t", "val": "Sale ends in 00:59"},
    {"n": "29", "step": "Click 'Read Terms'", "m": "clickable", "st": ["Read Terms"], "tf": None, "exp": "x29"},
    {"n": "30", "step": "Click 'Close Upsell'", "m": "clickable", "st": ["Close Upsell"], "tf": None, "exp": "x30"},
    # Overlaps & Floating
    {"n": "31", "step": "Click 'Close Ad'", "m": "clickable", "st": ["Close Ad"], "tf": None, "exp": "x31"},
    {"n": "32", "step": "Click 'free iPad'", "m": "clickable", "st": ["free iPad"], "tf": None, "exp": "x32"},
    {"n": "33", "step": "Click 'Chat Support'", "m": "clickable", "st": ["Chat Support"], "tf": None, "exp": "x33"},
    {"n": "34", "step": "VERIFY 'How can we help?' is present", "ver": True, "res": True},
    {
        "n": "35",
        "step": "Fill 'Type message...' with 'Help'",
        "m": "input",
        "st": ["Type message..."],
        "tf": "type message...",
        "exp": "x35",
    },
    {"n": "36", "step": "Click 'Send Message'", "m": "clickable", "st": ["Send Message"], "tf": None, "exp": "x36"},
    {"n": "37", "step": "Click 'Minimize Chat'", "m": "clickable", "st": ["Minimize Chat"], "tf": None, "exp": "x37"},
    {
        "n": "38",
        "step": "Click 'End Chat Session'",
        "m": "clickable",
        "st": ["End Chat Session"],
        "tf": None,
        "exp": "x38",
    },
    {
        "n": "39",
        "step": "Click 'Sticky Header Menu'",
        "m": "clickable",
        "st": ["Sticky Header Menu"],
        "tf": None,
        "exp": "x39",
    },
    {
        "n": "40",
        "step": "Fill 'Global Search' with 'Manul'",
        "m": "input",
        "st": ["Global Search"],
        "tf": "global search",
        "exp": "x40",
    },
    # Rich Text
    {"n": "41", "step": "Click 'Bold (Ctrl+B)'", "m": "clickable", "st": ["Bold (Ctrl+B)"], "tf": None, "exp": "x41"},
    {
        "n": "42",
        "step": "Click 'Italic (Ctrl+I)'",
        "m": "clickable",
        "st": ["Italic (Ctrl+I)"],
        "tf": None,
        "exp": "x42",
    },
    {"n": "43", "step": "Click 'Underline'", "m": "clickable", "st": ["Underline"], "tf": None, "exp": "x43"},
    {"n": "44", "step": "Click 'Insert Link'", "m": "clickable", "st": ["Insert Link"], "tf": None, "exp": "x44"},
    {"n": "45", "step": "Click 'Insert Image'", "m": "clickable", "st": ["Insert Image"], "tf": None, "exp": "x45"},
    {
        "n": "46",
        "step": "Select '14pt' from 'Font Size'",
        "m": "select",
        "st": ["14pt", "Font Size"],
        "tf": None,
        "exp": "x46",
    },
    {
        "n": "47",
        "step": "Click 'View Source (HTML)'",
        "m": "clickable",
        "st": ["View Source (HTML)"],
        "tf": None,
        "exp": "x47",
    },
    {
        "n": "48",
        "step": "Fill 'Rich Text Area' with 'Hello'",
        "m": "input",
        "st": ["Rich Text Area"],
        "tf": "rich text area",
        "exp": "x48",
    },
    {"n": "49", "step": "Click 'Publish Post'", "m": "clickable", "st": ["Publish Post"], "tf": None, "exp": "x49"},
    {"n": "50", "step": "Click 'Save as Draft'", "m": "clickable", "st": ["Save as Draft"], "tf": None, "exp": "x50"},
    # Exotic Inputs
    {
        "n": "51",
        "step": "Fill 'Pick a color' with '#00ff00'",
        "m": "input",
        "st": ["Pick a color"],
        "tf": "pick a color",
        "exp": "x51",
    },
    {
        "n": "52",
        "step": "Fill 'Alarm Time' with '08:00'",
        "m": "input",
        "st": ["Alarm Time"],
        "tf": "alarm time",
        "exp": "x52",
    },
    {
        "n": "53",
        "step": "Fill 'Expiration Month' with '2026-10'",
        "m": "input",
        "st": ["Expiration Month"],
        "tf": "expiration month",
        "exp": "x53",
    },
    {
        "n": "54",
        "step": "Fill 'Intensity' with '8'",
        "m": "input",
        "st": ["Intensity"],
        "tf": "intensity",
        "exp": "x54",
    },
    {
        "n": "55",
        "step": "Fill 'Secret Key' with 'override'",
        "m": "input",
        "st": ["Secret Key"],
        "tf": "secret key",
        "exp": "x55",
        "execute_step": True,
    },  # Need to remove readonly
    {"n": "56", "step": "Click 'Unlock Key'", "m": "clickable", "st": ["Unlock Key"], "tf": None, "exp": "x56"},
    {"n": "57", "step": "Click 'Avatar Upload'", "m": "clickable", "st": ["Avatar Upload"], "tf": None, "exp": "x57"},
    {"n": "58", "step": "Click 'Clear File'", "m": "clickable", "st": ["Clear File"], "tf": None, "exp": "x58"},
    {
        "n": "59",
        "step": "Fill 'Volume Knob' with '90'",
        "m": "input",
        "st": ["Volume Knob"],
        "tf": "volume knob",
        "exp": "x59",
    },  # Using role=slider
    {"n": "60", "step": "Click 'Reset Defaults'", "m": "clickable", "st": ["Reset Defaults"], "tf": None, "exp": "x60"},
    # Tooltips & Dynamic
    {
        "n": "61",
        "step": "HOVER over 'Hover me'",
        "m": "hover",
        "st": ["Hover me"],
        "tf": None,
        "exp": "x61",
        "execute_step": True,
    },
    {"n": "62", "step": "Click 'Submit' button", "m": "clickable", "st": ["Submit"], "tf": None, "exp": "x62"},
    {
        "n": "63",
        "step": "Click 'Click for more info'",
        "m": "clickable",
        "st": ["Click for more info"],
        "tf": None,
        "exp": "x63",
    },
    {
        "n": "64",
        "step": "VERIFY that 'Here is the secret info' is NOT present",
        "ver": True,
        "res": True,
    },  # Hidden initially
    {"n": "65", "step": "Click 'Close Popover'", "m": "clickable", "st": ["Close Popover"], "tf": None, "exp": "x65"},
    {"n": "66", "step": "Click 'Help' icon", "m": "clickable", "st": ["Help"], "tf": None, "exp": "x66"},
    {
        "n": "67",
        "step": "Fill 'Hover to reveal' with 'Test'",
        "m": "input",
        "st": ["Hover to reveal"],
        "tf": "hover to reveal",
        "exp": "x67",
    },
    {"n": "68", "step": "Click 'Ghost Action'", "m": "clickable", "st": ["Ghost Action"], "tf": None, "exp": "x68"},
    {"n": "69", "step": "VERIFY 'Loading...' is present", "ver": True, "res": True},
    {"n": "70", "step": "Click 'Load Data'", "m": "clickable", "st": ["Load Data"], "tf": None, "exp": "x70"},
    # Nested & ARIA
    {"n": "71", "step": "Click 'Facebook' icon", "m": "clickable", "st": ["Facebook"], "tf": None, "exp": "x71"},
    {"n": "72", "step": "Click 'Twitter' icon", "m": "clickable", "st": ["Twitter"], "tf": None, "exp": "x72"},
    {"n": "73", "step": "Click 'LinkedIn' icon", "m": "clickable", "st": ["LinkedIn"], "tf": None, "exp": "x73"},
    {"n": "74", "step": "Click 'Actual Action'", "m": "clickable", "st": ["Actual Action"], "tf": None, "exp": "x74"},
    {
        "n": "75",
        "step": "Click 'Looks clickable'",
        "m": "clickable",
        "st": ["Looks clickable"],
        "tf": None,
        "exp": "x75",
    },
    {"n": "76", "step": "Click 'Go to Target'", "m": "clickable", "st": ["Go to Target"], "tf": None, "exp": "x76"},
    {
        "n": "77",
        "step": "Fill 'Fake Input' with 'Hacked'",
        "m": "input",
        "st": ["Fake Input"],
        "tf": "fake input",
        "exp": "x77",
    },
    {
        "n": "78",
        "step": "Click 'Clear Fake Input'",
        "m": "clickable",
        "st": ["Clear Fake Input"],
        "tf": None,
        "exp": "x78",
    },
    {"n": "79", "step": "VERIFY 'Warning' is present", "ver": True, "res": True},
    {
        "n": "80",
        "step": "Click 'Dismiss Warning'",
        "m": "clickable",
        "st": ["Dismiss Warning"],
        "tf": None,
        "exp": "x80",
    },
    # Data Extraction Chaos
    {"n": "81", "step": "EXTRACT Name into {n}", "ex": True, "var": "n", "val": "Manul"},
    {"n": "82", "step": "EXTRACT Age into {a}", "ex": True, "var": "a", "val": "3 years"},
    {"n": "83", "step": "EXTRACT Job into {j}", "ex": True, "var": "j", "val": "QA Automation"},
    {"n": "84", "step": "EXTRACT Status into {s}", "ex": True, "var": "s", "val": "Operational"},
    {"n": "85", "step": "EXTRACT Ping into {p}", "ex": True, "var": "p", "val": "42ms"},
    {"n": "86", "step": "EXTRACT Deep Text into {dt}", "ex": True, "var": "dt", "val": "Deep Text"},
    {
        "n": "87",
        "step": "Click 'Extract Everything'",
        "m": "clickable",
        "st": ["Extract Everything"],
        "tf": None,
        "exp": "x87",
    },
    {
        "n": "88",
        "step": "Fill 'Pre-filled data' with 'New Data'",
        "m": "input",
        "st": ["Pre-filled data"],
        "tf": "pre-filled data",
        "exp": "x88",
    },
    {
        "n": "89",
        "step": "Fill 'Pre-filled textarea' with 'Empty'",
        "m": "input",
        "st": ["Pre-filled textarea"],
        "tf": "pre-filled textarea",
        "exp": "x89",
    },
    {"n": "90", "step": "Click 'Wipe Data'", "m": "clickable", "st": ["Wipe Data"], "tf": None, "exp": "x90"},
    # FINAL BOSS
    {"n": "91", "step": "Click 'Shadow Strike'", "m": "clickable", "st": ["Shadow Strike"], "tf": None, "exp": "x91"},
    {
        "n": "92",
        "step": "Fill 'Shadow Input' with 'Pierced'",
        "m": "input",
        "st": ["Shadow Input"],
        "tf": "shadow input",
        "exp": "x92",
    },
    {
        "n": "93",
        "step": "Click 'Zero Pixel Trap' optional",
        "m": "clickable",
        "st": ["Zero Pixel Trap"],
        "tf": None,
        "exp": None,
    },  # Ignore invisibles
    {
        "n": "94",
        "step": "Click 'Clipped Trap' optional",
        "m": "clickable",
        "st": ["Clipped Trap"],
        "tf": None,
        "exp": None,
    },  # Ignore clipped
    {
        "n": "95",
        "step": "Check 'Custom Span Checkbox'",
        "m": "clickable",
        "st": ["Custom Span Checkbox"],
        "tf": None,
        "exp": "x95",
    },
    {
        "n": "96",
        "step": "Click 'Submit'",
        "m": "clickable",
        "st": ["Submit"],
        "tf": None,
        "exp": "x62",
    },  # Ambiguous 'Submit' matches first best (x62 is native button)
    {"n": "97", "step": "Click 'Submit Final'", "m": "clickable", "st": ["Submit Final"], "tf": None, "exp": "x97"},
    {"n": "98", "step": "VERIFY 'Test Complete' is present", "ver": True, "res": True},
    {
        "n": "99",
        "step": "Click 'Hidden Hover Button' optional",
        "m": "clickable",
        "st": ["Hidden Hover Button"],
        "tf": None,
        "exp": None,
    },  # Hidden, skipped
    {"n": "100", "step": "Click 'FINISH LAB'", "m": "clickable", "st": ["FINISH LAB"], "tf": None, "exp": "x100"},
]


async def run_suite():
    print(f"\n{'=' * 70}")
    print("🙀 THE UNHOLY MESS & FINAL BOSS: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(MESS_DOM)

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n🧬 {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

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

            elif "if exists" in t["step"] or "optional" in t["step"]:
                result = await manul._execute_step(page, t["step"], "")
                if result is True:
                    print("   ✅ PASSED  → Optional handled")
                    passed += 1
                else:
                    msg = "FAILED — optional step did not pass"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            elif t.get("execute_step"):
                result = await manul._execute_step(page, t["step"], "")
                if result:
                    print("   ✅ PASSED  → execute_step succeeded")
                    passed += 1
                else:
                    msg = "FAILED — execute_step returned False"
                    print(f"   ❌ {msg}")
                    failed += 1
                    failures.append(f"{t['n']}: {msg}")

            else:
                el = await manul._resolve_element(page, t["step"], t["m"], t["st"], t["tf"], "", set())
                found = el.get("html_id") if el else None
                if found == t["exp"] or (t["n"] == "96" and found in ["x62", "x96"]):
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
            print("\n🙀 Failures:")
            for f in failures:
                print(f"   • {f}")
        if passed == len(TESTS):
            print("\n👑 1000/1000 TESTS COMPLETED. THE MANUL IS OMNIPOTENT! 👑")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == len(TESTS)


if __name__ == "__main__":
    asyncio.run(run_suite())
