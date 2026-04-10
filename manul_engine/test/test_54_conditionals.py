# manul_engine/test/test_54_conditionals.py
"""
Unit-test suite for IF/ELIF/ELSE conditional blocks in Hunt DSL.

Tests:
  Section 1: classify_step() detects if/elif/else keywords
  Section 2: parse_hunt_blocks() produces IfBlock AST nodes
  Section 3: ConditionalSyntaxError on invalid syntax
  Section 4: Nested conditionals
  Section 5: Condition pattern matching (regex validation)
  Section 6: Variable condition evaluation (synchronous tests)
  Section 7: Integration — full block parsing with mixed actions

No network, no live browser, no Ollama required.
All tests run against in-memory parsed Hunt DSL — no Playwright.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python run_tests.py``) and must remain async.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.helpers import (
    IfBlock,
    classify_step,
    parse_hunt_blocks,
)
from manul_engine.exceptions import ConditionalSyntaxError
from manul_engine.conditionals import (
    _RE_ELEMENT_EXISTS,
    _RE_TEXT_PRESENT,
    _RE_VAR_COMPARE,
    _RE_VAR_CONTAINS,
    _RE_VAR_TRUTHY,
)

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


# ── Section 1: classify_step — if/elif/else detection ─────────────────────────


def test_classify_step():
    print("\n── Section 1: classify_step — if/elif/else detection ──")

    _assert(classify_step("if button 'Save' exists:") == "if_block", "if lowercase with element exists condition")

    _assert(classify_step("IF text 'Welcome' is present:") == "if_block", "IF uppercase with text present condition")

    _assert(
        classify_step("elif button 'Confirm' exists:") == "elif_block", "elif lowercase with element exists condition"
    )

    _assert(classify_step("ELIF {status} == 'active':") == "elif_block", "ELIF uppercase with variable comparison")

    _assert(classify_step("else:") == "else_block", "else: lowercase")

    _assert(classify_step("ELSE:") == "else_block", "ELSE: uppercase")

    _assert(classify_step("  else:") == "else_block", "else: with leading whitespace")

    # These should NOT match as conditionals
    _assert(classify_step("Click the 'if exists' button") == "action", "'if exists' inside quotes is an action")

    _assert(classify_step("VERIFY that 'else' is present") == "verify", "'else' inside a VERIFY is still verify")

    _assert(classify_step("if button 'Save' exists") != "if_block", "if without trailing colon is NOT if_block")

    _assert(classify_step("else") != "else_block", "else without colon is NOT else_block")


# ── Section 2: parse_hunt_blocks — IfBlock AST nodes ─────────────────────────


def test_parse_if_block():
    print("\n── Section 2: parse_hunt_blocks — IfBlock AST ──")

    # Simple if/else — indentation marks body lines
    task = """STEP 1: Conditional click
    IF button 'Save' exists:
        Click the 'Save' button
    ELSE:
        Click the 'Cancel' button
    DONE."""

    blocks = parse_hunt_blocks(task)
    _assert(len(blocks) == 1, "Single STEP block", f"got {len(blocks)}")

    actions = blocks[0].actions
    # Should be: [IfBlock, "DONE."]
    _assert(len(actions) == 2, "Two actions (IfBlock + DONE)", f"got {len(actions)}")
    _assert(isinstance(actions[0], IfBlock), "First action is IfBlock")

    if isinstance(actions[0], IfBlock):
        if_block = actions[0]
        _assert(len(if_block.branches) == 2, "Two branches (if + else)", f"got {len(if_block.branches)}")
        _assert(if_block.branches[0].kind == "if", "First branch is 'if'")
        _assert(
            if_block.branches[0].condition == "button 'Save' exists",
            "If condition text",
            f"got {if_block.branches[0].condition!r}",
        )
        _assert(len(if_block.branches[0].actions) == 1, "If branch has one action")
        _assert(if_block.branches[1].kind == "else", "Second branch is 'else'")
        _assert(if_block.branches[1].condition == "", "Else has no condition")
        _assert(len(if_block.branches[1].actions) == 1, "Else branch has one action")


def test_parse_if_elif_else():
    print("\n── Section 2b: parse_hunt_blocks — if/elif/else ──")

    task = """STEP 1: Multi-branch
    IF button 'Save' exists:
        Click the 'Save' button
    ELIF button 'Confirm' exists:
        Click the 'Confirm' button
    ELIF button 'OK' exists:
        Click the 'OK' button
    ELSE:
        Click the 'Cancel' button
    DONE."""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(isinstance(actions[0], IfBlock), "First action is IfBlock")

    if isinstance(actions[0], IfBlock):
        if_block = actions[0]
        _assert(len(if_block.branches) == 4, "Four branches (if + 2 elif + else)", f"got {len(if_block.branches)}")
        _assert(if_block.branches[0].kind == "if", "Branch 0 is 'if'")
        _assert(if_block.branches[1].kind == "elif", "Branch 1 is 'elif'")
        _assert(if_block.branches[2].kind == "elif", "Branch 2 is 'elif'")
        _assert(if_block.branches[3].kind == "else", "Branch 3 is 'else'")
        _assert(
            if_block.branches[1].condition == "button 'Confirm' exists",
            "Elif 1 condition",
            f"got {if_block.branches[1].condition!r}",
        )


def test_parse_if_only():
    print("\n── Section 2c: parse_hunt_blocks — if only (no else) ──")

    task = """STEP 1: Optional action
    IF button 'Close Ad' exists:
        Click the 'Close Ad' button
    VERIFY that 'Welcome' is present
    DONE."""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(isinstance(actions[0], IfBlock), "First action is IfBlock")
    _assert(isinstance(actions[1], str), "Second action is string (VERIFY)")
    _assert(isinstance(actions[2], str), "Third action is string (DONE)")

    if isinstance(actions[0], IfBlock):
        _assert(len(actions[0].branches) == 1, "One branch (if only)")


def test_parse_multi_action_branch():
    print("\n── Section 2d: parse_hunt_blocks — multiple actions in branch ──")

    task = """STEP 1: Complex
    IF text 'Login' is present:
        Fill 'Username' field with 'admin'
        Fill 'Password' field with 'secret'
        Click the 'Login' button
    ELSE:
        Click the 'Logout' button
    DONE."""

    blocks = parse_hunt_blocks(task)
    if_block = blocks[0].actions[0]
    _assert(isinstance(if_block, IfBlock), "First action is IfBlock")

    if isinstance(if_block, IfBlock):
        _assert(
            len(if_block.branches[0].actions) == 3,
            "If branch has 3 actions",
            f"got {len(if_block.branches[0].actions)}",
        )
        _assert(len(if_block.branches[1].actions) == 1, "Else branch has 1 action")


# ── Section 3: ConditionalSyntaxError ────────────────────────────────────────


def test_syntax_errors():
    print("\n── Section 3: ConditionalSyntaxError ──")

    # elif without if
    try:
        parse_hunt_blocks("STEP 1: Bad\n    ELIF button 'X' exists:\n        Click 'X' button")
        _assert(False, "ELIF without IF should raise")
    except ConditionalSyntaxError as e:
        _assert("elif" in str(e).lower() and "without" in str(e).lower(), "ELIF without IF error message", str(e))

    # else without if
    try:
        parse_hunt_blocks("STEP 1: Bad\n    ELSE:\n        Click 'X' button")
        _assert(False, "ELSE without IF should raise")
    except ConditionalSyntaxError as e:
        _assert("else" in str(e).lower() and "without" in str(e).lower(), "ELSE without IF error message", str(e))

    # Multiple else blocks
    try:
        parse_hunt_blocks(
            "STEP 1: Bad\n    IF button 'A' exists:\n        Click 'A'\n"
            "    ELSE:\n        Click 'B'\n    ELSE:\n        Click 'C'"
        )
        _assert(False, "Multiple ELSE should raise")
    except ConditionalSyntaxError as e:
        _assert("multiple" in str(e).lower() or "else" in str(e).lower(), "Multiple ELSE error message", str(e))

    # elif after else
    try:
        parse_hunt_blocks(
            "STEP 1: Bad\n    IF button 'A' exists:\n        Click 'A'\n"
            "    ELSE:\n        Click 'B'\n    ELIF button 'C' exists:\n        Click 'C'"
        )
        _assert(False, "ELIF after ELSE should raise")
    except ConditionalSyntaxError as e:
        _assert("elif" in str(e).lower() and "after" in str(e).lower(), "ELIF after ELSE error message", str(e))


# ── Section 4: Nested conditionals ──────────────────────────────────────────


def test_nested_conditionals():
    print("\n── Section 4: Nested conditionals ──")

    task = """STEP 1: Nested
    IF text 'Login' is present:
        IF button 'SSO Login' exists:
            Click the 'SSO Login' button
        ELSE:
            Fill 'Username' field with 'admin'
            Click the 'Login' button
    ELSE:
        Click the 'Dashboard' link
    DONE."""

    blocks = parse_hunt_blocks(task)
    outer = blocks[0].actions[0]
    _assert(isinstance(outer, IfBlock), "Outer is IfBlock")

    if isinstance(outer, IfBlock):
        _assert(len(outer.branches) == 2, "Outer has 2 branches")
        inner_actions = outer.branches[0].actions
        _assert(len(inner_actions) >= 1, "If branch has actions")
        # The first action of the if branch should be a nested IfBlock
        _assert(isinstance(inner_actions[0], IfBlock), "Nested IfBlock found", f"got type {type(inner_actions[0])}")


# ── Section 5: Condition pattern matching ────────────────────────────────────


def test_condition_patterns():
    print("\n── Section 5: Condition pattern matching ──")

    # Element exists
    m = _RE_ELEMENT_EXISTS.match("button 'Save' exists")
    _assert(m is not None, "button 'Save' exists matches")
    if m:
        _assert(m.group("target") == "Save", "target is 'Save'")
        _assert(m.group("neg") is None, "not negated")

    m = _RE_ELEMENT_EXISTS.match("element 'Error' not exists")
    _assert(m is not None, "element 'Error' not exists matches")
    if m:
        _assert(m.group("neg") is not None, "is negated")

    m = _RE_ELEMENT_EXISTS.match("link 'Home' exists")
    _assert(m is not None, "link 'Home' exists matches")

    m = _RE_ELEMENT_EXISTS.match("checkbox 'Terms' exists")
    _assert(m is not None, "checkbox 'Terms' exists matches")

    # Text present
    m = _RE_TEXT_PRESENT.match("text 'Welcome' is present")
    _assert(m is not None, "text 'Welcome' is present matches")
    if m:
        _assert(m.group("target") == "Welcome", "target is 'Welcome'")
        _assert(m.group("neg") is None, "not negated")

    m = _RE_TEXT_PRESENT.match("text 'Error' is not present")
    _assert(m is not None, "text 'Error' is not present matches")
    if m:
        _assert(m.group("neg") is not None, "is negated")

    # Variable comparison
    m = _RE_VAR_COMPARE.match("{status} == 'active'")
    _assert(m is not None, "{status} == 'active' matches")
    if m:
        _assert(m.group("var") == "status", "var is 'status'")
        _assert(m.group("op") == "==", "op is '=='")
        _assert(m.group("value") == "active", "value is 'active'")

    m = _RE_VAR_COMPARE.match("role != 'admin'")
    _assert(m is not None, "role != 'admin' matches (bare key)")
    if m:
        _assert(m.group("op") == "!=", "op is '!='")

    # Variable contains
    m = _RE_VAR_CONTAINS.match("{message} contains 'success'")
    _assert(m is not None, "{message} contains 'success' matches")
    if m:
        _assert(m.group("var") == "message", "var is 'message'")
        _assert(m.group("value") == "success", "value is 'success'")

    # Variable truthy
    m = _RE_VAR_TRUTHY.match("{logged_in}")
    _assert(m is not None, "{logged_in} matches truthy")
    if m:
        _assert(m.group("var") == "logged_in", "var is 'logged_in'")

    m = _RE_VAR_TRUTHY.match("token")
    _assert(m is not None, "token matches truthy (bare key)")


# ── Section 6: Variable condition evaluation (sync) ──────────────────────────


async def test_variable_conditions_async():
    """Test variable-based conditions without a browser."""
    print("\n── Section 6: Variable condition evaluation ──")

    from manul_engine.variables import ScopedVariables
    from manul_engine.conditionals import evaluate_condition

    mem = ScopedVariables()
    mem["status"] = "active"
    mem["role"] = "admin"
    mem["message"] = "Operation successful"
    mem["empty_var"] = ""
    mem["falsy_var"] = "false"
    mem["truthy_var"] = "yes"

    # We need a mock page for element/text conditions — skip those here.
    # Only test variable conditions which don't need a page.

    # == comparison
    result = await evaluate_condition("{status} == 'active'", None, mem)
    _assert(result is True, "status == 'active' → True")

    result = await evaluate_condition("{status} == 'inactive'", None, mem)
    _assert(result is False, "status == 'inactive' → False")

    # != comparison
    result = await evaluate_condition("{role} != 'user'", None, mem)
    _assert(result is True, "role != 'user' → True")

    result = await evaluate_condition("{role} != 'admin'", None, mem)
    _assert(result is False, "role != 'admin' → False")

    # contains
    result = await evaluate_condition("{message} contains 'successful'", None, mem)
    _assert(result is True, "message contains 'successful' → True")

    result = await evaluate_condition("{message} contains 'error'", None, mem)
    _assert(result is False, "message contains 'error' → False")

    # truthy
    result = await evaluate_condition("{truthy_var}", None, mem)
    _assert(result is True, "truthy_var → True")

    result = await evaluate_condition("{empty_var}", None, mem)
    _assert(result is False, "empty_var → False")

    result = await evaluate_condition("{falsy_var}", None, mem)
    _assert(result is False, "falsy_var ('false') → False")

    result = await evaluate_condition("{nonexistent_var}", None, mem)
    _assert(result is False, "nonexistent_var → False")

    # Invalid/unrecognized syntax
    try:
        await evaluate_condition("banana smoothie", None, mem)
        _assert(False, "Invalid syntax should raise ValueError")
    except ValueError:
        _assert(True, "Invalid syntax raises ValueError")

    # Page-dependent conditions with page=None must raise ValueError
    try:
        await evaluate_condition("button 'Save' exists", None, mem)
        _assert(False, "Element-exists with page=None should raise ValueError")
    except ValueError as exc:
        _assert("requires an active page" in str(exc), "Element-exists None page guard")

    try:
        await evaluate_condition("text 'Hello' is present", None, mem)
        _assert(False, "Text-present with page=None should raise ValueError")
    except ValueError as exc:
        _assert("requires an active page" in str(exc), "Text-present None page guard")


# ── Section 7: Integration — mixed actions and conditionals ──────────────────


def test_mixed_actions():
    print("\n── Section 7: Integration — mixed actions ──")

    task = """STEP 1: Navigate and adapt
    NAVIGATE to 'https://example.com'
    VERIFY that 'Welcome' is present
    IF button 'Cookie Banner' exists:
        Click the 'Accept Cookies' button
        VERIFY that 'Cookie Banner' is NOT present
    Fill 'Search' field with 'test'
    PRESS ENTER
    IF text 'No results' is present:
        VERIFY that 'No results' is present
    ELIF text 'Results' is present:
        Click the 'First Result' link
    DONE."""

    blocks = parse_hunt_blocks(task)
    _assert(len(blocks) == 1, "Single block")

    actions = blocks[0].actions
    _assert(isinstance(actions[0], str), "NAVIGATE is string")
    _assert(isinstance(actions[1], str), "VERIFY is string")
    _assert(isinstance(actions[2], IfBlock), "Cookie banner check is IfBlock")
    _assert(isinstance(actions[3], str), "Fill is string")
    _assert(isinstance(actions[4], str), "PRESS is string")
    _assert(isinstance(actions[5], IfBlock), "Results check is IfBlock")
    _assert(isinstance(actions[6], str), "DONE is string")

    # Check first conditional
    if isinstance(actions[2], IfBlock):
        _assert(len(actions[2].branches) == 1, "Cookie banner has 1 branch (if only)")
        _assert(len(actions[2].branches[0].actions) == 2, "Cookie if branch has 2 actions")

    # Check second conditional
    if isinstance(actions[5], IfBlock):
        _assert(len(actions[5].branches) == 2, "Results check has 2 branches (if + elif)")
        _assert(actions[5].branches[0].kind == "if", "First is 'if'")
        _assert(actions[5].branches[1].kind == "elif", "Second is 'elif'")


def test_conditional_with_variables():
    print("\n── Section 7b: Conditionals with variable conditions ──")

    task = """STEP 1: Variable-based branching
    EXTRACT the 'User Role' into {role}
    IF {role} == 'admin':
        Click the 'Admin Panel' link
    ELIF {role} == 'user':
        Click the 'Dashboard' link
    ELSE:
        Click the 'Login' link
    DONE."""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(isinstance(actions[0], str), "EXTRACT is string")
    _assert(isinstance(actions[1], IfBlock), "Role check is IfBlock")

    if isinstance(actions[1], IfBlock):
        _assert(len(actions[1].branches) == 3, "Three branches (if + elif + else)")
        _assert(
            actions[1].branches[0].condition == "{role} == 'admin'",
            "If condition",
            f"got {actions[1].branches[0].condition!r}",
        )
        _assert(
            actions[1].branches[1].condition == "{role} == 'user'",
            "Elif condition",
            f"got {actions[1].branches[1].condition!r}",
        )
        _assert(actions[1].branches[2].condition == "", "Else has empty condition")


# ── Section 8: Playwright-backed element/text condition tests ────────────────

_CONDITIONAL_DOM = """<!DOCTYPE html>
<html><body>
<h1>Welcome Page</h1>
<button id="save-btn">Save</button>
<a href="#">Home</a>
<input placeholder="Search here" aria-label="Search Input">
<span style="display:none">Hidden Text</span>
<p>This page has some visible content for testing.</p>
</body></html>"""


async def test_element_exists_browser():
    """Test _element_exists and _text_present with a real Playwright page."""
    print("\n── Section 8: Playwright-backed element/text conditions ──")

    from playwright.async_api import async_playwright
    from manul_engine.conditionals import _element_exists, _text_present, evaluate_condition
    from manul_engine.variables import ScopedVariables

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(_CONDITIONAL_DOM)

        # ── _element_exists ──

        # Button by text
        found = await _element_exists(page, "Save")
        _assert(found is True, "element_exists: 'Save' button found")

        # Link by text
        found = await _element_exists(page, "Home")
        _assert(found is True, "element_exists: 'Home' link found")

        # By placeholder
        found = await _element_exists(page, "Search here")
        _assert(found is True, "element_exists: 'Search here' placeholder found")

        # By aria-label
        found = await _element_exists(page, "Search Input")
        _assert(found is True, "element_exists: 'Search Input' label found")

        # Non-existent element
        found = await _element_exists(page, "Delete Everything")
        _assert(found is False, "element_exists: non-existent returns False")

        # Hidden element text — button/link strategies won't match hidden spans
        found = await _element_exists(page, "Hidden Text")
        _assert(found is False, "element_exists: hidden element returns False")

        # ── _text_present ──

        # Visible heading text
        found = await _text_present(page, "Welcome Page")
        _assert(found is True, "text_present: 'Welcome Page' found")

        # Visible paragraph text (substring)
        found = await _text_present(page, "visible content")
        _assert(found is True, "text_present: 'visible content' substring found")

        # Case-insensitive
        found = await _text_present(page, "welcome page")
        _assert(found is True, "text_present: case-insensitive match")

        # Non-existent text
        found = await _text_present(page, "This text does not exist anywhere")
        _assert(found is False, "text_present: non-existent returns False")

        # ── evaluate_condition with real page ──

        mem = ScopedVariables()

        result = await evaluate_condition("button 'Save' exists", page, mem)
        _assert(result is True, "evaluate: button 'Save' exists → True")

        result = await evaluate_condition("button 'Delete' not exists", page, mem)
        _assert(result is True, "evaluate: button 'Delete' not exists → True")

        result = await evaluate_condition("button 'Save' not exists", page, mem)
        _assert(result is False, "evaluate: button 'Save' not exists → False")

        result = await evaluate_condition("link 'Home' exists", page, mem)
        _assert(result is True, "evaluate: link 'Home' exists → True")

        result = await evaluate_condition("text 'Welcome Page' is present", page, mem)
        _assert(result is True, "evaluate: text 'Welcome Page' is present → True")

        result = await evaluate_condition("text 'Nonexistent' is present", page, mem)
        _assert(result is False, "evaluate: text 'Nonexistent' is present → False")

        result = await evaluate_condition("text 'Welcome Page' is not present", page, mem)
        _assert(result is False, "evaluate: text 'Welcome Page' is not present → False")

        result = await evaluate_condition("text 'Nonexistent' is not present", page, mem)
        _assert(result is True, "evaluate: text 'Nonexistent' is not present → True")

        await browser.close()


# ── Entry point ──────────────────────────────────────────────────────────────


async def run_suite() -> tuple[int, int]:
    """Execute all conditional block tests. Returns (pass_count, fail_count)."""
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    test_classify_step()
    test_parse_if_block()
    test_parse_if_elif_else()
    test_parse_if_only()
    test_parse_multi_action_branch()
    test_syntax_errors()
    test_nested_conditionals()
    test_condition_patterns()
    await test_variable_conditions_async()
    test_mixed_actions()
    test_conditional_with_variables()
    await test_element_exists_browser()

    total = _PASS + _FAIL
    print(f"\n  Conditionals suite: {_PASS} passed, {_FAIL} failed")
    print(f"SCORE: {_PASS}/{total}")
    return _PASS, _FAIL


if __name__ == "__main__":
    import asyncio

    p, f = asyncio.run(run_suite())
    raise SystemExit(0 if f == 0 else 1)
