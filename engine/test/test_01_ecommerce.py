import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from playwright.async_api import async_playwright
from engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: E-commerce & Checkout (100 Elements)
# ─────────────────────────────────────────────────────────────────────────────
ECOMMERCE_DOM = """
<!DOCTYPE html><html><head><style>
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0;}
.color-swatch{width:30px;height:30px;display:inline-block;cursor:pointer;}
.hidden-input{display:none;}
.out-of-stock{opacity:0.5;pointer-events:none;}
</style></head><body>

<button id="e1">Add to Cart</button>
<div id="e2" role="button" aria-label="Add to Bag">🛒</div>
<a href="/cart/add/123" id="e3" class="btn">Add to Basket</a>
<button id="e4"><span class="sr-only">Add Product</span><svg><path d="cart"/></svg></button>
<input type="submit" id="e5" value="Buy Now">
<button id="e6" disabled>Add to Cart</button><button id="e7">Pre-order</button>
<div id="e8" onclick="addToCart()"><span class="text">Toss in Cart</span></div>
<button id="e9" data-qa="add-cart-btn">Add</button>
<button id="e10" class="add-to-cart-action">Submit</button>

<div class="price-box">Regular: <span id="e11">$49.99</span></div>
<div class="sale-box">Old: <s>$50</s> New: <strong id="e12" data-qa="sale-new">$39.99</strong></div>
<table><tr><td>MacBook</td><td id="e13">$1200</td></tr></table>
<div aria-label="Price is 15 dollars" id="e14">£15.00</div>
<span class="price"><span class="currency">€</span><span class="value" id="e15">99</span></span>
<div data-testid="product-amount" id="e16">1,450 UAH</div>
<p>Total: <b id="e17">250.50 PLN</b></p>
<div class="discount">Save 20%! Final: <span id="e18" data-qa="discount-final">$80</span></div>
<div id="e19">Price: Free</div>
<span id="e20">Contact for pricing</span>

<div role="radiogroup" aria-label="Size">
    <div role="radio" id="e21" aria-checked="false">Small</div>
    <div role="radio" id="e22" aria-checked="true">Medium</div>
    <div role="radio" id="e23" aria-checked="false" class="out-of-stock">Large</div>
</div>
<label for="e24_hidden">XL</label><input type="radio" id="e24_hidden" class="hidden-input" name="size">
<select id="e25"><option>Size</option><option>XXL</option></select>
<div aria-label="Color Red" id="e26" class="color-swatch" style="background:red;"></div>
<div aria-label="Color Blue" id="e27" class="color-swatch" style="background:blue;"></div>
<button id="e28" aria-label="Select Green Variant" class="color-swatch" style="background:green;"></button>
<input type="radio" name="color" id="e29" value="black"><label for="e29">Black</label>
<div data-value="white" id="e30" class="swatch-white">White Variant</div>

<div><button id="e31_minus">-</button><input type="text" id="e32_qty" value="1"><button id="e33_plus">+</button></div>
<input type="number" id="e34" aria-label="Item Quantity" min="1">
<select id="e35" aria-label="Qty"><option>1</option><option>2</option><option>3</option></select>
<label for="e36">Qty <input type="number" id="e36"></label>
<label>Gift Wrap Qty <input type="number" id="e37" min="0" aria-label="Gift Wrap Qty"></label>
<button id="e38" aria-label="Increase quantity">▲</button>
<button id="e39" aria-label="Decrease quantity">▼</button>
<input type="number" id="e40_moq" aria-label="Minimum Order" min="1">

<fieldset>
    <legend>Delivery Method</legend>
    <label><input type="radio" name="ship" id="e41"> Standard ($5)</label>
    <label><input type="radio" name="ship" id="e42"> Express ($15)</label>
    <label><input type="radio" name="ship" id="e43"> Pickup (Free)</label>
</fieldset>
<div role="radio" id="e44" aria-label="Next Day Delivery">Next Day</div>
<select id="e45" aria-label="Courier"><option>FedEx</option><option>DHL</option></select>
<button id="e46" class="select-shipping-btn">Choose UPS</button>
<div id="e47" data-qa="shipping-dhl">Select DHL</div>
<input type="checkbox" id="e48"><label for="e48">Gift Wrap</label>
<label id="e49_lbl"><input type="checkbox" id="e49"> Add Insurance</label>
<button id="e50">Calculate Shipping</button>

<div><label for="e51">Discount Code</label><input type="text" id="e51"></div>
<div><input type="text" id="e52" placeholder="Got a promo code?"></div>
<input type="text" id="e53" aria-label="Voucher">
<button id="e54">Apply Code</button>
<div id="e55" role="button">Redeem</div>
<a href="#" id="e56">Apply Coupon</a>
<input type="text" id="e57" data-testid="promo-input">
<button id="e58" data-testid="promo-submit">Apply</button>
<div class="promo-box"><span id="e59" class="sr-only">Enter Code</span><input type="text" id="e60" aria-label="Enter Code"></div>

<div id="shipping_section">
    <h3>Shipping Address</h3>
    <input type="text" id="e61" placeholder="First Name">
    <input type="text" id="e62" placeholder="Last Name">
    <input type="text" id="e63" placeholder="Street Address">
    <input type="text" id="e64" aria-label="City">
    <select id="e65" aria-label="State"><option>CA</option><option>NY</option></select>
    <input type="text" id="e66" placeholder="ZIP Code">
    <input type="tel" id="e67" placeholder="Phone">
    <input type="email" id="e68" placeholder="Email">
</div>
<label><input type="checkbox" id="e69" checked> Billing same as shipping</label>
<div id="billing_section">
    <h3>Billing Address</h3>
    <input type="text" id="e70" placeholder="First Name">
    <input type="text" id="e71" placeholder="Last Name">
    <input type="text" id="e72" placeholder="Street Address">
    <input type="text" id="e73" aria-label="City">
    <select id="e74" aria-label="State"><option>CA</option><option>NY</option></select>
    <input type="text" id="e75" placeholder="ZIP Code">
    <input type="tel" id="e76" placeholder="Phone">
    <input type="email" id="e77" placeholder="Email">
    <input type="text" id="e78" placeholder="Company (Optional)">
    <input type="text" id="e79" placeholder="Tax ID">
</div>
<button id="e80">Continue to Payment</button>

<input type="radio" id="e81" name="pay"><label for="e81">Credit Card</label>
<input type="radio" id="e82" name="pay"><label for="e82">PayPal</label>
<div role="button" id="e83" aria-label="Pay with Apple Pay">🍏 Pay</div>
<input type="text" id="e84" placeholder="Card Number" autocomplete="cc-number">
<input type="text" id="e85" placeholder="MM/YY" aria-label="Expiration Date">
<input type="text" id="e86" placeholder="CVC" aria-label="Security Code">
<input type="text" id="e87" placeholder="Name on Card">
<iframe id="stripe_frame" title="Secure Payment"></iframe> <button id="e88">Place Order</button>
<button id="e89" class="pay-btn"><svg><path d="lock"/></svg> Pay $99.00</button>
<div id="e90" role="checkbox" aria-checked="false">Save card for future</div>

<div class="modal">
    <button id="e91" aria-label="Close Newsletter">X</button>
    <input type="email" id="e92" placeholder="Subscribe for 10% off">
    <button id="e93">Subscribe</button>
    <a href="#" id="e94">No thanks, I prefer paying full price</a>
</div>
<div class="review">
    <div role="button" id="e95" aria-label="Write a Review">Write Review</div>
    <div role="radiogroup" aria-label="Rating">
        <span role="radio" id="e96" aria-label="5 Stars">⭐⭐⭐⭐⭐</span>
    </div>
    <input type="text" id="e97" placeholder="Review Title">
    <textarea id="e98" placeholder="Your experience..."></textarea>
    <button id="e99">Submit Review</button>
    <button id="e100" style="display:none;">Hidden Spam Trap</button>
</div>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-100
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # Cart Buttons (1-10)
    {"n": "1", "step": "Click 'Add to Cart'", "m": "clickable", "st": ["Add to Cart"], "tf": None, "exp": "e1"},
    {"n": "2", "step": "Click 'Add to Bag'", "m": "clickable", "st": ["Add to Bag"], "tf": None, "exp": "e2"},
    {"n": "3", "step": "Click 'Add to Basket'", "m": "clickable", "st": ["Add to Basket"], "tf": None, "exp": "e3"},
    {"n": "4", "step": "Click 'Add Product'", "m": "clickable", "st": ["Add Product"], "tf": None, "exp": "e4"},
    {"n": "5", "step": "Click 'Buy Now'", "m": "clickable", "st": ["Buy Now"], "tf": None, "exp": "e5"},
    {"n": "6", "step": "Click 'Pre-order'", "m": "clickable", "st": ["Pre-order"], "tf": None, "exp": "e7"}, # Should skip disabled e6
    {"n": "7", "step": "Click 'Toss in Cart'", "m": "clickable", "st": ["Toss in Cart"], "tf": None, "exp": "e8"},
    {"n": "8", "step": "Click 'Add'", "m": "clickable", "st": ["Add"], "tf": None, "exp": "e9"},
    {"n": "9", "step": "Click the 'Submit' button", "m": "clickable", "st": ["Submit"], "tf": None, "exp": "e10"},
    {"n": "10", "step": "Click 'Add' (fallback)", "m": "clickable", "st": ["Add"], "tf": None, "exp": "e9"},
    
    # Prices (11-20)
    {"n": "11", "step": "EXTRACT Regular price into {p}", "ex": True, "var": "p", "val": "$49.99"},
    {"n": "12", "step": "EXTRACT New price into {p}", "ex": True, "var": "p", "val": "$39.99"},
    {"n": "13", "step": "EXTRACT price of 'MacBook' into {p}", "ex": True, "var": "p", "val": "$1200"},
    {"n": "14", "step": "EXTRACT £ price into {p}", "ex": True, "var": "p", "val": "£15.00"},
    {"n": "15", "step": "EXTRACT € price into {p}", "ex": True, "var": "p", "val": "€99"},
    {"n": "16", "step": "EXTRACT UAH price into {p}", "ex": True, "var": "p", "val": "1,450 UAH"},
    {"n": "17", "step": "EXTRACT Total into {p}", "ex": True, "var": "p", "val": "250.50 PLN"},
    {"n": "18", "step": "EXTRACT Final price into {p}", "ex": True, "var": "p", "val": "$80"},
    {"n": "19", "step": "EXTRACT Price into {p}", "ex": True, "var": "p", "val": "Free"},
    {"n": "20", "step": "VERIFY that 'Contact for pricing' is present.", "ver": True, "res": True},

    # Size/Color (21-30)
    {"n": "21", "step": "Click 'Small'", "m": "clickable", "st": ["Small"], "tf": None, "exp": "e21"},
    {"n": "22", "step": "Click 'Medium'", "m": "clickable", "st": ["Medium"], "tf": None, "exp": "e22"},
    {"n": "23", "step": "Click 'Large'", "m": "clickable", "st": ["Large"], "tf": None, "exp": "e23"},
    {"n": "24", "step": "Click the radio button for 'XL'", "m": "clickable", "st": ["XL"], "tf": None, "exp": "e24_hidden"},
    {"n": "25", "step": "Select 'XXL' from 'Size'", "m": "select", "st": ["XXL", "Size"], "tf": None, "exp": "e25"},
    {"n": "26", "step": "Click 'Color Red'", "m": "clickable", "st": ["Color Red"], "tf": None, "exp": "e26"},
    {"n": "27", "step": "Click 'Color Blue'", "m": "clickable", "st": ["Color Blue"], "tf": None, "exp": "e27"},
    {"n": "28", "step": "Click 'Green Variant'", "m": "clickable", "st": ["Green Variant"], "tf": None, "exp": "e28"},
    {"n": "29", "step": "Click 'Black'", "m": "clickable", "st": ["Black"], "tf": None, "exp": "e29"},
    {"n": "30", "step": "Click 'White Variant'", "m": "clickable", "st": ["White Variant"], "tf": None, "exp": "e30"},

    # Qty (31-40)
    {"n": "31", "step": "Click '-'", "m": "clickable", "st": ["-"], "tf": None, "exp": "e31_minus"},
    {"n": "32", "step": "Fill 'e32_qty' with '2'", "m": "input", "st": ["e32_qty"], "tf": "e32_qty", "exp": "e32_qty"}, # ID match
    {"n": "33", "step": "Click '+'", "m": "clickable", "st": ["+"], "tf": None, "exp": "e33_plus"},
    {"n": "34", "step": "Fill 'Item Quantity' with '5'", "m": "input", "st": ["Item Quantity"], "tf": "item quantity", "exp": "e34"},
    {"n": "35", "step": "Select '3' from 'Qty'", "m": "select", "st": ["3", "Qty"], "tf": None, "exp": "e35"},
    {"n": "36", "step": "Fill 'Qty' field with '10'", "m": "input", "st": ["Qty"], "tf": "qty", "exp": "e36"},
    {"n": "37", "step": "Fill 'Gift Wrap Qty' with '4'", "m": "input", "st": ["Gift Wrap Qty"], "tf": "gift wrap qty", "exp": "e37"},
    {"n": "38", "step": "Click 'Increase quantity'", "m": "clickable", "st": ["Increase quantity"], "tf": None, "exp": "e38"},
    {"n": "39", "step": "Click 'Decrease quantity'", "m": "clickable", "st": ["Decrease quantity"], "tf": None, "exp": "e39"},
    {"n": "40", "step": "Fill 'Minimum Order' with '2'", "m": "input", "st": ["Minimum Order"], "tf": "minimum order", "exp": "e40_moq"},

    # Shipping (41-50)
    {"n": "41", "step": "Click 'Standard'", "m": "clickable", "st": ["Standard"], "tf": None, "exp": "e41"},
    {"n": "42", "step": "Click 'Express'", "m": "clickable", "st": ["Express"], "tf": None, "exp": "e42"},
    {"n": "43", "step": "Click 'Pickup'", "m": "clickable", "st": ["Pickup"], "tf": None, "exp": "e43"},
    {"n": "44", "step": "Click 'Next Day Delivery'", "m": "clickable", "st": ["Next Day Delivery"], "tf": None, "exp": "e44"},
    {"n": "45", "step": "Select 'DHL' from 'Courier'", "m": "select", "st": ["DHL", "Courier"], "tf": None, "exp": "e45"},
    {"n": "46", "step": "Click 'Choose UPS'", "m": "clickable", "st": ["Choose UPS"], "tf": None, "exp": "e46"},
    {"n": "47", "step": "Click 'Select DHL'", "m": "clickable", "st": ["Select DHL"], "tf": None, "exp": "e47"},
    {"n": "48", "step": "Check the 'Gift Wrap' checkbox", "m": "clickable", "st": ["Gift Wrap"], "tf": None, "exp": "e48"},
    {"n": "49", "step": "Check 'Add Insurance'", "m": "clickable", "st": ["Add Insurance"], "tf": None, "exp": "e49"},
    {"n": "50", "step": "Click 'Calculate Shipping'", "m": "clickable", "st": ["Calculate Shipping"], "tf": None, "exp": "e50"},

    # Promo (51-60)
    {"n": "51", "step": "Fill 'Discount Code' with 'SALE'", "m": "input", "st": ["Discount Code"], "tf": "discount code", "exp": "e51"},
    {"n": "52", "step": "Fill 'Got a promo code?' with 'TEST'", "m": "input", "st": ["Got a promo code?"], "tf": "got a promo code?", "exp": "e52"},
    {"n": "53", "step": "Fill 'Voucher' with 'FREE'", "m": "input", "st": ["Voucher"], "tf": "voucher", "exp": "e53"},
    {"n": "54", "step": "Click 'Apply Code'", "m": "clickable", "st": ["Apply Code"], "tf": None, "exp": "e54"},
    {"n": "55", "step": "Click 'Redeem'", "m": "clickable", "st": ["Redeem"], "tf": None, "exp": "e55"},
    {"n": "56", "step": "Click 'Apply Coupon'", "m": "clickable", "st": ["Apply Coupon"], "tf": None, "exp": "e56"},
    {"n": "57", "step": "Fill 'promo-input' with 'ABC'", "m": "input", "st": ["promo-input"], "tf": "promo-input", "exp": "e57"},
    {"n": "58", "step": "Click 'Apply' (promo-submit)", "m": "clickable", "st": ["Apply", "promo-submit"], "tf": None, "exp": "e58"},
    {"n": "59", "step": "VERIFY 'Enter Code' is present", "ver": True, "res": True},
    {"n": "60", "step": "Fill 'Enter Code' with '123'", "m": "input", "st": ["Enter Code"], "tf": "enter code", "exp": "e60"},

    # Shipping Form (61-69)
    {"n": "61", "step": "Fill 'First Name' in Shipping with 'John'", "m": "input", "st": ["First Name", "Shipping"], "tf": "first name", "exp": "e61"},
    {"n": "62", "step": "Fill 'Last Name' in Shipping with 'Doe'", "m": "input", "st": ["Last Name", "Shipping"], "tf": "last name", "exp": "e62"},
    {"n": "63", "step": "Fill 'Street Address' in Shipping with 'Main St'", "m": "input", "st": ["Street Address", "Shipping"], "tf": "street address", "exp": "e63"},
    {"n": "64", "step": "Fill 'City' in Shipping with 'NY'", "m": "input", "st": ["City", "Shipping"], "tf": "city", "exp": "e64"},
    {"n": "65", "step": "Select 'NY' from 'State' in Shipping", "m": "select", "st": ["NY", "State", "Shipping"], "tf": None, "exp": "e65"},
    {"n": "66", "step": "Fill 'ZIP Code' in Shipping with '10001'", "m": "input", "st": ["ZIP Code", "Shipping"], "tf": "zip code", "exp": "e66"},
    {"n": "67", "step": "Fill 'Phone' in Shipping with '123'", "m": "input", "st": ["Phone", "Shipping"], "tf": "phone", "exp": "e67"},
    {"n": "68", "step": "Fill 'Email' in Shipping with 'a@b.com'", "m": "input", "st": ["Email", "Shipping"], "tf": "email", "exp": "e68"},
    {"n": "69", "step": "Uncheck 'Billing same as shipping'", "m": "clickable", "st": ["Billing same as shipping"], "tf": None, "exp": "e69"},

    # Billing Form (70-80)
    {"n": "70", "step": "Fill 'First Name' in Billing with 'Jane'", "m": "input", "st": ["First Name", "Billing Address"], "tf": "first name", "exp": "e70"},
    {"n": "71", "step": "Fill 'Last Name' in Billing with 'Smith'", "m": "input", "st": ["Last Name", "Billing Address"], "tf": "last name", "exp": "e71"},
    {"n": "72", "step": "Fill 'Street Address' in Billing with 'Oak St'", "m": "input", "st": ["Street Address", "Billing Address"], "tf": "street address", "exp": "e72"},
    {"n": "73", "step": "Fill 'City' in Billing with 'LA'", "m": "input", "st": ["City", "Billing Address"], "tf": "city", "exp": "e73"},
    {"n": "74", "step": "Select 'CA' from 'State' in Billing", "m": "select", "st": ["CA", "State", "Billing Address"], "tf": None, "exp": "e74"},
    {"n": "75", "step": "Fill 'ZIP Code' in Billing with '90001'", "m": "input", "st": ["ZIP Code", "Billing Address"], "tf": "zip code", "exp": "e75"},
    {"n": "76", "step": "Fill 'Phone' in Billing with '999'", "m": "input", "st": ["Phone", "Billing Address"], "tf": "phone", "exp": "e76"},
    {"n": "77", "step": "Fill 'Email' in Billing with 'c@d.com'", "m": "input", "st": ["Email", "Billing Address"], "tf": "email", "exp": "e77"},
    {"n": "78", "step": "Fill 'Company' with 'Acme'", "m": "input", "st": ["Company"], "tf": "company", "exp": "e78"},
    {"n": "79", "step": "Fill 'Tax ID' with '123'", "m": "input", "st": ["Tax ID"], "tf": "tax id", "exp": "e79"},
    {"n": "80", "step": "Click 'Continue to Payment'", "m": "clickable", "st": ["Continue to Payment"], "tf": None, "exp": "e80"},

    # Payment (81-90)
    {"n": "81", "step": "Click 'Credit Card'", "m": "clickable", "st": ["Credit Card"], "tf": None, "exp": "e81"},
    {"n": "82", "step": "Click 'PayPal'", "m": "clickable", "st": ["PayPal"], "tf": None, "exp": "e82"},
    {"n": "83", "step": "Click 'Pay with Apple Pay'", "m": "clickable", "st": ["Pay with Apple Pay"], "tf": None, "exp": "e83"},
    {"n": "84", "step": "Fill 'Card Number' with '4444'", "m": "input", "st": ["Card Number"], "tf": "card number", "exp": "e84"},
    {"n": "85", "step": "Fill 'Expiration Date' with '12/26'", "m": "input", "st": ["Expiration Date"], "tf": "expiration date", "exp": "e85"},
    {"n": "86", "step": "Fill 'Security Code' with '123'", "m": "input", "st": ["Security Code"], "tf": "security code", "exp": "e86"},
    {"n": "87", "step": "Fill 'Name on Card' with 'Bob'", "m": "input", "st": ["Name on Card"], "tf": "name on card", "exp": "e87"},
    {"n": "88", "step": "Click 'Place Order'", "m": "clickable", "st": ["Place Order"], "tf": None, "exp": "e88"},
    {"n": "89", "step": "Click 'Pay $99.00'", "m": "clickable", "st": ["Pay $99.00"], "tf": None, "exp": "e89"},
    {"n": "90", "step": "Click 'Save card for future'", "m": "clickable", "st": ["Save card for future"], "tf": None, "exp": "e90"},

    # Popups & Reviews (91-100)
    {"n": "91", "step": "Click 'Close Newsletter'", "m": "clickable", "st": ["Close Newsletter"], "tf": None, "exp": "e91"},
    {"n": "92", "step": "Fill 'Subscribe for 10% off' with 'x@y.com'", "m": "input", "st": ["Subscribe for 10% off"], "tf": "subscribe for 10% off", "exp": "e92"},
    {"n": "93", "step": "Click 'Subscribe'", "m": "clickable", "st": ["Subscribe"], "tf": None, "exp": "e93"},
    {"n": "94", "step": "Click 'No thanks'", "m": "clickable", "st": ["No thanks"], "tf": None, "exp": "e94"},
    {"n": "95", "step": "Click 'Write a Review'", "m": "clickable", "st": ["Write a Review"], "tf": None, "exp": "e95"},
    {"n": "96", "step": "Click '5 Stars'", "m": "clickable", "st": ["5 Stars"], "tf": None, "exp": "e96"},
    {"n": "97", "step": "Fill 'Review Title' with 'Awesome'", "m": "input", "st": ["Review Title"], "tf": "review title", "exp": "e97"},
    {"n": "98", "step": "Fill 'Your experience' with 'Good'", "m": "input", "st": ["Your experience"], "tf": "your experience", "exp": "e98"},
    {"n": "99", "step": "Click 'Submit Review'", "m": "clickable", "st": ["Submit Review"], "tf": None, "exp": "e99"},
    {"n": "100", "step": "Click 'Hidden Spam Trap' if exists", "m": "clickable", "st": ["Hidden Spam Trap"], "tf": None, "exp": None}, # Should gracefully skip
]

async def run_suite():
    print(f"\n{'=' * 70}")
    print("🛒 E-COMMERCE HELL: 100 REAL-WORLD TRAPS")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(ECOMMERCE_DOM)

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