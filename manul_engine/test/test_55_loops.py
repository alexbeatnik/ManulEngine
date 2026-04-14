# manul_engine/test/test_55_loops.py
"""
Unit-test suite for REPEAT / FOR EACH / WHILE loop blocks in Hunt DSL.

Tests:
  Section 1: classify_step() detects loop keywords
  Section 2: parse_hunt_blocks() produces LoopBlock AST nodes
  Section 3: Syntax errors — malformed loop headers, empty bodies, invalid inputs
  Section 4: Nested loops & conditionals
  Section 5: LoopBlock field validation
  Section 6: collect_loopblock_lines() utility
  Section 7: Integration — loops with mixed actions, DONE, IF blocks
  Section 8: Edge cases — zero iterations, large counts, missing vars

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
    LoopBlock,
    classify_step,
    collect_loopblock_lines,
    collect_ifblock_lines,
    parse_hunt_blocks,
    MAX_LOOP_ITERATIONS,
)
from manul_engine.exceptions import ConditionalSyntaxError

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


# ── Section 1: classify_step — loop keyword detection ─────────────────────────


def test_classify_step_loops():
    print("\n── Section 1: classify_step — loop keyword detection ──")

    # REPEAT
    _assert(classify_step("REPEAT 3 TIMES:") == "repeat_loop", "REPEAT 3 TIMES: uppercase")
    _assert(classify_step("repeat 10 times:") == "repeat_loop", "repeat 10 times: lowercase")
    _assert(classify_step("Repeat 1 Times:") == "repeat_loop", "Repeat 1 Times: mixed case")
    _assert(classify_step("REPEAT 100 TIMES:") == "repeat_loop", "REPEAT 100 TIMES: large count")

    # FOR EACH
    _assert(classify_step("FOR EACH {item} IN {items}:") == "for_each_loop", "FOR EACH with braces")
    _assert(classify_step("for each {x} in {list}:") == "for_each_loop", "for each lowercase")
    _assert(classify_step("FOR EACH item IN items:") == "for_each_loop", "FOR EACH without braces")
    _assert(classify_step("For Each {color} In {palette}:") == "for_each_loop", "For Each mixed case")

    # WHILE
    _assert(classify_step("WHILE text 'Loading' is present:") == "while_loop", "WHILE with text present")
    _assert(classify_step("while button 'Next' exists:") == "while_loop", "while lowercase")
    _assert(classify_step("WHILE {counter} != '0':") == "while_loop", "WHILE with variable comparison")
    _assert(classify_step("While {running}:") == "while_loop", "While with truthy var")

    # NOT loops — should NOT match
    _assert(classify_step("Click the 'Repeat' button") != "repeat_loop", "Repeat in quotes is not a loop")
    _assert(classify_step("VERIFY that 'while' is present") != "while_loop", "while in VERIFY is not a loop")
    _assert(classify_step("REPEAT 3 TIMES") != "repeat_loop", "REPEAT without colon is not a loop")
    _assert(classify_step("FOR EACH") != "for_each_loop", "Incomplete FOR EACH is not a loop")


# ── Section 2: parse_hunt_blocks — LoopBlock AST nodes ───────────────────────


def test_parse_repeat():
    print("\n── Section 2a: parse_hunt_blocks — REPEAT ──")

    task = """STEP 1: Repeat navigation
    REPEAT 3 TIMES:
        Click the 'Next' button
        VERIFY that 'Page' is present"""

    blocks = parse_hunt_blocks(task)
    _assert(len(blocks) == 1, "Single STEP block", f"got {len(blocks)}")

    actions = blocks[0].actions
    _assert(len(actions) == 1, "One action (LoopBlock)", f"got {len(actions)}")
    _assert(isinstance(actions[0], LoopBlock), "First action is LoopBlock")

    if isinstance(actions[0], LoopBlock):
        lb = actions[0]
        _assert(lb.kind == "repeat", "kind is 'repeat'", f"got {lb.kind!r}")
        _assert(lb.count == 3, "count is 3", f"got {lb.count}")
        _assert(len(lb.actions) == 2, "Two body actions", f"got {len(lb.actions)}")
        _assert(lb.actions[0] == "Click the 'Next' button", "First body action", f"got {lb.actions[0]!r}")
        _assert(lb.actions[1] == "VERIFY that 'Page' is present", "Second body action", f"got {lb.actions[1]!r}")


def test_parse_for_each():
    print("\n── Section 2b: parse_hunt_blocks — FOR EACH ──")

    task = """STEP 1: Color loop
    FOR EACH {color} IN {colors}:
        Click the '{color}' button
        VERIFY that '{color}' is present"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "Is LoopBlock")

    if isinstance(lb, LoopBlock):
        _assert(lb.kind == "for_each", "kind is 'for_each'", f"got {lb.kind!r}")
        _assert(lb.var_name == "color", "var_name is 'color'", f"got {lb.var_name!r}")
        _assert(lb.collection_expr == "colors", "collection_expr is 'colors'", f"got {lb.collection_expr!r}")
        _assert(len(lb.actions) == 2, "Two body actions", f"got {len(lb.actions)}")


