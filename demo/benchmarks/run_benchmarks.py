#!/usr/bin/env python3
# benchmarks/run_benchmarks.py
"""
ManulEngine Proof Pack — Benchmark Suite

Compares ManulEngine's heuristic element resolution against raw Playwright
locator strategies on the same local HTML fixtures.

Usage:
    python benchmarks/run_benchmarks.py

Spins up a local HTTP server, runs each resolution task via both approaches,
and prints a comparison table (Success Rate, Avg Resolution Time).
"""

from __future__ import annotations

import asyncio
import http.server
import os
import sys
import threading
import time
from pathlib import Path

# Ensure the package is importable when running from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from playwright.async_api import async_playwright
from manul_engine.scoring import score_elements
from manul_engine.js_scripts import SNAPSHOT_JS
from manul_engine.helpers import detect_mode, extract_quoted

# ── Fixtures directory ────────────────────────────────────────────────────────
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ── Local HTTP server ─────────────────────────────────────────────────────────


def _start_server(directory: str, port: int) -> http.server.HTTPServer:
    """Start a threaded HTTP server serving *directory* on *port*."""
    handler = http.server.SimpleHTTPRequestHandler
    original_init = handler.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["directory"] = directory
        original_init(self, *args, **kwargs)

    handler.__init__ = patched_init  # type: ignore[assignment]
    handler.log_message = lambda *_args, **_kw: None  # silence logs
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ── Task definitions ──────────────────────────────────────────────────────────


class Task:
    """A single resolution task to benchmark."""

    __slots__ = ("fixture", "step", "pw_locator", "expected_tag", "expected_text")

    def __init__(
        self,
        fixture: str,
        step: str,
        pw_locator: str,
        expected_tag: str = "",
        expected_text: str = "",
    ) -> None:
        self.fixture = fixture
        self.step = step
        self.pw_locator = pw_locator  # Playwright locator string
        self.expected_tag = expected_tag.lower()
        self.expected_text = expected_text.lower()


TASKS: list[Task] = [
    # ── dynamic_ids.html ──────────────────────────────────────────────
    Task(
        fixture="dynamic_ids.html",
        step="Fill 'Username' field with 'admin'",
        pw_locator="input#uid-a1b2c3",
        expected_tag="input",
        expected_text="username",
    ),
    Task(
        fixture="dynamic_ids.html",
        step="Click the 'Log In' button",
        pw_locator="button#btn-q4w5e6",
        expected_tag="button",
        expected_text="log in",
    ),
    Task(
        fixture="dynamic_ids.html",
        step="Click the 'Dashboard' link",
        pw_locator="a#link-m1n2o3",
        expected_tag="a",
        expected_text="dashboard",
    ),
    # ── overlapping.html ──────────────────────────────────────────────
    Task(
        fixture="overlapping.html",
        step="Click the 'Submit Order' button",
        pw_locator="button#submit-btn",
        expected_tag="button",
        expected_text="submit order",
    ),
    Task(
        fixture="overlapping.html",
        step="Click the 'Add to Cart' button",
        pw_locator="button#add-cart-visible",
        expected_tag="button",
        expected_text="add to cart",
    ),
    Task(
        fixture="overlapping.html",
        step="Fill the 'Email' field with 'test@test.com'",
        pw_locator="input#real-email",
        expected_tag="input",
        expected_text="email",
    ),
    Task(
        fixture="overlapping.html",
        step="Click the 'Contact Us' link",
        pw_locator="a#real-contact",
        expected_tag="a",
        expected_text="contact us",
    ),
    # ── nested_tables.html ────────────────────────────────────────────
    Task(
        fixture="nested_tables.html",
        step="Fill the 'First Name' field with 'Alice'",
        pw_locator="input[name='first_name']",
        expected_tag="input",
        expected_text="first name",
    ),
    Task(
        fixture="nested_tables.html",
        step="Click the 'Register' button",
        pw_locator="button[type='submit']",
        expected_tag="button",
        expected_text="register",
    ),
    Task(
        fixture="nested_tables.html",
        step="Select 'United States' from the 'Country' dropdown",
        pw_locator="select[name='country']",
        expected_tag="select",
        expected_text="country",
    ),
    # ── custom_dropdown.html ──────────────────────────────────────────
    Task(
        fixture="custom_dropdown.html",
        step="Click the 'Shipping Method' dropdown",
        pw_locator="[data-qa='shipping-method'] .custom-select-trigger",
        expected_tag="div",
        expected_text="shipping",
    ),
    Task(
        fixture="custom_dropdown.html",
        step="Select 'United States' from the 'Country' dropdown",
        pw_locator="select#native-country",
        expected_tag="select",
        expected_text="country",
    ),
]


# ── Benchmark runners ─────────────────────────────────────────────────────────


async def _run_playwright_task(page, task: Task) -> tuple[bool, float]:
    """Attempt to resolve the element using a raw Playwright locator.
    Returns (success, elapsed_ms)."""
    t0 = time.perf_counter()
    try:
        loc = page.locator(task.pw_locator)
        count = await loc.count()
        elapsed = (time.perf_counter() - t0) * 1000
        return count > 0, elapsed
    except Exception:
        elapsed = (time.perf_counter() - t0) * 1000
        return False, elapsed


