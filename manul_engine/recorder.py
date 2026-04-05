# manul_engine/recorder.py
"""
🎬 Semantic Test Recorder — `manul record <URL>`

Launches a headed Playwright browser, injects event listeners that capture
user interactions (clicks, typing, selects, Enter), translates them into
plain-English Hunt DSL steps, and saves the result to a `.hunt` file.

Unlike Playwright codegen, no CSS/XPath selectors are generated — only
semantic labels extracted from the DOM (data-qa, aria-label, placeholder,
name, visible text).
"""

from __future__ import annotations

import asyncio
import os
import sys
from urllib.parse import urlparse

# ── Injected JavaScript ──────────────────────────────────────────────────────
# This script runs in the browser page context.  It captures click, input
# (debounced), change (for selects), and keydown (Enter) events and forwards
# semantic descriptions to the Python handler via the exposed bridge function.

_RECORDER_JS = r"""
(() => {
  // Guard against double-injection (e.g. after SPA navigation).
  if (window.__manulRecorderInjected) return;
  window.__manulRecorderInjected = true;

  // ── Semantic label extraction ──────────────────────────────────────────
  function bestLabel(el) {
    // 1. data-qa / data-testid
    const dqa = el.getAttribute('data-qa') || el.getAttribute('data-testid') || '';
    if (dqa.trim()) return dqa.trim();

    // 2. aria-label
    const ariaLabel = el.getAttribute('aria-label') || '';
    if (ariaLabel.trim()) return ariaLabel.trim();

    // 2b. aria-labelledby
    const labelledBy = el.getAttribute('aria-labelledby') || '';
    if (labelledBy.trim()) {
      const parts = labelledBy.split(/\s+/).map(id => {
        const ref = document.getElementById(id);
        return ref ? ref.textContent.trim() : '';
      }).filter(Boolean);
      if (parts.length) return parts.join(' ');
    }

    // 3. placeholder (inputs)
    const ph = el.getAttribute('placeholder') || '';
    if (ph.trim()) return ph.trim();

    // 4. name attribute
    const nameAttr = el.getAttribute('name') || '';
    if (nameAttr.trim()) return nameAttr.trim();

    // 5. Associated <label>
    if (el.id) {
      const label = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (label) {
        const lt = label.textContent.trim();
        if (lt && lt.length <= 80) return lt;
      }
    }
    // Also check wrapping <label>
    const parentLabel = el.closest('label');
    if (parentLabel) {
      const lt = parentLabel.textContent.trim();
      if (lt && lt.length <= 80) return lt;
    }

    // 6. innerText / textContent (cleaned & truncated)
    const text = (el.innerText || el.textContent || '').trim();
    if (text && text.length <= 60) return text;
    if (text) return text.substring(0, 57) + '...';

    // 7. Fallback: tag + type
    const tag = el.tagName.toLowerCase();
    const type = el.getAttribute('type') || '';
    return type ? tag + '[type=' + type + ']' : tag;
  }

  // ── Debounce helper for input events ───────────────────────────────────
  const _inputTimers = new WeakMap();

  function debounceInput(el, value) {
    const existing = _inputTimers.get(el);
    if (existing) clearTimeout(existing);
    const timer = setTimeout(() => {
      _inputTimers.delete(el);
      const label = bestLabel(el);
      window.recordManulEvent(JSON.stringify({
        action: 'fill',
        target: label,
        value: value
      }));
    }, 600);
    _inputTimers.set(el, timer);
  }

  // ── Event listeners ────────────────────────────────────────────────────

  // Click
  document.addEventListener('click', (e) => {
    // Ignore clicks on <select> and its <option> children — the change event handles these semantically.
    const rawTag = (e.target.tagName || '').toLowerCase();
    if (rawTag === 'select') return;
    if (rawTag === 'option' && e.target.closest('select')) return;

    const el = e.target.closest('a, button, [role="button"], [role="link"], [role="menuitem"], [role="tab"], [role="option"], input[type="submit"], input[type="button"]');
    if (!el) return;
    // Ignore clicks on text inputs — those are handled by the input event.
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['text', 'email', 'password', 'search', 'tel', 'url', 'number'].includes(type)) return;
    if (tag === 'textarea') return;

    const label = bestLabel(el);

    window.recordManulEvent(JSON.stringify({
      action: 'click',
      target: label,
      value: ''
    }));
  }, true);

  // Input (debounced) — captures typing into text fields
  document.addEventListener('input', (e) => {
    const el = e.target;
    const tag = el.tagName.toLowerCase();
    if (tag === 'select') return;  // handled by change event
    if (tag !== 'input' && tag !== 'textarea' && !el.isContentEditable) return;
    const type = (el.getAttribute('type') || 'text').toLowerCase();
    if (['checkbox', 'radio', 'submit', 'button', 'file', 'image', 'reset', 'hidden'].includes(type)) return;
    debounceInput(el, el.value || el.textContent || '');
  }, true);

  // Change — captures <select> dropdown changes and checkbox/radio toggles
  document.addEventListener('change', (e) => {
    const el = e.target;
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();

    // Checkbox: read el.checked AFTER the toggle has occurred
    if (tag === 'input' && type === 'checkbox') {
      const label = bestLabel(el);
      const action = el.checked ? 'check' : 'uncheck';
      window.recordManulEvent(JSON.stringify({
        action: action,
        target: label,
        value: ''
      }));
      return;
    }

    // Radio button
    if (tag === 'input' && type === 'radio') {
      const label = bestLabel(el);
      window.recordManulEvent(JSON.stringify({
        action: 'radio',
        target: label,
        value: ''
      }));
      return;
    }

    // <select> dropdown
    if (tag !== 'select') return;
    const label = bestLabel(el);
    const selected = el.options[el.selectedIndex];
    const optionText = selected ? (selected.text || selected.textContent || '').trim() : el.value;
    window.recordManulEvent(JSON.stringify({
      action: 'select',
      target: label,
      value: optionText
    }));
  }, true);

  // Keydown — captures Enter key presses
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const el = e.target;
    const tag = el.tagName.toLowerCase();
    // If the user presses Enter inside an input/textarea, emit PRESS ENTER
    if (tag === 'input' || tag === 'textarea') {
      window.recordManulEvent(JSON.stringify({
        action: 'press',
        target: '',
        value: 'Enter'
      }));
    }
  }, true);
})();
"""


