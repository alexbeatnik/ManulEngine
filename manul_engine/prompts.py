# manul_engine/prompts.py
"""
ManulEngine configuration and runtime settings.

Reads settings from manul_engine_configuration.json (repo root) or environment
variables. Environment variables (MANUL_* prefix) always win over the JSON file.
Values can also be passed in code via ManulEngine(...) / EngineConfig(...).

Exports:
    HEADLESS_MODE, TIMEOUT, NAV_TIMEOUT, BROWSER, … — core settings
    lookup_page_name() — URL → friendly page-object name (mtime-cached)
"""

import json
import os
import re as _re
from pathlib import Path

from .helpers import env_bool

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ── JSON config loading ───────────────────────────────────────────────────────
# Look for manul_engine_configuration.json first in the current working
# directory (user's project root), then fall back to the package source root
# (useful when running directly from the ManulEngine dev repo).
# Environment variables (MANUL_*) always override JSON values.
_CONFIG_PATH = Path.cwd() / "manul_engine_configuration.json"
if not _CONFIG_PATH.exists():
    _CONFIG_PATH = _REPO_ROOT / "manul_engine_configuration.json"

# Maps JSON config keys → corresponding MANUL_* environment variable names.
_KEY_MAP: dict[str, str] = {
    "headless": "MANUL_HEADLESS",
    "browser": "MANUL_BROWSER",
    "timeout": "MANUL_TIMEOUT",
    "nav_timeout": "MANUL_NAV_TIMEOUT",
    "controls_cache_enabled": "MANUL_CONTROLS_CACHE_ENABLED",
    "controls_cache_dir": "MANUL_CONTROLS_CACHE_DIR",
    "semantic_cache_enabled": "MANUL_SEMANTIC_CACHE_ENABLED",
    "log_name_maxlen": "MANUL_LOG_NAME_MAXLEN",
    "log_thought_maxlen": "MANUL_LOG_THOUGHT_MAXLEN",
    "workers": "MANUL_WORKERS",
    "auto_annotate": "MANUL_AUTO_ANNOTATE",
    "channel": "MANUL_CHANNEL",
    "executable_path": "MANUL_EXECUTABLE_PATH",
    "retries": "MANUL_RETRIES",
    "screenshot": "MANUL_SCREENSHOT",
    "html_report": "MANUL_HTML_REPORT",
    "explain_mode": "MANUL_EXPLAIN",
    "verify_max_retries": "MANUL_VERIFY_MAX_RETRIES",
}

# browser_args is a list and cannot be round-tripped through a plain env string
# via _KEY_MAP, so it is handled separately below after the main loop.
_json_cfg_browser_args: "list[str]" = []
# custom_controls_dirs: list of directory names to scan for @custom_control modules.
_json_cfg_custom_modules_dirs: "list[str] | None" = None
_json_cfg_custom_controls_dirs: "list[str] | None" = None
if _CONFIG_PATH.exists():
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as _f:
            _json_cfg: dict = json.load(_f)
        for _jk, _ek in _KEY_MAP.items():
            # Skip keys starting with "_" (comments/notes) and skip if env already set.
            if _jk in _json_cfg and _ek not in os.environ:
                _val = _json_cfg[_jk]
                if _val is not None:
                    # Python booleans → lowercase strings so env_bool() parses them correctly.
                    os.environ[_ek] = str(_val).lower() if isinstance(_val, bool) else str(_val)
        # browser_args: list — handled outside _KEY_MAP to preserve type.
        if isinstance(_json_cfg.get("browser_args"), list):
            _json_cfg_browser_args = [str(a) for a in _json_cfg["browser_args"] if str(a).strip()]
        # custom_modules_dirs: deprecated alias for custom_controls_dirs.
        if isinstance(_json_cfg.get("custom_modules_dirs"), list):
            _json_cfg_custom_modules_dirs = [str(d).strip() for d in _json_cfg["custom_modules_dirs"] if str(d).strip()]
        if isinstance(_json_cfg.get("custom_controls_dirs"), list):
            _json_cfg_custom_controls_dirs = [
                str(d).strip() for d in _json_cfg["custom_controls_dirs"] if str(d).strip()
            ]
    except (json.JSONDecodeError, OSError) as _cfg_err:
        import warnings

        warnings.warn(f"ManulEngine: could not load config file '{_CONFIG_PATH}': {_cfg_err}", stacklevel=2)

