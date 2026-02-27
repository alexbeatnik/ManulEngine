import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import asyncio
import datetime
import json
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

from engine import ManulEngine
from engine import prompts


CACHE_TEST_DOM = """
<!DOCTYPE html>
<html>
<head><meta charset='utf-8'></head>
<body>
  <button id="save-btn" data-qa="save-profile" aria-label="Save Profile">Save Profile</button>
  <button id="other-btn" data-qa="cancel-profile">Cancel</button>
</body>
</html>
"""


async def run_suite() -> bool:
    print("\n🧪 CONTROLS CACHE — persistent cache hit/miss + temporary run folder")

    saved_enabled = getattr(prompts, "CONTROLS_CACHE_ENABLED", True)
    saved_dir = getattr(prompts, "CONTROLS_CACHE_DIR", "")

    passed = 0
    total = 5
    failures: list[str] = []

    project_root = Path(__file__).resolve().parents[2]
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_cache_root = project_root / "cache" / f"run_{run_id}"

    try:
        prompts.CONTROLS_CACHE_ENABLED = True
        prompts.CONTROLS_CACHE_DIR = str(temp_cache_root)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(no_viewport=True)
            page = await ctx.new_page()
            await page.set_content(CACHE_TEST_DOM)

            manul = ManulEngine(headless=True)
            manul._page_site_key = lambda _page: "synthetic.local"  # type: ignore[method-assign]

            mode = "clickable"
            search_texts = ["Save Profile"]
            target_field = None
            cache_key = manul._control_cache_key(mode, search_texts, target_field)

            class _StubPage:
                def __init__(self, url: str):
                    self.url = url

            page_dyn_a = _StubPage("https://example.com/user/dsdfddg/1/medication-list")
            page_dyn_b = _StubPage("https://example.com/user/zzxxyyq/2/medication-list")

            element = {
                "id": 1,
                "name": "Save Profile",
                "tag_name": "button",
                "xpath": "//*[@id='save-btn']",
                "html_id": "save-btn",
                "data_qa": "save-profile",
                "aria_label": "Save Profile",
                "placeholder": "",
            }

            manul._persist_control_cache_entry(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                element=element,
            )

            site_dir = temp_cache_root / "synthetic.local"
            url_files = list(site_dir.glob("*.json"))
            cache_file = url_files[0] if url_files else None
            if cache_file is not None and cache_file.exists():
                print("   ✅ Per-URL cache file created in site folder")
                passed += 1
            else:
                msg = f"FAILED — URL cache file was not created in {site_dir}"
                print(f"   ❌ {msg}")
                failures.append(msg)

            raw = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file is not None and cache_file.exists() else {}
            controls = raw.get("controls", {}) if isinstance(raw, dict) else {}
            has_key = cache_key in controls

            candidates_hit = [
                {
                    "id": 11,
                    "name": "Save Profile",
                    "tag_name": "button",
                    "xpath": "//*[@id='save-btn']",
                    "html_id": "save-btn",
                    "data_qa": "save-profile",
                    "aria_label": "Save Profile",
                    "placeholder": "",
                },
                {
                    "id": 12,
                    "name": "Cancel",
                    "tag_name": "button",
                    "xpath": "//*[@id='other-btn']",
                    "html_id": "other-btn",
                    "data_qa": "cancel-profile",
                    "aria_label": "Cancel",
                    "placeholder": "",
                },
            ]

            resolved_hit = manul._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=candidates_hit,
            )

            if has_key and resolved_hit is not None and resolved_hit.get("html_id") == "save-btn":
                print("   ✅ Cache hit returns cached control when present on page")
                passed += 1
            else:
                msg = f"FAILED — cache hit mismatch ({has_key=}, resolved={resolved_hit.get('html_id') if resolved_hit else None})"
                print(f"   ❌ {msg}")
                failures.append(msg)

            file_a = manul._page_url_file_name(page_dyn_a.url)
            file_b = manul._page_url_file_name(page_dyn_b.url)
            if file_a != file_b:
                print("   ✅ Dynamic route URLs use different per-page cache files")
                passed += 1
            else:
                msg = f"FAILED — expected different URL pages to map to different cache files ({file_a} == {file_b})"
                print(f"   ❌ {msg}")
                failures.append(msg)

            updated_element = {
                "id": 2,
                "name": "Save Profile",
                "tag_name": "button",
                "xpath": "//*[@id='save-btn-v2']",
                "html_id": "save-btn-v2",
                "data_qa": "save-profile-v2",
                "aria_label": "Save Profile",
                "placeholder": "",
            }
            manul._persist_control_cache_entry(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                element=updated_element,
            )
            raw_after = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file is not None and cache_file.exists() else {}
            controls_after = raw_after.get("controls", {}) if isinstance(raw_after, dict) else {}
            overwritten = isinstance(controls_after.get(cache_key), dict) and controls_after.get(cache_key, {}).get("html_id") == "save-btn-v2"
            if overwritten:
                print("   ✅ Cache entry is overwritten when resolved control changes")
                passed += 1
            else:
                msg = "FAILED — expected updated control to overwrite the previous cached value"
                print(f"   ❌ {msg}")
                failures.append(msg)

            candidates_miss = [
                {
                    "id": 21,
                    "name": "Cancel",
                    "tag_name": "button",
                    "xpath": "//*[@id='other-btn']",
                    "html_id": "other-btn",
                    "data_qa": "cancel-profile",
                    "aria_label": "Cancel",
                    "placeholder": "",
                }
            ]

            resolved_miss = manul._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=candidates_miss,
            )

            if resolved_miss is None:
                print("   ✅ Cache miss (after overwrite) falls back to normal resolution path")
                passed += 1
            else:
                msg = f"FAILED — expected cache miss to return None, got {resolved_miss.get('html_id')}"
                print(f"   ❌ {msg}")
                failures.append(msg)

            await browser.close()

    finally:
        prompts.CONTROLS_CACHE_ENABLED = saved_enabled
        prompts.CONTROLS_CACHE_DIR = saved_dir
        if temp_cache_root.exists():
            shutil.rmtree(temp_cache_root, ignore_errors=True)

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