# ── DSL generation ────────────────────────────────────────────────────────────


def _escape_dsl(text: str) -> str:
    """Escape single quotes in text to keep DSL lines balanced."""
    return text.replace("'", "\\'")


def _event_to_dsl(event: dict) -> str | None:
    """Convert a recorded browser event dict into a Hunt DSL line.

    Returns None for events that should be silently skipped.
    """
    action = event.get("action", "")
    target = _escape_dsl(event.get("target", "").strip())
    value = _escape_dsl(event.get("value", "").strip())

    if action == "click":
        if not target:
            return None
        return f"    Click the '{target}' button"

    if action == "fill":
        if not target:
            return None
        return f"    Fill '{target}' with '{value}'"

    if action == "select":
        if not target:
            return None
        return f"    Select '{value}' from the '{target}' dropdown"

    if action == "check":
        if not target:
            return None
        return f"    Check the checkbox for '{target}'"

    if action == "uncheck":
        if not target:
            return None
        return f"    Uncheck the checkbox for '{target}'"

    if action == "radio":
        if not target:
            return None
        return f"    Click the radio button for '{target}'"

    if action == "press":
        if value == "Enter":
            return "    PRESS ENTER"
        return None

    return None


# ── Step aggregation ──────────────────────────────────────────────────────────

def _aggregate_event(
    event: dict,
    recorded_lines: list[str],
    last_fill_target: list[str | None],
) -> str | None:
    """Process a recorded event with step aggregation (collapsing consecutive fills).

    If the event is a ``fill`` on the same target as the previous fill, the last
    entry in *recorded_lines* is **replaced** instead of appending a new line.

    Returns the DSL line that was appended/updated, or ``None`` when the event
    was silently skipped.

    *last_fill_target* is a single-element list used as mutable state — it is
    updated in-place so callers can track continuity between invocations.
    """
    dsl = _event_to_dsl(event)
    if dsl is None:
        return None

    action = event.get("action", "")
    target = event.get("target", "").strip()

    if action == "fill" and target and target == last_fill_target[0] and recorded_lines:
        recorded_lines[-1] = dsl
    else:
        recorded_lines.append(dsl)

    last_fill_target[0] = target if action == "fill" else None
    return dsl


# ── Default output path ──────────────────────────────────────────────────────

def _default_output(filename: str = "recorded_mission.hunt") -> str:
    """Return tests_home/filename, reading tests_home from the project config."""
    import json
    from pathlib import Path

    cfg_path = Path.cwd() / "manul_engine_configuration.json"
    if not cfg_path.exists():
        cfg_path = Path(__file__).resolve().parents[1] / "manul_engine_configuration.json"
    tests_home = "tests"
    if cfg_path.exists():
        try:
            tests_home = json.loads(cfg_path.read_text("utf-8")).get("tests_home", "tests") or "tests"
        except Exception:
            pass
    folder = Path(tests_home)
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / filename)


# ── Playwright orchestration ─────────────────────────────────────────────────

