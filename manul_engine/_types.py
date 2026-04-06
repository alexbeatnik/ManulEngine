"""Shared type definitions for ManulEngine internals.

This module is imported under ``TYPE_CHECKING`` only — it has zero runtime
cost.  Use it as the single source of truth for recurring dict shapes and
Playwright type aliases.
"""

from __future__ import annotations

from typing import TypedDict


class ElementSnapshot(TypedDict, total=False):
    """Shape of a single element returned by ``SNAPSHOT_JS``.

    All keys are optional (``total=False``) because the JS walker may omit
    some fields for SVG or non-standard elements.
    """

    id: int
    name: str
    xpath: str
    is_select: bool
    is_shadow: bool
    is_contenteditable: bool
    class_name: str
    tag_name: str
    input_type: str
    data_qa: str
    html_id: str
    icon_classes: str
    aria_label: str
    placeholder: str
    role: str
    disabled: bool
    aria_disabled: str | bool
    name_attr: str
    frame_index: int
    # Scoring / runtime additions
    score: int
    manul_id: str