# ── Core ──────────────────────────────────────────────────────────────────────
HEADLESS_MODE = env_bool("MANUL_HEADLESS")
_VALID_BROWSERS = ("chromium", "electron")
_raw_browser = (os.getenv("MANUL_BROWSER") or "chromium").strip().lower()
BROWSER: str = _raw_browser if _raw_browser in _VALID_BROWSERS else "chromium"
# MANUL_BROWSER_ARGS: comma-or-space separated extra flags, e.g. "--disable-gpu, --lang=uk"
# Env var always wins — even an empty value means "no extra args" (overrides JSON).
if "MANUL_BROWSER_ARGS" in os.environ:
    _env_browser_args = os.environ["MANUL_BROWSER_ARGS"].strip()
    if _env_browser_args:
        import re as _re_args

        BROWSER_ARGS: "list[str]" = [a.strip() for a in _re_args.split(r"[,\s]+", _env_browser_args) if a.strip()]
    else:
        # Explicitly set but empty → clear any JSON browser_args.
        BROWSER_ARGS: "list[str]" = []
else:
    BROWSER_ARGS = _json_cfg_browser_args

# channel: Playwright browser channel (e.g. "chrome", "chrome-beta", "msedge").
# Allows testing against branded browser builds instead of the bundled Chromium.
_raw_channel = (os.getenv("MANUL_CHANNEL") or "").strip()
CHANNEL: "str | None" = _raw_channel or None
# executable_path: absolute path to a custom browser executable (e.g. Electron).
_raw_executable_path = (os.getenv("MANUL_EXECUTABLE_PATH") or "").strip()
EXECUTABLE_PATH: "str | None" = _raw_executable_path or None

TIMEOUT = int(os.getenv("MANUL_TIMEOUT", "5000"))
NAV_TIMEOUT = int(os.getenv("MANUL_NAV_TIMEOUT", "30000"))

# ── Persistent controls cache ────────────────────────────────────────────────
CONTROLS_CACHE_ENABLED = env_bool("MANUL_CONTROLS_CACHE_ENABLED", "True")
_cache_dir_raw = os.getenv("MANUL_CONTROLS_CACHE_DIR", "cache")
_cache_dir_path = Path(_cache_dir_raw)
# Relative paths are always resolved against CWD (the user's project root),
# not against the package installation directory.
if not _cache_dir_path.is_absolute():
    _cache_dir_path = Path.cwd() / _cache_dir_path
CONTROLS_CACHE_DIR = str(_cache_dir_path.resolve())

# ── In-session semantic cache (learned_elements) ──────────────────────────────
# Remembers resolved elements within a single run (+200,000 score boost).
# Separate from the persistent controls cache — resets every time ManulEngine starts.
SEMANTIC_CACHE_ENABLED = env_bool("MANUL_SEMANTIC_CACHE_ENABLED", "True")

# ── Page Tracker & Auto-Annotator ────────────────────────────────────────────
# PAGE_REGISTRY maps URL patterns (regex strings) to human-readable page names.
# Keys are matched via re.search() against the FULL URL (scheme + domain + path);
# first match wins.  Unknown URLs are auto-added as "Auto: domain/path" placeholders.
#
# Storage layout (since 0.0.9.30):
#   <project>/pages/<safe_netloc>.json    — one file per site (the canonical form)
#
# Each fragment uses one of two shapes (auto-detected):
#   Lean:    { "site": "https://example.com/", "Domain": "Example", "/login": "Login" }
#            ("site" is optional: the filename stem doubles as a fallback when the
#            file contains no patterns yet, but the field is recommended.)
#   Wrapped: { "https://example.com/": { "Domain": "Example", "/login": "Login" } }
#
# The legacy flat file ``<project>/pages.json`` is no longer read or written.
# Run ``manul pages migrate`` once to split a pre-0.0.9.30 ``pages.json`` into
# ``pages/<site>.json`` fragments.
_PAGES_DIR_PATH: Path = Path(os.getenv("MANUL_PAGES_DIR", "").strip() or (Path.cwd() / "pages"))
if not _PAGES_DIR_PATH.is_absolute():
    _PAGES_DIR_PATH = (Path.cwd() / _PAGES_DIR_PATH).resolve()


