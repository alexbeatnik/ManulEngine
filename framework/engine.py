import asyncio
import json
import re
import ollama
from playwright.async_api import async_playwright
from . import config


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _substitute_memory(text: str, memory: dict) -> str:
    """Replace all {var} placeholders with values from memory."""
    for k, v in memory.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


def _extract_quoted(step: str, preserve_case: bool = False) -> list[str]:
    """Return all quoted strings from a step, preserving their order."""
    step = step.replace("\u2019", "'").replace("\u2018", "'")
    step = step.replace("\u201c", '"').replace("\u201d", '"')
    matches = re.findall(r'"([^"]*)"|\'([^\']*)\'', step)
    found = [m[0] if m[0] else m[1] for m in matches]
    return [x if preserve_case else x.lower() for x in found if x]


SCROLL_WAIT = 1.5
ACTION_WAIT = 2.0
NAV_WAIT    = 2.0


# ─────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────

class ManulEngine:
    def __init__(
        self,
        model:          "str | None"  = None,
        headless:       "bool | None" = None,
        ai_threshold:   "int | None"  = None,
        **_kwargs,
    ):
        self.model    = model    if model    is not None else config.DEFAULT_MODEL
        self.headless = headless if headless is not None else config.HEADLESS_MODE
        self.memory:          dict = {}
        self.last_xpath:      "str | None" = None
        self.learned_elements: dict = {}        # semantic cache: cache_key → {name, tag}
        # Resolve model-specific settings once at construction time
        self._threshold       = config.get_threshold(self.model, ai_threshold)
        self._executor_prompt = config.get_executor_prompt(self.model)

    # ── LLM ──────────────────────────────────

    async def _llm_json(self, system: str, user: str) -> dict | None:
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
        print("    🧠 AI PLANNER: Generating mission steps...")
        obj = await self._llm_json(config.PLANNER_SYSTEM_PROMPT, task)
        return obj.get("steps", []) if obj else []

    async def _llm_select_element(
        self, step: str, mode: str, candidates: list[dict], strategic_context: str
    ) -> int:
        payload = [
            {
                "id":           el["id"],
                "name":         el["name"],
                "tag":          el.get("tag_name", ""),
                "role":         el.get("role", ""),
                "data_qa":      el.get("data_qa", ""),
                "html_id":      el.get("html_id", ""),
                "icon_classes": el.get("icon_classes", ""),
            }
            for el in candidates
        ]
        prompt = (
            f"STEP: {step}\n"
            f"MODE: {mode.upper()}\n"
            f"ELEMENTS:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        system = self._executor_prompt.format(strategic_context=strategic_context)
        obj = await self._llm_json(system, prompt)
        if not obj or not isinstance(obj, dict):
            return 0

        raw_id = obj.get("id", None)
        chosen_id: int | None = None
        try:
            chosen_id = int(raw_id)
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
        return await page.evaluate(_SNAPSHOT_JS, [mode, texts or []])

    # ── Element selection ─────────────────────

    def _score_elements(
        self,
        els: list[dict],
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        is_blind: bool,
    ) -> list[dict]:
        step_l       = step.lower()
        target_words = set(re.findall(r'\b[a-z0-9]{3,}\b', step_l))

        wants_button = bool(re.search(r'\bbutton\b', step_l))
        wants_link   = bool(re.search(r'\blink\b',   step_l))
        wants_input  = bool(re.search(
            r'\bfield\b|\binput\b|\btextarea\b|\btype\b|\bfill\b', step_l
        ))

        cache_key = (mode, tuple(t.lower() for t in search_texts), target_field)
        learned   = self.learned_elements.get(cache_key)

        for el in els:
            name    = el["name"].lower()
            tag     = el.get("tag_name",    "")
            itype   = el.get("input_type",  "")
            data_qa = el.get("data_qa",     "").lower()
            html_id = el.get("html_id",     "").lower()
            icons   = el.get("icon_classes","").lower()   # "fa arrow circle right"
            aria    = el.get("aria_label",  "").lower()
            role    = el.get("role",        "").lower()
            score   = 0

            # ── Semantic cache (strongest signal) ──────────────────────────
            if learned and el["name"] == learned["name"] and tag == learned["tag"]:
                score += 20_000

            # ── Context memory (blind continuation) ────────────────────────
            if is_blind and self.last_xpath and el["xpath"] == self.last_xpath:
                score += 10_000

            # ── Explicit field / target name ───────────────────────────────
            if target_field and target_field in name:
                score += 2_000

            # ── Search text precision scoring ──────────────────────────────
            # Strip context prefix ("Section -> core name") for tighter matching.
            # Strip the " input <type>" suffix that _SNAPSHOT_JS appends to plain inputs.
            # It helps disambiguation elsewhere but hurts text-matching here.
            _itype_suffix = f" input {itype}" if itype else " input "
            name_clean = (
                name[: -len(_itype_suffix)].strip()
                if tag == "input" and itype and name.endswith(_itype_suffix)
                else name
            )
            name_core = name_clean.split(" -> ")[-1].strip() if " -> " in name_clean else name_clean
            context_prefix_raw = name_clean.split(" -> ")[0].strip().lower() if " -> " in name_clean else ""

            for t in search_texts:
                tl = t.lower().strip()
                if not tl:
                    continue

                context_prefix = context_prefix_raw
                if name_core == tl or name_clean == tl or context_prefix == tl:
                    score += 3_000
                elif name_core.startswith(tl) or name_core.endswith(tl) or context_prefix.startswith(tl):
                    score += 2_000
                elif tl in name_core:
                    extra = max(0, len(name_core.split()) - len(tl.split()))
                    score += max(200, 1_000 - extra * 150)
                elif tl in name:
                    extra = max(0, len(name.split()) - len(tl.split()))
                    score += max(100, 800 - extra * 100)
                else:
                    # ── FIX 5: word-level partial / typo tolerance ─────────
                    # Handles field names with typos ("Suggession" ≈ "suggestion")
                    # or where label words partially overlap element words.
                    t_words = set(re.findall(r'[a-z0-9]{3,}', tl))
                    n_words = set(re.findall(r'[a-z0-9]{3,}', name))
                    overlap = t_words & n_words
                    if overlap:
                        score += len(overlap) * 150
                    else:
                        # Substring of any word — e.g. "suggest" in "suggession"
                        partial = sum(
                            1 for tw in t_words
                            for nw in n_words
                            if len(tw) >= 4 and (tw in nw or nw in tw)
                        )
                        if partial:
                            score += partial * 80

                if tl in aria:    score += 800
                if tl in html_id: score += 600
                if any(w in icons for w in tl.split() if len(w) > 3):
                    score += 700

            # General word overlap between step and element
            score += sum(10 for w in target_words if w in name)
            score += sum(8  for w in target_words if len(w) > 3 and w in icons)
            score += sum(15 for w in target_words if len(w) > 3 and w in html_id)
            score += sum(12 for w in target_words if len(w) > 3 and w in aria)

            # ── FIX 4: strong icon boost for blind clicks ──────────────────
            # When step has no quoted search text and an icon class word matches
            # a step word (e.g. "arrow button" + icons "fa arrow circle right"),
            # give a large boost so icon-only buttons beat random elements.
            if is_blind and icons:
                icon_words    = set(icons.split())
                matched_icons = target_words & icon_words
                if matched_icons:
                    score += len(matched_icons) * 800   # e.g. "arrow" → +800

            # ── data-qa / data-testid match ────────────────────────────────
            # FIX 11: data-qa exact match must dominate plain text matches.
            for t in search_texts:
                t_l = t.lower().replace(" ", "-").replace("_", "-")
                if t_l and data_qa:
                    if t_l == data_qa:        score += 8_000   # exact → supreme
                    elif t_l in data_qa:      score += 5_000   # substring
                    elif data_qa in t_l:      score += 3_000   # partial
                # Word-level data-qa fallback: "confirm" and "order" both in "confirm-order"
                t_words_qa = set(re.findall(r'[a-z0-9]{3,}', t.lower()))
                dqa_words  = set(re.findall(r'[a-z0-9]{3,}', data_qa))
                qa_overlap = t_words_qa & dqa_words
                if qa_overlap and not (t_l and t_l in data_qa):
                    score += len(qa_overlap) * 1_500

            # ── Element-type flags ─────────────────────────────────────────
            is_native_button = (tag == "button"
                                or (tag == "input"
                                    and itype in ("submit", "button", "image", "reset")))
            is_real_button   = is_native_button or role == "button"
            is_real_link     = tag == "a"
            is_real_input    = ((tag in ("input", "textarea")
                                 and itype not in
                                 ("submit", "button", "image", "reset", "radio", "checkbox"))
                                or role in ("textbox", "searchbox", "spinbutton"))
            is_real_checkbox = ((tag == "input" and itype == "checkbox")
                                or role == "checkbox")
            is_real_radio    = ((tag == "input" and itype == "radio")
                                or role == "radio")

            # FIX 5 (ARIA): exact aria-label match → big bonus (not just +800)
            for t in search_texts:
                tl = t.lower().strip()
                if tl and aria:
                    if tl == aria:            score += 3_500   # exact ARIA → beats text
                    # (substring +800 already added above in the main loop)

            # FIX 15 (Disabled): skip disabled elements entirely
            # We penalise heavily so they never surface as top pick.
            if el.get("disabled", False) or el.get("aria_disabled", "") == "true":
                score -= 20_000

            # FIX 22 (Password): when typing into a password field, prefer type=password
            if wants_input and itype == "password":
                for t in search_texts:
                    if "password" in t.lower():
                        score += 2_000

            # ── Type wants/penalties ───────────────────────────────────────
            if wants_button:
                if is_native_button: score += 500  # native wins over role=button
                elif is_real_button: score += 300
                if is_real_link:     score -= 300
            if wants_link:
                if is_real_link:     score += 500
                if is_real_button:   score -= 300
            if wants_input:
                if is_real_input:    score += 500
                if is_real_button:   score -= 300

            # Select mode: strongly prefer <select> and reject checkboxes/radios
            if mode == "select":
                if el.get("is_select"):   score += 3_500
                elif is_real_checkbox:     score -= 3_000
                elif is_real_radio:        score -= 3_000

            # FIX 10 (Custom Role Checkbox): real checkbox must dominate over
            # inputs that have matching aria-label but wrong type.
            # Bonus (3500) > ARIA exact match boost (3500) on wrong type (minus penalty).
            if "checkbox" in step_l:
                if is_real_checkbox:     score += 3_500
                elif "checkbox" in name: score += 200
                else:                    score -= 3_000  # heavy penalty: wrong type
            if "radio" in step_l:
                if is_real_radio:        score += 3_500
                elif "radio" in name:    score += 200
                else:                    score -= 3_000

            # Blind-mode type hints (no search text)
            if not search_texts:
                if "dropdown" in step_l and "combobox" in name:    score += 5_000
                elif "shadow"  in step_l and "shadow"   in name:   score += 5_000
                elif "input"   in step_l and is_real_input:         score += 500
                elif "list"    in step_l \
                        and ("dropdown" in name or "combo" in name): score += 500

            el["score"] = score

        return sorted(els, key=lambda x: x.get("score", 0), reverse=True)

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

        failed_ids: optional set of element ids to skip (used by _execute_step
                    for self-healing retries; also accepted by tests calling directly).
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
                    # Also match on aria-label and data-qa so elements
                    # identified by those attributes aren't filtered out.
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

        # ── FIX 2: Anti-phantom guard — only for input/select modes ─────────
        # For clickable / locate / hover the guard caused too many false rejections
        # (Colors SELECT not found, draggable divs, table rows, etc.).
        # Typing into the wrong element is genuinely catastrophic; clicking the
        # wrong one is recoverable, so we only guard input/select.
        if mode in ("input", "select") and not is_blind:
            search_terms = [t.lower() for t in search_texts]
            if target_field:
                search_terms.append(target_field.lower())
            guard_words  = set(re.findall(r'\b[a-z0-9]{3,}\b', " ".join(search_terms)))
            element_text = (
                f"{ai_choice['name']} "
                f"{ai_choice.get('html_id', '')} "
                f"{ai_choice.get('data_qa', '')}"
            ).lower()
            if guard_words and not any(w in element_text for w in guard_words):
                missing = search_texts[0] if search_texts else target_field
                print(f"    👻 ANTI-PHANTOM GUARD: AI chose '{ai_choice['name']}', "
                      f"but target '{missing}' is missing. Rejecting.")
                return None

        return ai_choice

    # ── High-level step handlers ──────────────

    async def _handle_navigate(self, page, step: str) -> bool:
        url = re.search(r'(https?://[^\s\'"<>]+)', step)
        if not url:
            print("    ❌ Invalid URL")
            return False
        await page.goto(
            url.group(1), wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT
        )
        self.last_xpath = None
        await asyncio.sleep(NAV_WAIT)
        return True

    async def _handle_scroll(self, page, step: str):
        step_l = step.lower()
        if "inside" in step_l or "list" in step_l:
            await page.evaluate(
                "const d=document.querySelector('#dropdown')||"
                "document.querySelector('[class*=\"dropdown\"]');"
                "if(d)d.scrollTop=d.scrollHeight;"
            )
        else:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(SCROLL_WAIT)

    async def _handle_extract(self, page, step: str) -> bool:
        var_m  = re.search(r'\{(.*?)\}', step)
        target = (_extract_quoted(step) or [""])[0].replace("'", "")
        print("    ⚙️  DOM HEURISTICS: Extracting data via JS…")

        val = await page.evaluate(f"""() => {{
            const t = "{target.lower()}";
            const row = Array.from(document.querySelectorAll('tr, [role="row"]'))
                             .find(r => r.innerText.toLowerCase().includes(t));
            if (row) {{
                const tds = Array.from(row.querySelectorAll('td'));
                if (tds.length > 0) {{
                    const numTd = tds.find(c =>
                        c.innerText.includes('%') || c.innerText.includes('$') ||
                        c.innerText.includes('Rs.') ||
                        !isNaN(parseFloat(c.innerText.trim()))
                    );
                    if (numTd) return numTd.innerText.trim();
                    return tds[tds.length - 1].innerText.trim();
                }}
                return row.innerText.trim();
            }}
            return null;
        }}""")

        if val and var_m:
            self.memory[var_m.group(1)] = val.strip()
            print(f"    📦 COLLECTED: {val.strip()}")
            return True
        return False

    async def _handle_verify(self, page, step: str) -> bool:
        expected          = _extract_quoted(step)
        is_negative       = bool(re.search(r'\b(NOT|HIDDEN|ABSENT)\b', step.upper()))
        state_check       = (
            "disabled" if re.search(r'\bDISABLED\b', step.upper()) else
            "enabled"  if re.search(r'\bENABLED\b',  step.upper()) else None
        )
        is_checked_verify = bool(re.search(r'\bchecked\b', step.lower()))

        msg = f"    ⚙️  DOM HEURISTICS: Scanning for {expected}"
        if is_negative:       msg += " [MUST BE ABSENT]"
        if is_checked_verify: msg += " [CHECK STATE]"
        if state_check:       msg += f" [MUST BE {state_check.upper()}]"
        print(msg)

        for _ in range(12):
            try:
                if is_checked_verify and expected:
                    # Use JS to find the actual input[type=checkbox/radio] by label text.
                    # snapshot() may return a <label> or <span>, which Playwright can't
                    # call is_checked() on — so we resolve the real input via DOM instead.
                    label_text = expected[0].lower().replace("\\", "\\\\").replace("`", "").replace('"', '\\"')
                    result = await page.evaluate(f"""() => {{
                        const target = `{label_text}`;

                        // 1. Native inputs: checkbox / radio
                        const inputs = Array.from(document.querySelectorAll(
                            'input[type="checkbox"], input[type="radio"]'
                        ));
                        for (const inp of inputs) {{
                            const lbl = inp.closest('label') ||
                                        document.querySelector(`label[for="${{inp.id}}"]`);
                            const row = inp.closest('tr');
                            const ctx = (lbl?.innerText || row?.innerText || '').toLowerCase();
                            const nm  = (inp.name || inp.id || inp.value || '').toLowerCase();
                            if (ctx.includes(target) || nm.includes(target)) {{
                                return inp.checked;
                            }}
                        }}

                        // 2. ARIA role=checkbox / role=radio (custom components, React trees)
                        const roleEls = Array.from(document.querySelectorAll(
                            '[role="checkbox"], [role="radio"]'
                        ));
                        for (const el of roleEls) {{
                            const txt = (el.innerText ||
                                        el.getAttribute('aria-label') || '').toLowerCase();
                            if (txt.includes(target)) {{
                                return el.getAttribute('aria-checked') === 'true';
                            }}
                        }}

                        return null;  // not found yet — keep retrying
                    }}""")
                    if result is not None:
                        ok = (not result) if is_negative else result
                        if ok:
                            print("    ✅ VERIFIED")
                            return True
                    # result is None → element not found yet, keep retrying

                elif state_check and expected:
                    els = await self._snapshot(page, "locate", expected)
                    if els:
                        loc      = page.locator(f"xpath={els[0]['xpath']}").first
                        disabled = await loc.is_disabled()
                        ok = ((state_check == "disabled" and disabled)
                              or (state_check == "enabled"  and not disabled))
                        if ok:
                            print("    ✅ VERIFIED")
                            return True

                else:
                    text  = await page.evaluate(_VISIBLE_TEXT_JS)
                    clean = " ".join(text.replace("\u2019", "'").split())
                    matched = (all(e.lower() in clean for e in expected)
                               if expected else False)
                    success = (not matched) if is_negative else matched
                    if success:
                        print("    ✅ VERIFIED")
                        return True

            except Exception:
                pass
            await asyncio.sleep(1)

        print("    ❌ VERIFICATION FAILED")
        return False

    async def _do_drag(self, page, step: str, expected: list[str], _hint_id: int) -> bool:
        all_els = await self._snapshot(page, "drag", [])
        if not all_els:
            return False

        src_idx = tgt_idx = -1
        if len(expected) >= 2:
            for i, el in enumerate(all_els):
                n = el["name"].lower()
                if expected[0].lower() in n and src_idx == -1: src_idx = i
                if expected[1].lower() in n:                   tgt_idx  = i
        else:
            for i, el in enumerate(all_els):
                n  = el["name"].lower()
                cl = el.get("class_name", "").lower()
                if ("drag" in n or "draggable" in cl) and src_idx == -1: src_idx = i
                if expected and expected[0].lower() in n:                 tgt_idx  = i

        if src_idx < 0: src_idx = 0
        if tgt_idx < 0: tgt_idx = len(all_els) - 1 if len(all_els) > 1 else 0

        try:
            src_loc = page.locator(f"xpath={all_els[src_idx]['xpath']}").first
            tgt_loc = page.locator(f"xpath={all_els[tgt_idx]['xpath']}").first
            await src_loc.scroll_into_view_if_needed()
            await self._highlight(
                page, all_els[src_idx]["id"], "red",   "#ffcccc", by_js_id=True
            )
            await self._highlight(
                page, all_els[tgt_idx]["id"], "green", "#ccffcc", by_js_id=True
            )
            print(f"    🔄 Dragging '{all_els[src_idx]['name'][:25]}'"
                  f" → '{all_els[tgt_idx]['name'][:25]}'")
            await src_loc.drag_to(tgt_loc, timeout=3000)
            await asyncio.sleep(ACTION_WAIT)
            return True
        except Exception as ex:
            print(f"    ❌ Drag error: {ex}")
            return False

    # ── Action dispatcher ─────────────────────

    async def _execute_step(self, page, step: str, strategic_context: str) -> bool:
        step_l = step.lower()
        words  = set(re.findall(r'\b[a-z0-9]+\b', step_l))

        if   "drag" in words and "drop" in words:              mode = "drag"
        elif "select" in words or "choose" in words:           mode = "select"
        elif any(w in words for w in ("type","fill","enter")): mode = "input"
        elif any(w in words for w in ("click","double","check","uncheck")): mode = "clickable"
        elif "hover" in words:                                  mode = "hover"
        else:                                                    mode = "locate"

        preserve    = mode in ("input", "select")
        expected    = _extract_quoted(step, preserve_case=preserve)

        target_field: str | None = None
        txt_to_type  = ""
        search_texts: list[str] = []

        if mode == "input" and expected:
            txt_to_type  = expected[-1]
            search_texts = expected[:-1]
            m = re.search(r'(?:into\s+the\s+|into\s+)([a-zA-Z0-9_]+)\s*field', step_l)
            if m and m.group(1) not in ("that", "the", "a", "an"):
                target_field = m.group(1).lower()
        else:
            search_texts = expected

        # Clear context memory when we have explicit targets
        if search_texts or target_field:
            self.last_xpath = None

        # ── Optional step detection ──────────────────────────────────
        # "if exists" / "optional" AFTER all quoted strings → soft step.
        # Strip quotes first so 'Promotion Code if exists' (literal label) is
        # NOT treated as optional.  Only trailing qualifiers count.
        _stripped = re.sub(r'''["'][^"']*["']''', '', step_l)
        is_optional = bool(re.search(r'\bif\s+exists\b|\boptional\b', _stripped))

        cache_key       = (mode, tuple(t.lower() for t in search_texts), target_field)
        failed_ids: set = set()
        MAX_ATTEMPTS    = 3

        for attempt in range(MAX_ATTEMPTS):
            try:
                el = await self._resolve_element(
                    page, step, mode, search_texts, target_field, strategic_context,
                    failed_ids=failed_ids,
                )
            except Exception:
                if is_optional:
                    return True
                raise

            if el is None:
                # ── FIX 3: locate steps are soft — they just highlight and move on ──
                # "Find / Locate" steps precede drag-and-drop or are table-row locators.
                # They don't perform any real action; failing them kills the mission
                # unnecessarily. Return True (soft success) so the next step can proceed.
                if mode == "locate":
                    return True
                if is_optional:
                    return True
                if attempt > 0:
                    print("    💀 SELF-HEALING FAILED: No more candidates.")
                return False

            # ── Optional step guard: require exact text match ────────────
            # For "if exists" / "optional" steps, only proceed when the
            # resolved element genuinely matches the search text.  Without
            # this, a vague partial/keyword match could click a completely
            # unrelated element that happened to score above the threshold.
            if is_optional and search_texts:
                el_name  = el["name"].lower()
                el_aria  = el.get("aria_label", "").lower()
                el_dqa   = el.get("data_qa", "").lower()
                el_haystack = f"{el_name} {el_aria} {el_dqa}"
                if not any(t.lower() in el_haystack for t in search_texts):
                    # Resolved element doesn't actually contain the target
                    # text — treat as "not found" and skip gracefully.
                    return True

            # Skip elements already known to cause errors
            if el["id"] in failed_ids:
                continue

            self.last_xpath = el["xpath"]
            name    = el["name"]
            xpath   = el["xpath"]
            is_sel  = el.get("is_select",  False)
            is_shad = el.get("is_shadow",  False)
            el_id   = el["id"]
            tag     = el.get("tag_name",   "")
            itype   = el.get("input_type", "")

            # Guard: never type into non-typeable controls
            if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
                print(f"    👻 ANTI-PHANTOM GUARD: Rejecting '{name}' "
                      f"(cannot type into {itype}).")
                failed_ids.add(el_id)
                self.last_xpath = None
                continue

            if mode == "locate":
                # Locate = highlight only, never click. Sets context for next step.
                try:
                    loc = page.locator(f"xpath={xpath}").first
                    if not is_shad:
                        await loc.scroll_into_view_if_needed(timeout=2000)
                        await self._highlight(page, loc)
                    else:
                        await self._highlight(page, el_id, by_js_id=True)
                except Exception:
                    pass
                print(f"    🔍 Located '{name[:40]}'")
                return True

            if mode == "drag":
                return await self._do_drag(page, step, expected, el_id)

            loc = page.locator(f"xpath={xpath}").first
            try:
                if not is_shad:
                    await loc.scroll_into_view_if_needed(timeout=2000)
                    await self._highlight(page, loc)
                else:
                    await self._highlight(page, el_id, by_js_id=True)
            except Exception:
                pass

            act_timeout = 3000
            try:
                # ── Input ─────────────────────────────────────────────────
                if mode == "input":
                    print(f"    ⌨️  Typed '{txt_to_type}' → '{name[:30]}'")
                    if is_shad:
                        await page.evaluate(f"window.manulType({el_id}, '{txt_to_type}')")
                    else:
                        is_readonly = await loc.evaluate(
                            "el => el.readOnly || el.hasAttribute('readonly')"
                        )
                        if is_readonly:
                            escaped = txt_to_type.replace("'", "\\'")
                            await page.evaluate(f"""el => {{
                                el.removeAttribute('readonly');
                                el.value = '{escaped}';
                                el.dispatchEvent(new Event('input',  {{bubbles:true}}));
                                el.dispatchEvent(new Event('change', {{bubbles:true}}));
                                el.dispatchEvent(
                                    new KeyboardEvent('keydown', {{bubbles:true}})
                                );
                            }}""", await loc.element_handle())
                        else:
                            await loc.fill("",          timeout=act_timeout)
                            await loc.type(txt_to_type, delay=50, timeout=act_timeout)
                    if "enter" in step_l:
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(4)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    self.last_xpath = None
                    return True

                # ── Select ────────────────────────────────────────────────
                elif mode == "select":
                    if is_sel:
                        valid = await loc.evaluate(
                            """(sel, exp) => exp.filter(e =>
                                Array.from(sel.options).some(o =>
                                    o.text.trim().toLowerCase()  === e.toLowerCase() ||
                                    o.value.trim().toLowerCase() === e.toLowerCase()
                                ))""",
                            expected,
                        )
                        opts = (valid or expected
                                or [list(set(
                                    re.findall(r'\b[a-z0-9]{3,}\b', step_l)
                                ))[0]])
                        print(f"    🗂️  Selected {opts} from '{name[:30]}'")
                        try:
                            await loc.select_option(label=opts, timeout=act_timeout)
                        except Exception:
                            await loc.select_option(
                                value=[o.lower() for o in opts], timeout=act_timeout
                            )
                    else:
                        await loc.click(force=True, timeout=act_timeout)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                # ── Hover ─────────────────────────────────────────────────
                elif mode == "hover":
                    print(f"    🚁  Hovered '{name[:30]}'")
                    if is_shad:
                        await page.evaluate(
                            f"window.manulElements[{el_id}].dispatchEvent("
                            "new MouseEvent('mouseover',{bubbles:true,cancelable:true,"
                            "view:window}))"
                        )
                    else:
                        await loc.hover(force=True, timeout=act_timeout)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                # ── Click / double-click ───────────────────────────────────
                else:
                    print(f"    🖱️  Clicked '{name[:30]}'")
                    if is_shad:
                        fn = "manulDoubleClick" if "double" in step_l else "manulClick"
                        await page.evaluate(f"window.{fn}({el_id})")
                        await asyncio.sleep(ACTION_WAIT)
                    else:
                        if "double" in step_l:
                            await loc.dblclick(timeout=act_timeout)
                            await asyncio.sleep(ACTION_WAIT)
                        elif itype in ("checkbox", "radio"):
                            # JS click is far more reliable for native
                            # checkbox / radio inputs than Playwright's
                            # coordinate-based click(force=True).  Some
                            # practice pages hide the real <input> behind
                            # a label or custom styling, causing misclicks.
                            await loc.evaluate("el => el.click()")
                            await asyncio.sleep(ACTION_WAIT)
                        else:
                            is_submit = (
                                itype == "submit"
                                or (tag == "button" and itype in ("", "submit"))
                            )
                            if is_submit:
                                # One click, then wait for the page to settle.
                                # Do NOT click again in the except — that causes
                                # double-submit (stale CSRF tokens, duplicate posts).
                                await loc.click(force=True, timeout=act_timeout)
                                try:
                                    await page.wait_for_load_state(
                                        "networkidle", timeout=10_000
                                    )
                                except Exception:
                                    await asyncio.sleep(3.0)
                            else:
                                await loc.click(force=True, timeout=act_timeout)
                                await asyncio.sleep(ACTION_WAIT)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    return True

            except Exception as ex:
                err = str(ex).split('\n')[0][:80]
                print(f"    ❌ Action error: {err}…")
                print(f"    🚑 SELF-HEALING: Rejecting candidate {el_id} and retrying…")
                failed_ids.add(el_id)
                self.last_xpath = None
                await asyncio.sleep(1)

        return False

    # ── Mission runner ────────────────────────

    async def run_mission(self, task: str, strategic_context: str = "") -> bool:
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
                    step = _substitute_memory(raw_step, self.memory)
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


# ─────────────────────────────────────────────
# JavaScript constants
# ─────────────────────────────────────────────

_VISIBLE_TEXT_JS = """() => {
    let t = (document.body.innerText || "") + " ";
    document.querySelectorAll('*').forEach(el => {
        const st = window.getComputedStyle(el);
        const isHidden = st.display === 'none'
                      || st.visibility === 'hidden'
                      || st.opacity === '0';
        // Always scan alert/success/notification divs — success messages may appear
        // via JS after a form POST and their computed style can be briefly stale.
        const isAlert = el.classList && (
            el.classList.contains('alert')        ||
            el.classList.contains('success')      ||
            el.classList.contains('notification') ||
            el.classList.contains('message')      ||
            el.getAttribute('role') === 'alert'
        );
        if (isHidden && !isAlert) return;
        if (el.title)       t += el.title + " ";
        if (el.value && typeof el.value === 'string') t += el.value + " ";
        if (el.placeholder) t += el.placeholder + " ";
        if (el.shadowRoot)
            t += Array.from(el.shadowRoot.querySelectorAll('*'))
                      .map(e => e.innerText || e.value || '').join(' ');
    });
    return t.toLowerCase();
}"""

_SNAPSHOT_JS = r"""([mode, expected_texts]) => {
    if (!window.manulElements) {
        window.manulElements = {};
        window.manulIdCounter = 0;
    }

    window.manulHighlight = (id, color, bg) => {
        const el = window.manulElements[id]; if (!el) return;
        el.scrollIntoView({ behavior:'smooth', block:'center' });
        const oB=el.style.border, oBg=el.style.backgroundColor;
        el.style.border=`4px solid ${color}`; el.style.backgroundColor=bg;
        setTimeout(()=>{el.style.border=oB;el.style.backgroundColor=oBg;},2000);
    };
    window.manulClick = id => {
        const el=window.manulElements[id];
        if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.click();}
    };
    window.manulDoubleClick = id => {
        const el=window.manulElements[id];
        if(el) el.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));
    };
    window.manulType = (id, text) => {
        const el=window.manulElements[id];
        if(!el) return;
        el.scrollIntoView({behavior:'smooth',block:'center'});
        el.value=text;
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
    };

    const INTERACTIVE_INPUT = "input,textarea,[contenteditable='true']";
    const INTERACTIVE_CLICK = [
        // Standard HTML interactive elements
        "button","a","input[type='radio']","input[type='checkbox']",
        "select",".dropbtn","summary",
        ".ui-draggable",".ui-droppable",".option","input",
        // Labels (real click target in custom checkbox/radio trees)
        "label",
        // ARIA roles
        "[role='button']","[role='checkbox']","[role='radio']",
        "[role='tab']","[role='option']","[role='menuitem']","[role='switch']",
        // React Checkbox Tree
        "[class*='rct-node-clickable']","[class*='rct-title']",
        // Generic custom checkbox wrappers
        "[class*='checkbox']","[class*='check-box']",
        // Catch-all for JS-only widgets
        "[onclick]",
    ].join(",");

    // FIX 1: "locate" mode uses INTERACTIVE_CLICK so SELECT elements,
    // draggable divs, and custom widgets are found by "Find / Locate" steps.
    // Only pure text-input mode restricts to INTERACTIVE_INPUT.
    const INTERACTIVE = (mode === "input")
        ? INTERACTIVE_INPUT
        : INTERACTIVE_CLICK;

    const seen    = new Set();
    const results = [];

    const collect = (root, inShadow=false) => {
        root.querySelectorAll(INTERACTIVE).forEach(el => {
            if (seen.has(el)) return;
            seen.add(el);

            const r  = el.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) return;
            const st = window.getComputedStyle(el);
            if (st.visibility === 'hidden' || st.display === 'none') return;

            // Skip labels that are just wrappers around a visible input.
            // Keep them only when their linked input is hidden (custom trees).
            if (el.tagName === 'LABEL') {
                const linked = el.htmlFor
                    ? document.getElementById(el.htmlFor)
                    : el.querySelector('input');
                if (linked) {
                    const lr = linked.getBoundingClientRect();
                    if (lr.width > 2 && lr.height > 2
                            && window.getComputedStyle(linked).display !== 'none') {
                        return;
                    }
                }
            }

            if (!el.dataset.manulId) {
                const id = window.manulIdCounter++;
                el.dataset.manulId  = id;
                window.manulElements[id] = el;
            }
            results.push({el, inShadow});
        });
        root.querySelectorAll('*').forEach(el => {
            if(el.shadowRoot) collect(el.shadowRoot, true);
        });
    };
    collect(document);

    results.sort((a,b) =>
        a.el.getBoundingClientRect().top - b.el.getBoundingClientRect().top
    );

    const getXPath = el => {
        if(el.id) return `//*[@id="${el.id}"]`;
        const parts = [];
        while(el && el.nodeType === Node.ELEMENT_NODE) {
            const idx = Array.from(el.parentNode?.children || [])
                              .filter(s => s.tagName === el.tagName)
                              .indexOf(el) + 1;
            parts.unshift(`${el.tagName.toLowerCase()}[${idx}]`);
            el = el.parentNode;
        }
        return `/${parts.join('/')}`;
    };

    const labelFor = el => {
        if (el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio')) {
            const tr = el.closest('tr');
            if (tr) return tr.innerText.trim().replace(/\s+/g,' ');
            const lbl = el.closest('label')
                     || document.querySelector(`label[for="${el.id}"]`);
            if (lbl) return lbl.innerText.trim();
        }
        if (['INPUT','SELECT','TEXTAREA'].includes(el.tagName)) {
            const lbl = document.querySelector(`label[for="${el.id}"]`);
            if (lbl) return lbl.innerText.trim();
            let curr = el;
            while (curr && curr.tagName !== 'BODY') {
                let prev = curr.previousElementSibling;
                while (prev) {
                    if (/^H[1-6]$/.test(prev.tagName)
                            || prev.classList.contains('title'))
                        return prev.innerText.trim();
                    prev = prev.previousElementSibling;
                }
                curr = curr.parentElement;
            }
        }
        // Custom checkbox/radio tree nodes (React Checkbox Tree, demoqa, etc.)
        const role = el.getAttribute('role') || '';
        if (role === 'checkbox' || role === 'radio' ||
            (el.className && typeof el.className === 'string' &&
             (el.className.includes('rct-') || el.className.includes('checkbox')))) {
            const title =
                el.querySelector('[class*="title"],[class*="label"]') ||
                el.closest('[class*="node"],[class*="item"],[class*="tree-item"]')
                  ?.querySelector('[class*="title"],[class*="label"]');
            if (title) return title.innerText.trim();
        }
        return '';
    };

    return results.map(({el, inShadow}) => {
        let name, isSelect = false;

        // Collect icon-class keywords from child <i>/<svg>/<span[icon]>.
        // "fa-arrow-circle-o-right" → "fa arrow circle right"
        const iconClasses = Array.from(
            el.querySelectorAll('i, svg, span[class*="icon"]')
        ).map(i => i.className || i.getAttribute('class') || '')
         .join(' ')
         .replace(/[-_]/g, ' ')
         .toLowerCase();

        const htmlId    = el.id || '';
        const ariaLabel = el.getAttribute('aria-label') || el.getAttribute('title') || '';

        if (el.tagName === 'SELECT') {
            isSelect = true;
            name = 'dropdown [' +
                Array.from(el.options).map(o => o.text.trim()).join(' | ') +
                ']';
        } else {
            const rawText = el.innerText ? el.innerText.trim() : '';
            name = rawText
                || ariaLabel
                || el.placeholder
                || el.getAttribute('value')
                || htmlId
                || el.name
                || el.className
                || 'item';
            name = name.trim();
        }

        if (el.tagName === 'INPUT') name += ` input ${el.type || ''}`;

        const ctx = labelFor(el);
        if (ctx)      name = `${ctx} -> ${name}`;
        if (inShadow) name += ' [SHADOW_DOM]';

        return {
            id:           parseInt(el.dataset.manulId),
            name:         name.substring(0, 150).replace(/\n/g, ' '),
            xpath:        getXPath(el),
            is_select:    isSelect,
            is_shadow:    inShadow,
            class_name:   el.className || '',
            tag_name:     el.tagName.toLowerCase(),
            input_type:   el.type ? el.type.toLowerCase() : '',
            data_qa:      el.getAttribute('data-qa')
                       || el.getAttribute('data-testid') || '',
            html_id:      htmlId,
            icon_classes: iconClasses,
            aria_label:   ariaLabel,
            role:          el.getAttribute('role') || '',
            disabled:      el.disabled || false,
            aria_disabled:  el.getAttribute('aria-disabled') || '',
        };
    });
}"""