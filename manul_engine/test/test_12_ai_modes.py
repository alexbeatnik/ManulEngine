import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import asyncio
from playwright.async_api import async_playwright

from manul_engine import ManulEngine
from manul_engine import prompts


AI_MODES_DOM = """
<!DOCTYPE html>
<html>
<head><meta charset='utf-8'></head>
<body>
  <button id="primary">Primary</button>
    <button id="decoy">Primary (Decoy)</button>
</body>
</html>
"""


async def run_suite() -> bool:
    print("\n🧪 AI MODES — Always-AI / Strict / Rejection")

    saved_ai_always = getattr(prompts, "AI_ALWAYS", False)
    saved_ai_policy = getattr(prompts, "AI_POLICY", "prior")

    passed = 0
    total = 3
    failures: list[str] = []

    try:
        # ── 1) STRICT vs PRIOR override behavior (unit-level, no browser) ──
        manul = ManulEngine(headless=True)

        async def _fake_llm_json(_system: str, _user: str) -> dict:
            return {"id": 2, "thought": "pick lower-score candidate"}

        manul._llm_json = _fake_llm_json  # type: ignore[method-assign]

        candidates = [
            {"id": 1, "name": "Best", "score": 100, "tag_name": "button"},
            {"id": 2, "name": "Worse", "score": 50, "tag_name": "button"},
        ]

        prompts.AI_ALWAYS = True

        prompts.AI_POLICY = "prior"
        idx_prior = await manul._llm_select_element("Click 'X'", "clickable", candidates, "")

        prompts.AI_POLICY = "strict"
        idx_strict = await manul._llm_select_element("Click 'X'", "clickable", candidates, "")

        if idx_prior == 1 and idx_strict == 0:
            print("   ✅ STRICT override: prior keeps LLM, strict enforces best score")
            passed += 1
        else:
            msg = f"FAILED — expected idx_prior=1 idx_strict=0, got {idx_prior=} {idx_strict=}"
            print(f"   ❌ {msg}")
            failures.append(msg)

        # ── 2) AI rejection returns None in Always-AI mode (unit-level) ──
        async def _fake_llm_json_reject(_system: str, _user: str) -> dict:
            return {"id": None, "thought": "no suitable element"}

        manul._llm_json = _fake_llm_json_reject  # type: ignore[method-assign]
        prompts.AI_POLICY = "prior"
        idx_reject = await manul._llm_select_element("Click 'X'", "clickable", candidates, "")

        if idx_reject is None:
            print("   ✅ AI rejection: null id returns None")
            passed += 1
        else:
            msg = f"FAILED — expected None on rejection, got {idx_reject}"
            print(f"   ❌ {msg}")
            failures.append(msg)

        # ── 3) Always-AI calls picker even when heuristics are confident ──
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(no_viewport=True)
            page = await ctx.new_page()
            await page.set_content(AI_MODES_DOM)

            manul2 = ManulEngine(headless=True)
            called = {"n": 0}

            async def _fake_select(_step: str, _mode: str, cand: list[dict], _ctx: str) -> int:
                called["n"] += 1
                # Always choose the element with html_id == 'decoy'
                for i, el in enumerate(cand):
                    if str(el.get("html_id", "")) == "decoy":
                        return i
                return 0

            manul2._llm_select_element = _fake_select  # type: ignore[method-assign]

            # When Always-AI is enabled, the picker choice should be used.
            prompts.AI_ALWAYS = True
            el_ai = await manul2._resolve_element(
                page,
                "Click 'Primary'",
                "clickable",
                ["Primary"],
                None,
                "",
                set(),
            )

            # When Always-AI is disabled, heuristics should win (and picker should not be called).
            prompts.AI_ALWAYS = False
            called_before = called["n"]
            el_heur = await manul2._resolve_element(
                page,
                "Click 'Primary'",
                "clickable",
                ["Primary"],
                None,
                "",
                set(),
            )
            called_after = called["n"]

            await browser.close()

        ok_ai = el_ai is not None and el_ai.get("html_id") == "decoy" and called["n"] >= 1
        ok_heur = el_heur is not None and el_heur.get("html_id") == "primary" and called_after == called_before

        if ok_ai and ok_heur:
            print("   ✅ Always-AI: picker used; Mixed: heuristics used")
            passed += 1
        else:
            msg = f"FAILED — always-ai/mixed behavior mismatch (ai={getattr(el_ai,'get',lambda *_: None)('html_id') if el_ai else None}, heur={getattr(el_heur,'get',lambda *_: None)('html_id') if el_heur else None}, picker_calls={called['n']})"
            print(f"   ❌ {msg}")
            failures.append(msg)

    finally:
        prompts.AI_ALWAYS = saved_ai_always
        prompts.AI_POLICY = saved_ai_policy

    print(f"\n{'=' * 70}")
    print(f"📊 SCORE: {passed}/{total} passed")
    if failures:
        print("\n🙀 Failures:")
        for f in failures:
            print(f"   • {f}")
    if passed == total:
        print("\n🏆 FLAWLESS VICTORY!")
    print(f"{'=' * 70}")

    return passed == total


if __name__ == "__main__":
    asyncio.run(run_suite())