def test_parse_for_each_bare_keys():
    print("\n── Section 2c: parse_hunt_blocks — FOR EACH bare keys ──")

    task = """STEP 1: Bare keys
    FOR EACH item IN items:
        Click the '{item}' element"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "Is LoopBlock")

    if isinstance(lb, LoopBlock):
        _assert(lb.var_name == "item", "var_name from bare key", f"got {lb.var_name!r}")
        _assert(lb.collection_expr == "items", "collection_expr from bare key", f"got {lb.collection_expr!r}")


def test_parse_while():
    print("\n── Section 2d: parse_hunt_blocks — WHILE ──")

    task = """STEP 1: Pagination
    WHILE button 'Next' exists:
        Click the 'Next' button
        WAIT 1"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "Is LoopBlock")

    if isinstance(lb, LoopBlock):
        _assert(lb.kind == "while", "kind is 'while'", f"got {lb.kind!r}")
        _assert(lb.condition_text == "button 'Next' exists", "condition_text", f"got {lb.condition_text!r}")
        _assert(lb.count is None, "count is None for while", f"got {lb.count}")
        _assert(len(lb.actions) == 2, "Two body actions", f"got {len(lb.actions)}")


def test_parse_while_variable_condition():
    print("\n── Section 2e: parse_hunt_blocks — WHILE variable condition ──")

    task = """STEP 1: Counter loop
    WHILE {counter} != '0':
        Click the 'Decrement' button"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "Is LoopBlock")

    if isinstance(lb, LoopBlock):
        _assert(
            lb.condition_text == "{counter} != '0'", "condition preserves variable syntax", f"got {lb.condition_text!r}"
        )


# ── Section 3: Syntax errors ────────────────────────────────────────────────


def test_syntax_errors():
    print("\n── Section 3: Loop syntax errors ──")

    # Empty repeat body — REPEAT with no indented lines
    try:
        parse_hunt_blocks("STEP 1: Bad\n    REPEAT 3 TIMES:\n    VERIFY that 'X' is present")
        _assert(False, "Empty REPEAT body should raise")
    except (ConditionalSyntaxError, ValueError) as e:
        _assert(True, "Empty REPEAT body raises", str(e))

    # Empty while body
    try:
        parse_hunt_blocks("STEP 1: Bad\n    WHILE text 'X' is present:\n    Click the 'Y' button")
        _assert(False, "Empty WHILE body should raise")
    except (ConditionalSyntaxError, ValueError) as e:
        _assert(True, "Empty WHILE body raises", str(e))

    # Empty for each body
    try:
        parse_hunt_blocks("STEP 1: Bad\n    FOR EACH {x} IN {y}:\n    DONE.")
        _assert(False, "Empty FOR EACH body should raise")
    except (ConditionalSyntaxError, ValueError) as e:
        _assert(True, "Empty FOR EACH body raises", str(e))

    # REPEAT 0 — must require positive integer
    try:
        parse_hunt_blocks("STEP 1: Bad\n    REPEAT 0 TIMES:\n        CLICK the 'X' button")
        _assert(False, "REPEAT 0 should raise")
    except (ConditionalSyntaxError, ValueError) as e:
        _assert(
            "positive integer" in str(e).lower() or ">= 1" in str(e), "REPEAT 0 error mentions positive integer", str(e)
        )

    # FOR EACH {i} — reserved variable name
    try:
        parse_hunt_blocks("STEP 1: Bad\n    FOR EACH {i} IN {items}:\n        CLICK the 'X' button")
        _assert(False, "FOR EACH {i} should raise")
    except (ConditionalSyntaxError, ValueError) as e:
        _assert("reserved" in str(e).lower(), "FOR EACH {i} error mentions reserved", str(e))


# ── Section 4: Nested loops & conditionals ───────────────────────────────────


def test_nested_loop_in_if():
    print("\n── Section 4a: Nested loop inside IF ──")

    task = """STEP 1: Conditional loop
    IF button 'Load More' exists:
        REPEAT 5 TIMES:
            Click the 'Load More' button
            WAIT 1
    ELSE:
        VERIFY that 'All items loaded' is present"""

    blocks = parse_hunt_blocks(task)
    outer = blocks[0].actions[0]
    _assert(isinstance(outer, IfBlock), "Outer is IfBlock")

    if isinstance(outer, IfBlock):
        if_branch = outer.branches[0]
        _assert(len(if_branch.actions) == 1, "If branch has one action (loop)", f"got {len(if_branch.actions)}")
        inner = if_branch.actions[0]
        _assert(isinstance(inner, LoopBlock), "Inner is LoopBlock")
        if isinstance(inner, LoopBlock):
            _assert(inner.kind == "repeat", "Inner loop kind", f"got {inner.kind!r}")
            _assert(inner.count == 5, "Inner loop count", f"got {inner.count}")
            _assert(len(inner.actions) == 2, "Inner loop has 2 body actions", f"got {len(inner.actions)}")


def test_nested_if_in_loop():
    print("\n── Section 4b: Nested IF inside loop ──")

    task = """STEP 1: Loop with conditional
    REPEAT 3 TIMES:
        IF text 'Error' is present:
            Click the 'Retry' button
        ELSE:
            Click the 'Next' button"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "Outer is LoopBlock")

    if isinstance(lb, LoopBlock):
        _assert(lb.kind == "repeat", "kind is repeat")
        _assert(len(lb.actions) == 1, "One action (IfBlock)", f"got {len(lb.actions)}")
        inner = lb.actions[0]
        _assert(isinstance(inner, IfBlock), "Inner is IfBlock")
        if isinstance(inner, IfBlock):
            _assert(len(inner.branches) == 2, "Two branches (if + else)", f"got {len(inner.branches)}")


