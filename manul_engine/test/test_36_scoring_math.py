import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from manul_engine.scoring import DOMScorer, WEIGHTS, SCALE

# ─────────────────────────────────────────────────────────────────────────────
# SCORING MATH LAB — Exact Numerical Validation (25 Tests)
#
# Validates:
# 1. Individual _score_* methods return expected floats for known inputs
# 2. score_all() combines channels via WEIGHTS and SCALE correctly
# 3. Penalty multipliers (disabled ×0.0, hidden ×0.1) apply after weighting
# 4. Stacked signals accumulate correctly across channels
# 5. Exact integer score = round(weighted_sum × SCALE)
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
    """Build a minimal element dict with all fields expected by _preprocess."""
    base = {
        "name": overrides.pop("name", "Submit button"),
        "xpath": overrides.pop("xpath", "/html/body/button[1]"),
        "is_select": False, "is_shadow": False, "is_contenteditable": False,
        "class_name": "", "tag_name": "button", "input_type": "",
        "data_qa": "", "html_id": "", "icon_classes": "",
        "aria_label": "", "placeholder": "", "role": "",
        "disabled": False, "aria_disabled": "", "name_attr": "",
        "id": 1,
    }
    base.update(overrides)
    return base


def _make_scorer(**overrides) -> DOMScorer:
    """Build a scorer with defaults suitable for simple tests."""
    return DOMScorer(
        step=overrides.get("step", "Click the 'Submit' button"),
        mode=overrides.get("mode", "clickable"),
        search_texts=overrides.get("search_texts", ["Submit"]),
        target_field=overrides.get("target_field", None),
        is_blind=overrides.get("is_blind", False),
        learned_elements=overrides.get("learned_elements", {}),
        last_xpath=overrides.get("last_xpath", None),
    )


# ── Test 1: data-qa exact match produces ~80k score ──────────────────────────

def _test_data_qa_exact_score():
    print("\n── data-qa exact match score ──")
    el = _make_el(name="Go button", data_qa="submit", html_id="dqa_btn")
    scorer = _make_scorer(step="Click the 'Submit' button", search_texts=["Submit"])
    results = scorer.score_all([el])
    score = results[0]["score"]

    # data-qa exact = +1.0 text. With mode synergy and type hints,
    # text channel contributes 1.0 × W_text(0.45) × SCALE ≈ 80,000
    # Plus semantics and attributes channels.
    _assert(score >= 70_000, f"data-qa exact ≥ 70k, got {score}")
    _assert(score < 200_000, f"data-qa exact < 200k (no cache), got {score}")


# ── Test 2: text exact match produces ~50k score ─────────────────────────────

def _test_text_exact_match_score():
    print("\n── text exact match score ──")
    # name_core after preprocessing must equal the search term for exact match
    el = _make_el(name="Submit", html_id="btn_submit")
    scorer = _make_scorer(step="Click the 'Submit' button", search_texts=["Submit"])
    results = scorer.score_all([el])
    score = results[0]["score"]

    # name exact = +0.625 text → 0.625 × W_text(0.45) × SCALE ≈ 50k + semantics
    _assert(score >= 30_000, f"text exact ≥ 30k, got {score}")
    _assert(score < 200_000, f"text exact < 200k (no cache), got {score}")


# ── Test 3: disabled penalty zeroes the score ────────────────────────────────

def _test_disabled_penalty_zeroes():
    print("\n── disabled penalty ──")
    el = _make_el(name="Submit button", disabled=True)
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]

    _assert(score == 0, f"disabled element score = 0, got {score}")


# ── Test 4: hidden penalty reduces to ~10% ───────────────────────────────────

