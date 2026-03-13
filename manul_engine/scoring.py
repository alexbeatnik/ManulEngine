# manul_engine/scoring.py
"""
Heuristic scoring logic for ManulEngine (v0.0.8.9).

Architecture:
  DOMScorer      — class with pre-compiled regex, per-invocation feature
                   caching, and modular scoring methods.
  score_elements — backward-compatible public function delegating to DOMScorer.

Scoring categories (additive integer system):
  1. Cache Reuse   — semantic cache (+200k) and blind context reuse (+10k)
  2. Text Match    — aria/placeholder, data-qa, name, icons, name_attr
  3. Attributes    — target_field, html_id variants, context words, target words
  4. Semantics     — element type, role, mode synergy, cross-mode penalties
  5. Penalties     — disabled, hidden/off-screen
  6. Proximity     — DOM depth-based form context bonus
"""

from __future__ import annotations

import re

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
    __slots__ = ("text", "dashed", "words", "id_variants")

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


# ── DOMScorer class ───────────────────────────────────────────────────────────

class DOMScorer:
    """Heuristic DOM element scorer.

    Instantiated once per ``score_elements()`` call with pre-computed step-level
    features.  Provides modular scoring methods that each return an integer
    score contribution (additive system preserving legacy thresholds).

    Score ranges (current additive system):
      Cache reuse:    up to +200,000
      Text match:     up to +80,000 per search term
      Attributes:     up to +15,000
      Semantics:      up to +60,000 (mode synergy), down to -200,000 (cross-mode)
      Penalties:      down to -50,000
      Proximity:      up to +2,000
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
    ) -> None:
        self._step_l = step.lower()
        self._mode = mode
        self._target_field = target_field
        self._is_blind = is_blind
        self._last_xpath = last_xpath
        self._has_search_texts = bool(search_texts)

        # Pre-compute search terms once
        self._terms: list[_SearchTerm] = [_SearchTerm(t) for t in search_texts]

        # Pre-compute step-level features (once per invocation)
        self._target_words:   frozenset[str] = frozenset(_RE_WORD_BOUNDARY_3.findall(self._step_l))
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
        cache_key = (mode, tuple(t.lower() for t in search_texts), target_field)
        self._learned_entry = learned_elements.get(cache_key)

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

        el["_name"]       = sl(el.get("name", ""))
        el["_tag"]        = el.get("tag_name", "")
        el["_itype"]      = el.get("input_type", "")
        el["_data_qa"]    = sl(el.get("data_qa", ""))
        el["_html_id"]    = sl(el.get("html_id", ""))
        el["_class_name"] = sl(el.get("class_name", ""))
        el["_icons"]      = sl(el.get("icon_classes", ""))
        el["_aria"]       = sl(el.get("aria_label", ""))
        el["_role"]       = sl(el.get("role", ""))
        el["_ph"]         = sl(el.get("placeholder", ""))
        el["_name_attr"]  = str(el.get("name_attr", "")).lower()
        el["_dev_names"]  = f"{el['_html_id']} {el['_class_name']} {el['_data_qa']}"

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

    # ── Scoring methods ───────────────────────────────────────────────────

    def _score_cache_reuse(self, el: dict) -> int:
        """Semantic cache reuse (+200k) and blind contextual reuse (+10k)."""
        score = 0
        learned = self._learned_entry
        if learned and el["name"] == learned["name"] and el["_tag"] == learned["tag"]:
            score += 200_000
        if self._is_blind and self._last_xpath and el["xpath"] == self._last_xpath:
            score += 10_000
        return score

    def _score_text_match(self, el: dict) -> tuple[int, bool]:
        """Text matching across aria, placeholder, data-qa, name, icons, name_attr.

        Returns ``(score, is_perfect_text_match)``.
        """
        score = 0
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
                score += 50_000
                is_perfect = True
            elif len(tl) > 2 and aria.startswith(tl + " "):
                score += 3_000

            # ── data-qa match ─────────────────────────────────────
            if term.dashed == data_qa or tl == data_qa:
                score += 80_000
                is_perfect = True
            elif term.dashed in data_qa:
                score += 5_000

            # ── Name matching ─────────────────────────────────────
            if tl == name_core or tl == name or tl == name_cc or tl == ctx_prefix:
                score += 50_000
                is_perfect = True
            elif name_core.startswith(tl) or name_core.endswith(tl) or ctx_prefix.startswith(tl):
                score += 2_000
            elif tl in name_core or tl in ctx_prefix:
                extra_words = max(0, len(name_core.split()) - len(tl.split()))
                score += max(200, 1_000 - extra_words * 150)
            elif tl in name:
                extra_words = max(0, len(name.split()) - len(tl.split()))
                score += max(100, 800 - extra_words * 100)
            else:
                overlap = term.words & name_words
                if overlap:
                    score += len(overlap) * 150
                if term.words and all(w in html_id for w in term.words):
                    score += 2_000

            # ── html_id / icon substring ──────────────────────────
            if tl in html_id:
                score += 600
            if any(w in icons for w in tl.split() if len(w) > 3):
                score += 700

            # ── HTML name attribute ───────────────────────────────
            if name_attr:
                if tl == name_attr:
                    score += 3_000
                elif len(name_attr) >= 3 and name_attr in tl:
                    score += 1_000

        return score, is_perfect

    def _score_attributes(self, el: dict) -> int:
        """Target-field matching, html_id variants, context words, target-word signals."""
        score   = 0
        name    = el["_name"]
        html_id = el["_html_id"]
        ph      = el["_ph"]
        aria    = el["_aria"]
        icons   = el["_icons"]

        # ── target_field matching ─────────────────────────────────
        tf = self._target_field
        if tf and (tf in name or tf == ph):
            score += 5_000
        if tf and html_id and html_id in (
            tf.replace(" ", "_"), tf.replace(" ", "-"), tf.replace(" ", ""),
        ):
            score += 15_000

        # ── Search-text → html_id variant matching ───────────────
        for term in self._terms:
            if term.text and html_id and html_id in term.id_variants:
                score += 10_000

        # ── Context words in developer names ──────────────────────
        if self._context_words:
            cls_n = _RE_DELIMITERS.sub(" ", el["_class_name"])
            id_n  = _RE_DELIMITERS.sub(" ", html_id)
            dqa_n = _RE_DELIMITERS.sub(" ", el["_data_qa"])
            dev_text = f"{cls_n} {id_n} {dqa_n}"
            ctx_hits = sum(1 for w in self._context_words if w in dev_text)
            if ctx_hits:
                score += ctx_hits * 2_000

        # ── Target-word signals ───────────────────────────────────
        score += sum(10 for w in self._target_words if w in name)
        score += sum(8  for w in self._target_words if len(w) > 3 and w in icons)
        score += sum(15 for w in self._target_words if len(w) > 3 and w in html_id)
        score += sum(12 for w in self._target_words if len(w) > 3 and w in aria)

        return score

    def _score_semantics(self, el: dict, is_perfect: bool, all_els: list[dict]) -> int:
        """Element type hints, mode synergy, cross-mode penalties, structural signals."""
        score     = 0
        tag       = el["_tag"]
        itype     = el["_itype"]
        role      = el["_role"]
        dev_names = el["_dev_names"]

        # ── Shadow DOM bonus ──────────────────────────────────────
        if "shadow" in self._step_l and el.get("is_shadow"):
            score += 50_000

        # ── Element type hints ────────────────────────────────────
        if self._wants_button:
            if tag == "input" and itype == "submit":
                score += 800
            elif el["_is_native_button"]:
                score += 500
            elif el["_is_real_button"]:
                score += 300
            if el["_is_real_link"]:
                score -= 300
            if _RE_BTN_DEV.search(dev_names):
                score += 1500

        if self._wants_image and tag == "img":
            score += 3000

        if "textarea" in self._step_l and tag == "textarea":
            score += 5000

        if self._wants_input:
            if el["_is_real_input"]:
                score += 500
            if el["_is_real_button"]:
                score -= 300
            if itype:
                if itype in self._step_l or (self._target_field and itype in self._target_field):
                    score += 5000
            if _RE_INP_DEV.search(dev_names):
                score += 1500

        # ── Strict checkbox / radio filtering ─────────────────────
        if self._wants_checkbox:
            if el["_is_real_checkbox"]:
                score += 50_000
            elif _RE_CHK_DEV.search(dev_names):
                score += 20_000
            else:
                score -= 50_000
        elif self._wants_radio:
            if el["_is_real_radio"]:
                score += 50_000
                if el["_context_prefix"] and any(
                    term.text == el["_context_prefix"] for term in self._terms if term.text
                ):
                    score += 5_000
            elif _RE_RAD_DEV.search(dev_names):
                score += 20_000
            else:
                score -= 50_000

        if self._wants_select:
            if _RE_SEL_DEV.search(dev_names):
                score += 2000

        # ── Native select options ─────────────────────────────────
        if self._mode == "select" and el.get("is_select"):
            score += 5_000
            m = _RE_OPTIONS.search(el["_name"])
            options_text = m.group(1) if m else el["_name"]
            for term in self._terms:
                tl = term.text
                if tl and tl not in ("dropdown", "select", "list", "menu") and tl in options_text:
                    score += 60_000
                    break

        # ── Mode synergy ──────────────────────────────────────────
        if is_perfect:
            if self._mode in ("clickable", "hover") and (
                el["_is_real_button"] or el["_is_real_link"]
                or role in ("button", "link", "menuitem", "tab", "switch")
            ):
                score += 50_000
            elif self._mode == "input" and el["_is_real_input"]:
                score += 50_000
            elif self._mode == "select" and (
                el.get("is_select") or tag == "option"
                or role in ("option", "menuitem", "combobox", "button")
                or tag == "li"
            ):
                score += 50_000
        else:
            if self._mode in ("clickable", "hover"):
                if (el["_is_real_button"] or el["_is_real_link"]
                        or role in ("button", "link", "menuitem", "tab", "switch")):
                    score += 1_000
                elif tag in ("li", "summary", "td", "th", "tr"):
                    score += 500
            elif self._mode == "input":
                if el["_is_real_input"]:
                    score += 1_000
            elif self._mode == "select":
                if el.get("is_select"):
                    score += 1_500
                elif role in ("listbox", "combobox", "option", "menuitem", "button") or tag == "option":
                    score += 1_000
                elif tag == "li":
                    score += 800

        # ── Cross-mode penalties ──────────────────────────────────
        if self._mode == "select":
            if el["_is_real_checkbox"] and not self._wants_checkbox:
                score -= 50_000
            if el["_is_real_radio"] and not self._wants_radio:
                score -= 50_000
        elif self._mode == "input":
            if el["_is_real_checkbox"] or el["_is_real_radio"]:
                score -= 50_000
        elif self._mode == "clickable":
            if el["_is_real_input"] and not el["_is_native_button"] and self._wants_button:
                score -= 200_000

        # ── File uploads ──────────────────────────────────────────
        if tag == "label":
            linked_id = el.get("html_id", "")
            if linked_id:
                linked_el = next(
                    (e for e in all_els
                     if str(e.get("html_id")) == linked_id
                     and str(e.get("input_type")) == "file"),
                    None,
                )
                if linked_el:
                    score += 2_000
        if itype == "file":
            has_label = any(
                str(e.get("tag_name")) == "label"
                and str(e.get("html_id")) == el["_html_id"]
                for e in all_els
            )
            if has_label:
                score -= 3_000

        # ── Blind icon clicks ─────────────────────────────────────
        if self._is_blind and not self._has_search_texts:
            for w in self._target_words:
                if len(w) > 3 and w in el["_icons"]:
                    score += 3_000
                if len(w) > 3 and w in el["_html_id"]:
                    score += 1_500
                if len(w) > 3 and w in el["_aria"]:
                    score += 1_500

        return score

    def _calculate_penalties(self, el: dict) -> int:
        """Penalties for disabled and off-screen (hidden) elements."""
        score = 0
        if el.get("disabled") or el.get("aria_disabled") == "true":
            score -= 50_000
        if el["_is_hidden"]:
            score -= 5_000
        return score

    def _score_proximity(self, el: dict) -> int:
        """DOM proximity bonus based on shared xpath depth with last resolved element."""
        if not self._last_xpath or not el.get("xpath"):
            return 0
        last_parts = self._last_xpath.split("/")
        curr_parts = el["xpath"].split("/")
        common_depth = 0
        for p1, p2 in zip(last_parts, curr_parts):
            if p1 == p2:
                common_depth += 1
            else:
                break
        return min(common_depth, 5) * 400

    # ── Orchestrator ──────────────────────────────────────────────────

    def score_all(self, els: list[dict]) -> list[dict]:
        """Pre-process, score, and sort elements by score (descending)."""
        # Phase 1: attach normalised strings (single pass)
        for el in els:
            self._preprocess(el)

        # Phase 2: score each element via modular methods
        for el in els:
            cache_score            = self._score_cache_reuse(el)
            text_score, is_perfect = self._score_text_match(el)
            attr_score             = self._score_attributes(el)
            sem_score              = self._score_semantics(el, is_perfect, els)
            penalty_score          = self._calculate_penalties(el)
            proximity_score        = self._score_proximity(el)

            el["score"] = (
                cache_score
                + text_score
                + attr_score
                + sem_score
                + penalty_score
                + proximity_score
            )

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
    last_xpath: "str | None",
) -> list[dict]:
    """Score and rank DOM elements against a given step.

    Backward-compatible entry point — delegates to :class:`DOMScorer`.
    """
    scorer = DOMScorer(
        step, mode, search_texts, target_field,
        is_blind, learned_elements, last_xpath,
    )
    return scorer.score_all(els)