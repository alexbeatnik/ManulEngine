# manul_engine/js_scripts.py
"""
JavaScript constants injected into the browser page.

All page-level JS lives here to keep Python modules focused on logic.
"""

# ── Debug Modal ───────────────────────────────────────────────────────────────
# A lightweight floating panel injected into the live page during debug pauses.
# Shows the step text and an ✕ Abort button that sets window.__manul_debug_action.

DEBUG_MODAL_JS: str = """(stepText) => {
    const old = document.getElementById('manul-debug-modal');
    if (old) old.remove();
    window.__manul_debug_action = null;

    const modal = document.createElement('div');
    modal.id = 'manul-debug-modal';
    modal.setAttribute('data-manul-debug', 'true');
    modal.style.cssText = [
        'position:fixed', 'top:12px', 'right:12px', 'z-index:2147483647',
        'background:#1e1e2e', 'color:#cdd6f4',
        'border:2px solid #89b4fa', 'border-radius:8px',
        'padding:14px 40px 14px 16px',
        'font-family:monospace', 'font-size:13px',
        'max-width:420px', 'word-break:break-all',
        'box-shadow:0 4px 24px rgba(0,0,0,.55)',
        'pointer-events:all', 'user-select:none',
    ].join(';');

    const label = document.createElement('div');
    label.style.cssText = 'font-weight:bold;color:#89b4fa;margin-bottom:6px;font-size:11px;letter-spacing:.06em;';
    label.textContent = '\\uD83D\\uDC3E MANUL DEBUG PAUSE';

    const text = document.createElement('div');
    text.style.cssText = 'line-height:1.5;';
    text.textContent = stepText;

    const btn = document.createElement('button');
    btn.id = 'manul-debug-abort';
    btn.textContent = '\\u2715';
    btn.title = 'Abort test run';
    btn.style.cssText = [
        'position:absolute', 'top:8px', 'right:8px',
        'background:transparent', 'border:none',
        'color:#a6adc8', 'font-size:16px', 'font-weight:bold',
        'cursor:pointer', 'line-height:1', 'padding:2px 6px',
        'border-radius:4px', 'transition:background .15s,color .15s',
    ].join(';');
    btn.onmouseover = () => { btn.style.background='#f38ba8'; btn.style.color='#1e1e2e'; };
    btn.onmouseout  = () => { btn.style.background='transparent'; btn.style.color='#a6adc8'; };
    btn.addEventListener('click', () => { window.__manul_debug_action = 'ABORT'; });

    modal.appendChild(label);
    modal.appendChild(text);
    modal.appendChild(btn);
    document.body.appendChild(modal);
}"""

DEBUG_REMOVE_MODAL_JS: str = """() => {
    const m = document.getElementById('manul-debug-modal');
    if (m) m.remove();
    window.__manul_debug_action = null;
}"""

# ── DOM Helpers ───────────────────────────────────────────────────────────────

FIND_CONTAINER_XPATH_JS = """(xpath) => {
    const res = document.evaluate(
        xpath,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null,
    );
    let el = res.singleNodeValue;
    if (!el) return '';
    const ROW_TAGS = new Set(['TR', 'LI']);
    let curr = el.parentElement;
    while (curr && curr !== document.body) {
        if (
            ROW_TAGS.has(curr.tagName) ||
            curr.getAttribute('role') === 'row' ||
            (curr.tagName === 'DIV' && curr.dataset && curr.dataset.rowIndex !== undefined)
        ) {
            const parts = [];
            let n = curr;
            while (n && n.nodeType === Node.ELEMENT_NODE) {
                let idx = 1;
                let sib = n.previousElementSibling;
                while (sib) {
                    if (sib.tagName === n.tagName) idx++;
                    sib = sib.previousElementSibling;
                }
                parts.unshift(n.tagName.toLowerCase() + '[' + idx + ']');
                n = n.parentNode;
            }
            return '/' + parts.join('/');
        }
        curr = curr.parentElement;
    }
    return '';
}"""