async def record_session(
    url: str,
    output_file: str | None = None,
    browser: str = "chromium",
) -> str:
    """Launch a headed browser, record user interactions, and save a .hunt file.

    Parameters
    ----------
    url:
        The URL to navigate to initially.
    output_file:
        Absolute or relative path for the generated .hunt file.
        When *None*, defaults to ``tests_home/recorded_mission.hunt``.
    browser:
        Playwright browser engine: ``chromium``, ``firefox``, or ``webkit``.

    Returns
    -------
    str
        Absolute path to the saved .hunt file.
    """
    from playwright.async_api import async_playwright

    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        print(f"❌ Invalid URL: {url}", file=sys.stderr)
        sys.exit(1)

    if output_file is None:
        output_file = _default_output()
    output_abs = os.path.abspath(output_file)

    # Collected DSL lines (4-space indented action lines).
    recorded_lines: list[str] = []
    # Step aggregation state — collapse consecutive fills on the same target.
    last_fill_target: list[str | None] = [None]

    def on_event(raw_json: str) -> None:
        """Bridge callback invoked from the browser JS context."""
        import json
        try:
            event = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            return

        prev_len = len(recorded_lines)
        dsl = _aggregate_event(event, recorded_lines, last_fill_target)
        if dsl is None:
            return

        # Real-time console feedback for the user.
        if len(recorded_lines) == prev_len:
            print(f"  📝 {dsl.strip()}  (updated)")
        else:
            print(f"  📝 {dsl.strip()}")

    print(f"\n🎬 Manul Recorder — recording session for {url}")
    print(f"   Browser: {browser} | Output: {output_abs}")
    print("   Interact with the page. Close the browser or press Ctrl+C to finish.\n")

    async with async_playwright() as pw:
        launcher = getattr(pw, browser)
        b = await launcher.launch(headless=False)
        context = await b.new_context()

        # Inject the recorder script into every new page/frame automatically.
        await context.add_init_script(_RECORDER_JS)

        page = await context.new_page()

        # Expose the Python bridge so JS can call window.recordManulEvent().
        await page.expose_function("recordManulEvent", on_event)

        # Re-inject on navigations (add_init_script covers new documents,
        # but expose_function bindings persist across navigations in the
        # same page automatically in Playwright).
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        except Exception as exc:
            print(f"   ⚠️  Initial navigation issue: {exc}")
            # Continue — the browser is still usable.

        # Wait until the browser is closed by the user.
        try:
            await _wait_for_close(page)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n⏹  Recording stopped by user.")
        finally:
            try:
                await b.close()
            except Exception:
                pass

    # ── Write the .hunt file ──────────────────────────────────────────────
    _write_hunt_file(output_abs, url, recorded_lines)

    print(f"\n✅ Recorded {len(recorded_lines)} step(s) → {output_abs}")
    return output_abs


async def _wait_for_close(page) -> None:
    """Block until the page (or its browser) is closed."""
    closed = asyncio.get_running_loop().create_future()

    def _on_close(_: object = None) -> None:
        if not closed.done():
            closed.set_result(True)

    page.on("close", _on_close)
    try:
        await closed
    except asyncio.CancelledError:
        raise


def _write_hunt_file(path: str, url: str, lines: list[str]) -> None:
    """Write the final .hunt file with proper STEP-grouped format."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    header = [
        "@context: Recorded session",
        f"@title: {urlparse(url).netloc or 'recorded'}",
        "",
        "STEP 1: Recorded interactions",
        f"    NAVIGATE to {url}",
    ]

    with open(path, "w", encoding="utf-8") as fh:
        for line in header:
            fh.write(line + "\n")
        for line in lines:
            fh.write(line + "\n")
        fh.write("DONE.\n")


# ── CLI entry point ──────────────────────────────────────────────────────────

async def record_main(args: list[str]) -> None:
    """Async entry point called from ``cli.main()`` when subcommand is ``record``."""

    _VALID_BROWSERS = {"chromium", "firefox", "webkit"}
    browser = "chromium"
    if "--browser" in args:
        idx = args.index("--browser")
        if idx + 1 < len(args):
            candidate = args[idx + 1].strip().lower()
            if candidate in _VALID_BROWSERS:
                browser = candidate
            else:
                print(f"Error: unsupported browser '{args[idx + 1]}'.", file=sys.stderr)
                sys.exit(1)
            args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]
        else:
            print("Error: --browser requires a value (chromium|firefox|webkit).", file=sys.stderr)
            sys.exit(1)

    if not args:
        print(
            "Usage: manul record <URL> [output.hunt] [--browser chromium|firefox|webkit]",
            file=sys.stderr,
        )
        sys.exit(1)

    url = args[0]

    # Optional output file: second positional arg or --output flag.
    output_file: str | None = None
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_file = args[idx + 1]
        else:
            print("Error: --output requires a value.", file=sys.stderr)
            sys.exit(1)
    elif len(args) >= 2 and args[1].endswith(".hunt"):
        raw = args[1]
        if "/" in raw or "\\" in raw:
            output_file = raw
        else:
            output_file = _default_output(raw)

    await record_session(url, output_file=output_file, browser=browser)
