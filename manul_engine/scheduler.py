"""Built-in scheduler for ManulEngine daemon mode.

Parses human-readable ``@schedule:`` expressions (e.g. ``every 5 minutes``,
``daily at 09:00``, ``every monday``) into concrete intervals/times using only
the Python standard library (no third-party ``schedule`` dependency).

Public API
----------
* ``parse_schedule(expr)`` — returns a ``Schedule`` describing the cadence.
* ``daemon_main(args)``    — async entry point for ``manul daemon <dir>``.
"""

from __future__ import annotations

import asyncio
import glob
import os
import re
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

# ── Schedule representation ──────────────────────────────────────────────────

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# Pre-compiled patterns  — all case-insensitive.
_RE_EVERY_N = re.compile(
    r"^every\s+(\d+)\s+(second|seconds|minute|minutes|hour|hours)$", re.I,
)
_RE_EVERY_UNIT = re.compile(
    r"^every\s+(second|minute|hour)$", re.I,
)
_RE_DAILY_AT = re.compile(
    r"^daily\s+at\s+(\d{1,2}):(\d{2})$", re.I,
)
_RE_EVERY_WEEKDAY = re.compile(
    r"^every\s+(" + "|".join(_WEEKDAYS) + r")$", re.I,
)
_RE_EVERY_WEEKDAY_AT = re.compile(
    r"^every\s+(" + "|".join(_WEEKDAYS) + r")\s+at\s+(\d{1,2}):(\d{2})$", re.I,
)


@dataclass(frozen=True)
class Schedule:
    """Parsed schedule descriptor.

    Exactly one of the fields will be set:
    * ``interval_seconds`` — run every N seconds (``every 5 minutes``).
    * ``daily_at``         — ``(hour, minute)`` tuple for ``daily at HH:MM``.
    * ``weekly``           — ``(weekday_int, hour, minute)`` for ``every monday [at HH:MM]``.

    ``raw`` always stores the original expression string.
    """
    raw: str
    interval_seconds: int | None = None
    daily_at: tuple[int, int] | None = None
    weekly: tuple[int, int, int] | None = None


def parse_schedule(expr: str) -> Schedule:
    """Parse a human-readable schedule expression.

    Supported forms
    ---------------
    * ``every 5 minutes`` / ``every 30 seconds`` / ``every 2 hours``
    * ``every minute`` / ``every hour`` / ``every second``
    * ``daily at 09:00``
    * ``every monday`` (defaults to 00:00)
    * ``every friday at 14:30``

    Raises ``ValueError`` on unrecognised expressions.
    """
    s = expr.strip()
    if not s:
        raise ValueError("Empty schedule expression")

    # every N <unit>
    m = _RE_EVERY_N.match(s)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower().rstrip("s")  # "minutes" → "minute"
        multiplier = {"second": 1, "minute": 60, "hour": 3600}[unit]
        return Schedule(raw=s, interval_seconds=n * multiplier)

    # every <unit>  (shorthand for every 1 <unit>)
    m = _RE_EVERY_UNIT.match(s)
    if m:
        unit = m.group(1).lower()
        multiplier = {"second": 1, "minute": 60, "hour": 3600}[unit]
        return Schedule(raw=s, interval_seconds=multiplier)

    # daily at HH:MM
    m = _RE_DAILY_AT.match(s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError(f"Invalid time in schedule: {s!r}")
        return Schedule(raw=s, daily_at=(hh, mm))

    # every <weekday> at HH:MM
    m = _RE_EVERY_WEEKDAY_AT.match(s)
    if m:
        day = _WEEKDAYS[m.group(1).lower()]
        hh, mm = int(m.group(2)), int(m.group(3))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError(f"Invalid time in schedule: {s!r}")
        return Schedule(raw=s, weekly=(day, hh, mm))

    # every <weekday>  (defaults to 00:00)
    m = _RE_EVERY_WEEKDAY.match(s)
    if m:
        day = _WEEKDAYS[m.group(1).lower()]
        return Schedule(raw=s, weekly=(day, 0, 0))

    raise ValueError(f"Unrecognised @schedule expression: {s!r}")


# ── Time helpers ─────────────────────────────────────────────────────────────

def _seconds_until_time(hh: int, mm: int, now: datetime | None = None) -> float:
    """Seconds from *now* until the next occurrence of *hh:mm* today or tomorrow."""
    now = now or datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _seconds_until_weekday(weekday: int, hh: int, mm: int,
                           now: datetime | None = None) -> float:
    """Seconds from *now* until the next *weekday* at *hh:mm*."""
    now = now or datetime.now()
    days_ahead = (weekday - now.weekday()) % 7
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0) + timedelta(days=days_ahead)
    if target <= now:
        target += timedelta(weeks=1)
    return (target - now).total_seconds()