def test_nested_loop_in_loop():
    print("\n── Section 4c: Nested loop inside loop ──")

    task = """STEP 1: Double loop
    REPEAT 3 TIMES:
        REPEAT 2 TIMES:
            Click the 'Item' button"""

    blocks = parse_hunt_blocks(task)
    outer_lb = blocks[0].actions[0]
    _assert(isinstance(outer_lb, LoopBlock), "Outer is LoopBlock")

    if isinstance(outer_lb, LoopBlock):
        _assert(outer_lb.count == 3, "Outer count is 3")
        _assert(len(outer_lb.actions) == 1, "Outer has 1 action (inner loop)")
        inner_lb = outer_lb.actions[0]
        _assert(isinstance(inner_lb, LoopBlock), "Inner is LoopBlock")
        if isinstance(inner_lb, LoopBlock):
            _assert(inner_lb.count == 2, "Inner count is 2")
            _assert(len(inner_lb.actions) == 1, "Inner has 1 action")


def test_nested_for_each_in_while():
    print("\n── Section 4d: FOR EACH inside WHILE ──")

    task = """STEP 1: Complex nesting
    WHILE button 'Continue' exists:
        FOR EACH {item} IN {items}:
            Click the '{item}' element"""

    blocks = parse_hunt_blocks(task)
    while_lb = blocks[0].actions[0]
    _assert(isinstance(while_lb, LoopBlock), "Outer is WHILE LoopBlock")

    if isinstance(while_lb, LoopBlock):
        _assert(while_lb.kind == "while", "Outer kind is while")
        inner = while_lb.actions[0]
        _assert(isinstance(inner, LoopBlock), "Inner is FOR EACH LoopBlock")
        if isinstance(inner, LoopBlock):
            _assert(inner.kind == "for_each", "Inner kind is for_each")
            _assert(inner.var_name == "item", "Inner var_name")


