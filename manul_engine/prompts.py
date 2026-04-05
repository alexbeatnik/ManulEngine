# manul_engine/prompts.py
"""
ManulEngine configuration, thresholds, and LLM prompts.

Reads settings from manul_engine_configuration.json (repo root) or environment
variables. Environment variables (MANUL_* prefix) always win over the JSON file.
All values can also be overridden in code via ManulEngine(model=..., ai_threshold=...).

Exports:
    DEFAULT_MODEL, HEADLESS_MODE, TIMEOUT, NAV_TIMEOUT — core settings
    get_threshold()       — model-aware confidence threshold
    get_executor_prompt() — model-size-aware executor prompt
    PLANNER_SYSTEM_PROMPT — planner system prompt
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
    "model":                  "MANUL_MODEL",
    "headless":               "MANUL_HEADLESS",
    "browser":                "MANUL_BROWSER",
    "timeout":                "MANUL_TIMEOUT",
    "nav_timeout":            "MANUL_NAV_TIMEOUT",
    "ai_threshold":           "MANUL_AI_THRESHOLD",
    "ai_always":              "MANUL_AI_ALWAYS",
    "ai_policy":              "MANUL_AI_POLICY",
    "controls_cache_enabled": "MANUL_CONTROLS_CACHE_ENABLED",
    "controls_cache_dir":     "MANUL_CONTROLS_CACHE_DIR",
    "semantic_cache_enabled": "MANUL_SEMANTIC_CACHE_ENABLED",
    "log_name_maxlen":        "MANUL_LOG_NAME_MAXLEN",
    "log_thought_maxlen":     "MANUL_LOG_THOUGHT_MAXLEN",
    "workers":                "MANUL_WORKERS",
    "auto_annotate":          "MANUL_AUTO_ANNOTATE",
    "channel":                "MANUL_CHANNEL",
    "executable_path":        "MANUL_EXECUTABLE_PATH",
    "retries":                "MANUL_RETRIES",
    "screenshot":             "MANUL_SCREENSHOT",
    "html_report":            "MANUL_HTML_REPORT",
    "explain_mode":           "MANUL_EXPLAIN",
    "verify_max_retries":     "MANUL_VERIFY_MAX_RETRIES",
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
            _json_cfg_custom_controls_dirs = [str(d).strip() for d in _json_cfg["custom_controls_dirs"] if str(d).strip()]
    except (json.JSONDecodeError, OSError) as _cfg_err:
        import warnings
        warnings.warn(f"ManulEngine: could not load config file '{_CONFIG_PATH}': {_cfg_err}", stacklevel=2)

# ── Core ──────────────────────────────────────────────────────────────────────
# If MANUL_MODEL is unset or empty, DEFAULT_MODEL is None — AI is fully disabled.
DEFAULT_MODEL: "str | None" = os.getenv("MANUL_MODEL") or None
HEADLESS_MODE = env_bool("MANUL_HEADLESS")
_VALID_BROWSERS = ("chromium", "firefox", "webkit", "electron")
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

TIMEOUT       = int(os.getenv("MANUL_TIMEOUT",     "5000"))
NAV_TIMEOUT   = int(os.getenv("MANUL_NAV_TIMEOUT", "30000"))

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
# _PAGES_WRITE_PATH — always CWD/pages.json (the user's project root); all writes
#   go here, and it is auto-created if absent so the user can start editing it.
# _PAGES_READ_PATH  — CWD/pages.json when it exists, otherwise the package root
#   (useful when running from the ManulEngine dev repo without a local copy).
_PAGES_WRITE_PATH: Path = Path.cwd() / "pages.json"
_PAGES_READ_PATH:  Path = (
    _PAGES_WRITE_PATH if _PAGES_WRITE_PATH.exists() else _REPO_ROOT / "pages.json"
)

# PAGE_REGISTRY: nested dict — { site_root_url: { pattern_or_"Domain": name } }
# Supports multiple sites.  The top-level key is the site root URL (prefix match).
PAGE_REGISTRY: dict[str, dict[str, str]] = {}
if _PAGES_READ_PATH.exists():
    try:
        with open(_PAGES_READ_PATH, encoding="utf-8") as _pf:
            _pages_raw = json.load(_pf)
        if isinstance(_pages_raw, dict):
            for _site_key, _site_val in _pages_raw.items():
                _site_key = str(_site_key).strip()
                if not _site_key:
                    continue
                if isinstance(_site_val, dict):
                    PAGE_REGISTRY[_site_key] = {str(k): str(v) for k, v in _site_val.items()}
    except (json.JSONDecodeError, OSError) as _pages_err:
        import warnings as _warnings
        _warnings.warn(f"ManulEngine: could not load pages file '{_PAGES_READ_PATH}': {_pages_err}", stacklevel=2)

# Auto-create pages.json in CWD if it doesn't exist anywhere, so the user has
# a ready-made file to populate after the first run.
if not _PAGES_WRITE_PATH.exists():
    try:
        _PAGES_WRITE_PATH.write_text("{}\n", encoding="utf-8")
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
_env_custom_controls_dirs: "list[str]" = [
    part.strip() for part in _raw_custom_controls_dirs.split(",") if part.strip()
] if _raw_custom_controls_dirs else []
_raw_custom_modules_dirs = os.getenv("MANUL_CUSTOM_MODULES_DIRS", "").strip()
_env_custom_modules_dirs: "list[str]" = [
    part.strip() for part in _raw_custom_modules_dirs.split(",") if part.strip()
] if _raw_custom_modules_dirs else []
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
    """Safe read-modify-write of pages.json for an unmapped URL.

    Always reads from _PAGES_WRITE_PATH before writing so that any entries
    accumulated since module load (by other lookups or manual edits) are never
    clobbered.  Only adds keys that are not already present (deep merge).

    Returns the placeholder string generated for *url*.
    """
    from urllib.parse import urlparse as _urlparse_ap
    _up = _urlparse_ap(url)
    netloc = _up.netloc
    _slug = (netloc + _up.path).rstrip("/")
    placeholder = f"Auto: {_slug}" if _slug else f"Auto: {url}"
    site_root_auto = f"{_up.scheme}://{netloc}/" if netloc else url

    # 1. Read the current on-disk state from the definitive write target.
    registry: dict[str, dict[str, str]] = {}
    if _PAGES_WRITE_PATH.exists():
        try:
            with open(_PAGES_WRITE_PATH, encoding="utf-8") as _rf:
                _raw = json.load(_rf)
            if isinstance(_raw, dict):
                for _sk, _sv in _raw.items():
                    _sk = str(_sk).strip()
                    if _sk and isinstance(_sv, dict):
                        registry[_sk] = {str(k): str(v) for k, v in _sv.items()}
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Deep merge: never overwrite existing keys.
    if site_root_auto not in registry:
        # New site block: persist both the domain-level label and the specific URL.
        registry[site_root_auto] = {"Domain": placeholder, url: placeholder}
    else:
        # Site block exists; backfill Domain/URL entries only if they are missing.
        site_block = registry[site_root_auto]
        if "Domain" not in site_block:
            site_block["Domain"] = placeholder
        if url not in site_block:
            site_block[url] = placeholder

    # 3. Sync the in-memory PAGE_REGISTRY so subsequent lookups in this session
    #    see the latest state without another disk read.
    PAGE_REGISTRY.clear()
    PAGE_REGISTRY.update(registry)

    # 4. Write the combined state back to disk.
    try:
        with open(_PAGES_WRITE_PATH, "w", encoding="utf-8") as _wf:
            json.dump(registry, _wf, indent=4, ensure_ascii=False)
            _wf.write("\n")
    except OSError:
        pass

    return placeholder


def pages_registry_mtime() -> float:
    """Return the last-modified time of the *active* pages.json file.

    Mirrors the effective-path selection used by ``lookup_page_name()``:
    if CWD/pages.json is absent or contains only the empty placeholder
    written by auto-create (≤ 4 bytes), the package-root copy is the
    active registry and its mtime is returned instead.

    Returns 0.0 if the active file cannot be stat-ed (missing, permission
    error, etc.), so callers can safely compare without a try/except.
    """
    try:
        effective = _PAGES_WRITE_PATH if _PAGES_WRITE_PATH.stat().st_size > 4 else _PAGES_READ_PATH
    except OSError:
        effective = _PAGES_READ_PATH
    try:
        return effective.stat().st_mtime
    except OSError:
        return 0.0


def lookup_page_name(url: str) -> str:
    """Match *url* against PAGE_REGISTRY and return the mapped page name.

    pages.json uses a nested format::

        {
          "https://example.com/": {
            "Domain": "Example Site",
            ".*/login": "Login Page",
            "https://example.com/dashboard": "Dashboard"
          }
        }

    Matching logic:
    1. Re-read pages.json from disk on every call (picks up manual edits instantly).
    2. Find the best-matching site block: the top-level key whose prefix is the
       longest match against the URL (longest-prefix wins, so sub-domain entries
       shadow more general ones).
    3. Within the site block, match page patterns with priority:
       a. Exact URL equality.
       b. Regex via re.search() (invalid regex falls back to substring).
       c. The special ``"Domain"`` key — returned when no page pattern matches
          but the URL belongs to this site.
    4. If no site block matches, auto-generate a placeholder, add it as a new
       site entry, and write it back to pages.json.
    """
    import re as _re_lkp
    from urllib.parse import urlparse as _urlparse

    def _belongs_to_site(candidate_url: str, site_root: str) -> bool:
        candidate_parts = _urlparse(candidate_url)
        site_parts = _urlparse(site_root)
        if (
            candidate_parts.scheme != site_parts.scheme
            or candidate_parts.netloc != site_parts.netloc
        ):
            return False

        candidate_path = candidate_parts.path.rstrip("/")
        site_path = site_parts.path.rstrip("/")
        if not site_path:
            return True
        return candidate_path == site_path or candidate_path.startswith(site_path + "/")

    # ── 1. Reload registry from disk ─────────────────────────────────────────
    # Always prefer _PAGES_WRITE_PATH (CWD) when it exists — it accumulates all
    # auto-populated entries from previous lookups.  Fall back to the package-root
    # copy only when CWD has no file at all (fresh checkout without a local copy).
    _live_registry: dict[str, dict[str, str]] = PAGE_REGISTRY
    # Prefer _PAGES_WRITE_PATH (CWD) when it has real content; an empty file
    # produced by the auto-create block at module load time is treated as absent
    # so the richer package/repo copy stays in effect until the user (or
    # _auto_populate_registry) writes actual entries.
    try:
        _cwd_populated = _PAGES_WRITE_PATH.stat().st_size > 4
    except OSError:
        _cwd_populated = False
    _effective_read_path = _PAGES_WRITE_PATH if _cwd_populated else _PAGES_READ_PATH
    if _effective_read_path.exists():
        try:
            with open(_effective_read_path, encoding="utf-8") as _rf:
                _raw = json.load(_rf)
            if isinstance(_raw, dict):
                _parsed_reg: dict[str, dict[str, str]] = {}
                for _sk, _sv in _raw.items():
                    _sk = str(_sk).strip()
                    if _sk and isinstance(_sv, dict):
                        _parsed_reg[_sk] = {str(k): str(v) for k, v in _sv.items()}
                PAGE_REGISTRY.clear()
                PAGE_REGISTRY.update(_parsed_reg)
                _live_registry = PAGE_REGISTRY
        except (json.JSONDecodeError, OSError):
            pass

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

# ── AI control switches ──────────────────────────────────────────────────────
# When enabled, ALL element resolution decisions go through the LLM picker.
AI_ALWAYS = env_bool("MANUL_AI_ALWAYS")

# Policy for how the LLM should treat heuristic scores when selecting.
# - prior  (default): score is a hint/prior; model may override with a clear reason.
# - strict          : enforce best score deterministically (useful for synthetic/id-strict tests).
AI_POLICY = os.getenv("MANUL_AI_POLICY", "prior").strip().lower()
if AI_POLICY not in ("prior", "strict"):
    AI_POLICY = "prior"

# ── Confidence threshold ───────────────────────────────────────────────────────

_env_threshold  = os.getenv("MANUL_AI_THRESHOLD")
ENV_AI_THRESHOLD: "int | None" = int(_env_threshold) if _env_threshold else None


def _threshold_for_model(model_name: "str | None") -> int:
    """
    Auto-derive LLM confidence threshold from model parameter count.
    Returns 0 (disable AI) when model_name is None.

        None    →    0  (heuristics-only mode)
        < 1 b   →  500
        1–4 b   →  750
        5–9 b   → 1 000
       10–19 b  → 1 500
       20 b+    → 2 000
    """
    if not model_name:
        return 0
    m = _re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    if not m:
        return 500
    size = float(m.group(1))
    if   size < 1:    return 500
    elif size < 5:    return 750
    elif size < 10:   return 1_000
    elif size < 20:   return 1_500
    else:             return 2_000


def get_threshold(model_name: "str | None", custom_threshold: "int | None" = None) -> int:
    """
    Priority:
      1. custom_threshold  (passed directly to ManulEngine)
      2. MANUL_AI_THRESHOLD in config / env
      3. 0 when model_name is None (heuristics-only mode)
      4. Auto-calculated from model size
    """
    if custom_threshold is not None:
        return custom_threshold
    if ENV_AI_THRESHOLD is not None:
        return ENV_AI_THRESHOLD
    return _threshold_for_model(model_name)  # returns 0 when model_name is None


# ── Planner prompt ─────────────────────────────────────────────────────────────
PLANNER_SYSTEM_PROMPT = """\
You are a QA Automation Planner for a browser agent.
Your ONLY job: convert the user's task into a strict, ordered JSON step list.