def _safe_site_filename(site_root: str) -> str:
    """Return ``<safe_netloc>.json`` for *site_root*. Used by auto-fill."""
    from urllib.parse import urlparse as _urlparse_sf

    netloc = _urlparse_sf(site_root).netloc or site_root
    safe = _re.sub(r"[^0-9A-Za-z._-]", "_", netloc).strip("_") or "site"
    return f"{safe}.json"


def _normalise_fragment(raw: dict, *, source: Path) -> dict[str, dict[str, str]]:
    """Turn a single ``pages/*.json`` payload into ``{site_root: {pattern: name}}``.

    Detects the lean vs. wrapped form by inspecting top-level values.
    Silently drops malformed entries; emits a single ``warnings.warn`` per file
    when nothing recoverable is present.
    """
    import warnings as _warnings

    out: dict[str, dict[str, str]] = {}
    if not isinstance(raw, dict) or not raw:
        return out

    # Wrapped form: every top-level value is a dict → keyed by site root URL.
    if all(isinstance(v, dict) for v in raw.values()):
        for site_key, site_val in raw.items():
            site_key = str(site_key).strip()
            if site_key and isinstance(site_val, dict):
                out[site_key] = {str(k): str(v) for k, v in site_val.items()}
        return out

    # Lean form: top-level values are strings (patterns → names).  Site root
    # comes from the explicit "site" field, falling back to the filename stem
    # when it looks like a URL (e.g. saved manually as "https___example_com.json").
    site = str(raw.get("site", "")).strip()
    if not site:
        # Without an explicit site field we cannot place the fragment.  Emit a
        # diagnostic and skip — refusing to silently merge into the wrong key.
        _warnings.warn(
            f"ManulEngine: '{source}' has no 'site' field and no wrapped site key; "
            f'add `"site": "https://your.site/"` at the top of the file.',
            stacklevel=2,
        )
        return out
    fields = {str(k): str(v) for k, v in raw.items() if k != "site"}
    if fields:
        out[site] = fields
    return out


def _load_pages_dir(pages_dir: Path) -> dict[str, dict[str, str]]:
    """Merge every ``pages_dir/*.json`` fragment into a single registry."""
    import warnings as _warnings

    merged: dict[str, dict[str, str]] = {}
    if not pages_dir.is_dir():
        return merged
    for fragment_path in sorted(pages_dir.glob("*.json")):
        try:
            with open(fragment_path, encoding="utf-8") as _pf:
                raw = json.load(_pf)
        except (json.JSONDecodeError, OSError) as exc:
            _warnings.warn(f"ManulEngine: could not load '{fragment_path}': {exc}", stacklevel=2)
            continue
        for site_key, site_val in _normalise_fragment(raw, source=fragment_path).items():
            existing = merged.setdefault(site_key, {})
            existing.update(site_val)  # later fragments override earlier ones for the same key
    return merged


# PAGE_REGISTRY: nested dict — { site_root_url: { pattern_or_"Domain": name } }
# Loaded by merging every JSON fragment in _PAGES_DIR_PATH at module import.
PAGE_REGISTRY: dict[str, dict[str, str]] = _load_pages_dir(_PAGES_DIR_PATH)

# Auto-create the pages/ directory in CWD so the user has a ready-made
# place for new fragments after the first auto-fill.
try:
    _PAGES_DIR_PATH.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

AUTO_ANNOTATE: bool = env_bool("MANUL_AUTO_ANNOTATE")

# ── Retries & Reporting ──────────────────────────────────────────────────────
try:
    RETRIES: int = max(0, int(os.getenv("MANUL_RETRIES", "0")))
except ValueError:
    RETRIES = 0
_VALID_SCREENSHOT = ("on-fail", "always", "none")
_raw_screenshot = (os.getenv("MANUL_SCREENSHOT") or "on-fail").strip().lower()
SCREENSHOT: str = _raw_screenshot if _raw_screenshot in _VALID_SCREENSHOT else "on-fail"
HTML_REPORT: bool = env_bool("MANUL_HTML_REPORT")
EXPLAIN_MODE: bool = env_bool("MANUL_EXPLAIN")