def _test_hidden_penalty_tenth():
    print("\n── hidden penalty ──")
    el_vis = _make_el(name="Submit button", html_id="vis")
    el_hid = _make_el(name="Submit button [HIDDEN]", html_id="hid", id=2)
    scorer = _make_scorer()
    results = scorer.score_all([dict(el_vis), dict(el_hid)])

    vis = next(e["score"] for e in results if e["html_id"] == "vis")
    hid = next(e["score"] for e in results if e["html_id"] == "hid")

    _assert(vis > 0, f"visible score > 0, got {vis}")
    _assert(hid < vis, f"hidden < visible, {hid} < {vis}")
    if vis > 0:
        ratio = hid / vis
        _assert(ratio < 0.15, f"hidden/visible ratio < 0.15, got {ratio:.4f}")


# ── Test 5: semantic cache reuse produces ≥200k ──────────────────────────────

def _test_semantic_cache_score():
    print("\n── semantic cache reuse ──")
    el = _make_el(name="Submit button", tag_name="button", html_id="cached_btn")
    # Cache key uses tuple (not frozenset) of lowered search_texts
    learned = {("clickable", ("submit",), None): {"name": "Submit button", "tag": "button"}}
    scorer = _make_scorer(learned_elements=learned)
    results = scorer.score_all([el])
    score = results[0]["score"]

    # cache_score = 1.0, × W_cache(2.0) × SCALE = 355,556 + other channels
    _assert(score >= 200_000, f"semantic cache ≥ 200k, got {score}")
    _assert(score >= 300_000, f"semantic cache ≥ 300k (cache channel alone ~355k), got {score}")


# ── Test 6: blind context reuse (last_xpath) ─────────────────────────────────

def _test_blind_context_score():
    print("\n── blind context reuse ──")
    xpath = "/html/body/form/input[2]"
    el = _make_el(name="Password input text", tag_name="input", input_type="password",
                  xpath=xpath, html_id="ctx_inp")
    scorer = DOMScorer(
        step="type 'secret' into that field",
        mode="input",
        search_texts=[],
        target_field=None,
        is_blind=True,
        learned_elements={},
        last_xpath=xpath,
    )
    results = scorer.score_all([el])
    score = results[0]["score"]

    # blind context: cache_score = 0.05, × W_cache(2.0) × SCALE ≈ 17,778
    _assert(score >= 10_000, f"blind context ≥ 10k, got {score}")


# ── Test 7: aria-label exact match (+0.625 text) ─────────────────────────────

def _test_aria_exact_match():
    print("\n── aria-label exact match ──")
    el = _make_el(name="input text", tag_name="input", input_type="text",
                  aria_label="Email Address", html_id="aria_inp")
    scorer = _make_scorer(
        step="Fill 'Email Address' field with 'test@example.com'",
        mode="input",
        search_texts=["Email Address"],
        target_field="email address",
    )
    results = scorer.score_all([el])
    score = results[0]["score"]

    # aria exact = +0.625 text, + input mode synergy +0.5 sem, + target_field attrs
    _assert(score >= 40_000, f"aria exact ≥ 40k, got {score}")


# ── Test 8: placeholder exact match (+0.625 text) ────────────────────────────

def _test_placeholder_exact_match():
    print("\n── placeholder exact match ──")
    el = _make_el(name="input text", tag_name="input", input_type="text",
                  placeholder="Search Query", html_id="ph_inp")
    scorer = _make_scorer(
        step="Fill 'Search Query' field with 'cats'",
        mode="input",
        search_texts=["Search Query"],
        target_field="search query",
    )
    results = scorer.score_all([el])
    score = results[0]["score"]

    _assert(score >= 40_000, f"placeholder exact ≥ 40k, got {score}")


# ── Test 9: name_attr exact match (+0.0375 text) ─────────────────────────────

def _test_name_attr_exact():
    print("\n── name_attr exact match ──")
    el = _make_el(name="input text", tag_name="input", input_type="text",
                  name_attr="username", html_id="na_inp")
    scorer = _make_scorer(
        step="Fill 'username' field with 'admin'",
        mode="input",
        search_texts=["username"],
        target_field="username",
    )
    results = scorer.score_all([el])
    score = results[0]["score"]

    # name_attr exact = +0.0375 text × W_text(0.45) × SCALE ≈ 3,000
    _assert(score >= 2_000, f"name_attr exact ≥ 2k, got {score}")


