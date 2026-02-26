import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Healthcare & Government (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
GOV_DOM = """
<!DOCTYPE html><html><head><style>
.legacy-table td { padding: 5px; border: 1px solid #ccc; }
.signature-pad { width: 300px; height: 100px; border: 2px dashed #000; background: #eee; }
.sr-only { position: absolute; left: -10000px; width: 1px; height: 1px; }
.required::after { content: '*'; color: red; }
</style></head><body>

<div class="login-box">
    <h2>Citizen Portal Login</h2>
    <label for="h1" class="required">Social Security Number</label>
    <input type="password" id="h1" placeholder="XXX-XX-XXXX">
    <label for="h2" class="required">Date of Birth</label>
    <input type="date" id="h2">
    <button id="h3" class="btn-primary">Authenticate</button>
    <a href="/forgot" id="h4">Forgot ID?</a>
    <select id="h5" aria-label="ID Type"><option>State ID</option><option>Passport</option><option>Military ID</option></select>
    <input type="text" id="h6" placeholder="Document Number">
    <input type="checkbox" id="h7"><label for="h7">I am not a robot</label>
    <button id="h8" aria-label="Audio Captcha">🔊</button>
    <button id="h9" disabled>Verify Captcha</button>
    <div id="h10" role="alert" style="color:red;">Session expires in 04:59</div>
</div>

<fieldset>
    <legend>Section 1: Personal Details</legend>
    <input type="text" id="h11" placeholder="First Name">
    <input type="text" id="h12" placeholder="Middle Initial" maxlength="1">
    <input type="text" id="h13" placeholder="Last Name">
    <label>Suffix</label><select id="h14"><option>None</option><option>Jr.</option><option>Sr.</option></select>
    <label>Sex assigned at birth:</label>
    <input type="radio" name="sex" id="h15" value="M"><label for="h15">Male</label>
    <input type="radio" name="sex" id="h16" value="F"><label for="h16">Female</label>
    <select id="h17" aria-label="Marital Status"><option>Single</option><option>Married</option><option>Divorced</option></select>
    <input type="text" id="h18" placeholder="Maiden Name (if applicable)">
    <input type="text" id="h19" placeholder="Place of Birth (City)">
    <button id="h20">Validate Identity</button>
</fieldset>

<table class="legacy-table">
    <tr>
        <td><label for="h21">Address Line 1</label></td>
        <td><input type="text" id="h21"></td>
        <td><label for="h22">Apt/Suite</label></td>
        <td><input type="text" id="h22"></td>
    </tr>
    <tr>
        <td><label for="h23">City</label></td>
        <td><input type="text" id="h23"></td>
        <td><label for="h24">State</label></td>
        <td><select id="h24"><option>TX</option><option>CA</option><option>NY</option></select></td>
    </tr>
    <tr>
        <td><label for="h25">ZIP Code</label></td>
        <td><input type="text" id="h25" maxlength="5"></td>
        <td><label for="h26">County</label></td>
        <td><input type="text" id="h26"></td>
    </tr>
</table>
<input type="checkbox" id="h27"><label for="h27">Mailing address same as residential</label>
<input type="tel" id="h28" placeholder="Primary Phone">
<input type="email" id="h29" placeholder="Email Address">
<button id="h30">Update Contact Info</button>

<div class="medical-history">
    <h3>Conditions</h3>
    <input type="checkbox" id="h31"><label for="h31">Diabetes</label>
    <input type="checkbox" id="h32"><label for="h32">Hypertension</label>
    <input type="checkbox" id="h33"><label for="h33">Asthma</label>
    <input type="checkbox" id="h34" class="none-of-above"><label for="h34">None of the above</label>
    <label for="h35">List any surgeries:</label>
    <textarea id="h35" rows="4"></textarea>
    <label for="h36">Current Medications:</label>
    <input type="text" id="h36">
    <button id="h37">Add Medication</button>
    <label for="h38">Allergies:</label>
    <input type="text" id="h38">
    <button id="h39">Add Allergy</button>
    <input type="checkbox" id="h40"><label for="h40">No known allergies</label>
</div>

<fieldset>
    <legend>Coverage</legend>
    <select id="h41" aria-label="Insurance Provider"><option>Medicare</option><option>BlueCross</option></select>
    <input type="text" id="h42" placeholder="Policy Number">
    <input type="text" id="h43" placeholder="Group ID">
    <label for="h44">Upload Insurance Card (Front)</label>
    <input type="file" id="h44">
    <label for="h45">Upload Insurance Card (Back)</label>
    <input type="file" id="h45">
    <button id="h46">Verify Coverage</button>
    <span id="h47">Status: Active</span>
    <input type="text" id="h48" placeholder="Primary Care Physician">
    <button id="h49">Search Providers</button>
    <input type="checkbox" id="h50"><label for="h50">I am the primary policyholder</label>
</fieldset>

<div class="scheduler">
    <button id="h51" class="btn-schedule">Schedule New Appointment</button>
    <select id="h52" aria-label="Reason for Visit"><option>Annual Physical</option><option>Follow-up</option></select>
    <input type="date" id="h53" aria-label="Preferred Date">
    <select id="h54" aria-label="Preferred Time"><option>Morning</option><option>Afternoon</option></select>
    <button id="h55">Find Available Slots</button>
    <div role="button" id="h56" class="time-slot">09:00 AM</div>
    <div role="button" id="h57" class="time-slot">10:30 AM</div>
    <button id="h58">Confirm Appointment</button>
    <button id="h59">Cancel Appointment</button>
    <button id="h60">Reschedule</button>
</div>

<div class="a11y-tools">
    <button id="h61" aria-label="Toggle High Contrast">🌓</button>
    <button id="h62" aria-label="Increase Text Size">A+</button>
    <button id="h63" aria-label="Decrease Text Size">A-</button>
    <select id="h64" aria-label="Language Translation"><option>English</option><option>Español</option></select>
    <a href="#main-content" id="h65" class="sr-only">Skip to main content</a>
    <button id="h66">Print Page</button>
    <button id="h67">Download PDF</button>
    <button id="h68">Chat with Virtual Assistant</button>
    <button id="h69">Contact Live Agent</button>
    <button id="h70">Leave Feedback</button>
</div>

<div class="consent-form">
    <textarea id="h71" readonly>HIPAA Privacy Notice...</textarea>
    <input type="checkbox" id="h72"><label for="h72">I acknowledge receipt of the Privacy Notice</label>
    <input type="checkbox" id="h73"><label for="h73">I consent to telehealth services</label>
    <div id="h74" class="signature-pad" role="application" aria-label="Sign here"></div>
    <button id="h75">Clear Signature</button>
    <input type="text" id="h76" placeholder="Type name to sign">
    <input type="date" id="h77" aria-label="Signature Date">
    <input type="text" id="h78" placeholder="Relationship to patient">
    <button id="h79">Accept & Sign</button>
    <button id="h80" style="color:red;">Decline</button>
</div>

<table id="records_table">
    <tr><th>Document</th><th>Date</th><th>Action</th></tr>
    <tr><td>W-2 Tax Form 2025</td><td>01/15/2026</td><td><button id="h81">Download W-2</button></td></tr>
    <tr><td>Vaccination Record</td><td>11/10/2025</td><td><button id="h82">View Record</button></td></tr>
    <tr><td>Lab Results</td><td>12/05/2025</td><td><a href="/labs/1" id="h83">Open PDF</a></td></tr>
</table>
<button id="h84">Request Medical Records</button>
<button id="h85">Appeal Tax Decision</button>
<input type="text" id="h86" placeholder="Search records by year">
<button id="h87">Search Records</button>
<select id="h88" aria-label="Filter Records"><option>All</option><option>Taxes</option><option>Health</option></select>
<div id="h89">Total documents: 14</div>
<button id="h90">Upload New Document</button>

<div class="form-footer">
    <button id="h91">Save Draft</button>
    <button id="h92">Next Section >></button>
    <button id="h93"><< Previous Section</button>
    <input type="submit" id="h94" value="SUBMIT APPLICATION" class="btn-success">
    <input type="reset" id="h95" value="CLEAR FORM" class="btn-danger">
    <div id="h96" style="display:none;">Are you sure you want to submit?</div>
    <button id="h97">Yes, Submit</button>
    <button id="h98">No, Go Back</button>
    <button id="h99" disabled>Processing...</button>
    <a href="/logout" id="h100">Secure Logout</a>
</div>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Identity & Login
    {"n": "1", "step": "Fill 'Social Security Number' with '123-45-6789'", "m": "input", "st": ["Social Security Number"], "tf": "social security number", "exp": "h1"},
    {"n": "2", "step": "Fill 'Date of Birth' with '1980-01-01'", "m": "input", "st": ["Date of Birth"], "tf": "date of birth", "exp": "h2"},
    {"n": "3", "step": "Click 'Authenticate'", "m": "clickable", "st": ["Authenticate"], "tf": None, "exp": "h3"},
    {"n": "4", "step": "Click 'Forgot ID?'", "m": "clickable", "st": ["Forgot ID?"], "tf": None, "exp": "h4"},
    {"n": "5", "step": "Select 'Passport' from 'ID Type'", "m": "select", "st": ["Passport", "ID Type"], "tf": None, "exp": "h5"},
    {"n": "6", "step": "Fill 'Document Number' with 'A123'", "m": "input", "st": ["Document Number"], "tf": "document number", "exp": "h6"},
    {"n": "7", "step": "Check 'I am not a robot'", "m": "clickable", "st": ["I am not a robot"], "tf": None, "exp": "h7"},
    {"n": "8", "step": "Click 'Audio Captcha'", "m": "clickable", "st": ["Audio Captcha"], "tf": None, "exp": "h8"},
    {"n": "9", "step": "VERIFY 'Verify Captcha' is disabled", "ver": True, "step": "VERIFY that 'Verify Captcha' is disabled", "res": True},
    {"n": "10", "step": "VERIFY 'Session expires' is present", "ver": True, "res": True},

    # Personal Information
    {"n": "11", "step": "Fill 'First Name' with 'John'", "m": "input", "st": ["First Name"], "tf": "first name", "exp": "h11"},
    {"n": "12", "step": "Fill 'Middle Initial' with 'Q'", "m": "input", "st": ["Middle Initial"], "tf": "middle initial", "exp": "h12"},
    {"n": "13", "step": "Fill 'Last Name' with 'Public'", "m": "input", "st": ["Last Name"], "tf": "last name", "exp": "h13"},
    {"n": "14", "step": "Select 'Jr.' from 'Suffix'", "m": "select", "st": ["Jr.", "Suffix"], "tf": None, "exp": "h14"},
    {"n": "15", "step": "Click the radio button for 'Male'", "m": "clickable", "st": ["Male"], "tf": None, "exp": "h15"},
    {"n": "16", "step": "Click the radio button for 'Female'", "m": "clickable", "st": ["Female"], "tf": None, "exp": "h16"},
    {"n": "17", "step": "Select 'Single' from 'Marital Status'", "m": "select", "st": ["Single", "Marital Status"], "tf": None, "exp": "h17"},
    {"n": "18", "step": "Fill 'Maiden Name' with 'Smith'", "m": "input", "st": ["Maiden Name"], "tf": "maiden name", "exp": "h18"},
    {"n": "19", "step": "Fill 'Place of Birth' with 'Dallas'", "m": "input", "st": ["Place of Birth"], "tf": "place of birth", "exp": "h19"},
    {"n": "20", "step": "Click 'Validate Identity'", "m": "clickable", "st": ["Validate Identity"], "tf": None, "exp": "h20"},

    # Contact & Address
    {"n": "21", "step": "Fill 'Address Line 1' with '123 Elm St'", "m": "input", "st": ["Address Line 1"], "tf": "address line 1", "exp": "h21"},
    {"n": "22", "step": "Fill 'Apt/Suite' with '4B'", "m": "input", "st": ["Apt/Suite"], "tf": "apt/suite", "exp": "h22"},
    {"n": "23", "step": "Fill 'City' with 'Austin'", "m": "input", "st": ["City"], "tf": "city", "exp": "h23"},
    {"n": "24", "step": "Select 'TX' from 'State'", "m": "select", "st": ["TX", "State"], "tf": None, "exp": "h24"},
    {"n": "25", "step": "Fill 'ZIP Code' with '73301'", "m": "input", "st": ["ZIP Code"], "tf": "zip code", "exp": "h25"},
    {"n": "26", "step": "Fill 'County' with 'Travis'", "m": "input", "st": ["County"], "tf": "county", "exp": "h26"},
    {"n": "27", "step": "Check 'Mailing address same as residential'", "m": "clickable", "st": ["Mailing address same as residential"], "tf": None, "exp": "h27"},
    {"n": "28", "step": "Fill 'Primary Phone' with '555-0100'", "m": "input", "st": ["Primary Phone"], "tf": "primary phone", "exp": "h28"},
    {"n": "29", "step": "Fill 'Email Address' with 'john@test.gov'", "m": "input", "st": ["Email Address"], "tf": "email address", "exp": "h29"},
    {"n": "30", "step": "Click 'Update Contact Info'", "m": "clickable", "st": ["Update Contact Info"], "tf": None, "exp": "h30"},

    # Medical History
    {"n": "31", "step": "Check 'Diabetes'", "m": "clickable", "st": ["Diabetes"], "tf": None, "exp": "h31"},
    {"n": "32", "step": "Check 'Hypertension'", "m": "clickable", "st": ["Hypertension"], "tf": None, "exp": "h32"},
    {"n": "33", "step": "Check 'Asthma'", "m": "clickable", "st": ["Asthma"], "tf": None, "exp": "h33"},
    {"n": "34", "step": "Check 'None of the above'", "m": "clickable", "st": ["None of the above"], "tf": None, "exp": "h34"},
    {"n": "35", "step": "Fill 'surgeries' field with 'Appendectomy'", "m": "input", "st": ["surgeries"], "tf": "surgeries", "exp": "h35"},
    {"n": "36", "step": "Fill 'Current Medications' with 'Aspirin'", "m": "input", "st": ["Current Medications"], "tf": "current medications", "exp": "h36"},
    {"n": "37", "step": "Click 'Add Medication'", "m": "clickable", "st": ["Add Medication"], "tf": None, "exp": "h37"},
    {"n": "38", "step": "Fill 'Allergies' with 'Penicillin'", "m": "input", "st": ["Allergies"], "tf": "allergies", "exp": "h38"},
    {"n": "39", "step": "Click 'Add Allergy'", "m": "clickable", "st": ["Add Allergy"], "tf": None, "exp": "h39"},
    {"n": "40", "step": "Check 'No known allergies'", "m": "clickable", "st": ["No known allergies"], "tf": None, "exp": "h40"},

    # Insurance & Tax
    {"n": "41", "step": "Select 'Medicare' from 'Insurance Provider'", "m": "select", "st": ["Medicare", "Insurance Provider"], "tf": None, "exp": "h41"},
    {"n": "42", "step": "Fill 'Policy Number' with 'POL123'", "m": "input", "st": ["Policy Number"], "tf": "policy number", "exp": "h42"},
    {"n": "43", "step": "Fill 'Group ID' with 'GRP456'", "m": "input", "st": ["Group ID"], "tf": "group id", "exp": "h43"},
    {"n": "44", "step": "Click 'Upload Insurance Card (Front)'", "m": "clickable", "st": ["Upload Insurance Card (Front)"], "tf": None, "exp": "h44"},
    {"n": "45", "step": "Click 'Upload Insurance Card (Back)'", "m": "clickable", "st": ["Upload Insurance Card (Back)"], "tf": None, "exp": "h45"},
    {"n": "46", "step": "Click 'Verify Coverage'", "m": "clickable", "st": ["Verify Coverage"], "tf": None, "exp": "h46"},
    {"n": "47", "step": "EXTRACT coverage Status into {cov_stat}", "ex": True, "var": "cov_stat", "val": "Active"},
    {"n": "48", "step": "Fill 'Primary Care Physician' with 'Dr. House'", "m": "input", "st": ["Primary Care Physician"], "tf": "primary care physician", "exp": "h48"},
    {"n": "49", "step": "Click 'Search Providers'", "m": "clickable", "st": ["Search Providers"], "tf": None, "exp": "h49"},
    {"n": "50", "step": "Check 'primary policyholder'", "m": "clickable", "st": ["primary policyholder"], "tf": None, "exp": "h50"},

    # Appointments
    {"n": "51", "step": "Click 'Schedule New Appointment'", "m": "clickable", "st": ["Schedule New Appointment"], "tf": None, "exp": "h51"},
    {"n": "52", "step": "Select 'Annual Physical' from 'Reason for Visit'", "m": "select", "st": ["Annual Physical", "Reason for Visit"], "tf": None, "exp": "h52"},
    {"n": "53", "step": "Fill 'Preferred Date' with '2026-05-10'", "m": "input", "st": ["Preferred Date"], "tf": "preferred date", "exp": "h53"},
    {"n": "54", "step": "Select 'Morning' from 'Preferred Time'", "m": "select", "st": ["Morning", "Preferred Time"], "tf": None, "exp": "h54"},
    {"n": "55", "step": "Click 'Find Available Slots'", "m": "clickable", "st": ["Find Available Slots"], "tf": None, "exp": "h55"},
    {"n": "56", "step": "Click '09:00 AM'", "m": "clickable", "st": ["09:00 AM"], "tf": None, "exp": "h56"},
    {"n": "57", "step": "Click '10:30 AM'", "m": "clickable", "st": ["10:30 AM"], "tf": None, "exp": "h57"},
    {"n": "58", "step": "Click 'Confirm Appointment'", "m": "clickable", "st": ["Confirm Appointment"], "tf": None, "exp": "h58"},
    {"n": "59", "step": "Click 'Cancel Appointment'", "m": "clickable", "st": ["Cancel Appointment"], "tf": None, "exp": "h59"},
    {"n": "60", "step": "Click 'Reschedule'", "m": "clickable", "st": ["Reschedule"], "tf": None, "exp": "h60"},

    # Accessibility & Global
    {"n": "61", "step": "Click 'Toggle High Contrast'", "m": "clickable", "st": ["Toggle High Contrast"], "tf": None, "exp": "h61"},
    {"n": "62", "step": "Click 'Increase Text Size'", "m": "clickable", "st": ["Increase Text Size"], "tf": None, "exp": "h62"},
    {"n": "63", "step": "Click 'Decrease Text Size'", "m": "clickable", "st": ["Decrease Text Size"], "tf": None, "exp": "h63"},
    {"n": "64", "step": "Select 'Español' from 'Language Translation'", "m": "select", "st": ["Español", "Language Translation"], "tf": None, "exp": "h64"},
    {"n": "65", "step": "Click 'Skip to main content'", "m": "clickable", "st": ["Skip to main content"], "tf": None, "exp": "h65"},
    {"n": "66", "step": "Click 'Print Page'", "m": "clickable", "st": ["Print Page"], "tf": None, "exp": "h66"},
    {"n": "67", "step": "Click 'Download PDF'", "m": "clickable", "st": ["Download PDF"], "tf": None, "exp": "h67"},
    {"n": "68", "step": "Click 'Chat with Virtual Assistant'", "m": "clickable", "st": ["Chat with Virtual Assistant"], "tf": None, "exp": "h68"},
    {"n": "69", "step": "Click 'Contact Live Agent'", "m": "clickable", "st": ["Contact Live Agent"], "tf": None, "exp": "h69"},
    {"n": "70", "step": "Click 'Leave Feedback'", "m": "clickable", "st": ["Leave Feedback"], "tf": None, "exp": "h70"},

    # Consents & Signatures
    {"n": "71", "step": "VERIFY 'Privacy Notice' is present in text", "ver": True, "step": "VERIFY that 'HIPAA Privacy Notice' is present", "res": True},
    {"n": "72", "step": "Check 'receipt of the Privacy Notice'", "m": "clickable", "st": ["receipt of the Privacy Notice"], "tf": None, "exp": "h72"},
    {"n": "73", "step": "Check 'telehealth services'", "m": "clickable", "st": ["telehealth services"], "tf": None, "exp": "h73"},
    {"n": "74", "step": "Click 'Sign here'", "m": "clickable", "st": ["Sign here"], "tf": None, "exp": "h74"},
    {"n": "75", "step": "Click 'Clear Signature'", "m": "clickable", "st": ["Clear Signature"], "tf": None, "exp": "h75"},
    {"n": "76", "step": "Fill 'Type name to sign' with 'John Public'", "m": "input", "st": ["Type name to sign"], "tf": "type name to sign", "exp": "h76"},
    {"n": "77", "step": "Fill 'Signature Date' with '2026-02-26'", "m": "input", "st": ["Signature Date"], "tf": "signature date", "exp": "h77"},
    {"n": "78", "step": "Fill 'Relationship to patient' with 'Self'", "m": "input", "st": ["Relationship to patient"], "tf": "relationship to patient", "exp": "h78"},
    {"n": "79", "step": "Click 'Accept & Sign'", "m": "clickable", "st": ["Accept & Sign"], "tf": None, "exp": "h79"},
    {"n": "80", "step": "Click 'Decline'", "m": "clickable", "st": ["Decline"], "tf": None, "exp": "h80"},

    # Tables & Records
    {"n": "81", "step": "Click 'Download W-2'", "m": "clickable", "st": ["Download W-2"], "tf": None, "exp": "h81"},
    {"n": "82", "step": "Click 'View Record'", "m": "clickable", "st": ["View Record"], "tf": None, "exp": "h82"},
    {"n": "83", "step": "Click 'Open PDF'", "m": "clickable", "st": ["Open PDF"], "tf": None, "exp": "h83"},
    {"n": "84", "step": "Click 'Request Medical Records'", "m": "clickable", "st": ["Request Medical Records"], "tf": None, "exp": "h84"},
    {"n": "85", "step": "Click 'Appeal Tax Decision'", "m": "clickable", "st": ["Appeal Tax Decision"], "tf": None, "exp": "h85"},
    {"n": "86", "step": "Fill 'Search records by year' with '2025'", "m": "input", "st": ["Search records by year"], "tf": "search records by year", "exp": "h86"},
    {"n": "87", "step": "Click 'Search Records'", "m": "clickable", "st": ["Search Records"], "tf": None, "exp": "h87"},
    {"n": "88", "step": "Select 'Health' from 'Filter Records'", "m": "select", "st": ["Health", "Filter Records"], "tf": None, "exp": "h88"},
    {"n": "89", "step": "EXTRACT Total documents into {docs}", "ex": True, "var": "docs", "val": "14"},
    {"n": "90", "step": "Click 'Upload New Document'", "m": "clickable", "st": ["Upload New Document"], "tf": None, "exp": "h90"},

    # Form Submission
    {"n": "91", "step": "Click 'Save Draft'", "m": "clickable", "st": ["Save Draft"], "tf": None, "exp": "h91"},
    {"n": "92", "step": "Click 'Next Section'", "m": "clickable", "st": ["Next Section"], "tf": None, "exp": "h92"},
    {"n": "93", "step": "Click 'Previous Section'", "m": "clickable", "st": ["Previous Section"], "tf": None, "exp": "h93"},
    {"n": "94", "step": "Click 'SUBMIT APPLICATION'", "m": "clickable", "st": ["SUBMIT APPLICATION"], "tf": None, "exp": "h94"},
    {"n": "95", "step": "Click 'CLEAR FORM'", "m": "clickable", "st": ["CLEAR FORM"], "tf": None, "exp": "h95"},
    {"n": "96", "step": "VERIFY 'Are you sure you want to submit' is NOT present", "ver": True, "step": "VERIFY that 'Are you sure you want to submit' is NOT present", "res": True}, # Hidden
    {"n": "97", "step": "Click 'Yes, Submit'", "m": "clickable", "st": ["Yes, Submit"], "tf": None, "exp": "h97"},
    {"n": "98", "step": "Click 'No, Go Back'", "m": "clickable", "st": ["No, Go Back"], "tf": None, "exp": "h98"},
    {"n": "99", "step": "VERIFY 'Processing...' is disabled", "ver": True, "step": "VERIFY that 'Processing...' is disabled", "res": True},
    {"n": "100", "step": "Click 'Secure Logout'", "m": "clickable", "st": ["Secure Logout"], "tf": None, "exp": "h100"},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("🏛️ GOV & HEALTHCARE HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(GOV_DOM)

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