# ── Verify retry limit ──────────────────────────────────────────────────────
# Maximum number of polling retries for VERIFY steps (default 15 ≈ 15-22 seconds).
try:
    VERIFY_MAX_RETRIES: int = max(1, int(os.getenv("MANUL_VERIFY_MAX_RETRIES", "15")))
except ValueError:
    VERIFY_MAX_RETRIES = 15

# ── Custom control directories ──────────────────────────────────────────────
# custom_controls_dirs is the canonical config key. custom_modules_dirs remains
# as a backward-compatible alias for existing projects.
_raw_custom_controls_dirs = os.getenv("MANUL_CUSTOM_CONTROLS_DIRS", "").strip()
_env_custom_controls_dirs: "list[str]" = (
    [part.strip() for part in _raw_custom_controls_dirs.split(",") if part.strip()] if _raw_custom_controls_dirs else []
)
_raw_custom_modules_dirs = os.getenv("MANUL_CUSTOM_MODULES_DIRS", "").strip()
_env_custom_modules_dirs: "list[str]" = (
    [part.strip() for part in _raw_custom_modules_dirs.split(",") if part.strip()] if _raw_custom_modules_dirs else []
)
CUSTOM_CONTROLS_DIRS: "list[str]" = (
    _env_custom_controls_dirs
    or _env_custom_modules_dirs
    or _json_cfg_custom_controls_dirs
    or _json_cfg_custom_modules_dirs
    or ["controls"]
)
# Backward-compatible export for older call sites.
CUSTOM_MODULES_DIRS: "list[str]" = CUSTOM_CONTROLS_DIRS


def _auto_populate_registry(url: str) -> str:
    """Persist a placeholder entry for an unmapped *url* into ``pages/``.

    Reads the per-site fragment ``pages/<safe_netloc>.json`` (creating it when
    absent), merges in ``Domain`` + the exact URL placeholder, and writes the
    file back as the lean shape with an explicit ``"site"`` field. Existing
    user-curated entries are never overwritten.

    Returns the placeholder string generated for *url*.
    """
    from urllib.parse import urlparse as _urlparse_ap

    _up = _urlparse_ap(url)
    netloc = _up.netloc
    _slug = (netloc + _up.path).rstrip("/")
    placeholder = f"Auto: {_slug}" if _slug else f"Auto: {url}"
    site_root_auto = f"{_up.scheme}://{netloc}/" if netloc else url

    fragment_path = _PAGES_DIR_PATH / _safe_site_filename(site_root_auto)

    # 1. Read the current on-disk fragment (if any).
    site_block: dict[str, str] = {}
    fragment_site: str = site_root_auto
    if fragment_path.exists():
        try:
            with open(fragment_path, encoding="utf-8") as _rf:
                raw = json.load(_rf)
            if isinstance(raw, dict):
                # Inspect: lean form has string values + optional "site" key;
                # wrapped form has the site URL as the only top-level key.
                if all(isinstance(v, dict) for v in raw.values()) and raw:
                    # Wrapped: pull out the matching site (or first) block.
                    if site_root_auto in raw:
                        site_block = {str(k): str(v) for k, v in raw[site_root_auto].items()}
                    else:
                        first_key = next(iter(raw))
                        site_block = {str(k): str(v) for k, v in raw[first_key].items()}
                        fragment_site = str(first_key).strip() or site_root_auto
                else:
                    fragment_site = str(raw.get("site", "")).strip() or site_root_auto
                    site_block = {str(k): str(v) for k, v in raw.items() if k != "site"}
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Deep merge: never overwrite existing keys.
    if "Domain" not in site_block:
        site_block["Domain"] = placeholder
    if url not in site_block:
        site_block[url] = placeholder

    # 3. Sync the in-memory PAGE_REGISTRY so subsequent lookups see the update
    #    without another disk read.
    site_entry = PAGE_REGISTRY.setdefault(fragment_site, {})
    site_entry.update(site_block)

    # 4. Persist the lean form back to disk.
    try:
        _PAGES_DIR_PATH.mkdir(parents=True, exist_ok=True)
        payload = {"site": fragment_site, **site_block}
        with open(fragment_path, "w", encoding="utf-8") as _wf:
            json.dump(payload, _wf, indent=4, ensure_ascii=False)
            _wf.write("\n")
    except OSError:
        pass

    return placeholder


