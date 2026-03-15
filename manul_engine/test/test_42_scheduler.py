# manul_engine/test/test_42_scheduler.py
"""
Unit-test suite for the built-in scheduler (scheduler.py).

Tests:
  1. parse_schedule — all supported expression forms.
  2. parse_schedule — error cases for invalid expressions.
  3. next_run_delay — interval schedules return the interval.
  4. _seconds_until_time — daily schedule time math.
  5. _seconds_until_weekday — weekly schedule time math.
  6. @schedule: header parsed correctly in ParsedHunt.
  7. ParsedHunt.schedule is empty string when not declared.

No browser or network required — tests the parser and time math only.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.scheduler import (
    Schedule,
    parse_schedule,
    next_run_delay,
    _seconds_until_time,
    _seconds_until_weekday,
)
from manul_engine.cli import parse_hunt_file

# ── Test helpers ──────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0


def _assert(condition: bool, name: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"    ✅  {name}")
    else:
        _FAIL += 1
        suffix = f" ({detail})" if detail else ""
        print(f"    ❌  {name}{suffix}")


# ── 1. parse_schedule — interval expressions ─────────────────────────────────

def test_parse_every_n_minutes() -> None:
    s = parse_schedule("every 5 minutes")
    _assert(s.interval_seconds == 300, "every 5 minutes = 300s")
    _assert(s.daily_at is None, "no daily_at for interval")
    _assert(s.weekly is None, "no weekly for interval")
    _assert(s.raw == "every 5 minutes", "raw preserved")


def test_parse_every_n_seconds() -> None:
    s = parse_schedule("every 30 seconds")
    _assert(s.interval_seconds == 30, "every 30 seconds = 30s")


def test_parse_every_n_hours() -> None:
    s = parse_schedule("every 2 hours")
    _assert(s.interval_seconds == 7200, "every 2 hours = 7200s")


def test_parse_every_unit_shorthand() -> None:
    s1 = parse_schedule("every minute")
    _assert(s1.interval_seconds == 60, "every minute = 60s")
    s2 = parse_schedule("every hour")
    _assert(s2.interval_seconds == 3600, "every hour = 3600s")
    s3 = parse_schedule("every second")
    _assert(s3.interval_seconds == 1, "every second = 1s")


def test_parse_every_1_minute() -> None:
    s = parse_schedule("every 1 minute")
    _assert(s.interval_seconds == 60, "every 1 minute = 60s")


# ── 2. parse_schedule — daily expressions ────────────────────────────────────

def test_parse_daily_at() -> None:
    s = parse_schedule("daily at 09:00")
    _assert(s.daily_at == (9, 0), "daily at 09:00 → (9, 0)")
    _assert(s.interval_seconds is None, "no interval for daily")


def test_parse_daily_at_afternoon() -> None:
    s = parse_schedule("daily at 15:30")
    _assert(s.daily_at == (15, 30), "daily at 15:30 → (15, 30)")


# ── 3. parse_schedule — weekly expressions ───────────────────────────────────

def test_parse_every_monday() -> None:
    s = parse_schedule("every monday")
    _assert(s.weekly == (0, 0, 0), "every monday → (0, 0, 0)")
    _assert(s.interval_seconds is None, "no interval for weekly")
    _assert(s.daily_at is None, "no daily_at for weekly")


def test_parse_every_friday_at() -> None:
    s = parse_schedule("every friday at 14:30")
    _assert(s.weekly == (4, 14, 30), "every friday at 14:30 → (4, 14, 30)")


def test_parse_every_sunday() -> None:
    s = parse_schedule("every sunday")
    _assert(s.weekly == (6, 0, 0), "every sunday → (6, 0, 0)")


def test_parse_every_wednesday_at() -> None:
    s = parse_schedule("every wednesday at 08:15")
    _assert(s.weekly == (2, 8, 15), "every wednesday at 08:15 → (2, 8, 15)")


# ── 4. parse_schedule — case insensitivity ───────────────────────────────────

def test_parse_case_insensitive() -> None:
    s1 = parse_schedule("Every 5 Minutes")
    _assert(s1.interval_seconds == 300, "case insensitive: Every 5 Minutes")
    s2 = parse_schedule("DAILY AT 12:00")
    _assert(s2.daily_at == (12, 0), "case insensitive: DAILY AT 12:00")
    s3 = parse_schedule("Every Monday")
    _assert(s3.weekly == (0, 0, 0), "case insensitive: Every Monday")


# ── 5. parse_schedule — error cases ──────────────────────────────────────────

def test_parse_empty() -> None:
    try:
        parse_schedule("")
        _assert(False, "empty expression should raise ValueError")
    except ValueError:
        _assert(True, "empty expression raises ValueError")


def test_parse_unknown_expression() -> None:
    try:
        parse_schedule("at dawn")
        _assert(False, "unknown expression should raise ValueError")
    except ValueError:
        _assert(True, "unknown expression raises ValueError")


def test_parse_invalid_time() -> None:
    try:
        parse_schedule("daily at 25:00")
        _assert(False, "invalid time should raise ValueError")
    except ValueError:
        _assert(True, "invalid hour raises ValueError")


def test_parse_invalid_weekly_time() -> None:
    try:
        parse_schedule("every monday at 12:99")
        _assert(False, "invalid weekly time should raise ValueError")
    except ValueError:
        _assert(True, "invalid weekly minute raises ValueError")


# ── 6. next_run_delay — interval ─────────────────────────────────────────────

def test_next_run_delay_interval() -> None:
    s = parse_schedule("every 10 minutes")
    delay = next_run_delay(s)
    _assert(delay == 600.0, f"interval delay = 600.0 (got {delay})")


# ── 7. _seconds_until_time ───────────────────────────────────────────────────

def test_seconds_until_time_future_today() -> None:
    now = datetime(2026, 3, 15, 8, 0, 0)
    secs = _seconds_until_time(9, 0, now=now)
    _assert(secs == 3600.0, f"8:00 → 9:00 = 3600s (got {secs})")


def test_seconds_until_time_past_today() -> None:
    now = datetime(2026, 3, 15, 10, 0, 0)
    secs = _seconds_until_time(9, 0, now=now)
    expected = 23 * 3600.0  # next day 09:00
    _assert(secs == expected, f"10:00 → next day 09:00 = {expected}s (got {secs})")


def test_seconds_until_time_exact_now() -> None:
    now = datetime(2026, 3, 15, 9, 0, 0)
    secs = _seconds_until_time(9, 0, now=now)
    # Exactly now → should schedule for next day
    _assert(secs == 86400.0, f"exact now → 86400s (got {secs})")


# ── 8. _seconds_until_weekday ────────────────────────────────────────────────

def test_seconds_until_weekday_same_day_future() -> None:
    # 2026-03-15 is a Sunday (weekday=6)
    now = datetime(2026, 3, 15, 8, 0, 0)
    secs = _seconds_until_weekday(6, 10, 0, now=now)
    _assert(secs == 7200.0, f"Sunday 08:00 → Sunday 10:00 = 7200s (got {secs})")


def test_seconds_until_weekday_same_day_past() -> None:
    # 2026-03-15 is Sunday, time already past
    now = datetime(2026, 3, 15, 12, 0, 0)
    secs = _seconds_until_weekday(6, 10, 0, now=now)
    expected = 7 * 86400 - 2 * 3600  # next Sunday at 10:00
    _assert(secs == expected, f"Sunday past → next Sunday (got {secs})")


def test_seconds_until_weekday_different_day() -> None:
    # 2026-03-15 is Sunday (6), asking for Monday (0)
    now = datetime(2026, 3, 15, 0, 0, 0)
    secs = _seconds_until_weekday(0, 0, 0, now=now)
    expected = 86400.0  # tomorrow
    _assert(secs == expected, f"Sunday → Monday = 86400s (got {secs})")


# ── 9. next_run_delay — daily, weekly ────────────────────────────────────────

def test_next_run_delay_daily() -> None:
    s = parse_schedule("daily at 14:00")
    now = datetime(2026, 3, 15, 10, 0, 0)
    delay = next_run_delay(s, now=now)
    _assert(delay == 4 * 3600.0, f"daily delay 10:00→14:00 = 14400s (got {delay})")


def test_next_run_delay_weekly() -> None:
    s = parse_schedule("every monday")
    # Sunday → Monday at 00:00 = 24h
    now = datetime(2026, 3, 15, 0, 0, 0)  # Sunday
    delay = next_run_delay(s, now=now)
    _assert(delay == 86400.0, f"weekly Sunday→Monday = 86400s (got {delay})")


# ── 10. ParsedHunt @schedule: integration ────────────────────────────────────

def test_parse_hunt_file_with_schedule() -> None:
    content = (
        "@context: Health check\n"
        "@title: Monitor\n"
        "@schedule: every 5 minutes\n"
        "\n"
        "STEP 1: Check site\n"
        "    NAVIGATE to https://example.com\n"
        "    VERIFY that 'Welcome' is present\n"
        "    DONE.\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False) as f:
        f.write(content)
        f.flush()
        path = f.name
    try:
        parsed = parse_hunt_file(path)
        _assert(parsed.schedule == "every 5 minutes", f"schedule parsed (got {parsed.schedule!r})")
        _assert(parsed.context == "Health check", "context still parsed")
        _assert(parsed.title == "Monitor", "title still parsed")
        _assert("NAVIGATE" in parsed.mission, "mission lines present")
    finally:
        os.unlink(path)


def test_parse_hunt_file_no_schedule() -> None:
    content = (
        "@context: Normal test\n"
        "@title: Test\n"
        "\n"
        "STEP 1: Do stuff\n"
        "    NAVIGATE to https://example.com\n"
        "    DONE.\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False) as f:
        f.write(content)
        f.flush()
        path = f.name
    try:
        parsed = parse_hunt_file(path)
        _assert(parsed.schedule == "", f"no schedule → empty string (got {parsed.schedule!r})")
    finally:
        os.unlink(path)


def test_parse_hunt_file_schedule_with_tags_and_vars() -> None:
    content = (
        "@context: Combined\n"
        "@title: Combo\n"
        "@tags: smoke, monitor\n"
        "@var: {url} = https://example.com\n"
        "@schedule: daily at 09:00\n"
        "\n"
        "STEP 1: Check\n"
        "    NAVIGATE to {url}\n"
        "    DONE.\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".hunt", delete=False) as f:
        f.write(content)
        f.flush()
        path = f.name
    try:
        parsed = parse_hunt_file(path)
        _assert(parsed.schedule == "daily at 09:00", "schedule with tags/vars")
        _assert(parsed.tags == ["smoke", "monitor"], "tags preserved")
        _assert(parsed.parsed_vars.get("url") == "https://example.com", "vars preserved")
    finally:
        os.unlink(path)


# ── 11. Schedule dataclass frozen ────────────────────────────────────────────

def test_schedule_frozen() -> None:
    s = parse_schedule("every 5 minutes")
    try:
        s.interval_seconds = 999  # type: ignore[misc]
        _assert(False, "Schedule should be frozen")
    except (AttributeError, TypeError):
        _assert(True, "Schedule is frozen")


# ── 12. All weekday names parse ──────────────────────────────────────────────

def test_all_weekdays() -> None:
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(days):
        s = parse_schedule(f"every {day}")
        _assert(s.weekly is not None and s.weekly[0] == i, f"every {day} → weekday {i}")


# ── Suite runner ─────────────────────────────────────────────────────────────

async def run_suite() -> tuple[int, int]:
    global _PASS, _FAIL
    _PASS = _FAIL = 0

    print("\n🧪 Scheduler Test Suite")
    print("=" * 50)

    print("\n  1. parse_schedule — interval expressions")
    test_parse_every_n_minutes()
    test_parse_every_n_seconds()
    test_parse_every_n_hours()
    test_parse_every_unit_shorthand()
    test_parse_every_1_minute()

    print("\n  2. parse_schedule — daily expressions")
    test_parse_daily_at()
    test_parse_daily_at_afternoon()

    print("\n  3. parse_schedule — weekly expressions")
    test_parse_every_monday()
    test_parse_every_friday_at()
    test_parse_every_sunday()
    test_parse_every_wednesday_at()

    print("\n  4. parse_schedule — case insensitivity")
    test_parse_case_insensitive()

    print("\n  5. parse_schedule — error cases")
    test_parse_empty()
    test_parse_unknown_expression()
    test_parse_invalid_time()
    test_parse_invalid_weekly_time()

    print("\n  6. next_run_delay — intervals")
    test_next_run_delay_interval()

    print("\n  7. _seconds_until_time — daily math")
    test_seconds_until_time_future_today()
    test_seconds_until_time_past_today()
    test_seconds_until_time_exact_now()

    print("\n  8. _seconds_until_weekday — weekly math")
    test_seconds_until_weekday_same_day_future()
    test_seconds_until_weekday_same_day_past()
    test_seconds_until_weekday_different_day()

    print("\n  9. next_run_delay — daily & weekly")
    test_next_run_delay_daily()
    test_next_run_delay_weekly()

    print("\n  10. ParsedHunt @schedule: integration")
    test_parse_hunt_file_with_schedule()
    test_parse_hunt_file_no_schedule()
    test_parse_hunt_file_schedule_with_tags_and_vars()

    print("\n  11. Schedule dataclass frozen")
    test_schedule_frozen()

    print("\n  12. All weekday names")
    test_all_weekdays()

    total = _PASS + _FAIL
    print(f"\n{'='*50}")
    if _FAIL == 0:
        print(f"SCORE: {_PASS}/{total} — FLAWLESS VICTORY 🏆")
    else:
        print(f"SCORE: {_PASS}/{total} — {_FAIL} FAILED 💀")
    print(f"{'='*50}")
    return _PASS, _FAIL


if __name__ == "__main__":
    asyncio.run(run_suite())
