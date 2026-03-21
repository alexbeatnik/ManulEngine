# manul_engine/cache.py
"""
Persistent controls cache mixin for ManulEngine.

Stores and retrieves successful element resolutions per-site/per-page,
enabling the engine to reuse known controls on subsequent runs.

Layout: cache/<site>/<page_slug>/controls.json
"""

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from .helpers import ContextualHint


class _ControlsCacheMixin:
    """Mixin providing persistent per-site controls cache.

    Expects the following instance attributes (set by ManulEngine.__init__):
        _controls_cache_enabled: bool
        _controls_cache_root:    Path
        _controls_cache_site:    str | None
        _controls_cache_url:     str | None
        _controls_cache_path:    Path | None
        _controls_cache_data:    dict[str, dict]
    """

    # ── Key helpers ───────────────────────────────────────────────────

    def _legacy_control_cache_key(self, mode: str, search_texts: list[str], target_field: str | None) -> str:
        payload = {
            "mode": str(mode or "").lower(),
            "search_texts": [str(t).lower().strip() for t in (search_texts or []) if str(t).strip()],
            "target_field": str(target_field or "").lower().strip() or None,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _control_cache_key(
        self,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        contextual_hint: ContextualHint | None = None,
    ) -> str:
        hint_kind = getattr(contextual_hint, "kind", None)
        context_qualifier = None
        if hint_kind:
            context_qualifier = {
                "kind": str(hint_kind).lower(),
                "anchor": str(getattr(contextual_hint, "anchor", "") or "").lower().strip() or None,
                "row_text": str(getattr(contextual_hint, "row_text", "") or "").lower().strip() or None,
            }
        payload = json.loads(self._legacy_control_cache_key(mode, search_texts, target_field))
        payload["context"] = context_qualifier
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _page_site_key(self, page) -> str | None:
        try:
            parsed = urlparse(str(getattr(page, "url", "") or ""))
        except Exception:
            return None
        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            return None
        port_suffix = f":{parsed.port}" if parsed.port else ""
        host_port = f"{hostname}{port_suffix}"
        safe = re.sub(r"[^a-z0-9.-]+", "_", host_port)
        safe = safe.strip("._")
        return safe or None

    def _page_url_file_name(self, page_url: str) -> str:
        parsed = urlparse(str(page_url or ""))
        raw_path = (parsed.path or "/").strip()
        if raw_path in ("", "/"):
            slug = "root"
        else:
            slug = re.sub(r"[^a-z0-9._-]+", "_", raw_path.strip("/").lower())
            slug = slug.strip("._-") or "root"
        path_digest = hashlib.sha1((parsed.path or "/").encode("utf-8")).hexdigest()[:10]
        slug = f"{slug[:64]}__p_{path_digest}"

        # Page-object style layout:
        #   cache/<site>/<page_slug>/controls.json
        # For query/fragment variants of the same path, include a stable suffix.
        suffix = ""
        if parsed.query or parsed.fragment:
            unique_src = f"{parsed.query}|{parsed.fragment}"
            digest = hashlib.sha1(unique_src.encode("utf-8")).hexdigest()[:10]
            suffix = f"__q_{digest}"

        return f"{slug}{suffix}/controls.json"

    # ── Load / flush ──────────────────────────────────────────────────

    def _ensure_url_controls_cache_loaded(self, page) -> None:
        if not self._controls_cache_enabled:
            return
        site_key = self._page_site_key(page)
        page_url = str(getattr(page, "url", "") or "").strip()
        if not site_key:
            return
        if not page_url:
            return
        if (
            site_key == self._controls_cache_site
            and page_url == self._controls_cache_url
            and self._controls_cache_path is not None
        ):
            return

        cache_path = self._controls_cache_root / site_key / self._page_url_file_name(page_url)
        cache_data: dict[str, dict] = {}
        if cache_path.exists():
            try:
                raw = json.loads(cache_path.read_text(encoding="utf-8"))
                controls = raw.get("controls", {}) if isinstance(raw, dict) else {}
                if isinstance(controls, dict):
                    cache_data = {str(k): v for k, v in controls.items() if isinstance(v, dict)}
            except Exception:
                cache_data = {}

        self._controls_cache_site = site_key
        self._controls_cache_url = page_url
        self._controls_cache_path = cache_path
        self._controls_cache_data = cache_data

    def _flush_url_controls_cache(self) -> None:
        if not self._controls_cache_enabled:
            return
        if not self._controls_cache_site or not self._controls_cache_url or self._controls_cache_path is None:
            return
        payload = {
            "version": 1,
            "site": self._controls_cache_site,
            "url": self._controls_cache_url,
            "controls": self._controls_cache_data,
        }
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        self._controls_cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._controls_cache_path.with_name(
            f"{self._controls_cache_path.name}.tmp-{time.time_ns()}"
        )
        try:
            tmp_path.write_text(serialized, encoding="utf-8")
            tmp_path.replace(self._controls_cache_path)
        except (OSError, ValueError, TypeError) as err:
            print(f"    ⚠️  CONTROL CACHE: failed to flush cache file: {err}")
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError as cleanup_err:
                print(f"    ⚠️  CONTROL CACHE: failed to remove temp file: {cleanup_err}")

    # ── Persist / match / resolve ─────────────────────────────────────

    def _persist_control_cache_entry(
        self,
        *,
        page,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        contextual_hint: ContextualHint | None = None,
        element: dict,
    ) -> None:
        if not self._controls_cache_enabled:
            return
        self._ensure_url_controls_cache_loaded(page)
        if not self._controls_cache_site:
            return

        key = self._control_cache_key(mode, search_texts, target_field, contextual_hint)
        new_entry = {
            "name": str(element.get("name", "")),
            "tag_name": str(element.get("tag_name", "")),
            "xpath": str(element.get("xpath", "")),
            "html_id": str(element.get("html_id", "")),
            "data_qa": str(element.get("data_qa", "")),
            "aria_label": str(element.get("aria_label", "")),
            "placeholder": str(element.get("placeholder", "")),
        }
        old_entry = self._controls_cache_data.get(key)
        if old_entry == new_entry:
            return

        self._controls_cache_data[key] = new_entry
        self._flush_url_controls_cache()

    def _match_cached_control(self, entry: dict, candidates: list[dict]) -> dict | None:
        if not entry or not candidates:
            return None

        def _norm(value: object) -> str:
            return str(value or "").strip().lower()

        for field in ("html_id", "data_qa", "xpath"):
            expected = _norm(entry.get(field, ""))
            if not expected:
                continue
            for el in candidates:
                if _norm(el.get(field, "")) == expected:
                    return el

        expected_name = _norm(entry.get("name", ""))
        expected_tag = _norm(entry.get("tag_name", ""))
        if expected_name and expected_tag:
            for el in candidates:
                if _norm(el.get("name", "")) == expected_name and _norm(el.get("tag_name", "")) == expected_tag:
                    return el

        expected_aria = _norm(entry.get("aria_label", ""))
        if expected_aria:
            for el in candidates:
                if _norm(el.get("aria_label", "")) == expected_aria:
                    return el

        return None

    def _resolve_from_control_cache(
        self,
        *,
        page,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        contextual_hint: ContextualHint | None = None,
        candidates: list[dict],
    ) -> dict | None:
        if not self._controls_cache_enabled:
            return None
        self._ensure_url_controls_cache_loaded(page)
        if not self._controls_cache_site:
            return None

        key = self._control_cache_key(mode, search_texts, target_field, contextual_hint)
        entry = self._controls_cache_data.get(key)
        if not isinstance(entry, dict):
            legacy_key = self._legacy_control_cache_key(mode, search_texts, target_field)
            entry = self._controls_cache_data.get(legacy_key)
        if not isinstance(entry, dict):
            return None

        matched = self._match_cached_control(entry, candidates)
        if matched is None:
            return None

        print(f"    💾 CONTROL CACHE: Reusing cached control for site '{self._controls_cache_site}'")
        return matched
