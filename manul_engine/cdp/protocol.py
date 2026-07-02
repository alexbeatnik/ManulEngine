# manul_engine/cdp/protocol.py
"""JavaScript building blocks for the CDP backend.

These are the element-operation scripts ported from ManulEngine (Go)'s
``pkg/cdp/cdp.go`` (``SetInputValue``, ``SetChecked``, file-input resolution),
adapted to run as ``Runtime.callFunctionOn`` function declarations that receive
the target element as ``this`` instead of re-resolving it by id/xpath. The node
is resolved once to a RemoteObject (objectId); every subsequent operation binds
to that object, which automatically executes in the element's own frame —
giving correct per-frame routing for free.
"""

from __future__ import annotations

import json


def node_expression(selector: str) -> str:
    """JS expression resolving *selector* to a single DOM node (or null).

    Supports ``xpath=…`` / raw XPath, ``text=…`` (exact trimmed text match),
    and CSS (the default). Used with ``Runtime.evaluate`` in a frame context to
    obtain a RemoteObject for the element.
    """
    s = selector.strip()
    low = s.lower()
    if low.startswith("xpath="):
        return _xpath_expr(s[6:].strip())
    if s[:2] in ("//", "./") or s[:3] == "../" or s[:1] in ("/", "("):
        return _xpath_expr(s)
    if low.startswith("text="):
        return _text_expr(s[5:].strip().strip("'\""), last=False)
    return f"document.querySelector({json.dumps(s)})"


def node_expression_last(selector: str) -> str:
    """Like :func:`node_expression` but returns the LAST match (text/CSS)."""
    s = selector.strip()
    low = s.lower()
    if low.startswith("text="):
        return _text_expr(s[5:].strip().strip("'\""), last=True)
    return (
        f"(() => {{ const n = document.querySelectorAll({json.dumps(s)}); "
        "return n.length ? n[n.length - 1] : null; }})()"
    )


def _xpath_expr(xpath: str) -> str:
    return (
        f"document.evaluate({json.dumps(xpath)}, document, null, "
        "XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue"
    )


def _text_expr(text: str, *, last: bool) -> str:
    pick = "matches[matches.length - 1]" if last else "matches[0]"
    return (
        "(() => {"
        f"  const want = {json.dumps(text)};"
        "  const all = Array.from(document.querySelectorAll('*'));"
        "  const matches = all.filter(e => {"
        "    const t = (e.textContent || '').trim();"
        "    return t === want || t.includes(want);"
        "  }).filter(e => {"
        "    return !Array.from(e.children).some(c => (c.textContent || '').trim().includes(want));"
        "  });"
        f"  return matches.length ? {pick} : null;"
        "})()"
    )


# Function declaration: scroll the element to viewport centre.
SCROLL_INTO_VIEW_FN = """
function() {
    if (typeof this.scrollIntoView === 'function') {
        this.scrollIntoView({block: 'center', inline: 'center'});
    }
}
"""

# Function declaration: centre coordinates after instant scroll-into-view.
BOX_CENTER_FN = """
function() {
    if (typeof this.scrollIntoView === 'function') {
        this.scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'});
    }
    const r = this.getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height,
            cx: r.x + r.width / 2, cy: r.y + r.height / 2};
}
"""

# Function declaration: set an input/textarea/contenteditable value using the
# native value setter (so React/Vue/Angular state updates fire), with the
# label/wrapper → real-input refinement ported from cdp.go SetInputValue.
SET_VALUE_FN = r"""
function(value) {
    var el = this;
    if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA' && el.tagName !== 'SELECT'
        && el.getAttribute('contenteditable') !== 'true') {
        if (el.tagName === 'LABEL' && el.htmlFor) {
            el = document.getElementById(el.htmlFor) || el;
        } else {
            var child = el.querySelector('input, textarea, select');
            if (child) el = child;
        }
    }
    if (el.getAttribute && el.getAttribute('contenteditable') === 'true') {
        el.textContent = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
    }
    var proto = Object.getPrototypeOf(el);
    var setter = null;
    while (proto && proto !== Object.prototype) {
        var desc = Object.getOwnPropertyDescriptor(proto, 'value');
        if (desc && desc.set) { setter = desc.set; break; }
        proto = Object.getPrototypeOf(proto);
    }
    if (setter) { setter.call(el, value); } else { el.value = value; }
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    if (typeof el.focus === 'function') {
        try { el.focus({ preventScroll: true }); } catch (_) { el.focus(); }
    }
    return true;
}
"""

# Function declaration: native click via the element's own .click().
ELEMENT_CLICK_FN = "function() { this.click(); }"

# Function declaration: select an <option> by label or value, firing change.
SELECT_OPTION_FN = r"""
function(spec) {
    var el = this;
    if (el.tagName !== 'SELECT') {
        var inner = el.querySelector && el.querySelector('select');
        if (inner) el = inner;
    }
    if (el.tagName !== 'SELECT') return false;
    var labels = spec.labels || [];
    var values = spec.values || [];
    var matched = false;
    for (var i = 0; i < el.options.length; i++) {
        var opt = el.options[i];
        var byLabel = labels.some(function(l) {
            return (opt.label === l) || (opt.textContent || '').trim() === l
                || (opt.textContent || '').trim().toLowerCase() === String(l).toLowerCase();
        });
        var byValue = values.some(function(v) {
            return opt.value === v || opt.value.toLowerCase() === String(v).toLowerCase();
        });
        if (byLabel || byValue) { opt.selected = true; matched = true; }
    }
    if (matched) {
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return matched;
}
"""
