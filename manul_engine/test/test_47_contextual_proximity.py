import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from manul_engine.actions import _ActionsMixin
from manul_engine.scoring import DOMScorer, WEIGHTS, SCALE
from manul_engine.helpers import parse_contextual_hint, ContextualHint

# ─────────────────────────────────────────────────────────────────────────────
# CONTEXTUAL PROXIMITY LAB — NEAR / ON HEADER / ON FOOTER / INSIDE
#
# Validates:
# 1. parse_contextual_hint() extracts NEAR, ON HEADER, ON FOOTER, INSIDE clauses
# 2. DOMScorer proximity scoring with contextual hints
# 3. NEAR: Euclidean distance boosting (closest candidate wins)
# 4. ON HEADER: top 15% viewport + <header>/<nav> ancestor scoring
# 5. ON FOOTER: bottom 15% viewport + <footer> ancestor scoring
# 6. INSIDE: container subtree filtering
# 7. Proximity weight boost when hint is active (0.10 → 1.5)
# 8. Explain mode includes contextual details
# 9. Edge cases: no hint, missing rect data, empty containers
# ─────────────────────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0


class _DummyActions(_ActionsMixin):
    pass


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
    """Build a minimal element dict with all fields expected by DOMScorer."""
    base = {
        "name": overrides.pop("name", "Save button"),
        "xpath": overrides.pop("xpath", "/html/body/button[1]"),
        "is_select": False,
        "is_shadow": False,
        "is_contenteditable": False,
        "class_name": "",
        "tag_name": "button",
        "input_type": "",
        "data_qa": "",
        "html_id": "",
        "icon_classes": "",
        "aria_label": "",
        "placeholder": "",
        "role": "",
        "disabled": False,
        "aria_disabled": "",
        "name_attr": "",
        "label_for": "",
        "id": 1,
        "frame_index": 0,
        "rect_top": 100,
        "rect_left": 200,
        "rect_bottom": 130,
        "rect_right": 300,
        "ancestors": ["div", "body", "html"],
    }
    base.update(overrides)
    return base


# =====================================
# SECTION 1: parse_contextual_hint()
# =====================================


def _test_parse_near():
    print("\n── parse_contextual_hint: NEAR ──")
    hint, cleaned = parse_contextual_hint("Click 'Save' NEAR 'Cancel'")
    _assert(hint.kind == "near", f"kind='near', got {hint.kind!r}")
    _assert(hint.anchor == "Cancel", f"anchor='Cancel', got {hint.anchor!r}")
    _assert(hint.row_text is None, f"row_text=None, got {hint.row_text!r}")
    _assert("NEAR" not in cleaned, f"NEAR removed from step, got {cleaned!r}")
    _assert("Save" in cleaned, f"'Save' preserved in step, got {cleaned!r}")


def _test_parse_near_double_quotes():
    print("\n── parse_contextual_hint: NEAR with double quotes ──")
    hint, cleaned = parse_contextual_hint('Click "Delete" near "Row 3"')
    _assert(hint.kind == "near", f"kind='near', got {hint.kind!r}")
    _assert(hint.anchor == "Row 3", f"anchor='Row 3', got {hint.anchor!r}")
    _assert(
        "near" not in cleaned.lower() or "near" in cleaned.lower().split("'")[1::2], f"near removed, got {cleaned!r}"
    )


def _test_parse_on_header():
    print("\n── parse_contextual_hint: ON HEADER ──")
    hint, cleaned = parse_contextual_hint("Click 'Login' ON HEADER")
    _assert(hint.kind == "on_header", f"kind='on_header', got {hint.kind!r}")
    _assert(hint.anchor is None, f"anchor=None, got {hint.anchor!r}")
    _assert("ON HEADER" not in cleaned, f"ON HEADER removed, got {cleaned!r}")
    _assert("Login" in cleaned, f"'Login' preserved, got {cleaned!r}")


