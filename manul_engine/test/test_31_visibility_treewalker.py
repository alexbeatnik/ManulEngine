import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine import ManulEngine

# ─────────────────────────────────────────────────────────────────────────────
# DOM: VISIBILITY & TREEWALKER — Scanner Filtering Gauntlet (20 Tests)
#
# Validates:
# 1. TreeWalker PRUNE set skips SCRIPT/STYLE/SVG/TEMPLATE subtrees entirely
# 2. checkVisibility() API filters display:none, visibility:hidden, opacity:0
# 3. Hidden elements get [HIDDEN] suffix → ×0.1 penalty in scoring
# 4. Special inputs (checkbox, radio, file) remain discoverable even when hidden
# 5. Visible element always wins over hidden duplicate
# 6. aria-hidden="true" elements are properly penalized
# ─────────────────────────────────────────────────────────────────────────────
VISIBILITY_DOM = """
<!DOCTYPE html><html><head><title>Visibility & TreeWalker Lab</title>
<style>
    .offscreen { position: absolute; left: -10000px; top: -10000px; }
    .zero-dim  { width: 0; height: 0; overflow: hidden; display: inline-block; }
    .sr-only   { position: absolute; width: 1px; height: 1px; padding: 0;
                 margin: -1px; overflow: hidden; clip: rect(0,0,0,0);
                 white-space: nowrap; border: 0; }
</style>
</head><body>

<!-- Group 1: display:none — invisible element should lose to visible -->
<button id="vis_btn1">Checkout</button>
<button id="hid_btn1" style="display:none;">Checkout</button>

<!-- Group 2: visibility:hidden -->
<button id="vis_btn2">Pay Now</button>
<button id="hid_btn2" style="visibility:hidden;">Pay Now</button>

<!-- Group 3: opacity:0 (checkVisibility checks opacity) -->
<button id="vis_btn3">Apply Coupon</button>
<button id="hid_btn3" style="opacity:0;">Apply Coupon</button>

<!-- Group 4: offscreen (position absolute, far left) -->
<button id="vis_btn4">Subscribe</button>
<button id="hid_btn4" class="offscreen">Subscribe</button>

<!-- Group 5: zero-size element -->
<button id="vis_btn5">Refresh</button>
<button id="hid_btn5" class="zero-dim">Refresh</button>

<!-- Group 6: aria-hidden="true" -->
<button id="vis_btn6">Connect Wallet</button>
<button id="hid_btn6" aria-hidden="true">Connect Wallet</button>

<!-- Group 7: nested in display:none parent -->
<div style="display:none;">
    <button id="nested_hid">Hidden Nested Delete</button>
</div>
<button id="nested_vis">Delete</button>

<!-- Group 8: PRUNE subtrees — buttons inside SCRIPT, STYLE, TEMPLATE, NOSCRIPT -->
<script>
    // This button text should never appear in snapshot
    document.write('<button id="script_btn">Inside Script</button>');
</script>
<noscript>
    <button id="noscript_btn">Inside NoScript</button>
</noscript>
<template>
    <button id="template_btn">Inside Template</button>
</template>
<button id="real_action_btn">Action Button</button>

<!-- Group 9: special inputs — hidden file/checkbox/radio ARE still discoverable -->
<input id="file_hidden" type="file" style="display:none;">
<label id="file_label" for="file_hidden">Upload Resume</label>

<input id="chk_hidden" type="checkbox" style="display:none;">
<label id="chk_label" for="chk_hidden">Accept Terms</label>

<input id="radio_hidden" type="radio" name="gender" value="male" style="display:none;">
<label id="radio_label" for="radio_hidden">Male</label>

<!-- Group 10: multiple layers of hiding stacked -->
<div style="visibility:hidden;">
    <div style="opacity:0;">
        <button id="deep_hid">Deep Hidden Submit</button>
    </div>
</div>
<button id="deep_vis">Submit</button>

<!-- Group 11: clip-rect sr-only pattern (screen reader only) -->
<button id="sr_btn" class="sr-only">Accessible Only</button>
<button id="normal_btn">Normal Button</button>

<!-- Group 12: shadow DOM visibility (element inside shadow root) -->
<div id="shadow_host"></div>
<script>
    const host = document.getElementById('shadow_host');
    const shadow = host.attachShadow({ mode: 'open' });
    shadow.innerHTML = '<button id="shadow_btn">Shadow Action</button>';
</script>

<!-- Group 13: data-manul-debug overlay — must be pruned by TreeWalker -->
<div id="manul-debug-modal" data-manul-debug="true"
     style="position:fixed;top:12px;right:12px;z-index:2147483647;">
    <div>🐾 MANUL DEBUG PAUSE</div>
    <div>Fill "Name" field with "Mega Manul"</div>
    <button id="manul-debug-abort">✕</button>
</div>
<button id="real_after_debug">Name</button>

</body></html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
TESTS = [
    # ── Group 1: display:none ──────────────────────────────────────────
    {
        "n": "1. Visible beats display:none",
        "step": "Click the 'Checkout' button",
        "m": "clickable",
        "st": ["Checkout"],
        "tf": None,
        "exp": "vis_btn1",
    },
    # ── Group 2: visibility:hidden ─────────────────────────────────────
    {
        "n": "2. Visible beats visibility:hidden",
        "step": "Click the 'Pay Now' button",
        "m": "clickable",
        "st": ["Pay Now"],
        "tf": None,
        "exp": "vis_btn2",
    },
    # ── Group 3: opacity:0 ────────────────────────────────────────────
    {
        "n": "3. Visible beats opacity:0",
        "step": "Click the 'Apply Coupon' button",
        "m": "clickable",
        "st": ["Apply Coupon"],
        "tf": None,
        "exp": "vis_btn3",
    },
    # ── Group 4: offscreen ────────────────────────────────────────────
    {
        "n": "4. Visible beats offscreen",
        "step": "Click the 'Subscribe' button",
        "m": "clickable",
        "st": ["Subscribe"],
        "tf": None,
        "exp": "vis_btn4",
    },
    # ── Group 5: zero-size ────────────────────────────────────────────
    {
        "n": "5. Visible beats zero-size",
        "step": "Click the 'Refresh' button",
        "m": "clickable",
        "st": ["Refresh"],
        "tf": None,
        "exp": "vis_btn5",
    },
    # ── Group 6: aria-hidden ──────────────────────────────────────────
    {
        "n": "6. Visible beats aria-hidden",
        "step": "Click the 'Connect Wallet' button",
        "m": "clickable",
        "st": ["Connect Wallet"],
        "tf": None,
        "exp": "vis_btn6",
    },
    # ── Group 7: nested hiding ────────────────────────────────────────
    {
        "n": "7. Visible beats nested-in-display-none",
        "step": "Click the 'Delete' button",
        "m": "clickable",
        "st": ["Delete"],
        "tf": None,
        "exp": "nested_vis",
    },
    # ── Group 8: PRUNE subtrees ──────────────────────────────────────
    {
        "n": "8. Action button found (PRUNE skips script/template)",
        "step": "Click the 'Action Button' button",
        "m": "clickable",
        "st": ["Action Button"],
        "tf": None,
        "exp": "real_action_btn",
    },
    # ── Group 9: special hidden inputs ───────────────────────────────
    {
        "n": "9. Hidden file input — label clickable",
        "step": "Click the 'Upload Resume' button",
        "m": "clickable",
        "st": ["Upload Resume"],
        "tf": None,
        "exp": "file_label",
    },
    {
        "n": "10. Hidden checkbox — engine finds real input (special input)",
        "step": "Check the 'Accept Terms' checkbox",
        "m": "clickable",
        "st": ["Accept Terms"],
        "tf": None,
        "exp": "chk_hidden",
    },
    {
        "n": "11. Hidden radio — label clickable",
        "step": "Click the radio button for 'Male'",
        "m": "clickable",
        "st": ["Male"],
        "tf": None,
        "exp": "radio_label",
    },
    # ── Group 10: deep nested hiding ─────────────────────────────────
    {
        "n": "12. Visible beats deeply hidden element",
        "step": "Click the 'Submit' button",
        "m": "clickable",
        "st": ["Submit"],
        "tf": None,
        "exp": "deep_vis",
    },
    # ── Group 12: shadow DOM visibility ──────────────────────────────
    {
        "n": "13. Shadow DOM button is discoverable",
        "step": "Click the 'Shadow Action' button",
        "m": "clickable",
        "st": ["Shadow Action"],
        "tf": None,
        "exp": "shadow_btn",
    },
]


async def _test_snapshot_filtering(page, manul):
    """Verify that _snapshot does not return elements from pruned subtrees."""
    print(f"\n{'─' * 70}")
    print("🔬 Part 2: Snapshot Filtering Assertions")
    print(f"{'─' * 70}")

    p = 0
    f = 0
    failures: list[str] = []

    # Get the full snapshot
    all_els = await manul._snapshot(page, "clickable", [])
    all_names_lower = " ".join(str(el.get("name", "")).lower() for el in all_els)
    all_ids = {str(el.get("html_id", "")) for el in all_els}

    # 1. Elements inside <template> should NOT appear
    if "template_btn" not in all_ids:
        print("    ✅  <template> elements excluded from snapshot")
        p += 1
    else:
        print("    ❌  <template> elements FOUND in snapshot (should be pruned)")
        f += 1
        failures.append("template elements in snapshot")

    # 2. Elements inside <noscript> should NOT appear
    if "noscript_btn" not in all_ids:
        print("    ✅  <noscript> elements excluded from snapshot")
        p += 1
    else:
        print("    ❌  <noscript> elements FOUND in snapshot (should be pruned)")
        f += 1
        failures.append("noscript elements in snapshot")

    # 2b. data-manul-debug overlay must be pruned (no child elements in snapshot)
    debug_ids = {"manul-debug-modal", "manul-debug-abort"}
    debug_leaked = debug_ids & all_ids
    debug_name_leaked = any("MANUL DEBUG PAUSE" in str(el.get("name", "")) for el in all_els)
    if not debug_leaked and not debug_name_leaked:
        print("    ✅  data-manul-debug overlay excluded from snapshot")
        p += 1
    else:
        print(f"    ❌  debug overlay elements FOUND in snapshot (leaked ids={debug_leaked})")
        f += 1
        failures.append("data-manul-debug overlay in snapshot")

    # 2c. Real element after debug overlay is still discoverable
    if "real_after_debug" in all_ids:
        print("    ✅  Element after debug overlay still in snapshot")
        p += 1
    else:
        print("    ❌  Element after debug overlay missing from snapshot")
        f += 1
        failures.append("real_after_debug missing")

    # 3. Hidden elements may appear but with [HIDDEN] tag
    hidden_els = [
        el for el in all_els if "[HIDDEN]" in str(el.get("name", "")).upper() or "[hidden]" in str(el.get("name", ""))
    ]
    visible_els = [
        el
        for el in all_els
        if "[HIDDEN]" not in str(el.get("name", "")).upper() and "[hidden]" not in str(el.get("name", ""))
    ]

    if len(visible_els) > 0:
        print(f"    ✅  Snapshot contains {len(visible_els)} visible + {len(hidden_els)} hidden elements")
        p += 1
    else:
        print("    ❌  No visible elements in snapshot")
        f += 1
        failures.append("no visible elements")

    # 4. Shadow DOM element should be discoverable
    shadow_els = [el for el in all_els if el.get("is_shadow", False)]
    if len(shadow_els) > 0:
        print(f"    ✅  Shadow DOM elements discovered ({len(shadow_els)} found)")
        p += 1
    else:
        print("    ❌  No shadow DOM elements in snapshot")
        f += 1
        failures.append("no shadow DOM elements")

    # 5. Each element has required keys from SNAPSHOT_JS
    required_keys = {"id", "name", "xpath", "tag_name", "data_qa", "html_id", "aria_label"}
    if all_els:
        sample = all_els[0]
        missing = required_keys - set(sample.keys())
        if not missing:
            print(f"    ✅  Element dict has all required keys")
            p += 1
        else:
            print(f"    ❌  Missing keys: {missing}")
            f += 1
            failures.append(f"missing keys: {missing}")
    else:
        print("    ❌  Snapshot returned 0 elements")
        f += 1
        failures.append("empty snapshot")

    # 6. Hidden elements should have lower scores than visible ones
    # Score both a visible and hidden "Checkout" button
    scored = await manul._snapshot(page, "clickable", ["Checkout"])
    from manul_engine.scoring import score_elements

    scored = score_elements(scored, "Click 'Checkout'", "clickable", ["Checkout"], None, False, {}, None)
    vis_scores = [el["score"] for el in scored if el.get("html_id") == "vis_btn1"]
    hid_scores = [el["score"] for el in scored if el.get("html_id") == "hid_btn1"]
    if vis_scores and hid_scores:
        if vis_scores[0] > hid_scores[0]:
            print(f"    ✅  Visible 'Checkout' score ({vis_scores[0]}) > hidden ({hid_scores[0]})")
            p += 1
        else:
            print(f"    ❌  Visible score ({vis_scores[0]}) NOT > hidden ({hid_scores[0]})")
            f += 1
            failures.append("visible not scored higher than hidden")
    elif vis_scores:
        # Hidden was completely filtered out — also acceptable
        print(f"    ✅  Hidden 'Checkout' filtered out entirely (visible score={vis_scores[0]})")
        p += 1
    else:
        print(f"    ❌  Could not find vis_btn1 in scored elements")
        f += 1
        failures.append("vis_btn1 not in scored elements")

    # 7. Opacity:0 element either filtered or penalized
    opacity_scored = score_elements(
        await manul._snapshot(page, "clickable", ["Apply Coupon"]),
        "Click 'Apply Coupon'",
        "clickable",
        ["Apply Coupon"],
        None,
        False,
        {},
        None,
    )
    vis3 = [el["score"] for el in opacity_scored if el.get("html_id") == "vis_btn3"]
    hid3 = [el["score"] for el in opacity_scored if el.get("html_id") == "hid_btn3"]
    if vis3 and hid3:
        if vis3[0] > hid3[0]:
            print(f"    ✅  opacity:0 element penalized (vis={vis3[0]} > hid={hid3[0]})")
            p += 1
        else:
            print(f"    ❌  opacity:0 not penalized properly")
            f += 1
            failures.append("opacity:0 not penalized")
    elif vis3:
        print(f"    ✅  opacity:0 element completely filtered (only visible returned)")
        p += 1
    else:
        print(f"    ❌  vis_btn3 not found")
        f += 1
        failures.append("vis_btn3 missing")

    return p, f, failures


async def run_suite():
    print(f"\n{'=' * 70}")
    print("👁️   VISIBILITY & TREEWALKER LAB — Scanner Filtering Gauntlet")
    print(f"{'=' * 70}")

    manul = ManulEngine(headless=True, disable_cache=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(VISIBILITY_DOM)

        # ── Part 1: Resolution tests ────────────────────────────────
        print(f"\n{'─' * 70}")
        print(f"🌐 Part 1: Visibility Resolution Tests ({len(TESTS)} traps)")
        print(f"{'─' * 70}")

        passed = failed = 0
        failures: list[str] = []

        for t in TESTS:
            print(f"\n👁️  {t['n']}")
            print(f"   🐾 Step : {t['step']}")

            manul.reset_session_state()

            el = await manul._resolve_element(page, t["step"], t["m"], t["st"], t["tf"], "", set())

            if el is None:
                msg = "FAILED — element not found (None)"
                print(f"   ❌ {msg}")
                failed += 1
                failures.append(f"{t['n']}: {msg}")
                continue

            found_id = el.get("html_id", "")
            if found_id == t["exp"]:
                print(f"   ✅ PASSED  → '{found_id}'")
                passed += 1
            else:
                msg = f"FAILED — got '{found_id}', expected '{t['exp']}'"
                print(f"   ❌ {msg}")
                failed += 1
                failures.append(f"{t['n']}: {msg}")

        # ── Part 2: Snapshot filtering assertions ───────────────────
        snap_p, snap_f, snap_failures = await _test_snapshot_filtering(page, manul)
        failures.extend(snap_failures)

        total = len(TESTS) + snap_p + snap_f
        total_passed = passed + snap_p

        print(f"\n{'=' * 70}")
        print(f"📊 SCORE: {total_passed}/{total} passed")
        print(f"   Resolution: {passed}/{len(TESTS)}")
        print(f"   Snapshot:   {snap_p}/{snap_p + snap_f}")
        if failures:
            print("\n🙀 Failures:")
            for f in failures:
                print(f"   • {f}")
        if total_passed == total:
            print("\n🏆 VISIBILITY FILTERING FLAWLESS — TreeWalker + checkVisibility() are airtight!")
        print(f"{'=' * 70}")
        await browser.close()

    return total_passed == total


if __name__ == "__main__":
    asyncio.run(run_suite())