# ── Section 5: LoopBlock field validation ────────────────────────────────────


def test_loopblock_fields():
    print("\n── Section 5: LoopBlock field validation ──")

    # REPEAT fields
    task = """STEP 1: R
    REPEAT 7 TIMES:
        Click 'X' button"""
    lb = parse_hunt_blocks(task)[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "REPEAT LoopBlock created")
    if isinstance(lb, LoopBlock):
        _assert(lb.kind == "repeat", "kind = repeat")
        _assert(lb.count == 7, "count = 7", f"got {lb.count}")
        _assert(lb.var_name is None or lb.var_name == "i", "var_name default", f"got {lb.var_name!r}")
        _assert(lb.collection_expr is None, "collection_expr None for repeat")
        _assert(lb.condition_text is None, "condition_text None for repeat")
        _assert(len(lb.action_lines) == len(lb.actions), "action_lines length matches actions")
        _assert(isinstance(lb.loop_line, int), "loop_line is int", f"got {lb.loop_line}")

    # FOR EACH fields
    task2 = """STEP 1: FE
    FOR EACH {name} IN {names}:
        Fill 'Search' with '{name}'"""
    lb2 = parse_hunt_blocks(task2)[0].actions[0]
    if isinstance(lb2, LoopBlock):
        _assert(lb2.kind == "for_each", "kind = for_each")
        _assert(lb2.var_name == "name", "var_name = name")
        _assert(lb2.collection_expr == "names", "collection_expr = names")
        _assert(lb2.count is None, "count None for for_each")
        _assert(lb2.condition_text is None, "condition_text None for for_each")

    # WHILE fields
    task3 = """STEP 1: W
    WHILE {flag}:
        Click 'X' button"""
    lb3 = parse_hunt_blocks(task3)[0].actions[0]
    if isinstance(lb3, LoopBlock):
        _assert(lb3.kind == "while", "kind = while")
        _assert(lb3.condition_text == "{flag}", "condition_text preserved", f"got {lb3.condition_text!r}")
        _assert(lb3.count is None, "count None for while")
        _assert(lb3.var_name is None, "var_name None for while")


# ── Section 6: collect_loopblock_lines ───────────────────────────────────────