def _test_parse_on_footer():
    print("\n── parse_contextual_hint: ON FOOTER ──")
    hint, cleaned = parse_contextual_hint("Click 'Privacy Policy' ON FOOTER")
    _assert(hint.kind == "on_footer", f"kind='on_footer', got {hint.kind!r}")
    _assert("ON FOOTER" not in cleaned, f"ON FOOTER removed, got {cleaned!r}")


def _test_parse_inside():
    print("\n── parse_contextual_hint: INSIDE ──")
    hint, cleaned = parse_contextual_hint("Click 'Delete' INSIDE 'Actions' row with 'John Doe'")
    _assert(hint.kind == "inside", f"kind='inside', got {hint.kind!r}")
    _assert(hint.anchor == "Actions", f"anchor='Actions', got {hint.anchor!r}")
    _assert(hint.row_text == "John Doe", f"row_text='John Doe', got {hint.row_text!r}")
    _assert("INSIDE" not in cleaned, f"INSIDE removed, got {cleaned!r}")
    _assert("Delete" in cleaned, f"'Delete' preserved, got {cleaned!r}")


def _test_parse_no_hint():
    print("\n── parse_contextual_hint: no hint ──")
    step = "Click the 'Submit' button"
    hint, cleaned = parse_contextual_hint(step)
    _assert(hint.kind is None, f"kind=None, got {hint.kind!r}")
    _assert(cleaned == step, f"step unchanged, got {cleaned!r}")


def _test_parse_case_insensitive():
    print("\n── parse_contextual_hint: case insensitive ──")
    hint, cleaned = parse_contextual_hint("Click 'Save' near 'Cancel'")
    _assert(hint.kind == "near", f"lowercase near, kind='near', got {hint.kind!r}")
    hint2, _ = parse_contextual_hint("Click 'Home' on header")
    _assert(hint2.kind == "on_header", f"lowercase on header, kind='on_header', got {hint2.kind!r}")


def _test_parse_inside_double_quotes():
    print("\n── parse_contextual_hint: INSIDE with double quotes ──")
    hint, cleaned = parse_contextual_hint('Click "Edit" INSIDE "Actions" row with "Jane"')
    _assert(hint.kind == "inside", f"kind='inside', got {hint.kind!r}")
    _assert(hint.anchor == "Actions", f"anchor='Actions', got {hint.anchor!r}")
    _assert(hint.row_text == "Jane", f"row_text='Jane', got {hint.row_text!r}")


# =====================================
# SECTION 2: DOMScorer NEAR proximity
# =====================================


