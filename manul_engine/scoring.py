# manul_engine/scoring.py
"""
Heuristic scoring logic for ManulEngine (v0.0.8.9).

Architecture:
  DOMScorer      — class with pre-compiled regex, per-invocation feature
                   caching, and modular scoring methods.
  score_elements — backward-compatible public function delegating to DOMScorer.

Each ``_score_*`` method returns a float representing the strength of
that heuristic category for a given element.  Most categories are
non-negative and tuned so that a single strong signal is ≈1.0, but
multiple sub-signals within the same category may **stack** and push
the score above 1.0.  The semantics channel may be negative when used
for cross-mode penalties.
``_calculate_penalties`` returns a **multiplier** in ``[0.0, 1.0]``.
``score_all()`` combines per-category scores via a ``WEIGHTS`` dictionary
and converts the weighted total to the integer scale consumed by
``core.py`` (via ``SCALE``).  There is no hard upper bound on the
combined score beyond what ``WEIGHTS`` and ``SCALE`` imply.

Scoring categories:
  1. Cache Reuse  — semantic cache and blind context reuse signals
  2. Text Match   — aria/placeholder, data-qa, name, icons, name_attr
  3. Attributes   — target_field, html_id variants, context words
  4. Semantics    — element type, role, mode synergy, cross-mode penalties
  5. Penalties    — disabled (×0.0), hidden (×0.1) → multiplier
  6. Proximity    — DOM depth-based form context bonus
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from .helpers import ContextualHint

if TYPE_CHECKING:
    from ._types import ElementSnapshot  # noqa: F401

# ── Pre-compiled regex patterns (compiled once at module load) ────────────────

_RE_WORD_BOUNDARY_3 = re.compile(r"\b[a-z0-9]{3,}\b")
_RE_WORD_3          = re.compile(r"[a-z0-9]{3,}")
_RE_WORD_BOUNDARY_4 = re.compile(r"\b[a-z]{4,}\b")
_RE_QUOTES          = re.compile(r"'[^']*'|\"[^\"]*\"")
_RE_HIDDEN          = re.compile(r"\[hidden\]", re.IGNORECASE)
_RE_SUFFIX          = re.compile(r"(\s*\[(hidden|above|shadow_dom)\])+$")
_RE_INPUT_SUFFIX    = re.compile(r"\s+input\s+\w*$")
_RE_BTN_DEV         = re.compile(r"\bbtn\b|-btn|btn-|button")
_RE_INP_DEV         = re.compile(r"\binp\b|-inp|inp-|input|\btxt\b|-txt|txt-|field")
_RE_CHK_DEV         = re.compile(r"\bchk\b|-chk|chk-|checkbox")
_RE_RAD_DEV         = re.compile(r"\brad\b|-rad|rad-|radio")
_RE_SEL_DEV         = re.compile(r"\bsel\b|-sel|sel-|select|\bdrop\b|-drop|drop-|\bcmb\b|-cmb|cmb-|combo")
_RE_OPTIONS         = re.compile(r"\[(.*?)\]")
_RE_DELIMITERS      = re.compile(r"[-_]")
_RE_DEV_BOUNDARIES  = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])")
_RE_BUTTON          = re.compile(r"\bbutton\b")
_RE_LINK            = re.compile(r"\blink\b")
_RE_IMAGE           = re.compile(r"\bimage\b|\bimg\b|\bpicture\b|\bphoto\b")
_RE_WANTS_INPUT     = re.compile(r"\bfield\b|\binput\b|\btextarea\b|\btype\b|\bfill\b")

# Context words stripped when extracting step context
_STOP_WORDS = frozenset({
    "click", "fill", "type", "enter", "select", "choose", "check", "uncheck",
    "hover", "button", "field", "input", "link", "checkbox", "radio",
    "from", "with", "into", "the", "that", "this", "step", "double",
    "image", "dropdown", "textarea", "optional", "exists", "shadow", "root",
})


# ── Pre-computed search term ──────────────────────────────────────────────────

class _SearchTerm:
    """Pre-computed search-term data for efficient per-element matching."""
    __slots__ = ("dashed", "id_variants", "text", "words")

    def __init__(self, raw: str) -> None:
        self.text: str = raw.lower().strip()
        self.dashed: str = self.text.replace(" ", "-").replace("_", "-")
        self.words: frozenset[str] = (
            frozenset(_RE_WORD_3.findall(self.text)) if self.text else frozenset()
        )
        # Variants for html_id matching (preserves original order, deduped)
        self.id_variants: tuple[str, ...] = (
            tuple(dict.fromkeys(filter(None, (
                self.text,
                self.text.replace(" ", "_"),
                self.text.replace(" ", "-"),
                self.text.replace(" ", ""),
            )))) if self.text else ()
        )


# ── Weighting & scale constants ──────────────────────────────────────────────

WEIGHTS: dict[str, float] = {
    "cache":      2.0,
    "text":       0.45,
    "attributes": 0.25,
    "semantics":  0.60,
    "proximity":  0.10,
}

# Converts the weighted float into the integer range expected by
# ``core.py`` thresholds (200k for semantic cache, 10k for confidence, etc.)
# Derived: SCALE = 3000 / (name_attr_exact * W_text) = 3000 / (0.0375 * 0.45)
SCALE: int = 177_778

# Maximum theoretical score used to normalise explain-mode output to
# the ``[0.0, 1.0]`` confidence range.  Equals ``SCALE`` so that a
# weighted sum of 1.0 maps to confidence 1.0.  Scores above this
# (e.g. semantic cache hits at ~355k) are clamped via ``min(..., 1.0)``.
MAX_THEORETICAL_SCORE: int = SCALE


# ── DOMScorer class ───────────────────────────────────────────────────────────

class DOMScorer:
    """Heuristic DOM element scorer.

    Instantiated once per ``score_elements()`` call with pre-computed step-level
    features.  Every ``_score_*`` method returns a **normalised float** —
    ``1.0`` represents a single perfect signal; stacking multiple strong signals
    can exceed ``1.0``.  ``_calculate_penalties`` returns a **multiplier** in
    ``[0.0, 1.0]``.  ``score_all()`` combines them via ``WEIGHTS`` and applies
    ``SCALE`` to produce the integer scores consumed by the rest of the engine.
    """

    def __init__(
        self,
        step: str,
        mode: str,
        search_texts: list[str],
        target_field: str | None,
        is_blind: bool,
        learned_elements: dict,
        last_xpath: str | None,
        explain: bool = False,
        contextual_hint: ContextualHint | None = None,
        anchor_rect: dict | None = None,
        container_elements: list[dict] | None = None,
        viewport_height: int = 0,
    ) -> None:
        self._step_l = step.lower()
        self._mode = mode
        self._target_field = target_field
        self._is_blind = is_blind
        self._last_xpath = last_xpath
        self._has_search_texts = bool(search_texts)
        self._explain = explain

        # Contextual proximity state
        self._hint = contextual_hint or ContextualHint(None, None, None)
        self._anchor_rect = anchor_rect          # {"rect_top", "rect_left", "rect_bottom", "rect_right", "frame_index", "xpath"}
        self._container_id_set = (
            {(e.get("frame_index", 0), e["id"]) for e in container_elements}
            if container_elements is not None else None
        )
        self._viewport_h = viewport_height or 900

        # Pre-compute search terms once
        self._terms: list[_SearchTerm] = [_SearchTerm(t) for t in search_texts]
        self._has_term_words: bool = any(term.words for term in self._terms)

        # Pre-compute step-level features (once per invocation)
        self._target_words:   frozenset[str] = frozenset(_RE_WORD_BOUNDARY_3.findall(self._step_l))
        self._anchor_words:   frozenset[str] = (
            frozenset(_RE_WORD_BOUNDARY_3.findall(str(self._hint.anchor or "").lower())) - _STOP_WORDS
        ) if self._hint.kind == "near" else frozenset()
        self._wants_button:   bool = bool(_RE_BUTTON.search(self._step_l))
        self._wants_link:     bool = bool(_RE_LINK.search(self._step_l))
        self._wants_image:    bool = bool(_RE_IMAGE.search(self._step_l))
        self._wants_input:    bool = bool(_RE_WANTS_INPUT.search(self._step_l))
        self._wants_checkbox: bool = "checkbox" in self._step_l
        self._wants_radio:    bool = "radio" in self._step_l
        self._wants_select:   bool = "select" in self._step_l or "dropdown" in self._step_l

        # Context words outside quoted strings
        step_no_quotes = _RE_QUOTES.sub("", self._step_l)
        self._context_words: frozenset[str] = (
            frozenset(_RE_WORD_BOUNDARY_4.findall(step_no_quotes)) - _STOP_WORDS
        )

        # Semantic cache lookup
        context_qualifier = None
        if self._hint.kind:
            context_qualifier = (
                self._hint.kind,
                str(self._hint.anchor or "").lower().strip() or None,
                str(self._hint.row_text or "").lower().strip() or None,
            )
        cache_key = (mode, tuple(t.lower() for t in search_texts), target_field, context_qualifier)
        self._learned_entry = learned_elements.get(cache_key)
        if self._learned_entry is None:
            legacy_cache_key = (mode, tuple(t.lower() for t in search_texts), target_field)
            self._learned_entry = learned_elements.get(legacy_cache_key)

    # ── Pre-processing ────────────────────────────────────────────────────

    @staticmethod
    def _safe_lower(val: object) -> str:
        """Safely lowercase a value that might not be a string (e.g. SVGAnimatedString)."""
        return val.lower() if isinstance(val, str) else ""

    def _preprocess(self, el: dict) -> None:
        """Attach normalised strings and type classifications to *el*.

        Called once per element before any scoring method runs.
        All computed keys use an underscore prefix to avoid collisions
        with the original SNAPSHOT_JS payload.
        """
        sl = self._safe_lower
        raw_data_qa = str(el.get("data_qa", ""))
        raw_html_id = str(el.get("html_id", ""))
        raw_class_name = str(el.get("class_name", ""))

        el["_name"]       = sl(el.get("name", ""))
        el["_tag"]        = el.get("tag_name", "")
        el["_itype"]      = el.get("input_type", "")
        el["_data_qa"]    = sl(raw_data_qa)
        el["_html_id"]    = sl(raw_html_id)
        el["_class_name"] = sl(raw_class_name)
        el["_icons"]      = sl(el.get("icon_classes", ""))
        el["_aria"]       = sl(el.get("aria_label", ""))
        el["_role"]       = sl(el.get("role", ""))
        el["_ph"]         = sl(el.get("placeholder", ""))
        el["_name_attr"]  = str(el.get("name_attr", "")).lower()
        el["_label_for"]  = str(el.get("label_for", "")).lower()
        el["_dev_names"]  = f"{el['_html_id']} {el['_class_name']} {el['_data_qa']}"
        if self._has_term_words:
            dev_pool = f"{raw_html_id} {raw_class_name} {raw_data_qa}"
            dev_pool = _RE_DEV_BOUNDARIES.sub(" ", dev_pool)
            dev_pool = _RE_DELIMITERS.sub(" ", dev_pool).lower()
            el["_dev_tokens"] = frozenset(_RE_WORD_3.findall(dev_pool))
        else:
            el["_dev_tokens"] = frozenset()

        # Name decomposition
        name = el["_name"]
        if " -> " in name:
            el["_name_core"]      = name.split(" -> ")[-1].strip()
            el["_context_prefix"] = name.split(" -> ")[0].strip().lower()
        else:
            el["_name_core"]      = name
            el["_context_prefix"] = ""

        # Hidden/suffix detection and stripping
        el["_is_hidden"]       = bool(_RE_HIDDEN.search(el["_name_core"]))
        el["_name_core"]       = _RE_SUFFIX.sub("", el["_name_core"]).strip()
        el["_name_core_clean"] = _RE_INPUT_SUFFIX.sub("", el["_name_core"]).strip()
        el["_name_words"]      = frozenset(_RE_WORD_3.findall(el["_name"]))

        # Element type classification
        tag   = el["_tag"]
        itype = el["_itype"]

        el["_is_native_button"] = (
            tag == "button"
            or (tag == "input" and itype in ("submit", "button", "image", "reset"))
        )
        el["_is_real_button"]   = el["_is_native_button"] or el["_role"] == "button"
        el["_is_real_link"]     = tag == "a" or el["_role"] == "link"
        el["_is_real_input"]    = (
            (tag in ("input", "textarea")
             and itype not in ("submit", "button", "image", "reset", "radio", "checkbox"))
            or el["_role"] in ("textbox", "searchbox", "spinbutton", "slider")
            or el.get("is_contenteditable", False)
        )
        el["_is_real_checkbox"] = (tag == "input" and itype == "checkbox") or el["_role"] == "checkbox"
        el["_is_real_radio"]    = (tag == "input" and itype == "radio")    or el["_role"] == "radio"

    # ── Scoring methods (return normalised floats) ─────────────────────

    def _score_cache_reuse(self, el: dict) -> float:
        """Semantic cache (1.0) and blind contextual reuse (0.05).

        Returns a float in ``[0.0, 1.05]``.  Combined with
        ``WEIGHTS["cache"] = 2.0`` and the module-level ``SCALE``, a pure
        semantic cache hit contributes ``2 * SCALE`` (≈355,556 with
        ``SCALE = 177_778``) to the final integer score; with an additional
        blind-context reuse signal the maximum contribution is
        ``2.1 * SCALE``.
        """
        score = 0.0
        learned = self._learned_entry
        if learned and el["name"] == learned["name"] and el["_tag"] == learned["tag"]:
            score += 1.0
        if self._is_blind and self._last_xpath and el["xpath"] == self._last_xpath:
            score += 0.05
        return min(score, 1.05)

    def _score_text_match(self, el: dict) -> tuple[float, bool]:
        """Text matching across aria, placeholder, data-qa, name, icons, name_attr.

        Returns ``(score, is_perfect_text_match)``.
        Scores are additive normalised floats (0.625 = strong single match,
        can exceed 1.0 when multiple strong signals stack).
        """
        score = 0.0
        is_perfect = False

        name       = el["_name"]
        name_core  = el["_name_core"]
        name_cc    = el["_name_core_clean"]
        ctx_prefix = el["_context_prefix"]
        aria       = el["_aria"]
        ph         = el["_ph"]
        html_id    = el["_html_id"]
        icons      = el["_icons"]
        name_attr  = el["_name_attr"]
        data_qa    = el["_data_qa"]
        name_words = el["_name_words"]

        for term in self._terms:
            tl = term.text
            if not tl:
                continue

            # ── Aria / placeholder exact match ────────────────────
            if tl == aria or tl == ph:
                score += 0.625          # 50k / 80k
                is_perfect = True
            elif len(tl) > 2 and aria.startswith(tl + " "):
                score += 0.0375         # 3k / 80k

            # ── data-qa match ─────────────────────────────────────
            if term.dashed == data_qa or tl == data_qa:
                score += 1.0            # perfect data-qa
                is_perfect = True
            elif term.dashed in data_qa:
                score += 0.0625         # 5k / 80k

            # ── Name matching ─────────────────────────────────────
            if tl == name_core or tl == name or tl == name_cc or tl == ctx_prefix:
                score += 0.625          # 50k / 80k
                is_perfect = True
            elif name_core.startswith(tl) or name_core.endswith(tl) or ctx_prefix.startswith(tl):
                score += 0.025          # 2k / 80k
            elif tl in name_core or tl in ctx_prefix:
                extra_words = max(0, len(name_core.split()) - len(tl.split()))
                score += max(0.0025, 0.0125 - extra_words * 0.001875)
            elif tl in name:
                extra_words = max(0, len(name.split()) - len(tl.split()))
                score += max(0.00125, 0.01 - extra_words * 0.00125)
            else:
                overlap = term.words & name_words
                if overlap:
                    score += len(overlap) * 0.001875
                if term.words and all(w in html_id for w in term.words):
                    score += 0.025

            # ── html_id / icon substring ──────────────────────────
            if tl in html_id:
                score += 0.0075         # 600 / 80k
            if any(w in icons for w in tl.split() if len(w) > 3):
                score += 0.00875        # 700 / 80k

            # ── HTML name attribute ───────────────────────────────
            if name_attr:
                if tl == name_attr:
                    score += 0.0375     # 3k / 80k
                elif len(name_attr) >= 3 and (tl in name_attr or name_attr in tl):
                    score += 0.0125     # 1k / 80k

            # ── Attribute semantic keyword match ──────────────────
            # Strong signal when search-term words appear as discrete
            # tokens in developer-facing attributes (html_id, class_name,
            # data_qa), including camelCase identifiers. Catches functional icons/links whose visible
            # text is unrelated (e.g. cart icon showing badge count "2"
            # with class="shopping_cart_link").
            if term.words:
                _matched = term.words & el["_dev_tokens"]
                if _matched:
                    coverage = len(_matched) / len(term.words)
                    if coverage >= 1.0:
                        score += 0.375 if len(term.words) >= 2 else 0.1875
                    elif coverage >= 0.5:
                        score += 0.1875 * coverage

        return score, is_perfect

    def _score_attributes(self, el: dict) -> float:
        """Target-field matching, html_id variants, context words, target-word signals.

        Returns a normalised float (can exceed 1.0 with stacked signals).
        """
        score   = 0.0
        name    = el["_name"]
        html_id = el["_html_id"]
        ph      = el["_ph"]
        aria    = el["_aria"]
        icons   = el["_icons"]

        # ── target_field matching ─────────────────────────────────
        tf = self._target_field
        if tf and (tf in name or tf == ph):
            score += 0.2
        if tf and html_id and html_id in (
            tf.replace(" ", "_"), tf.replace(" ", "-"), tf.replace(" ", ""),
        ):
            score += 0.6

        # ── Search-text → html_id variant matching ───────────────
        for term in self._terms:
            if term.text and html_id and html_id in term.id_variants:
                score += 0.4

        # ── Context words in developer names ──────────────────────
        if self._context_words:
            cls_n = _RE_DELIMITERS.sub(" ", el["_class_name"])
            id_n  = _RE_DELIMITERS.sub(" ", html_id)
            dqa_n = _RE_DELIMITERS.sub(" ", el["_data_qa"])
            dev_text = f"{cls_n} {id_n} {dqa_n}"
            ctx_hits = sum(1 for w in self._context_words if w in dev_text)
            if ctx_hits:
                score += min(ctx_hits * 0.08, 0.4)

        # ── NEAR anchor entity affinity in developer attributes ───
        # Product cards / repeated list items often encode the row/card label
        # in button ids like add-to-cart-sauce-labs-fleece-jacket. When NEAR
        # is active, reward candidates whose dev-facing attrs strongly overlap
        # the anchor text so entity-specific controls outrank nearby controls
        # from neighbouring cards.
        if self._hint.kind == "near" and self._anchor_words:
            anchor_hits = len(self._anchor_words & el["_dev_tokens"])
            if anchor_hits:
                coverage = anchor_hits / len(self._anchor_words)
                if coverage >= 1.0:
                    score += 0.6
                elif coverage >= 0.75:
                    score += 0.35
                elif coverage >= 0.5:
                    score += 0.12

        # ── Target-word signals ───────────────────────────────────
        score += sum(0.004 for w in self._target_words if w in name)
        score += sum(0.003 for w in self._target_words if len(w) > 3 and w in icons)
        score += sum(0.006 for w in self._target_words if len(w) > 3 and w in html_id)
        score += sum(0.005 for w in self._target_words if len(w) > 3 and w in aria)

        return score

    def _score_semantics(self, el: dict, is_perfect: bool, all_els: list[dict]) -> float:
        """Element type hints, mode synergy, cross-mode penalties, structural signals.

        Returns a normalised float (negative = cross-mode penalty).
        """
        score     = 0.0
        tag       = el["_tag"]
        itype     = el["_itype"]
        role      = el["_role"]
        dev_names = el["_dev_names"]

        # ── Shadow DOM bonus ──────────────────────────────────────
        if "shadow" in self._step_l and el.get("is_shadow"):
            score += 0.5

        # ── Element type hints ────────────────────────────────────
        if self._wants_button:
            if tag == "input" and itype == "submit":
                score += 0.016
            elif el["_is_native_button"]:
                score += 0.01
            elif el["_is_real_button"]:
                score += 0.006
            if el["_is_real_link"]:
                score -= 0.006
            if _RE_BTN_DEV.search(dev_names):
                score += 0.03

        if self._wants_image and tag == "img":
            score += 0.06

        if "textarea" in self._step_l and tag == "textarea":
            score += 0.1

        if self._wants_input:
            if el["_is_real_input"]:
                score += 0.01
            if el["_is_real_button"]:
                score -= 0.006
            if itype:
                if itype in self._step_l or (self._target_field and itype in self._target_field):
                    score += 0.1
            if _RE_INP_DEV.search(dev_names):
                score += 0.03

        # ── Strict checkbox / radio filtering ─────────────────────
        if self._wants_checkbox:
            if el["_is_real_checkbox"]:
                score += 0.5
            elif _RE_CHK_DEV.search(dev_names):
                score += 0.2
            else:
                score -= 1.0
        elif self._wants_radio:
            if el["_is_real_radio"]:
                score += 0.5
                if el["_context_prefix"] and any(
                    term.text == el["_context_prefix"] for term in self._terms if term.text
                ):
                    score += 0.1
            elif _RE_RAD_DEV.search(dev_names):
                score += 0.2
            else:
                score -= 1.0

        if self._wants_select:
            if _RE_SEL_DEV.search(dev_names):
                score += 0.04

        # ── Native select options ─────────────────────────────────
        if self._mode == "select" and el.get("is_select"):
            score += 0.1
            m = _RE_OPTIONS.search(el["_name"])
            options_text = m.group(1) if m else el["_name"]
            for term in self._terms:
                tl = term.text
                if tl and tl not in ("dropdown", "select", "list", "menu") and tl in options_text:
                    score += 0.6
                    break

        # ── Mode synergy ──────────────────────────────────────────
        if is_perfect:
            if self._mode in ("clickable", "hover") and (
                el["_is_real_button"] or el["_is_real_link"]
                or role in ("button", "link", "menuitem", "tab", "switch")
            ):
                score += 0.5
            elif self._mode == "input" and el["_is_real_input"]:
                score += 0.5
            elif self._mode == "select" and (
                el.get("is_select") or tag == "option"
                or role in ("option", "menuitem", "combobox", "button")
                or tag == "li"
            ):
                score += 0.5
        else:
            if self._mode in ("clickable", "hover"):
                if (el["_is_real_button"] or el["_is_real_link"]
                        or role in ("button", "link", "menuitem", "tab", "switch")):
                    score += 0.02
                elif tag in ("li", "summary", "td", "th", "tr"):
                    score += 0.01
            elif self._mode == "input":
                if el["_is_real_input"]:
                    score += 0.02
            elif self._mode == "select":
                if el.get("is_select"):
                    score += 0.03
                elif role in ("listbox", "combobox", "option", "menuitem", "button") or tag == "option":
                    score += 0.02
                elif tag == "li":
                    score += 0.016

        # ── Cross-mode penalties ──────────────────────────────────
        if self._mode == "select":
            if el["_is_real_checkbox"] and not self._wants_checkbox:
                score -= 1.0
            if el["_is_real_radio"] and not self._wants_radio:
                score -= 1.0
        elif self._mode == "input":
            if el["_is_real_checkbox"] or el["_is_real_radio"]:
                score -= 1.0
        elif self._mode == "clickable":
            if el["_is_real_input"] and not el["_is_native_button"] and self._wants_button:
                score -= 1.0

        # ── File uploads ──────────────────────────────────────────
        if tag == "label":
            label_for = el.get("_label_for", "")
            if label_for:
                linked_el = next(
                    (e for e in all_els
                     if str(e.get("_html_id", "")) == label_for
                     and str(e.get("input_type", "")).lower() == "file"),
                    None,
                )
                if linked_el:
                    score += 0.04
        if itype == "file":
            has_label = any(
                str(e.get("tag_name", "")).lower() == "label"
                and str(e.get("_label_for", "")) == el["_html_id"]
                for e in all_els
            )
            if has_label:
                score -= 0.06

        # ── Blind icon clicks ─────────────────────────────────────
        if self._is_blind and not self._has_search_texts:
            for w in self._target_words:
                if len(w) > 3 and w in el["_icons"]:
                    score += 0.06
                if len(w) > 3 and w in el["_html_id"]:
                    score += 0.03
                if len(w) > 3 and w in el["_aria"]:
                    score += 0.03

        return score

    def _calculate_penalties(self, el: dict) -> float:
        """Penalty multiplier for disabled and off-screen (hidden) elements.

        Returns a float in ``[0.0, 1.0]``:
        - ``1.0``  — normal element (no penalty)
        - ``0.1``  — hidden / off-screen element
        - ``0.0``  — disabled element (kills the score)
        """
        if el.get("disabled") or el.get("aria_disabled") == "true":
            return 0.0
        if el["_is_hidden"]:
            return 0.1
        return 1.0

    def _score_proximity(self, el: dict) -> float:
        """Contextual proximity scoring combining DOM depth, spatial distance,
        and region/container filtering.

        Returns a float in ``[0.0, 1.0]``.

        Contextual modes (when a hint is present):
                - **NEAR**: Euclidean pixel distance between element center and the
                    anchor element center, blended with DOM ancestry affinity when the
                    anchor xpath is known. This helps repeated card/list layouts prefer
                    controls inside the same logical container as the anchor instead of
                    a slightly closer control in a neighbouring card. Elements further
                    than ``_NEAR_THRESHOLD_PX`` get 0 spatial score.
        - **ON HEADER / ON FOOTER**: Elements in the top / bottom 15 % of the
          viewport, or inside ``<header>`` / ``<footer>`` ancestor tags, get a
          +1.0 boost.
        - **INSIDE**: Elements whose ID is in the pre-filtered container
          subtree set get +1.0; others get 0.

        When no contextual hint is active, falls back to the original
        DOM xpath-depth proximity with ``last_xpath``.
        """
        _NEAR_THRESHOLD_PX = 500

        kind = self._hint.kind

        # ── NEAR: Euclidean distance to anchor ────────────────────────
        if kind == "near" and self._anchor_rect:
            if self._anchor_rect.get("frame_index", 0) != el.get("frame_index", 0):
                return 0.0
            el_cx = (el.get("rect_left", 0) + el.get("rect_right", 0)) / 2.0
            el_cy = (el.get("rect_top", 0) + el.get("rect_bottom", 0)) / 2.0
            a = self._anchor_rect
            a_cx = (a.get("rect_left", 0) + a.get("rect_right", 0)) / 2.0
            a_cy = (a.get("rect_top", 0) + a.get("rect_bottom", 0)) / 2.0
            dist = math.sqrt((el_cx - a_cx) ** 2 + (el_cy - a_cy) ** 2)
            if dist <= _NEAR_THRESHOLD_PX:
                spatial_score = max(0.0, 1.0 - dist / _NEAR_THRESHOLD_PX)
                anchor_xpath = str(a.get("xpath", "") or "")
                candidate_xpath = str(el.get("xpath", "") or "")
                if anchor_xpath and candidate_xpath:
                    anchor_parts = [p for p in anchor_xpath.split("/") if p]
                    candidate_parts = [p for p in candidate_xpath.split("/") if p]
                    common_depth = 0
                    for p1, p2 in zip(anchor_parts, candidate_parts):
                        if p1 == p2:
                            common_depth += 1
                        else:
                            break
                    dom_affinity = common_depth / max(len(anchor_parts), len(candidate_parts), 1)
                    return min(1.0, spatial_score * 0.45 + dom_affinity * 0.55)
                return spatial_score
            return 0.0

        # ── ON HEADER / ON FOOTER: region filtering ──────────────────
        if kind == "on_header":
            if el.get("frame_index", 0) != 0:
                return 0.0
            ancestors = el.get("ancestors", [])
            if "header" in ancestors or "nav" in ancestors:
                return 1.0
            top = el.get("rect_top", 0)
            if 0 <= top <= self._viewport_h * 0.15:
                return 1.0
            return 0.0

        if kind == "on_footer":
            if el.get("frame_index", 0) != 0:
                return 0.0
            ancestors = el.get("ancestors", [])
            if "footer" in ancestors:
                return 1.0
            bottom = el.get("rect_bottom", 0)
            if bottom >= self._viewport_h * 0.85:
                return 1.0
            return 0.0

        # ── INSIDE: container subtree filtering ──────────────────────
        if kind == "inside" and self._container_id_set is not None:
            el_key = (el.get("frame_index", 0), el["id"])
            return 1.0 if el_key in self._container_id_set else 0.0

        # ── Default: DOM xpath-depth proximity ───────────────────────
        if not self._last_xpath or not el.get("xpath"):
            return 0.0
        last_parts = self._last_xpath.split("/")
        curr_parts = el["xpath"].split("/")
        common_depth = 0
        for p1, p2 in zip(last_parts, curr_parts):
            if p1 == p2:
                common_depth += 1
            else:
                break
        return min(common_depth, 5) * 0.2

    def _has_effective_context(self) -> bool:
        """Return True when the contextual hint has usable resolved data.

        Some hint kinds need additional runtime context to influence scoring
        meaningfully. If that data is missing, score_all() should keep the
        default proximity weight so a failed contextual lookup does not skew
        ranking away from text/semantic signals.
        """
        kind = self._hint.kind
        if not kind:
            return False
        if kind == "near":
            return self._anchor_rect is not None
        if kind == "inside":
            return bool(self._container_id_set)
        return True

    # ── Orchestrator ──────────────────────────────────────────────────

    def score_all(self, els: list[dict], early_exit_score: int | None = None) -> list[dict]:
        """Pre-process, score, and sort elements by score (descending).

        Combines normalised ``[0.0, 1.0]`` sub-scores via the ``WEIGHTS``
        dictionary, applies the penalty multiplier, and scales the result
        to the integer range expected by ``core.py``.

        When a contextual proximity hint is active and usable (NEAR with a
        resolved anchor, ON HEADER/FOOTER, INSIDE with a resolved container),
        the proximity weight is boosted to 1.5 so spatial/region signals
        strongly influence the final ranking.

        When ``self._explain`` is True, each element dict receives an
        ``"_explain"`` key containing the per-channel score breakdown.
        """
        w = dict(WEIGHTS)  # shallow copy — may be mutated for contextual boost
        effective_context = self._has_effective_context()
        if effective_context:
            w["proximity"] = 1.5  # boost from default 0.10 when contextual hint is effective

        scale = SCALE

        # Phase 1: attach normalised strings (single pass)
        for el in els:
            self._preprocess(el)

        # Phase 2: score each element via modular methods
        for el in els:
            cache_score            = self._score_cache_reuse(el)
            text_score, is_perfect = self._score_text_match(el)
            attr_score             = self._score_attributes(el)
            sem_score              = self._score_semantics(el, is_perfect, els)
            penalty_mult           = self._calculate_penalties(el)
            prox_score             = self._score_proximity(el)

            base = (
                text_score * w["text"]
                + attr_score * w["attributes"]
                + sem_score * w["semantics"]
                + prox_score * w["proximity"]
            )
            weighted = (base + cache_score * w["cache"]) * penalty_mult

            el["score"] = round(weighted * scale)

            if self._explain:
                _max = MAX_THEORETICAL_SCORE
                def _norm(weighted_channel: float, _max: float = _max) -> float:
                    return round(min(weighted_channel * scale / _max, 1.0), 3)

                explain_dict: dict = {
                    "text":       _norm(text_score * w["text"]),
                    "attributes": _norm(attr_score * w["attributes"]),
                    "semantics":  _norm(sem_score * w["semantics"]),
                    "proximity":  _norm(prox_score * w["proximity"]),
                    "cache":      _norm(cache_score * w["cache"]),
                    "penalty":    penalty_mult,
                    "total":      round(min(el["score"] / _max, 1.0), 3),
                }
                if self._hint.kind:
                    explain_dict["ctx_kind"] = self._hint.kind
                    explain_dict["ctx_prox_raw"] = round(prox_score, 3)
                el["_explain"] = explain_dict

            # Early exit optimisation: when an element scores above the
            # threshold, the remaining candidates are very unlikely to beat
            # it (cache reuse or exact data-qa matches are near-unique).
            # Skipping the rest avoids O(n) scoring on large DOMs.
            # Note: explain mode always scores all elements for completeness.
            if (
                early_exit_score is not None
                and not self._explain
                and el["score"] >= early_exit_score
            ):
                # Move the winning element to the front; unscored elements
                # keep their default score of 0 which is safe.
                els.remove(el)
                els.insert(0, el)
                return els

        return sorted(els, key=lambda x: x.get("score", 0), reverse=True)


# ── Backward-compatible public API ────────────────────────────────────────────

def score_elements(
    els: list[dict],
    step: str,
    mode: str,
    search_texts: list[str],
    target_field: str | None,
    is_blind: bool,
    learned_elements: dict,
    last_xpath: str | None,
    explain: bool = False,
    contextual_hint: ContextualHint | None = None,
    anchor_rect: dict | None = None,
    container_elements: list[dict] | None = None,
    viewport_height: int = 0,
) -> list[dict]:
    """Score and rank DOM elements against a given step.

    Backward-compatible entry point — delegates to :class:`DOMScorer`.
    """
    scorer = DOMScorer(
        step, mode, search_texts, target_field,
        is_blind, learned_elements, last_xpath,
        explain=explain,
        contextual_hint=contextual_hint,
        anchor_rect=anchor_rect,
        container_elements=container_elements,
        viewport_height=viewport_height,
    )
    return scorer.score_all(els)
