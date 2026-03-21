import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from manul_engine.scoring import DOMScorer

# ─────────────────────────────────────────────────────────────────────────────
# ATTRIBUTE SEMANTIC KEYWORD MATCH LAB — 31 scenarios / 34 assertions
#
# Validates that elements whose visible text is unrelated (e.g. a badge
# count "2") but whose html_id, class_name, or data_qa contain semantic
# keywords matching the user's search term are scored highly enough to
# pass the engine's confidence thresholds.
#
# Covers: shopping cart icons, notification badges, hamburger menus,
# user profile icons, search icons, multi-class matching, camelCase
# fallback, partial coverage, single-word terms, and false-positive
# resistance.
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


def _make_el(**overrides) -> dict:
    base = {
        "name": overrides.pop("name", ""),
        "xpath": overrides.pop("xpath", "/html/body/a[1]"),
        "is_select": False, "is_shadow": False, "is_contenteditable": False,
        "class_name": "", "tag_name": "a", "input_type": "",
        "data_qa": "", "html_id": "", "icon_classes": "",
        "aria_label": "", "placeholder": "", "role": "",
        "disabled": False, "aria_disabled": "", "name_attr": "",
        "id": 1,
    }
    base.update(overrides)
    return base


def _make_scorer(**kw) -> DOMScorer:
    return DOMScorer(
        step=kw.get("step", "Click the 'Shopping cart'"),
        mode=kw.get("mode", "clickable"),
        search_texts=kw.get("search_texts", ["Shopping cart"]),
        target_field=kw.get("target_field", None),
        is_blind=kw.get("is_blind", False),
        learned_elements=kw.get("learned_elements", {}),
        last_xpath=kw.get("last_xpath", None),
    )


# ── 1: Shopping cart link with class_name, visible text is badge count ────────

def _test_cart_class_badge_text():
    print("\n── Cart icon: class_name match, visible text '2' ──")
    el = _make_el(
        name="2",
        class_name="shopping_cart_link",
        tag_name="a",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"shopping_cart_link ≥ 10k, got {score}")


# ── 2: Shopping cart container by html_id ─────────────────────────────────────

def _test_cart_id():
    print("\n── Cart icon: html_id match ──")
    el = _make_el(
        name="2",
        html_id="shopping_cart_container",
        tag_name="a",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"shopping_cart_container ≥ 10k, got {score}")


# ── 3: Cart with data_qa ─────────────────────────────────────────────────────

def _test_cart_data_qa():
    print("\n── Cart icon: data_qa match ──")
    el = _make_el(
        name="0",
        data_qa="shopping-cart-badge",
        tag_name="span",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"shopping-cart-badge data-qa ≥ 10k, got {score}")


# ── 4: Single-word "Cart" search against class ───────────────────────────────

