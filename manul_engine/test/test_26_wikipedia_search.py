# manul_engine/test/test_26_wikipedia_search.py
"""
Unit-test suite for heuristic scoring of Wikipedia Vector 2022-style
search inputs — no browser required.

Tests call score_elements() directly with synthetic element dicts to
verify that <input type="search"> elements are correctly identified and
ranked above decoys when:
  • aria-label / placeholder match the search text exactly,
  • the HTML `name` attribute provides an extra scoring signal,
  • competing buttons, text inputs, and links do not outscore the target.

Also validates the new `name_attr` scoring feature: the HTML form `name`
attribute (e.g. name="search", name="q") is now exposed in element dicts
and used as a secondary scoring signal in the text-matching pass.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.scoring import score_elements

# ── Helpers ───────────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0


def _assert(condition: bool, name: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"    ✅  {name}")
    else:
        _FAIL += 1
        suffix = f" ({detail})" if detail else ""
        print(f"    ❌  {name}{suffix}")


def _el(
    name: str,
    tag: str = "input",
    itype: str = "text",
    aria: str = "",
    ph: str = "",
    html_id: str = "",
    data_qa: str = "",
    cls: str = "",
    role: str = "",
    name_attr: str = "",
    uid: int = 0,
    disabled: bool = False,
) -> dict:
    """Build a minimal element dict matching the shape returned by SNAPSHOT_JS."""
    return {
        "id": uid,
        "name": name,
        "xpath": f"//*[@id='{html_id or uid}']",
        "tag_name": tag,
        "input_type": itype,
        "aria_label": aria,
        "placeholder": ph,
        "role": role,
        "html_id": html_id,
        "data_qa": data_qa,
        "class_name": cls,
        "icon_classes": "",
        "is_select": False,
        "is_shadow": False,
        "is_contenteditable": False,
        "disabled": disabled,
        "aria_disabled": "",
        "name_attr": name_attr,
    }


def _score(el: dict, step: str, mode: str, search_texts: list[str]) -> int:
    """Call score_elements for a single element and return its score."""
    scored = score_elements(
        [el], step, mode, search_texts, None, False, {}, None
    )
    return scored[0].get("score", 0)


def _rank1(els: list[dict], step: str, mode: str, search_texts: list[str]) -> dict:
    """Return the top-ranked element from a list."""
    return score_elements(els, step, mode, search_texts, None, False, {}, None)[0]


# ── Section 1: Basic Wikipedia scenario ──────────────────────────────────────

def _test_wiki_search_wins_over_button() -> None:
    print("\n  ── Wikipedia search input beats submit button ─────────────")

    wiki_input = _el(
        "Search Wikipedia input search",
        tag="input", itype="search",
        aria="Search Wikipedia",
        ph="search wikipedia",
        cls="cdx-text-input__input",
        role="searchbox",
        name_attr="search",
        uid=0,
    )
    submit_btn = _el(
        "Search button",
        tag="button", itype="submit",
        aria="Search",
        html_id="searchButton",
        uid=1,
    )
    nav_link = _el(
        "Search results link",
        tag="a", itype="",
        uid=2,
    )

    step = "Fill 'Search Wikipedia' with 'Neuro-symbolic AI'"
    search_texts = ["Search Wikipedia"]
    ranked = score_elements(
        [wiki_input, submit_btn, nav_link],
        step, "input", search_texts, None, False, {}, None,
    )

    best = ranked[0]
    _assert(best["id"] == 0, "Wikipedia search input ranked #1")
    input_score = next(e["score"] for e in ranked if e["id"] == 0)
    btn_score   = next(e["score"] for e in ranked if e["id"] == 1)
    _assert(input_score > btn_score, "Search input outscores submit button",
            f"input={input_score}, btn={btn_score}")


# ── Section 2: aria-label and placeholder matching ────────────────────────────

def _test_aria_exact_match_score() -> None:
    print("\n  ── Exact aria-label match produces large score ────────────")

    target = _el("Search Wikipedia input search", itype="search",
                 aria="Search Wikipedia", uid=0)
    decoy  = _el("Username input text", itype="text",
                 aria="Username", uid=1)

    step = "Fill 'Search Wikipedia' with 'test'"
    search_texts = ["Search Wikipedia"]

    t_score = _score(target, step, "input", search_texts)
    d_score = _score(decoy,  step, "input", search_texts)

    _assert(t_score >= 50_000, "Exact aria-label match ≥ 50,000",
            f"got {t_score}")
    _assert(t_score > d_score, "aria match outscores unrelated input",
            f"target={t_score}, decoy={d_score}")


def _test_placeholder_exact_match_score() -> None:
    print("\n  ── Exact placeholder match produces same large score ──────")

    # Element whose placeholder matches (but no aria-label)
    ph_only = _el("search wikipedia input search", itype="search",
                  ph="search wikipedia", uid=0)
    step = "Fill 'Search Wikipedia' with 'test'"
    ph_score = _score(ph_only, step, "input", ["Search Wikipedia"])

    _assert(ph_score >= 50_000, "Exact placeholder match ≥ 50,000",
            f"got {ph_score}")


def _test_partial_aria_match_lower_than_exact() -> None:
    print("\n  ── Partial aria match scores below exact ──────────────────")

    exact   = _el("Search Wikipedia input search", itype="search",
                  aria="Search Wikipedia", uid=0)
    partial = _el("Wikipedia input search", itype="search",
                  aria="Wikipedia Help", uid=1)

    step = "Fill 'Search Wikipedia' with 'test'"
    search_texts = ["Search Wikipedia"]

    e_score = _score(exact,   step, "input", search_texts)
    p_score = _score(partial, step, "input", search_texts)

    _assert(e_score > p_score, "Exact aria > partial aria match",
            f"exact={e_score}, partial={p_score}")


# ── Section 3: name_attr scoring ─────────────────────────────────────────────

def _test_name_attr_exact_match() -> None:
    print("\n  ── HTML name attribute: exact match adds +3,000 ───────────")

    with_name    = _el("search input search", itype="search", name_attr="search", uid=0)
    without_name = _el("search input search", itype="search", name_attr="",       uid=1)

    step = "Fill 'search' field with 'test'"
    search_texts = ["search"]

    wn_score = _score(with_name,    step, "input", search_texts)
    wo_score = _score(without_name, step, "input", search_texts)

    _assert(wn_score > wo_score, "name_attr exact match raises score",
            f"with_name={wn_score}, without={wo_score}")
    _assert(wn_score - wo_score == 3_000, "name_attr exact match difference is +3,000",
            f"diff={wn_score - wo_score}")


def _test_name_attr_substring_match() -> None:
    print("\n  ── HTML name attribute: substring in search_text adds +1,000 ")

    # name_attr="search" and tl="search wikipedia" → "search" in "search wikipedia"
    with_name    = _el("Search Wikipedia input search", itype="search",
                        aria="Search Wikipedia", name_attr="search", uid=0)
    without_name = _el("Search Wikipedia input search", itype="search",
                        aria="Search Wikipedia", name_attr="",       uid=1)

    step = "Fill 'Search Wikipedia' with 'AI'"
    search_texts = ["Search Wikipedia"]

    wn_score = _score(with_name,    step, "input", search_texts)
    wo_score = _score(without_name, step, "input", search_texts)

    _assert(wn_score > wo_score, "name_attr substring match raises score",
            f"with_name={wn_score}, without={wo_score}")
    _assert(wn_score - wo_score == 1_000, "name_attr substring match difference is +1,000",
            f"diff={wn_score - wo_score}")


def _test_name_attr_short_ignored() -> None:
    print("\n  ── HTML name attribute: length < 3 not used as substring ──")

    # name_attr="q" (len=1) should not give substring bonus for "q" in "quite long query"
    short_name = _el("quite long query input search", itype="search",
                      name_attr="q", uid=0)
    no_name    = _el("quite long query input search", itype="search",
                      name_attr="", uid=1)

    step = "Fill 'quite long query' with 'test'"
    search_texts = ["quite long query"]

    sn_score = _score(short_name, step, "input", search_texts)
    nn_score = _score(no_name,    step, "input", search_texts)

    # exact match check: "quite long query" != "q" → no +3000
    # substring check: len("q") < 3 → no +1000
    _assert(sn_score == nn_score, "name_attr len<3 does not trigger substring bonus",
            f"short={sn_score}, none={nn_score}")


# ── Section 4: type="search" treated as real input ───────────────────────────

def _test_search_type_not_penalized_in_input_mode() -> None:
    print("\n  ── type='search' is not penalized in mode='input' ─────────")

    search_el = _el("My Search input search", itype="search",
                    aria="My Search", uid=0)
    text_el   = _el("My Search input text", itype="text",
                    aria="My Search", uid=1)

    step = "Fill 'My Search' with 'test'"
    search_texts = ["My Search"]

    s_score = _score(search_el, step, "input", search_texts)
    t_score = _score(text_el,   step, "input", search_texts)

    # type="search" should score at least as well as type="text" with the same aria-label
    _assert(s_score >= t_score, "type=search ≥ type=text for same aria-label",
            f"search={s_score}, text={t_score}")


def _test_search_type_is_real_input() -> None:
    print("\n  ── type='search' passes is_real_input check ───────────────")

    # If type="search" were treated as excluded (like "submit"/"button"),
    # it would receive the mode cross-penalty: score -= 50,000
    # A correct implementation should give a positive score.

    search_el = _el("Query input search", itype="search",
                    aria="Query", uid=0)
    btn_el    = _el("Query button", itype="submit",
                    aria="Query", uid=1)

    step = "Fill 'Query' with 'x'"
    st = _score(search_el, step, "input", ["Query"])
    bt = _score(btn_el,    step, "input", ["Query"])

    _assert(st > 0,  "type=search element has positive score in input mode",
            f"score={st}")
    _assert(bt < st, "submit button scores less than search input in input mode",
            f"btn={bt}, input={st}")


def _test_role_searchbox_is_real_input() -> None:
    print("\n  ── role='searchbox' treated as real input ──────────────────")

    searchbox = _el("City search input search", itype="search",
                    role="searchbox", aria="City search", uid=0)
    button    = _el("City search button", tag="button", aria="City search", uid=1)

    step = "Fill 'City search' with 'Berlin'"
    ranked = score_elements(
        [searchbox, button], step, "input", ["City search"], None, False, {}, None,
    )

    _assert(ranked[0]["id"] == 0, "role=searchbox ranked #1 over button",
            f"top id={ranked[0]['id']}")


# ── Section 5: Mode synergy fires for perfect text match ────────────────────

def _test_mode_synergy_fires() -> None:
    print("\n  ── Mode synergy adds +50,000 on perfect text match ────────")

    # Synergy expects: is_perfect_text_match=True AND mode=="input" AND is_real_input
    # We verify by checking that the element with a perfect aria match scores
    # at least 100,000 (50k aria + 50k synergy).

    el = _el("Search Wikipedia input search", itype="search",
             aria="Search Wikipedia", uid=0)
    step = "Fill 'Search Wikipedia' with 'test'"
    s = _score(el, step, "input", ["Search Wikipedia"])

    _assert(s >= 100_000, "Mode synergy fires: score ≥ 100,000 for perfect aria match",
            f"score={s}")


# ── Section 6: Full Wikipedia disambiguation scenario ────────────────────────

def _test_wikipedia_full_disambiguation() -> None:
    print("\n  ── Full Wikipedia DOM disambiguation ──────────────────────")

    els = [
        _el("Search Wikipedia input search",
            tag="input", itype="search",
            aria="Search Wikipedia", ph="search wikipedia",
            cls="cdx-text-input__input", role="searchbox",
            name_attr="search", uid=0),
        _el("Search button",
            tag="button", itype="", aria="Search",
            html_id="searchButton", uid=1),
        _el("Create account link",
            tag="a", itype="", uid=2),
        _el("Log in link",
            tag="a", itype="", uid=3),
        _el("Username input text",
            tag="input", itype="text", aria="Username",
            html_id="wpName1", uid=4),
    ]

    step = "Fill 'Search Wikipedia' with 'Neuro-symbolic AI'"
    search_texts = ["Search Wikipedia"]
    ranked = score_elements(
        els, step, "input", search_texts, None, False, {}, None,
    )

    best = ranked[0]
    best_score  = best["score"]
    btn_score   = next(e["score"] for e in ranked if e["id"] == 1)
    user_score  = next(e["score"] for e in ranked if e["id"] == 4)

    _assert(best["id"] == 0, "Wikipedia search input is #1",
            f"top id={best['id']} (score={best_score})")
    _assert(best_score > btn_score * 5, "Search input score dominates button score",
            f"input={best_score}, btn={btn_score}")
    _assert(best_score > user_score,    "Search input outscores Username field",
            f"input={best_score}, username={user_score}")


# ── Section 7: Disabled element penalty ──────────────────────────────────────

def _test_disabled_search_input_penalised() -> None:
    print("\n  ── Disabled search input is penalised ─────────────────────")

    enabled  = _el("Search Wikipedia input search", itype="search",
                   aria="Search Wikipedia", uid=0, disabled=False)
    disabled = _el("Search Wikipedia input search", itype="search",
                   aria="Search Wikipedia", uid=1, disabled=True)

    step = "Fill 'Search Wikipedia' with 'AI'"
    e_score = _score(enabled,  step, "input", ["Search Wikipedia"])
    d_score = _score(disabled, step, "input", ["Search Wikipedia"])

    _assert(e_score > d_score, "Enabled search input outscores disabled one",
            f"enabled={e_score}, disabled={d_score}")


# ── Suite entry point ─────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n🔍 WIKIPEDIA SEARCH INPUT HEURISTICS TEST SUITE")

    _test_wiki_search_wins_over_button()
    _test_aria_exact_match_score()
    _test_placeholder_exact_match_score()
    _test_partial_aria_match_lower_than_exact()
    _test_name_attr_exact_match()
    _test_name_attr_substring_match()
    _test_name_attr_short_ignored()
    _test_search_type_not_penalized_in_input_mode()
    _test_search_type_is_real_input()
    _test_role_searchbox_is_real_input()
    _test_mode_synergy_fires()
    _test_wikipedia_full_disambiguation()
    _test_disabled_search_input_penalised()

    total = _PASS + _FAIL
    icon  = "✅" if _FAIL == 0 else "❌"
    print(f"\n  {icon} Wikipedia search suite: {_PASS}/{total} passed")
    print(f"\nSCORE: {_PASS}/{total}")
    return _FAIL == 0


if __name__ == "__main__":
    asyncio.run(run_suite())
