#!/usr/bin/env python3
"""Token-efficiency benchmark for ManulEngine's agent surface.

Measures how many tokens an LLM agent spends to *perceive* a page via
``manul map`` versus the two common baselines — raw page HTML and the
accessibility tree — and compares authoring a flow as a ``.hunt`` file versus
an equivalent Playwright script.

Run from the repo root::

    pip install tiktoken          # one-off; not a runtime dependency
    python scripts/measure_tokens.py

Requires a system-installed Chrome/Chromium on PATH (the CDP target). Pages are
ManulEngine's own synthetic test fixtures — clean by design, so the reported
advantage is conservative; real-world HTML is far more bloated.
"""

from __future__ import annotations

import asyncio
import importlib
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def toks(s: str) -> int:
        return len(_ENC.encode(s))

    _TOK_NOTE = "GPT-4 tokenizer (cl100k_base)"
except ImportError:

    def toks(s: str) -> int:
        # Transparent fallback: ~4 chars/token BPE estimate.
        return max(1, round(len(s) / 4))

    _TOK_NOTE = "≈ chars/4 estimate (install tiktoken for exact GPT-4 counts)"

from manul_engine import agent_cli  # noqa: E402
from manul_engine.cdp import CDPBrowser  # noqa: E402
from manul_engine.cdp.chrome import launch_chrome  # noqa: E402


def _biggest_dom(modname: str) -> tuple[str, str]:
    mod = importlib.import_module(f"manul_engine.test.{modname}")
    best: tuple[str, str] | None = None
    for k, v in vars(mod).items():
        if k.endswith("_DOM") and isinstance(v, str) and (best is None or len(v) > len(best[1])):
            best = (k, v)
    if best is None:
        raise RuntimeError(f"no *_DOM constant in {modname}")
    return best


async def _map_json(endpoint: str) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        await agent_cli.agent_main("map", ["--cdp", endpoint, "--max-per-group", "12"])
    return buf.getvalue().strip()


async def _ax_tree(page) -> str:
    await page._send("Accessibility.enable")
    res = await page._send("Accessibility.getFullAXTree")
    lines = []
    for n in res.get("nodes", []):
        role = (n.get("role") or {}).get("value", "")
        name = (n.get("name") or {}).get("value", "")
        if role and name:
            lines.append(f"{role}: {name}")
    return "\n".join(lines)


_HUNT = """@title: swag-checkout
@var: {user} = standard_user
@var: {pass} = secret_sauce

STEP 1: Login
    NAVIGATE to https://www.saucedemo.com/
    Fill 'Username' field with '{user}'
    Fill 'Password' field with '{pass}'
    Click 'Login' button
STEP 2: Checkout
    Click 'Add to cart' button near 'Sauce Labs Backpack'
    Click the 'Shopping cart' link
    Click 'Checkout' button
    Fill 'First Name' with 'Alice'
    Fill 'Last Name' with 'Smith'
    Fill 'Zip/Postal Code' with '49000'
    Click 'Continue' button
    Click 'Finish' button
    VERIFY that 'Thank you for your order!' is present
DONE.
"""

_PLAYWRIGHT = """import asyncio
from playwright.async_api import async_playwright, expect

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.saucedemo.com/")
        await page.fill("#user-name", "standard_user")
        await page.fill("#password", "secret_sauce")
        await page.click("#login-button")
        await page.click("button[data-test='add-to-cart-sauce-labs-backpack']")
        await page.click(".shopping_cart_link")
        await page.click("#checkout")
        await page.fill("#first-name", "Alice")
        await page.fill("#last-name", "Smith")
        await page.fill("#postal-code", "49000")
        await page.click("#continue")
        await page.click("#finish")
        await expect(page.locator("text=Thank you for your order!")).to_be_visible()
        await browser.close()

asyncio.run(main())
"""


async def main() -> None:
    print(f"Token counts via: {_TOK_NOTE}\n")
    cp = await launch_chrome(headless=True)
    endpoint = cp.endpoint
    rows = []
    try:
        for mod in ("test_01_ecommerce", "test_08_crm"):
            name, dom = _biggest_dom(mod)
            b = await CDPBrowser.connect_over_cdp(endpoint)
            page = await b.page_matching("")
            await page.navigate("about:blank")
            await page.set_content(dom)
            await asyncio.sleep(0.4)
            raw_html = await page.content()
            ax = await _ax_tree(page)
            await b.close()
            rows.append(
                {
                    "page": f"{mod} ({name})",
                    "raw": toks(raw_html),
                    "ax": toks(ax),
                    "map": toks(await _map_json(endpoint)),
                }
            )
    finally:
        await cp.close()

    print("=== Page perception: tokens an LLM spends to 'see' the page ===")
    print(f"{'page':32}{'raw HTML':>10}{'a11y tree':>11}{'manul map':>11}{'vs HTML':>9}{'vs a11y':>9}")
    for r in rows:
        print(
            f"{r['page']:32}{r['raw']:>10}{r['ax']:>11}{r['map']:>11}"
            f"{r['raw'] / r['map']:>8.1f}x{(r['ax'] / r['map'] if r['ax'] else 0):>8.1f}x"
        )

    print("\n=== Script authoring: same checkout flow ===")
    h, pw = toks(_HUNT), toks(_PLAYWRIGHT)
    print(f"  .hunt (plain English, no selectors): {h:>4} tokens")
    print(f"  Playwright (Python + CSS selectors): {pw:>4} tokens")
    print(f"  → {pw / h:.2f}x ({100 * (1 - h / pw):.0f}% fewer) and zero brittle selectors")


if __name__ == "__main__":
    asyncio.run(main())
