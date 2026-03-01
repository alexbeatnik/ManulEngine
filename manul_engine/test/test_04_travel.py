import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: Travel & Booking (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
TRAVEL_DOM = """
<!DOCTYPE html><html><head><style>
.seat { width: 40px; height: 40px; border: 1px solid #ccc; display: inline-block; }
.seat-taken { background: red; pointer-events: none; }
.seat-avail { background: green; cursor: pointer; }
.sr-only { position: absolute; clip: rect(0,0,0,0); }
</style></head><body>

<div class="search-widget">
    <div role="radiogroup">
        <label><input type="radio" name="trip" id="t1" checked> Round Trip</label>
        <label><input type="radio" name="trip" id="t2"> One Way</label>
        <label><input type="radio" name="trip" id="t3"> Multi-city</label>
    </div>
    <input type="text" id="t4" placeholder="Flying from">
    <button id="t5" aria-label="Swap Origin and Destination">⇄</button>
    <input type="text" id="t6" placeholder="Flying to">
    <input type="checkbox" id="t7"><label for="t7">Direct flights only</label>
    <input type="checkbox" id="t8"><label for="t8">Add nearby airports</label>
    <button id="t9" class="btn-search">Search Flights</button>
    <a href="/deals" id="t10">Explore Deals</a>
</div>

<div class="calendar">
    <input type="text" id="t11" placeholder="Depart" readonly>
    <input type="text" id="t12" placeholder="Return" readonly>
    <button id="t13" aria-label="Previous Month">◀</button>
    <span id="t14" aria-live="polite" data-qa="current-month">March 2026</span>
    <button id="t15" aria-label="Next Month">▶</button>
    <div role="button" id="t16" aria-label="March 10, 2026">10</div>
    <div role="button" id="t17" aria-label="March 15, 2026">15</div>
    <div role="button" id="t18" aria-label="March 20, 2026" class="disabled">20</div>
    <button id="t19">I'm flexible (+/- 3 days)</button>
    <button id="t20">Done (Dates)</button>
</div>

<div class="pax-selector">
    <div role="button" id="t21" aria-expanded="false">1 Adult, Economy ▼</div>
    <div class="dropdown">
        <div>Adults (16+) <button id="t22" aria-label="Decrease Adults">-</button> <span id="t23" data-qa="adults">1</span> <button id="t24" aria-label="Increase Adults">+</button></div>
        <div>Children (2-15) <button id="t25" aria-label="Decrease Children">-</button> <span id="t26" data-qa="children">0</span> <button id="t27" aria-label="Increase Children">+</button></div>
        <select id="t28" aria-label="Cabin Class">
            <option>Economy</option>
            <option>Premium Economy</option>
            <option>Business</option>
            <option>First</option>
        </select>
        <button id="t29">Apply Pax</button>
        <button id="t30" style="display:none;">Add Infant</button>
    </div>
</div>

<div class="sidebar-filters">
    <h3>Stops</h3>
    <label><input type="checkbox" id="t31" checked> Non-stop</label>
    <label><input type="checkbox" id="t32"> 1 Stop</label>
    <label><input type="checkbox" id="t33"> 2+ Stops</label>
    <h3>Airlines</h3>
    <button id="t34">Clear All Airlines</button>
    <label><input type="checkbox" id="t35"> Lufthansa</label>
    <label><input type="checkbox" id="t36"> Ryanair</label>
    <h3>Times</h3>
    <input type="range" id="t37" aria-label="Departure Time">
    <select id="t38" aria-label="Sort by"><option>Price (Lowest)</option><option>Duration (Shortest)</option></select>
    <button id="t39">Reset Filters</button>
    <div role="switch" id="t40" aria-checked="false">Hide overnight flights</div>
</div>

<div class="flight-card">
    <div class="airline">Lufthansa</div>
    <div class="duration">2h 15m</div>
    <div class="price" id="t41">€129.00</div>
    <button id="t42" aria-label="Select Lufthansa flight">Select</button>
    <button id="t43">View Details</button>
</div>
<div class="flight-card">
    <div class="airline">Ryanair</div>
    <div class="price" id="t44">€19.99</div>
    <button id="t45" aria-label="Select Ryanair flight">Select</button>
</div>
<button id="t46">Show more flights</button>
<button id="t47">Track Prices</button>
<input type="email" id="t48" placeholder="Email for price alerts">
<button id="t49">Set Alert</button>
<div id="t50">No flights found for selected dates</div>

<div class="seat-map">
    <h3>Select your seat</h3>
    <div id="t51" role="checkbox" aria-checked="false" aria-label="Seat 1A" class="seat seat-avail">1A</div>
    <div id="t52" role="checkbox" aria-checked="true" aria-label="Seat 1B" class="seat seat-taken">1B</div>
    <div id="t53" role="checkbox" aria-checked="false" aria-label="Seat 1C" class="seat seat-avail">1C</div>
    <button id="t54">Skip Seat Selection</button>
    <button id="t55">Confirm Seats</button>
    <div role="button" id="t56">Extra Legroom (+$20)</div>
    <div role="button" id="t57">Window Seat</div>
    <div role="button" id="t58">Aisle Seat</div>
    <button id="t59">View upper deck</button>
    <button id="t60" disabled>Next Passenger</button>
</div>

<div class="addons">
    <div class="bag-card">
        <h4>Personal Item</h4><span id="t61">Included</span>
    </div>
    <div class="bag-card">
        <h4>Cabin Bag</h4>
        <button id="t62">Add Cabin Bag (+€15)</button>
    </div>
    <div class="bag-card">
        <h4>Checked Bag (20kg)</h4>
        <select id="t63" aria-label="Checked Bags"><option>0</option><option>1 (+€30)</option><option>2 (+€60)</option></select>
    </div>
    <input type="checkbox" id="t64"><label for="t64">Priority Boarding</label>
    <input type="checkbox" id="t65"><label for="t65">Fast Track Security</label>
    <div class="insurance-box">
        <label><input type="radio" name="ins" id="t66"> Yes, protect my trip</label>
        <label><input type="radio" name="ins" id="t67"> No, I will risk it</label>
    </div>
    <button id="t68">Read Policy</button>
    <button id="t69">Add Rental Car</button>
    <button id="t70">Continue to Passenger Details</button>
</div>

<div class="pax-form">
    <select id="t71" aria-label="Title"><option>Mr</option><option>Ms</option><option>Mrs</option></select>
    <input type="text" id="t72" placeholder="First Name (as in passport)">
    <input type="text" id="t73" placeholder="Last Name (as in passport)">
    <input type="date" id="t74" aria-label="Date of Birth">
    <select id="t75" aria-label="Nationality"><option>Ukraine</option><option>USA</option></select>
    <input type="text" id="t76" placeholder="Passport Number">
    <input type="date" id="t77" aria-label="Passport Expiry">
    <input type="email" id="t78" placeholder="Contact Email">
    <input type="tel" id="t79" placeholder="Mobile Number">
    <button id="t80">Save Passenger</button>
</div>

<div class="hotel-search">
    <input type="text" id="t81" placeholder="Where are you going?">
    <button id="t82">Search Hotels</button>
    <input type="checkbox" id="t83"><label for="t83">I'm traveling for work</label>
    <button id="t84" aria-label="Show Map">🗺️ Map View</button>
    <select id="t85" aria-label="Star Rating"><option>Any</option><option>4 Stars</option><option>5 Stars</option></select>
    <label><input type="checkbox" id="t86"> Free Cancellation</label>
    <label><input type="checkbox" id="t87"> Breakfast Included</label>
    <button id="t88" aria-label="Select Hilton Hotel">Book Hilton</button>
    <span id="t89" class="hotel-price">$150/night</span>
    <button id="t90">Read Guest Reviews</button>
</div>

<div class="checkout">
    <div class="summary">Flight Total: <span id="t91">$250.00</span></div>
    <div class="summary">Taxes & Fees: <span id="t92">$45.50</span></div>
    <div class="summary">Grand Total: <span id="t93">$295.50</span></div>
    <input type="text" id="t94" placeholder="Promo / Voucher Code">
    <button id="t95">Apply Voucher</button>
    <input type="checkbox" id="t96"><label for="t96">I accept the Terms & Conditions</label>
    <input type="checkbox" id="t97"><label for="t97">I acknowledge the Hazmat Policy</label>
    <button id="t98" class="btn-pay">Pay Now</button>
    <button id="t99">Save Cart</button>
    <a href="#" id="t100">Back to Home</a>
</div>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Flight Search
    {"n": "1", "step": "Click the radio button for 'Round Trip'", "m": "clickable", "st": ["Round Trip"], "tf": None, "exp": "t1"},
    {"n": "2", "step": "Click the radio button for 'One Way'", "m": "clickable", "st": ["One Way"], "tf": None, "exp": "t2"},
    {"n": "3", "step": "Click the radio button for 'Multi-city'", "m": "clickable", "st": ["Multi-city"], "tf": None, "exp": "t3"},
    {"n": "4", "step": "Fill 'Flying from' with 'JFK'", "m": "input", "st": ["Flying from"], "tf": "flying from", "exp": "t4"},
    {"n": "5", "step": "Click 'Swap Origin and Destination'", "m": "clickable", "st": ["Swap Origin and Destination"], "tf": None, "exp": "t5"},
    {"n": "6", "step": "Fill 'Flying to' with 'LHR'", "m": "input", "st": ["Flying to"], "tf": "flying to", "exp": "t6"},
    {"n": "7", "step": "Check 'Direct flights only'", "m": "clickable", "st": ["Direct flights only"], "tf": None, "exp": "t7"},
    {"n": "8", "step": "Check 'Add nearby airports'", "m": "clickable", "st": ["Add nearby airports"], "tf": None, "exp": "t8"},
    {"n": "9", "step": "Click 'Search Flights'", "m": "clickable", "st": ["Search Flights"], "tf": None, "exp": "t9"},
    {"n": "10", "step": "Click 'Explore Deals'", "m": "clickable", "st": ["Explore Deals"], "tf": None, "exp": "t10"},

    # Date Pickers
    {"n": "11", "step": "Click 'Depart'", "m": "clickable", "st": ["Depart"], "tf": None, "exp": "t11"},
    {"n": "12", "step": "Click 'Return'", "m": "clickable", "st": ["Return"], "tf": None, "exp": "t12"},
    {"n": "13", "step": "Click 'Previous Month'", "m": "clickable", "st": ["Previous Month"], "tf": None, "exp": "t13"},
    {"n": "14", "step": "EXTRACT current month into {m}", "ex": True, "var": "m", "val": "March 2026"},
    {"n": "15", "step": "Click 'Next Month'", "m": "clickable", "st": ["Next Month"], "tf": None, "exp": "t15"},
    {"n": "16", "step": "Click 'March 10, 2026'", "m": "clickable", "st": ["March 10, 2026"], "tf": None, "exp": "t16"},
    {"n": "17", "step": "Click 'March 15, 2026'", "m": "clickable", "st": ["March 15, 2026"], "tf": None, "exp": "t17"},
    {"n": "18", "step": "VERIFY that 'March 20, 2026' is present", "ver": True, "res": True},
    {"n": "19", "step": "Click 'flexible'", "m": "clickable", "st": ["flexible"], "tf": None, "exp": "t19"},
    {"n": "20", "step": "Click 'Done (Dates)'", "m": "clickable", "st": ["Done (Dates)"], "tf": None, "exp": "t20"},

    # Passengers & Class
    {"n": "21", "step": "Click 'Adult, Economy'", "m": "clickable", "st": ["Adult, Economy"], "tf": None, "exp": "t21"},
    {"n": "22", "step": "Click 'Decrease Adults'", "m": "clickable", "st": ["Decrease Adults"], "tf": None, "exp": "t22"},
    {"n": "23", "step": "EXTRACT Adult count into {ac}", "ex": True, "var": "ac", "val": "1"},
    {"n": "24", "step": "Click 'Increase Adults'", "m": "clickable", "st": ["Increase Adults"], "tf": None, "exp": "t24"},
    {"n": "25", "step": "Click 'Decrease Children'", "m": "clickable", "st": ["Decrease Children"], "tf": None, "exp": "t25"},
    {"n": "26", "step": "EXTRACT Children count into {cc}", "ex": True, "var": "cc", "val": "0"},
    {"n": "27", "step": "Click 'Increase Children'", "m": "clickable", "st": ["Increase Children"], "tf": None, "exp": "t27"},
    {"n": "28", "step": "Select 'Business' from 'Cabin Class'", "m": "select", "st": ["Business", "Cabin Class"], "tf": None, "exp": "t28"},
    {"n": "29", "step": "Click 'Apply Pax'", "m": "clickable", "st": ["Apply Pax"], "tf": None, "exp": "t29"},
    {"n": "30", "step": "Click 'Add Infant' if exists", "m": "clickable", "st": ["Add Infant"], "tf": None, "exp": None}, # It's display:none

    # Filters
    {"n": "31", "step": "Check 'Non-stop'", "m": "clickable", "st": ["Non-stop"], "tf": None, "exp": "t31"},
    {"n": "32", "step": "Check '1 Stop'", "m": "clickable", "st": ["1 Stop"], "tf": None, "exp": "t32"},
    {"n": "33", "step": "Check '2+ Stops'", "m": "clickable", "st": ["2+ Stops"], "tf": None, "exp": "t33"},
    {"n": "34", "step": "Click 'Clear All Airlines'", "m": "clickable", "st": ["Clear All Airlines"], "tf": None, "exp": "t34"},
    {"n": "35", "step": "Check 'Lufthansa'", "m": "clickable", "st": ["Lufthansa"], "tf": None, "exp": "t35"},
    {"n": "36", "step": "Check 'Ryanair'", "m": "clickable", "st": ["Ryanair"], "tf": None, "exp": "t36"},
    {"n": "37", "step": "Fill 'Departure Time' with '50'", "m": "input", "st": ["Departure Time"], "tf": "departure time", "exp": "t37"},
    {"n": "38", "step": "Select 'Duration (Shortest)' from 'Sort by'", "m": "select", "st": ["Duration (Shortest)", "Sort by"], "tf": None, "exp": "t38"},
    {"n": "39", "step": "Click 'Reset Filters'", "m": "clickable", "st": ["Reset Filters"], "tf": None, "exp": "t39"},
    {"n": "40", "step": "Click 'Hide overnight flights' switch", "m": "clickable", "st": ["Hide overnight flights"], "tf": None, "exp": "t40"},

    # Flight Results
    {"n": "41", "step": "EXTRACT Price of 'Lufthansa' into {p1}", "ex": True, "var": "p1", "val": "€129.00"},
    {"n": "42", "step": "Click 'Select Lufthansa flight'", "m": "clickable", "st": ["Select Lufthansa flight"], "tf": None, "exp": "t42"},
    {"n": "43", "step": "Click 'View Details'", "m": "clickable", "st": ["View Details"], "tf": None, "exp": "t43"},
    {"n": "44", "step": "EXTRACT Price of 'Ryanair' into {p2}", "ex": True, "var": "p2", "val": "€19.99"},
    {"n": "45", "step": "Click 'Select Ryanair flight'", "m": "clickable", "st": ["Select Ryanair flight"], "tf": None, "exp": "t45"},
    {"n": "46", "step": "Click 'Show more flights'", "m": "clickable", "st": ["Show more flights"], "tf": None, "exp": "t46"},
    {"n": "47", "step": "Click 'Track Prices'", "m": "clickable", "st": ["Track Prices"], "tf": None, "exp": "t47"},
    {"n": "48", "step": "Fill 'Email for price alerts' with 'a@b.c'", "m": "input", "st": ["Email for price alerts"], "tf": "email for price alerts", "exp": "t48"},
    {"n": "49", "step": "Click 'Set Alert'", "m": "clickable", "st": ["Set Alert"], "tf": None, "exp": "t49"},
    {"n": "50", "step": "VERIFY that 'No flights found' is present", "ver": True, "res": True},

    # Seat Selection
    {"n": "51", "step": "Click 'Seat 1A'", "m": "clickable", "st": ["Seat 1A"], "tf": None, "exp": "t51"},
    {"n": "52", "step": "VERIFY 'Seat 1B' is present", "ver": True, "res": True}, # seat taken
    {"n": "53", "step": "Click 'Seat 1C'", "m": "clickable", "st": ["Seat 1C"], "tf": None, "exp": "t53"},
    {"n": "54", "step": "Click 'Skip Seat Selection'", "m": "clickable", "st": ["Skip Seat Selection"], "tf": None, "exp": "t54"},
    {"n": "55", "step": "Click 'Confirm Seats'", "m": "clickable", "st": ["Confirm Seats"], "tf": None, "exp": "t55"},
    {"n": "56", "step": "Click 'Extra Legroom'", "m": "clickable", "st": ["Extra Legroom"], "tf": None, "exp": "t56"},
    {"n": "57", "step": "Click 'Window Seat'", "m": "clickable", "st": ["Window Seat"], "tf": None, "exp": "t57"},
    {"n": "58", "step": "Click 'Aisle Seat'", "m": "clickable", "st": ["Aisle Seat"], "tf": None, "exp": "t58"},
    {"n": "59", "step": "Click 'View upper deck'", "m": "clickable", "st": ["View upper deck"], "tf": None, "exp": "t59"},
    {"n": "60", "step": "VERIFY 'Next Passenger' is disabled", "ver": True, "step": "VERIFY that 'Next Passenger' is disabled", "res": True},

    # Baggage & Add-ons
    {"n": "61", "step": "EXTRACT 'Personal Item' into {bag}", "ex": True, "var": "bag", "val": "Included"},
    {"n": "62", "step": "Click 'Add Cabin Bag'", "m": "clickable", "st": ["Add Cabin Bag"], "tf": None, "exp": "t62"},
    {"n": "63", "step": "Select '1 (+€30)' from 'Checked Bags'", "m": "select", "st": ["1 (+€30)", "Checked Bags"], "tf": None, "exp": "t63"},
    {"n": "64", "step": "Check 'Priority Boarding'", "m": "clickable", "st": ["Priority Boarding"], "tf": None, "exp": "t64"},
    {"n": "65", "step": "Check 'Fast Track Security'", "m": "clickable", "st": ["Fast Track Security"], "tf": None, "exp": "t65"},
    {"n": "66", "step": "Click radio 'Yes, protect my trip'", "m": "clickable", "st": ["Yes, protect my trip"], "tf": None, "exp": "t66"},
    {"n": "67", "step": "Click radio 'No, I will risk it'", "m": "clickable", "st": ["No, I will risk it"], "tf": None, "exp": "t67"},
    {"n": "68", "step": "Click 'Read Policy'", "m": "clickable", "st": ["Read Policy"], "tf": None, "exp": "t68"},
    {"n": "69", "step": "Click 'Add Rental Car'", "m": "clickable", "st": ["Add Rental Car"], "tf": None, "exp": "t69"},
    {"n": "70", "step": "Click 'Continue to Passenger Details'", "m": "clickable", "st": ["Continue to Passenger Details"], "tf": None, "exp": "t70"},

    # Passenger Details
    {"n": "71", "step": "Select 'Mr' from 'Title'", "m": "select", "st": ["Mr", "Title"], "tf": None, "exp": "t71"},
    {"n": "72", "step": "Fill 'First Name' with 'Oleksii'", "m": "input", "st": ["First Name"], "tf": "first name", "exp": "t72"},
    {"n": "73", "step": "Fill 'Last Name' with 'Smith'", "m": "input", "st": ["Last Name"], "tf": "last name", "exp": "t73"},
    {"n": "74", "step": "Fill 'Date of Birth' with '1990-01-01'", "m": "input", "st": ["Date of Birth"], "tf": "date of birth", "exp": "t74"},
    {"n": "75", "step": "Select 'Ukraine' from 'Nationality'", "m": "select", "st": ["Ukraine", "Nationality"], "tf": None, "exp": "t75"},
    {"n": "76", "step": "Fill 'Passport Number' with 'XX12345'", "m": "input", "st": ["Passport Number"], "tf": "passport number", "exp": "t76"},
    {"n": "77", "step": "Fill 'Passport Expiry' with '2030-01-01'", "m": "input", "st": ["Passport Expiry"], "tf": "passport expiry", "exp": "t77"},
    {"n": "78", "step": "Fill 'Contact Email' with 'q@q.com'", "m": "input", "st": ["Contact Email"], "tf": "contact email", "exp": "t78"},
    {"n": "79", "step": "Fill 'Mobile Number' with '000'", "m": "input", "st": ["Mobile Number"], "tf": "mobile number", "exp": "t79"},
    {"n": "80", "step": "Click 'Save Passenger'", "m": "clickable", "st": ["Save Passenger"], "tf": None, "exp": "t80"},

    # Hotels
    {"n": "81", "step": "Fill 'Where are you going?' with 'Tokyo'", "m": "input", "st": ["Where are you going?"], "tf": "where are you going?", "exp": "t81"},
    {"n": "82", "step": "Click 'Search Hotels'", "m": "clickable", "st": ["Search Hotels"], "tf": None, "exp": "t82"},
    {"n": "83", "step": "Check 'traveling for work'", "m": "clickable", "st": ["traveling for work"], "tf": None, "exp": "t83"},
    {"n": "84", "step": "Click 'Map View'", "m": "clickable", "st": ["Map View"], "tf": None, "exp": "t84"},
    {"n": "85", "step": "Select '5 Stars' from 'Star Rating'", "m": "select", "st": ["5 Stars", "Star Rating"], "tf": None, "exp": "t85"},
    {"n": "86", "step": "Check 'Free Cancellation'", "m": "clickable", "st": ["Free Cancellation"], "tf": None, "exp": "t86"},
    {"n": "87", "step": "Check 'Breakfast Included'", "m": "clickable", "st": ["Breakfast Included"], "tf": None, "exp": "t87"},
    {"n": "88", "step": "Click 'Book Hilton'", "m": "clickable", "st": ["Book Hilton"], "tf": None, "exp": "t88"},
    {"n": "89", "step": "EXTRACT hotel price into {hp}", "ex": True, "var": "hp", "val": "$150/night"},
    {"n": "90", "step": "Click 'Read Guest Reviews'", "m": "clickable", "st": ["Read Guest Reviews"], "tf": None, "exp": "t90"},

    # Checkout
    {"n": "91", "step": "EXTRACT Flight Total into {ft}", "ex": True, "var": "ft", "val": "$250.00"},
    {"n": "92", "step": "EXTRACT Taxes into {tax}", "ex": True, "var": "tax", "val": "$45.50"},
    {"n": "93", "step": "EXTRACT Grand Total into {gt}", "ex": True, "var": "gt", "val": "$295.50"},
    {"n": "94", "step": "Fill 'Voucher Code' with 'SAVE50'", "m": "input", "st": ["Voucher Code"], "tf": "voucher code", "exp": "t94"},
    {"n": "95", "step": "Click 'Apply Voucher'", "m": "clickable", "st": ["Apply Voucher"], "tf": None, "exp": "t95"},
    {"n": "96", "step": "Check 'Terms & Conditions'", "m": "clickable", "st": ["Terms & Conditions"], "tf": None, "exp": "t96"},
    {"n": "97", "step": "Check 'Hazmat Policy'", "m": "clickable", "st": ["Hazmat Policy"], "tf": None, "exp": "t97"},
    {"n": "98", "step": "Click 'Pay Now'", "m": "clickable", "st": ["Pay Now"], "tf": None, "exp": "t98"},
    {"n": "99", "step": "Click 'Save Cart'", "m": "clickable", "st": ["Save Cart"], "tf": None, "exp": "t99"},
    {"n": "100", "step": "Click 'Back to Home'", "m": "clickable", "st": ["Back to Home"], "tf": None, "exp": "t100"},
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("✈️ TRAVEL & BOOKING HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(TRAVEL_DOM)

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