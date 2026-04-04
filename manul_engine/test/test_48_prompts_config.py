# manul_engine/test/test_48_prompts_config.py
"""
Unit-test suite for prompts.py — configuration loading, threshold derivation,
page name lookup, and environment variable override logic.

Tests:
  1. get_threshold — model-size auto-derivation.
  2. get_threshold — custom_threshold override.
  3. get_threshold — None (heuristics-only) returns 0.
  4. _threshold_for_model — boundary values.
  5. lookup_page_name — exact URL match.
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
    _threshold_for_model,
    get_threshold,
    lookup_page_name,
    _KEY_MAP,
    PAGE_REGISTRY,
    _PAGES_WRITE_PATH,
    AI_POLICY,
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


# ── 1. _threshold_for_model — auto-derivation ────────────────────────────────

def test_threshold_none_model() -> None:
    _assert(_threshold_for_model(None) == 0, "None model → 0 (heuristics-only)")
    _assert(_threshold_for_model("") == 0, "empty model → 0")


def test_threshold_sub_1b() -> None:
    _assert(_threshold_for_model("qwen2.5:0.5b") == 500, "0.5b model → 500")
    _assert(_threshold_for_model("tiny-0.1b") == 500, "0.1b model → 500")


def test_threshold_1_to_4b() -> None:
    _assert(_threshold_for_model("llama3:1b") == 750, "1b model → 750")
    _assert(_threshold_for_model("phi-3:3.8b") == 750, "3.8b model → 750")


def test_threshold_5_to_9b() -> None:
    _assert(_threshold_for_model("llama3:7b") == 1000, "7b model → 1000")
    _assert(_threshold_for_model("mistral:5b") == 1000, "5b model → 1000")


def test_threshold_10_to_19b() -> None:
    _assert(_threshold_for_model("codellama:13b") == 1500, "13b model → 1500")


def test_threshold_20b_plus() -> None:
    _assert(_threshold_for_model("llama3:70b") == 2000, "70b model → 2000")
    _assert(_threshold_for_model("mixtral:22b") == 2000, "22b model → 2000")


def test_threshold_no_size_in_name() -> None:
    _assert(_threshold_for_model("gpt-4") == 500, "no size tag → default 500")
    _assert(_threshold_for_model("custom-model") == 500, "unparseable → default 500")


# ── 2. get_threshold — priority chain ────────────────────────────────────────

def test_get_threshold_custom_wins() -> None:
    _assert(get_threshold("qwen2.5:7b", custom_threshold=42) == 42,
            "custom_threshold overrides model-derived")


def test_get_threshold_env_wins_over_model() -> None:
    from manul_engine import prompts as _p
    original = _p.ENV_AI_THRESHOLD
    try:
        _p.ENV_AI_THRESHOLD = 999
        _assert(get_threshold("qwen2.5:7b") == 999, "ENV_AI_THRESHOLD overrides model")
    finally:
        _p.ENV_AI_THRESHOLD = original


def test_get_threshold_custom_wins_over_env() -> None:
    from manul_engine import prompts as _p
    original = _p.ENV_AI_THRESHOLD
    try:
        _p.ENV_AI_THRESHOLD = 999
        _assert(get_threshold("qwen2.5:7b", custom_threshold=42) == 42,
                "custom_threshold beats ENV_AI_THRESHOLD")
    finally:
        _p.ENV_AI_THRESHOLD = original


def test_get_threshold_none_model_no_overrides() -> None:
    from manul_engine import prompts as _p
    original = _p.ENV_AI_THRESHOLD
    try:
        _p.ENV_AI_THRESHOLD = None
        _assert(get_threshold(None) == 0, "None model, no overrides → 0")
    finally:
        _p.ENV_AI_THRESHOLD = original


# ── 3. lookup_page_name — exact match ────────────────────────────────────────

def test_lookup_exact_match() -> None:
    saved = dict(PAGE_REGISTRY)
    try:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY["https://example.com/"] = {
            "Domain": "Example Site",
            "https://example.com/login": "Login Page",
        }
        # Patch the effective read path to skip disk reads
        with patch("manul_engine.prompts._PAGES_WRITE_PATH", Path("/nonexistent")):
            with patch("manul_engine.prompts._PAGES_READ_PATH", Path("/nonexistent")):
                result = lookup_page_name("https://example.com/login")
                _assert(result == "Login Page", "exact URL → Login Page",
                        f"got '{result}'")
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
        with patch("manul_engine.prompts._PAGES_WRITE_PATH", Path("/nonexistent")):
            with patch("manul_engine.prompts._PAGES_READ_PATH", Path("/nonexistent")):
                result = lookup_page_name("https://shop.com/products/42")
                _assert(result == "Product Detail", "regex pattern matches product URL",
                        f"got '{result}'")
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
        with patch("manul_engine.prompts._PAGES_WRITE_PATH", Path("/nonexistent")):
            with patch("manul_engine.prompts._PAGES_READ_PATH", Path("/nonexistent")):
                result = lookup_page_name("https://example.com/unknown-page")
                _assert(result == "Example Site", "no pattern match → Domain fallback",
                        f"got '{result}'")
    finally:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY.update(saved)


# ── 6. lookup_page_name — auto-populate for unknown site ─────────────────────

def test_lookup_auto_populate() -> None:
    saved = dict(PAGE_REGISTRY)
    tmp_pages = None
    try:
        PAGE_REGISTRY.clear()
        # Create a temporary pages.json so auto-populate has somewhere to write
        tmp_pages = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp_pages.write("{}\n")
        tmp_pages.close()
        tmp_path = Path(tmp_pages.name)

        with patch("manul_engine.prompts._PAGES_WRITE_PATH", tmp_path):
            with patch("manul_engine.prompts._PAGES_READ_PATH", tmp_path):
                result = lookup_page_name("https://brand-new-site.io/dashboard")
                _assert("Auto:" in result, "unknown site → auto-generated placeholder",
                        f"got '{result}'")
                _assert("brand-new-site.io" in result, "placeholder includes domain",
                        f"got '{result}'")
        # Verify it was written to disk
        disk = json.loads(tmp_path.read_text(encoding="utf-8"))
        _assert("https://brand-new-site.io/" in disk, "auto-populated entry written to pages.json")
    finally:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY.update(saved)
        if tmp_pages is not None:
            try:
                os.unlink(tmp_pages.name)
            except OSError:
                pass


# ── 7. _KEY_MAP completeness ─────────────────────────────────────────────────

def test_key_map_expected_keys() -> None:
    expected = {
        "model", "headless", "browser", "timeout", "nav_timeout",
        "ai_threshold", "ai_always", "ai_policy",
        "controls_cache_enabled", "controls_cache_dir", "semantic_cache_enabled",
        "log_name_maxlen", "log_thought_maxlen", "workers",
        "auto_annotate", "channel", "executable_path",
        "retries", "screenshot", "html_report", "explain_mode",
    }
    for key in expected:
        _assert(key in _KEY_MAP, f"_KEY_MAP has '{key}'")
    _assert(len(_KEY_MAP) >= len(expected), f"_KEY_MAP has at least {len(expected)} entries",
            f"got {len(_KEY_MAP)}")


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

def test_ai_policy_valid() -> None:
    _assert(AI_POLICY in ("prior", "strict"), f"AI_POLICY is '{AI_POLICY}'")


def test_browser_valid() -> None:
    _assert(BROWSER in ("chromium", "firefox", "webkit", "electron"),
            f"BROWSER is '{BROWSER}'")


def test_screenshot_valid() -> None:
    _assert(SCREENSHOT in ("on-fail", "always", "none"),
            f"SCREENSHOT is '{SCREENSHOT}'")


# ── 10. VERIFY_MAX_RETRIES config ───────────────────────────────────────────

def test_verify_max_retries_default() -> None:
    _assert(VERIFY_MAX_RETRIES == 15,
            f"default VERIFY_MAX_RETRIES is 15 (got {VERIFY_MAX_RETRIES})")


def test_verify_max_retries_minimum() -> None:
    _assert(VERIFY_MAX_RETRIES >= 1,
            f"VERIFY_MAX_RETRIES >= 1 (got {VERIFY_MAX_RETRIES})")


def test_verify_max_retries_env_override() -> None:
    import importlib
    import manul_engine.prompts as _p
    with patch.dict(os.environ, {"MANUL_VERIFY_MAX_RETRIES": "3"}):
        importlib.reload(_p)
        val = _p.VERIFY_MAX_RETRIES
    importlib.reload(_p)  # restore
    _assert(val == 3,
            f"MANUL_VERIFY_MAX_RETRIES=3 override",
            f"got {val}")


def test_verify_max_retries_env_floor() -> None:
    import importlib
    import manul_engine.prompts as _p
    with patch.dict(os.environ, {"MANUL_VERIFY_MAX_RETRIES": "0"}):
        importlib.reload(_p)
        val = _p.VERIFY_MAX_RETRIES
    importlib.reload(_p)  # restore
    _assert(val == 1,
            f"MANUL_VERIFY_MAX_RETRIES=0 floors to 1",
            f"got {val}")


def test_verify_max_retries_env_garbage() -> None:
    import importlib
    import manul_engine.prompts as _p
    with patch.dict(os.environ, {"MANUL_VERIFY_MAX_RETRIES": "abc"}):
        importlib.reload(_p)
        val = _p.VERIFY_MAX_RETRIES
    importlib.reload(_p)  # restore
    _assert(val == 15,
            f"MANUL_VERIFY_MAX_RETRIES=abc falls back to 15",
            f"got {val}")


# ── Entry point ──────────────────────────────────────────────────────────────

async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n🧪 Prompts & Config Test Suite")
    print("=" * 50)

    print("\n  1. _threshold_for_model — auto-derivation")
    test_threshold_none_model()
    test_threshold_sub_1b()
    test_threshold_1_to_4b()
    test_threshold_5_to_9b()
    test_threshold_10_to_19b()
    test_threshold_20b_plus()
    test_threshold_no_size_in_name()

    print("\n  2. get_threshold — priority chain")
    test_get_threshold_custom_wins()
    test_get_threshold_env_wins_over_model()
    test_get_threshold_custom_wins_over_env()
    test_get_threshold_none_model_no_overrides()

    print("\n  3. lookup_page_name — exact match")
    test_lookup_exact_match()

    print("\n  4. lookup_page_name — regex match")
    test_lookup_regex_match()

    print("\n  5. lookup_page_name — Domain fallback")
    test_lookup_domain_fallback()

    print("\n  6. lookup_page_name — auto-populate")
    test_lookup_auto_populate()

    print("\n  7. _KEY_MAP completeness")
    test_key_map_expected_keys()
    test_key_map_env_prefix()

    print("\n  8. env_bool helper")
    test_env_bool_truthy()
    test_env_bool_falsy()
    test_env_bool_default()

    print("\n  9. Module-level constants")
    test_ai_policy_valid()
    test_browser_valid()
    test_screenshot_valid()

    print("\n  10. VERIFY_MAX_RETRIES config")
    test_verify_max_retries_default()
    test_verify_max_retries_minimum()
    test_verify_max_retries_env_override()
    test_verify_max_retries_env_floor()
    test_verify_max_retries_env_garbage()

    total = _PASS + _FAIL
    print(f"\n{'='*50}")
    if _FAIL == 0:
        print(f"SCORE: {_PASS}/{total} — FLAWLESS VICTORY 🏆")
    else:
        print(f"SCORE: {_PASS}/{total} — {_FAIL} FAILED 💀")
    print(f"{'='*50}")
    return _PASS, _FAIL


if __name__ == "__main__":
    _passed, _failed = asyncio.run(run_suite())
    sys.exit(0 if _failed == 0 else 1)