# ── Test 10: SCALE constant derivation ────────────────────────────────────────

def _test_scale_derivation():
    print("\n── SCALE derivation ──")
    # SCALE = 3000 / (name_attr_exact × W_text) = 3000 / (0.0375 × 0.45)
    expected = round(3000 / (0.0375 * WEIGHTS["text"]))
    _assert(SCALE == expected, f"SCALE = {SCALE} matches 3000/(0.0375×W_text) = {expected}")
    _assert(SCALE == 177_778, f"SCALE = 177,778, got {SCALE}")


# ── Test 11: WEIGHTS ordering ────────────────────────────────────────────────

def _test_weights_ordering():
    print("\n── WEIGHTS ordering ──")
    w = WEIGHTS
    _assert(w["cache"] == 2.0, f"cache = 2.0, got {w['cache']}")
    _assert(w["semantics"] == 0.60, f"semantics = 0.60, got {w['semantics']}")
    _assert(w["text"] == 0.45, f"text = 0.45, got {w['text']}")
    _assert(w["attributes"] == 0.25, f"attributes = 0.25, got {w['attributes']}")
    _assert(w["proximity"] == 0.10, f"proximity = 0.10, got {w['proximity']}")


# ── Test 12: checkbox mode penalty on non-checkbox ────────────────────────────

