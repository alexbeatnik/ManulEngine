# manul_engine/scanner.py
"""
🔍 Smart Page Scanner — `manul scan <URL>`

Opens a URL with Playwright, scans for interactive elements (including Shadow DOM),
and writes a draft `.hunt` file with ManulEngine-compatible steps.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from urllib.parse import urlparse

from .js_scripts import SCAN_JS

# ── Element → hunt step mapping ───────────────────────────────────────────────

_SKIP_LABELS = frozenset({
    "", "click", "button", "submit", "link", "go", "close", "×", "✕", "✖",
    "menu", "toggle", "show", "hide",
})

def _is_useful(identifier: str, kind: str) -> bool:
    """Filter out labels that produce useless / ambiguous steps."""
    label = identifier.strip().lower()
    if not label or label in _SKIP_LABELS:
        return False
    if len(label) > 80:
        return False
    # Nav links with raw URLs are noise
    if label.startswith("http://") or label.startswith("https://"):
        return False
    return True


def _map_to_step(kind: str, identifier: str) -> str:
    """Convert a scanned element into a plain hunt action line (no number prefix)."""
    i = identifier.strip()
    if kind == "input":
        return f"Fill '{i}' with ''"
    if kind == "select":
        return f"Select 'Option' from the '{i}' dropdown"
    if kind == "checkbox":
        return f"Check the checkbox for '{i}'"
    if kind == "radio":
        return f"Click the radio button for '{i}'"
    if kind == "link":
        return f"Click the '{i}' link"
    # button / role=button / fallback
    return f"Click the '{i}' button"


def build_hunt(url: str, elements: list[dict]) -> str:
    """
    Build a complete .hunt file text from a URL and the scanned element list.

    Parameters
    ----------
    url:
        The page URL that was scanned.
    elements:
        List of dicts ``{"type": str, "identifier": str}`` from SCAN_JS.

    Returns
    -------
    str
        Ready-to-save .hunt file content.
    """
    lines: list[str] = [
        f"@context: Auto-generated scan for {url}",
        "@title: scan-draft",
        "",
        f"STEP 1:\n    NAVIGATE to {url}",
        "",
        f"STEP 2:\n    WAIT 2",
        "",
    ]

    step = 3
    seen_labels: set[tuple[str, str]] = set()

    for el in elements:
        kind = el.get("type", "")
        identifier = el.get("identifier", "").strip()

        if not _is_useful(identifier, kind):
            continue

        dedup_key = (kind, identifier.lower())
        if dedup_key in seen_labels:
            continue
        seen_labels.add(dedup_key)

        action = _map_to_step(kind, identifier)
        lines.append(f"STEP {step}:\n    {action}")
        lines.append("")
        step += 1

    lines.append("DONE.")

    return "\n".join(lines) + "\n"


# ── Playwright execution ───────────────────────────────────────────────────────

async def scan_page(
    url: str,
    output_file: str = "draft.hunt",
    headless: bool = False,
    browser: str = "chromium",
) -> None:
    """
    Open *url* in a Playwright browser, run the DOM scanner, and write a
    draft .hunt file to *output_file*.

    Parameters
    ----------
    url:
        Full URL to scan (must include scheme).
    output_file:
        Path to write the generated .hunt draft.
    headless:
        Run the browser headless (default: False so user can watch).
    browser:
        Playwright browser engine: 'chromium', 'firefox', or 'webkit'.
    """
    from playwright.async_api import async_playwright

    # ── Normalise URL ─────────────────────────────────────────────────────────
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        print(f"❌ Invalid URL: {url}", file=sys.stderr)
        sys.exit(1)

    # ── Launch browser ───────────────────────────────────────────────────────
    print(f"\n🔍 Manul Scanner — scanning {url}")
    print("   Browser:", browser, "| Headless:", headless)

    async with async_playwright() as pw:
        launcher = getattr(pw, browser)
        b = await launcher.launch(headless=headless)
        page = await b.new_page()

        try:
            print("   Navigating …")
            await page.goto(url, wait_until="networkidle", timeout=30_000)
        except Exception as exc:
            # Fallback: load → domcontentloaded if networkidle times out
            print(f"   ⚠️  networkidle timed out ({exc}), falling back to domcontentloaded …")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                await asyncio.sleep(2)
            except Exception as exc2:
                print(f"❌ Navigation failed: {exc2}", file=sys.stderr)
                await b.close()
                sys.exit(1)

        print("   Running DOM scanner …")
        raw = await page.evaluate(SCAN_JS)
        await b.close()

    elements: list[dict] = json.loads(raw)
    print(f"   Found {len(elements)} interactive element(s) before dedup/filter.")

    # ── Build & write hunt ────────────────────────────────────────────────────
    hunt_text = build_hunt(url, elements)

    output_abs = os.path.abspath(output_file)
    os.makedirs(os.path.dirname(output_abs) or ".", exist_ok=True)
    with open(output_abs, "w", encoding="utf-8") as fh:
        fh.write(hunt_text)

    print(f"\n✅ Draft saved → {output_abs}")
    print(f"\n{'─'*60}")
    print(hunt_text)
    print(f"{'─'*60}\n")


def _default_output(filename: str = "draft.hunt") -> str:
    """Return tests_home/filename, reading tests_home from the project config."""
    import json, pathlib
    cfg_path = pathlib.Path.cwd() / "manul_engine_configuration.json"
    if not cfg_path.exists():
        cfg_path = pathlib.Path(__file__).resolve().parents[1] / "manul_engine_configuration.json"
    tests_home = "tests"
    if cfg_path.exists():
        try:
            tests_home = json.loads(cfg_path.read_text("utf-8")).get("tests_home", "tests") or "tests"
        except Exception:
            pass
    folder = pathlib.Path(tests_home)
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / filename)


async def scan_main(args: list[str]) -> None:
    """Async entry point called by cli.main() when first real arg is 'scan'."""

    headless = "--headless" in args
    args = [a for a in args if a != "--headless"]

    _VALID_BROWSERS = {"chromium", "firefox", "webkit"}
    browser = "chromium"
    if "--browser" in args:
        idx = args.index("--browser")
        if idx + 1 < len(args):
            candidate = args[idx + 1].strip().lower()
            if candidate in _VALID_BROWSERS:
                browser = candidate
            else:
                print(f"Error: unsupported browser '{args[idx+1]}'.", file=sys.stderr)
                sys.exit(1)
            args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
        else:
            print("Error: --browser requires a value (chromium|firefox|webkit).", file=sys.stderr)
            sys.exit(1)

    output_file = _default_output()
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_file = args[idx + 1]
            args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
        else:
            print("Error: --output requires a value.", file=sys.stderr)
            sys.exit(1)

    if not args:
        print(
            "Usage: manul scan <URL> [output.hunt] [--output output.hunt] [--headless] [--browser chromium|firefox|webkit]",
            file=sys.stderr,
        )
        sys.exit(1)

    url = args[0]

    # Second positional arg ending in .hunt is treated as --output:
    #   manul scan facebook.com tests/test.hunt  (explicit path → use as-is)
    #   manul scan facebook.com test.hunt         (bare name → tests_home/test.hunt)
    if len(args) >= 2 and args[1].endswith(".hunt"):
        raw = args[1]
        # Treat both / and \ as path separators so Windows-style paths work on
        # POSIX too (os.path.dirname ignores \ on Linux).
        if "/" in raw or "\\" in raw:
            output_file = raw
        else:
            output_file = _default_output(raw)

    await scan_page(url, output_file=output_file, headless=headless, browser=browser)
