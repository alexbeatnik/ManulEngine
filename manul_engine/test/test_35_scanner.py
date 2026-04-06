import sys, os, asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from playwright.async_api import async_playwright
from manul_engine.scanner import build_hunt, _is_useful, _map_to_step

# ─────────────────────────────────────────────────────────────────────────────
# SCANNER LAB — Smart Page Scanner Unit Tests (30 Tests)
#
# Validates:
# 1. _is_useful() — filters out noise labels, empty strings, long labels, URLs
# 2. _map_to_step() — maps element types to correct hunt step syntax
# 3. build_hunt() — assembles header, NAVIGATE, WAIT, steps, DONE
# 4. build_hunt() deduplication — same (type, label) pair not repeated
# 5. build_hunt() ordering — step numbers are sequential
# 6. SCAN_JS integration — scans real DOM with checkboxes, radios, selects, etc.
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


# ── Part 1: _is_useful() filter ──────────────────────────────────────────────


def _test_is_useful():
    print("\n── _is_useful() filter ──")
    # Accepted labels
    _assert(_is_useful("Login", "button"), "normal label accepted")
    _assert(_is_useful("Search Products", "input"), "multi-word label accepted")
    _assert(_is_useful("Subscribe to Newsletter", "checkbox"), "long-ish label accepted")

    # Rejected labels
    _assert(not _is_useful("", "button"), "empty string rejected")
    _assert(not _is_useful("button", "button"), "generic 'button' rejected")
    _assert(not _is_useful("click", "button"), "generic 'click' rejected")
    _assert(not _is_useful("×", "button"), "close symbol '×' rejected")
    _assert(not _is_useful("submit", "button"), "generic 'submit' rejected")
    _assert(not _is_useful("https://example.com/page", "link"), "URL rejected")
    _assert(not _is_useful("http://cdn.example.com/asset.js", "link"), "HTTP URL rejected")
    _assert(not _is_useful("A" * 81, "button"), "overlength label (>80) rejected")

    # Edge cases
    _assert(_is_useful("A" * 80, "button"), "exactly 80 chars accepted")
    _assert(not _is_useful("  ", "button"), "whitespace-only rejected")
    _assert(not _is_useful("toggle", "button"), "'toggle' in skip list")


# ── Part 2: _map_to_step() type mapping ─────────────────────────────────────


def _test_map_to_step():
    print("\n── _map_to_step() type mapping ──")

    r = _map_to_step("input", "Email")
    _assert("Fill" in r and "'Email'" in r, f"input → Fill step: {r}")

    r = _map_to_step("select", "Country")
    _assert("Select" in r and "'Country'" in r and "dropdown" in r, f"select → Select step: {r}")

    r = _map_to_step("checkbox", "Terms")
    _assert("Check" in r and "'Terms'" in r and "checkbox" in r, f"checkbox → Check step: {r}")

    r = _map_to_step("radio", "Male")
    _assert("radio" in r and "'Male'" in r, f"radio → radio step: {r}")

    r = _map_to_step("link", "About Us")
    _assert("Click" in r and "'About Us'" in r and "link" in r, f"link → Click link step: {r}")

    r = _map_to_step("button", "Submit")
    _assert("Click" in r and "'Submit'" in r and "button" in r, f"button → Click button step: {r}")

    # No number prefix — plain action text
    _assert(not r[0].isdigit(), f"no number prefix: {r}")


# ── Part 3: build_hunt() assembly ─────────────────────────────────────────────


def _test_build_hunt_basic():
    print("\n── build_hunt() basic assembly ──")
    elements = [
        {"type": "button", "identifier": "Login"},
        {"type": "input", "identifier": "Username"},
        {"type": "input", "identifier": "Password"},
    ]
    result = build_hunt("https://example.com", elements)

    _assert("@context:" in result, "has @context header")
    _assert("@title: scan-draft" in result, "has @title header")
    _assert("NAVIGATE to https://example.com" in result, "has NAVIGATE step")
    _assert("WAIT 2" in result, "has WAIT step")
    _assert("DONE." in result, "has DONE step")
    _assert("'Login'" in result, "Login button present")
    _assert("'Username'" in result, "Username input present")
    _assert("'Password'" in result, "Password input present")


def _test_build_hunt_dedup():
    print("\n── build_hunt() deduplication ──")
    elements = [
        {"type": "button", "identifier": "Save"},
        {"type": "button", "identifier": "Save"},  # exact duplicate
        {"type": "button", "identifier": "save"},  # case-insensitive duplicate
        {"type": "button", "identifier": "Cancel"},
    ]
    result = build_hunt("https://example.com", elements)

    # Count occurrences of 'Save' steps (should be 1)
    save_count = result.count("'Save'") + result.count("'save'")
    _assert(save_count == 1, f"dedup: Save appears once, got {save_count}")
    _assert("'Cancel'" in result, "Cancel not deduped")


