# manul_engine/config.py
"""
EngineConfig — centralised, injectable configuration for ManulEngine.

Provides a frozen dataclass that encapsulates all runtime settings previously
scattered across module-level globals in ``prompts.py``.  This allows multiple
ManulEngine instances with different configurations in the same process — a
requirement that module-globals cannot satisfy.

``prompts.py`` continues to load and export the same globals for backward
compatibility.  ``ManulEngine.__init__`` reads from ``EngineConfig`` when
one is provided, falling back to individual keyword arguments and then to
``prompts.*`` globals.

Usage::

    from manul_engine.config import EngineConfig

    cfg = EngineConfig.from_file("manul_engine_configuration.json")
    engine = ManulEngine(config=cfg)

    # Or construct programmatically:
    cfg = EngineConfig(model=None, headless=True, browser="firefox")
    engine = ManulEngine(config=cfg)
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger("manul_engine")


def _find_config_file() -> Path | None:
    """Locate ``manul_engine_configuration.json`` (CWD first, then package root)."""
    cwd_path = Path.cwd() / "manul_engine_configuration.json"
    if cwd_path.exists():
        return cwd_path
    pkg_root = Path(__file__).resolve().parents[1]
    pkg_path = pkg_root / "manul_engine_configuration.json"
    return pkg_path if pkg_path.exists() else None


@dataclasses.dataclass(frozen=True)
class EngineConfig:
    """Immutable runtime configuration for ManulEngine.

    All fields mirror keys in ``manul_engine_configuration.json`` and can be
    overridden via the ``MANUL_*`` environment variables documented in the
    project README.

    Construct via :meth:`from_file` (JSON + env overlay) or directly::

        cfg = EngineConfig(headless=True, browser="firefox")
    """

    model: str | None = None
    headless: bool = False
    browser: str = "chromium"
    browser_args: tuple[str, ...] = ()
    channel: str | None = None
    executable_path: str | None = None
    timeout: int = 5000
    nav_timeout: int = 30000
    ai_threshold: int | None = None
    ai_always: bool = False
    ai_policy: str = "prior"
    controls_cache_enabled: bool = True
    controls_cache_dir: str = "cache"
    semantic_cache_enabled: bool = True
    auto_annotate: bool = False
    retries: int = 0
    screenshot: str = "on-fail"
    html_report: bool = False
    explain_mode: bool = False
    log_name_maxlen: int = 0
    log_thought_maxlen: int = 0
    tests_home: str = "tests"
    verify_max_retries: int = 15
    custom_controls_dirs: tuple[str, ...] = ("controls",)

    # ── Factory methods ───────────────────────────────────────────────────

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> EngineConfig:
        """Load configuration from a JSON file with environment variable overlay.

        Resolution order for each setting:
        1. ``MANUL_*`` environment variable (always wins)
        2. JSON file value
        3. Dataclass default

        Args:
            path: Explicit path to the JSON config file.  When *None*, the
                  standard discovery logic is used (CWD → package root).
        """
        cfg_path = Path(path) if path else _find_config_file()
        raw: dict[str, Any] = {}
        if cfg_path and cfg_path.exists():
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    raw = json.load(f)
            except json.JSONDecodeError as exc:
                log.warning("EngineConfig: invalid JSON in %s: %s", cfg_path, exc)
            except OSError as exc:
                log.warning("EngineConfig: cannot read %s: %s", cfg_path, exc)

        return cls._build(raw)

    @classmethod
    def default(cls) -> EngineConfig:
        """Return default configuration (environment variable overlay only)."""
        return cls._build({})

    # ── Internal builder ──────────────────────────────────────────────────

    @classmethod
    def _build(cls, raw: dict[str, Any]) -> EngineConfig:
        """Merge JSON *raw* dict with env vars and return a frozen instance."""

        def _str(key: str, env: str, default: str = "") -> str:
            env_val = os.getenv(env)
            if env_val:
                return env_val.strip()
            val = raw.get(key)
            if val is not None:
                return str(val).strip()
            return default

        def _int(key: str, env: str, default: int) -> int:
            raw_val = os.getenv(env)
            if raw_val is not None:
                try:
                    return int(raw_val)
                except ValueError:
                    return default
            val = raw.get(key)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return default
            return default

        def _bool(key: str, env: str, default: bool = False) -> bool:
            env_val = os.getenv(env, "").strip().lower()
            if env_val:
                return env_val in ("1", "true", "yes")
            val = raw.get(key)
            if val is not None:
                if isinstance(val, bool):
                    return val
                return str(val).strip().lower() in ("1", "true", "yes")
            return default

        def _optional_str(key: str, env: str) -> str | None:
            env_val = (os.getenv(env) or "").strip()
            if env_val:
                return env_val
            val = raw.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
            return None

        def _optional_int(key: str, env: str) -> int | None:
            env_val = os.getenv(env)
            if env_val is not None:
                try:
                    return int(env_val)
                except ValueError:
                    return None
            val = raw.get(key)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return None
            return None

        # ── model ──
        model = _optional_str("model", "MANUL_MODEL")

        # ── browser_args (special: list type) ──
        browser_args: list[str] = []
        if "MANUL_BROWSER_ARGS" in os.environ:
            import re
            _env_ba = os.environ["MANUL_BROWSER_ARGS"].strip()
            if _env_ba:
                browser_args = [a.strip() for a in re.split(r"[,\s]+", _env_ba) if a.strip()]
        elif isinstance(raw.get("browser_args"), list):
            browser_args = [str(a) for a in raw["browser_args"] if str(a).strip()]

        # ── custom_controls_dirs (special: list type) ──
        _raw_ccd = os.getenv("MANUL_CUSTOM_CONTROLS_DIRS", "").strip()
        _raw_cmd = os.getenv("MANUL_CUSTOM_MODULES_DIRS", "").strip()
        if _raw_ccd:
            ccd = tuple(p.strip() for p in _raw_ccd.split(",") if p.strip())
        elif _raw_cmd:
            ccd = tuple(p.strip() for p in _raw_cmd.split(",") if p.strip())
        elif isinstance(raw.get("custom_controls_dirs"), list):
            ccd = tuple(str(d).strip() for d in raw["custom_controls_dirs"] if str(d).strip())
        elif isinstance(raw.get("custom_modules_dirs"), list):
            ccd = tuple(str(d).strip() for d in raw["custom_modules_dirs"] if str(d).strip())
        else:
            ccd = ("controls",)

        # ── browser validation ──
        _valid_browsers = ("chromium", "firefox", "webkit", "electron")
        _b = _str("browser", "MANUL_BROWSER", "chromium").lower()
        browser = _b if _b in _valid_browsers else "chromium"

        # ── screenshot validation ──
        _valid_ss = ("on-fail", "always", "none")
        _ss = _str("screenshot", "MANUL_SCREENSHOT", "on-fail").lower()
        screenshot = _ss if _ss in _valid_ss else "on-fail"

        return cls(
            model=model,
            headless=_bool("headless", "MANUL_HEADLESS"),
            browser=browser,
            browser_args=tuple(browser_args),
            channel=_optional_str("channel", "MANUL_CHANNEL"),
            executable_path=_optional_str("executable_path", "MANUL_EXECUTABLE_PATH"),
            timeout=_int("timeout", "MANUL_TIMEOUT", 5000),
            nav_timeout=_int("nav_timeout", "MANUL_NAV_TIMEOUT", 30000),
            ai_threshold=_optional_int("ai_threshold", "MANUL_AI_THRESHOLD"),
            ai_always=_bool("ai_always", "MANUL_AI_ALWAYS"),
            ai_policy=_str("ai_policy", "MANUL_AI_POLICY", "prior"),
            controls_cache_enabled=_bool("controls_cache_enabled", "MANUL_CONTROLS_CACHE_ENABLED", True),
            controls_cache_dir=_str("controls_cache_dir", "MANUL_CONTROLS_CACHE_DIR", "cache"),
            semantic_cache_enabled=_bool("semantic_cache_enabled", "MANUL_SEMANTIC_CACHE_ENABLED", True),
            auto_annotate=_bool("auto_annotate", "MANUL_AUTO_ANNOTATE"),
            retries=_int("retries", "MANUL_RETRIES", 0),
            screenshot=screenshot,
            html_report=_bool("html_report", "MANUL_HTML_REPORT"),
            explain_mode=_bool("explain_mode", "MANUL_EXPLAIN"),
            log_name_maxlen=_int("log_name_maxlen", "MANUL_LOG_NAME_MAXLEN", 0),
            log_thought_maxlen=_int("log_thought_maxlen", "MANUL_LOG_THOUGHT_MAXLEN", 0),
            tests_home=_str("tests_home", "MANUL_TESTS_HOME", "tests"),
            verify_max_retries=_int("verify_max_retries", "MANUL_VERIFY_MAX_RETRIES", 15),
            custom_controls_dirs=ccd,
        )

    # ── Convenience ───────────────────────────────────────────────────────

    def replace(self, **changes: Any) -> EngineConfig:
        """Return a copy with the given fields replaced (like ``dataclasses.replace``)."""
        return dataclasses.replace(self, **changes)