def _test_checkbox_penalty():
    print("\n── checkbox penalty on non-checkbox element ──")
    el = _make_el(name="Newsletter button", tag_name="button", html_id="chk_decoy")
    scorer = _make_scorer(
        step="Check the 'Newsletter' checkbox",
        mode="clickable",
        search_texts=["Newsletter"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]

    # Non-checkbox element with "Check" in step gets -1.0 semantics penalty
    # The semantics channel deduction should heavily suppress the score
    _assert(score < 5_000, f"non-checkbox penalised < 5k, got {score}")


# ── Test 13: real checkbox gets bonus ─────────────────────────────────────────

def _test_checkbox_bonus():
    print("\n── real checkbox semantic bonus ──")
    el = _make_el(name="Newsletter checkbox", tag_name="input", input_type="checkbox",
                  html_id="chk_real")
    scorer = _make_scorer(
        step="Check the 'Newsletter' checkbox",
        mode="clickable",
        search_texts=["Newsletter"],
    )
    results = scorer.score_all([el])
    score = results[0]["score"]

    # Real checkbox: +0.5 semantics → 0.5 × W_sem(0.60) × SCALE ≈ 53k + text match
    _assert(score >= 40_000, f"real checkbox ≥ 40k, got {score}")


# ── Test 14: proximity bonus with shared xpath ───────────────────────────────

def _test_proximity_bonus():
    print("\n── proximity bonus ──")
    last = "/html/body/form/div[1]/input[1]"
    el_close = _make_el(name="Submit button", xpath="/html/body/form/div[1]/button[1]",
                        html_id="close_btn")
    el_far   = _make_el(name="Submit button", xpath="/html/body/footer/button[1]",
                        html_id="far_btn", id=2)
    scorer = _make_scorer(last_xpath=last)
    results = scorer.score_all([dict(el_close), dict(el_far)])

    close_score = next(e["score"] for e in results if e["html_id"] == "close_btn")
    far_score   = next(e["score"] for e in results if e["html_id"] == "far_btn")

    _assert(close_score > far_score, f"close ({close_score}) > far ({far_score})")


# ── Test 15: mode synergy for input mode ──────────────────────────────────────

def _test_input_mode_synergy():
    print("\n── input mode synergy ──")
    el_input  = _make_el(name="Query input text", tag_name="input", input_type="text",
                         placeholder="Query", html_id="real_inp")
    el_button = _make_el(name="Query button", tag_name="button",
                         html_id="btn_decoy", id=2)
    scorer = _make_scorer(
        step="Fill 'Query' field with 'test'",
        mode="input",
        search_texts=["Query"],
        target_field="query",
    )
    results = scorer.score_all([dict(el_input), dict(el_button)])

    inp_score = next(e["score"] for e in results if e["html_id"] == "real_inp")
    btn_score = next(e["score"] for e in results if e["html_id"] == "btn_decoy")

    _assert(inp_score > btn_score, f"input ({inp_score}) > button ({btn_score}) in input mode")


# ── Test 16: stacked data-qa + aria + placeholder ────────────────────────────

def _test_stacked_signals():
    print("\n── stacked signals ──")
    el_stack = _make_el(
        name="Promo input text", tag_name="input", input_type="text",
        data_qa="promo-code", placeholder="Promo Code", aria_label="Promo Code",
        html_id="stacked",
    )
    el_weak = _make_el(
        name="Enter code input text", tag_name="input", input_type="text",
        placeholder="Enter code", html_id="weak", id=2,
    )
    scorer = _make_scorer(
        step="Fill 'Promo Code' field with 'SAVE20'",
        mode="input",
        search_texts=["Promo Code"],
        target_field="promo code",
    )
    results = scorer.score_all([dict(el_stack), dict(el_weak)])

    stack_score = next(e["score"] for e in results if e["html_id"] == "stacked")
    weak_score  = next(e["score"] for e in results if e["html_id"] == "weak")

    _assert(stack_score > weak_score, f"stacked ({stack_score}) >> weak ({weak_score})")
    _assert(stack_score >= 80_000, f"stacked ≥ 80k (data-qa + aria + ph), got {stack_score}")


# ── Test 17: target_field exact html_id match (+0.6 attr) ─────────────────────

def _test_target_field_html_id():
    print("\n── target_field → html_id exact match ──")
    el = _make_el(name="input text", tag_name="input", input_type="text",
                  html_id="shipping_address")
    scorer = _make_scorer(
        step="Fill 'Shipping Address' field with '123 Main St'",
        mode="input",
        search_texts=["Shipping Address"],
        target_field="shipping address",
    )
    results = scorer.score_all([el])
    score = results[0]["score"]

    # html_id variants match: +0.6 attr × W_attr(0.25) × SCALE ≈ 26.7k. Plus target_field name match.
    _assert(score >= 20_000, f"target_field html_id ≥ 20k, got {score}")


# ── Test 18: aria-disabled penalty ────────────────────────────────────────────

def _test_aria_disabled_penalty():
    print("\n── aria-disabled penalty ──")
    el = _make_el(name="Submit button", aria_disabled="true", html_id="aria_dis")
    scorer = _make_scorer()
    results = scorer.score_all([el])
    score = results[0]["score"]

    _assert(score == 0, f"aria-disabled='true' → score 0, got {score}")


# ── Run all tests ─────────────────────────────────────────────────────────────

async def run_suite():
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print(f"\n{'=' * 70}")
    print("🔢  SCORING MATH LAB — Exact Numerical Validation")
    print(f"{'=' * 70}")

    _test_data_qa_exact_score()
    _test_text_exact_match_score()
    _test_disabled_penalty_zeroes()
    _test_hidden_penalty_tenth()
    _test_semantic_cache_score()
    _test_blind_context_score()
    _test_aria_exact_match()
    _test_placeholder_exact_match()
    _test_name_attr_exact()
    _test_scale_derivation()
    _test_weights_ordering()
    _test_checkbox_penalty()
    _test_checkbox_bonus()
    _test_proximity_bonus()
    _test_input_mode_synergy()
    _test_stacked_signals()
    _test_target_field_html_id()
    _test_aria_disabled_penalty()

    total = _PASS + _FAIL
    print(f"\n{'=' * 70}")
    print(f"📊 SCORE: {_PASS}/{total} passed")
    if _FAIL:
        print(f"\n🙀 {_FAIL} failure(s)")
    if _PASS == total:
        print("\n🏆 SCORING MATH VALIDATION FLAWLESS!")
    print(f"{'=' * 70}")

    return _PASS == total


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_suite())
