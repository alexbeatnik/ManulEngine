# engine/js_scripts.py
"""
JavaScript constants injected into the browser page.

All page-level JS lives here to keep Python modules focused on logic.
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
        "[class*='option']",
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
                    if (linked.type === 'file') {
                        // Keep this label — don't skip it
                    } else {
                        const lr = linked.getBoundingClientRect();
                        if (lr.width > 2 && lr.height > 2 && window.getComputedStyle(linked).display !== 'none') {
                            return;
                        }
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
            
            // NEW: Fallback for bad HTML where label is near input but without 'for' attr
            const wrapper = el.closest('.form-group, .row, div[class*="wrapper"]');
            if (wrapper) {
                const wrapLbl = wrapper.querySelector('label');
                if (wrapLbl) return wrapLbl.innerText.trim();
            }

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
            .map(i => (typeof i.className === 'string' ? i.className : (i.getAttribute('class') || '')))
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
            class_name:    (typeof el.className === 'string' ? el.className : (el.getAttribute('class') || '')),
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


# ── Data extraction (used by _handle_extract) ────────────────────────────────

EXTRACT_DATA_JS = """(args) => {
            const t = args[0];
            const hint = args[1];
            const currencyHint = args[2] || '';

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
            
            const stripLabel = (text) => {
                if (!text) return text;
                const m = text.match(/^([A-Za-z][A-Za-z ]+?)\\s*:\\s+(.+)$/);
                if (m && m[2].trim().length > 0) return m[2].trim();
                return text;
            };

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

            if (currencyHint) {
                const allPriceEls = Array.from(document.querySelectorAll(ALL_TAGS));
                const priceMatches = [];
                for (const el of allPriceEls) {
                    const txt = (el.innerText || '').trim();
                    if (!txt || txt.length > 100) continue;
                    if (txt.includes(currencyHint)) {
                        const childEls = el.querySelectorAll(VALUE_TAGS);
                        const isLeaf = childEls.length === 0 ||
                            Array.from(childEls).every(c => !(c.innerText || '').trim().includes(currencyHint) || c.innerText.trim() === txt);
                        if (isLeaf || txt.length < 30) {
                            priceMatches.push({el, txt, len: txt.length});
                        }
                    }
                }
                if (priceMatches.length === 1) {
                    return priceMatches[0].txt;
                }
                if (priceMatches.length > 1) {
                    if (hintWords.length > 0) {
                        for (const pm of priceMatches) {
                            const parent = pm.el.parentElement;
                            const ctx = parent ? (parent.innerText || '').toLowerCase() : '';
                            if (hintWords.some(w => ctx.includes(w) && !pm.txt.toLowerCase().includes(w))) {
                                return pm.txt;
                            }
                        }
                    }
                    priceMatches.sort((a, b) => a.len - b.len);
                    return priceMatches[0].txt;
                }
                const currSymEls = Array.from(document.querySelectorAll('span, div, i, b, strong'))
                    .filter(el => (el.innerText || '').trim() === currencyHint);
                for (const cEl of currSymEls) {
                    const parent = cEl.parentElement;
                    if (parent) {
                        const sibText = Array.from(parent.childNodes)
                            .map(n => (n.innerText || n.textContent || '').trim())
                            .filter(t => t.length > 0)
                            .join('');
                        if (sibText && /\\d/.test(sibText)) {
                            return currencyHint + sibText.replace(currencyHint, '').trim();
                        }
                    }
                }
            }

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

            const allEls = Array.from(document.querySelectorAll(ALL_TAGS));
            const inputs = Array.from(document.querySelectorAll(
                'input, textarea, select'));

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
                    const dtid = (el.getAttribute && el.getAttribute('data-testid') || '').toLowerCase();
                    if (hintWords.some(w => id.includes(w) || dq.includes(w) || dtid.includes(w))) {
                        const txt = (el.innerText || el.value || '').trim();
                        if (txt && hasAlpha(txt))
                            idMatches.push({el, txt});
                    }
                }
                if (idMatches.length > 0) {
                    idMatches.sort((a, b) => a.txt.length - b.txt.length);
                    return stripLabel(idMatches[0].txt);
                }
                
                const liveEls = Array.from(document.querySelectorAll('[aria-live]'));
                for (const el of liveEls) {
                    const txt = (el.innerText || '').trim();
                    if (txt && hasAlpha(txt) && txt.length < 100) {
                        const elId = (el.id || '').toLowerCase();
                        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                        if (hintWords.some(w => elId.includes(w) || aria.includes(w) || txt.toLowerCase().includes(w))) {
                            return txt;
                        }
                    }
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
                    return stripLabel(best.txt);
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
                    return stripLabel(drillValue(best.el));
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
        }"""


# ── Deep text collector (used by _handle_verify) ─────────────────────────────

DEEP_TEXT_JS = """() => {
    let text = document.body.innerText || "";
    function traverse(root) {
        root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) {
                text += " " + (el.shadowRoot.innerText || "");
                traverse(el.shadowRoot);
            }
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                text += " " + (el.value || "");
            }
        });
    }
    traverse(document);
    return text.toLowerCase();
}"""


# ── Disabled/enabled state checker (used by _handle_verify) ──────────────────

STATE_CHECK_JS = """(args) => {
    const searchText = args[0].toLowerCase();
    const wantDisabled = args[1] === 'disabled';
    const els = Array.from(document.querySelectorAll('button, input, select, textarea, a, [role="button"], [role="menuitem"], [role="tab"], label'));
    
    for (const el of els) {
        const txt = (el.innerText || el.value || '').toLowerCase().trim();
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        if (txt === searchText || aria === searchText) {
            let isDisabled = el.disabled || el.getAttribute('aria-disabled') === 'true' || el.hasAttribute('disabled') || el.classList.contains('disabled');
            if (el.tagName === 'LABEL' && el.control) isDisabled = isDisabled || el.control.disabled || el.control.hasAttribute('disabled');
            return wantDisabled ? isDisabled : !isDisabled;
        }
    }
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
}"""