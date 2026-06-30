# manul_engine/cdp/keys.py
"""Keyboard name → ``Input.dispatchKeyEvent`` parameter mapping.

Ported from ManulEngine (Go)'s ``pkg/browser/cdp_backend.go`` key helpers. Maps the
spellings agents/LLMs emit ("enter", "ESC", "ctrl+a") to the canonical DOM
``KeyboardEvent.key`` values and the Windows virtual-key codes Chrome wants.
"""

from __future__ import annotations

_NORMALISE = {
    "enter": "Enter",
    "return": "Enter",
    "esc": "Escape",
    "escape": "Escape",
    "tab": "Tab",
    "space": " ",
    "spacebar": " ",
    "backspace": "Backspace",
    "delete": "Delete",
    "del": "Delete",
    "up": "ArrowUp",
    "arrowup": "ArrowUp",
    "down": "ArrowDown",
    "arrowdown": "ArrowDown",
    "left": "ArrowLeft",
    "arrowleft": "ArrowLeft",
    "right": "ArrowRight",
    "arrowright": "ArrowRight",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
}

_MODIFIER_BITS = {"alt": 1, "ctrl": 2, "control": 2, "meta": 4, "cmd": 4, "command": 4, "shift": 8}

_VIRTUAL_CODES = {
    "Enter": 13,
    "Tab": 9,
    "Escape": 27,
    "Backspace": 8,
    "Delete": 46,
    "ArrowUp": 38,
    "ArrowDown": 40,
    "ArrowLeft": 37,
    "ArrowRight": 39,
    "Home": 36,
    "End": 35,
    "PageUp": 33,
    "PageDown": 34,
    " ": 32,
    "F1": 112,
    "F2": 113,
    "F3": 114,
    "F4": 115,
    "F5": 116,
    "F6": 117,
    "F7": 118,
    "F8": 119,
    "F9": 120,
    "F10": 121,
    "F11": 122,
    "F12": 123,
}


def normalise_key(key: str) -> str:
    """Map a loose key spelling to the canonical ``KeyboardEvent.key`` value."""
    return _NORMALISE.get(key.strip().lower(), key.strip())


def parse_combo(combo: str) -> tuple[int, str]:
    """Split a key combo like ``"Control+Shift+A"`` into (modifier_bits, key)."""
    parts = [p for p in combo.replace(" ", "").split("+") if p]
    if not parts:
        return 0, ""
    *mods, key = parts
    bits = 0
    for m in mods:
        bits |= _MODIFIER_BITS.get(m.lower(), 0)
    return bits, normalise_key(key)


def key_text(key: str) -> str:
    """The character a key produces ("" for non-printing keys)."""
    if key == "Enter":
        return "\r"
    if key == " ":
        return " "
    if len(key) == 1:
        return key
    return ""


def key_code(key: str) -> str:
    """``KeyboardEvent.code`` for a canonical key value."""
    fixed = {
        "Enter": "Enter",
        "Tab": "Tab",
        "Escape": "Escape",
        " ": "Space",
        "Backspace": "Backspace",
        "Delete": "Delete",
    }
    if key in fixed:
        return fixed[key]
    if key in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown"):
        return key
    if len(key) == 1:
        c = key
        if c.isalpha():
            return "Key" + c.upper()
        if c.isdigit():
            return "Digit" + c
    return ""


def virtual_code(key: str) -> int:
    """Windows virtual-key code for a canonical key value."""
    if key in _VIRTUAL_CODES:
        return _VIRTUAL_CODES[key]
    if len(key) == 1:
        c = key
        if c.isalpha():
            return ord(c.upper())
        if c.isdigit():
            return ord(c)
    return 0


def key_event_params(key: str, *, modifiers: int = 0, is_down: bool) -> dict:
    """Build the ``Input.dispatchKeyEvent`` params for a key down/up."""
    params: dict[str, object] = {
        "type": "keyDown" if is_down else "keyUp",
        "key": key,
        "code": key_code(key),
        "windowsVirtualKeyCode": virtual_code(key),
        "modifiers": modifiers,
    }
    # Character-producing keys must carry text on keyDown (else Chrome treats it
    # as rawKeyDown: no keypress fires, Enter won't submit forms). Clear on keyUp.
    if is_down:
        text = key_text(key)
        if text:
            params["text"] = text
            params["unmodifiedText"] = text
    return params