RULES:
- Copy every step VERBATIM. Do NOT paraphrase, merge, or skip any step.
- Every step must be a single, atomic browser instruction.
- Preserve all quoted values, variable placeholders ({like_this}), and URLs exactly.
- Preserve deterministic DSL qualifiers exactly when they appear: `NEAR 'Anchor'`, `ON HEADER`, `ON FOOTER`, `INSIDE 'Container' row with 'Text'`.
- When the task clearly describes repeated controls, header/footer actions, or row-specific actions, emit the appropriate contextual qualifier instead of inventing selectors or paraphrasing away the context.
- Return ONLY valid JSON — no markdown, no comments, no prose.

OUTPUT FORMAT:
{"steps": ["1. Step one", "2. Step two", "..."]}
"""

# ── Executor prompts (model-size aware) ───────────────────────────────────────

_RULES_CORE = """\
Each element candidate has:
    id              – integer (RETURN THIS EXACT ID)
    score           – integer heuristic rank (HIGHER IS BETTER; treat as a PRIOR)
    name            – visible text / aria-label / "Context -> element text"
    tag             – HTML tag (input, button, a, select, textarea, div, etc.)
    input_type      – for <input>, the type (text/password/email/checkbox/radio/submit/...)
    role            – ARIA role (button, checkbox, textbox, combobox, etc.)
    data_qa         – Test IDs (extremely strong signal)
    html_id         – HTML id attribute
    class_name      – HTML classes (important for inferring intent)
    icon_classes    – CSS classes for icons (e.g., "fa search")
    aria_label      – aria-label/title (often the real label for icon buttons)
    placeholder     – placeholder/data-placeholder/aria-placeholder
    disabled        – boolean
    aria_disabled   – string ("true"/"false"/"")
    is_select       – boolean (native <select>)
    contenteditable – boolean
    is_shadow       – boolean