def pages_registry_mtime() -> float:
    """Return the most recent mtime across all ``pages/*.json`` fragments.

    Used by callers that cache page-name resolutions per mission and need to
    invalidate when any fragment is edited on disk. Returns 0.0 when the
    directory is missing or empty so callers can compare without a try/except.
    """
    if not _PAGES_DIR_PATH.is_dir():
        return 0.0
    latest = 0.0
    try:
        for fragment in _PAGES_DIR_PATH.glob("*.json"):
            try:
                m = fragment.stat().st_mtime
                if m > latest:
                    latest = m
            except OSError:
                continue
    except OSError:
        return 0.0
    return latest


def lookup_page_name(url: str) -> str:
    """Match *url* against PAGE_REGISTRY and return the mapped page name.

    The registry is loaded from per-site fragments under ``<project>/pages/``.
    Each fragment uses one of two shapes::

        # lean (preferred)
        { "site": "https://example.com/", "Domain": "Example", ".*/login": "Login Page" }

        # wrapped (mirrors the pre-0.0.9.30 nested format)
        { "https://example.com/": { "Domain": "Example", ".*/login": "Login Page" } }

    Matching logic:
    1. Re-read every ``pages/*.json`` fragment from disk on every call so manual
       edits are picked up within a session.
    2. Find the best-matching site block: the top-level key whose prefix is the
       longest match against the URL (longest-prefix wins, so sub-domain entries
       shadow more general ones).
    3. Within the site block, match page patterns with priority:
       a. Exact URL equality.
       b. Regex via re.search() (invalid regex falls back to substring).
       c. The special ``"Domain"`` key — returned when no page pattern matches
          but the URL belongs to this site.
    4. If no site block matches, auto-generate a placeholder, add it to the
       per-site fragment, and write that fragment back to disk.
    """
    import re as _re_lkp
    from urllib.parse import urlparse as _urlparse

    def _belongs_to_site(candidate_url: str, site_root: str) -> bool:
        candidate_parts = _urlparse(candidate_url)
        site_parts = _urlparse(site_root)
        if candidate_parts.scheme != site_parts.scheme or candidate_parts.netloc != site_parts.netloc:
            return False

        candidate_path = candidate_parts.path.rstrip("/")
        site_path = site_parts.path.rstrip("/")
        if not site_path:
            return True
        return candidate_path == site_path or candidate_path.startswith(site_path + "/")

    # ── 1. Reload registry from disk ─────────────────────────────────────────
    # Re-merge every pages/*.json fragment so manual edits and auto-populated
    # entries from previous lookups in this session are visible.
    fresh = _load_pages_dir(_PAGES_DIR_PATH)
    if fresh:
        PAGE_REGISTRY.clear()
        PAGE_REGISTRY.update(fresh)
    _live_registry: dict[str, dict[str, str]] = PAGE_REGISTRY

    # ── 2. Find the best (longest-prefix) site block ──────────────────────────
    best_site_key: str | None = None
    for site_root in _live_registry:
        if _belongs_to_site(url, site_root):
            if best_site_key is None or len(site_root) > len(best_site_key):
                best_site_key = site_root

    # ── 3. Match within the site block ───────────────────────────────────────
    if best_site_key is not None:
        pages = _live_registry[best_site_key]
        domain_name: str | None = pages.get("Domain")

        # a. Exact URL match.
        if url in pages:
            return pages[url]

        # b. Regex / substring patterns (skip the "Domain" meta-key).
        for pattern, name in pages.items():
            if pattern == "Domain":
                continue
            try:
                if _re_lkp.search(pattern, url):
                    return name
            except _re_lkp.error:
                if pattern in url:
                    return name

        # c. Nothing matched — return the domain display name as fallback.
        if domain_name:
            return domain_name

    # ── 4. No site block matched — delegate to safe read-modify-write helper ─
    return _auto_populate_registry(url)
