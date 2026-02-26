# engine/js_scripts.py
"""
JavaScript constants injected into the browser page.
Separated from core.py to keep the main module readable.
"""

VISIBLE_TEXT_JS = """() => {
    let t = (document.body.innerText || "") + " ";
    document.querySelectorAll('*').forEach(el => {
        const st = window.getComputedStyle(el);
        const isHidden = st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0';
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
        const ariaLabel = el.getAttribute && el.getAttribute('aria-label');
        if (ariaLabel) t += ariaLabel + " ";
        const ariaValText = el.getAttribute && el.getAttribute('aria-valuetext');
        if (ariaValText) t += ariaValText + " ";
        if (el.shadowRoot)
            t += Array.from(el.shadowRoot.querySelectorAll('*'))
                      .map(e => e.innerText || e.value || '').join(' ');
    });
    return t.toLowerCase();
}"""

SNAPSHOT_JS = r"""([mode, expected_texts]) => {
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
        if (el.isContentEditable || el.getAttribute('contenteditable') === 'true') {
            el.innerText = text;
        } else {
            el.value=text;
        }
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
    };

    const INTERACTIVE_INPUT = "input,textarea,[contenteditable='true'],[role='textbox'],[role='slider'],[role='spinbutton']";
    const INTERACTIVE_CLICK = [
        "button","a","input[type='radio']","input[type='checkbox']",
        "select",".dropbtn","summary",
        ".ui-draggable",".ui-droppable","input",
        "label",
        "[role='button']","[role='checkbox']","[role='radio']",
        "[role='tab']","[role='option']","[role='menuitem']","[role='switch']",
        "[role='slider']","[role='application']","[role='link']",
        "[class*='btn']","[class*='button']","[class*='swatch']","[class*='card']","[class*='tab']",
        "[data-qa]","[data-testid]",
        "[aria-label]","[title]",
        "div[id]","span[id]",
        "[onclick]",
    ].join(",");

    const INTERACTIVE = (mode === "input") ? INTERACTIVE_INPUT : INTERACTIVE_CLICK;

    const seen    = new Set();
    const results = [];

    const collect = (root, inShadow=false) => {
        root.querySelectorAll(INTERACTIVE).forEach(el => {
            if (seen.has(el)) return;
            seen.add(el);

            const r  = el.getBoundingClientRect();
            const elRole = (el.getAttribute('role') || '').toLowerCase();
            
            const st = window.getComputedStyle(el);
            const isHidden = st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0';
            
            // Якщо елемент прихований, АЛЕ це не кастомний чекбокс/файл-інпут під лейблом - ігноруємо
            if (isHidden) {
                if (el.tagName !== 'INPUT' || (el.type !== 'file' && el.type !== 'checkbox' && el.type !== 'radio')) {
                    return; 
                }
            }
            
            if (r.width < 2 || r.height < 2) {
                if (elRole !== 'switch' && el.tagName !== 'INPUT') return;
            }

            if (el.tagName === 'LABEL') {
                const linked = el.htmlFor
                    ? document.getElementById(el.htmlFor)
                    : el.querySelector('input');
                if (linked) {
                    const lr = linked.getBoundingClientRect();
                    if (lr.width > 2 && lr.height > 2 && window.getComputedStyle(linked).display !== 'none') {
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

    results.sort((a,b) => a.el.getBoundingClientRect().top - b.el.getBoundingClientRect().top);

    const getXPath = el => {
        if(el.id) return `//*[@id="${el.id}"]`;
        const parts = [];
        while(el && el.nodeType === Node.ELEMENT_NODE) {
            const idx = Array.from(el.parentNode?.children || []).filter(s => s.tagName === el.tagName).indexOf(el) + 1;
            parts.unshift(`${el.tagName.toLowerCase()}[${idx}]`);
            el = el.parentNode;
        }
        return `/${parts.join('/')}`;
    };

    const labelFor = el => {
        if (el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio')) {
            const tr = el.closest('tr');
            if (tr) return tr.innerText.trim().replace(/\s+/g,' ');
            const lbl = el.closest('label') || document.querySelector(`label[for="${el.id}"]`);
            if (lbl) return lbl.innerText.trim();
            const nextSib = el.nextElementSibling;
            if (nextSib && nextSib.tagName === 'LABEL') return nextSib.innerText.trim();
            const prevSib = el.previousElementSibling;
            if (prevSib && prevSib.tagName === 'LABEL') return prevSib.innerText.trim();
            const par = el.parentElement;
            if (par) {
                const parText = par.innerText.trim().replace(/\s+/g,' ');
                if (parText && parText.length < 80) return parText;
            }
        }
        if (['INPUT','SELECT','TEXTAREA'].includes(el.tagName)) {
            const lbl = document.querySelector(`label[for="${el.id}"]`);
            if (lbl) return lbl.innerText.trim();
            let curr = el;
            while (curr && curr.tagName !== 'BODY') {
                let prev = curr.previousElementSibling;
                while (prev) {
                    if (/^H[1-6]$/.test(prev.tagName) || prev.classList.contains('title')) return prev.innerText.trim();
                    prev = prev.previousElementSibling;
                }
                curr = curr.parentElement;
            }
        }
        return '';
    };

    return results.map(({el, inShadow}) => {
        let name, isSelect = false;
        const iconClasses = Array.from(el.querySelectorAll('i, svg, span[class*="icon"]'))
            .map(i => i.className || i.getAttribute('class') || '')
            .join(' ').replace(/[-_]/g, ' ').toLowerCase();

        const htmlId    = el.id || el.getAttribute('for') || '';
        let ariaLabel = el.getAttribute('aria-label') || el.getAttribute('title') || '';
        if (!ariaLabel) {
            const labelledBy = el.getAttribute('aria-labelledby');
            if (labelledBy) {
                const lblEl = document.getElementById(labelledBy);
                if (lblEl) ariaLabel = lblEl.innerText.trim();
            }
        }
        
        const ph = (el.placeholder || el.getAttribute('data-placeholder') || el.getAttribute('aria-placeholder') || '').toLowerCase();

        if (el.tagName === 'SELECT') {
            isSelect = true;
            name = 'dropdown [' + Array.from(el.options).map(o => o.text.trim()).join(' | ') + ']';
        } else {
            const rawText = el.innerText ? el.innerText.trim() : '';
            name = rawText || ariaLabel || ph || el.getAttribute('value') || htmlId || el.name || el.className || 'item';
            name = name.trim();
        }

        if (el.tagName === 'INPUT') name += ` input ${el.type || ''}`;

        const ctx = labelFor(el);
        if (ctx)      name = `${ctx} -> ${name}`;
        if (inShadow) name += ' [SHADOW_DOM]';

        const isEditable = el.isContentEditable || el.getAttribute('contenteditable') === 'true';

        return {
            id:            parseInt(el.dataset.manulId),
            name:          name.substring(0, 150).replace(/\n/g, ' '),
            xpath:         getXPath(el),
            is_select:     isSelect,
            is_shadow:     inShadow,
            is_contenteditable: isEditable,
            class_name:    el.className || '',
            tag_name:      el.tagName.toLowerCase(),
            input_type:    el.type ? el.type.toLowerCase() : '',
            data_qa:       el.getAttribute('data-qa') || el.getAttribute('data-testid') || '',
            html_id:       htmlId,
            icon_classes:  iconClasses,
            aria_label:    ariaLabel,
            placeholder:   ph,
            role:          el.getAttribute('role') || '',
            disabled:      el.hasAttribute('disabled') || el.disabled || false,
            aria_disabled: el.getAttribute('aria-disabled') || '',
        };
    });
}"""