def _test_near_closest_wins():
    print("\n── NEAR: closest element wins ──")
    # Anchor at (200, 100). Element A at (250, 120) = close. Element B at (800, 600) = far.
    anchor_rect = {"rect_top": 90, "rect_left": 190, "rect_bottom": 120, "rect_right": 250}
    el_close = _make_el(id=1, name="Save", rect_top=110, rect_left=240, rect_bottom=140, rect_right=340)
    el_far = _make_el(id=2, name="Save", rect_top=580, rect_left=780, rect_bottom=610, rect_right=880)

    hint = ContextualHint("near", "Anchor", None)
    scorer = DOMScorer(
        step="Click the 'Save' button",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    results = scorer.score_all([el_close, el_far])
    _assert(results[0]["id"] == 1, f"closest element wins, got id={results[0]['id']}")
    _assert(
        results[0]["score"] > results[1]["score"],
        f"close score ({results[0]['score']}) > far score ({results[1]['score']})",
    )


def _test_near_distance_scoring():
    print("\n── NEAR: distance scoring values ──")
    anchor_rect = {"rect_top": 100, "rect_left": 100, "rect_bottom": 130, "rect_right": 200}
    # Element directly overlapping anchor
    el_on_top = _make_el(id=1, name="Save", rect_top=100, rect_left=100, rect_bottom=130, rect_right=200)
    hint = ContextualHint("near", "Anchor", None)
    scorer = DOMScorer(
        step="Click the 'Save' button",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    scorer._preprocess(el_on_top)
    prox = scorer._score_proximity(el_on_top)
    _assert(prox == 1.0, f"element overlapping anchor → prox=1.0, got {prox}")


def _test_near_same_container_beats_closer_neighbor_card():
    print("\n── NEAR: same container beats slightly closer neighbor card ──")
    anchor_rect = {
        "rect_top": 100,
        "rect_left": 420,
        "rect_bottom": 130,
        "rect_right": 560,
        "frame_index": 0,
        "xpath": "/html/body/div/div[1]/div[4]/div[1]/a/div",
    }
    el_same_card = _make_el(
        id=1,
        name="Add to cart",
        xpath="/html/body/div/div[1]/div[4]/div[2]/button",
        rect_top=112,
        rect_left=565,
        rect_bottom=142,
        rect_right=670,
    )
    el_neighbor_card = _make_el(
        id=2,
        name="Add to cart",
        xpath="/html/body/div/div[1]/div[3]/div[2]/button",
        rect_top=106,
        rect_left=360,
        rect_bottom=136,
        rect_right=465,
    )
    hint = ContextualHint("near", "Sauce Labs Fleece Jacket", None)
    scorer = DOMScorer(
        step="Click 'Add to cart' button near 'Sauce Labs Fleece Jacket'",
        mode="clickable",
        search_texts=["Add to cart"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    results = scorer.score_all([el_neighbor_card, el_same_card])
    _assert(results[0]["id"] == 1, f"same-card button wins, got id={results[0]['id']}")
    _assert(results[0]["score"] > results[1]["score"], "same-card score beats neighbor-card score")


def _test_near_beyond_threshold():
    print("\n── NEAR: element beyond threshold gets 0 ──")
    anchor_rect = {"rect_top": 0, "rect_left": 0, "rect_bottom": 30, "rect_right": 100}
    # Element very far away (center ~1500px away)
    el_far = _make_el(id=1, name="Save", rect_top=1400, rect_left=1400, rect_bottom=1430, rect_right=1500)
    hint = ContextualHint("near", "Anchor", None)
    scorer = DOMScorer(
        step="Click the 'Save' button",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    scorer._preprocess(el_far)
    prox = scorer._score_proximity(el_far)
    _assert(prox == 0.0, f"element beyond 500px threshold → prox=0.0, got {prox}")


def _test_near_cross_frame_rejected():
    print("\n── NEAR: cross-frame candidate gets 0 ──")
    anchor_rect = {
        "rect_top": 100,
        "rect_left": 100,
        "rect_bottom": 130,
        "rect_right": 200,
        "frame_index": 0,
    }
    el_other_frame = _make_el(
        id=1,
        name="Save",
        frame_index=1,
        rect_top=110,
        rect_left=120,
        rect_bottom=140,
        rect_right=220,
    )
    hint = ContextualHint("near", "Anchor", None)
    scorer = DOMScorer(
        step="Click the 'Save' button",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    scorer._preprocess(el_other_frame)
    prox = scorer._score_proximity(el_other_frame)
    _assert(prox == 0.0, f"cross-frame NEAR → prox=0.0, got {prox}")


def _test_near_no_anchor_rect():
    print("\n── NEAR: fallback when no anchor rect ──")
    hint = ContextualHint("near", "Anchor", None)
    el = _make_el(id=1, name="Save", xpath="/html/body/div/button[1]")
    scorer = DOMScorer(
        step="Click the 'Save' button",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath="/html/body/div/button[2]",
        contextual_hint=hint,
        anchor_rect=None,  # no anchor found
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    # Without anchor_rect, NEAR falls through to default xpath proximity
    _assert(prox >= 0.0, f"fallback proximity ≥ 0, got {prox}")


def _test_near_anchor_picker_prefers_text_over_image():
    print("\n── NEAR: anchor picker prefers text title over image alt ──")
    picker = _DummyActions()
    img_anchor = _make_el(
        id=26,
        name="Sauce Labs Fleece Jacket",
        tag_name="img",
        xpath="/html/body/div/div[4]/div[1]/a/img[1]",
    )
    img_anchor["score"] = 50711
    text_anchor = _make_el(
        id=27,
        name="Sauce Labs Fleece Jacket",
        tag_name="a",
        html_id="item_5_title_link",
        xpath='//*[@id="item_5_title_link"]',
    )
    text_anchor["score"] = 50711
    picked = picker._pick_near_anchor_candidate([img_anchor, text_anchor], "Sauce Labs Fleece Jacket")
    _assert(picked is not None, "anchor picker returned a candidate")
    _assert(picked["id"] == 27, f"text anchor preferred over image, got id={picked['id']}")


def _test_near_anchor_dev_attr_affinity_beats_same_column_neighbor():
    print("\n── NEAR: anchor dev-attr affinity beats same-column neighbor ──")
    anchor_rect = {
        "rect_top": 427,
        "rect_left": 916,
        "rect_bottom": 447,
        "rect_right": 1215,
        "frame_index": 0,
        "xpath": '//*[@id="item_5_title_link"]',
    }
    bike = _make_el(
        id=20,
        name="Add to cart",
        html_id="add-to-cart-sauce-labs-bike-light",
        data_qa="add-to-cart-sauce-labs-bike-light",
        xpath='//*[@id="add-to-cart-sauce-labs-bike-light"]',
        rect_top=339,
        rect_left=1055,
        rect_bottom=373,
        rect_right=1215,
    )
    fleece = _make_el(
        id=28,
        name="Add to cart",
        html_id="add-to-cart-sauce-labs-fleece-jacket",
        data_qa="add-to-cart-sauce-labs-fleece-jacket",
        xpath='//*[@id="add-to-cart-sauce-labs-fleece-jacket"]',
        rect_top=591,
        rect_left=1055,
        rect_bottom=625,
        rect_right=1215,
    )
    hint = ContextualHint("near", "Sauce Labs Fleece Jacket", None)
    scorer = DOMScorer(
        step="Click 'Add to cart' near 'Sauce Labs Fleece Jacket'",
        mode="clickable",
        search_texts=["Add to cart"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    results = scorer.score_all([bike, fleece])
    _assert(results[0]["id"] == 28, f"fleece card button wins, got id={results[0]['id']}")
    _assert(results[0]["score"] > results[1]["score"], "fleece score beats bike-light score")


# =====================================
# SECTION 3: ON HEADER / ON FOOTER
# =====================================


def _test_on_header_ancestor():
    print("\n── ON HEADER: element inside <header> ancestor ──")
    el = _make_el(id=1, name="Login", ancestors=["header", "body", "html"], rect_top=500)
    hint = ContextualHint("on_header", None, None)
    scorer = DOMScorer(
        step="Click 'Login' ON HEADER",
        mode="clickable",
        search_texts=["Login"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 1.0, f"inside <header> → prox=1.0, got {prox}")


def _test_on_header_nav_ancestor():
    print("\n── ON HEADER: element inside <nav> ancestor ──")
    el = _make_el(id=1, name="Home", ancestors=["nav", "div", "body", "html"], rect_top=50)
    hint = ContextualHint("on_header", None, None)
    scorer = DOMScorer(
        step="Click 'Home' ON HEADER",
        mode="clickable",
        search_texts=["Home"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 1.0, f"inside <nav> → prox=1.0, got {prox}")


def _test_on_header_top_15_percent():
    print("\n── ON HEADER: element in top 15% of viewport ──")
    el = _make_el(id=1, name="Cart", ancestors=["div", "body"], rect_top=100)
    hint = ContextualHint("on_header", None, None)
    scorer = DOMScorer(
        step="Click 'Cart' ON HEADER",
        mode="clickable",
        search_texts=["Cart"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 1.0, f"rect_top=100 in top 15% of 1000px → prox=1.0, got {prox}")


def _test_on_header_bottom_element_rejected():
    print("\n── ON HEADER: element at bottom gets 0 ──")
    el = _make_el(id=1, name="Login", ancestors=["div", "body"], rect_top=800)
    hint = ContextualHint("on_header", None, None)
    scorer = DOMScorer(
        step="Click 'Login' ON HEADER",
        mode="clickable",
        search_texts=["Login"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 0.0, f"element at bottom → prox=0.0, got {prox}")


def _test_on_footer_ancestor():
    print("\n── ON FOOTER: element inside <footer> ancestor ──")
    el = _make_el(id=1, name="Privacy", ancestors=["footer", "body"], rect_top=50)
    hint = ContextualHint("on_footer", None, None)
    scorer = DOMScorer(
        step="Click 'Privacy' ON FOOTER",
        mode="clickable",
        search_texts=["Privacy"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 1.0, f"inside <footer> → prox=1.0, got {prox}")


def _test_on_footer_bottom_15_percent():
    print("\n── ON FOOTER: element in bottom 15% of viewport ──")
    el = _make_el(id=1, name="Terms", ancestors=["div", "body"], rect_top=870, rect_bottom=900)
    hint = ContextualHint("on_footer", None, None)
    scorer = DOMScorer(
        step="Click 'Terms' ON FOOTER",
        mode="clickable",
        search_texts=["Terms"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 1.0, f"rect_bottom=900 in bottom 15% of 1000px → prox=1.0, got {prox}")


def _test_on_footer_top_element_rejected():
    print("\n── ON FOOTER: element at top gets 0 ──")
    el = _make_el(id=1, name="Terms", ancestors=["div", "body"], rect_top=50, rect_bottom=80)
    hint = ContextualHint("on_footer", None, None)
    scorer = DOMScorer(
        step="Click 'Terms' ON FOOTER",
        mode="clickable",
        search_texts=["Terms"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 0.0, f"element at top → prox=0.0, got {prox}")


def _test_on_header_iframe_rejected():
    print("\n── ON HEADER: iframe element gets 0 ──")
    el = _make_el(id=1, name="Login", frame_index=1, ancestors=["header", "body"], rect_top=10)
    hint = ContextualHint("on_header", None, None)
    scorer = DOMScorer(
        step="Click 'Login' ON HEADER",
        mode="clickable",
        search_texts=["Login"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 0.0, f"iframe header qualifier → prox=0.0, got {prox}")


def _test_on_footer_iframe_rejected():
    print("\n── ON FOOTER: iframe element gets 0 ──")
    el = _make_el(id=1, name="Privacy", frame_index=1, ancestors=["footer", "body"], rect_bottom=990)
    hint = ContextualHint("on_footer", None, None)
    scorer = DOMScorer(
        step="Click 'Privacy' ON FOOTER",
        mode="clickable",
        search_texts=["Privacy"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 0.0, f"iframe footer qualifier → prox=0.0, got {prox}")


# =====================================
# SECTION 4: INSIDE container filtering
# =====================================


def _test_inside_container_match():
    print("\n── INSIDE: element in the container subtree ──")
    container_els = [
        _make_el(id=10, name="Delete", xpath="/html/body/table/tr[3]/td[4]/button[1]"),
        _make_el(id=11, name="Edit", xpath="/html/body/table/tr[3]/td[4]/button[2]"),
    ]
    el_in = _make_el(id=10, name="Delete", xpath="/html/body/table/tr[3]/td[4]/button[1]")
    el_out = _make_el(id=20, name="Delete", xpath="/html/body/table/tr[1]/td[4]/button[1]")

    hint = ContextualHint("inside", "Actions", "John Doe")
    scorer = DOMScorer(
        step="Click 'Delete'",
        mode="clickable",
        search_texts=["Delete"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        container_elements=container_els,
    )
    results = scorer.score_all([el_in, el_out])
    _assert(results[0]["id"] == 10, f"inside-container wins, got id={results[0]['id']}")
    _assert(
        results[0]["score"] > results[1]["score"], f"inside ({results[0]['score']}) > outside ({results[1]['score']})"
    )


def _test_inside_empty_container():
    print("\n── INSIDE: empty container → all score 0 proximity ──")
    el = _make_el(id=1, name="Delete")
    hint = ContextualHint("inside", "Actions", "Nobody")
    scorer = DOMScorer(
        step="Click 'Delete'",
        mode="clickable",
        search_texts=["Delete"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        container_elements=[],
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 0.0, f"empty container → prox=0.0, got {prox}")


# =====================================
# SECTION 5: Weight boost & scoring
# =====================================


def _test_proximity_weight_boosted():
    print("\n── Proximity WEIGHTS boosted to 1.5 when hint active ──")
    hint = ContextualHint("near", "Anchor", None)
    anchor_rect = {"rect_top": 100, "rect_left": 100, "rect_bottom": 130, "rect_right": 200}
    el_close = _make_el(id=1, name="Save", rect_top=100, rect_left=100, rect_bottom=130, rect_right=200)
    el_far = _make_el(id=2, name="Save", rect_top=580, rect_left=780, rect_bottom=610, rect_right=880)

    # With hint → boosted proximity
    scorer_hint = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    results_hint = scorer_hint.score_all(
        [_make_el(id=1, name="Save", rect_top=100, rect_left=100, rect_bottom=130, rect_right=200)]
    )
    score_with_hint = results_hint[0]["score"]

    # Without hint → normal proximity (0.10)
    scorer_no_hint = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
    )
    results_no_hint = scorer_no_hint.score_all(
        [_make_el(id=3, name="Save", rect_top=100, rect_left=100, rect_bottom=130, rect_right=200)]
    )
    score_no_hint = results_no_hint[0]["score"]

    # With the huge proximity boost for a close element, the hint score should be higher
    _assert(score_with_hint > score_no_hint, f"hint score ({score_with_hint}) > no-hint score ({score_no_hint})")


def _test_ineffective_near_keeps_default_weight():
    print("\n── NEAR without anchor keeps default proximity weight ──")
    el = _make_el(id=1, name="Save", xpath="/html/body/div[1]/form[1]/button[1]")
    hint = ContextualHint("near", "Missing Anchor", None)

    scorer_hint = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath="/html/body/div[1]/form[1]/button[2]",
        contextual_hint=hint,
        anchor_rect=None,
    )
    scorer_no_hint = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath="/html/body/div[1]/form[1]/button[2]",
    )

    score_hint = scorer_hint.score_all([dict(el)])[0]["score"]
    score_no_hint = scorer_no_hint.score_all([dict(el)])[0]["score"]
    _assert(score_hint == score_no_hint, f"missing anchor keeps default weight: {score_hint} == {score_no_hint}")


def _test_near_ranking_multiple_candidates():
    print("\n── NEAR: ranking 5 candidates by distance ──")
    anchor_rect = {"rect_top": 200, "rect_left": 300, "rect_bottom": 230, "rect_right": 400}
    # Create 5 elements at increasing distances
    els = []
    for i, (x, y) in enumerate([(310, 210), (500, 400), (100, 50), (700, 700), (350, 250)]):
        els.append(
            _make_el(
                id=i + 1,
                name="Save",
                tag_name="button",
                rect_top=y,
                rect_left=x,
                rect_bottom=y + 30,
                rect_right=x + 100,
            )
        )

    hint = ContextualHint("near", "Anchor", None)
    scorer = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    results = scorer.score_all(els)

    # Element at (310,210) is closest → should rank first
    _assert(results[0]["id"] == 1, f"closest element (310,210) wins, got id={results[0]['id']}")
    # Element at (700,700) is furthest → should rank last (or near last)
    last_id = results[-1]["id"]
    _assert(last_id == 4, f"furthest element (700,700) ranks last, got id={last_id}")


# =====================================
# SECTION 6: Explain mode with context
# =====================================


def _test_explain_includes_contextual_info():
    print("\n── Explain mode includes contextual hint info ──")
    anchor_rect = {"rect_top": 100, "rect_left": 100, "rect_bottom": 130, "rect_right": 200}
    el = _make_el(id=1, name="Save", rect_top=110, rect_left=120, rect_bottom=140, rect_right=220)
    hint = ContextualHint("near", "Cancel", None)
    scorer = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        explain=True,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    results = scorer.score_all([el])
    expl = results[0].get("_explain", {})
    _assert("ctx_kind" in expl, f"explain has ctx_kind, got keys={list(expl.keys())}")
    _assert(expl.get("ctx_kind") == "near", f"ctx_kind='near', got {expl.get('ctx_kind')!r}")
    _assert("ctx_prox_raw" in expl, f"explain has ctx_prox_raw, got keys={list(expl.keys())}")
    _assert(expl["ctx_prox_raw"] > 0, f"ctx_prox_raw > 0, got {expl['ctx_prox_raw']}")


def _test_explain_contextual_channels_clamped():
    print("\n── Explain mode clamps contextual channels to [0.0, 1.0] ──")
    anchor_rect = {"rect_top": 100, "rect_left": 100, "rect_bottom": 130, "rect_right": 200}
    el = _make_el(id=1, name="Save", rect_top=100, rect_left=100, rect_bottom=130, rect_right=200)
    scorer = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        explain=True,
        contextual_hint=ContextualHint("near", "Anchor", None),
        anchor_rect=anchor_rect,
    )
    expl = scorer.score_all([el])[0]["_explain"]
    _assert(0.0 <= expl["proximity"] <= 1.0, f"contextual proximity explain stays in [0,1], got {expl['proximity']}")


def _test_explain_no_context():
    print("\n── Explain mode without contextual hint ──")
    el = _make_el(id=1, name="Save")
    scorer = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        explain=True,
    )
    results = scorer.score_all([el])
    expl = results[0].get("_explain", {})
    _assert("ctx_kind" not in expl, f"no contextual hint → no ctx_kind, keys={list(expl.keys())}")


# =====================================
# SECTION 7: Default fallback (no hint)
# =====================================


def _test_default_xpath_proximity():
    print("\n── Default xpath proximity (no hint) ──")
    el = _make_el(id=1, xpath="/html/body/div[1]/form[1]/input[1]")
    scorer = DOMScorer(
        step="Fill 'Email'",
        mode="input",
        search_texts=["Email"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath="/html/body/div[1]/form[1]/input[2]",
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    # 4 common path segments: html, body, div[1], form[1] → 4 * 0.2 = 0.8
    _assert(prox >= 0.6, f"shared xpath depth → prox ≥ 0.6, got {prox}")


def _test_default_no_last_xpath():
    print("\n── Default: no last_xpath → prox=0 ──")
    el = _make_el(id=1, xpath="/html/body/button[1]")
    scorer = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    _assert(prox == 0.0, f"no last_xpath → prox=0.0, got {prox}")


# =====================================
# SECTION 8: Edge cases
# =====================================


def _test_near_identical_positions():
    print("\n── NEAR: two elements at identical positions ──")
    anchor_rect = {"rect_top": 200, "rect_left": 300, "rect_bottom": 230, "rect_right": 400}
    el1 = _make_el(
        id=1, name="Save", data_qa="save-primary", rect_top=250, rect_left=350, rect_bottom=280, rect_right=450
    )
    el2 = _make_el(id=2, name="Save", rect_top=250, rect_left=350, rect_bottom=280, rect_right=450)
    hint = ContextualHint("near", "Anchor", None)
    scorer = DOMScorer(
        step="Click 'Save'",
        mode="clickable",
        search_texts=["Save"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        anchor_rect=anchor_rect,
    )
    results = scorer.score_all([el1, el2])
    # Both should have the same proximity score; data-qa breaks the tie
    _assert(results[0]["id"] == 1, f"data-qa tiebreaker wins, got id={results[0]['id']}")


def _test_on_header_boundary():
    print("\n── ON HEADER: element exactly at 15% boundary ──")
    el = _make_el(id=1, name="Logo", ancestors=["div", "body"], rect_top=150)
    hint = ContextualHint("on_header", None, None)
    scorer = DOMScorer(
        step="Click 'Logo' ON HEADER",
        mode="clickable",
        search_texts=["Logo"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    # 150 is exactly 15% of 1000 → should be included (<=)
    _assert(prox == 1.0, f"exactly at 15% boundary → prox=1.0, got {prox}")


def _test_on_header_negative_rect():
    print("\n── ON HEADER: element with negative rect_top (scrolled above) ──")
    el = _make_el(id=1, name="Banner", ancestors=["div", "body"], rect_top=-50)
    hint = ContextualHint("on_header", None, None)
    scorer = DOMScorer(
        step="Click 'Banner' ON HEADER",
        mode="clickable",
        search_texts=["Banner"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        contextual_hint=hint,
        viewport_height=1000,
    )
    scorer._preprocess(el)
    prox = scorer._score_proximity(el)
    # Negative rect_top is NOT in range [0, 150]
    _assert(prox == 0.0, f"negative rect_top → prox=0.0, got {prox}")


def _test_contextual_hint_namedtuple():
    print("\n── ContextualHint is a NamedTuple ──")
    h = ContextualHint("near", "anchor_text", None)
    _assert(h.kind == "near", f"kind accessible, got {h.kind!r}")
    _assert(h.anchor == "anchor_text", f"anchor accessible, got {h.anchor!r}")
    _assert(h[0] == "near", f"index access works, got {h[0]!r}")
    _assert(len(h) == 3, f"3 fields, got {len(h)}")


def _test_parse_hint_preserves_quotes_in_main_step():
    print("\n── parse_contextual_hint: does not corrupt quoted targets ──")
    hint, cleaned = parse_contextual_hint("Fill 'Email' with 'test@test.com' NEAR 'Login Form'")
    _assert(hint.kind == "near", f"hint detected, got {hint.kind!r}")
    _assert("Email" in cleaned, f"'Email' preserved, got {cleaned!r}")
    _assert("test@test.com" in cleaned, f"'test@test.com' preserved, got {cleaned!r}")
    _assert("Login Form" not in cleaned, f"'Login Form' removed with NEAR clause, got {cleaned!r}")


# ── Runner ────────────────────────────────────────────────────────────────────


def run_all():
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║  CONTEXTUAL PROXIMITY LAB — NEAR / ON HEADER/FOOTER / INSIDE   ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    # Section 1: Parsing
    _test_parse_near()
    _test_parse_near_double_quotes()
    _test_parse_on_header()
    _test_parse_on_footer()
    _test_parse_inside()
    _test_parse_no_hint()
    _test_parse_case_insensitive()
    _test_parse_inside_double_quotes()

    # Section 2: NEAR proximity scoring
    _test_near_closest_wins()
    _test_near_distance_scoring()
    _test_near_beyond_threshold()
    _test_near_cross_frame_rejected()
    _test_near_no_anchor_rect()
    _test_near_anchor_picker_prefers_text_over_image()
    _test_near_anchor_dev_attr_affinity_beats_same_column_neighbor()

    # Section 3: ON HEADER / ON FOOTER
    _test_on_header_ancestor()
    _test_on_header_nav_ancestor()
    _test_on_header_top_15_percent()
    _test_on_header_bottom_element_rejected()
    _test_on_footer_ancestor()
    _test_on_footer_bottom_15_percent()
    _test_on_footer_top_element_rejected()
    _test_on_header_iframe_rejected()
    _test_on_footer_iframe_rejected()

    # Section 4: INSIDE container
    _test_inside_container_match()
    _test_inside_empty_container()

    # Section 5: Weight boost & full scoring
    _test_proximity_weight_boosted()
    _test_ineffective_near_keeps_default_weight()
    _test_near_ranking_multiple_candidates()

    # Section 6: Explain mode
    _test_explain_includes_contextual_info()
    _test_explain_contextual_channels_clamped()
    _test_explain_no_context()

    # Section 7: Default fallback
    _test_default_xpath_proximity()
    _test_default_no_last_xpath()

    # Section 8: Edge cases
    _test_near_identical_positions()
    _test_on_header_boundary()
    _test_on_header_negative_rect()
    _test_contextual_hint_namedtuple()
    _test_parse_hint_preserves_quotes_in_main_step()

    print(f"\n{'=' * 60}")
    print(f"📊 SCORE: {_PASS}/{_PASS + _FAIL} passed")
    print(f"  TOTAL: {_PASS + _FAIL} assertions — ✅ {_PASS} passed, ❌ {_FAIL} failed")
    print(f"{'=' * 60}")

    return _FAIL == 0


async def run_suite() -> None:
    run_all()


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
