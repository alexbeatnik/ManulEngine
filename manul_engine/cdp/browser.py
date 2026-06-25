# manul_engine/cdp/browser.py
"""CDPBrowser — owns a Chrome process and the browser-level CDP connection.

Replaces Playwright's ``Browser`` / ``BrowserContext``. A single browser-level
:class:`~manul_engine.cdp.conn.Conn` drives the whole browser; pages are opened
as targets and attached over flat sessions multiplexed on that one socket.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .chrome import ChromeProcess, launch_chrome
from .conn import Conn
from .page import CDPPage

_log = logging.getLogger("manul_engine").getChild("cdp.browser")


class _LauncherProxy:
    """Returns the already-started browser from ``p.chromium.launch(...)``.

    Lets test bootstraps keep the familiar ``await p.<engine>.launch()`` line
    while ``p`` is a :class:`CDPBrowser` started by ``async with``."""

    def __init__(self, browser: CDPBrowser) -> None:
        self._browser = browser

    async def launch(self, **_kwargs: Any) -> CDPBrowser:
        await self._browser._ensure_started()
        return self._browser


class CDPBrowser:
    """A running Chrome instance driven over the Chrome DevTools Protocol.

    Two construction styles are supported:

    * ``browser = await CDPBrowser.launch(headless=True)`` — production form.
    * ``async with CDPBrowser(headless=True) as browser:`` — deferred-launch
      context manager used by the test suite.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        channel: str | None = None,
        executable_path: str | None = None,
        extra_args: list[str] | None = None,
    ) -> None:
        self._headless = headless
        self._channel = channel
        self._executable_path = executable_path
        self._extra_args = extra_args
        self._conn: Conn | None = None
        self._chrome: ChromeProcess | None = None
        self._endpoint = ""
        self._started = False
        self._closed = False
        self._pages: list[CDPPage] = []
        self._new_target_cbs: list[Any] = []
        # Playwright-shaped launcher attributes for the test bootstrap.
        self.chromium = _LauncherProxy(self)
        self.firefox = _LauncherProxy(self)
        self.webkit = _LauncherProxy(self)

    # ── construction ─────────────────────────────────────────────────────

    async def _ensure_started(self) -> None:
        if self._started:
            return
        chrome = await launch_chrome(
            headless=self._headless,
            channel=self._channel,
            executable_path=self._executable_path,
            extra_args=self._extra_args,
        )
        ws = await chrome.browser_ws_url()
        conn = await Conn.dial(ws)
        self._attach(conn, chrome, chrome.endpoint)
        await self._send("Target.setDiscoverTargets", {"discover": True})

    def _attach(self, conn: Conn, chrome: ChromeProcess | None, endpoint: str) -> None:
        self._conn = conn
        self._chrome = chrome
        self._endpoint = endpoint
        self._started = True
        conn.on("Target.targetCreated", self._on_target_created)
        conn.on("Target.targetDestroyed", self._on_target_destroyed)

    @classmethod
    async def launch(
        cls,
        *,
        headless: bool = True,
        channel: str | None = None,
        executable_path: str | None = None,
        extra_args: list[str] | None = None,
    ) -> CDPBrowser:
        browser = cls(
            headless=headless, channel=channel, executable_path=executable_path, extra_args=extra_args
        )
        await browser._ensure_started()
        return browser

    @classmethod
    async def connect_over_cdp(cls, endpoint: str) -> CDPBrowser:
        """Attach to an already-running Chrome/Electron at *endpoint* (no launch)."""
        from .chrome import _fetch_browser_ws  # local: reuse the HTTP helper

        ws = await _fetch_browser_ws(endpoint)
        conn = await Conn.dial(ws)
        browser = cls()
        browser._attach(conn, None, endpoint)
        await browser._send("Target.setDiscoverTargets", {"discover": True})
        return browser

    async def __aenter__(self) -> CDPBrowser:
        await self._ensure_started()
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        await self.close()
        return False

    async def new_context(self, **_kwargs: Any) -> CDPBrowser:
        """CDP has no separate browser context; returns the browser itself."""
        await self._ensure_started()
        return self

    async def _send(self, method: str, params: dict | None = None) -> dict:
        if self._conn is None:
            raise RuntimeError("CDPBrowser is not started")
        return await self._conn.send(method, params)

    # ── pages ────────────────────────────────────────────────────────────

    async def new_page(self, *, url: str = "about:blank") -> CDPPage:
        await self._ensure_started()
        created = await self._send("Target.createTarget", {"url": url})
        target_id = created.get("targetId")
        if not target_id:
            raise RuntimeError("Target.createTarget returned no targetId")
        return await self._attach_page(target_id)

    async def first_page(self) -> CDPPage:
        """Attach to the first existing page target (electron/connect mode)."""
        targets = (await self._send("Target.getTargets")).get("targetInfos", [])
        for info in targets:
            if info.get("type") == "page":
                return await self._attach_page(info["targetId"])
        return await self.new_page()

    async def _attach_page(self, target_id: str) -> CDPPage:
        attached = await self._send("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        session_id = attached.get("sessionId")
        if not session_id:
            raise RuntimeError("Target.attachToTarget returned no sessionId")
        page = CDPPage(self._conn, session_id, target_id, self)
        await page._init()
        self._pages.append(page)
        return page

    async def _close_target(self, target_id: str) -> None:
        await self._send("Target.closeTarget", {"targetId": target_id})

    @property
    def pages(self) -> list[CDPPage]:
        return list(self._pages)

    # ── popup / new-target tracking ──────────────────────────────────────

    def _on_target_created(self, params: dict, _session: str | None) -> None:
        info = params.get("targetInfo", {})
        if info.get("type") == "page" and info.get("openerId"):
            for cb in self._new_target_cbs:
                try:
                    cb(info)
                except Exception as exc:  # noqa: BLE001
                    _log.debug("new target cb error: %s", exc)

    def _on_target_destroyed(self, params: dict, _session: str | None) -> None:
        tid = params.get("targetId")
        for p in self._pages:
            if p._target_id == tid:
                p._fire_close()
        self._pages = [p for p in self._pages if p._target_id != tid]

    async def wait_for_event(self, event: str, *, timeout: float = 30000) -> CDPPage:
        """Playwright-style context event wait. Supports ``"page"`` (new tab/popup)."""
        if event == "page":
            return await self.wait_for_new_page(timeout=timeout / 1000.0)
        raise NotImplementedError(f"wait_for_event({event!r}) is not supported")

    async def wait_for_new_page(self, *, timeout: float = 30.0) -> CDPPage:
        """Wait for a popup/new page target to open and attach to it."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict] = loop.create_future()

        def _cb(info: dict) -> None:
            if not fut.done():
                fut.set_result(info)

        self._new_target_cbs.append(_cb)
        try:
            info = await asyncio.wait_for(fut, timeout=timeout)
        finally:
            if _cb in self._new_target_cbs:
                self._new_target_cbs.remove(_cb)
        return await self._attach_page(info["targetId"])

    # ── teardown ─────────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._conn is not None:
            try:
                await self._conn.close()
            except Exception as exc:  # noqa: BLE001
                _log.debug("conn close error: %s", exc)
        if self._chrome is not None:
            await self._chrome.close()