def _test_single_word_cart():
    print("\n── Single word 'Cart' vs class with cart ──")
    el = _make_el(
        name="3",
        class_name="header_cart_icon",
        tag_name="a",
    )
    scorer = _make_scorer(
        step="Click the 'Cart'",
        search_texts=["Cart"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"single-word cart ≥ 10k, got {score}")


# ── 5: "Basket" keyword in class ─────────────────────────────────────────────

def _test_basket_keyword():
    print("\n── 'Basket' keyword in class_name ──")
    el = _make_el(
        name="Items: 1",
        class_name="mini_basket_trigger",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Basket'",
        search_texts=["Basket"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"basket class ≥ 10k, got {score}")


# ── 6: Notification bell icon ─────────────────────────────────────────────────

def _test_notification_bell():
    print("\n── Notification bell: class + badge ──")
    el = _make_el(
        name="5",
        class_name="notification_bell",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Notification bell'",
        search_texts=["Notification bell"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"notification_bell ≥ 10k, got {score}")


# ── 7: Hamburger menu icon ───────────────────────────────────────────────────

def _test_hamburger_menu():
    print("\n── Hamburger menu: id=nav_menu, text '☰' ──")
    el = _make_el(
        name="☰",
        html_id="nav_menu_btn",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Menu' button",
        search_texts=["Menu"],
        mode="clickable",
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 5_000, f"nav_menu_btn ≥ 5k, got {score}")


# ── 8: User profile icon ─────────────────────────────────────────────────────

def _test_user_profile():
    print("\n── User profile: class=user_profile_icon, text '👤' ──")
    el = _make_el(
        name="👤",
        class_name="user_profile_icon",
        tag_name="a",
    )
    scorer = _make_scorer(
        step="Click the 'User profile'",
        search_texts=["User profile"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"user_profile ≥ 10k, got {score}")


# ── 9: Cart link BEATS plain text element ─────────────────────────────────────

def _test_cart_beats_plain_number():
    print("\n── Cart link must outscore a plain <span> with same text ──")
    cart = _make_el(
        name="2",
        class_name="shopping_cart_link",
        tag_name="a",
        id=1,
    )
    plain_span = _make_el(
        name="2 items in your list",
        tag_name="span",
        id=2,
    )
    scorer = _make_scorer()
    results = scorer.score_all([cart, plain_span])
    _assert(results[0]["id"] == 1, f"cart link wins, top id={results[0]['id']}")


# ── 10: Cart beats disabled cart ──────────────────────────────────────────────

def _test_cart_beats_disabled():
    print("\n── Enabled cart link beats disabled cart ──")
    enabled = _make_el(
        name="2",
        class_name="shopping_cart_link",
        tag_name="a",
        id=1,
    )
    disabled = _make_el(
        name="Cart",
        class_name="shopping_cart_link",
        tag_name="a",
        disabled=True,
        id=2,
    )
    scorer = _make_scorer()
    results = scorer.score_all([enabled, disabled])
    _assert(results[0]["id"] == 1, f"enabled cart wins, top id={results[0]['id']}")


# ── 11: Multi-class element with cart keyword ─────────────────────────────────

def _test_multi_class():
    print("\n── Multi-class: 'btn primary shopping_cart_action' ──")
    el = _make_el(
        name="🛒",
        class_name="btn primary shopping_cart_action",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"multi-class cart ≥ 10k, got {score}")


# ── 12: Partial coverage — 1 of 2 words match ────────────────────────────────

def _test_partial_coverage():
    print("\n── Partial: 'shopping' in class but no 'cart' ──")
    el = _make_el(
        name="Deals",
        class_name="shopping_deals_banner",
        tag_name="div",
    )
    full_cart = _make_el(
        name="2",
        class_name="shopping_cart_link",
        tag_name="a",
        id=2,
    )
    scorer = _make_scorer()
    results = scorer.score_all([el, full_cart])
    # Full coverage cart should outscore partial
    _assert(results[0]["id"] == 2, f"full coverage cart wins, top id={results[0]['id']}")


# ── 13: Search icon with no visible text ──────────────────────────────────────

def _test_search_icon():
    print("\n── Search icon: class=search_btn, no text ──")
    el = _make_el(
        name="",
        class_name="search_btn_icon",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Search' button",
        search_texts=["Search"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 5_000, f"search_btn_icon ≥ 5k, got {score}")


# ── 14: Checkout button vs cart icon — both have "cart" context ───────────────

def _test_checkout_vs_cart():
    print("\n── 'Shopping cart' should prefer shopping_cart class over checkout ──")
    cart = _make_el(
        name="2",
        class_name="shopping_cart_link",
        tag_name="a",
        id=1,
    )
    checkout = _make_el(
        name="Proceed to Checkout button",
        class_name="checkout_btn",
        tag_name="button",
        role="button",
        id=2,
    )
    scorer = _make_scorer()
    results = scorer.score_all([cart, checkout])
    _assert(results[0]["id"] == 1, f"cart icon wins over checkout, top id={results[0]['id']}")


# ── 15: data-qa with dashes matches search term with spaces ──────────────────

def _test_data_qa_dashes():
    print("\n── data-qa='shopping-cart' matches 'Shopping cart' ──")
    el = _make_el(
        name="",
        data_qa="shopping-cart",
        tag_name="a",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    # data-qa exact dashed match gives +1.0 text — very high
    _assert(score >= 70_000, f"data-qa dashed exact ≥ 70k, got {score}")


# ── 16: html_id with underscores matches multi-word search ────────────────────

def _test_id_underscores():
    print("\n── html_id='shopping_cart' attr semantic match ──")
    el = _make_el(
        name="",
        html_id="shopping_cart",
        tag_name="a",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"id underscore semantic ≥ 10k, got {score}")


# ── 17: camelCase class_name matches multi-word search ───────────────────────

def _test_camel_case_class():
    print("\n── className='shoppingCartLink' semantic match ──")
    el = _make_el(
        name="2",
        class_name="shoppingCartLink",
        tag_name="a",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"camelCase cart ≥ 10k, got {score}")


# ── 18: False positive resistance — unrelated class ──────────────────────────

def _test_false_positive_unrelated():
    print("\n── Unrelated class 'footer_links' should NOT score high ──")
    el = _make_el(
        name="About Us",
        class_name="footer_links",
        tag_name="a",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score < 10_000, f"unrelated class < 10k, got {score}")


# ── 19: False positive — "cart" as substring of unrelated word ────────────────

def _test_false_positive_substring():
    print("\n── 'cartography_section' should not get full cart boost ──")
    el = _make_el(
        name="Maps",
        class_name="cartography_section",
        tag_name="div",
    )
    # "cartography" splits to "cartography" — not "cart"
    scorer = _make_scorer(
        step="Click the 'Cart'",
        search_texts=["Cart"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    # "cart" is a substring of "cartography" but NOT a discrete token
    _assert(score < 10_000, f"cartography false positive < 10k, got {score}")


# ── 20: Hidden cart element gets penalty ──────────────────────────────────────

def _test_hidden_cart():
    print("\n── Hidden cart gets ×0.1 penalty ──")
    el = _make_el(
        name="2 [hidden]",
        class_name="shopping_cart_link",
        tag_name="a",
    )
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]
    visible = _make_el(
        name="2",
        class_name="shopping_cart_link",
        tag_name="a",
        id=2,
    )
    results2 = scorer.score_all([visible])
    visible_score = results2[0]["score"]
    _assert(score < visible_score, f"hidden ({score}) < visible ({visible_score})")


# ── 21: SauceDemo-style cart — realistic scenario ─────────────────────────────

def _test_saucedemo_cart():
    print("\n── SauceDemo: <a class='shopping_cart_link'><span class='shopping_cart_badge'>2</span></a> ──")
    link = _make_el(
        name="2",
        html_id="shopping_cart_container",
        class_name="shopping_cart_link",
        tag_name="a",
        id=1,
    )
    badge = _make_el(
        name="2",
        class_name="shopping_cart_badge",
        tag_name="span",
        id=2,
    )
    scorer = _make_scorer()
    results = scorer.score_all([link, badge])
    _assert(results[0]["score"] >= 10_000, f"SauceDemo cart link ≥ 10k, got {results[0]['score']}")
    # The <a> should win because it gets mode synergy for being a link
    _assert(results[0]["id"] == 1, f"<a> cart wins over <span> badge, top id={results[0]['id']}")


# ── 22: Wishlist icon — "wish_list" class ─────────────────────────────────────

def _test_wishlist():
    print("\n── Wishlist: class=wish_list_icon ──")
    el = _make_el(
        name="♡",
        class_name="wish_list_icon",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Wish list'",
        search_texts=["Wish list"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"wish_list ≥ 10k, got {score}")


# ── 23: Close button — "close_modal_btn" ─────────────────────────────────────

def _test_close_modal():
    print("\n── Close button: id=close_modal_btn, text 'X' ──")
    el = _make_el(
        name="X",
        html_id="close_modal_btn",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Close modal' button",
        search_texts=["Close modal"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"close_modal ≥ 10k, got {score}")


# ── 24: Add-to-cart button with data-qa and competing text ───────────────────

def _test_add_to_cart_data_qa_wins():
    print("\n── data-qa='add-to-cart' beats text-only match ──")
    with_dqa = _make_el(
        name="Submit",
        data_qa="add-to-cart",
        tag_name="button",
        role="button",
        id=1,
    )
    text_only = _make_el(
        name="Add to Cart button",
        tag_name="button",
        role="button",
        id=2,
    )
    scorer = _make_scorer(
        step="Click the 'Add to cart' button",
        search_texts=["Add to cart"],
    )
    results = scorer.score_all([with_dqa, text_only])
    # data-qa exact should win (dashed match)
    _assert(results[0]["id"] == 1, f"data-qa btn wins, top id={results[0]['id']}")


# ── 25: Attribute match + mode synergy compound ──────────────────────────────

def _test_attr_plus_mode_synergy():
    print("\n── Attribute match + link mode synergy compound ──")
    cart_link = _make_el(
        name="",
        class_name="shopping_cart_link",
        tag_name="a",
        role="link",
        id=1,
    )
    cart_div = _make_el(
        name="",
        class_name="shopping_cart_summary",
        tag_name="div",
        id=2,
    )
    scorer = _make_scorer()
    results = scorer.score_all([cart_link, cart_div])
    _assert(results[0]["id"] == 1, f"<a> link beats <div>, top id={results[0]['id']}")


# ── 26: Three-word search term — "add to cart" ───────────────────────────────

def _test_three_word_class():
    print("\n── 3-word: 'Add to cart' vs class 'add_to_cart_btn' ──")
    el = _make_el(
        name="🛒",
        class_name="add_to_cart_btn",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Add to cart' button",
        search_texts=["Add to cart"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    # "add" is only 3 chars, but _RE_WORD_3 catches 3+ char words
    _assert(score >= 10_000, f"add_to_cart_btn ≥ 10k, got {score}")


# ── 27: Attribute match should NOT set is_perfect ─────────────────────────────

def _test_not_perfect_text():
    print("\n── Attribute semantic match does not trigger is_perfect ──")
    el = _make_el(
        name="2",
        class_name="shopping_cart_link",
        tag_name="a",
    )
    scorer = _make_scorer()
    scorer._preprocess(el)
    text_score, is_perfect = scorer._score_text_match(el)
    _assert(not is_perfect, f"is_perfect should be False, got {is_perfect}")
    _assert(text_score > 0.3, f"text_score > 0.3, got {text_score:.4f}")


# ── 28: Class with only one matching word gives partial coverage ──────────────

def _test_single_word_partial():
    print("\n── Partial: class='shopping_deals' vs 'Shopping cart' ──")
    el = _make_el(
        name="Deals",
        class_name="shopping_deals",
        tag_name="div",
    )
    scorer = _make_scorer()
    scorer._preprocess(el)
    text_score, _ = scorer._score_text_match(el)
    # Only 1 of 2 words match → partial boost
    _assert(text_score > 0, f"partial text_score > 0, got {text_score:.4f}")
    # But less than full coverage
    full_el = _make_el(name="2", class_name="shopping_cart_link", tag_name="a")
    scorer._preprocess(full_el)
    full_score, _ = scorer._score_text_match(full_el)
    _assert(text_score < full_score, f"partial {text_score:.4f} < full {full_score:.4f}")


# ── 29: Both ID and class match — stacking ───────────────────────────────────

def _test_id_and_class_stack():
    print("\n── ID + class both contain keywords — score stacks ──")
    both = _make_el(
        name="",
        html_id="shopping_cart",
        class_name="shopping_cart_link",
        tag_name="a",
        id=1,
    )
    id_only = _make_el(
        name="",
        html_id="shopping_cart",
        tag_name="a",
        id=2,
    )
    class_only = _make_el(
        name="",
        class_name="shopping_cart_link",
        tag_name="a",
        id=3,
    )
    scorer = _make_scorer()
    results = scorer.score_all([both, id_only, class_only])
    # "both" should score >= either individual because the tokens pool
    # is combined; the attribute semantic match fires once per term.
    # However, other signal channels (html_id matching) may stack for "both".
    _assert(results[0]["id"] == 1, f"both ID+class wins, top id={results[0]['id']}")


# ── 30: Checkout keyword — single word in class ──────────────────────────────

def _test_checkout_class():
    print("\n── 'Checkout' in class='checkout_proceed_btn' ──")
    el = _make_el(
        name="→",
        class_name="checkout_proceed_btn",
        tag_name="button",
        role="button",
    )
    scorer = _make_scorer(
        step="Click the 'Checkout' button",
        search_texts=["Checkout"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"checkout class ≥ 10k, got {score}")


# ── 31: "Login" in input mode — class="login_form_email" ─────────────────────

def _test_login_input_class():
    print("\n── Input mode: class='login_email_field' vs 'Login email' ──")
    el = _make_el(
        name="",
        class_name="login_email_field",
        tag_name="input",
        input_type="email",
    )
    scorer = _make_scorer(
        step="Fill the 'Login email' field with 'test@example.com'",
        search_texts=["Login email"],
        mode="input",
        target_field="login email",
    )
    results = scorer.score_all([el])
    score = results[0]["score"]
    _assert(score >= 10_000, f"login_email_field input ≥ 10k, got {score}")


# ── Runner ────────────────────────────────────────────────────────────────────

async def run_suite() -> None:
    _run()


def _run() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0
    print("\n🧪 ATTRIBUTE SEMANTIC KEYWORD MATCH LAB (31 scenarios / 34 assertions)")
    _test_cart_class_badge_text()            # 1
    _test_cart_id()                          # 2
    _test_cart_data_qa()                     # 3
    _test_single_word_cart()                 # 4
    _test_basket_keyword()                   # 5
    _test_notification_bell()                # 6
    _test_hamburger_menu()                   # 7
    _test_user_profile()                     # 8
    _test_cart_beats_plain_number()           # 9
    _test_cart_beats_disabled()               # 10
    _test_multi_class()                       # 11
    _test_partial_coverage()                  # 12
    _test_search_icon()                       # 13
    _test_checkout_vs_cart()                   # 14
    _test_data_qa_dashes()                    # 15
    _test_id_underscores()                    # 16
    _test_camel_case_class()                  # 17
    _test_false_positive_unrelated()          # 18
    _test_false_positive_substring()          # 19
    _test_hidden_cart()                       # 20
    _test_saucedemo_cart()                    # 21
    _test_wishlist()                          # 22
    _test_close_modal()                       # 23
    _test_add_to_cart_data_qa_wins()          # 24
    _test_attr_plus_mode_synergy()            # 25
    _test_three_word_class()                  # 26
    _test_not_perfect_text()                  # 27
    _test_single_word_partial()               # 28
    _test_id_and_class_stack()                # 29
    _test_checkout_class()                    # 30
    _test_login_input_class()                 # 31
    total = _PASS + _FAIL
    print(f"\n{'='*60}")
    print(f"📊 SCORE: {_PASS}/{total} passed")
    if _FAIL:
        print(f"\n🙀 {_FAIL} failure(s)")
    if _PASS == total:
        print("\n🏆 ATTRIBUTE SEMANTIC FLAWLESS!")
    print(f"{'='*60}")
    return _PASS, _FAIL


if __name__ == "__main__":
    p, f = _run()
    raise SystemExit(f)