def _test_build_hunt_filters_noise():
    print("\n── build_hunt() noise filtering ──")
    elements = [
        {"type": "button", "identifier": ""},  # empty
        {"type": "button", "identifier": "×"},  # close symbol
        {"type": "link", "identifier": "https://cdn.example.com"},  # URL
        {"type": "button", "identifier": "Real Button"},
    ]
    result = build_hunt("https://example.com", elements)

    _assert("'Real Button'" in result, "real button kept")
    # Count STEP lines that are not STEP 1 (NAV) or STEP 2 (WAIT)
    step_lines = [
        l
        for l in result.split("\n")
        if l.startswith("STEP ") and not l.startswith("STEP 1:") and not l.startswith("STEP 2:")
    ]
    _assert(len(step_lines) == 1, f"only 1 action STEP after filtering noise, got {len(step_lines)}")


def _test_build_hunt_step_numbering():
    print("\n── build_hunt() step numbering ──")
    elements = [
        {"type": "button", "identifier": "Alpha"},
        {"type": "input", "identifier": "Beta"},
        {"type": "link", "identifier": "Gamma"},
    ]
    result = build_hunt("https://example.com", elements)

    # Steps should be: STEP 1: NAV, STEP 2: WAIT, STEP 3: Alpha, STEP 4: Beta, STEP 5: Gamma, DONE.
    _assert("STEP 1:" in result and "NAVIGATE" in result, "STEP 1 is NAVIGATE")
    _assert("STEP 2:" in result and "WAIT" in result, "STEP 2 is WAIT")
    _assert("STEP 3:" in result and "Click" in result, "STEP 3 is first action")
    _assert(result.rstrip().endswith("DONE."), "file ends with flush-left DONE.")


# ── Part 4: SCAN_JS browser integration ──────────────────────────────────────

SCAN_DOM = """
<!DOCTYPE html><html><head><title>Scan Lab</title></head><body>
<form>
  <input type="text" placeholder="Search" aria-label="Search">
  <select aria-label="Category"><option>Books</option><option>Music</option></select>
  <label><input type="checkbox" aria-label="Remember Me"> Remember Me</label>
  <label><input type="radio" name="ship" checked> Express</label>
  <label><input type="radio" name="ship"> Standard</label>
  <button type="submit">Go</button>
  <a href="/help">Help Center</a>
</form>
<!-- hidden element — should be skipped -->
<button style="display:none;">Hidden Action</button>
</body></html>
"""


async def _test_scan_js_integration():
    """Run SCAN_JS on real DOM and verify element discovery."""
    print("\n── SCAN_JS browser integration ──")
    import json
    from manul_engine.js_scripts import SCAN_JS

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(SCAN_DOM)

        raw = await page.evaluate(SCAN_JS)
        elements = json.loads(raw)
        await browser.close()

    types_found = {e["type"] for e in elements}
    ids_found = {e["identifier"] for e in elements}

    _assert(len(elements) >= 4, f"found ≥ 4 elements, got {len(elements)}")
    _assert("input" in types_found, "input type discovered")
    _assert("select" in types_found or "Category" in ids_found, "select/Category discovered")
    _assert("checkbox" in types_found, "checkbox type discovered")
    _assert("radio" in types_found, "radio type discovered")
    # "Go" is in the skip list, so the submit button may be filtered later by build_hunt
    _assert("link" in types_found, "link type discovered")
    _assert("Hidden Action" not in ids_found, "hidden button excluded")


async def run_suite():
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print(f"\n{'=' * 70}")
    print("🔍  SCANNER LAB — Smart Page Scanner Unit Tests")
    print(f"{'=' * 70}")

    # ── Part 1: Pure-Python unit tests ────────────────────────────────
    print(f"\n{'─' * 70}")
    print("📐 Part 1: _is_useful() filter")
    print(f"{'─' * 70}")
    _test_is_useful()

    print(f"\n{'─' * 70}")
    print("📐 Part 2: _map_to_step() type mapping")
    print(f"{'─' * 70}")
    _test_map_to_step()

    print(f"\n{'─' * 70}")
    print("📐 Part 3: build_hunt() assembly")
    print(f"{'─' * 70}")
    _test_build_hunt_basic()
    _test_build_hunt_dedup()
    _test_build_hunt_filters_noise()
    _test_build_hunt_step_numbering()

    # ── Part 2: Browser integration ───────────────────────────────────
    print(f"\n{'─' * 70}")
    print("🌐 Part 4: SCAN_JS browser integration")
    print(f"{'─' * 70}")
    await _test_scan_js_integration()

    total = _PASS + _FAIL
    print(f"\n{'=' * 70}")
    print(f"📊 SCORE: {_PASS}/{total} passed")
    if _FAIL:
        print(f"\n🙀 {_FAIL} failure(s)")
    if _PASS == total:
        print("\n🏆 SCANNER UNIT TESTS FLAWLESS!")
    print(f"{'=' * 70}")

    return _PASS == total


if __name__ == "__main__":
    asyncio.run(run_suite())
