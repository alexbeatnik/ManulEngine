# manul_engine/cdp/page.py
"""High-level CDP page/frame/element objects driven over a single Conn.

These are the objects the rest of ManulEngine talks to in place of Playwright's
``Page`` / ``Frame`` / ``Locator``. The API is CDP-native (explicit awaits, no
auto-wait magic, selectors resolved to RemoteObjects) rather than a Playwright
clone:

* :class:`CDPPage`   — one page target (attached via a flat session).
* :class:`CDPFrame`  — one execution context inside that page (main or iframe).
* :class:`CDPElement` — a resolved DOM node handle (a RemoteObject by objectId).

Per-frame routing: a selector is resolved once via ``Runtime.evaluate`` in the
owning frame's execution context; the returned ``objectId`` is then used for all
``Runtime.callFunctionOn`` operations, which run in that frame automatically.
"""

from __future__ import annotations

import asyncio
import base64
import fnmatch
import json
import logging
import re
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from . import keys as _keys
from . import protocol as _proto

if TYPE_CHECKING:
    from .conn import Conn

_log = logging.getLogger("manul_engine").getChild("cdp.page")

# Matches a JS *function* expression (arrow or classic) vs a bare expression.
_FUNC_RE = re.compile(r"^\s*(async\s+)?(function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)")


def _is_function_source(js: str) -> bool:
    return bool(_FUNC_RE.match(js))


class _UnsetType:
    def __repr__(self) -> str:  # pragma: no cover
        return "<unset>"


_UNSET = _UnsetType()


