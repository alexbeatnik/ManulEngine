# manul_engine/test/test_44_explain_mode.py
"""
Unit-test suite for --explain mode (heuristic score breakdown).

Tests:
  1. DOMScorer with explain=True attaches _explain dict to scored elements
  2. _explain dict contains all 7 expected keys
  3. Channel scores sum correctly to total (when no penalty)
  4. Penalty multiplier is reflected in _explain
  5. explain=False (default) does NOT attach _explain
  6. score_elements() passes explain flag through
  7. _print_explain() output format validation

No network or browser required.
"""

from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.scoring import DOMScorer, WEIGHTS, SCALE, MAX_THEORETICAL_SCORE, score_elements

# ── Test helpers ──────────────────────────────────────────────────────────────

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


def _make_el(**overrides) -> dict:
    """Build a minimal element dict compatible with DOMScorer._preprocess."""
    base = {
        "name": overrides.pop("name", "Login button"),
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


def _make_scorer(explain: bool = True, **overrides) -> DOMScorer:
    return DOMScorer(
        step=overrides.get("step", "Click the 'Login' button"),
        mode=overrides.get("mode", "clickable"),
        search_texts=overrides.get("search_texts", ["Login"]),
        target_field=overrides.get("target_field", None),
        is_blind=overrides.get("is_blind", False),
        learned_elements=overrides.get("learned_elements", {}),
        last_xpath=overrides.get("last_xpath", None),
        explain=explain,
    )


# ── Section 1: _explain dict is attached when explain=True ───────────────────

def _test_explain_attached() -> None:
    print("\n  ── _explain dict attached ────────────────────────────────────")

    el = _make_el(name="Login button")
    scorer = _make_scorer(explain=True)
    results = scorer.score_all([el])

    _assert(len(results) == 1, "Scored one element")
    _assert("_explain" in results[0], "_explain key present when explain=True")


# ── Section 2: _explain has all 7 keys ───────────────────────────────────────

def _test_explain_keys() -> None:
    print("\n  ── _explain key set ──────────────────────────────────────────")

    el = _make_el(name="Login button")
    scorer = _make_scorer(explain=True)
    results = scorer.score_all([el])
    expl = results[0]["_explain"]

    expected_keys = {"text", "attributes", "semantics", "proximity", "cache", "penalty", "total"}
    _assert(set(expl.keys()) == expected_keys,
            f"All 7 keys present: {sorted(expl.keys())}")

    _assert(isinstance(expl["text"], float), "text is float")
    _assert(isinstance(expl["attributes"], float), "attributes is float")
    _assert(isinstance(expl["semantics"], float), "semantics is float")
    _assert(isinstance(expl["proximity"], float), "proximity is float")
    _assert(isinstance(expl["cache"], float), "cache is float")
    _assert(isinstance(expl["penalty"], (int, float)), "penalty is numeric")
    _assert(isinstance(expl["total"], float), "total is float")

    # All channel values and total must be in [0.0, 1.0]
    for key in ("text", "attributes", "semantics", "proximity", "cache", "total"):
        _assert(0.0 <= expl[key] <= 1.0, f"{key} in [0.0, 1.0]: {expl[key]}")


# ── Section 3: Channel scores sum to total (no penalty) ─────────────────────

def _test_channel_sum() -> None:
    print("\n  ── Channel sum → total ──────────────────────────────────────")

    el = _make_el(name="Login button")
    scorer = _make_scorer(explain=True)
    results = scorer.score_all([el])
    expl = results[0]["_explain"]

    channel_sum = sum(expl[k] for k in ("text", "attributes", "semantics", "proximity", "cache"))

    if expl["penalty"] == 1.0:
        _assert(abs(expl["total"] - channel_sum) < 0.01,
                f"total ({expl['total']}) ≈ sum of channels ({channel_sum:.3f})")
    else:
        # With penalty, total < channel_sum
        _assert(expl["total"] < channel_sum + 0.001,
                f"total ({expl['total']}) < sum ({channel_sum:.3f}) due to penalty {expl['penalty']}")

    _assert(expl["total"] == round(min(results[0]["score"] / MAX_THEORETICAL_SCORE, 1.0), 3),
            "total matches normalized el['score']")


# ── Section 4: Penalty multiplier for disabled elements ──────────────────────

def _test_penalty_disabled() -> None:
    print("\n  ── Penalty: disabled element ─────────────────────────────────")

    el = _make_el(name="Login button", disabled=True)
    scorer = _make_scorer(explain=True)
    results = scorer.score_all([el])
    expl = results[0]["_explain"]

    _assert(expl["penalty"] == 0.0,
            f"Disabled penalty = 0.0, got {expl['penalty']}")
    _assert(expl["total"] == 0.0,
            f"Disabled element total = 0.0, got {expl['total']}")


# ── Section 5: explain=False does NOT attach _explain ────────────────────────

def _test_no_explain_by_default() -> None:
    print("\n  ── No _explain when explain=False ────────────────────────────")

    el = _make_el(name="Login button")
    scorer = _make_scorer(explain=False)
    results = scorer.score_all([el])

    _assert("_explain" not in results[0],
            "_explain absent when explain=False")


# ── Section 6: score_elements() passes explain through ──────────────────────

def _test_score_elements_explain() -> None:
    print("\n  ── score_elements() explain passthrough ──────────────────────")

    el = _make_el(name="Login button")
    results = score_elements(
        els=[el],
        step="Click the 'Login' button",
        mode="clickable",
        search_texts=["Login"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        explain=True,
    )

    _assert("_explain" in results[0],
            "score_elements with explain=True attaches _explain")

    results2 = score_elements(
        els=[_make_el(name="Login button")],
        step="Click the 'Login' button",
        mode="clickable",
        search_texts=["Login"],
        target_field=None,
        is_blind=False,
        learned_elements={},
        last_xpath=None,
        explain=False,
    )
    _assert("_explain" not in results2[0],
            "score_elements with explain=False omits _explain")


# ── Section 7: _print_explain output format ──────────────────────────────────

def _test_print_explain_format() -> None:
    print("\n  ── _print_explain output format ──────────────────────────────")

    # Import ManulEngine only for its static method — no browser needed
    from manul_engine.core import ManulEngine

    el = _make_el(name="Login button", tag_name="button")
    el["score"] = 50000
    el["_explain"] = {
        "text": 0.169,
        "attributes": 0.028,
        "semantics": 0.056,
        "proximity": 0.028,
        "cache": 0.0,
        "penalty": 1.0,
        "total": 0.281,
    }

    old_stdout = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        ManulEngine._print_explain("Click 'Login' button", ["Login"], [el])
    finally:
        sys.stdout = old_stdout

    output = buf.getvalue()
    _assert("EXPLAIN" in output, "Output contains 'EXPLAIN' header")
    _assert("Login" in output, "Output contains target name")
    _assert("Text:" in output, "Output contains 'Text:' channel label")
    _assert("Attributes:" in output, "Output contains 'Attributes:' label")
    _assert("Semantics:" in output, "Output contains 'Semantics:' label")
    _assert("Proximity:" in output, "Output contains 'Proximity:' label")
    _assert("Cache:" in output, "Output contains 'Cache:' label")
    _assert("Decision:" in output, "Output contains 'Decision:' line")


# ── Section 8: Multiple elements — explain on each ──────────────────────────

def _test_explain_multiple_elements() -> None:
    print("\n  ── Explain on multiple elements ──────────────────────────────")

    els = [
        _make_el(name="Login button", id=1),
        _make_el(name="Logout button", id=2),
        _make_el(name="Submit button", id=3),
    ]
    scorer = _make_scorer(explain=True)
    results = scorer.score_all(els)

    all_have_explain = all("_explain" in r for r in results)
    _assert(all_have_explain, "All scored elements have _explain when explain=True")

    all_have_total = all(
        r["_explain"]["total"] == round(min(r["score"] / MAX_THEORETICAL_SCORE, 1.0), 3)
        for r in results
    )
    _assert(all_have_total, "All _explain.total match normalized el.score")


# ── Run ───────────────────────────────────────────────────────────────────────

async def run_suite() -> None:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n🔍 TEST SUITE: Explain Mode (v0.0.9.4)")

    _test_explain_attached()
    _test_explain_keys()
    _test_channel_sum()
    _test_penalty_disabled()
    _test_no_explain_by_default()
    _test_score_elements_explain()
    _test_print_explain_format()
    _test_explain_multiple_elements()

    total = _PASS + _FAIL
    print(f"\n    SCORE: {_PASS}/{total}")
    if _FAIL:
        print(f"    ⚠️  {_FAIL} assertion(s) failed!")
