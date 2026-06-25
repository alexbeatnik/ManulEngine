# manul_engine/cdp/conn.py
"""Low-level Chrome DevTools Protocol WebSocket transport.

A thin async JSON-RPC client over a single Chrome DevTools WebSocket.
Ported from ManulHeart's ``pkg/cdp/conn.go`` (Go) to Python/asyncio.

One :class:`Conn` owns one WebSocket. CDP multiplexes every target
(page, iframe, worker) over that single socket using ``sessionId`` once
flat auto-attach is enabled, so a single :class:`Conn` drives the whole
browser. ``send(method, params, session_id=…)`` issues a command and
awaits its reply; ``on(event, cb)`` subscribes to protocol events.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

_log = logging.getLogger("manul_engine").getChild("cdp.conn")

# Event callbacks receive the event ``params`` dict plus the originating
# ``session_id`` (None for the browser-level session).
EventHandler = Callable[[dict[str, Any], str | None], Any]


class CDPError(RuntimeError):
    """A CDP command returned a protocol-level error."""

    def __init__(self, method: str, code: int, message: str, data: str = "") -> None:
        self.method = method
        self.code = code
        self.cdp_message = message
        detail = f"{message}: {data}" if data else message
        super().__init__(f"cdp error in {method}: code={code} {detail}")


class Conn:
    """A live CDP WebSocket connection, safe for concurrent awaiters."""

    def __init__(self, ws: websockets.ClientConnection, ws_url: str) -> None:
        self._ws = ws
        self._ws_url = ws_url
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        # event method -> list of handlers; "*" receives every event.
        self._handlers: dict[str, list[EventHandler]] = {}
        self._closed = asyncio.Event()
        self._reader: asyncio.Task[None] | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    @classmethod
    async def dial(cls, ws_url: str) -> Conn:
        """Open a WebSocket to *ws_url* and start the read loop."""
        # Chrome sends large DOM payloads; disable the inbound size cap and
        # ping/pong keepalive (CDP has no application-level pong contract).
        ws = await websockets.connect(
            ws_url,
            max_size=None,
            ping_interval=None,
            open_timeout=30,
        )
        conn = cls(ws, ws_url)
        conn._reader = asyncio.create_task(conn._read_loop(), name="cdp-read-loop")
        return conn

    async def close(self) -> None:
        """Close the socket and fail every in-flight command."""
        if self._closed.is_set():
            return
        self._closed.set()
        try:
            await self._ws.close()
        except Exception as exc:  # noqa: BLE001 — best-effort teardown
            _log.debug("ws close error: %s", exc)
        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(ConnectionError("cdp connection closed"))
        self._pending.clear()
        if self._reader:
            self._reader.cancel()

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    # ── command / event API ──────────────────────────────────────────────

    async def send(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        session_id: str | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Issue a CDP command and await its result dict."""
        if self._closed.is_set():
            raise ConnectionError("cdp connection closed")
        msg_id = next(self._ids)
        payload: dict[str, Any] = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        if session_id:
            payload["sessionId"] = session_id

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[msg_id] = fut
        try:
            await self._ws.send(json.dumps(payload))
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending.pop(msg_id, None)

    def on(self, event: str, handler: EventHandler) -> Callable[[], None]:
        """Register *handler* for a CDP *event* (or ``"*"`` for all).

        Returns a zero-arg function that unregisters the handler.
        """
        self._handlers.setdefault(event, []).append(handler)

        def _off() -> None:
            lst = self._handlers.get(event)
            if lst and handler in lst:
                lst.remove(handler)

        return _off

    # ── read loop ────────────────────────────────────────────────────────

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                self._dispatch(msg)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — socket died; tear down
            _log.debug("cdp read loop ended: %s", exc)
        finally:
            await self.close()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        msg_id = msg.get("id")
        if msg_id is not None:
            fut = self._pending.get(msg_id)
            if fut is None or fut.done():
                return
            err = msg.get("error")
            if err is not None:
                fut.set_exception(
                    CDPError(
                        "<command>",
                        err.get("code", 0),
                        err.get("message", ""),
                        err.get("data", ""),
                    )
                )
            else:
                fut.set_result(msg.get("result", {}))
            return

        method = msg.get("method")
        if not method:
            return
        params = msg.get("params", {}) or {}
        session_id = msg.get("sessionId")
        for handler in (*self._handlers.get(method, ()), *self._handlers.get("*", ())):
            try:
                result = handler(params, session_id)
                if isinstance(result, Awaitable):
                    asyncio.create_task(result)  # noqa: RUF006 — fire-and-forget event handler
            except Exception as exc:  # noqa: BLE001 — one bad handler must not kill the loop
                _log.debug("cdp event handler for %s failed: %s", method, exc)
