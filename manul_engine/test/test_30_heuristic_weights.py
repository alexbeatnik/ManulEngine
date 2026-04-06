import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine
from manul_engine.scoring import DOMScorer, WEIGHTS, SCALE

# ─────────────────────────────────────────────────────────────────────────────
# HEURISTIC WEIGHTING LAB — DOMScorer Priority Hierarchy
#
# Validates:
# 1. data-qa exact match dominates over partial text/aria/placeholder
# 2. WEIGHTS dict priorities (cache > semantics > text > attributes > proximity)
# 3. SCALE constant maps floats to expected integer ranges
# 4. Penalty multipliers crush disabled/hidden elements
# 5. Element-type alignment (checkbox penalty, input/button synergy)
# ─────────────────────────────────────────────────────────────────────────────
WEIGHT_DOM = """
<!DOCTYPE html><html><head><title>Heuristic Weighting Lab</title></head><body>

<!-- Group 1: data-qa dominance — exact data-qa must beat aria/text match -->
<button id="dqa_exact"   data-qa="confirm-order">Proceed</button>
<button id="dqa_partial" data-qa="confirm-order-legacy">Confirm Order Legacy</button>
<button id="text_match"  >Confirm Order</button>
<button id="aria_match"  aria-label="Confirm Order">✓</button>

<!-- Group 2: aria-label vs placeholder vs text -->
<input  id="aria_input"  aria-label="Billing Address" type="text">
<input  id="ph_input"    placeholder="Billing Address" type="text">
<input  id="label_input" type="text"><label for="label_input">Billing Address</label>

<!-- Group 3: html_id alignment with target_field -->
<input  id="shipping_address" placeholder="Enter here" type="text">
<input  id="billing_info"     placeholder="Billing Info" type="text">

<!-- Group 4: disabled penalty (×0.0) -->
<button id="enabled_btn"  >Place Order</button>
<button id="disabled_btn" disabled>Place Order</button>

<!-- Group 5: hidden penalty (×0.1) -->
<button id="visible_btn">Apply Coupon</button>
<button id="hidden_btn" style="display:none;">Apply Coupon</button>

<!-- Group 6: checkbox/radio mode strictness -->
<input  id="chk_real"  type="checkbox"><label for="chk_real">Newsletter</label>
<button id="chk_decoy" >Newsletter</button>
<td     id="chk_td"    >Newsletter</td>

<!-- Group 7: input mode synergy — input fields should beat buttons -->
<input  id="input_field" placeholder="Search Query" type="text">
<button id="input_decoy" >Search Query</button>

<!-- Group 8: select mode — actual <select> should beat div -->
<select id="sel_real"><option>Red</option><option>Blue</option></select>
<div    id="sel_fake" role="button">Red</div>

<!-- Group 9: data-testid as data-qa fallback -->
<button id="testid_btn" data-testid="checkout-submit">Go</button>
<button id="text_go"    >Checkout Submit</button>

<!-- Group 10: exact text match vs substring -->
<button id="exact_save"    >Save</button>
<button id="substring_save">Save Draft Changes</button>

<!-- Group 11: name_attr matching -->
<input  id="name_attr_input" name="security_pin" type="password">
<input  id="name_generic"    placeholder="PIN" type="password">

<!-- Group 12: context words in developer names -->
<button id="ctx_dev"   class="btn-payment-finalize">Finalize Payment</button>
<button id="ctx_plain" >Finalize Payment</button>

<!-- Group 13: multiple stacked signals -->
<input  id="stacked_all"  data-qa="promo-code" placeholder="Promo Code" aria-label="Promo Code" type="text">
<input  id="stacked_one"  placeholder="Enter code" type="text">

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── Group 1: data-qa dominance ───────────────────────────────────────
    {
        "n": "1. data-qa exact beats text match",
        "step": "Click the 'Confirm Order' button",
        "m": "clickable",
        "st": ["Confirm Order"],
        "tf": None,
        "exp": "dqa_exact",
        "desc": "data-qa='confirm-order' scores +1.0 text; text='Confirm Order' scores +0.625",
    },
    {
        "n": "2. data-qa exact beats aria match",
        "step": "Click the 'Confirm Order' button",
        "m": "clickable",
        "st": ["Confirm Order"],
        "tf": None,
        "exp": "dqa_exact",
        "desc": "data-qa exact (+1.0) dominates aria-label exact (+0.625)",
    },
    # ── Group 2: aria vs placeholder ─────────────────────────────────────
    {
        "n": "3. Aria-label input",
        "step": "Fill 'Billing Address' field with '123 Main St'",
        "m": "input",
        "st": ["Billing Address"],
        "tf": "billing address",
        "exp": "aria_input",
        "desc": "aria-label exact match should resolve correctly",
    },
    {
        "n": "4. Placeholder input",
        "step": "Fill 'Billing Address' field with '123 Main St'",
        "m": "input",
        "st": ["Billing Address"],
        "tf": "billing address",
        "exp": "aria_input",
        "desc": "aria and placeholder both exact — either is acceptable, aria wins ties",
    },
    # ── Group 3: html_id alignment ──────────────────────────────────────
    {
        "n": "5. html_id aligns with target_field",
        "step": "Fill 'Shipping Address' field with '456 Oak Ave'",
        "m": "input",
        "st": ["Shipping Address"],
        "tf": "shipping address",
        "exp": "shipping_address",
        "desc": "html_id='shipping_address' matches target_field 'shipping address' (+0.6 attr)",
    },
    # ── Group 4: disabled penalty ──────────────────────────────────────
    {
        "n": "6. Enabled beats disabled (×0.0 penalty)",
        "step": "Click the 'Place Order' button",
        "m": "clickable",
        "st": ["Place Order"],
        "tf": None,
        "exp": "enabled_btn",
        "desc": "Disabled element gets penalty mult × 0.0 → score collapses to 0",
    },
    # ── Group 5: hidden penalty ─────────────────────────────────────────
    {
        "n": "7. Visible beats display:none (×0.1 penalty)",
        "step": "Click the 'Apply Coupon' button",
        "m": "clickable",
        "st": ["Apply Coupon"],
        "tf": None,
        "exp": "visible_btn",
        "desc": "Hidden element gets penalty mult × 0.1 → visible element wins easily",
    },
    # ── Group 6: checkbox strictness ────────────────────────────────────
    {
        "n": "8. Checkbox mode resolves real checkbox",
        "step": "Check the 'Newsletter' checkbox",
        "m": "clickable",
        "st": ["Newsletter"],
        "tf": None,
        "exp": "chk_real",
        "desc": "Step says 'Check' — real checkbox input must win over button/td",
    },
    # ── Group 7: input mode synergy ─────────────────────────────────────
    {
        "n": "9. Input field wins over button in input mode",
        "step": "Fill 'Search Query' field with 'manul cats'",
        "m": "input",
        "st": ["Search Query"],
        "tf": "search query",
        "exp": "input_field",
        "desc": "mode=input → input tag gets mode synergy bonus; button gets penalty",
    },
    # ── Group 8: select mode ────────────────────────────────────────────
    {
        "n": "10. Real <select> wins in select mode",
        "step": "Select 'Blue' from the dropdown",
        "m": "select",
        "st": ["Blue"],
        "tf": None,
        "exp": "sel_real",
        "desc": "mode=select → actual <select> tag gets type alignment bonus",
    },
    # ── Group 9: data-testid ─────────────────────────────────────────────
    {
        "n": "11. data-testid acts as data-qa",
        "step": "Click the 'Checkout Submit' button",
        "m": "clickable",
        "st": ["Checkout Submit"],
        "tf": None,
        "exp": "testid_btn",
        "desc": "SNAPSHOT_JS reads data-testid as fallback for data-qa → exact match",
    },
    # ── Group 10: exact vs substring ────────────────────────────────────
    {
        "n": "12. Exact text wins over substring",
        "step": "Click the 'Save' button",
        "m": "clickable",
        "st": ["Save"],
        "tf": None,
        "exp": "exact_save",
        "desc": "Exact text 'Save' > substring 'Save Draft Changes'",
    },
    # ── Group 11: name_attr ─────────────────────────────────────────────
    {
        "n": "13. name_attr exact match",
        "step": "Fill 'security_pin' field with '0000'",
        "m": "input",
        "st": ["security_pin"],
        "tf": "security pin",
        "exp": "name_attr_input",
        "desc": "HTML name='security_pin' exact match (+0.0375 text)",
    },
    # ── Group 12: context words ─────────────────────────────────────────
    {
        "n": "14. Dev-name context words boost",
        "step": "Click the 'Finalize Payment' button",
        "m": "clickable",
        "st": ["Finalize Payment"],
        "tf": None,
        "exp": "ctx_dev",
        "desc": "class='btn-payment-finalize' has context word 'payment' in dev names",
    },
    # ── Group 13: stacked signals ────────────────────────────────────────
    {
        "n": "15. Stacked signals (data-qa + placeholder + aria)",
        "step": "Fill 'Promo Code' field with 'MANUL2025'",
        "m": "input",
        "st": ["Promo Code"],
        "tf": "promo code",
        "exp": "stacked_all",
        "desc": "data-qa + placeholder + aria all match → stacked score dominates",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Unit-level DOMScorer assertions (no browser)
# ─────────────────────────────────────────────────────────────────────────────
_PASS = 0
_FAIL = 0


def _assert(cond: bool, name: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"    ✅  {name}")
    else:
        _FAIL += 1
        suffix = f" ({detail})" if detail else ""
        print(f"    ❌  {name}{suffix}")


def _test_weights_dict():
    print("\n── WEIGHTS dict ──")
    _assert("cache" in WEIGHTS, "cache key exists")
    _assert("text" in WEIGHTS, "text key exists")
    _assert("attributes" in WEIGHTS, "attributes key exists")
    _assert("semantics" in WEIGHTS, "semantics key exists")
    _assert("proximity" in WEIGHTS, "proximity key exists")
    _assert(
        WEIGHTS["cache"] > WEIGHTS["semantics"] > WEIGHTS["text"],
        "cache > semantics > text priority",
        f"{WEIGHTS['cache']} > {WEIGHTS['semantics']} > {WEIGHTS['text']}",
    )
    _assert(
        WEIGHTS["text"] > WEIGHTS["attributes"],
        "text > attributes priority",
        f"{WEIGHTS['text']} > {WEIGHTS['attributes']}",
    )
    _assert(
        WEIGHTS["attributes"] > WEIGHTS["proximity"],
        "attributes > proximity priority",
        f"{WEIGHTS['attributes']} > {WEIGHTS['proximity']}",
    )


def _test_scale_constant():
    print("\n── SCALE constant ──")
    _assert(isinstance(SCALE, int), "SCALE is an integer")
    _assert(SCALE > 100_000, "SCALE > 100k for integer range", f"SCALE={SCALE}")
    _assert(SCALE == 177_778, "SCALE = 177,778", f"SCALE={SCALE}")


def _test_scorer_data_qa_dominance():
    """Prove data-qa exact match outscores text match at the scorer level."""
    print("\n── DOMScorer: data-qa vs text ──")
    # Minimal element dicts matching _preprocess expectations
    el_dqa = {
        "name": "Proceed button",
        "xpath": "/btn[1]",
        "is_select": False,
        "is_shadow": False,
        "is_contenteditable": False,
        "class_name": "",
        "tag_name": "button",
        "input_type": "",
        "data_qa": "confirm-order",
        "html_id": "dqa_exact",
        "icon_classes": "",
        "aria_label": "",
        "placeholder": "",
        "role": "",
        "disabled": False,
        "aria_disabled": "",
        "name_attr": "",
        "id": 1,
    }
    el_text = {
        "name": "Confirm Order button",
        "xpath": "/btn[2]",
        "is_select": False,
        "is_shadow": False,
        "is_contenteditable": False,
        "class_name": "",
        "tag_name": "button",
        "input_type": "",
        "data_qa": "",
        "html_id": "text_match",
        "icon_classes": "",
        "aria_label": "",
        "placeholder": "",
        "role": "",
        "disabled": False,
        "aria_disabled": "",
        "name_attr": "",
        "id": 2,
    }

    scorer = DOMScorer(
        step="Click the 'Confirm Order' button",
        mode="clickable",
        search_texts=["Confirm Order"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
    )
    results = scorer.score_all([dict(el_dqa), dict(el_text)])

    dqa_score = next(e["score"] for e in results if e["html_id"] == "dqa_exact")
    txt_score = next(e["score"] for e in results if e["html_id"] == "text_match")

    _assert(dqa_score > txt_score, "data-qa exact score > text match score", f"dqa={dqa_score} vs txt={txt_score}")
    _assert(dqa_score > 10_000, "data-qa exact crosses 10k threshold", f"score={dqa_score}")


def _test_disabled_penalty():
    """Prove disabled elements get penalty multiplier → score ≈ 0."""
    print("\n── DOMScorer: disabled penalty ──")
    el_ok = {
        "name": "Submit button",
        "xpath": "/btn[1]",
        "is_select": False,
        "is_shadow": False,
        "is_contenteditable": False,
        "class_name": "",
        "tag_name": "button",
        "input_type": "",
        "data_qa": "",
        "html_id": "ok_btn",
        "icon_classes": "",
        "aria_label": "",
        "placeholder": "",
        "role": "",
        "disabled": False,
        "aria_disabled": "",
        "name_attr": "",
        "id": 1,
    }
    el_dis = dict(el_ok, html_id="dis_btn", id=2, disabled=True)

    scorer = DOMScorer(
        step="Click the 'Submit' button",
        mode="clickable",
        search_texts=["Submit"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
    )
    results = scorer.score_all([dict(el_ok), dict(el_dis)])

    ok_score = next(e["score"] for e in results if e["html_id"] == "ok_btn")
    dis_score = next(e["score"] for e in results if e["html_id"] == "dis_btn")

    _assert(ok_score > 0, "enabled element score > 0", f"score={ok_score}")
    _assert(dis_score == 0, "disabled element score = 0 (×0.0 penalty)", f"score={dis_score}")


def _test_hidden_penalty():
    """Prove [HIDDEN] elements get ×0.1 penalty multiplier."""
    print("\n── DOMScorer: hidden penalty ──")
    el_vis = {
        "name": "Save button",
        "xpath": "/btn[1]",
        "is_select": False,
        "is_shadow": False,
        "is_contenteditable": False,
        "class_name": "",
        "tag_name": "button",
        "input_type": "",
        "data_qa": "",
        "html_id": "vis_btn",
        "icon_classes": "",
        "aria_label": "",
        "placeholder": "",
        "role": "",
        "disabled": False,
        "aria_disabled": "",
        "name_attr": "",
        "id": 1,
    }
    el_hid = dict(el_vis, html_id="hid_btn", id=2, name="Save button [HIDDEN]")

    scorer = DOMScorer(
        step="Click the 'Save' button",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
    )
    results = scorer.score_all([dict(el_vis), dict(el_hid)])

    vis_score = next(e["score"] for e in results if e["html_id"] == "vis_btn")
    hid_score = next(e["score"] for e in results if e["html_id"] == "hid_btn")

    _assert(vis_score > hid_score, "visible score > hidden score", f"vis={vis_score} vs hid={hid_score}")
    # Hidden should be roughly 10% of visible (×0.1 multiplier)
    if vis_score > 0:
        ratio = hid_score / vis_score
        _assert(ratio < 0.15, "hidden/visible ratio < 0.15", f"ratio={ratio:.3f}")


async def run_suite():
    print(f"\n{'=' * 70}")
    print("⚖️   HEURISTIC WEIGHTING LAB — DOMScorer Priority Hierarchy")
    print(f"{'=' * 70}")

    # ── Part 1: Unit-level DOMScorer tests (no browser) ───────────────
    print(f"\n{'─' * 70}")
    print("📐 Part 1: DOMScorer Unit Tests (no browser)")
    print(f"{'─' * 70}")
    _test_weights_dict()
    _test_scale_constant()
    _test_scorer_data_qa_dominance()
    _test_disabled_penalty()
    _test_hidden_penalty()

    unit_passed = _PASS
    unit_total = _PASS + _FAIL

    # ── Part 2: Browser-level resolution tests ──────────────────────
    print(f"\n{'─' * 70}")
    print(f"🌐 Part 2: Browser Resolution Tests ({len(TESTS)} traps)")
    print(f"{'─' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(WEIGHT_DOM)

        browser_passed = browser_failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n⚖️  {t['n']}")
            if t.get("desc"):
                print(f"   📋 {t['desc']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

            el = await manul._resolve_element(page, t["step"], t["m"], t["st"], t["tf"], "", set())

            if el is None:
                msg = "FAILED — element not found (None)"
                print(f"   ❌ {msg}")
                browser_failed += 1
                failures.append(f"{t['n']}: {msg}")
                continue

            found_id = el.get("html_id", "")
            if found_id == t["exp"]:
                print(f"   ✅ PASSED  → '{found_id}'")
                browser_passed += 1
            else:
                msg = f"FAILED — got '{found_id}', expected '{t['exp']}'"
                print(f"   ❌ {msg}")
                browser_failed += 1
                failures.append(f"{t['n']}: {msg}")

        total = unit_total + len(TESTS)
        total_passed = unit_passed + browser_passed

        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {total_passed}/{total} passed")
        print(f"   Unit:    {unit_passed}/{unit_total}")
        print(f"   Browser: {browser_passed}/{len(TESTS)}")
        if failures:
            print("\n🙀 Failures:")
            for f in failures:
                print(f"   • {f}")
        if total_passed == total:
            print("\n🏆 HEURISTIC WEIGHTING FLAWLESS — DOMScorer priorities are airtight!")
        print(f"{'=' * 70}")
        await browser.close()

    return total_passed == total


if __name__ == "__main__":
    asyncio.run(run_suite())