async def _run_manul_task(page, task: Task) -> tuple[bool, float]:
    """Attempt to resolve the element using ManulEngine's heuristic scorer.
    Returns (success, elapsed_ms)."""
    mode = detect_mode(task.step)
    search_texts = extract_quoted(task.step)

    t0 = time.perf_counter()
    try:
        args = [mode, [t.lower() for t in search_texts]]
        elements = await page.evaluate(SNAPSHOT_JS, args)
        if not elements:
            return False, (time.perf_counter() - t0) * 1000

        scored = score_elements(
            elements,
            step=task.step,
            mode=mode,
            search_texts=search_texts,
            target_field=None,
            is_blind=False,
            learned_elements={},
            last_xpath=None,
        )
        elapsed = (time.perf_counter() - t0) * 1000

        if not scored:
            return False, elapsed

        best = scored[0]
        best_name = best.get("name", "").lower()
        best_tag = best.get("tag_name", "").lower()
        best_aria = best.get("aria_label", "").lower()

        # Validate: the resolved element should match expected signals
        tag_ok = not task.expected_tag or best_tag == task.expected_tag
        text_ok = not task.expected_text or (task.expected_text in best_name or task.expected_text in best_aria)
        return tag_ok and text_ok, elapsed
    except Exception:
        return False, (time.perf_counter() - t0) * 1000


# ── Table printer ─────────────────────────────────────────────────────────────


def _print_table(results: list[dict]) -> None:
    """Print a formatted comparison table."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="ManulEngine vs Raw Playwright — Benchmark Results")
        table.add_column("Fixture", style="cyan")
        table.add_column("Task", style="white", max_width=45)
        table.add_column("PW Success", justify="center")
        table.add_column("PW Time (ms)", justify="right")
        table.add_column("Manul Success", justify="center")
        table.add_column("Manul Time (ms)", justify="right")
        for r in results:
            pw_icon = "[green]✅[/green]" if r["pw_ok"] else "[red]❌[/red]"
            mn_icon = "[green]✅[/green]" if r["mn_ok"] else "[red]❌[/red]"
            table.add_row(
                r["fixture"],
                r["step"][:45],
                pw_icon,
                f"{r['pw_ms']:.1f}",
                mn_icon,
                f"{r['mn_ms']:.1f}",
            )
        # Summary row
        pw_total = sum(1 for r in results if r["pw_ok"])
        mn_total = sum(1 for r in results if r["mn_ok"])
        pw_avg = sum(r["pw_ms"] for r in results) / len(results) if results else 0
        mn_avg = sum(r["mn_ms"] for r in results) / len(results) if results else 0
        table.add_section()
        table.add_row(
            "TOTAL",
            f"{len(results)} tasks",
            f"{pw_total}/{len(results)}",
            f"avg {pw_avg:.1f}",
            f"{mn_total}/{len(results)}",
            f"avg {mn_avg:.1f}",
        )
        console.print(table)

    except ImportError:
        # Fallback: plain text table
        header = f"{'Fixture':<24} {'Task':<45} {'PW':>6} {'PW ms':>8} {'Manul':>6} {'Manul ms':>9}"
        print(f"\n{'=' * len(header)}")
        print("ManulEngine vs Raw Playwright — Benchmark Results")
        print(f"{'=' * len(header)}")
        print(header)
        print("-" * len(header))
        for r in results:
            pw_icon = "  OK" if r["pw_ok"] else "FAIL"
            mn_icon = "  OK" if r["mn_ok"] else "FAIL"
            print(
                f"{r['fixture']:<24} {r['step'][:45]:<45} "
                f"{pw_icon:>6} {r['pw_ms']:>7.1f}ms "
                f"{mn_icon:>6} {r['mn_ms']:>8.1f}ms"
            )
        print("-" * len(header))
        pw_total = sum(1 for r in results if r["pw_ok"])
        mn_total = sum(1 for r in results if r["mn_ok"])
        pw_avg = sum(r["pw_ms"] for r in results) / len(results) if results else 0
        mn_avg = sum(r["mn_ms"] for r in results) / len(results) if results else 0
        print(
            f"{'TOTAL':<24} {len(results)} tasks{' ' * 37}"
            f"{pw_total}/{len(results):>3} avg {pw_avg:>5.1f}ms "
            f"{mn_total}/{len(results):>3} avg {mn_avg:>6.1f}ms"
        )
        print(f"{'=' * len(header)}\n")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    port = 18932  # unlikely to collide
    server = _start_server(str(FIXTURES_DIR), port)
    base_url = f"http://127.0.0.1:{port}"

    print(f"🐾 ManulEngine Benchmark Suite")
    print(f"   Fixtures served at {base_url}")
    print(f"   Tasks: {len(TASKS)}\n")

    results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for task in TASKS:
            url = f"{base_url}/{task.fixture}"
            await page.goto(url, wait_until="domcontentloaded")

            pw_ok, pw_ms = await _run_playwright_task(page, task)
            mn_ok, mn_ms = await _run_manul_task(page, task)

            icon = "✅" if mn_ok else "❌"
            print(f"  {icon} [{task.fixture}] {task.step[:50]}")

            results.append(
                {
                    "fixture": task.fixture,
                    "step": task.step,
                    "pw_ok": pw_ok,
                    "pw_ms": pw_ms,
                    "mn_ok": mn_ok,
                    "mn_ms": mn_ms,
                }
            )

        await browser.close()

    server.shutdown()
    print()
    _print_table(results)


if __name__ == "__main__":
    asyncio.run(main())