def test_collect_lines():
    print("\n── Section 6: collect_loopblock_lines ──")

    task = """STEP 1: Loop with lines
    REPEAT 2 TIMES:
        Click the 'A' button
        Click the 'B' button"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "Got LoopBlock")

    if isinstance(lb, LoopBlock):
        lines = collect_loopblock_lines(lb)
        _assert(len(lines) == 2, "Two lines collected", f"got {len(lines)}")
        _assert(all(isinstance(n, int) for n in lines), "All line numbers are ints")
        _assert(all(isinstance(n, int) for n in lines), "All line numbers are ints (may include 0)")

    # Nested: loop inside loop
    task2 = """STEP 1: Nested
    REPEAT 2 TIMES:
        REPEAT 3 TIMES:
            Click 'X' button
        Click 'Y' button"""

    blocks2 = parse_hunt_blocks(task2)
    lb2 = blocks2[0].actions[0]
    if isinstance(lb2, LoopBlock):
        lines2 = collect_loopblock_lines(lb2)
        # Inner loop has 1 action + outer has 1 action after inner loop = 2 leaf actions
        _assert(len(lines2) == 2, "Nested lines collected (2 leaf actions)", f"got {len(lines2)}")

    # Loop inside IF — test collect_ifblock_lines handles LoopBlock children
    task3 = """STEP 1: Conditional loop
    IF button 'Go' exists:
        REPEAT 2 TIMES:
            Click 'Go' button"""

    blocks3 = parse_hunt_blocks(task3)
    ib = blocks3[0].actions[0]
    if isinstance(ib, IfBlock):
        lines3 = collect_ifblock_lines(ib)
        _assert(len(lines3) == 1, "collect_ifblock_lines traverses LoopBlock", f"got {len(lines3)}")


# ── Section 7: Integration — loops with mixed actions ────────────────────────


def test_loop_with_done():
    print("\n── Section 7a: Loop followed by DONE ──")

    task = """STEP 1: Loop then done
    REPEAT 2 TIMES:
        Click the 'Next' button
    DONE."""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(len(actions) == 2, "Two actions (loop + DONE)", f"got {len(actions)}")
    _assert(isinstance(actions[0], LoopBlock), "First is LoopBlock")
    _assert(isinstance(actions[1], str) and "DONE" in actions[1].upper(), "Second is DONE")


def test_loop_with_preceding_actions():
    print("\n── Section 7b: Actions before and after loop ──")

    task = """STEP 1: Mixed
    NAVIGATE to https://example.com
    REPEAT 3 TIMES:
        Click the 'Load' button
    VERIFY that 'Complete' is present
    DONE."""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(len(actions) == 4, "Four actions (nav + loop + verify + done)", f"got {len(actions)}")
    _assert(isinstance(actions[0], str), "First is string (navigate)")
    _assert(isinstance(actions[1], LoopBlock), "Second is LoopBlock")
    _assert(isinstance(actions[2], str), "Third is string (verify)")
    _assert(isinstance(actions[3], str), "Fourth is string (done)")


def test_multiple_loops_in_step():
    print("\n── Section 7c: Multiple loops in one STEP ──")

    task = """STEP 1: Two loops
    REPEAT 2 TIMES:
        Click the 'A' button
    REPEAT 3 TIMES:
        Click the 'B' button"""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(len(actions) == 2, "Two LoopBlocks", f"got {len(actions)}")
    _assert(isinstance(actions[0], LoopBlock), "First is LoopBlock")
    _assert(isinstance(actions[1], LoopBlock), "Second is LoopBlock")
    if isinstance(actions[0], LoopBlock) and isinstance(actions[1], LoopBlock):
        _assert(actions[0].count == 2, "First count is 2")
        _assert(actions[1].count == 3, "Second count is 3")


def test_loop_after_if():
    print("\n── Section 7d: Loop after IF block ──")

    task = """STEP 1: If then loop
    IF text 'Welcome' is present:
        Click the 'Continue' button
    REPEAT 2 TIMES:
        SCROLL DOWN"""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(len(actions) == 2, "Two actions (if + loop)", f"got {len(actions)}")
    _assert(isinstance(actions[0], IfBlock), "First is IfBlock")
    _assert(isinstance(actions[1], LoopBlock), "Second is LoopBlock")


def test_all_three_loop_types():
    print("\n── Section 7e: All three loop types in one STEP ──")

    task = """STEP 1: All loops
    REPEAT 2 TIMES:
        Click the 'X' button
    FOR EACH {item} IN {items}:
        Click the '{item}' button
    WHILE button 'More' exists:
        Click the 'More' button"""

    blocks = parse_hunt_blocks(task)
    actions = blocks[0].actions
    _assert(len(actions) == 3, "Three LoopBlocks", f"got {len(actions)}")

    if len(actions) >= 3:
        _assert(isinstance(actions[0], LoopBlock) and actions[0].kind == "repeat", "First is REPEAT")
        _assert(isinstance(actions[1], LoopBlock) and actions[1].kind == "for_each", "Second is FOR EACH")
        _assert(isinstance(actions[2], LoopBlock) and actions[2].kind == "while", "Third is WHILE")


# ── Section 8: Edge cases ───────────────────────────────────────────────────


def test_repeat_one():
    print("\n── Section 8a: REPEAT 1 TIMES ──")

    task = """STEP 1: Single
    REPEAT 1 TIMES:
        Click the 'OK' button"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    _assert(isinstance(lb, LoopBlock), "Single-iteration REPEAT parses")
    if isinstance(lb, LoopBlock):
        _assert(lb.count == 1, "count is 1")


def test_max_loop_constant():
    print("\n── Section 8b: MAX_LOOP_ITERATIONS constant ──")

    _assert(isinstance(MAX_LOOP_ITERATIONS, int), "MAX_LOOP_ITERATIONS is int")
    _assert(MAX_LOOP_ITERATIONS > 0, "MAX_LOOP_ITERATIONS is positive", f"got {MAX_LOOP_ITERATIONS}")
    _assert(MAX_LOOP_ITERATIONS == 100, "MAX_LOOP_ITERATIONS is 100", f"got {MAX_LOOP_ITERATIONS}")


