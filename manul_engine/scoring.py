# manul_engine/scoring.py
"""
Heuristic scoring logic for ManulEngine.
Determines which element is the most likely target for a given step.
"""

import re

def score_elements(
    els: list[dict],
    step: str,
    mode: str,
    search_texts: list[str],
    target_field: str | None,
    is_blind: bool,
    learned_elements: dict,
    last_xpath: "str | None"
) -> list[dict]:
    
    step_l = step.lower()
    target_words = set(re.findall(r'\b[a-z0-9]{3,}\b', step_l))
    wants_button = bool(re.search(r'\bbutton\b', step_l))
    wants_link   = bool(re.search(r'\blink\b', step_l))
    wants_image  = bool(re.search(r'\bimage\b|\bimg\b|\bpicture\b|\bphoto\b', step_l))
    wants_input  = bool(re.search(r'\bfield\b|\binput\b|\btextarea\b|\btype\b|\bfill\b', step_l))
    wants_checkbox = "checkbox" in step_l
    wants_radio    = "radio" in step_l
    wants_select   = "select" in step_l or "dropdown" in step_l
    
    # Extract context words OUTSIDE the quoted parts of the step
    step_no_quotes = re.sub(r"'[^']*'|\"[^\"]*\"", "", step_l)
    context_words = set(re.findall(r'\b[a-z]{4,}\b', step_no_quotes)) - {
        "click", "fill", "type", "enter", "select", "choose", "check", "uncheck",
        "hover", "button", "field", "input", "link", "checkbox", "radio",
        "from", "with", "into", "the", "that", "this", "step", "double",
        "image", "dropdown", "textarea", "optional", "exists", "shadow", "root"
    }
    
    cache_key = (mode, tuple([t.lower() for t in search_texts]), target_field)
    learned = learned_elements.get(cache_key)

    for el in els:
        name       = el["name"].lower() if isinstance(el["name"], str) else ""
        tag        = el.get("tag_name", "")
        itype      = el.get("input_type", "")
        data_qa    = el.get("data_qa", "").lower() if isinstance(el.get("data_qa", ""), str) else ""
        html_id    = el.get("html_id", "").lower() if isinstance(el.get("html_id", ""), str) else ""
        class_name = el.get("class_name", "")
        class_name = class_name.lower() if isinstance(class_name, str) else ""
        icons      = el.get("icon_classes", "").lower() if isinstance(el.get("icon_classes", ""), str) else ""
        aria       = el.get("aria_label", "").lower() if isinstance(el.get("aria_label", ""), str) else ""
        role       = el.get("role", "").lower() if isinstance(el.get("role", ""), str) else ""
        ph         = el.get("placeholder", "").lower() if isinstance(el.get("placeholder", ""), str) else ""
        
        dev_names = f"{html_id} {class_name} {data_qa}"
        score = 0

        # Severely penalize natively disabled elements (unless verifying)
        if el.get("disabled") or el.get("aria_disabled") == "true":
            score -= 50_000

        # 1. SEMANTIC CACHE
        if learned and el["name"] == learned["name"] and tag == learned["tag"]:
            score += 200_000

        # 2. CONTEXTUAL REUSE
        if is_blind and last_xpath and el["xpath"] == last_xpath:
            score += 10_000

        # Target field match
        if target_field and (target_field in name or target_field == ph):
            score += 5_000

        if target_field and html_id and html_id in (target_field.replace(" ", "_"), target_field.replace(" ", "-"), target_field.replace(" ", "")):
            score += 15_000
            
        for t in search_texts:
            tl = t.lower().strip()
            if tl and html_id and html_id in (tl, tl.replace(" ", "_"), tl.replace(" ", "-"), tl.replace(" ", "")):
                score += 10_000

        name_core = name.split(" -> ")[-1].strip() if " -> " in name else name
        context_prefix = name.split(" -> ")[0].strip().lower() if " -> " in name else ""
        name_core_clean = re.sub(r'\s+input\s+\w*$', '', name_core).strip()
        
        is_native_button = tag == "button" or (tag == "input" and itype in ("submit", "button", "image", "reset"))
        is_real_button = is_native_button or role == "button"
        is_real_link   = tag == "a" or role == "link"
        is_real_input  = (
            (tag in ("input", "textarea") and itype not in ("submit", "button", "image", "reset", "radio", "checkbox")) 
            or role in ("textbox", "searchbox", "spinbutton", "slider")
            or el.get("is_contenteditable", False)
        )
        is_real_checkbox = (tag == "input" and itype == "checkbox") or role == "checkbox"
        is_real_radio    = (tag == "input" and itype == "radio")    or role == "radio"

        is_perfect_text_match = False

        # 3. TEXT MATCHING
        for t in search_texts:
            tl = t.lower().strip()
            if not tl: continue

            if tl == aria or tl == ph: 
                score += 50_000 
                is_perfect_text_match = True
            elif len(tl) > 2 and (aria.startswith(tl + " (") or aria.startswith(tl + " [")):
                score += 3_000
                
            t_dashed = tl.replace(" ", "-").replace("_", "-")
            if t_dashed == data_qa or tl == data_qa: 
                score += 80_000                  # Increased priority for QA attributes
                is_perfect_text_match = True     # Main fix: activates synergy
            elif t_dashed in data_qa: 
                score += 5_000

            if tl == name_core or tl == name or tl == name_core_clean or tl == context_prefix: 
                score += 50_000 
                is_perfect_text_match = True
            elif name_core.startswith(tl) or name_core.endswith(tl) or context_prefix.startswith(tl): 
                score += 2_000
            elif tl in name_core or tl in context_prefix:
                extra_words = max(0, len(name_core.split()) - len(tl.split()))
                score += max(200, 1_000 - extra_words * 150)
            elif tl in name:
                extra_words = max(0, len(name.split()) - len(tl.split()))
                score += max(100, 800 - extra_words * 100)
            else:
                t_words = set(re.findall(r'[a-z0-9]{3,}', tl))
                n_words = set(re.findall(r'[a-z0-9]{3,}', name))
                overlap = t_words & n_words
                if overlap: score += len(overlap) * 150
                if t_words and all(w in html_id for w in t_words):
                    score += 2_000

            if tl in html_id: score += 600
            if any(w in icons for w in tl.split() if len(w) > 3): score += 700

        if context_words:
            cls_normalized = re.sub(r'[-_]', ' ', class_name)
            id_normalized = re.sub(r'[-_]', ' ', html_id)
            dqa_normalized = re.sub(r'[-_]', ' ', data_qa)
            dev_text = f"{cls_normalized} {id_normalized} {dqa_normalized}"
            ctx_hits = sum(1 for w in context_words if w in dev_text)
            if ctx_hits: score += ctx_hits * 2_000

        score += sum(10 for w in target_words if w in name)
        score += sum(8  for w in target_words if len(w) > 3 and w in icons)
        score += sum(15 for w in target_words if len(w) > 3 and w in html_id)
        score += sum(12 for w in target_words if len(w) > 3 and w in aria)

        # 4. SHADOW DOM BONUS
        if "shadow" in step_l and el.get("is_shadow"):
            score += 50_000

        if wants_button:
            if tag == "input" and itype == "submit": score += 800
            elif is_native_button: score += 500
            elif is_real_button: score += 300
            if is_real_link:     score -= 300
            if re.search(r'\bbtn\b|-btn|btn-|button', dev_names): score += 1500

        if wants_image:
            if tag == "img": score += 3000
            
        if "textarea" in step_l and tag == "textarea":
            score += 5000

        if wants_input:
            if is_real_input:    score += 500
            if is_real_button:   score -= 300
            if itype:
                if itype in step_l or (target_field and itype in target_field): score += 5000
            if re.search(r'\binp\b|-inp|inp-|input|\btxt\b|-txt|txt-|field', dev_names): score += 1500

        # 5. STRICT CHECKBOX/RADIO FILTERING
        if wants_checkbox:
            if is_real_checkbox: 
                score += 50_000
            elif re.search(r'\bchk\b|-chk|chk-|checkbox', dev_names): 
                score += 20_000
            else:
                score -= 50_000
                
        elif wants_radio:
            if is_real_radio: 
                score += 50_000
            elif re.search(r'\brad\b|-rad|rad-|radio', dev_names): 
                score += 20_000
            else:
                score -= 50_000

        if wants_select:
            if re.search(r'\bsel\b|-sel|sel-|select|\bdrop\b|-drop|drop-|\bcmb\b|-cmb|cmb-|combo', dev_names): score += 2000
        
        # MASSIVE BOOST FOR NATIVE SELECT OPTIONS
        if mode == "select" and el.get("is_select"):
            score += 5_000
            m = re.search(r'\[(.*?)\]', name)
            options_text = m.group(1) if m else name
            for t in search_texts:
                tl = t.lower().strip()
                if tl and tl not in ("dropdown", "select", "list", "menu") and tl in options_text:
                    score += 60_000
                    break
                    
        # 6. MODE SYNERGY
        if is_perfect_text_match:
            if mode in ("clickable", "hover") and (is_real_button or is_real_link or role in ("button", "link", "menuitem", "tab", "switch")):
                score += 50_000
            elif mode == "input" and is_real_input:
                score += 50_000
            elif mode == "select" and (el.get("is_select") or tag == "option" or role in ("option", "menuitem", "combobox", "button") or tag == "li"):
                score += 50_000
        else:
            if mode in ("clickable", "hover"):
                if is_real_button or is_real_link or role in ("button", "link", "menuitem", "tab", "switch"):
                    score += 1_000
                elif tag in ("li", "summary", "td", "th", "tr"):
                    score += 500
            elif mode == "input":
                if is_real_input:
                    score += 1_000
            elif mode == "select":
                if el.get("is_select"):
                    score += 1_500
                elif role in ("listbox", "combobox", "option", "menuitem", "button") or tag == "option":
                    score += 1_000
                elif tag == "li":
                    score += 800

        # CROSS-MODE PENALTIES (Protects Dropdowns from Checkboxes)
        if mode == "select":
            if is_real_checkbox and not wants_checkbox:
                score -= 50_000
            if is_real_radio and not wants_radio:
                score -= 50_000
        elif mode == "input":
            if is_real_checkbox or is_real_radio:
                score -= 50_000
        
        # 7. FILE UPLOADS
        if tag == "label":
            linked_id = el.get("html_id", "")
            if linked_id:
                linked_el = next((e for e in els if str(e.get("html_id")) == linked_id and str(e.get("input_type")) == "file"), None)
                if linked_el: score += 2_000
        if itype == "file":
            has_label = any(str(e.get("tag_name")) == "label" and str(e.get("html_id")) == html_id for e in els)
            if has_label: score -= 3_000

        # 8. BLIND ICON CLICKS
        if is_blind and not search_texts:
            for w in target_words:
                if len(w) > 3 and w in icons: score += 3_000
                if len(w) > 3 and w in html_id: score += 1_500
                if len(w) > 3 and w in aria: score += 1_500

        # =====================================================================
        # 9. DOM PROXIMITY BONUS (Form Context Awareness)
        # =====================================================================
        if last_xpath and el.get("xpath"):
            last_parts = last_xpath.split('/')
            curr_parts = el["xpath"].split('/')
            common_depth = 0
            for p1, p2 in zip(last_parts, curr_parts):
                if p1 == p2:
                    common_depth += 1
                else:
                    break
            capped_depth = min(common_depth, 5)
            score += (capped_depth * 400)

        el["score"] = score

    return sorted(els, key=lambda x: x.get("score", 0), reverse=True)