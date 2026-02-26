# engine/scoring.py
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
    wants_input  = bool(re.search(r'\bfield\b|\binput\b|\btextarea\b|\btype\b|\bfill\b', step_l))
    wants_checkbox = "checkbox" in step_l
    wants_select   = "select" in step_l or "dropdown" in step_l
    
    cache_key = (mode, tuple([t.lower() for t in search_texts]), target_field)
    learned = learned_elements.get(cache_key)

    for el in els:
        name       = el["name"].lower()
        tag        = el.get("tag_name", "")
        itype      = el.get("input_type", "")
        data_qa    = el.get("data_qa", "").lower()
        html_id    = el.get("html_id", "").lower()
        class_name = el.get("class_name", "").lower()
        icons      = el.get("icon_classes", "").lower()
        aria       = el.get("aria_label", "").lower()
        role       = el.get("role", "").lower()
        ph         = el.get("placeholder", "").lower()
        
        # Об'єднуємо всі технічні атрибути для пошуку патернів розробників
        dev_names = f"{html_id} {class_name} {data_qa}"
        
        score = 0

        # Severely penalize natively disabled elements (unless verifying)
        if el.get("disabled") or el.get("aria_disabled") == "true":
            score -= 50_000

        if learned and el["name"] == learned["name"] and tag == learned["tag"]:
            score += 20_000

        if is_blind and last_xpath and el["xpath"] == last_xpath:
            score += 10_000

        if target_field and (target_field in name or target_field == ph):
            score += 2_000

        name_core = name.split(" -> ")[-1].strip() if " -> " in name else name
        context_prefix = name.split(" -> ")[0].strip().lower() if " -> " in name else ""

        for t in search_texts:
            tl = t.lower().strip()
            if not tl:
                continue

            if tl == aria or tl == ph:
                score += 5_000
                
            t_dashed = tl.replace(" ", "-").replace("_", "-")
            
            if t_dashed == data_qa or tl == data_qa:
                score += 10_000
            elif t_dashed in data_qa:
                score += 3_000

            if tl == name_core or tl == name or tl == context_prefix:
                score += 5_000
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
                if overlap:
                    score += len(overlap) * 150

            if tl in html_id:     
                score += 600
            if any(w in icons for w in tl.split() if len(w) > 3):
                score += 700

        score += sum(10 for w in target_words if w in name)
        score += sum(8  for w in target_words if len(w) > 3 and w in icons)
        score += sum(15 for w in target_words if len(w) > 3 and w in html_id)
        score += sum(12 for w in target_words if len(w) > 3 and w in aria)

        is_native_button = tag == "button" or (tag == "input" and itype in ("submit", "button", "image", "reset"))
        is_real_button = is_native_button or role == "button"
        is_real_link   = tag == "a"
        is_real_input  = (
            (tag in ("input", "textarea") and itype not in ("submit", "button", "image", "reset", "radio", "checkbox")) 
            or role in ("textbox", "searchbox", "spinbutton") 
            or el.get("is_contenteditable", False)
        )
        is_real_checkbox = (tag == "input" and itype == "checkbox") or role == "checkbox"
        is_real_radio    = (tag == "input" and itype == "radio")    or role == "radio"

        # =====================================================================
        # DOM Element Type Validation & DEVELOPER NAMING CONVENTIONS
        # =====================================================================

        if wants_button:
            if is_native_button: score += 500
            elif is_real_button: score += 300
            if is_real_link:     score -= 300
            
            # Dev Convention: ID/Class contains 'btn' or 'button'
            if re.search(r'\bbtn\b|-btn|btn-|button', dev_names):
                score += 1500
            
        if "textarea" in step_l and tag == "textarea":
            score += 5000

        if wants_input:
            if is_real_input:    score += 500
            if is_real_button:   score -= 300
            
            if itype:
                if itype in step_l or (target_field and itype in target_field):
                    score += 5000
                    
            # Dev Convention: ID/Class contains 'inp', 'txt', 'field'
            if re.search(r'\binp\b|-inp|inp-|input|\btxt\b|-txt|txt-|field', dev_names):
                score += 1500

        if wants_checkbox:
            if is_real_checkbox: score += 15000
            elif itype in ("text", "password", "email", "number", "tel", "search") or tag == "textarea": score -= 10000
            elif "checkbox" not in name: score -= 5000
            
            # Dev Convention: ID/Class contains 'chk' or 'checkbox'
            if re.search(r'\bchk\b|-chk|chk-|checkbox', dev_names):
                score += 3000
                
        if "radio" in step_l:
            if is_real_radio: score += 15000
            elif itype in ("text", "password", "email", "number", "tel", "search") or tag == "textarea": score -= 10000
            elif "radio" in name: score += 200
            else: score -= 5000
            
            # Dev Convention: ID/Class contains 'rad' or 'radio'
            if re.search(r'\brad\b|-rad|rad-|radio', dev_names):
                score += 3000

        if wants_select:
            # Dev Convention: ID/Class contains 'sel', 'drop', 'cmb'
            if re.search(r'\bsel\b|-sel|sel-|select|\bdrop\b|-drop|drop-|\bcmb\b|-cmb|cmb-|combo', dev_names):
                score += 2000

        el["score"] = score

    return sorted(els, key=lambda x: x.get("score", 0), reverse=True)