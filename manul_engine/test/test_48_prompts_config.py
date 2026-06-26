# manul_engine/test/test_48_prompts_config.py
"""
Unit-test suite for prompts.py — configuration loading,
page name lookup, and environment variable override logic.

Tests:
  1. lookup_page_name — exact URL match.
  6. lookup_page_name — regex pattern match.
  7. lookup_page_name — Domain fallback.
  8. lookup_page_name — auto-population for unknown URL.
  9. _KEY_MAP completeness — all expected keys present.
 10. env_bool helper — truthy and falsy values.
 11. Configuration module-level constants — defaults.

No browser or network required — tests the config layer only.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.prompts import (
    lookup_page_name,
    _KEY_MAP,
    PAGE_REGISTRY,
    _PAGES_DIR_PATH,
    BROWSER,
    SCREENSHOT,
    VERIFY_MAX_RETRIES,
)
from manul_engine.helpers import env_bool

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


# ── 3. lookup_page_name — exact match ────────────────────────────────────────


def test_lookup_exact_match() -> None:
    saved = dict(PAGE_REGISTRY)
    try:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY["https://example.com/"] = {
            "Domain": "Example Site",
            "https://example.com/login": "Login Page",
        }
        # Point the registry directory at an empty path so the live re-merge
        # in lookup_page_name() doesn't clobber the in-memory PAGE_REGISTRY.
        with patch("manul_engine.prompts._PAGES_DIR_PATH", Path("/nonexistent")):
            result = lookup_page_name("https://example.com/login")
            _assert(result == "Login Page", "exact URL → Login Page", f"got '{result}'")
    finally:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY.update(saved)


# ── 4. lookup_page_name — regex match ────────────────────────────────────────


def test_lookup_regex_match() -> None:
    saved = dict(PAGE_REGISTRY)
    try:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY["https://shop.com/"] = {
            "Domain": "Shop",
            r".*/products/\d+": "Product Detail",
        }
        with patch("manul_engine.prompts._PAGES_DIR_PATH", Path("/nonexistent")):
            result = lookup_page_name("https://shop.com/products/42")
            _assert(result == "Product Detail", "regex pattern matches product URL", f"got '{result}'")
    finally:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY.update(saved)


# ── 5. lookup_page_name — Domain fallback ────────────────────────────────────


def test_lookup_domain_fallback() -> None:
    saved = dict(PAGE_REGISTRY)
    try:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY["https://example.com/"] = {
            "Domain": "Example Site",
        }
        with patch("manul_engine.prompts._PAGES_DIR_PATH", Path("/nonexistent")):
            result = lookup_page_name("https://example.com/unknown-page")
            _assert(result == "Example Site", "no pattern match → Domain fallback", f"got '{result}'")
    finally:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY.update(saved)


# ── 6. lookup_page_name — auto-populate for unknown site ─────────────────────


def test_lookup_auto_populate() -> None:
    saved = dict(PAGE_REGISTRY)
    tmp_dir = None
    try:
        PAGE_REGISTRY.clear()
        # Create a temporary pages/ directory so auto-populate has somewhere to write.
        tmp_dir = Path(tempfile.mkdtemp(prefix="manul_pages_"))

        with patch("manul_engine.prompts._PAGES_DIR_PATH", tmp_dir):
            result = lookup_page_name("https://brand-new-site.io/dashboard")
            _assert("Auto:" in result, "unknown site → auto-generated placeholder", f"got '{result}'")
            _assert("brand-new-site.io" in result, "placeholder includes domain", f"got '{result}'")

            # Verify a per-site fragment was written.
            fragment = tmp_dir / "brand-new-site.io.json"
            _assert(fragment.exists(), "auto-populated fragment written to pages/", f"path={fragment}")
            disk = json.loads(fragment.read_text(encoding="utf-8"))
            _assert(disk.get("site") == "https://brand-new-site.io/", "fragment carries 'site' field")
            _assert(
                "https://brand-new-site.io/dashboard" in disk,
                "fragment includes the auto-populated URL key",
            )
    finally:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY.update(saved)
        if tmp_dir is not None and tmp_dir.exists():
            import shutil as _sh

            _sh.rmtree(tmp_dir, ignore_errors=True)


# ── 6b. pages/ directory loader — lean & wrapped fragment shapes ─────────────


def test_pages_dir_lean_and_wrapped() -> None:
    import shutil
    from manul_engine.prompts import _load_pages_dir, _safe_site_filename

    tmp = Path(tempfile.mkdtemp(prefix="manul_pages_dir_"))
    try:
        # Lean form with explicit "site" field.
        (tmp / "example.com.json").write_text(
            json.dumps(
                {
                    "site": "https://example.com/",
                    "Domain": "Example",
                    ".*/login": "Login Page",
                }
            ),
            encoding="utf-8",
        )
        # Wrapped form (back-compat shape).
        (tmp / "shop.json").write_text(
            json.dumps({"https://shop.com/": {"Domain": "Shop", ".*/cart": "Cart"}}),
            encoding="utf-8",
        )
        # Malformed: no "site" field, lean form. Should be skipped (and warn).
        (tmp / "broken.json").write_text(
            json.dumps({"Domain": "Orphan"}),
            encoding="utf-8",
        )

        import warnings as _warnings

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            registry = _load_pages_dir(tmp)

        _assert("https://example.com/" in registry, "lean fragment contributes site key")
        _assert(registry["https://example.com/"].get("Domain") == "Example", "lean Domain preserved")
        _assert(
            registry["https://example.com/"].get(".*/login") == "Login Page",
            "lean pattern preserved",
        )
        _assert("https://shop.com/" in registry, "wrapped fragment contributes site key")
        _assert(registry["https://shop.com/"].get(".*/cart") == "Cart", "wrapped pattern preserved")
        _assert("Orphan" not in str(registry), "fragment without 'site' field is skipped")

        # _safe_site_filename slugifies special characters in the netloc.
        _assert(_safe_site_filename("https://www.shop.com/") == "www.shop.com.json", "safe filename basic")
        _assert(
            _safe_site_filename("https://api.shop.com:8080/") == "api.shop.com_8080.json",
            "safe filename strips port colon",
        )
        _assert(_safe_site_filename("") == "site.json", "safe filename has fallback")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 7. _KEY_MAP completeness ─────────────────────────────────────────────────


def test_key_map_expected_keys() -> None:
    expected = {
        "headless",
        "browser",
        "timeout",
        "nav_timeout",
        "semantic_cache_enabled",
        "log_name_maxlen",
        "log_thought_maxlen",
        "workers",
        "auto_annotate",
        "channel",
        "executable_path",
        "retries",
        "screenshot",
        "html_report",
        "explain_mode",
    }
    for key in expected:
        _assert(key in _KEY_MAP, f"_KEY_MAP has '{key}'")
    _assert(len(_KEY_MAP) >= len(expected), f"_KEY_MAP has at least {len(expected)} entries", f"got {len(_KEY_MAP)}")


def test_key_map_env_prefix() -> None:
    for key, env_var in _KEY_MAP.items():
        _assert(env_var.startswith("MANUL_"), f"{key} env var '{env_var}' has MANUL_ prefix")


# ── 8. env_bool helper ───────────────────────────────────────────────────────


def test_env_bool_truthy() -> None:
    for val in ("true", "True", "TRUE", "1", "yes", "t"):
        os.environ["_MANUL_TEST_BOOL"] = val
        _assert(env_bool("_MANUL_TEST_BOOL") is True, f"env_bool('{val}') → True")
    if "_MANUL_TEST_BOOL" in os.environ:
        del os.environ["_MANUL_TEST_BOOL"]


def test_env_bool_falsy() -> None:
    for val in ("false", "False", "0", "no", "f", ""):
        os.environ["_MANUL_TEST_BOOL"] = val
        _assert(env_bool("_MANUL_TEST_BOOL") is False, f"env_bool('{val}') → False")
    if "_MANUL_TEST_BOOL" in os.environ:
        del os.environ["_MANUL_TEST_BOOL"]


def test_env_bool_default() -> None:
    key = "_MANUL_TEST_ABSENT_KEY"
    if key in os.environ:
        del os.environ[key]
    _assert(env_bool(key) is False, "env_bool missing key → False default")
    _assert(env_bool(key, "True") is True, "env_bool missing key, default='True' → True")


# ── 9. Module-level defaults ─────────────────────────────────────────────────


def test_browser_valid() -> None:
    _assert(BROWSER in ("chromium", "electron"), f"BROWSER is '{BROWSER}'")


def test_screenshot_valid() -> None:
    _assert(SCREENSHOT in ("on-fail", "always", "none"), f"SCREENSHOT is '{SCREENSHOT}'")


# ── 10. VERIFY_MAX_RETRIES config ───────────────────────────────────────────


def test_verify_max_retries_default() -> None:
    _assert(VERIFY_MAX_RETRIES == 15, f"default VERIFY_MAX_RETRIES is 15 (got {VERIFY_MAX_RETRIES})")


def test_verify_max_retries_minimum() -> None:
    _assert(VERIFY_MAX_RETRIES >= 1, f"VERIFY_MAX_RETRIES >= 1 (got {VERIFY_MAX_RETRIES})")


def test_verify_max_retries_env_override() -> None:
    import importlib
    import manul_engine.prompts as _p

    with patch.dict(os.environ, {"MANUL_VERIFY_MAX_RETRIES": "3"}):
        importlib.reload(_p)
        val = _p.VERIFY_MAX_RETRIES
    importlib.reload(_p)  # restore
    _assert(val == 3, f"MANUL_VERIFY_MAX_RETRIES=3 override", f"got {val}")


def test_verify_max_retries_env_floor() -> None:
    import importlib
    import manul_engine.prompts as _p

    with patch.dict(os.environ, {"MANUL_VERIFY_MAX_RETRIES": "0"}):
        importlib.reload(_p)
        val = _p.VERIFY_MAX_RETRIES
    importlib.reload(_p)  # restore
    _assert(val == 1, f"MANUL_VERIFY_MAX_RETRIES=0 floors to 1", f"got {val}")


def test_verify_max_retries_env_garbage() -> None:
    import importlib
    import manul_engine.prompts as _p

    with patch.dict(os.environ, {"MANUL_VERIFY_MAX_RETRIES": "abc"}):
        importlib.reload(_p)
        val = _p.VERIFY_MAX_RETRIES
    importlib.reload(_p)  # restore
    _assert(val == 15, f"MANUL_VERIFY_MAX_RETRIES=abc falls back to 15", f"got {val}")


# ── Entry point ──────────────────────────────────────────────────────────────


async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n🧪 Prompts & Config Test Suite")
    print("=" * 50)

    print("\n  1. lookup_page_name — exact match")
    test_lookup_exact_match()

    print("\n  4. lookup_page_name — regex match")
    test_lookup_regex_match()

    print("\n  5. lookup_page_name — Domain fallback")
    test_lookup_domain_fallback()

    print("\n  6. lookup_page_name — auto-populate")
    test_lookup_auto_populate()

    print("\n  6b. pages/ directory loader (lean & wrapped fragments)")
    test_pages_dir_lean_and_wrapped()

    print("\n  7. _KEY_MAP completeness")
    test_key_map_expected_keys()
    test_key_map_env_prefix()

    print("\n  8. env_bool helper")
    test_env_bool_truthy()
    test_env_bool_falsy()
    test_env_bool_default()

    print("\n  9. Module-level constants")
    test_browser_valid()
    test_screenshot_valid()

    print("\n  10. VERIFY_MAX_RETRIES config")
    test_verify_max_retries_default()
    test_verify_max_retries_minimum()
    test_verify_max_retries_env_override()
    test_verify_max_retries_env_floor()
    test_verify_max_retries_env_garbage()

    total = _PASS + _FAIL
    print(f"\n{'=' * 50}")
    if _FAIL == 0:
        print(f"SCORE: {_PASS}/{total} — FLAWLESS VICTORY 🏆")
    else:
        print(f"SCORE: {_PASS}/{total} — {_FAIL} FAILED 💀")
    print(f"{'=' * 50}")
    return _PASS, _FAIL


if __name__ == "__main__":
    _passed, _failed = asyncio.run(run_suite())
    sys.exit(0 if _failed == 0 else 1)