class CDPElement:
    """A handle to a resolved DOM node (Runtime RemoteObject by objectId)."""

    def __init__(self, page: CDPPage, object_id: str, frame: CDPFrame) -> None:
        self._page = page
        self._object_id = object_id
        self.frame = frame

    async def _call(self, fn: str, *args: Any, return_by_value: bool = True) -> Any:
        # Internal: element bound as `this` (used by protocol.py `function(){ this… }`).
        return await self._page._call_function_on(self._object_id, fn, args, return_by_value=return_by_value)

    async def evaluate(self, js: str, arg: Any = _UNSET) -> Any:
        """Run ``js`` with this element passed as the FIRST argument.

        Mirrors Playwright's ``ElementHandle.evaluate(fn, arg)`` where the
        function is ``(el, arg) => …``. The element is also bound as ``this``.
        """
        arguments: list[dict] = [{"objectId": self._object_id}]
        if arg is not _UNSET:
            arguments.append({"value": arg})
        res = await self._page._send(
            "Runtime.callFunctionOn",
            {
                "functionDeclaration": js,
                "objectId": self._object_id,
                "arguments": arguments,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        if res.get("exceptionDetails"):
            raise RuntimeError(_format_exception(res["exceptionDetails"]))
        return res.get("result", {}).get("value")

    async def scroll_into_view(self, *, timeout: float | None = None) -> None:
        await self._call(_proto.SCROLL_INTO_VIEW_FN, return_by_value=True)

    # Playwright-name alias used across the action layer.
    async def scroll_into_view_if_needed(self, *, timeout: float | None = None) -> None:
        await self.scroll_into_view()

    async def bounding_box(self, *, timeout: float | None = None) -> dict[str, float] | None:
        box = await self._call(_proto.BOX_CENTER_FN)
        if not box:
            return None
        return {"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]}

    async def click(
        self, *, button: str = "left", click_count: int = 1, timeout: float | None = None, force: bool = False
    ) -> None:
        """Click via a real mouse event at the element centre (main frame) or a
        synthetic mouse-event sequence (iframes, where viewport coords differ).

        ``timeout``/``force`` are accepted for action-layer call compatibility;
        CDP input is already trusted, so ``force`` is implicit."""
        box = await self._call(_proto.BOX_CENTER_FN)
        if box and self.frame.is_main:
            await self._page.mouse.click(box["cx"], box["cy"], button=button, click_count=click_count)
        else:
            await self._dispatch_mouse_js(button, click_count)

    async def dblclick(self, *, timeout: float | None = None, force: bool = False) -> None:
        await self.click(click_count=2)

    async def hover(self, *, timeout: float | None = None, force: bool = False) -> None:
        box = await self._call(_proto.BOX_CENTER_FN)
        if box and self.frame.is_main:
            await self._page.mouse.move(box["cx"], box["cy"])
        else:
            await self._call(
                "function(){ this.dispatchEvent(new MouseEvent('mouseover',"
                "{bubbles:true,cancelable:true,view:window})); }"
            )

    async def _dispatch_mouse_js(self, button: str, click_count: int) -> None:
        btn = {"left": 0, "middle": 1, "right": 2}.get(button, 0)
        fn = (
            "function(b, cc){"
            "  const opt={bubbles:true,cancelable:true,view:window,button:b};"
            "  this.dispatchEvent(new MouseEvent('mousedown',opt));"
            "  this.dispatchEvent(new MouseEvent('mouseup',opt));"
            "  if(cc>=2){this.dispatchEvent(new MouseEvent('dblclick',opt));}"
            "  else if(b===2){this.dispatchEvent(new MouseEvent('contextmenu',opt));}"
            "  else if(typeof this.click==='function'){this.click();}"
            "}"
        )
        await self._call(fn, btn, click_count)

    async def js_click(self) -> None:
        await self._call(_proto.ELEMENT_CLICK_FN)

    async def fill(self, value: str, *, timeout: float | None = None) -> None:
        await self._call(_proto.SET_VALUE_FN, value)

    async def type(self, text: str, *, delay: float = 0.0, timeout: float | None = None) -> None:
        """Focus the element and type character-by-character via key events."""
        await self._call("function(){ try{this.focus({preventScroll:true});}catch(e){this.focus();} }")
        await self._page.keyboard.type(text, delay=delay)

    async def press(self, key: str, *, timeout: float | None = None) -> None:
        await self._call("function(){ try{this.focus({preventScroll:true});}catch(e){this.focus();} }")
        await self._page.keyboard.press(key)

    async def select_option(
        self,
        *,
        value: list[str] | str | None = None,
        label: list[str] | str | None = None,
        timeout: float | None = None,
    ) -> bool:
        values = [value] if isinstance(value, str) else (value or [])
        labels = [label] if isinstance(label, str) else (label or [])
        spec = {"values": values, "labels": labels}
        return bool(await self._call(_proto.SELECT_OPTION_FN, spec))

    async def get_attribute(self, name: str, *, timeout: float | None = None) -> str | None:
        return await self._call("function(n){ return this.getAttribute(n); }", name)

    async def input_value(self, *, timeout: float | None = None) -> str:
        return await self._call("function(){ return this.value != null ? this.value : ''; }") or ""

    async def inner_text(self, *, timeout: float | None = None) -> str:
        return await self._call("function(){ return this.innerText || this.textContent || ''; }") or ""

    async def is_checked(self, *, timeout: float | None = None) -> bool:
        return bool(await self._call("function(){ return !!this.checked; }"))

    async def screenshot(self, *, type: str = "png", timeout: float | None = None) -> bytes:
        """Capture a PNG of just this element (clipped to its box)."""
        box = await self._call(_proto.BOX_CENTER_FN)
        if not box or box["width"] <= 0 or box["height"] <= 0:
            raise RuntimeError("element has no visible box to screenshot")
        return await self._page.screenshot(
            clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]}
        )

    async def wait_for(self, *, state: str = "visible", timeout: float = 30000) -> None:
        deadline = asyncio.get_running_loop().time() + timeout / 1000.0
        while asyncio.get_running_loop().time() < deadline:
            visible = await self.is_visible()
            if (state in ("visible", "attached") and visible) or (state == "hidden" and not visible):
                return
            await asyncio.sleep(0.05)
        raise TimeoutError(f"wait_for(state={state!r}) timed out")

    async def is_visible(self) -> bool:
        return bool(
            await self._call(
                "function(){ const r=this.getBoundingClientRect();"
                " const s=getComputedStyle(this);"
                " return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'; }"
            )
        )

    async def set_input_files(self, files: list[str] | str, *, timeout: float | None = None) -> None:
        paths = [files] if isinstance(files, str) else list(files)
        await self._page._set_file_input(self._object_id, paths)

    async def drag_to(self, dest: CDPElement, *, timeout: float | None = None) -> None:
        src = await self._call(_proto.BOX_CENTER_FN)
        dst = await dest._call(_proto.BOX_CENTER_FN)
        if not src or not dst:
            raise RuntimeError("drag_to: could not resolve element boxes")
        await self._page.mouse.drag(src["cx"], src["cy"], dst["cx"], dst["cy"])


class CDPFrame:
    """One execution context (main document or an iframe)."""

    def __init__(self, page: CDPPage, frame_id: str, *, is_main: bool) -> None:
        self._page = page
        self.frame_id = frame_id
        self.is_main = is_main
        self.url = ""
        self.name = ""
        self.context_id: int | None = None

    async def evaluate(self, js: str, arg: Any = _UNSET) -> Any:
        """Evaluate JS in this frame. Function sources are auto-invoked with *arg*."""
        if _is_function_source(js):
            if arg is _UNSET:
                expr = f"({js})()"
            else:
                expr = f"({js})({json.dumps(arg)})"
        else:
            expr = js
        return await self._page._evaluate(expr, context_id=self.context_id, is_main=self.is_main)

    async def query(self, selector: str, *, last: bool = False) -> CDPElement | None:
        """Resolve *selector* to a :class:`CDPElement` in this frame, or None."""
        expr = _proto.node_expression_last(selector) if last else _proto.node_expression(selector)
        object_id = await self._page._resolve_object_id(expr, context_id=self.context_id, is_main=self.is_main)
        if object_id is None:
            return None
        return CDPElement(self._page, object_id, self)


class CDPKeyboard:
    def __init__(self, page: CDPPage) -> None:
        self._page = page

    async def press(self, combo: str) -> None:
        modifiers, key = _keys.parse_combo(combo)
        await self._page._send("Input.dispatchKeyEvent", _keys.key_event_params(key, modifiers=modifiers, is_down=True))
        await self._page._send("Input.dispatchKeyEvent", _keys.key_event_params(key, modifiers=modifiers, is_down=False))

    async def type(self, text: str, *, delay: float = 0.0) -> None:
        for ch in text:
            if ch == "\n":
                await self.press("Enter")
            else:
                await self._page._send("Input.dispatchKeyEvent", {"type": "keyDown", "text": ch, "key": ch})
                await self._page._send("Input.dispatchKeyEvent", {"type": "keyUp", "key": ch})
            if delay:
                await asyncio.sleep(delay / 1000.0)


class CDPMouse:
    def __init__(self, page: CDPPage) -> None:
        self._page = page
        self._x = 0.0
        self._y = 0.0

    async def move(self, x: float, y: float, *, steps: int = 1) -> None:
        sx, sy = self._x, self._y
        steps = max(1, steps)
        for i in range(1, steps + 1):
            ix = sx + (x - sx) * i / steps
            iy = sy + (y - sy) * i / steps
            await self._page._send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": ix, "y": iy})
        self._x, self._y = x, y

    async def down(self, *, button: str = "left") -> None:
        await self._page._send(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "button": button, "x": self._x, "y": self._y, "clickCount": 1},
        )

    async def up(self, *, button: str = "left") -> None:
        await self._page._send(
            "Input.dispatchMouseEvent",
            {"type": "mouseReleased", "button": button, "x": self._x, "y": self._y, "clickCount": 1},
        )

    async def click(self, x: float, y: float, *, button: str = "left", click_count: int = 1) -> None:
        for cc in range(1, click_count + 1):
            await self._page._send(
                "Input.dispatchMouseEvent",
                {"type": "mousePressed", "button": button, "x": x, "y": y, "clickCount": cc},
            )
            await self._page._send(
                "Input.dispatchMouseEvent",
                {"type": "mouseReleased", "button": button, "x": x, "y": y, "clickCount": cc},
            )

    async def drag(self, fx: float, fy: float, tx: float, ty: float) -> None:
        await self.move(fx, fy)
        await self._page._send(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "button": "left", "x": fx, "y": fy, "clickCount": 1},
        )
        await self._page._send("Input.dispatchMouseEvent", {"type": "mouseMoved", "button": "left", "x": tx, "y": ty})
        await self._page._send(
            "Input.dispatchMouseEvent",
            {"type": "mouseReleased", "button": "left", "x": tx, "y": ty, "clickCount": 1},
        )


