# engine/js_scripts.py
"""
JavaScript constants injected into the browser page.
Separated from core.py to keep the main module readable.
"""

VISIBLE_TEXT_JS = """() => {
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
