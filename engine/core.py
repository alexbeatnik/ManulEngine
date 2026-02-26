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
import json
import re
import ollama
from playwright.async_api import async_playwright

from . import prompts
from .helpers import substitute_memory
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
        # Resolve model-specific settings once at construction time
        self._threshold       = prompts.get_threshold(self.model, ai_threshold)
        self._executor_prompt = prompts.get_executor_prompt(self.model)

    # ── LLM helpers ───────────────────────────

    async def _llm_json(self, system: str, user: str) -> dict | None:
        """Send a system+user prompt to the local LLM and parse JSON response."""
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
    ) -> int:
        """Ask the LLM to pick the best element from scored candidates."""
        payload = [
            {
                "id":           el["id"],
                "name":         el["name"],
                "tag":          el.get("tag_name", ""),
                "role":         el.get("role", ""),
                "data_qa":      el.get("data_qa", ""),
                "html_id":      el.get("html_id", ""),
                "class_name":   el.get("class_name", ""), # <--- ДОДАНО ПІДТРИМКУ КЛАСІВ ДЛЯ ШІ
                "icon_classes": el.get("icon_classes", ""),
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
            return 0

        raw_id = obj.get("id", None)
        if raw_id is None: # fallback for generic keys
            for key in ["id", '"id"', "ID"]:
                if key in obj:
                    raw_id = obj[key]
                    break

        try:
            chosen_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            chosen_id = None

        thought = obj.get("thought", "")
        if chosen_id is not None:
            idx = next((i for i, el in enumerate(candidates) if el["id"] == chosen_id), 0)
        else:
            idx = 0
        print(f"    🎯 AI DECISION: '{candidates[idx]['name'][:40]}' — {thought}")
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

        # Genuinely ambiguous → ask the LLM
        print(f"    🧠 AI AGENT: Ambiguity detected, analysing {len(top)} candidates…")
        try:
            idx = await self._llm_select_element(step, mode, top, strategic_context)
        except Exception:
            idx = 0
        ai_choice = top[idx]

        # Anti-phantom guard — only for input/select modes
        if mode in ("input", "select") and not is_blind:
            search_terms = [t.lower() for t in search_texts]
            if target_field:
                search_terms.append(target_field.lower())
            guard_words  = set(re.findall(r'\b[a-z0-9]{2,}\b', " ".join(search_terms)))
            element_text = (
                f"{ai_choice['name']} "
                f"{ai_choice.get('html_id', '')} "
                f"{ai_choice.get('data_qa', '')} "
                f"{ai_choice.get('aria_label', '')} "
                f"{ai_choice.get('placeholder', '')}"
            ).lower()
            if guard_words and not any(w in element_text for w in guard_words):
                missing = search_texts[0] if search_texts else target_field
                print(f"    👻 ANTI-PHANTOM GUARD: AI chose '{ai_choice['name']}', "
                      f"but target '{missing}' is missing. Rejecting.")
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

            if not plan:
                await browser.close()
                return False

            ok = True
            try:
                for i, raw_step in enumerate(plan, 1):
                    step = substitute_memory(raw_step, self.memory)
                    print(f"\n[🚀 STEP {i}] {step}")
                    s_up = step.upper()

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
                        return True

                    else:
                        if not await self._execute_step(page, step, strategic_context):
                            print("    ❌ ACTION FAILED")
                            ok = False; break

            finally:
                await browser.close()

        return ok