FILTER_CONTAINER_DESCENDANT_XPATHS_JS = """({ containerXPath, candidateXPaths }) => {
    const resolve = xp => document.evaluate(
        xp,
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null,
    ).singleNodeValue;
    const container = resolve(containerXPath);
    if (!container) return [];
    const matches = [];
    for (const xp of candidateXPaths) {
        const node = resolve(xp);
        if (node && (node === container || container.contains(node))) {
            matches.push(xp);
        }
    }
    return matches;
}"""

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
    // ── Global element registry (idempotent) ──────────────────────────
    if (!window.manulElements) {
        window.manulElements = {};
        window.manulIdCounter = 0;
    }

    window.manulHighlight = (id, color, bg) => {
        const el = window.manulElements[id]; if (!el) return;
        el.scrollIntoView({ behavior:'smooth', block:'center' });
        const oB = el.style.border, oBg = el.style.backgroundColor;
        el.style.border = `4px solid ${color}`; el.style.backgroundColor = bg;
        setTimeout(() => { el.style.border = oB; el.style.backgroundColor = oBg; }, 2000);
    };
    window.manulClick = id => {
        const el = window.manulElements[id];
        if (el) { el.scrollIntoView({behavior:'smooth',block:'center'}); el.click(); }
    };
    window.manulDoubleClick = id => {
        const el = window.manulElements[id];
        if (el) el.dispatchEvent(new MouseEvent('dblclick', {bubbles:true}));
    };
    window.manulType = (id, text) => {
        const el = window.manulElements[id];
        if (!el) return;
        el.scrollIntoView({behavior:'smooth',block:'center'});
        if (el.isContentEditable || el.getAttribute('contenteditable') === 'true') {
            el.innerText = text;
        } else {
            el.value = text;
        }
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
    };

    // ── Tags to prune at traversal level (subtrees skipped entirely) ──
    const PRUNE = new Set([
        'SCRIPT','STYLE','NOSCRIPT','SVG','TEMPLATE',
        'META','PATH','G','BR','HR'
    ]);

    const isInputMode = mode === 'input';
    const hasCheckVis = typeof Element.prototype.checkVisibility === 'function';

    // ── Mode-dependent interactivity predicate ────────────────────────
    const ROLES = new Set([
        'button','checkbox','radio','tab','option','menuitem',
        'switch','slider','application','link','textbox','spinbutton'
    ]);
    const RE_CLS = /btn|button|swatch|card|tab|option|ui-drag|ui-drop/i;

    const isInteractive = isInputMode
        ? (el) => {
            const t = el.tagName;
            if (t === 'INPUT' || t === 'TEXTAREA') return true;
            if (el.getAttribute('contenteditable') === 'true') return true;
            const r = el.getAttribute('role');
            return r === 'textbox' || r === 'slider' || r === 'spinbutton';
        }
        : (el) => {
            const t = el.tagName;
            if (t === 'BUTTON' || t === 'A' || t === 'INPUT' || t === 'SELECT' ||
                t === 'TEXTAREA' || t === 'SUMMARY' || t === 'LABEL') return true;
            if (t === 'IMG') return !!el.getAttribute('alt');
            if (t.includes('-')) return true;
            const r = el.getAttribute('role');
            if (r && ROLES.has(r)) return true;
            if (el.hasAttribute('data-qa') || el.hasAttribute('data-testid')) return true;
            if (el.hasAttribute('aria-label') || el.hasAttribute('title')) return true;
            if (el.hasAttribute('onclick')) return true;
            if (el.id && (t === 'DIV' || t === 'SPAN')) return true;
            const cn = typeof el.className === 'string' ? el.className : '';
            if (cn && RE_CLS.test(cn)) return true;
            return false;
        };

    // ── Collection ────────────────────────────────────────────────────
    const seen    = new Set();
    const results = [];

    const processElement = (el, inShadow) => {
        if (seen.has(el)) return;
        seen.add(el);

        const tag = el.tagName;
        const isSpecialInput = tag === 'INPUT'
            && (el.type === 'file' || el.type === 'checkbox' || el.type === 'radio');

        // ── Visibility (minimal getComputedStyle in fallback only) ────
        let hidden = false;
        if (hasCheckVis) {
            if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) {
                if (!isSpecialInput) return;
                hidden = true;
            }
        } else {
            const cs = window.getComputedStyle(el);
            const hasLayout = el.offsetWidth > 0 && el.offsetHeight > 0;
            const styleHidden = cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0';
            if (!hasLayout || styleHidden) {
                if (!isSpecialInput) return;
                hidden = true;
            }
        }

        // ── Size gate ─────────────────────────────────────────────────
        const rect = el.getBoundingClientRect();
        if (rect.width < 2 || rect.height < 2) {
            const elRole = (el.getAttribute('role') || '').toLowerCase();
            if (elRole !== 'switch' && tag !== 'INPUT') return;
        }

        // ── Label deduplication (skip label when linked input visible) ─
        if (tag === 'LABEL') {
            const linked = el.htmlFor
                ? document.getElementById(el.htmlFor)
                : el.querySelector('input');
            if (linked && linked.type !== 'file') {
                const lr = linked.getBoundingClientRect();
                const vis = hasCheckVis
                    ? linked.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })
                    : (() => {
                        const cs = window.getComputedStyle(linked);
                        const hasLayout = linked.offsetWidth > 0 || linked.offsetHeight > 0;
                        const styleHidden = cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0';
                        return hasLayout && !styleHidden;
                    })();
                if (lr.width > 2 && lr.height > 2 && vis) return;
            }
        }

        results.push({ el, inShadow, hidden, rect });
    };

    // ── TreeWalker traversal (single pass, subtree pruning) ───────────
    const walk = (root, inShadow) => {
        const tw = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, {
            acceptNode(n) {
                if (PRUNE.has(n.tagName)) return NodeFilter.FILTER_REJECT;
                if (n.hasAttribute && n.hasAttribute('data-manul-debug')) return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        let n;
        while ((n = tw.nextNode())) {
            if (n.shadowRoot) walk(n.shadowRoot, true);
            if (isInteractive(n)) processElement(n, inShadow);
        }
    };

    walk(document.body || document.documentElement, false);

    // ── Assign stable runtime IDs (batched after layout reads to prevent CSS thrashing) ───
    for (let i = 0; i < results.length; i++) {
        const el = results[i].el;
        if (!el.dataset.manulId) {
            const id = window.manulIdCounter++;
            el.dataset.manulId = id;
            window.manulElements[id] = el;
        }
    }

    // ── Sort by vertical position (cached rects — no extra reflows) ───
    results.sort((a, b) => a.rect.top - b.rect.top);

    // ── XPath generator (sibling walk, no Array.from) ─────────────────
    const getXPath = el => {
        if (el.id) return `//*[@id="${el.id}"]`;
        const parts = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let idx = 1;
            let sib = el.previousElementSibling;
            while (sib) {
                if (sib.tagName === el.tagName) idx++;
                sib = sib.previousElementSibling;
            }
            parts.unshift(`${el.tagName.toLowerCase()}[${idx}]`);
            el = el.parentNode;
        }
        return `/${parts.join('/')}`;
    };

    // ── Label / context resolver ──────────────────────────────────────
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

            const fieldset = el.closest('fieldset');
            if (fieldset) {
                const leg = fieldset.querySelector('legend');
                if (leg) return leg.innerText.trim();
            }

            const wrapper = el.closest('.form-group, .row, div[class*="wrapper"]');
            if (wrapper) {
                const wrapLbl = wrapper.querySelector('label');
                if (wrapLbl) return wrapLbl.innerText.trim();
                const divLbl = wrapper.querySelector('div[class*="label"], span[class*="label"]');
                if (divLbl) return divLbl.innerText.trim();
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

    // ── Build output payload ──────────────────────────────────────────
    return results.map(({ el, inShadow, hidden, rect }) => {
        let name, isSelect = false;
        const iconClasses = Array.from(el.querySelectorAll('i, svg, span[class*="icon"]'))
            .map(i => (typeof i.className === 'string' ? i.className : (i.getAttribute('class') || '')))
            .join(' ').replace(/[-_]/g, ' ').toLowerCase();

        const htmlId    = el.id || el.getAttribute('for') || '';
        const elLabelFor = el.tagName === 'LABEL' ? (el.getAttribute('for') || '') : '';
        let ariaLabel = el.getAttribute('aria-label') || el.getAttribute('title') || '';
        if (!ariaLabel) {
            const labelledBy = el.getAttribute('aria-labelledby');
            if (labelledBy) {
                const lblEl = document.getElementById(labelledBy);
                if (lblEl) ariaLabel = lblEl.innerText.trim();
            }
        }

        let altText = '';
        if (['IMG', 'SVG', 'AREA'].includes(el.tagName)) {
            altText = el.getAttribute('alt') || '';
        }

        const nameAttr = el.getAttribute('name') || '';
        const ph = (el.placeholder || el.getAttribute('data-placeholder') || el.getAttribute('aria-placeholder') || '').toLowerCase();

        if (el.tagName === 'SELECT') {
            isSelect = true;
            name = 'dropdown [' + Array.from(el.options).map(o => o.text.trim()).join(' | ') + ']';
        } else {
            const rawText = el.innerText ? el.innerText.trim() : '';
            name = rawText || ariaLabel || altText || ph || nameAttr || el.getAttribute('value') || htmlId || el.className || 'item';
            name = name.trim();
        }

        if (el.tagName === 'INPUT') name += ` input ${el.type || ''}`;

        const ctx = labelFor(el);
        if (ctx)      name = `${ctx} -> ${name}`;
        if (inShadow) name += ' [SHADOW_DOM]';

        // Distinguish structural hiding (aria-hidden, off-screen LEFT)
        // from scroll-above (element scrolled above the viewport).
        // [HIDDEN] = intentionally hidden → scored with a penalty.
        // [ABOVE]  = temporarily off-screen → stripped for text matching.
        let isStructuralHidden = false;
        if (el.getAttribute('aria-hidden') === 'true') isStructuralHidden = true;
        if (rect.left < -999) isStructuralHidden = true;
        if (!isStructuralHidden && hidden) isStructuralHidden = true;

        const isScrollAbove = rect.top < -999 && !isStructuralHidden;

        if (isStructuralHidden) name += ' [HIDDEN]';
        else if (isScrollAbove) name += ' [ABOVE]';

        const isEditable = el.isContentEditable || el.getAttribute('contenteditable') === 'true';

        // ── Ancestor tag chain (for ON HEADER/FOOTER, INSIDE container) ──
        const ancestors = [];
        let _p = el.parentElement;
        for (let depth = 0; _p && depth < 8; depth++) {
            ancestors.push(_p.tagName.toLowerCase());
            _p = _p.parentElement;
        }

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
            name_attr:     nameAttr,
            label_for:     elLabelFor,
            rect_top:      Math.round(rect.top),
            rect_left:     Math.round(rect.left),
            rect_bottom:   Math.round(rect.bottom),
            rect_right:    Math.round(rect.right),
            ancestors:     ancestors,
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
                let row = null;
                const targetWords = t.split(/\\s+/).filter(w => w.length > 2);
                let maxMatches = 0;
                let bestLen = Infinity;
                for (const r of rows) {
                    const rText = r.innerText.toLowerCase();
                    let matches = 0;
                    if (targetWords.length === 0) {
                        if (wordMatch(rText, t)) matches = 1;
                    } else {
                        matches = targetWords.filter(w => wordMatch(rText, w)).length;
                    }
                    if (matches > maxMatches) {
                        maxMatches = matches;
                        bestLen = rText.length;
                        row = r;
                    } else if (matches === maxMatches && maxMatches > 0) {
                        if (rText.length < bestLen) {
                            bestLen = rText.length;
                            row = r;
                        }
                    }
                }
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

# ── Smart Page Scanner ────────────────────────────────────────────────────────
SCAN_JS = """() => {
    // ── Helpers ─────────────────────────────────────────────────────────────

    /** Return true if the element is visually hidden / off-screen. */
    function isHidden(el) {
        if (el.getAttribute('aria-hidden') === 'true') return true;
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return true;
        try {
            const st = window.getComputedStyle(el);
            if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) === 0) return true;
        } catch (_) {}
        return false;
    }

    /** Best human-readable label for an element (order: text, aria-label, placeholder, title, name, id). */
    function bestLabel(el) {
        const tag  = el.tagName ? el.tagName.toUpperCase() : '';
        const type = (el.getAttribute('type') || '').toLowerCase();
        // For radio/checkbox prefer the associated <label for="..."> text.
        if (tag === 'INPUT' && (type === 'radio' || type === 'checkbox')) {
            if (el.id) {
                const root = el.getRootNode();
                const lbl = root.querySelector('label[for="' + CSS.escape(el.id) + '"]');
                if (lbl) return lbl.innerText.trim();
            }
            const closestLbl = el.closest('label');
            if (closestLbl) return closestLbl.innerText.trim();
            const nextSib = el.nextElementSibling;
            if (nextSib && nextSib.tagName === 'LABEL') return nextSib.innerText.trim();
        }
        const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
        if (text && text.length <= 80) return text;
        const aria = el.getAttribute('aria-label') || '';
        if (aria.trim()) return aria.trim();
        const ph = el.getAttribute('placeholder') || '';
        if (ph.trim()) return ph.trim();
        const title = el.getAttribute('title') || '';
        if (title.trim()) return title.trim();
        const name = el.getAttribute('name') || '';
        if (name.trim()) return name.trim();
        const id = el.getAttribute('id') || '';
        if (id.trim()) return id.trim();
        return '';
    }

    /** Classify an element into one of our semantic types or null to skip. */
    function classify(el) {
        const tag = el.tagName ? el.tagName.toUpperCase() : '';
        const type = (el.getAttribute('type') || '').toLowerCase();
        const role = (el.getAttribute('role') || '').toLowerCase();

        if (tag === 'SELECT') return 'select';
        if (tag === 'INPUT' && type === 'checkbox') return 'checkbox';
        if (tag === 'INPUT' && type === 'radio') return 'radio';
        if (tag === 'INPUT' && !['submit', 'reset', 'image', 'hidden', 'button'].includes(type)) return 'input';
        if (tag === 'TEXTAREA') return 'input';
        if (tag === 'BUTTON') return 'button';
        if (tag === 'A' && el.getAttribute('href') !== null) return 'link';
        if (role === 'button') return 'button';
        if (role === 'link') return 'link';
        if (role === 'checkbox') return 'checkbox';
        if (role === 'radio') return 'radio';
        if (role === 'combobox') return 'select';
        if (role === 'switch') return 'checkbox';
        if (tag === 'INPUT' && type === 'submit') return 'button';
        if (tag === 'INPUT' && type === 'button') return 'button';
        return null;
    }

    /** Collect results from a DOM root (document or shadowRoot). */
    function scanRoot(root, results, seen) {
        const candidates = root.querySelectorAll(
            'button, a[href], input, select, textarea, ' +
            '[role="button"], [role="link"], [role="checkbox"], [role="radio"], ' +
            '[role="combobox"], [role="switch"]'
        );
        for (const el of candidates) {
            if (seen.has(el)) continue;
            seen.add(el);

            if (isHidden(el)) continue;
            const kind = classify(el);
            if (!kind) continue;
            const label = bestLabel(el);
            if (!label) continue;

            const entry = { type: kind, identifier: label };
            const mid = el.getAttribute('data-manul-id');
            if (mid !== null) {
                const parsedManulId = parseInt(mid, 10);
                if (Number.isFinite(parsedManulId)) entry.manul_id = parsedManulId;
            }
            // Include current value for fillable elements so callers can verify state.
            if ((kind === 'input' || kind === 'select') && el.value !== undefined && el.value !== '') {
                entry.value = el.value;
            }
            results.push(entry);
        }
        for (const el of root.querySelectorAll('*')) {
            if (el.shadowRoot) scanRoot(el.shadowRoot, results, seen);
        }
    }

    const results = [];
    const seen = new WeakSet();
    scanRoot(document, results, seen);
    return JSON.stringify(results);
}"""