The STEP text may also contain deterministic contextual qualifiers:
    NEAR 'Anchor'                      – prefer the candidate nearest to the resolved anchor element
    ON HEADER                          – prefer candidates in header/nav ancestry or top-of-page region
    ON FOOTER                          – prefer candidates in footer ancestry or bottom-of-page region
    INSIDE 'Container' row with 'Text' – prefer candidates inside the resolved row/container subtree

CRITICAL RULES (Apply strictly in this order):
1. JSON ONLY: Return ONLY valid JSON. No markdown, no extra text. Format: {"id": 123, "thought": "reasoning"}
2. EXACT MATCH WINS: An exact match in `name`, `data_qa`, or `aria_label` ALWAYS beats a partial match.
3. USE SCORE AS A PRIOR (NOT A SHACKLE):
    - Prefer higher `score` when candidates are otherwise comparable.
    - You MAY choose a lower-score candidate only if you can state a clear disqualifying reason for the higher-score one
      (wrong element type for the requested mode, disabled/aria-disabled, wrong checkbox/radio alignment, etc.).
    - If scores tie, choose the first one in the list.
    - Note: In strict test mode a separate policy may enforce max-score determinism.
4. MATCH THE ACTION TO THE ELEMENT TYPE:
        - "Fill/Type" -> MUST prefer `tag=input`, `tag=textarea`, or `contenteditable=true`.
            If `tag=input`, prefer the right `input_type` (password/email/search/number/etc.).
        - "Check/Uncheck" -> MUST prefer `input_type=checkbox` or `role=checkbox`. NEVER pick a generic button.
        - "Select from dropdown" -> Prefer `is_select=true` / `tag=select` / `role=combobox`.
            If there is no native select, pick the most dropdown-like candidate (class/id contains drop/select/combo).
        - "Click link" -> MUST prefer `tag=a` or `role=link`.
        - "Click button" -> MUST prefer `tag=button`, `role=button`, or `input_type=submit`.
