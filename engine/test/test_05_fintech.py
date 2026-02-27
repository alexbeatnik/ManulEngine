import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Fintech, Banking & Crypto (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
FINTECH_DOM = """
<!DOCTYPE html><html><head><style>
.hidden { display: none; }
.card-block { border: 1px solid #ccc; padding: 10px; }
.blurred { filter: blur(4px); }
</style></head><body>

<div class="dashboard">
    <h2>Total Balance</h2>
    <h1 id="f1" class="blurred">$124,500.00</h1>
    <button id="f2" aria-label="Reveal Balance">👁️</button>
    <div class="account-list">
        <span>Checking</span><span id="f3">$5,000.00</span>
        <span>Savings</span><span id="f4">$119,500.00</span>
    </div>
    <button id="f5">Add Funds</button>
    <button id="f6">Withdraw</button>
    <button id="f7" data-testid="quick-xfer">Quick Transfer</button>
    <a href="/statements" id="f8">Download Statements</a>
    <div role="switch" id="f9" aria-checked="false">Hide zero balances</div>
    <button id="f10" aria-label="Account Settings">⚙️</button>
</div>

<div class="transfer-form">
    <input type="text" id="f11" placeholder="Recipient Name or IBAN">
    <input type="number" id="f12" aria-label="Amount to Send">
    <select id="f13" aria-label="Currency"><option>USD</option><option>EUR</option><option>GBP</option></select>
    <input type="text" id="f14" placeholder="Reference / Message">
    <label><input type="radio" name="speed" id="f15" checked> Standard (Free)</label>
    <label><input type="radio" name="speed" id="f16"> Instant ($1.50)</label>
    <button id="f17" class="btn-primary">Review Transfer</button>
    <button id="f18" class="btn-secondary">Save as Template</button>
    <button id="f19">Schedule for later</button>
    <button id="f20" style="display:none;">Cancel Transfer</button>
</div>

<div class="crypto-terminal">
    <div class="pair-selector">
        <span id="f21">BTC/USDT</span> <button id="f22">Change Pair</button>
    </div>
    <div class="trade-tabs">
        <button id="f23" class="active">Buy</button>
        <button id="f24">Sell</button>
    </div>
    <select id="f25" aria-label="Order Type"><option>Market</option><option>Limit</option></select>
    <input type="number" id="f26" placeholder="Price (USDT)">
    <input type="number" id="f27" placeholder="Amount (BTC)">
    <input type="range" id="f28" min="1" max="100" aria-label="Leverage Slider">
    <button id="f29" style="background:green;">Execute Buy</button>
    <div id="f30" class="fee-display">Est. Fee: 0.1%</div>
</div>

<table id="tx_table">
    <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead>
    <tbody>
        <tr>
            <td>2026-02-25</td>
            <td>Coffee Shop</td>
            <td id="f31">-$4.50</td>
            <td id="f32">Completed</td>
            <td><button id="f33">Dispute</button></td>
        </tr>
        <tr>
            <td>2026-02-24</td>
            <td>Salary</td>
            <td id="f34">+$5,000.00</td>
            <td id="f35">Pending</td>
            <td><button id="f36">View Receipt</button></td>
        </tr>
    </tbody>
</table>
<button id="f37">Load More Transactions</button>
<input type="text" id="f38" placeholder="Search transactions">
<button id="f39">Export to CSV</button>
<button id="f40">Export to PDF</button>

<div class="security-module">
    <input type="password" id="f41" placeholder="Enter Current PIN">
    <input type="password" id="f42" placeholder="Enter New PIN">
    <input type="password" id="f43" placeholder="Confirm New PIN">
    <button id="f44">Update PIN</button>
    <input type="text" id="f45" placeholder="6-digit OTP Code" maxlength="6">
    <button id="f46">Verify OTP</button>
    <button id="f47">Resend SMS</button>
    <div role="switch" id="f48" aria-checked="true">Enable FaceID</div>
    <button id="f49">Register Hardware Key</button>
    <button id="f50" class="btn-danger">Lock Account</button>
</div>

<div class="cards-section">
    <div class="card-display">**** **** **** <span id="f51">1234</span></div>
    <button id="f52">Show Card Details</button>
    <button id="f53" aria-label="Copy Card Number">📋</button>
    <div role="switch" id="f54" aria-checked="false">Freeze Card</div>
    <button id="f55">Report Lost/Stolen</button>
    <button id="f56">Change Limits</button>
    <input type="number" id="f57" placeholder="Daily Limit" value="1000">
    <button id="f58">Save Limits</button>
    <button id="f59">Create Virtual Card</button>
    <div role="switch" id="f60" aria-checked="true">Online Purchases</div>
</div>

<div class="profile-form">
    <input type="text" id="f61" placeholder="Legal Name">
    <input type="date" id="f62" aria-label="Date of Birth">
    <input type="text" id="f63" placeholder="Residential Address">
    <button id="f64">Verify Identity (KYC)</button>
    <select id="f65" aria-label="Account Tier"><option>Standard</option><option>Premium</option><option>Metal</option></select>
    <div class="risk-tolerance">
        <label><input type="radio" name="risk" id="f66"> Low Risk</label>
        <label><input type="radio" name="risk" id="f67"> Medium Risk</label>
        <label><input type="radio" name="risk" id="f68"> High Risk</label>
    </div>
    <button id="f69">Save Profile</button>
    <a href="/tax" id="f70">Tax Documents</a>
</div>

<div class="loan-widget">
    <h3>Personal Loan</h3>
    <input type="range" id="f71" min="1000" max="50000" aria-label="Loan Amount">
    <div id="f72">$10,000</div>
    <select id="f73" aria-label="Term"><option>12 Months</option><option>24 Months</option></select>
    <div>Interest Rate: <span id="f74">5.99%</span></div>
    <div>Monthly Payment: <span id="f75">$860.00</span></div>
    <button id="f76">Apply for Loan</button>
    <button id="f77">View Amortization Schedule</button>
    <input type="checkbox" id="f78"><label for="f78">Include Payment Protection</label>
    <button id="f79">Pay Early</button>
    <div id="f80">Credit Score: 750</div>
</div>

<div class="invest-section">
    <button id="f81">Create Portfolio</button>
    <input type="text" id="f82" placeholder="Ticker (e.g. AAPL)">
    <button id="f83">Search Asset</button>
    <div role="switch" id="f84" aria-checked="true">Auto-Invest</div>
    <input type="number" id="f85" placeholder="Auto-deposit amount">
    <select id="f86" aria-label="Frequency"><option>Weekly</option><option>Monthly</option></select>
    <button id="f87">Confirm Auto-Invest</button>
    <button id="f88">Rebalance Portfolio</button>
    <div id="f89">YTD Return: +12.4%</div>
    <button id="f90">Withdraw Funds</button>
</div>

<div class="modal" id="timeout_modal">
    <h3>Session Expiring</h3>
    <button id="f91">Stay Logged In</button>
    <button id="f92">Log Out Now</button>
</div>
<div class="toast">
    <span id="f93">Transfer Successful</span>
    <button id="f94" aria-label="Dismiss Alert">X</button>
</div>
<button id="f95" class="confirm-transfer">Confirm</button>
<button id="f96" class="confirm-delete" style="color:red;">Confirm</button>
<button id="f97" class="confirm-generic">Confirm</button>
<div id="f98" role="button" tabindex="0">Acknowledge Risk</div>
<input type="checkbox" id="f99"><label for="f99">I agree to the updated terms</label>
<button id="f100" disabled>Finalize</button>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Dashboard & Balances (1-10)
    {"n": "1", "step": "EXTRACT Total Balance into {tb}", "ex": True, "var": "tb", "val": "$124,500.00"},
    {"n": "2", "step": "Click 'Reveal Balance'", "m": "clickable", "st": ["Reveal Balance"], "tf": None, "exp": "f2"},
    {"n": "3", "step": "EXTRACT Checking balance into {cb}", "ex": True, "var": "cb", "val": "$5,000.00"},
    {"n": "4", "step": "EXTRACT Savings balance into {sb}", "ex": True, "var": "sb", "val": "$119,500.00"},
    {"n": "5", "step": "Click 'Add Funds'", "m": "clickable", "st": ["Add Funds"], "tf": None, "exp": "f5"},
    {"n": "6", "step": "Click 'Withdraw'", "m": "clickable", "st": ["Withdraw"], "tf": None, "exp": "f6"},
    {"n": "7", "step": "Click 'Quick Transfer'", "m": "clickable", "st": ["Quick Transfer"], "tf": None, "exp": "f7"},
    {"n": "8", "step": "Click 'Download Statements'", "m": "clickable", "st": ["Download Statements"], "tf": None, "exp": "f8"},
    {"n": "9", "step": "Click 'Hide zero balances' switch", "m": "clickable", "st": ["Hide zero balances"], "tf": None, "exp": "f9"},
    {"n": "10", "step": "Click 'Account Settings'", "m": "clickable", "st": ["Account Settings"], "tf": None, "exp": "f10"},

    # Transfer & Send Money (11-20)
    {"n": "11", "step": "Fill 'Recipient Name or IBAN' with 'UA12345'", "m": "input", "st": ["Recipient Name or IBAN"], "tf": "recipient name or iban", "exp": "f11"},
    {"n": "12", "step": "Fill 'Amount to Send' with '500'", "m": "input", "st": ["Amount to Send"], "tf": "amount to send", "exp": "f12"},
    {"n": "13", "step": "Select 'EUR' from 'Currency'", "m": "select", "st": ["EUR", "Currency"], "tf": None, "exp": "f13"},
    {"n": "14", "step": "Fill 'Reference' with 'Rent'", "m": "input", "st": ["Reference"], "tf": "reference", "exp": "f14"},
    {"n": "15", "step": "Click radio 'Standard (Free)'", "m": "clickable", "st": ["Standard (Free)"], "tf": None, "exp": "f15"},
    {"n": "16", "step": "Click radio 'Instant'", "m": "clickable", "st": ["Instant"], "tf": None, "exp": "f16"},
    {"n": "17", "step": "Click 'Review Transfer'", "m": "clickable", "st": ["Review Transfer"], "tf": None, "exp": "f17"},
    {"n": "18", "step": "Click 'Save as Template'", "m": "clickable", "st": ["Save as Template"], "tf": None, "exp": "f18"},
    {"n": "19", "step": "Click 'Schedule for later'", "m": "clickable", "st": ["Schedule for later"], "tf": None, "exp": "f19"},
    {"n": "20", "step": "Click 'Cancel Transfer' if exists", "m": "clickable", "st": ["Cancel Transfer"], "tf": None, "exp": None}, # Hidden

    # Crypto Terminal (21-30)
    {"n": "21", "step": "EXTRACT Crypto pair into {pair}", "ex": True, "var": "pair", "val": "BTC/USDT"},
    {"n": "22", "step": "Click 'Change Pair'", "m": "clickable", "st": ["Change Pair"], "tf": None, "exp": "f22"},
    {"n": "23", "step": "Click 'Buy' tab", "m": "clickable", "st": ["Buy"], "tf": None, "exp": "f23"},
    {"n": "24", "step": "Click 'Sell' tab", "m": "clickable", "st": ["Sell"], "tf": None, "exp": "f24"},
    {"n": "25", "step": "Select 'Limit' from 'Order Type'", "m": "select", "st": ["Limit", "Order Type"], "tf": None, "exp": "f25"},
    {"n": "26", "step": "Fill 'Price (USDT)' with '90000'", "m": "input", "st": ["Price (USDT)"], "tf": "price (usdt)", "exp": "f26"},
    {"n": "27", "step": "Fill 'Amount (BTC)' with '0.1'", "m": "input", "st": ["Amount (BTC)"], "tf": "amount (btc)", "exp": "f27"},
    {"n": "28", "step": "Fill 'Leverage Slider' with '10'", "m": "input", "st": ["Leverage Slider"], "tf": "leverage slider", "exp": "f28"},
    {"n": "29", "step": "Click 'Execute Buy'", "m": "clickable", "st": ["Execute Buy"], "tf": None, "exp": "f29"},
    {"n": "30", "step": "VERIFY that 'Est. Fee: 0.1%' is present", "ver": True, "res": True},

    # Transaction History (31-40)
    {"n": "31", "step": "EXTRACT Coffee Shop amount into {amt}", "ex": True, "var": "amt", "val": "-$4.50"},
    {"n": "32", "step": "EXTRACT Coffee Shop status into {stat}", "ex": True, "var": "stat", "val": "Completed"},
    {"n": "33", "step": "Click 'Dispute'", "m": "clickable", "st": ["Dispute"], "tf": None, "exp": "f33"},
    {"n": "34", "step": "EXTRACT Salary amount into {sal}", "ex": True, "var": "sal", "val": "+$5,000.00"},
    {"n": "35", "step": "EXTRACT Salary status into {sstat}", "ex": True, "var": "sstat", "val": "Pending"},
    {"n": "36", "step": "Click 'View Receipt'", "m": "clickable", "st": ["View Receipt"], "tf": None, "exp": "f36"},
    {"n": "37", "step": "Click 'Load More Transactions'", "m": "clickable", "st": ["Load More Transactions"], "tf": None, "exp": "f37"},
    {"n": "38", "step": "Fill 'Search transactions' with 'Uber'", "m": "input", "st": ["Search transactions"], "tf": "search transactions", "exp": "f38"},
    {"n": "39", "step": "Click 'Export to CSV'", "m": "clickable", "st": ["Export to CSV"], "tf": None, "exp": "f39"},
    {"n": "40", "step": "Click 'Export to PDF'", "m": "clickable", "st": ["Export to PDF"], "tf": None, "exp": "f40"},

    # Security & 2FA (41-50)
    {"n": "41", "step": "Fill 'Enter Current PIN' with '1111'", "m": "input", "st": ["Enter Current PIN"], "tf": "enter current pin", "exp": "f41"},
    {"n": "42", "step": "Fill 'Enter New PIN' with '2222'", "m": "input", "st": ["Enter New PIN"], "tf": "enter new pin", "exp": "f42"},
    {"n": "43", "step": "Fill 'Confirm New PIN' with '2222'", "m": "input", "st": ["Confirm New PIN"], "tf": "confirm new pin", "exp": "f43"},
    {"n": "44", "step": "Click 'Update PIN'", "m": "clickable", "st": ["Update PIN"], "tf": None, "exp": "f44"},
    {"n": "45", "step": "Fill 'OTP Code' with '654321'", "m": "input", "st": ["OTP Code"], "tf": "otp code", "exp": "f45"},
    {"n": "46", "step": "Click 'Verify OTP'", "m": "clickable", "st": ["Verify OTP"], "tf": None, "exp": "f46"},
    {"n": "47", "step": "Click 'Resend SMS'", "m": "clickable", "st": ["Resend SMS"], "tf": None, "exp": "f47"},
    {"n": "48", "step": "Click 'Enable FaceID' switch", "m": "clickable", "st": ["Enable FaceID"], "tf": None, "exp": "f48"},
    {"n": "49", "step": "Click 'Register Hardware Key'", "m": "clickable", "st": ["Register Hardware Key"], "tf": None, "exp": "f49"},
    {"n": "50", "step": "Click 'Lock Account'", "m": "clickable", "st": ["Lock Account"], "tf": None, "exp": "f50"},

    # Cards Management (51-60)
    {"n": "51", "step": "EXTRACT card ending into {end}", "ex": True, "var": "end", "val": "1234"},
    {"n": "52", "step": "Click 'Show Card Details'", "m": "clickable", "st": ["Show Card Details"], "tf": None, "exp": "f52"},
    {"n": "53", "step": "Click 'Copy Card Number'", "m": "clickable", "st": ["Copy Card Number"], "tf": None, "exp": "f53"},
    {"n": "54", "step": "Click 'Freeze Card'", "m": "clickable", "st": ["Freeze Card"], "tf": None, "exp": "f54"},
    {"n": "55", "step": "Click 'Report Lost/Stolen'", "m": "clickable", "st": ["Report Lost/Stolen"], "tf": None, "exp": "f55"},
    {"n": "56", "step": "Click 'Change Limits'", "m": "clickable", "st": ["Change Limits"], "tf": None, "exp": "f56"},
    {"n": "57", "step": "Fill 'Daily Limit' with '500'", "m": "input", "st": ["Daily Limit"], "tf": "daily limit", "exp": "f57"},
    {"n": "58", "step": "Click 'Save Limits'", "m": "clickable", "st": ["Save Limits"], "tf": None, "exp": "f58"},
    {"n": "59", "step": "Click 'Create Virtual Card'", "m": "clickable", "st": ["Create Virtual Card"], "tf": None, "exp": "f59"},
    {"n": "60", "step": "Click 'Online Purchases'", "m": "clickable", "st": ["Online Purchases"], "tf": None, "exp": "f60"},

    # Settings & Profile (61-70)
    {"n": "61", "step": "Fill 'Legal Name' with 'Oleksii'", "m": "input", "st": ["Legal Name"], "tf": "legal name", "exp": "f61"},
    {"n": "62", "step": "Fill 'Date of Birth' with '1990-01-01'", "m": "input", "st": ["Date of Birth"], "tf": "date of birth", "exp": "f62"},
    {"n": "63", "step": "Fill 'Residential Address' with 'Kyiv'", "m": "input", "st": ["Residential Address"], "tf": "residential address", "exp": "f63"},
    {"n": "64", "step": "Click 'Verify Identity (KYC)'", "m": "clickable", "st": ["Verify Identity (KYC)"], "tf": None, "exp": "f64"},
    {"n": "65", "step": "Select 'Metal' from 'Account Tier'", "m": "select", "st": ["Metal", "Account Tier"], "tf": None, "exp": "f65"},
    {"n": "66", "step": "Click radio 'Low Risk'", "m": "clickable", "st": ["Low Risk"], "tf": None, "exp": "f66"},
    {"n": "67", "step": "Click radio 'Medium Risk'", "m": "clickable", "st": ["Medium Risk"], "tf": None, "exp": "f67"},
    {"n": "68", "step": "Click radio 'High Risk'", "m": "clickable", "st": ["High Risk"], "tf": None, "exp": "f68"},
    {"n": "69", "step": "Click 'Save Profile'", "m": "clickable", "st": ["Save Profile"], "tf": None, "exp": "f69"},
    {"n": "70", "step": "Click 'Tax Documents'", "m": "clickable", "st": ["Tax Documents"], "tf": None, "exp": "f70"},

    # Loans & Credit (71-80)
    {"n": "71", "step": "Fill 'Loan Amount' with '20000'", "m": "input", "st": ["Loan Amount"], "tf": "loan amount", "exp": "f71"},
    {"n": "72", "step": "VERIFY '$10,000' is present", "ver": True, "res": True},
    {"n": "73", "step": "Select '24 Months' from 'Term'", "m": "select", "st": ["24 Months", "Term"], "tf": None, "exp": "f73"},
    {"n": "74", "step": "EXTRACT Interest Rate into {rate}", "ex": True, "var": "rate", "val": "5.99%"},
    {"n": "75", "step": "EXTRACT Monthly Payment into {pay}", "ex": True, "var": "pay", "val": "$860.00"},
    {"n": "76", "step": "Click 'Apply for Loan'", "m": "clickable", "st": ["Apply for Loan"], "tf": None, "exp": "f76"},
    {"n": "77", "step": "Click 'View Amortization Schedule'", "m": "clickable", "st": ["View Amortization Schedule"], "tf": None, "exp": "f77"},
    {"n": "78", "step": "Check 'Include Payment Protection'", "m": "clickable", "st": ["Include Payment Protection"], "tf": None, "exp": "f78"},
    {"n": "79", "step": "Click 'Pay Early'", "m": "clickable", "st": ["Pay Early"], "tf": None, "exp": "f79"},
    {"n": "80", "step": "VERIFY 'Credit Score: 750' is present", "ver": True, "res": True},

    # Investments (81-90)
    {"n": "81", "step": "Click 'Create Portfolio'", "m": "clickable", "st": ["Create Portfolio"], "tf": None, "exp": "f81"},
    {"n": "82", "step": "Fill 'Ticker' with 'TSLA'", "m": "input", "st": ["Ticker"], "tf": "ticker", "exp": "f82"},
    {"n": "83", "step": "Click 'Search Asset'", "m": "clickable", "st": ["Search Asset"], "tf": None, "exp": "f83"},
    {"n": "84", "step": "Click 'Auto-Invest' switch", "m": "clickable", "st": ["Auto-Invest"], "tf": None, "exp": "f84"},
    {"n": "85", "step": "Fill 'Auto-deposit amount' with '100'", "m": "input", "st": ["Auto-deposit amount"], "tf": "auto-deposit amount", "exp": "f85"},
    {"n": "86", "step": "Select 'Monthly' from 'Frequency'", "m": "select", "st": ["Monthly", "Frequency"], "tf": None, "exp": "f86"},
    {"n": "87", "step": "Click 'Confirm Auto-Invest'", "m": "clickable", "st": ["Confirm Auto-Invest"], "tf": None, "exp": "f87"},
    {"n": "88", "step": "Click 'Rebalance Portfolio'", "m": "clickable", "st": ["Rebalance Portfolio"], "tf": None, "exp": "f88"},
    {"n": "89", "step": "EXTRACT YTD Return into {ytd}", "ex": True, "var": "ytd", "val": "+12.4%"},
    {"n": "90", "step": "Click 'Withdraw Funds'", "m": "clickable", "st": ["Withdraw Funds"], "tf": None, "exp": "f90"},

    # Edge Cases & Popups (91-100)
    {"n": "91", "step": "Click 'Stay Logged In'", "m": "clickable", "st": ["Stay Logged In"], "tf": None, "exp": "f91"},
    {"n": "92", "step": "Click 'Log Out Now'", "m": "clickable", "st": ["Log Out Now"], "tf": None, "exp": "f92"},
    {"n": "93", "step": "VERIFY 'Transfer Successful' is present", "ver": True, "res": True},
    {"n": "94", "step": "Click 'Dismiss Alert'", "m": "clickable", "st": ["Dismiss Alert"], "tf": None, "exp": "f94"},
    # Resolving exact classes/texts:
    {"n": "95", "step": "Click 'Confirm' in transfer", "m": "clickable", "st": ["Confirm", "transfer"], "tf": None, "exp": "f95"},
    {"n": "96", "step": "Click 'Confirm' to delete", "m": "clickable", "st": ["Confirm", "delete"], "tf": None, "exp": "f96"},
    {"n": "97", "step": "Click 'Confirm'", "m": "clickable", "st": ["Confirm"], "tf": None, "exp": "f95"}, # Without context, should pick first available
    {"n": "98", "step": "Click 'Acknowledge Risk'", "m": "clickable", "st": ["Acknowledge Risk"], "tf": None, "exp": "f98"},
    {"n": "99", "step": "Check 'I agree to the updated terms'", "m": "clickable", "st": ["I agree to the updated terms"], "tf": None, "exp": "f99"},
    {"n": "100", "step": "VERIFY 'Finalize' is disabled", "ver": True, "step": "VERIFY that 'Finalize' is disabled", "res": True},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("💰 FINTECH & CRYPTO HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(FINTECH_DOM)

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
                if found == t["exp"] or (t["n"] == "97" and found in ["f95", "f96", "f97"]):
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
            print("\n🏆 FLAWLESS VICTORY!")
        print(f"{'=' * 70}")
        await browser.close()

    return passed == len(TESTS)

if __name__ == "__main__":
    asyncio.run(run_suite())