def test_for_each_multi_word_var():
    print("\n── Section 8c: FOR EACH with multi-char var names ──")

    task = """STEP 1: Long var
    FOR EACH {product_name} IN {all_products}:
        Fill 'Search' with '{product_name}'"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    if isinstance(lb, LoopBlock):
        _assert(lb.var_name == "product_name", "Multi-char var_name", f"got {lb.var_name!r}")
        _assert(lb.collection_expr == "all_products", "Multi-char collection", f"got {lb.collection_expr!r}")


def test_loop_preserves_raw_actions():
    print("\n── Section 8d: raw_actions preserved ──")

    task = """STEP 1: Raw
    REPEAT 2 TIMES:
        Click the 'A' button
        WAIT 1"""

    blocks = parse_hunt_blocks(task)
    lb = blocks[0].actions[0]
    if isinstance(lb, LoopBlock):
        _assert(len(lb.raw_actions) == 2, "raw_actions has 2 entries", f"got {len(lb.raw_actions)}")
        _assert(isinstance(lb.raw_actions[0], str), "raw_actions[0] is string")


def test_while_complex_condition():
    print("\n── Section 8e: WHILE with complex conditions ──")

    # Variable contains
    task = """STEP 1: Contains
    WHILE {message} contains 'loading':
        WAIT 1"""
    lb = parse_hunt_blocks(task)[0].actions[0]
    if isinstance(lb, LoopBlock):
        _assert(lb.condition_text == "{message} contains 'loading'", "contains condition", f"got {lb.condition_text!r}")

    # Variable comparison
    task2 = """STEP 1: Compare
    WHILE {retries} != '0':
        Click the 'Retry' button"""
    lb2 = parse_hunt_blocks(task2)[0].actions[0]
    if isinstance(lb2, LoopBlock):
        _assert(lb2.condition_text == "{retries} != '0'", "!= condition", f"got {lb2.condition_text!r}")


def test_deeply_nested():
    print("\n── Section 8f: Deep nesting — loop > if > loop ──")

    task = """STEP 1: Deep
    REPEAT 3 TIMES:
        IF button 'Expand' exists:
            REPEAT 2 TIMES:
                Click the 'Expand' button"""

    blocks = parse_hunt_blocks(task)
    outer = blocks[0].actions[0]
    _assert(isinstance(outer, LoopBlock), "Outer is LoopBlock")

    if isinstance(outer, LoopBlock):
        _assert(outer.count == 3, "Outer count is 3")
        inner_if = outer.actions[0]
        _assert(isinstance(inner_if, IfBlock), "Inner is IfBlock")
        if isinstance(inner_if, IfBlock):
            deepest = inner_if.branches[0].actions[0]
            _assert(isinstance(deepest, LoopBlock), "Deepest is LoopBlock")
            if isinstance(deepest, LoopBlock):
                _assert(deepest.count == 2, "Deepest count is 2")


# ── Entry point ──────────────────────────────────────────────────────────────


async def run_suite() -> tuple[int, int]:
    """Execute all loop block tests. Returns (pass_count, fail_count)."""
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    test_classify_step_loops()
    test_parse_repeat()
    test_parse_for_each()
    test_parse_for_each_bare_keys()
    test_parse_while()
    test_parse_while_variable_condition()
    test_syntax_errors()
    test_nested_loop_in_if()
    test_nested_if_in_loop()
    test_nested_loop_in_loop()
    test_nested_for_each_in_while()
    test_loopblock_fields()
    test_collect_lines()
    test_loop_with_done()
    test_loop_with_preceding_actions()
    test_multiple_loops_in_step()
    test_loop_after_if()
    test_all_three_loop_types()
    test_repeat_one()
    test_max_loop_constant()
    test_for_each_multi_word_var()
    test_loop_preserves_raw_actions()
    test_while_complex_condition()
    test_deeply_nested()

    total = _PASS + _FAIL
    print(f"\n  Loops suite: {_PASS} passed, {_FAIL} failed")
    print(f"SCORE: {_PASS}/{total}")
    return _PASS, _FAIL


if __name__ == "__main__":
    import asyncio

    p, f = asyncio.run(run_suite())
    raise SystemExit(0 if f == 0 else 1)
