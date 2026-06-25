# manul_engine/cdp/__init__.py
"""Native Chrome DevTools Protocol backend for ManulEngine.

Drives a system-installed Chrome over a raw WebSocket (single dependency:
``websockets``), replacing the Playwright layer. Public objects:

* :class:`CDPBrowser` — owns the Chrome process + browser-level connection.
* :class:`CDPPage`    — a page target (flat session) with per-frame contexts.
* :class:`CDPFrame` / :class:`CDPElement` — frame and resolved-node handles.
"""

from __future__ import annotations

from .browser import CDPBrowser
from .chrome import ChromeNotFoundError, ChromeProcess, find_chrome, launch_chrome
from .conn import CDPError, Conn
from .page import CDPElement, CDPFrame, CDPKeyboard, CDPMouse, CDPPage

__all__ = [
    "CDPBrowser",
    "CDPElement",
    "CDPError",
    "CDPFrame",
    "CDPKeyboard",
    "CDPMouse",
    "CDPPage",
    "ChromeNotFoundError",
    "ChromeProcess",
    "Conn",
    "find_chrome",
    "launch_chrome",
]
