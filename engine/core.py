# engine/core.py
"""
ManulEngine — the main browser automation class.

Orchestrates the full automation pipeline:
  1. Parse mission into steps (LLM planner or numbered list)
  2. For each step, detect interaction mode and resolve the target element
  3. Delegate action execution to the _ActionsMixin (engine/actions.py)

Element resolution uses a multi-stage pipeline:
  DOM snapshot (JS) → heuristic scoring → optional LLM fallback → anti-phantom guard

Inherits action handlers from _ActionsMixin (navigate, scroll, extract, verify,
drag-and-drop, click/type/select/hover via _execute_step).
"""

import asyncio
import datetime
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

try:
    import ollama  # type: ignore
except Exception:  # pragma: no cover
    ollama = None

from . import prompts
from .helpers import substitute_memory, compact_log_field
from .js_scripts import SNAPSHOT_JS
from .scoring import score_elements
from .actions import _ActionsMixin


class ManulEngine(_ActionsMixin):
    def __init__(
        self,
        model:          "str | None"  = None,
        headless:       "bool | None" = None,
        ai_threshold:   "int | None"  = None,
        **_kwargs,
    ):
        self.model    = model    if model    is not None else prompts.DEFAULT_MODEL
        self.headless = headless if headless is not None else prompts.HEADLESS_MODE
        self.memory:          dict = {}
        self.last_xpath:      "str | None" = None
        self.learned_elements: dict = {}        # semantic cache: cache_key → {name, tag}
        self._controls_cache_enabled = bool(getattr(prompts, "CONTROLS_CACHE_ENABLED", True))
        self._controls_cache_root = Path(str(getattr(prompts, "CONTROLS_CACHE_DIR", str(Path(__file__).resolve().parents[1] / "cache"))))
        self._controls_cache_site: str | None = None
        self._controls_cache_url: str | None = None
        self._controls_cache_path: Path | None = None
        self._controls_cache_data: dict[str, dict] = {}
        # Resolve model-specific settings once at construction time
        self._threshold       = prompts.get_threshold(self.model, ai_threshold)
        self._executor_prompt = prompts.get_executor_prompt(self.model)

    # ── Persistent controls cache ─────────────────────────────────────

    def _control_cache_key(self, mode: str, search_texts: list[str], target_field: str | None) -> str:
        payload = {
            "mode": str(mode or "").lower(),
            "search_texts": [str(t).lower().strip() for t in (search_texts or []) if str(t).strip()],
            "target_field": str(target_field or "").lower().strip() or None,
        }
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
            if tmp_path.exists():
                tmp_path.unlink()

    def _persist_control_cache_entry(
        self,
        *,
        page,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        element: dict,
    ) -> None:
        if not self._controls_cache_enabled:
            return
        self._ensure_url_controls_cache_loaded(page)
        if not self._controls_cache_site:
            return

        key = self._control_cache_key(mode, search_texts, target_field)
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
        candidates: list[dict],
    ) -> dict | None:
        if not self._controls_cache_enabled:
            return None
        self._ensure_url_controls_cache_loaded(page)
        if not self._controls_cache_site:
            return None

        key = self._control_cache_key(mode, search_texts, target_field)
        entry = self._controls_cache_data.get(key)
        if not isinstance(entry, dict):
            return None

        matched = self._match_cached_control(entry, candidates)
        if matched is None:
            return None

        print(f"    💾 CONTROL CACHE: Reusing cached control for site '{self._controls_cache_site}'")
        return matched

    # ── LLM helpers ───────────────────────────

    def _passes_anti_phantom_guard(
        self,
        *,
        mode: str,
        is_blind: bool,
        search_texts: list[str],
        target_field: str | None,
        ai_choice: dict,
    ) -> bool:
        if mode not in ("input", "select") or is_blind:
            return True

        search_terms = [t.lower() for t in search_texts]
        if target_field:
            search_terms.append(target_field.lower())

        guard_words = set(re.findall(r"\b[a-z0-9]{2,}\b", " ".join(search_terms)))
        element_text = (
            f"{ai_choice.get('name', '')} "
            f"{ai_choice.get('html_id', '')} "
            f"{ai_choice.get('data_qa', '')} "
            f"{ai_choice.get('aria_label', '')} "
            f"{ai_choice.get('placeholder', '')}"
        ).lower()

        if not guard_words or any(w in element_text for w in guard_words):
            return True

        missing = search_texts[0] if search_texts else target_field
        compact_name = compact_log_field(ai_choice.get("name", ""), "MANUL_LOG_NAME_MAXLEN")

        print(
            f"    👻 ANTI-PHANTOM GUARD: AI chose '{compact_name}', "
            f"but target '{missing}' is missing. Rejecting."
        )
        return False

    async def _llm_json(self, system: str, user: str) -> dict | None:
        """Send a system+user prompt to the local LLM and parse JSON response."""
        if ollama is None:
            print("    ⚠️  LLM unavailable: Python package 'ollama' is not installed.")
            return None
        try:
            resp = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                format="json",
            )
            raw = resp["message"]["content"]
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            return json.loads(m.group(0) if m else raw)
        except Exception as e:
            print(f"    ⚠️  LLM error: {e}")
            return None

    async def _llm_plan(self, task: str) -> list[str]:
        """Ask the LLM to decompose a free-text task into numbered steps."""
        print("    🧠 AI PLANNER: Generating mission steps...")
        obj = await self._llm_json(prompts.PLANNER_SYSTEM_PROMPT, task)
        return obj.get("steps", []) if obj else []

    async def _llm_select_element(
        self, step: str, mode: str, candidates: list[dict], strategic_context: str
    ) -> "int | None":
        """Ask the LLM to pick the best element from scored candidates."""
        payload = [
            {
                "id":           el["id"],
                "score":        int(el.get("score", 0)),
                "name":         el["name"],
                "tag":          el.get("tag_name", ""),
                "input_type":   el.get("input_type", ""),
                "role":         el.get("role", ""),
                "data_qa":      el.get("data_qa", ""),
                "html_id":      el.get("html_id", ""),
                "class_name":   el.get("class_name", ""),
                "icon_classes": el.get("icon_classes", ""),
                "aria_label":   el.get("aria_label", ""),
                "placeholder":  el.get("placeholder", ""),
                "disabled":     el.get("disabled", False),
                "aria_disabled": el.get("aria_disabled", ""),
                "is_select":    el.get("is_select", False),
                "is_shadow":    el.get("is_shadow", False),
                "contenteditable": el.get("is_contenteditable", False),
            }
            for el in candidates
        ]
        prompt = (
            f"STEP: {step}\n"
            f"MODE: {mode.upper()}\n"
            f"ELEMENTS:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        system = self._executor_prompt.replace("{strategic_context}", strategic_context)
        obj = await self._llm_json(system, prompt)
        if not obj or not isinstance(obj, dict):
            # In pure-AI mode we must not silently fall back to heuristics.
            return None if getattr(prompts, "AI_ALWAYS", False) else 0

        raw_id = obj.get("id", None)
        if raw_id is None: # fallback for generic keys
            for key in ["id", '"id"', "ID"]:
                if key in obj:
                    raw_id = obj[key]
                    break

        # ── ОБРОБКА ВІДМОВИ ШІ (REJECTION) ──
        if raw_id is None or str(raw_id).lower() == "null":
            thought = obj.get("thought", "No matching element found.")
            print(f"    🚫 AI REJECTED CANDIDATES: '{thought}'")
            return None

        try:
            chosen_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            chosen_id = None

        thought = obj.get("thought", "")
        if chosen_id is not None:
            idx = next((i for i, el in enumerate(candidates) if el["id"] == chosen_id), 0)
        else:
            idx = 0

        # Optional deterministic guard for id-strict synthetic tests.
        # When MANUL_AI_POLICY=strict, enforce best score even if the LLM picked a neighbor.
        if getattr(prompts, "AI_ALWAYS", False) and getattr(prompts, "AI_POLICY", "prior") == "strict" and candidates:
            best_idx = max(range(len(candidates)), key=lambda i: int(candidates[i].get("score", 0)))
            if int(candidates[idx].get("score", 0)) < int(candidates[best_idx].get("score", 0)):
                print(
                    f"    🧷 AI OVERRIDE (strict): enforcing best score (ai={candidates[idx].get('score', 0)} "
                    f"< best={candidates[best_idx].get('score', 0)})"
                )
                idx = best_idx
        compact_name = compact_log_field(candidates[idx].get("name", ""), "MANUL_LOG_NAME_MAXLEN")
        compact_thought = compact_log_field(thought, "MANUL_LOG_THOUGHT_MAXLEN")

        print(f"    🎯 AI DECISION: '{compact_name}' — {compact_thought}")
        return idx

    # ── Visual feedback ───────────────────────

    async def _highlight(self, page, target, color="red", bg="#ffeb3b", *, by_js_id=False):
        """Flash a coloured border around an element for visual debugging."""
        try:
            if by_js_id:
                await page.evaluate(f"window.manulHighlight({target}, '{color}', '{bg}')")
            else:
                await target.evaluate(f"""el => {{
                    const oB=el.style.border, oBg=el.style.backgroundColor;
                    el.style.border='4px solid {color}'; el.style.backgroundColor='{bg}';
                    setTimeout(()=>{{el.style.border=oB;el.style.backgroundColor=oBg;}},2000);
                }}""")
            await asyncio.sleep(0.4)
        except Exception:
            pass

    # ── DOM snapshot ──────────────────────────

    async def _snapshot(self, page, mode: str, texts: list[str]) -> list[dict]:
        """Inject SNAPSHOT_JS into the page and return a list of interactive elements."""
        return await page.evaluate(SNAPSHOT_JS, [mode, texts or []])

    # ── Scoring (delegates to scoring module) ─

    def _score_elements(
        self,
        els: list[dict],
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        is_blind: bool,
    ) -> list[dict]:
        """Score and rank elements using heuristics from scoring.py."""
        return score_elements(
            els, step, mode, search_texts, target_field, is_blind,
            learned_elements=self.learned_elements,
            last_xpath=self.last_xpath,
        )

    # ── Element resolution ────────────────────

    async def _resolve_element(
        self,
        page,
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        strategic_context: str,
        failed_ids: "set | None" = None,
    ) -> dict | None:
        """
        Locate the target element with up to 5 scroll-and-retry attempts.
        Uses heuristics first; falls back to LLM only when genuinely ambiguous.
        Returns None if nothing suitable is found.
        """
        _skip = failed_ids or set()
        is_blind = not search_texts and not target_field

        els = []
        for attempt in range(5):
            raw_els = await self._snapshot(page, mode, [t.lower() for t in search_texts])
            els = [e for e in raw_els if e["id"] not in _skip]

            if not els:
                if attempt < 4:
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(1)
                continue

            if mode == "drag":
                break

            cached_control = self._resolve_from_control_cache(
                page=page,
                mode=mode,
                search_texts=search_texts,
                target_field=target_field,
                candidates=els,
            )
            if cached_control is not None:
                return cached_control

            # Quick exact-match pass
            exact = []
            for el in els:
                name = el["name"].lower().strip()
                aria = el.get("aria_label", "").lower().strip()
                dqa  = el.get("data_qa", "").lower().strip()
                if target_field and target_field in name:
                    exact.append(el)
                    continue
                for q in search_texts:
                    q_l = q.lower().strip()
                    if ((len(q_l) <= 2 and q_l == name)
                            or (len(q_l) > 2 and q_l in name)):
                        exact.append(el)
                        break
                    if len(q_l) > 2 and (
                        q_l in aria
                        or q_l.replace(" ", "-") in dqa
                        or q_l.replace(" ", "_") in dqa
                    ):
                        exact.append(el)
                        break

            if exact:
                els = exact
                break

            if els and (is_blind or not search_texts):
                break

            if attempt < 4:
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)

        if not els:
            return None

        scored     = self._score_elements(els, step, mode, search_texts, target_field, is_blind)
        top        = scored[:8]
        best_score = top[0].get("score", 0)

        # Pure-AI mode: always ask the LLM element picker, regardless of heuristic confidence.
        if getattr(prompts, "AI_ALWAYS", False):
            print(f"    🧠 AI AGENT: Always-AI enabled, analysing {len(top)} candidates…")
            idx = await self._llm_select_element(step, mode, top, strategic_context)
            if idx is None:
                if failed_ids is not None:
                    for c in top:
                        failed_ids.add(c["id"])
                return None
            ai_choice = top[idx]

            if not self._passes_anti_phantom_guard(
                mode=mode,
                is_blind=is_blind,
                search_texts=search_texts,
                target_field=target_field,
                ai_choice=ai_choice,
            ):
                return None

            return ai_choice

        if best_score >= 20_000:
            print(f"    🧠 SEMANTIC CACHE: Reusing learned element (score {best_score})")
            return top[0]

        if best_score >= 10_000:
            print(f"    ⚡ CONTEXT MEMORY: Reusing last element (score {best_score})")
            return top[0]

        if best_score >= self._threshold:
            label = "High confidence" if best_score >= self._threshold * 2 else "Keyword"
            print(f"    ⚙️  DOM HEURISTICS: {label} match (score {best_score})")
            return top[0]

        # Explicit AI disable switch: threshold <= 0 means "never call the LLM".
        # (Useful for deterministic runs and environments without Ollama.)
        if self._threshold <= 0:
            print(f"    ⚙️  DOM HEURISTICS: AI disabled (threshold {self._threshold}); using best candidate (score {best_score})")
            return top[0]

        # Genuinely ambiguous → ask the LLM
        print(f"    🧠 AI AGENT: Ambiguity detected, analysing {len(top)} candidates…")
        try:
            idx = await self._llm_select_element(step, mode, top, strategic_context)
        except Exception:
            idx = 0
            
        if idx is None:
            if failed_ids is not None:
                for c in top:
                    failed_ids.add(c["id"])
            return None

        ai_choice = top[idx]

        if not self._passes_anti_phantom_guard(
            mode=mode,
            is_blind=is_blind,
            search_texts=search_texts,
            target_field=target_field,
            ai_choice=ai_choice,
        ):
            return None

        return ai_choice

    # ── Mission runner ────────────────────────

    async def run_mission(self, task: str, strategic_context: str = "") -> bool:
        """
        Execute a full browser automation mission.

        The task can be either a numbered step list ("1. Navigate to ... 2. Click ...")
        or a free-text description that will be decomposed by the LLM planner.
        """
        print(f"\n🐾 ManulEngine [{self.model}]  — Transparent AI")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--start-maximized"],
            )
            ctx  = await browser.new_context(no_viewport=True)
            page = await ctx.new_page()

            if re.match(r'^\s*\d+\.', task):
                plan = [s.strip() for s in re.split(r'(?=\b\d+\.\s)', task) if s.strip()]
            else:
                plan = await self._llm_plan(task)

            if not plan and not re.match(r'^\s*\d+\.', task):
                print("    ❌ No plan produced. If you're running without Ollama, provide a numbered step list.")

            if not plan:
                await browser.close()
                return False

            ok = True
            done = False
            try:
                for i, raw_step in enumerate(plan, 1):
                    step = substitute_memory(raw_step, self.memory)
                    started_at = datetime.datetime.now()
                    started_perf = time.perf_counter()
                    print(f"\n[🐾 STEP {i} @ {started_at.strftime('%H:%M:%S')}] {step}")
                    s_up = step.upper()

                    try:
                        if re.search(r'\bNAVIGATE\b', s_up):
                            if not await self._handle_navigate(page, step):
                                ok = False; break

                        elif re.search(r'\bWAIT\b', s_up):
                            n = re.search(r'(\d+)', step)
                            await asyncio.sleep(int(n.group(1)) if n else 2)

                        elif re.search(r'\bSCROLL\b', s_up):
                            await self._handle_scroll(page, step)

                        elif re.search(r'\bEXTRACT\b', s_up):
                            if not await self._handle_extract(page, step):
                                ok = False; break

                        elif re.search(r'\bVERIFY\b', s_up):
                            if not await self._handle_verify(page, step):
                                ok = False; break

                        elif re.search(r'\bDONE\b', s_up):
                            print("    🏁 MISSION ACCOMPLISHED")
                            done = True
                            break

                        else:
                            if not await self._execute_step(page, step, strategic_context):
                                print("    ❌ ACTION FAILED")
                                ok = False; break
                    finally:
                        ended_at = datetime.datetime.now()
                        duration_s = time.perf_counter() - started_perf
                        print(
                            f"    ⏱️  STEP END @ {ended_at.strftime('%H:%M:%S')} — duration {duration_s:.2f}s"
                        )

            finally:
                await browser.close()

        return True if done else ok