5. DEV CONVENTIONS (CRITICAL): Read `html_id` and `class_name` to infer the real element type if `tag` is generic (like div/span):
   - `btn` / `button` -> It acts as a button.
   - `chk` / `checkbox` -> It acts as a checkbox.
   - `rad` / `radio` -> It acts as a radio button.
   - `sel` / `drop` / `cmb` -> It acts as a select/dropdown.
   - `inp` / `txt` / `field` -> It acts as an input field.
6. CONTEXT MATTERS: If the step says "in Shipping", pick the element whose `name` contains that context (e.g., "Shipping -> First Name").
7. DATA-QA / TEST-ID: If `data_qa` closely matches the target text, it is almost certainly the correct choice.
8. PASSWORDS: If the step mentions "password" or "secret", heavily prefer `input_type=password`.
9. ICONS AND FORMATTING: For media or text editors (e.g., "Fullscreen", "Theater mode", "Underline"), if there is a button with an empty name or a weird symbol, it is highly likely the correct tool. DO NOT REJECT IT.
10. DISABLED: Avoid `disabled=true` or `aria_disabled="true"` unless the step is about verifying disabled state.
11. SHADOW DOM: If you see `is_shadow=true` or the name contains `[SHADOW_DOM]` and it matches the target, prefer it.
12. BEWARE TRAPS: DO NOT pick elements with "honeypot", "spam", or "hidden" in their names/IDs unless explicitly asked.
13. CONTEXTUAL QUALIFIERS ARE STRONG SIGNALS: If the step includes `NEAR`, `ON HEADER`, `ON FOOTER`, or `INSIDE ... row with ...`, treat that qualifier as intentional deterministic context. Prefer candidates that satisfy it instead of drifting to a semantically similar control elsewhere.
14. DO NOT INVENT SELECTORS OR EXTRA LOGIC: Choose only from the provided candidates and the explicit step text. Never imagine hidden structure that is not present in the candidate list.
15. TIE-BREAKER: If multiple elements look equally correct, pick the one with the lowest `id`.
16. REJECTION (LAST RESORT): Return `null` ONLY if the target is completely missing and there is no plausible element of the correct type.
    WARNING: If the step asks for a formatting tool (like 'Underline') or a player control (like 'Fullscreen') and you see an unlabeled/icon button, ASSUME IT IS THE TARGET AND PICK IT!
