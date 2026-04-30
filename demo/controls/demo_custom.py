# controls/demo_custom.py
"""
Demo custom control: React Datepicker on the Checkout Page.

This file demonstrates the Custom Controls pattern for ManulEngine.
Drop any .py file into the controls/ directory at your project root and
the engine will auto-load it on demand via load_custom_controls().

The @custom_control decorator registers a (page, target) pair so that
whenever the engine encounters a matching step it calls this function
instead of attempting DOM heuristics or LLM resolution.

HOW IT WORKS
------------
1. pages/<site>.json maps the checkout URL to "Checkout Page".
2. The hunt step  Fill 'React Datepicker' with '2026-12-25'  is parsed.
3. Before any DOM snapshot is taken, core.py checks the registry:
       get_custom_control("Checkout Page", "React Datepicker")
4. This function is returned and called with a single ControlContext.
5. Standard heuristics and AI resolution are bypassed entirely.

HANDLER SIGNATURE  (since 0.0.9.30 — breaking change)
-----------------------------------------------------
    async def handler(ctx: ControlContext) -> None

    ctx.page       — live Playwright Page (use it as `ctx.page.locator(...)`).
    ctx.action     — DSL mode: "input" / "clickable" / "select" / "hover" / "drag" / "locate".
    ctx.value      — type/select value, or None.
    ctx.target     — the quoted target from the step (e.g. "React Datepicker").
    ctx.page_name  — the resolved pages/ label (matches @custom_control(page=…)).
    ctx.url        — page.url snapshot at dispatch time.
    ctx.step       — the original step text (with variables substituted).

Both sync and async handlers are supported; the engine awaits async ones.
"""

from __future__ import annotations

from manul_engine import ControlContext, custom_control


@custom_control(page="Checkout Page", target="React Datepicker")
async def handle_react_datepicker(ctx: ControlContext) -> None:
    """
    Interact with a React-based custom datepicker widget.

    The widget consists of:
    - A text input that triggers a calendar popup when focused.
    - Month/year navigation chevrons (previous / next).
    - Day cells rendered as <div role="option"> elements.

    Rather than fighting heuristics against 31 identically-styled day
    cells, we drive the widget with direct Playwright locators.
    """
    page = ctx.page
    input_selector = ".react-datepicker__input-container input"
    input_loc = page.locator(input_selector).first

    if ctx.action == "input" and ctx.value:
        # Open the calendar and clear any pre-filled date.
        await input_loc.click()
        await input_loc.fill("")

        # Parse the incoming date string.  Accepted format: YYYY-MM-DD.
        try:
            year_str, month_str, day_str = ctx.value.split("-")
            target_year = int(year_str)
            target_month = int(month_str)
            target_day = int(day_str)
        except ValueError:
            # Fallback: type the raw value directly and let the widget handle it.
            await input_loc.type(ctx.value, delay=50)
            return

        # Navigate month / year until the calendar shows the target month.
        # The header text looks like "December 2026".
        _MONTH_NAMES = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        target_header = f"{_MONTH_NAMES[target_month - 1]} {target_year}"
        header_loc = page.locator(".react-datepicker__current-month").first
        next_btn = page.locator(".react-datepicker__navigation--next").first
        prev_btn = page.locator(".react-datepicker__navigation--previous").first

        for _ in range(24):  # guard: max 2 years of navigation
            header_text = (await header_loc.inner_text()).strip()
            if header_text == target_header:
                break
            # Determine direction: compare "Month YYYY" lexicographically.
            current_parts = header_text.split()
            current_month_idx = _MONTH_NAMES.index(current_parts[0]) + 1
            current_year = int(current_parts[1])
            if (current_year, current_month_idx) < (target_year, target_month):
                await next_btn.click()
            else:
                await prev_btn.click()

        # Click the day cell.
        day_cell = page.locator(
            f".react-datepicker__day--0{target_day:02d}:not(.react-datepicker__day--outside-month)"
        ).first
        await day_cell.click()

    elif ctx.action in ("clickable", "locate"):
        # For a plain click or locate just focus the input to open the popup.
        await input_loc.click()

    # For hover, select, drag — not applicable to a datepicker; no-op.