def next_run_delay(sched: Schedule, now: datetime | None = None) -> float:
    """Return the number of seconds until the next scheduled execution."""
    if sched.interval_seconds is not None:
        return float(sched.interval_seconds)
    if sched.daily_at is not None:
        return _seconds_until_time(*sched.daily_at, now=now)
    if sched.weekly is not None:
        return _seconds_until_weekday(*sched.weekly, now=now)
    raise ValueError(f"Schedule has no timing data: {sched!r}")


# ── Per-job async loop ───────────────────────────────────────────────────────

async def _run_scheduled_job(hunt_path: str, sched: Schedule,
                             headless: bool, browser: str | None,
                             screenshot_mode: str) -> None:
    """Infinite loop that runs a single hunt file on its schedule."""
    from .cli import _run_hunt_file

    filename = os.path.basename(hunt_path)

    while True:
        delay = next_run_delay(sched)
        next_ts = datetime.now() + timedelta(seconds=delay)
        print(f"⏰ [{filename}] next run at {next_ts:%Y-%m-%d %H:%M:%S} "
              f"(in {delay:.0f}s) — {sched.raw}")
        await asyncio.sleep(delay)

        print(f"\n🚀 [{filename}] scheduled run starting — {datetime.now():%H:%M:%S}")
        try:
            result = await _run_hunt_file(
                hunt_path,
                headless=headless,
                browser=browser,
                screenshot_mode=screenshot_mode,
            )
            status = result.status.upper()
            print(f"🏁 [{filename}] finished — {status}")
        except Exception:
            print(f"💥 [{filename}] crashed — daemon continues")
            traceback.print_exc(file=sys.stdout)


# ── Daemon entry point ───────────────────────────────────────────────────────

async def daemon_main(args: list[str]) -> None:
    """Entry point for ``manul daemon <directory>``.

    Scans *directory* for ``*.hunt`` files that declare ``@schedule:``,
    launches an async task per file, and runs forever.
    """
    from .cli import parse_hunt_file

    headless = "--headless" in args
    args_clean = [a for a in args if a != "--headless"]

    # Extract --browser <name>
    browser: str | None = None
    if "--browser" in args_clean:
        idx = args_clean.index("--browser")
        if idx + 1 < len(args_clean):
            browser = args_clean[idx + 1]
            args_clean = [a for i, a in enumerate(args_clean) if i not in (idx, idx + 1)]
        else:
            print("Error: --browser requires a value.", file=sys.stderr)
            sys.exit(1)

    # Extract --screenshot <mode>
    screenshot_mode = "on-fail"
    if "--screenshot" in args_clean:
        idx = args_clean.index("--screenshot")
        if idx + 1 < len(args_clean):
            screenshot_mode = args_clean[idx + 1]
            args_clean = [a for i, a in enumerate(args_clean) if i not in (idx, idx + 1)]

    # Extract --html-report
    html_report = "--html-report" in args_clean
    args_clean = [a for a in args_clean if a != "--html-report"]

    if not args_clean:
        print("Usage: manul daemon <directory> [--headless] [--browser <name>]", file=sys.stderr)
        sys.exit(1)

    target_dir = args_clean[0]
    if not os.path.isdir(target_dir):
        print(f"Error: '{target_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Discover .hunt files with @schedule:
    hunt_files = sorted(glob.glob(os.path.join(target_dir, "**", "*.hunt"), recursive=True))
    if not hunt_files:
        print(f"No .hunt files found in '{target_dir}'.")
        return

    scheduled_jobs: list[tuple[str, Schedule]] = []
    for hf in hunt_files:
        parsed = parse_hunt_file(hf)
        if parsed.schedule:
            try:
                sched = parse_schedule(parsed.schedule)
                scheduled_jobs.append((hf, sched))
            except ValueError as exc:
                print(f"⚠️  Skipping {os.path.basename(hf)}: {exc}")

    if not scheduled_jobs:
        print(f"No .hunt files with @schedule: headers found in '{target_dir}'.")
        return

    print(f"\n{'='*60}")
    print(f"😼 ManulEngine Daemon — {len(scheduled_jobs)} scheduled job(s)")
    print(f"{'='*60}")
    for hf, sched in scheduled_jobs:
        print(f"  📋 {os.path.basename(hf)} — {sched.raw}")
    print()

    tasks = [
        asyncio.create_task(
            _run_scheduled_job(hf, sched, headless, browser, screenshot_mode)
        )
        for hf, sched in scheduled_jobs
    ]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("\n🛑 Daemon stopped.")
