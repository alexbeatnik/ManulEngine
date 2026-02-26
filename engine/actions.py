# engine/actions.py
import asyncio
import re
from .helpers import extract_quoted, SCROLL_WAIT, ACTION_WAIT, NAV_WAIT
from .js_scripts import VISIBLE_TEXT_JS
from . import prompts

class _ActionsMixin:
    async def _handle_navigate(self, page, step: str) -> bool:
        url = re.search(r'(https?://[^\s\'"<>]+)', step)
        if not url: return False
        await page.goto(url.group(1), wait_until="domcontentloaded", timeout=prompts.NAV_TIMEOUT)
        self.last_xpath = None
        await asyncio.sleep(NAV_WAIT)
        return True

    async def _handle_scroll(self, page, step: str):
        step_l = step.lower()
        if "inside" in step_l or "list" in step_l:
            await page.evaluate("const d=document.querySelector('#dropdown')||document.querySelector('[class*=\"dropdown\"]');if(d)d.scrollTop=d.scrollHeight;")
        else:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(SCROLL_WAIT)

    async def _handle_extract(self, page, step: str) -> bool:
        var_m  = re.search(r'\{(.*?)\}', step)
        target = (extract_quoted(step) or [""])[0].replace("'", "")
        print("    ⚙️  DOM HEURISTICS: Extracting data via JS…")

        # Build secondary hint from step text (words before 'into' minus noise)
        step_lower = step.lower()
        hint = ""
        m_hint = re.search(r'extract\s+(.+?)\s+into\b', step_lower)
        if m_hint:
            raw = m_hint.group(1)
            raw = re.sub(r"'[^']*'", "", raw).strip()
            for w in ("the", "of", "from", "a", "an", "text", "value"):
                raw = re.sub(rf'\b{w}\b', '', raw).strip()
            hint = raw.strip()

        val = await page.evaluate("""(args) => {
            const t = args[0];
            const hint = args[1];

            const ALL_TAGS = 'div, span, p, h1, h2, h3, h4, h5, h6, li, dd, dt, '
                + 'strong, b, i, em, label, a, button, td, th, article, section';
            const VALUE_TAGS = 'span, div, strong, b, i, em, dd, p, h1, h2, h3, h4, h5, h6';

            const hintWords = hint ? hint.split(/\\s+/).filter(w =>
                w.length > 1 || /[$\\u20ac\\u00a3\\u20b4\\u00a5\\u20b9]/.test(w)) : [];
            const hintJoined = hintWords.join(' ');

            const wordMatch = (text, word) => {
                if (word.length >= 5) return text.includes(word);
                if (word.length <= 1 && /[^a-zA-Z0-9]/.test(word))
                    return text.includes(word);
                const re = new RegExp('\\\\b' + word.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\b', 'i');
                return re.test(text);
            };

            const hasAlpha = (s) => /[a-zA-Z0-9]/.test(s);

            const hintSibling = (el) => {
                if (hintWords.length === 0) return null;
                const parent = el.parentElement;
                if (!parent) return null;
                const kids = Array.from(parent.children);
                const idx = kids.indexOf(el);
                for (let i = idx + 1; i < kids.length; i++) {
                    const sib = kids[i];
                    const stxt = (sib.innerText || '').trim();
                    const cls = (sib.className && typeof sib.className === 'string'
                        ? sib.className : '').toLowerCase().replace(/[-_]/g, ' ');
                    if (stxt && (hintWords.some(w => cls.includes(w)) ||
                        hintWords.some(w => stxt.toLowerCase().includes(w))))
                        return stxt;
                }
                for (let i = idx - 1; i >= 0; i--) {
                    const sib = kids[i];
                    const stxt = (sib.innerText || '').trim();
                    const cls = (sib.className && typeof sib.className === 'string'
                        ? sib.className : '').toLowerCase().replace(/[-_]/g, ' ');
                    if (stxt && (hintWords.some(w => cls.includes(w)) ||
                        hintWords.some(w => stxt.toLowerCase().includes(w))))
                        return stxt;
                }
                return null;
            };

            const nextSiblingValue = (el) => {
                let sib = el.nextElementSibling;
                if (sib) {
                    const txt = (sib.innerText || '').trim();
                    if (txt) return txt;
                }
                return null;
            };

            const drillValue = (el) => {
                const full = (el.innerText || '').trim();
                const kids = Array.from(el.querySelectorAll(VALUE_TAGS))
                    .filter(k => {
                        const kt = (k.innerText || '').trim();
                        return kt.length > 0 && kt.length < full.length;
                    });
                if (kids.length === 0) return full;

                if (hintWords.length > 0) {
                    const hintKids = kids.filter(k => {
                        const kt = (k.innerText || '').toLowerCase();
                        return kt.includes(hintJoined);
                    });
                    if (hintKids.length > 0) {
                        hintKids.sort((a, b) =>
                            (a.innerText||'').length - (b.innerText||'').length);
                        return hintKids[0].innerText.trim();
                    }
                    const partialKids = kids.filter(k => {
                        const kt = (k.innerText || '').toLowerCase();
                        const cls = (k.className && typeof k.className === 'string'
                            ? k.className : '').toLowerCase().replace(/[-_]/g, ' ');
                        return hintWords.some(w => kt.includes(w) || cls.includes(w));
                    });
                    if (partialKids.length > 0) {
                        partialKids.sort((a, b) =>
                            (a.innerText||'').length - (b.innerText||'').length);
                        const pkText = partialKids[0].innerText.trim().toLowerCase();
                        if (hintWords.some(w => pkText === w || pkText === w + ':')) {
                            if (full.length < 50) return full;
                            const pk = partialKids[0];
                            const pkSib = pk.nextElementSibling;
                            if (pkSib) {
                                const pst = (pkSib.innerText || '').trim();
                                if (pst && hasAlpha(pst)) return pst;
                            }
                            return full;
                        }
                        return partialKids[0].innerText.trim();
                    }
                }
                const currSymKid = kids.find(k =>
                    /^[$\\u20ac\\u00a3\\u20b4\\u00a5\\u20b9]$/.test(k.innerText.trim()));
                if (currSymKid) return full;
                const numKid = kids.find(k => {
                    const kt = k.innerText.trim();
                    return (kt.length > 1 && /[$\\u20ac\\u00a3%\\u20b4]/.test(kt)) ||
                        /^[\\d.,]+$/.test(kt);
                });
                if (numKid) return numKid.innerText.trim();
                const headingKid = kids.find(k => /^H[1-6]$/.test(k.tagName));
                if (headingKid) return headingKid.innerText.trim();
                return kids[kids.length - 1].innerText.trim();
            };

            // === 1. Table rows — when t is set ===
            if (t) {
                const rows = Array.from(document.querySelectorAll('tr, [role="row"]'));
                const row = rows.find(r => r.innerText.toLowerCase().includes(t));
                if (row) {
                    let cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length === 0)
                        cells = Array.from(row.querySelectorAll('[role="cell"]'));
                    if (cells.length > 1) {
                        if (hint) {
                            const table = row.closest('table');
                            if (table) {
                                const ths = Array.from(table.querySelectorAll('th'));
                                const colIdx = ths.findIndex(th =>
                                    th.innerText.toLowerCase().includes(hint));
                                if (colIdx >= 0 && colIdx < cells.length)
                                    return cells[colIdx].innerText.trim();
                            }
                            const hintIdx = cells.findIndex(c =>
                                c.innerText.toLowerCase().includes(hint));
                            if (hintIdx >= 0 && hintIdx + 1 < cells.length)
                                return cells[hintIdx + 1].innerText.trim();
                            const hintCell = cells.find(c =>
                                c.innerText.toLowerCase().includes(hint));
                            if (hintCell) return hintCell.innerText.trim();
                        }
                        const numTd = cells.find(c =>
                            /[$\\u20ac\\u00a3%\\u20b4]/.test(c.innerText) ||
                            c.innerText.includes('Rs.') ||
                            !isNaN(parseFloat(c.innerText.trim()))
                        );
                        if (numTd) return numTd.innerText.trim();
                        return cells[cells.length - 1].innerText.trim();
                    }
                    if (cells.length === 1) return cells[0].innerText.trim();
                    return row.innerText.trim();
                }
            }

            // === 1b. Table rows via hint words (no quoted target) ===
            if (!t && hint) {
                const rows = Array.from(document.querySelectorAll('tr'));
                for (const row of rows) {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length < 2) continue;
                    const rowText = cells.map(c => c.innerText.toLowerCase()).join(' ');
                    const table = row.closest('table');
                    const ths = table ? Array.from(table.querySelectorAll('th')) : [];
                    const colWords = hintWords.filter(w =>
                        ths.some(th => th.innerText.toLowerCase().includes(w)));
                    const rowWords = hintWords.filter(w => !colWords.includes(w));
                    if (rowWords.length > 0 &&
                        rowWords.every(w => rowText.includes(w))) {
                        if (colWords.length > 0) {
                            const colIdx = ths.findIndex(th =>
                                colWords.some(w => th.innerText.toLowerCase().includes(w)));
                            if (colIdx >= 0 && colIdx < cells.length)
                                return cells[colIdx].innerText.trim();
                        }
                        const numTd = cells.find(c =>
                            /[$\\u20ac\\u00a3%\\u20b4]/.test(c.innerText) ||
                            !isNaN(parseFloat(c.innerText.trim()))
                        );
                        if (numTd) return numTd.innerText.trim();
                        return cells[cells.length - 1].innerText.trim();
                    }
                }
            }

            // === 1c. Role-row cells (before generic search) ===
            if (hint) {
                const rows = Array.from(document.querySelectorAll('[role="row"]'));
                for (const row of rows) {
                    const cells = Array.from(row.querySelectorAll('[role="cell"]'));
                    if (cells.length >= 2) {
                        const labelCell = cells[0].innerText.toLowerCase();
                        if (hintWords.some(w => wordMatch(labelCell, w)))
                            return cells[cells.length - 1].innerText.trim();
                    }
                }
            }

            // === 2. Generic DOM search ===
            const allEls = Array.from(document.querySelectorAll(ALL_TAGS));
            const inputs = Array.from(document.querySelectorAll(
                'input, textarea, select'));

            // Strategy A: target text present
            if (t) {
                const matches = allEls.filter(el =>
                    (el.innerText || '').toLowerCase().includes(t));
                if (matches.length > 0) {
                    matches.sort((a, b) =>
                        (a.innerText || '').length - (b.innerText || '').length);
                    const best = matches[0];
                    const full = (best.innerText || '').trim();
                    const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g,'');
                    if (norm(full) === norm(t)) {
                        if (hint) {
                            const hs = hintSibling(best);
                            if (hs) return hs;
                        }
                        const tag = best.tagName;
                        if (/^(H[1-6]|LABEL|TH|DT)$/.test(tag)) {
                            const sibVal = nextSiblingValue(best);
                            if (sibVal) return sibVal;
                        }
                        if (hint) {
                            const sibVal = nextSiblingValue(best);
                            if (sibVal) return sibVal;
                            const parent = best.parentElement;
                            if (parent) {
                                const kids = Array.from(parent.children);
                                const idx = kids.indexOf(best);
                                for (let i = idx + 1; i < kids.length; i++) {
                                    const nxt = (kids[i].innerText || '').trim();
                                    if (nxt) return nxt;
                                }
                            }
                        }
                    }
                    if (full.length > t.length * 3)
                        return drillValue(best);
                    return full;
                }
                const inputMatch = inputs.find(el =>
                    (el.value || '').toLowerCase().includes(t));
                if (inputMatch) return inputMatch.value.trim();
            }

            // Strategy B: no quoted target → use hint words
            if (hint) {
                for (const el of inputs) {
                    const labelEl = el.labels && el.labels[0];
                    const lbl = (labelEl ? labelEl.innerText : '').toLowerCase();
                    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                    const ph = (el.placeholder || '').toLowerCase();
                    const combined = lbl + ' ' + aria + ' ' + ph;
                    if (hintWords.every(w => combined.includes(w))) {
                        const v = (el.value || '').trim();
                        if (v) return v;
                    }
                }

                const idMatches = [];
                for (const el of allEls) {
                    const id = (el.id || '').toLowerCase();
                    const dq = (el.getAttribute && el.getAttribute('data-qa') || '').toLowerCase();
                    if (hintWords.some(w => id.includes(w) || dq.includes(w))) {
                        const txt = (el.innerText || el.value || '').trim();
                        if (txt && hasAlpha(txt))
                            idMatches.push({el, txt});
                    }
                }
                if (idMatches.length > 0) {
                    idMatches.sort((a, b) => a.txt.length - b.txt.length);
                    return idMatches[0].txt;
                }

                const b2matches = [];
                for (const el of allEls) {
                    const txt = (el.innerText || '').trim();
                    const lower = txt.toLowerCase();
                    if (lower.includes(hintJoined) && txt.length < 200)
                        b2matches.push({el, txt, len: txt.length});
                }
                if (b2matches.length > 0) {
                    b2matches.sort((a, b) => a.len - b.len);
                    const best = b2matches[0];
                    const tag = best.el.tagName;
                    if (/^(H[1-6]|LABEL|TH|DT)$/.test(tag) ||
                        best.txt.endsWith(':')) {
                        const sibVal = nextSiblingValue(best.el);
                        if (sibVal) return sibVal;
                    }
                    const drilled = drillValue(best.el);
                    if (drilled !== best.txt) return drilled;
                    return best.txt;
                }

                const b56matches = [];
                for (const el of allEls) {
                    const aria = (el.getAttribute && el.getAttribute('aria-label') || '').toLowerCase();
                    const cls = (el.className && typeof el.className === 'string'
                        ? el.className : '').toLowerCase().replace(/[-_]/g, ' ');
                    if (!aria && !cls) continue;
                    let score = 0;
                    const matched = {};
                    for (const w of hintWords) {
                        if ((aria && aria.includes(w)) || cls.includes(w)) {
                            score++;
                            matched[w] = true;
                        }
                    }
                    if (score > 0) {
                        const txt = (el.innerText || '').trim();
                        if (txt && hasAlpha(txt) && txt.length >= 2 && txt.length < 200) {
                            if (txt.length < 50) {
                                const lower = txt.toLowerCase();
                                for (const w of hintWords) {
                                    if (!matched[w] && wordMatch(lower, w))
                                        score += 0.5;
                                }
                            }
                            b56matches.push({el, txt, score, len: txt.length});
                        }
                        if (!txt || !hasAlpha(txt) || txt.length < 2) {
                            const av = el.getAttribute('aria-valuenow');
                            if (av && hasAlpha(av))
                                b56matches.push({el, txt: av, score, len: av.length});
                        }
                    }
                }
                if (b56matches.length > 0) {
                    b56matches.sort((a, b) =>
                        b.score - a.score || a.len - b.len);
                    const best = b56matches[0];
                    const tag = best.el.tagName;
                    const bLower = best.txt.toLowerCase();
                    if ((/^(H[1-6]|LABEL|TH|DT|SPAN)$/.test(tag) ||
                         best.txt.endsWith(':')) &&
                        hintWords.some(w => wordMatch(bLower, w))) {
                        const sibVal = nextSiblingValue(best.el);
                        if (sibVal && hasAlpha(sibVal)) return sibVal;
                    }
                    return drillValue(best.el);
                }

                const b3scored = [];
                for (const el of allEls) {
                    const txt = (el.innerText || '').trim();
                    if (!txt || txt.length > 500 || !hasAlpha(txt)) continue;
                    const lower = txt.toLowerCase();
                    let score = 0;
                    for (const w of hintWords) {
                        if (wordMatch(lower, w)) score++;
                    }
                    if (score > 0)
                        b3scored.push({el, txt, score, len: txt.length});
                }
                if (b3scored.length > 0) {
                    b3scored.sort((a, b) =>
                        (b.score * a.len) - (a.score * b.len) || a.len - b.len);
                    const best = b3scored[0];
                    const tag = best.el.tagName;
                    if (/^(H[1-6]|LABEL|TH|DT|SPAN)$/.test(tag) ||
                        best.txt.endsWith(':')) {
                        const sibVal = nextSiblingValue(best.el);
                        if (sibVal && hasAlpha(sibVal)) return sibVal;
                    }
                    const drilled = drillValue(best.el);
                    if (hasAlpha(drilled)) return drilled;
                    return best.txt;
                }

                for (const el of inputs) {
                    const v = (el.value || '').toLowerCase();
                    if (hintWords.some(w => wordMatch(v, w)))
                        return el.value.trim();
                }
            }

            return null;
        }""", [target.lower(), hint])

        if val and var_m:
            self.memory[var_m.group(1)] = val.strip()
            print(f"    📦 COLLECTED: {val.strip()}")
            return True
        return False

    async def _handle_verify(self, page, step: str) -> bool:
        expected = extract_quoted(step)
        step_no_quotes = re.sub(r"'[^']*'", "", step)
        is_negative = bool(re.search(r'\b(NOT|HIDDEN|ABSENT)\b', step_no_quotes.upper()))
        state_check = "disabled" if re.search(r'\bDISABLED\b', step.upper()) else "enabled" if re.search(r'\bENABLED\b', step.upper()) else None
        is_checked_verify = bool(re.search(r'\bchecked\b', step.lower()))

        msg = f"    ⚙️  DOM HEURISTICS: Scanning for {expected}"
        if is_negative: msg += " [MUST BE ABSENT]"
        if state_check: msg += f" [{state_check.upper()}]"
        if is_checked_verify: msg += " [CHECKED]"
        print(msg)

        for retry in range(12):
            if is_checked_verify:
                raw_els = await self._snapshot(page, "clickable", [t.lower() for t in expected])
                scored  = self._score_elements(raw_els, step, "clickable", expected, None, False)
                if scored:
                    best   = scored[0]
                    xpath  = best["xpath"]
                    loc    = page.locator(f"xpath={xpath}").first
                    try: checked = await loc.is_checked(timeout=2000)
                    except Exception: checked = False
                    if is_negative:
                        ok = not checked
                        print(f"    {'✅' if ok else '❌'} Checkbox not-checked={ok}")
                        return ok
                    print(f"    {'✅' if checked else '❌'} Checkbox checked={checked}")
                    return checked
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                return False

            if state_check:
                search_text = expected[0] if expected else ""
                disabled_result = await page.evaluate("""(args) => {
                    const searchText = args[0].toLowerCase();
                    const wantDisabled = args[1] === 'disabled';
                    const els = Array.from(document.querySelectorAll('button, input, select, textarea, a, [role="button"], [role="menuitem"], [role="tab"], label'));
                    for (const el of els) {
                        const txt = (el.innerText || el.value || '').toLowerCase().trim();
                        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                        if (txt.includes(searchText) || aria.includes(searchText)) {
                            let isDisabled = el.disabled || el.getAttribute('aria-disabled') === 'true' || el.hasAttribute('disabled') || el.classList.contains('disabled');
                            if (el.tagName === 'LABEL' && el.control) isDisabled = isDisabled || el.control.disabled || el.control.hasAttribute('disabled');
                            return wantDisabled ? isDisabled : !isDisabled;
                        }
                    }
                    return null;
                }""", [search_text, state_check])
                
                if disabled_result is not None:
                    print(f"    {'✅' if disabled_result else '❌'} Element {state_check}={disabled_result}")
                    return disabled_result
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                return False

            text = await page.evaluate(VISIBLE_TEXT_JS)
            found = all(t.lower() in text for t in expected) if expected else bool(text)
            if is_negative:
                if not found:
                    print(f"    ✅ Verified ABSENT — OK")
                    return True
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                print(f"    ❌ Text still present after retries")
                return False
            else:
                if found:
                    print(f"    ✅ Verified — OK")
                    return True
                if retry < 11:
                    await asyncio.sleep(1)
                    continue
                print(f"    ❌ Not found after retries: {expected}")
                return False
        return False

    async def _do_drag(self, page, step: str, expected: list[str], source_id: int) -> bool:
        step_l = step.lower()
        target_text = ""
        m_to = re.search(r"to\s+['\"](.+?)['\"]", step_l)
        if m_to: target_text = m_to.group(1)
        elif len(expected) >= 2: target_text = expected[-1]

        raw_els = await self._snapshot(page, "drag", [target_text])
        dest = next((el for el in raw_els if el["id"] != source_id and target_text.lower() in el["name"].lower()), None)
        if not dest: return False

        src_el = next((el for el in raw_els if el["id"] == source_id), raw_els[0])
        src_loc  = page.locator(f"xpath={src_el['xpath']}").first
        dest_loc = page.locator(f"xpath={dest['xpath']}").first

        try:
            await src_loc.drag_to(dest_loc, timeout=5000)
        except Exception:
            sb = await src_loc.bounding_box()
            db = await dest_loc.bounding_box()
            if sb and db:
                await page.mouse.move(sb["x"] + sb["width"]/2, sb["y"] + sb["height"]/2)
                await page.mouse.down()
                await asyncio.sleep(0.3)
                await page.mouse.move(db["x"] + db["width"]/2, db["y"] + db["height"]/2, steps=20)
                await page.mouse.up()

        print(f"    🖱️  Dragged → '{dest['name'][:30]}'")
        await asyncio.sleep(ACTION_WAIT)
        return True

    async def _execute_step(self, page, step: str, strategic_context: str = "") -> bool:
        step_l = step.lower()
        words  = set(re.findall(r'\b[a-z]+\b', step_l))

        if   "drag" in words and "drop" in words:              mode = "drag"
        elif "select" in words or "choose" in words:           mode = "select"
        elif any(w in words for w in ("type","fill","enter")): mode = "input"
        elif any(w in words for w in ("click","double","check","uncheck")): mode = "clickable"
        elif "hover" in words:                                  mode = "hover"
        else:                                                   mode = "locate"

        preserve = mode in ("input", "select")
        expected = extract_quoted(step, preserve_case=preserve)

        target_field = None
        txt_to_type  = ""
        search_texts = []

        if mode == "input" and expected:
            txt_to_type  = expected[-1]
            search_texts = expected[:-1]
            m = re.search(r'(?:into\s+the\s+|into\s+)([a-zA-Z0-9_]+)\s*field', step_l)
            if m and m.group(1) not in ("that", "the", "a", "an"): target_field = m.group(1).lower()
        else:
            search_texts = expected

        if search_texts or target_field:
            self.last_xpath = None

        is_optional = bool(re.search(r'\bif\s+exists\b|\boptional\b', re.sub(r'''["'][^"']*["']''', '', step_l)))
        cache_key = (mode, tuple(t.lower() for t in search_texts), target_field)
        failed_ids = set()

        for attempt in range(3):
            try:
                el = await self._resolve_element(page, step, mode, search_texts, target_field, strategic_context, failed_ids=failed_ids)
            except Exception:
                if is_optional: return True
                raise

            if el is None:
                if mode == "locate" or is_optional: return True
                return False

            if el["id"] in failed_ids: continue

            self.last_xpath = el["xpath"]
            name, xpath, is_sel, is_shad, el_id, tag, itype = el["name"], el["xpath"], el.get("is_select"), el.get("is_shadow"), el["id"], el.get("tag_name", ""), el.get("input_type", "")

            if mode == "input" and itype in ("radio", "checkbox", "button", "submit", "image"):
                failed_ids.add(el_id)
                self.last_xpath = None
                continue

            if mode == "locate":
                try:
                    loc = page.locator(f"xpath={xpath}").first
                    if not is_shad: await loc.scroll_into_view_if_needed(timeout=2000)
                except Exception: pass
                print(f"    🔍 Located '{name[:40]}'")
                return True

            if mode == "drag": return await self._do_drag(page, step, expected, el_id)

            loc = page.locator(f"xpath={xpath}").first
            try:
                if not is_shad: await loc.scroll_into_view_if_needed(timeout=2000)
            except Exception: pass

            try:
                if mode == "input":
                    print(f"    ⌨️  Typed '{txt_to_type}' → '{name[:30]}'")
                    if is_shad: await page.evaluate(f"window.manulType({el_id}, '{txt_to_type}')")
                    else:
                        is_readonly = await loc.evaluate("el => el.readOnly || el.hasAttribute('readonly')")
                        if is_readonly:
                            escaped = txt_to_type.replace("'", "\\'")
                            await page.evaluate(f"el => {{ el.removeAttribute('readonly'); el.value = '{escaped}'; el.dispatchEvent(new Event('input', {{bubbles:true}})); el.dispatchEvent(new Event('change', {{bubbles:true}})); }}", await loc.element_handle())
                        else:
                            await loc.fill("", timeout=3000)
                            await loc.type(txt_to_type, delay=50, timeout=3000)
                    if "enter" in step_l:
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(4)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    self.last_xpath = None
                    return True

                elif mode == "select":
                    if is_sel:
                        opts = expected or [list(set(re.findall(r'\b[a-z0-9]{3,}\b', step_l)))[0]]
                        try: await loc.select_option(label=opts, timeout=3000)
                        except Exception: await loc.select_option(value=[o.lower() for o in opts], timeout=3000)
                    else: await loc.click(force=True, timeout=3000)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                elif mode == "hover":
                    print(f"    🚁  Hovered '{name[:30]}'")
                    if is_shad: await page.evaluate(f"window.manulElements[{el_id}].dispatchEvent(new MouseEvent('mouseover',{{bubbles:true,cancelable:true,view:window}}))")
                    else: await loc.hover(force=True, timeout=3000)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    await asyncio.sleep(ACTION_WAIT)
                    return True

                else:
                    print(f"    🖱️  Clicked '{name[:30]}'")
                    if is_shad:
                        fn = "manulDoubleClick" if "double" in step_l else "manulClick"
                        await page.evaluate(f"window.{fn}({el_id})")
                        await asyncio.sleep(ACTION_WAIT)
                    else:
                        if "double" in step_l:
                            await loc.dblclick(force=True, timeout=3000)
                        elif itype in ("checkbox", "radio", "file"):
                            await loc.evaluate("el => el.click()")
                        else:
                            await loc.click(force=True, timeout=3000)
                            if itype == "submit" or (tag == "button" and itype in ("", "submit")):
                                try: await page.wait_for_load_state("networkidle", timeout=10_000)
                                except Exception: await asyncio.sleep(3.0)
                        await asyncio.sleep(ACTION_WAIT)
                    self.learned_elements[cache_key] = {"name": name, "tag": tag}
                    return True

            except Exception as ex:
                failed_ids.add(el_id)
                self.last_xpath = None
                await asyncio.sleep(1)

        return False