"""

# Tiny (< 1 b) — minimal tokens
EXECUTOR_PROMPT_TINY = """\
You are a UI element picker for browser automation.
CONTEXT: {strategic_context}

""" + _RULES_CORE + """
Return ONLY: {"id": <integer or null>, "thought": "<one sentence>"}
"""

# Small (1–6 b)
EXECUTOR_PROMPT_SMALL = """\
You are a precise UI Element Selector for a browser automation agent.
CONTEXT: {strategic_context}

Given a browser STEP and a list of UI ELEMENTS, return the id of the best match.

""" + _RULES_CORE + """
OUTPUT (nothing else): {"id": <integer or null>, "thought": "one sentence"}
"""

# Large (7 b+) — with worked examples
EXECUTOR_PROMPT_LARGE = """\
You are a precise UI Element Selector for a browser automation agent.
CONTEXT: {strategic_context}

Given a browser STEP and a list of UI ELEMENTS, return the `id` of the best match.

""" + _RULES_CORE + """
EXAMPLES:
  Step: "Fill 'Email' in Billing" → Pick element with name "Billing -> Email input text", NOT "Shipping -> Email".
  Step: "Check 'I agree'" → Pick type=checkbox, or class_name containing 'chk'.
  Step: "Click 'Color Red'" → Pick element with aria-label="Color Red" or similar.
  Step: "Select 'Ukraine' from 'Country'" → Pick tag=select containing 'Country'.
  Step: "Fill 'Message Body'" → Pick element with contenteditable=true or tag=textarea.
    Step: "Click the 'Search' button NEAR 'Products'" → Prefer the candidate nearest the resolved 'Products' anchor, not another 'Search' elsewhere.
    Step: "Click the 'Login' button ON HEADER" → Prefer the header/nav login action, not a repeated CTA lower on the page.
    Step: "Click the 'Privacy Policy' link ON FOOTER" → Prefer the footer/legal link cluster.
    Step: "Click the 'Edit' button INSIDE 'Users' row with 'John Doe'" → Prefer the button inside John Doe's row, not another Edit button.

OUTPUT (strictly valid JSON, no markdown):
{"id": <integer or null>, "thought": "one sentence"}
"""

def get_executor_prompt(model_name: "str | None") -> str:
    """Return executor prompt sized for the model's parameter count."""
    if not model_name:
        return EXECUTOR_PROMPT_TINY  # fallback; won't be called in heuristics-only mode
    m = _re.search(r'(\d+(?:\.\d+)?)\s*b', model_name.lower())
    size = float(m.group(1)) if m else 0.5
    if   size < 1:  return EXECUTOR_PROMPT_TINY
    elif size < 7:  return EXECUTOR_PROMPT_SMALL
    else:           return EXECUTOR_PROMPT_LARGE


# Legacy alias
EXECUTOR_SYSTEM_PROMPT = EXECUTOR_PROMPT_SMALL