class CDPPage:
    """A page target attached over a flat CDP session."""

    def __init__(self, conn: Conn, session_id: str, target_id: str, browser: Any) -> None:
        self._conn = conn
        self._session_id = session_id
        self._target_id = target_id
        self._browser = browser
        self.keyboard = CDPKeyboard(self)
        self.mouse = CDPMouse(self)

        self._main_frame_id: str | None = None
        self._frames: dict[str, CDPFrame] = {}
        self._frame_order: list[str] = []
        self._closed = False
        self._url = ""
        self._init_scripts: list[str] = []
        self._bindings: dict[str, Any] = {}
        self._close_cbs: list[Any] = []
        self._new_page_cbs: list[Any] = []
        self._routes: list[tuple[str, Any]] = []
        self._fetch_enabled = False
        self._network_enabled = False
        self._dialog_cbs: list[Any] = []
        self._dialogs_enabled = False

    # ── construction ─────────────────────────────────────────────────────

    async def _init(self) -> None:
        """Enable domains and wire frame/context tracking on this session."""
        self._conn.on("Runtime.executionContextCreated", self._on_context_created)
        self._conn.on("Runtime.executionContextDestroyed", self._on_context_destroyed)
        self._conn.on("Runtime.executionContextsCleared", self._on_contexts_cleared)
        self._conn.on("Page.frameNavigated", self._on_frame_navigated)
        self._conn.on("Page.frameAttached", self._on_frame_attached)
        self._conn.on("Page.frameDetached", self._on_frame_detached)
        self._conn.on("Runtime.bindingCalled", self._on_binding_called)
        self._conn.on("Target.attachedToTarget", self._on_target_attached)

        await self._send("Page.enable")
        await self._send("Runtime.enable")
        await self._send("DOM.enable")
        await self._send("Page.setLifecycleEventsEnabled", {"enabled": True})
        # Discover same-origin frames + auto-attach OOPIF children to this session.
        await self._send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": False, "flatten": True})

        tree = await self._send("Page.getFrameTree")
        self._ingest_frame_tree(tree.get("frameTree", {}))
        await self._wait_for_main_context(timeout=3.0)

    def _ingest_frame_tree(self, node: dict, parent: str | None = None) -> None:
        frame = node.get("frame", {})
        fid = frame.get("id")
        if not fid:
            return
        is_main = parent is None
        if is_main:
            self._main_frame_id = fid
        f = self._frames.get(fid) or CDPFrame(self, fid, is_main=is_main)
        f.is_main = is_main
        f.url = frame.get("url", f.url)
        f.name = frame.get("name", f.name)
        self._register_frame(fid, f)
        if is_main:
            self._url = f.url
        for child in node.get("childFrames", []) or []:
            self._ingest_frame_tree(child, parent=fid)

    def _register_frame(self, fid: str, frame: CDPFrame) -> None:
        if fid not in self._frames:
            self._frames[fid] = frame
        if fid not in self._frame_order:
            self._frame_order.append(fid)

    async def _wait_for_main_context(self, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            mf = self.main_frame
            if mf and mf.context_id is not None:
                return
            await asyncio.sleep(0.02)
        # Main frame can still be evaluated without a contextId (default context).

    # ── event handlers (filtered to this page's sessions) ────────────────

    def _owns(self, session_id: str | None) -> bool:
        return session_id == self._session_id or session_id in getattr(self, "_child_sessions", ())

    def _on_context_created(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        ctx = params.get("context", {})
        aux = ctx.get("auxData", {}) or {}
        fid = aux.get("frameId")
        if not fid:
            return
        if aux.get("isDefault", True):
            frame = self._frames.get(fid) or CDPFrame(self, fid, is_main=(fid == self._main_frame_id))
            frame.context_id = ctx.get("id")
            self._register_frame(fid, frame)

    def _on_context_destroyed(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        cid = params.get("executionContextId")
        for f in self._frames.values():
            if f.context_id == cid:
                f.context_id = None

    def _on_contexts_cleared(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        for f in self._frames.values():
            f.context_id = None

    def _on_frame_navigated(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        frame = params.get("frame", {})
        fid = frame.get("id")
        if not fid:
            return
        is_main = fid == self._main_frame_id or frame.get("parentId") is None
        if is_main:
            self._main_frame_id = fid
        f = self._frames.get(fid) or CDPFrame(self, fid, is_main=is_main)
        f.is_main = is_main
        f.url = frame.get("url", f.url)
        f.name = frame.get("name", f.name)
        self._register_frame(fid, f)
        if is_main:
            self._url = f.url

    def _on_frame_attached(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        fid = params.get("frameId")
        if fid and fid not in self._frames:
            self._register_frame(fid, CDPFrame(self, fid, is_main=False))

    def _on_frame_detached(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        fid = params.get("frameId")
        if fid:
            self._frames.pop(fid, None)
            if fid in self._frame_order:
                self._frame_order.remove(fid)

    def _on_target_attached(self, params: dict, session_id: str | None) -> None:
        # Flat auto-attach: an OOPIF / popup attached. Track child page sessions
        # for popups; child iframe sessions are tracked for event ownership.
        info = params.get("targetInfo", {})
        child_session = params.get("sessionId")
        if not child_session:
            return
        children = getattr(self, "_child_sessions", set())
        children.add(child_session)
        self._child_sessions = children
        if info.get("type") == "page":
            for cb in self._new_page_cbs:
                try:
                    cb(info)
                except Exception as exc:
                    _log.debug("new_page cb error: %s", exc)

    def _on_binding_called(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        name = params.get("name")
        cb = self._bindings.get(name)
        if cb is None:
            return
        # Runtime.addBinding delivers exactly one string argument; pass it raw
        # (callers parse it themselves, matching the old expose_function bridge).
        payload = params.get("payload", "")
        try:
            cb(payload)
        except Exception as exc:
            _log.debug("binding %s cb error: %s", name, exc)

    def _fire_close(self) -> None:
        for cb in self._close_cbs:
            try:
                cb()
            except Exception as exc:
                _log.debug("close cb error: %s", exc)

    # ── low-level send + evaluate ────────────────────────────────────────

    async def _send(self, method: str, params: dict | None = None, *, timeout: float = 30.0) -> dict:
        return await self._conn.send(method, params, session_id=self._session_id, timeout=timeout)

    async def _evaluate(self, expression: str, *, context_id: int | None, is_main: bool) -> Any:
        params: dict[str, Any] = {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        }
        if context_id is not None:
            params["contextId"] = context_id
        elif not is_main:
            raise RuntimeError("frame execution context not available")
        res = await self._send("Runtime.evaluate", params)
        if res.get("exceptionDetails"):
            raise RuntimeError(_format_exception(res["exceptionDetails"]))
        return res.get("result", {}).get("value")

    async def _resolve_object_id(self, expression: str, *, context_id: int | None, is_main: bool) -> str | None:
        params: dict[str, Any] = {"expression": expression, "returnByValue": False, "awaitPromise": True}
        if context_id is not None:
            params["contextId"] = context_id
        elif not is_main:
            raise RuntimeError("frame execution context not available")
        res = await self._send("Runtime.evaluate", params)
        if res.get("exceptionDetails"):
            return None
        result = res.get("result", {})
        if result.get("subtype") == "null" or result.get("type") == "undefined":
            return None
        return result.get("objectId")

    async def _call_function_on(self, object_id: str, fn: str, args: tuple, *, return_by_value: bool) -> Any:
        res = await self._send(
            "Runtime.callFunctionOn",
            {
                "functionDeclaration": fn,
                "objectId": object_id,
                "arguments": [{"value": a} for a in args],
                "returnByValue": return_by_value,
                "awaitPromise": True,
            },
        )
        if res.get("exceptionDetails"):
            raise RuntimeError(_format_exception(res["exceptionDetails"]))
        return res.get("result", {}).get("value")

    async def _set_file_input(self, object_id: str, files: list[str]) -> None:
        await self._send("DOM.setFileInputFiles", {"files": files, "objectId": object_id})

    # ── public page API ──────────────────────────────────────────────────

    @property
    def main_frame(self) -> CDPFrame | None:
        if self._main_frame_id is None:
            return None
        return self._frames.get(self._main_frame_id)

    @property
    def frames(self) -> list[CDPFrame]:
        """Main frame first, then child frames in attach/DOM order."""
        ordered: list[CDPFrame] = []
        if self._main_frame_id and self._main_frame_id in self._frames:
            ordered.append(self._frames[self._main_frame_id])
        for fid in self._frame_order:
            if fid == self._main_frame_id:
                continue
            f = self._frames.get(fid)
            if f is not None:
                ordered.append(f)
        return ordered

    @property
    def url(self) -> str:
        return self._url

    async def evaluate(self, js: str, arg: Any = _UNSET) -> Any:
        mf = self.main_frame
        if mf is None:
            mf = CDPFrame(self, self._main_frame_id or "", is_main=True)
        return await mf.evaluate(js, arg)

    async def query(self, selector: str, *, last: bool = False) -> CDPElement | None:
        mf = self.main_frame
        if mf is None:
            return None
        return await mf.query(selector, last=last)

    async def title(self) -> str:
        return await self.evaluate("document.title") or ""

    async def content(self) -> str:
        return await self.evaluate("document.documentElement.outerHTML") or ""

    async def navigate(self, url: str, *, wait_until: str = "load", timeout: float = 30000) -> None:
        """Navigate to *url*. ``timeout`` is in **milliseconds** (Playwright convention)."""
        await self._send("Page.navigate", {"url": url}, timeout=max(timeout / 1000.0, 1.0))
        await self.wait_for_load(state=wait_until, timeout=timeout)
        self._url = await self.evaluate("location.href") or url

    # Playwright-name alias kept for the few callers that used goto().
    async def goto(self, url: str, *, wait_until: str = "load", timeout: float = 30000) -> None:
        await self.navigate(url, wait_until=wait_until, timeout=timeout)

    async def reload(self, *, wait_until: str = "load", timeout: float = 30000) -> None:
        await self._send("Page.reload", timeout=max(timeout / 1000.0, 1.0))
        await self.wait_for_load(state=wait_until, timeout=timeout)

    async def wait_for_load(self, *, state: str = "load", timeout: float = 30000) -> None:
        """Poll ``document.readyState`` until ready (JS-poll, like ManulHeart) —
        robust against missing load events on cached pages. ``timeout`` is in ms."""
        target = "complete" if state in ("load", "networkidle") else "interactive"
        deadline = asyncio.get_running_loop().time() + timeout / 1000.0
        while asyncio.get_running_loop().time() < deadline:
            try:
                ready = await self.evaluate("document.readyState")
            except Exception:
                ready = None
            if ready == "complete" or (target == "interactive" and ready in ("interactive", "complete")):
                if state == "networkidle":
                    await asyncio.sleep(0.5)
                return
            await asyncio.sleep(0.05)

    async def wait_for_load_state(self, state: str = "load", *, timeout: float = 30000) -> None:
        """Playwright-name alias for :meth:`wait_for_load`."""
        await self.wait_for_load(state=state, timeout=timeout)

    async def wait_for_selector(
        self,
        selector: str,
        *,
        frame: CDPFrame | None = None,
        state: str = "visible",
        timeout: float = 30000,
    ) -> CDPElement | None:
        """Poll until *selector* resolves (and is visible for state="visible")."""
        target = frame or self.main_frame
        if target is None:
            return None
        deadline = asyncio.get_running_loop().time() + timeout / 1000.0
        while asyncio.get_running_loop().time() < deadline:
            el = await target.query(selector)
            if el is not None:
                if state in ("attached", "present"):
                    return el
                if state == "hidden":
                    if not await el.is_visible():
                        return el
                elif await el.is_visible():
                    return el
            elif state == "hidden":
                return None
            await asyncio.sleep(0.05)
        if state == "hidden":
            return None
        raise TimeoutError(f"wait_for_selector timed out for {selector!r}")

    async def set_content(self, html: str, *, wait_until: str = "load") -> None:
        """Replace the document with *html* (test/scan helper)."""
        # document.open/write/close reliably replaces the whole document and
        # creates a fresh execution context, which our handlers pick up.
        await self.evaluate(
            "(h) => { document.open(); document.write(h); document.close(); }",
            html,
        )
        await self.wait_for_load(state=wait_until)

    async def screenshot(
        self, path: str | None = None, *, full_page: bool = False, clip: dict | None = None
    ) -> bytes:
        params: dict[str, Any] = {"format": "png", "captureBeyondViewport": full_page}
        if clip is not None:
            params["clip"] = {**clip, "scale": 1}
        res = await self._send("Page.captureScreenshot", params)
        data = base64.b64decode(res.get("data", ""))
        if path:
            with open(path, "wb") as fh:
                fh.write(data)
        return data

    # ── network: request mocking + response waiting ──────────────────────

    async def route(self, pattern: str, handler: Any) -> None:
        """Intercept requests matching *pattern* (glob ``**`` supported) and pass
        a :class:`CDPRoute` to *handler* (``Fetch.requestPaused``)."""
        if not self._fetch_enabled:
            await self._send("Fetch.enable", {"patterns": [{"urlPattern": "*"}]})
            self._fetch_enabled = True
            self._conn.on("Fetch.requestPaused", self._on_request_paused)
        self._routes.append((pattern, handler))

    async def _on_request_paused(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        url = params.get("request", {}).get("url", "")
        rid = params.get("requestId")
        route = CDPRoute(self, rid, params.get("request", {}))
        for pattern, handler in self._routes:
            if _glob_match(pattern, url):
                res = handler(route)
                if isinstance(res, Awaitable):
                    await res
                return
        await route.continue_()

    async def wait_for_response(self, predicate: Any, *, timeout: float = 30000) -> dict:
        """Wait for a ``Network.responseReceived`` whose response satisfies
        *predicate* (called with a small object exposing ``.url``)."""
        if not self._network_enabled:
            await self._send("Network.enable")
            self._network_enabled = True
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict] = loop.create_future()

        def _cb(params: dict, session_id: str | None) -> None:
            if not self._owns(session_id) or fut.done():
                return
            resp = params.get("response", {})
            try:
                if predicate(_Resp(resp.get("url", ""), resp.get("status", 0))):
                    fut.set_result(resp)
            except Exception as exc:
                _log.debug("wait_for_response predicate error: %s", exc)

        off = self._conn.on("Network.responseReceived", _cb)
        try:
            return await asyncio.wait_for(fut, timeout=timeout / 1000.0)
        finally:
            off()

    async def wait_for_event(self, event: str, *, timeout: float = 30000) -> Any:
        """Minimal Playwright-style event wait. Supports ``"page"`` (popup)."""
        if event == "page":
            return await self._browser.wait_for_new_page(timeout=timeout / 1000.0)
        raise NotImplementedError(f"wait_for_event({event!r}) is not supported")

    async def add_init_script(self, script: str) -> None:
        self._init_scripts.append(script)
        await self._send("Page.addScriptToEvaluateOnNewDocument", {"source": script})

    async def expose_binding(self, name: str, callback: Any) -> None:
        self._bindings[name] = callback
        await self._send("Runtime.addBinding", {"name": name})

    def on_new_page(self, callback: Any) -> None:
        self._new_page_cbs.append(callback)

    def on_close(self, callback: Any) -> None:
        self._close_cbs.append(callback)

    async def wait_for_timeout(self, timeout_ms: float) -> None:
        await asyncio.sleep(timeout_ms / 1000.0)

    def on(self, event: str, callback: Any) -> None:
        """Minimal Playwright-style event hook. Supports ``"close"`` and ``"dialog"``."""
        if event == "close":
            self.on_close(callback)
        elif event == "dialog":
            self._dialog_cbs.append(callback)
            asyncio.create_task(self._enable_dialogs())  # noqa: RUF006
        else:
            raise NotImplementedError(f"page.on({event!r}) is not supported")

    async def _enable_dialogs(self) -> None:
        if self._dialogs_enabled:
            return
        self._dialogs_enabled = True
        self._conn.on("Page.javascriptDialogOpening", self._on_dialog)

    def _on_dialog(self, params: dict, session_id: str | None) -> None:
        if not self._owns(session_id):
            return
        dialog = CDPDialog(self, params.get("message", ""), params.get("type", "alert"))
        if self._dialog_cbs:
            for cb in self._dialog_cbs:
                try:
                    cb(dialog)
                except Exception as exc:
                    _log.debug("dialog cb error: %s", exc)
        else:
            asyncio.create_task(dialog.accept())  # noqa: RUF006 — default: accept

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._browser._close_target(self._target_id)
        except Exception as exc:
            _log.debug("close target error: %s", exc)
        for cb in self._close_cbs:
            try:
                cb()
            except Exception as exc:
                _log.debug("close cb error: %s", exc)


class CDPDialog:
    """A JS dialog (alert/confirm/prompt) passed to ``page.on("dialog", …)``."""

    def __init__(self, page: CDPPage, message: str, dialog_type: str) -> None:
        self._page = page
        self.message = message
        self.type = dialog_type

    async def accept(self, prompt_text: str = "") -> None:
        await self._page._send("Page.handleJavaScriptDialog", {"accept": True, "promptText": prompt_text})

    async def dismiss(self) -> None:
        await self._page._send("Page.handleJavaScriptDialog", {"accept": False})


class _Resp:
    """Minimal response view passed to ``wait_for_response`` predicates."""

    def __init__(self, url: str, status: int) -> None:
        self.url = url
        self.status = status


class _CDPRequest:
    """The ``request`` attribute of a :class:`CDPRoute` (Playwright-shaped)."""

    def __init__(self, info: dict) -> None:
        self._info = info
        self.url = info.get("url", "")
        self.method = info.get("method", "GET")

    @property
    def headers(self) -> dict:
        return self._info.get("headers", {})


class CDPRoute:
    """A paused request handed to ``page.route`` handlers (``Fetch`` domain)."""

    def __init__(self, page: CDPPage, request_id: str, request_info: dict) -> None:
        self._page = page
        self._request_id = request_id
        self.request = _CDPRequest(request_info)

    async def fulfill(self, *, status: int = 200, content_type: str = "application/json", body: str = "") -> None:
        encoded = base64.b64encode(body.encode("utf-8")).decode("ascii")
        await self._page._send(
            "Fetch.fulfillRequest",
            {
                "requestId": self._request_id,
                "responseCode": status,
                "responseHeaders": [{"name": "Content-Type", "value": content_type}],
                "body": encoded,
            },
        )

    async def continue_(self) -> None:
        await self._page._send("Fetch.continueRequest", {"requestId": self._request_id})

    async def abort(self, error_reason: str = "Failed") -> None:
        await self._page._send("Fetch.failRequest", {"requestId": self._request_id, "errorReason": error_reason})


def _glob_match(pattern: str, url: str) -> bool:
    """Match a Playwright-style ``**`` glob against *url* (substring-friendly)."""
    if pattern.startswith("**"):
        return fnmatch.fnmatch(url, "*" + pattern[2:]) or pattern[2:] in url
    return fnmatch.fnmatch(url, pattern) or pattern in url


def _format_exception(details: dict) -> str:
    exc = details.get("exception", {})
    return exc.get("description") or exc.get("value") or details.get("text") or "JS exception"
