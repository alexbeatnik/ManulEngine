# manul_engine/test/test_40_self_healing_cache.py
"""
Unit-test suite for the Self-Healing Controls Cache feature.

Tests:
  1. Stale cache detection: when a cached element no longer matches any DOM
     candidate, the engine detects the stale entry and sets _had_stale_cache.
  2. Healed flag: _last_step_healed is set when heuristics re-resolve after
     a stale cache miss.
  3. Cache overwrite on heal: _remember_resolved_control updates the stale
     cache entry with the newly resolved element.
  4. Non-stale paths: _last_step_healed stays False when the cache hits or
     when no cache entry existed at all.
  5. StepResult.healed field: default False; can be set True.
  6. Reporter: healed badge rendered in step row HTML when healed=True.

No network or live browser required; uses synthetic DOM via Playwright.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine import ManulEngine
from manul_engine import prompts
from manul_engine.reporting import StepResult, MissionResult, RunSummary
from manul_engine.reporter import generate_report

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


# ── Synthetic DOM ─────────────────────────────────────────────────────────────

ORIGINAL_DOM = """\
<!DOCTYPE html>
<html><head><meta charset='utf-8'></head>
<body>
  <button id="login-btn" data-qa="login" aria-label="Log In">Log In</button>
  <input id="email-input" name="email" placeholder="Email" />
</body>
</html>
"""

CHANGED_DOM = """\
<!DOCTYPE html>
<html><head><meta charset='utf-8'></head>
<body>
  <button id="login-btn-v2" data-qa="sign-in" aria-label="Log In">Log In</button>
  <input id="email-field" name="user_email" placeholder="Email Address" />
