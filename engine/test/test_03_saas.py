import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: SaaS & Admin Panels (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
SAAS_DOM = """
<!DOCTYPE html><html><head><style>
.sidebar { width: 250px; background: #333; color: white; }
.badge { padding: 2px 6px; border-radius: 4px; font-size: 12px; }
.badge-success { background: green; }
.hidden { display: none; }
</style></head><body>

<nav class="sidebar">
    <a href="/dashboard" id="a1">Dashboard</a>
    <a href="/users" id="a2">User Management</a>
    <a href="/billing" id="a3">Billing & Plans</a>
    <a href="/settings" id="a4">Workspace Settings</a>
    <button id="a5" aria-label="Collapse Sidebar">◀</button>
    <div role="button" id="a6">Help & Support</div>
    <a href="/api" id="a7">API Keys</a>
    <a href="/audit" id="a8">Audit Logs</a>
    <button id="a9" data-qa="user-profile-menu">Profile</button>
    <button id="a10" style="color:red;">Sign Out</button>
</nav>

<div class="widget">
    <h3>Monthly Recurring Revenue</h3>
    <div id="a11" class="metric-value">$45,200</div>
    <button id="a12">Download Report</button>
</div>
<div class="widget">
    <h3>Active Users</h3><span id="a13">1,240</span>
    <button id="a14" aria-label="Refresh Data">🔄</button>
</div>
<button id="a15">Export to CSV</button>
<button id="a16">Export to PDF</button>
<div role="button" id="a17">Customize Dashboard</div>
<select id="a18"><option>Last 7 days</option><option>Last 30 days</option></select>
<button id="a19">Add Widget</button>
<div id="a20" class="alert alert-warning">Server load high <button id="close_alert">x</button></div>

<div class="filters">
    <input type="text" id="a21" placeholder="Search users by email...">
    <select id="a22" aria-label="Filter by Status"><option>All</option><option>Active</option><option>Suspended</option></select>
    <select id="a23" aria-label="Filter by Role"><option>All</option><option>Admin</option><option>Editor</option></select>
    <input type="date" id="a24" aria-label="Start Date">
    <input type="date" id="a25" aria-label="End Date">
    <button id="a26" class="btn-primary">Apply Filters</button>
    <button id="a27" class="btn-ghost">Clear Filters</button>
    <button id="a28" aria-label="Advanced Search">⚙️</button>
    <input type="checkbox" id="a29"><label for="a29">Show deleted records</label>
    <button id="a30">Save View</button>
</div>

<table id="users_table">
    <thead>
        <tr>
            <th><input type="checkbox" id="a31" aria-label="Select All Rows"></th>
            <th>Name <button id="a32" aria-label="Sort Ascending">↑</button></th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><input type="checkbox" id="a33" aria-label="Select Alice"></td>
            <td>Alice Smith</td>
            <td>alice@corp.com</td>
            <td id="a34">Admin</td>
            <td><span class="badge badge-success" id="a35">Active</span></td>
            <td>
                <button id="a36" aria-label="Edit Alice">✏️</button>
                <button id="a37" aria-label="Suspend Alice">🛑</button>
                <div role="button" id="a38" aria-label="More actions for Alice">•••</div>
            </td>
        </tr>
    </tbody>
</table>
<button id="a39" disabled>Bulk Delete</button>
<button id="a40">Bulk Export</button>

<div class="pagination">
    <span id="a41">Showing 1 to 10 of 500 entries</span>
    <button id="a42" disabled>Previous</button>
    <button id="a43">1</button>
    <button id="a44">2</button>
    <button id="a45">3</button>
    <button id="a46">Next</button>
    <button id="a47">Last</button>
    <select id="a48" aria-label="Rows per page"><option>10</option><option>50</option><option>100</option></select>
    <input type="number" id="a49" placeholder="Go to page" style="width:50px;">
    <button id="a50">Go</button>
</div>

<button id="a51">Invite User</button>
<div class="modal" id="invite_modal">
    <h2>Invite New Team Member</h2>
    <input type="email" id="a52" placeholder="colleague@company.com">
    <div role="radiogroup">
        <label><input type="radio" name="role" id="a53"> Admin</label>
        <label><input type="radio" name="role" id="a54"> Editor</label>
        <label><input type="radio" name="role" id="a55" checked> Viewer</label>
    </div>
    <select id="a56" aria-label="Assign to Department"><option>Engineering</option><option>Marketing</option></select>
    <input type="checkbox" id="a57"><label for="a57">Send welcome email</label>
    <button id="a58" class="btn-success">Send Invitation</button>
    <button id="a59" class="btn-cancel">Cancel</button>
    <button id="a60" aria-label="Close Modal">X</button>
</div>

<button id="a61">Generate New API Key</button>
<input type="text" id="a62" placeholder="Key Name (e.g. Production)">
<button id="a63">Create Key</button>
<div class="key-display">
    <input type="password" id="a64" value="sk_live_123456789" readonly>
    <button id="a65" aria-label="Reveal API Key">👁️</button>
    <button id="a66" aria-label="Copy API Key">📋</button>
</div>
<button id="a67" style="color:red;">Revoke Key</button>
<button id="a68">Add Webhook</button>
<input type="url" id="a69" placeholder="https://your-domain.com/webhook">
<div role="switch" id="a70" aria-checked="true" aria-label="Enable Webhook"></div>

<div class="plan-card">
    <h3>Pro Plan</h3>
    <button id="a71">Upgrade to Enterprise</button>
</div>
<button id="a72">Add Payment Method</button>
<input type="text" id="a73" placeholder="Cardholder Name">
<button id="a74">Save Card</button>
<button id="a75">Download Invoices</button>
<button id="a76">Update Billing Email</button>
<input type="text" id="a77" placeholder="Tax ID / VAT">
<button id="a78" class="btn-danger">Cancel Subscription</button>
<a href="/terms" id="a79">Terms of Service</a>
<div id="a80" role="button">Contact Sales</div>

<input type="text" id="a81" value="Acme Corp" aria-label="Workspace Name">
<input type="file" id="a82" aria-label="Upload Logo">
<select id="a83" aria-label="Timezone"><option>UTC</option><option>EST</option></select>
<div role="switch" id="a84" aria-label="Require MFA for all users"></div>
<button id="a85">Save Workspace Settings</button>
<button id="a86">Transfer Ownership</button>
<input type="text" id="a87" placeholder="Transfer to email">
<select id="a88" aria-label="Language"><option>English</option><option>Ukrainian</option></select>
<button id="a89">Sync Directory</button>
<button id="a90">Clear Workspace Cache</button>

<div class="danger-zone">
    <h3>Danger Zone</h3>
    <button id="a91" style="background:red; color:white;">Delete Workspace</button>
    <input type="text" id="a92" placeholder="Type workspace name to confirm">
    <button id="a93" disabled>Confirm Deletion</button>
</div>
<div class="tooltip" id="a94">Hover me for info</div>
<input type="text" id="a95" value="Cannot edit this" disabled>
<input type="text" id="a96" value="Readonly data" readonly>
<div role="menuitem" id="a97">Quick Action 1</div>
<div role="menuitem" id="a98">Quick Action 2</div>
<div aria-label="Progress: 75%" id="a99" role="progressbar"></div>
<button id="a100" style="display:none;">Easter Egg Button</button>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Sidebar
    {"n": "1", "step": "Click 'Dashboard'", "m": "clickable", "st": ["Dashboard"], "tf": None, "exp": "a1"},
    {"n": "2", "step": "Click 'User Management'", "m": "clickable", "st": ["User Management"], "tf": None, "exp": "a2"},
    {"n": "3", "step": "Click 'Billing & Plans'", "m": "clickable", "st": ["Billing & Plans"], "tf": None, "exp": "a3"},
    {"n": "4", "step": "Click 'Workspace Settings'", "m": "clickable", "st": ["Workspace Settings"], "tf": None, "exp": "a4"},
    {"n": "5", "step": "Click 'Collapse Sidebar'", "m": "clickable", "st": ["Collapse Sidebar"], "tf": None, "exp": "a5"},
    {"n": "6", "step": "Click 'Help & Support'", "m": "clickable", "st": ["Help & Support"], "tf": None, "exp": "a6"},
    {"n": "7", "step": "Click 'API Keys'", "m": "clickable", "st": ["API Keys"], "tf": None, "exp": "a7"},
    {"n": "8", "step": "Click 'Audit Logs'", "m": "clickable", "st": ["Audit Logs"], "tf": None, "exp": "a8"},
    {"n": "9", "step": "Click 'Profile'", "m": "clickable", "st": ["Profile"], "tf": None, "exp": "a9"},
    {"n": "10", "step": "Click 'Sign Out'", "m": "clickable", "st": ["Sign Out"], "tf": None, "exp": "a10"},

    # Widgets
    {"n": "11", "step": "EXTRACT MRR into {mrr}", "ex": True, "var": "mrr", "val": "$45,200"},
    {"n": "12", "step": "Click 'Download Report'", "m": "clickable", "st": ["Download Report"], "tf": None, "exp": "a12"},
    {"n": "13", "step": "EXTRACT Active Users into {au}", "ex": True, "var": "au", "val": "1,240"},
    {"n": "14", "step": "Click 'Refresh Data'", "m": "clickable", "st": ["Refresh Data"], "tf": None, "exp": "a14"},
    {"n": "15", "step": "Click 'Export to CSV'", "m": "clickable", "st": ["Export to CSV"], "tf": None, "exp": "a15"},
    {"n": "16", "step": "Click 'Export to PDF'", "m": "clickable", "st": ["Export to PDF"], "tf": None, "exp": "a16"},
    {"n": "17", "step": "Click 'Customize Dashboard'", "m": "clickable", "st": ["Customize Dashboard"], "tf": None, "exp": "a17"},
    {"n": "18", "step": "Select 'Last 30 days' from dropdown", "m": "select", "st": ["Last 30 days"], "tf": None, "exp": "a18"},
    {"n": "19", "step": "Click 'Add Widget'", "m": "clickable", "st": ["Add Widget"], "tf": None, "exp": "a19"},
    {"n": "20", "step": "VERIFY that 'Server load high' is present", "ver": True, "res": True},

    # Filters
    {"n": "21", "step": "Fill 'Search users' with 'admin@'", "m": "input", "st": ["Search users"], "tf": "search users", "exp": "a21"},
    {"n": "22", "step": "Select 'Active' from 'Status'", "m": "select", "st": ["Active", "Status"], "tf": None, "exp": "a22"},
    {"n": "23", "step": "Select 'Admin' from 'Role'", "m": "select", "st": ["Admin", "Role"], "tf": None, "exp": "a23"},
    {"n": "24", "step": "Fill 'Start Date' with '01/01/2026'", "m": "input", "st": ["Start Date"], "tf": "start date", "exp": "a24"},
    {"n": "25", "step": "Fill 'End Date' with '01/31/2026'", "m": "input", "st": ["End Date"], "tf": "end date", "exp": "a25"},
    {"n": "26", "step": "Click 'Apply Filters'", "m": "clickable", "st": ["Apply Filters"], "tf": None, "exp": "a26"},
    {"n": "27", "step": "Click 'Clear Filters'", "m": "clickable", "st": ["Clear Filters"], "tf": None, "exp": "a27"},
    {"n": "28", "step": "Click 'Advanced Search'", "m": "clickable", "st": ["Advanced Search"], "tf": None, "exp": "a28"},
    {"n": "29", "step": "Check 'Show deleted records'", "m": "clickable", "st": ["Show deleted records"], "tf": None, "exp": "a29"},
    {"n": "30", "step": "Click 'Save View'", "m": "clickable", "st": ["Save View"], "tf": None, "exp": "a30"},

    # Table
    {"n": "31", "step": "Check 'Select All Rows'", "m": "clickable", "st": ["Select All Rows"], "tf": None, "exp": "a31"},
    {"n": "32", "step": "Click 'Sort Ascending'", "m": "clickable", "st": ["Sort Ascending"], "tf": None, "exp": "a32"},
    {"n": "33", "step": "Check 'Select Alice'", "m": "clickable", "st": ["Select Alice"], "tf": None, "exp": "a33"},
    {"n": "34", "step": "EXTRACT Role of 'Alice' into {r}", "ex": True, "var": "r", "val": "Admin"},
    {"n": "35", "step": "EXTRACT Status of 'Alice' into {s}", "ex": True, "var": "s", "val": "Active"},
    {"n": "36", "step": "Click 'Edit Alice'", "m": "clickable", "st": ["Edit Alice"], "tf": None, "exp": "a36"},
    {"n": "37", "step": "Click 'Suspend Alice'", "m": "clickable", "st": ["Suspend Alice"], "tf": None, "exp": "a37"},
    {"n": "38", "step": "Click 'More actions for Alice'", "m": "clickable", "st": ["More actions for Alice"], "tf": None, "exp": "a38"},
    {"n": "39", "step": "VERIFY 'Bulk Delete' is disabled", "ver": True, "step": "VERIFY that 'Bulk Delete' is DISABLED", "res": True},
    {"n": "40", "step": "Click 'Bulk Export'", "m": "clickable", "st": ["Bulk Export"], "tf": None, "exp": "a40"},

    # Pagination
    {"n": "41", "step": "VERIFY 'Showing 1 to 10' is present", "ver": True, "res": True},
    {"n": "42", "step": "VERIFY 'Previous' is disabled", "ver": True, "step": "VERIFY that 'Previous' is DISABLED", "res": True},
    {"n": "43", "step": "Click '1'", "m": "clickable", "st": ["1"], "tf": None, "exp": "a43"},
    {"n": "44", "step": "Click '2'", "m": "clickable", "st": ["2"], "tf": None, "exp": "a44"},
    {"n": "45", "step": "Click '3'", "m": "clickable", "st": ["3"], "tf": None, "exp": "a45"},
    {"n": "46", "step": "Click 'Next'", "m": "clickable", "st": ["Next"], "tf": None, "exp": "a46"},
    {"n": "47", "step": "Click 'Last'", "m": "clickable", "st": ["Last"], "tf": None, "exp": "a47"},
    {"n": "48", "step": "Select '50' from 'Rows per page'", "m": "select", "st": ["50", "Rows per page"], "tf": None, "exp": "a48"},
    {"n": "49", "step": "Fill 'Go to page' with '5'", "m": "input", "st": ["Go to page"], "tf": "go to page", "exp": "a49"},
    {"n": "50", "step": "Click 'Go'", "m": "clickable", "st": ["Go"], "tf": None, "exp": "a50"},

    # Invite Modal
    {"n": "51", "step": "Click 'Invite User'", "m": "clickable", "st": ["Invite User"], "tf": None, "exp": "a51"},
    {"n": "52", "step": "Fill 'colleague@' with 'test@test.com'", "m": "input", "st": ["colleague@"], "tf": "colleague@", "exp": "a52"},
    {"n": "53", "step": "Click radio 'Admin'", "m": "clickable", "st": ["Admin"], "tf": None, "exp": "a53"},
    {"n": "54", "step": "Click radio 'Editor'", "m": "clickable", "st": ["Editor"], "tf": None, "exp": "a54"},
    {"n": "55", "step": "VERIFY 'Viewer' is checked", "ver": True, "step": "VERIFY that 'Viewer' is checked", "res": True},
    {"n": "56", "step": "Select 'Marketing' from 'Department'", "m": "select", "st": ["Marketing", "Department"], "tf": None, "exp": "a56"},
    {"n": "57", "step": "Check 'Send welcome email'", "m": "clickable", "st": ["Send welcome email"], "tf": None, "exp": "a57"},
    {"n": "58", "step": "Click 'Send Invitation'", "m": "clickable", "st": ["Send Invitation"], "tf": None, "exp": "a58"},
    {"n": "59", "step": "Click 'Cancel'", "m": "clickable", "st": ["Cancel"], "tf": None, "exp": "a59"},
    {"n": "60", "step": "Click 'Close Modal'", "m": "clickable", "st": ["Close Modal"], "tf": None, "exp": "a60"},

    # API Keys
    {"n": "61", "step": "Click 'Generate New API Key'", "m": "clickable", "st": ["Generate New API Key"], "tf": None, "exp": "a61"},
    {"n": "62", "step": "Fill 'Key Name' with 'Test'", "m": "input", "st": ["Key Name"], "tf": "key name", "exp": "a62"},
    {"n": "63", "step": "Click 'Create Key'", "m": "clickable", "st": ["Create Key"], "tf": None, "exp": "a63"},
    {"n": "64", "step": "EXTRACT API Key value into {k}", "ex": True, "var": "k", "val": "sk_live_123456789"}, # Value extract via HTML works? Test it!
    {"n": "65", "step": "Click 'Reveal API Key'", "m": "clickable", "st": ["Reveal API Key"], "tf": None, "exp": "a65"},
    {"n": "66", "step": "Click 'Copy API Key'", "m": "clickable", "st": ["Copy API Key"], "tf": None, "exp": "a66"},
    {"n": "67", "step": "Click 'Revoke Key'", "m": "clickable", "st": ["Revoke Key"], "tf": None, "exp": "a67"},
    {"n": "68", "step": "Click 'Add Webhook'", "m": "clickable", "st": ["Add Webhook"], "tf": None, "exp": "a68"},
    {"n": "69", "step": "Fill 'https://' with 'url'", "m": "input", "st": ["https://"], "tf": "https://", "exp": "a69"},
    {"n": "70", "step": "Click 'Enable Webhook' switch", "m": "clickable", "st": ["Enable Webhook"], "tf": None, "exp": "a70"},

    # Billing
    {"n": "71", "step": "Click 'Upgrade to Enterprise'", "m": "clickable", "st": ["Upgrade to Enterprise"], "tf": None, "exp": "a71"},
    {"n": "72", "step": "Click 'Add Payment Method'", "m": "clickable", "st": ["Add Payment Method"], "tf": None, "exp": "a72"},
    {"n": "73", "step": "Fill 'Cardholder Name' with 'Oleksii'", "m": "input", "st": ["Cardholder Name"], "tf": "cardholder name", "exp": "a73"},
    {"n": "74", "step": "Click 'Save Card'", "m": "clickable", "st": ["Save Card"], "tf": None, "exp": "a74"},
    {"n": "75", "step": "Click 'Download Invoices'", "m": "clickable", "st": ["Download Invoices"], "tf": None, "exp": "a75"},
    {"n": "76", "step": "Click 'Update Billing Email'", "m": "clickable", "st": ["Update Billing Email"], "tf": None, "exp": "a76"},
    {"n": "77", "step": "Fill 'Tax ID' with 'UA123'", "m": "input", "st": ["Tax ID"], "tf": "tax id", "exp": "a77"},
    {"n": "78", "step": "Click 'Cancel Subscription'", "m": "clickable", "st": ["Cancel Subscription"], "tf": None, "exp": "a78"},
    {"n": "79", "step": "Click 'Terms of Service'", "m": "clickable", "st": ["Terms of Service"], "tf": None, "exp": "a79"},
    {"n": "80", "step": "Click 'Contact Sales'", "m": "clickable", "st": ["Contact Sales"], "tf": None, "exp": "a80"},

    # Settings
    {"n": "81", "step": "Fill 'Workspace Name' with 'Manul Labs'", "m": "input", "st": ["Workspace Name"], "tf": "workspace name", "exp": "a81"},
    {"n": "82", "step": "Click 'Upload Logo'", "m": "clickable", "st": ["Upload Logo"], "tf": None, "exp": "a82"},
    {"n": "83", "step": "Select 'EST' from 'Timezone'", "m": "select", "st": ["EST", "Timezone"], "tf": None, "exp": "a83"},
    {"n": "84", "step": "Click 'Require MFA' switch", "m": "clickable", "st": ["Require MFA"], "tf": None, "exp": "a84"},
    {"n": "85", "step": "Click 'Save Workspace Settings'", "m": "clickable", "st": ["Save Workspace Settings"], "tf": None, "exp": "a85"},
    {"n": "86", "step": "Click 'Transfer Ownership'", "m": "clickable", "st": ["Transfer Ownership"], "tf": None, "exp": "a86"},
    {"n": "87", "step": "Fill 'Transfer to email' with 'boss@'", "m": "input", "st": ["Transfer to email"], "tf": "transfer to email", "exp": "a87"},
    {"n": "88", "step": "Select 'Ukrainian' from 'Language'", "m": "select", "st": ["Ukrainian", "Language"], "tf": None, "exp": "a88"},
    {"n": "89", "step": "Click 'Sync Directory'", "m": "clickable", "st": ["Sync Directory"], "tf": None, "exp": "a89"},
    {"n": "90", "step": "Click 'Clear Workspace Cache'", "m": "clickable", "st": ["Clear Workspace Cache"], "tf": None, "exp": "a90"},

    # Danger Zone
    {"n": "91", "step": "Click 'Delete Workspace'", "m": "clickable", "st": ["Delete Workspace"], "tf": None, "exp": "a91"},
    {"n": "92", "step": "Fill 'Type workspace name' with 'Acme Corp'", "m": "input", "st": ["Type workspace name"], "tf": "type workspace name", "exp": "a92"},
    {"n": "93", "step": "VERIFY 'Confirm Deletion' is disabled", "ver": True, "step": "VERIFY that 'Confirm Deletion' is disabled", "res": True},
    {"n": "94", "step": "HOVER over 'Hover me for info'", "m": "hover", "st": ["Hover me for info"], "tf": None, "exp": "a94", "execute_step": True},
    {"n": "95", "step": "VERIFY 'Cannot edit this' is disabled", "ver": True, "step": "VERIFY that 'Cannot edit this' is disabled", "res": True},
    {"n": "96", "step": "Fill 'Readonly data' with 'hacked'", "m": "input", "st": ["Readonly data"], "tf": "readonly data", "exp": "a96", "execute_step": True},
    {"n": "97", "step": "Click 'Quick Action 1'", "m": "clickable", "st": ["Quick Action 1"], "tf": None, "exp": "a97"},
    {"n": "98", "step": "Click 'Quick Action 2'", "m": "clickable", "st": ["Quick Action 2"], "tf": None, "exp": "a98"},
    {"n": "99", "step": "VERIFY 'Progress: 75%' is present", "ver": True, "res": True},
    {"n": "100", "step": "Click 'Easter Egg Button' if exists", "m": "clickable", "st": ["Easter Egg Button"], "tf": None, "exp": None},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("⚙️ SAAS & DASHBOARDS HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(SAAS_DOM)

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