# manul_engine/conditionals.py
"""
Condition evaluator for if/elif/else conditional blocks in the Hunt DSL.

Supported condition forms:
  - ``button 'Save' exists``  /  ``element 'Banner' exists``
  - ``button 'Save' not exists``  /  ``element 'Error' not exists``
  - ``text 'Welcome' is present``  /  ``text 'Error' is not present``
  - ``{variable} == 'value'``  /  ``{variable} != 'value'``
  - ``{variable} contains 'substr'``
  - ``{variable}``  (truthy check — non-empty and not 'false'/'0')
"""

import re
from typing import TYPE_CHECKING

from .js_scripts import VISIBLE_TEXT_JS
from .logging_config import logger

if TYPE_CHECKING:
    from .cdp import CDPPage as Page

    from .variables import ScopedVariables

_log = logger.getChild("conditionals")

# ── Condition patterns (order matters — most specific first) ──────────────────

# element/button/link/field 'Target' exists / not exists
_RE_ELEMENT_EXISTS = re.compile(
    r"^(?:button|element|link|field|input|checkbox|radio|dropdown)\s+"
    r"""(?P<q>['"])(?P<target>.+?)(?P=q)\s+(?P<neg>not\s+)?exists\s*$""",
    re.IGNORECASE,
)

# text 'Something' is present / is not present
_RE_TEXT_PRESENT = re.compile(
    r"""^text\s+(?P<q>['"])(?P<target>.+?)(?P=q)\s+is\s+(?P<neg>not\s+)?present\s*$""",
    re.IGNORECASE,
)

# {variable} == 'value' / {variable} != 'value'
_RE_VAR_COMPARE = re.compile(
    r"""^\{?(?P<var>\w+)\}?\s*(?P<op>==|!=)\s*(?P<q>['"])(?P<value>.+?)(?P=q)\s*$""",
)

# {variable} contains 'substring'
_RE_VAR_CONTAINS = re.compile(
    r"""^\{?(?P<var>\w+)\}?\s+contains\s+(?P<q>['"])(?P<value>.+?)(?P=q)\s*$""",
    re.IGNORECASE,
)

# {variable} (bare truthy check)
_RE_VAR_TRUTHY = re.compile(
    r"""^\{?(?P<var>\w+)\}?\s*$""",
)


async def evaluate_condition(
    condition: str,
    page: "Page | None",
    memory: "ScopedVariables",
) -> bool:
    """Evaluate a single DSL condition expression.

    *page* may be ``None`` for variable-only conditions.  Page-dependent
    conditions (element-exists, text-present) raise ``ValueError`` when
    *page* is ``None``.

    Returns ``True`` if the condition is met, ``False`` otherwise.
    Raises ``ValueError`` for unrecognized condition syntax.
    """
    cond = condition.strip()

    # ── element/button 'Target' [not] exists ──
    m = _RE_ELEMENT_EXISTS.match(cond)
    if m:
        if page is None:
            raise ValueError(f"Page-dependent condition requires an active page: {cond!r}")
        target = m.group("target")
        negate = bool(m.group("neg"))
        found = await _element_exists(page, target)
        result = (not found) if negate else found
        _log.debug(
            "Condition '%s': element_exists=%s, negate=%s → %s",
            cond,
            found,
            negate,
            result,
        )
        return result

    # ── text 'Something' is [not] present ──
    m = _RE_TEXT_PRESENT.match(cond)
    if m:
        if page is None:
            raise ValueError(f"Page-dependent condition requires an active page: {cond!r}")
        target = m.group("target")
        negate = bool(m.group("neg"))
        found = await _text_present(page, target)
        result = (not found) if negate else found
        _log.debug(
            "Condition '%s': text_present=%s, negate=%s → %s",
            cond,
            found,
            negate,
            result,
        )
        return result

    # ── {var} == 'value' / {var} != 'value' ──
    m = _RE_VAR_COMPARE.match(cond)
    if m:
        var_name = m.group("var")
        op = m.group("op")
        expected = m.group("value")
        actual = str(memory.get(var_name, ""))
        if op == "==":
            result = actual == expected
        else:
            result = actual != expected
        _log.debug(
            "Condition '%s': {%s}='%s' %s '%s' → %s",
            cond,
            var_name,
            actual,
            op,
            expected,
            result,
        )
        return result

    # ── {var} contains 'substring' ──
    m = _RE_VAR_CONTAINS.match(cond)
    if m:
        var_name = m.group("var")
        substring = m.group("value")
        actual = str(memory.get(var_name, ""))
        result = substring in actual
        _log.debug(
            "Condition '%s': {%s}='%s' contains '%s' → %s",
            cond,
            var_name,
            actual,
            substring,
            result,
        )
        return result

    # ── {var} — truthy check ──
    m = _RE_VAR_TRUTHY.match(cond)
    if m:
        var_name = m.group("var")
        actual = str(memory.get(var_name, ""))
        result = bool(actual) and actual.lower() not in ("false", "0", "none", "")
        _log.debug(
            "Condition '%s': {%s}='%s' → truthy=%s",
            cond,
            var_name,
            actual,
            result,
        )
        return result

    raise ValueError(f"Unrecognized condition syntax: {cond!r}")


_ELEMENT_EXISTS_JS = """
(target) => {
    const t = (target || '').toLowerCase().trim();
    if (!t) return false;
    const visible = (el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
    };
    const attr = (el, n) => ((el.getAttribute && el.getAttribute(n)) || '').toLowerCase();
    for (const el of document.querySelectorAll('*')) {
        const txt = (el.textContent || '').trim().toLowerCase();
        const matches =
            txt === t || txt.includes(t) ||
            attr(el, 'aria-label') === t || attr(el, 'placeholder') === t ||
            attr(el, 'title') === t || attr(el, 'name') === t || attr(el, 'value') === t;
        if (matches && visible(el)) return true;
    }
    return false;
}
"""


async def _element_exists(page: "Page", target: str) -> bool:
    """Check whether an element matching *target* is visible on the page.

    Replaces Playwright's get_by_text/role/label/placeholder strategies with a
    single DOM scan covering visible text plus aria-label/placeholder/title/name.
    """
    try:
        return bool(await page.evaluate(_ELEMENT_EXISTS_JS, target))
    except Exception:
        return False


async def _text_present(page: "Page", target: str) -> bool:
    """Check whether *target* text is visible on the page body."""
    try:
        visible_text = await page.evaluate(VISIBLE_TEXT_JS)
        if target.lower() in str(visible_text).lower():
            return True
        # Fallback: broad DOM scan for a visible element matching the text.
        return await _element_exists(page, target)
    except Exception:
        return False