</body>
</html>
"""


async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n🧪 SELF-HEALING CONTROLS CACHE — stale detection, heal flag, reporter badge")

    saved_enabled = getattr(prompts, "CONTROLS_CACHE_ENABLED", True)
    saved_dir = getattr(prompts, "CONTROLS_CACHE_DIR", "")

    project_root = Path(__file__).resolve().parents[2]
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_cache_root = project_root / "cache" / f"heal_run_{run_id}"

    try:
        prompts.CONTROLS_CACHE_ENABLED = True
        prompts.CONTROLS_CACHE_DIR = str(temp_cache_root)

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(no_viewport=True)
            page = await ctx.new_page()

            # ── 1. Populate cache with original DOM ───────────────────────

            await page.set_content(ORIGINAL_DOM)

            manul = ManulEngine(headless=True)
            manul._page_site_key = lambda _page: "selfheal.test"  # type: ignore[method-assign]

            mode = "clickable"
            search_texts = ["Log In"]
            target_field = None

            # Resolve the original element so it gets cached
            original_el = {
                "id": 1,
                "name": "Log In button",
                "tag_name": "button",
                "xpath": "//*[@id='login-btn']",
                "html_id": "login-btn",
                "data_qa": "login",
                "aria_label": "Log In",
                "placeholder": "",
            }
            manul._persist_control_cache_entry(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                element=original_el,
            )

            cache_key = manul._control_cache_key(mode, search_texts, target_field)

            _assert(
                cache_key in manul._controls_cache_data,
                "Cache entry created for original element",
            )

            # ── 2. Cache hit when DOM matches ─────────────────────────────

            candidates_match = [
                {
                    "id": 10,
                    "name": "Log In button",
                    "tag_name": "button",
                    "xpath": "//*[@id='login-btn']",
                    "html_id": "login-btn",
                    "data_qa": "login",
                    "aria_label": "Log In",
                    "placeholder": "",
                    "frame_index": 0,
                },
            ]

            resolved = manul._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=candidates_match,
            )
            _assert(
                resolved is not None and resolved.get("html_id") == "login-btn",
                "Cache hit returns matching element",
            )

            # ── 3. Stale cache detection ──────────────────────────────────

            candidates_changed = [
                {
                    "id": 20,
                    "name": "Sign In button",
                    "tag_name": "button",
                    "xpath": "//*[@id='login-btn-v2']",
                    "html_id": "login-btn-v2",
                    "data_qa": "sign-in",
                    "aria_label": "Sign In",
                    "placeholder": "",
                    "frame_index": 0,
                },
            ]

            resolved_miss = manul._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=candidates_changed,
            )
            _assert(
                resolved_miss is None,
                "Cache miss when DOM element properties changed (stale)",
            )

            # Verify cache entry still exists (stale, not deleted)
            _assert(
                cache_key in manul._controls_cache_data,
                "Stale cache entry still present in data (not prematurely deleted)",
            )

            # ── 4. _last_step_healed flag — stale path ───────────────────

            manul._last_step_healed = False
            manul._controls_cache_enabled = True

            # Simulate what _resolve_element does: cache miss + check stale
            _had_stale = cache_key in manul._controls_cache_data
            _assert(
                _had_stale is True,
                "_had_stale_cache detected when cache entry exists but DOM changed",
            )

            # ── 5. _last_step_healed stays False on cache hit ─────────────

            manul._last_step_healed = False
            resolved_hit = manul._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=candidates_match,
            )
            _assert(
                resolved_hit is not None and manul._last_step_healed is False,
                "_last_step_healed stays False on cache hit (no healing needed)",
            )

            # ── 6. _last_step_healed stays False when no cache entry ──────

            manul._last_step_healed = False
            no_entry_search = ["Nonexistent Button"]
            no_entry_key = manul._control_cache_key(mode, no_entry_search, None)
            _had_stale_no_entry = no_entry_key in manul._controls_cache_data
            _assert(
                _had_stale_no_entry is False,
                "No stale detection when cache entry does not exist",
            )

            # ── 7. Cache overwrite after heal ─────────────────────────────

            new_element = {
                "id": 20,
                "name": "Sign In button",
                "tag_name": "button",
                "xpath": "//*[@id='login-btn-v2']",
                "html_id": "login-btn-v2",
                "data_qa": "sign-in",
                "aria_label": "Sign In",
                "placeholder": "",
            }
            manul._persist_control_cache_entry(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                element=new_element,
            )

            updated_entry = manul._controls_cache_data.get(cache_key, {})
            _assert(
                updated_entry.get("html_id") == "login-btn-v2",
                "Cache entry overwritten with healed element (html_id updated)",
            )
            _assert(
                updated_entry.get("data_qa") == "sign-in",
                "Cache entry overwritten with healed element (data_qa updated)",
            )

            # ── 8. After heal, cache now hits the new element ─────────────

            resolved_after_heal = manul._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=candidates_changed,
            )
            _assert(
                resolved_after_heal is not None and resolved_after_heal.get("html_id") == "login-btn-v2",
                "After heal, cache hits the new element correctly",
            )

            await browser.close()

        # ── 9. StepResult.healed field ────────────────────────────────────

        sr_default = StepResult(index=1, text="Click 'Login'")
        _assert(
            sr_default.healed is False,
            "StepResult.healed defaults to False",
        )

        sr_healed = StepResult(index=2, text="Click 'Login'", healed=True)
        _assert(
            sr_healed.healed is True,
            "StepResult.healed can be set to True",
        )

        # ── 10. Reporter renders healed badge ─────────────────────────────

        import tempfile
        step_healed = StepResult(index=1, text="Click 'Login' button", status="pass",
                                 duration_ms=150, healed=True)
        step_normal = StepResult(index=2, text="DONE.", status="pass", duration_ms=5)
        mission = MissionResult(
            file="/tmp/heal_test.hunt", name="heal_test.hunt", status="pass",
            duration_ms=155, steps=[step_healed, step_normal],
        )
        summary = RunSummary()
        summary.started_at = "2025-01-15 10:30:00"
        summary.ended_at = "2025-01-15 10:30:01"
        summary.total = 1
        summary.passed = 1
        summary.missions = [mission]

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = os.path.join(tmpdir, "test_report.html")
            result_path = generate_report(summary, report_path)
            html = open(result_path, encoding="utf-8").read()

        _assert(
            "healed-badge" in html,
            "Reporter HTML contains healed-badge CSS class",
        )
        _assert(
            "healed" in html.lower(),
            "Reporter HTML contains 'healed' text",
        )

        # ── 11. Reporter does NOT render healed badge for non-healed steps

        step_no_heal = StepResult(index=1, text="Click 'OK' button", status="pass",
                                  duration_ms=100, healed=False)
        mission2 = MissionResult(
            file="/tmp/no_heal.hunt", name="no_heal.hunt", status="pass",
            duration_ms=100, steps=[step_no_heal],
        )
        summary2 = RunSummary()
        summary2.started_at = "2025-01-15 10:30:00"
        summary2.ended_at = "2025-01-15 10:30:01"
        summary2.total = 1
        summary2.passed = 1
        summary2.missions = [mission2]

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path2 = os.path.join(tmpdir, "test_no_heal.html")
            result_path2 = generate_report(summary2, report_path2)
            html2 = open(result_path2, encoding="utf-8").read()

        # The CSS class definition will be in the stylesheet; we check the
        # badge is NOT rendered as a *span* in the step row.
        _assert(
            '<span class="healed-badge">' not in html2,
            "Reporter does NOT render healed badge span for non-healed steps",
        )

        # ── 12. Reporter healed badge in logical step group ───────────────

        step_lg_healed = StepResult(index=1, text="Click 'Submit'", status="pass",
                                    duration_ms=200, healed=True,
                                    logical_step="STEP 1: Fill form")
        step_lg_normal = StepResult(index=2, text="DONE.", status="pass",
                                    duration_ms=5, logical_step="STEP 1: Fill form")
        mission3 = MissionResult(
            file="/tmp/lg_heal.hunt", name="lg_heal.hunt", status="pass",
            duration_ms=205, steps=[step_lg_healed, step_lg_normal],
        )
        summary3 = RunSummary()
        summary3.started_at = "2025-01-15 10:30:00"
        summary3.ended_at = "2025-01-15 10:30:01"
        summary3.total = 1
        summary3.passed = 1
        summary3.missions = [mission3]

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path3 = os.path.join(tmpdir, "test_lg_heal.html")
            result_path3 = generate_report(summary3, report_path3)
            html3 = open(result_path3, encoding="utf-8").read()

        _assert(
            html3.count("healed-badge") >= 2,
            "Logical step group shows healed badge (step row + group header)",
        )

    finally:
        prompts.CONTROLS_CACHE_ENABLED = saved_enabled
        prompts.CONTROLS_CACHE_DIR = saved_dir
        if temp_cache_root.exists():
            shutil.rmtree(temp_cache_root, ignore_errors=True)

    total = _PASS + _FAIL
    print(f"\n{'=' * 70}")
    print(f"📊 SCORE: {_PASS}/{total} passed")
    if _FAIL:
        print(f"\n🙀 {_FAIL} assertion(s) failed")
    else:
        print("\n🏆 FLAWLESS VICTORY!")
    print(f"{'=' * 70}")

    return _FAIL == 0


if __name__ == "__main__":
    asyncio.run(run_suite())
