# engine/scoring.py
"""
Element scoring heuristics for ManulEngine.
The score_elements() function ranks DOM elements by relevance to a step.
"""

import re


def score_elements(
    els: list[dict],
    step: str,
    mode: str,
    search_texts: list[str],
    target_field: str | None,
    is_blind: bool,
    *,
    learned_elements: dict | None = None,
    last_xpath: str | None = None,
) -> list[dict]:
    """
    Score and sort elements by relevance to the given step.

    Parameters
    ----------
    learned_elements : semantic cache  {cache_key → {name, tag}}
    last_xpath       : xpath of previously resolved element (context memory)
    """
    step_l       = step.lower()
    target_words = set(re.findall(r'\b[a-z0-9]{3,}\b', step_l))

    wants_button = bool(re.search(r'\bbutton\b', step_l))
    wants_link   = bool(re.search(r'\blink\b',   step_l))
    wants_input  = bool(re.search(
        r'\bfield\b|\binput\b|\btextarea\b|\btype\b|\bfill\b', step_l
    ))

    cache_key = (mode, tuple(t.lower() for t in search_texts), target_field)
    learned   = (learned_elements or {}).get(cache_key)

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
        if is_blind and last_xpath and el["xpath"] == last_xpath:
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
