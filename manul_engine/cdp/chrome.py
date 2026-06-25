# manul_engine/cdp/chrome.py
"""Chrome process lifecycle management for the CDP backend.

Launches a system-installed Chrome/Chromium with remote debugging enabled
and resolves its browser-level DevTools WebSocket endpoint. Ported from
ManulHeart's ``pkg/browser/chrome.go``.

Chrome is launched with ``--remote-debugging-port=0`` so it picks a free
port and writes it to ``<user-data-dir>/DevToolsActivePort``; we read that
file instead of guessing a port, which makes parallel test runs safe.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

_log = logging.getLogger("manul_engine").getChild("cdp.chrome")

# Flags that suppress Chrome dialogs/networking that interfere with automation
# (mirrors ManulHeart's chrome.go arg list).
_AUTOMATION_FLAGS = [
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-hang-monitor",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-sync",
    "--disable-translate",
    "--disable-search-engine-choice-screen",
    "--disable-features=PasswordLeakDetection,PasswordManagerOnboarding,"
    "AutofillServerCommunication,Translate,MediaRouter,GlobalMediaControls",
    "--no-service-autorun",
    "--password-store=basic",
    "--disable-save-password-bubble",
    "--disable-component-update",
    "--disable-infobars",
]

_LINUX_CANDIDATES = [
    "google-chrome-stable",
    "google-chrome",
    "chromium-browser",
    "chromium",
]
_DARWIN_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
]
_WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

# Chrome 'channel' names map to concrete Linux binaries; on other platforms
# Playwright used channels, but here we resolve to system executables.
_CHANNEL_BINARIES = {
    "chrome": ["google-chrome-stable", "google-chrome"],
    "chrome-beta": ["google-chrome-beta"],
    "chrome-dev": ["google-chrome-unstable"],
    "chromium": ["chromium", "chromium-browser"],
    "msedge": ["microsoft-edge-stable", "microsoft-edge"],
}


class ChromeNotFoundError(RuntimeError):
    """No Chrome/Chromium binary could be located."""


def find_chrome(channel: str | None = None, executable_path: str | None = None) -> str:
    """Locate a Chrome/Chromium binary.

    Precedence: explicit *executable_path* → *channel* mapping → ``MANUL_CHANNEL``
    env → platform default candidates. Raises :class:`ChromeNotFoundError`.
    """
    if executable_path:
        if Path(executable_path).exists():
            return executable_path
        raise ChromeNotFoundError(f"executable_path does not exist: {executable_path}")

    channel = channel or os.environ.get("MANUL_CHANNEL")
    candidates: list[str] = []
    if channel:
        candidates.extend(_CHANNEL_BINARIES.get(channel.lower(), [channel]))

    if os.name == "nt":
        candidates.extend(_WINDOWS_CANDIDATES)
    elif sys_is_darwin():
        candidates.extend(_DARWIN_CANDIDATES)
    else:
        candidates.extend(_LINUX_CANDIDATES)

    for cand in candidates:
        if ("/" in cand or "\\" in cand) and Path(cand).exists():
            return cand
        found = shutil.which(cand)
        if found:
            return found
    raise ChromeNotFoundError(
        "Chrome/Chromium not found; install Google Chrome or set executable_path / MANUL_CHANNEL"
    )


def sys_is_darwin() -> bool:
    import sys

    return sys.platform == "darwin"


class ChromeProcess:
    """A spawned Chrome process with remote debugging enabled."""

    def __init__(self, proc: subprocess.Popen[bytes], user_data_dir: str, owns_dir: bool, port: int) -> None:
        self._proc = proc
        self._user_data_dir = user_data_dir
        self._owns_dir = owns_dir
        self.port = port

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def alive(self) -> bool:
        return self._proc.poll() is None

    async def browser_ws_url(self) -> str:
        """Return Chrome's browser-level DevTools WebSocket endpoint."""
        return await _fetch_browser_ws(self.endpoint)

    async def close(self) -> None:
        """Terminate Chrome and clean up an owned profile directory."""
        try:
            self._proc.terminate()
            await asyncio.to_thread(self._proc.wait, 10)
        except Exception:
            try:
                self._proc.kill()
            except Exception as exc:
                _log.debug("chrome kill error: %s", exc)
        if self._owns_dir:
            shutil.rmtree(self._user_data_dir, ignore_errors=True)


async def launch_chrome(
    *,
    headless: bool = True,
    channel: str | None = None,
    executable_path: str | None = None,
    extra_args: list[str] | None = None,
    user_data_dir: str | None = None,
) -> ChromeProcess:
    """Launch Chrome with remote debugging and wait until CDP is reachable."""
    chrome_path = find_chrome(channel, executable_path)

    owns_dir = user_data_dir is None
    if user_data_dir is None:
        user_data_dir = tempfile.mkdtemp(prefix="manul-chrome-")
    _write_automation_prefs(user_data_dir)

    args = [
        chrome_path,
        "--remote-debugging-port=0",
        f"--user-data-dir={user_data_dir}",
        "--disable-gpu",
        *_AUTOMATION_FLAGS,
    ]
    if headless:
        args.append("--headless=new")
        args.append("--window-size=1920,1080")
    for a in extra_args or []:
        if a not in args:
            args.append(a)

    # Chrome must outlive any single task context — start detached, kill via close().
    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    port = await _read_devtools_port(Path(user_data_dir) / "DevToolsActivePort", proc, timeout=20.0)
    cp = ChromeProcess(proc, user_data_dir, owns_dir, port)
    try:
        await _wait_for_cdp(cp.endpoint, timeout=15.0)
    except Exception:
        await cp.close()
        raise
    return cp


# ── helpers ──────────────────────────────────────────────────────────────


async def _read_devtools_port(port_file: Path, proc: subprocess.Popen[bytes], timeout: float) -> int:
    """Read the port Chrome wrote to ``DevToolsActivePort`` (line 1)."""
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"chrome exited during startup (code {proc.returncode})")
        if port_file.exists():
            try:
                first = port_file.read_text().splitlines()[0].strip()
                if first:
                    return int(first)
            except (OSError, ValueError, IndexError):
                pass
        await asyncio.sleep(0.05)
    raise TimeoutError(f"chrome did not report a DevTools port at {port_file}")


async def _wait_for_cdp(endpoint: str, timeout: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    last_exc: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            await asyncio.to_thread(_http_get_json, f"{endpoint}/json/version")
            return
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(0.1)
    raise TimeoutError(f"CDP endpoint {endpoint} not reachable: {last_exc}")


async def _fetch_browser_ws(endpoint: str) -> str:
    data = await asyncio.to_thread(_http_get_json, f"{endpoint}/json/version")
    ws = data.get("webSocketDebuggerUrl")
    if not ws:
        raise RuntimeError("CDP: no browser-level webSocketDebuggerUrl")
    return ws


def _http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310 — localhost CDP endpoint
        return json.loads(resp.read().decode())


def _write_automation_prefs(user_data_dir: str) -> None:
    """Disable password manager / autofill / download prompts at profile level."""
    default_dir = Path(user_data_dir) / "Default"
    default_dir.mkdir(parents=True, exist_ok=True)
    prefs = {
        "credentials_enable_service": False,
        "credentials_enable_autosignin": False,
        "profile": {
            "password_manager_enabled": False,
            "default_content_setting_values": {"notifications": 2},
        },
        "autofill": {"profile_enabled": False, "credit_card_enabled": False},
        "download": {"prompt_for_download": False},
    }
    try:
        (default_dir / "Preferences").write_text(json.dumps(prefs))
    except OSError as exc:
        _log.debug("could not write chrome prefs: %s", exc)
