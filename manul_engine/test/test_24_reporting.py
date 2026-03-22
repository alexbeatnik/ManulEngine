# manul_engine/test/test_24_reporting.py
"""
Unit-test suite for the reporting data models, CLI flag parsing,
retry logic, and screenshot mode configuration.

No network or live browser required.  All tests run against synthetic
data and in-memory state only.

Tests:
  1. Data Models — StepResult, MissionResult, RunSummary construction and defaults.
  2. MissionResult truthiness — pass/flaky/fail boolean semantics.
  3. Config defaults — prompts.py exposes RETRIES, SCREENSHOT, HTML_REPORT.
  4. CLI flag extraction — parse_hunt_file remains backward-compatible,
     _run_hunt_file signature accepts screenshot_mode.

Entry point ``run_suite()`` is picked up by the dev test runner
(``python manul.py test``) and must remain async.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from manul_engine.reporting import (
    StepResult,
    MissionResult,
    RunSummary,
    BlockResult,
    load_report_state,
    save_report_state,
    merge_report_summaries,
)

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


# ── Section 1: StepResult defaults ────────────────────────────────────────────

def _test_step_result() -> None:
    print("\n  ── StepResult data model ──────────────────────────────────")

    sr = StepResult(index=1, text="NAVIGATE to https://example.com")
    _assert(sr.index == 1, "StepResult.index default")
    _assert(sr.text == "NAVIGATE to https://example.com", "StepResult.text stored")
    _assert(sr.status == "pass", "StepResult.status defaults to 'pass'")
    _assert(sr.duration_ms == 0.0, "StepResult.duration_ms defaults to 0.0")
    _assert(sr.error is None, "StepResult.error defaults to None")
    _assert(sr.screenshot is None, "StepResult.screenshot defaults to None")

    sr_fail = StepResult(index=3, text="Click 'Login'", status="fail", error="Timeout", screenshot="abc123")
    _assert(sr_fail.status == "fail", "StepResult with explicit fail status")
    _assert(sr_fail.error == "Timeout", "StepResult.error stores message")
    _assert(sr_fail.screenshot == "abc123", "StepResult.screenshot stores base64")


# ── Section 2: MissionResult defaults + truthiness ────────────────────────────

def _test_mission_result() -> None:
    print("\n  ── MissionResult data model + truthiness ─────────────────")

    mr_pass = MissionResult(file="/tmp/test.hunt", name="test.hunt")
    _assert(mr_pass.status == "pass", "MissionResult.status defaults to 'pass'")
    _assert(mr_pass.attempts == 1, "MissionResult.attempts defaults to 1")
    _assert(mr_pass.duration_ms == 0.0, "MissionResult.duration_ms defaults to 0.0")
    _assert(mr_pass.error is None, "MissionResult.error defaults to None")
    _assert(mr_pass.steps == [], "MissionResult.steps defaults to empty list")
    _assert(mr_pass.blocks == [], "MissionResult.blocks defaults to empty list")
    _assert(bool(mr_pass) is True, "MissionResult(status='pass') is truthy")

    mr_fail = MissionResult(file="/tmp/fail.hunt", name="fail.hunt", status="fail", error="Step 3 timeout")
    _assert(bool(mr_fail) is False, "MissionResult(status='fail') is falsy")

    mr_broken = MissionResult(file="/tmp/broken.hunt", name="broken.hunt", status="broken", error="SETUP failed")
    _assert(bool(mr_broken) is False, "MissionResult(status='broken') is falsy")

    mr_flaky = MissionResult(file="/tmp/flaky.hunt", name="flaky.hunt", status="flaky", attempts=3)
    _assert(bool(mr_flaky) is True, "MissionResult(status='flaky') is truthy")
    _assert(mr_flaky.attempts == 3, "MissionResult.attempts stores retry count")

    # Step list is not shared between instances (mutable default safety)
    mr_a = MissionResult(file="a", name="a")
    mr_b = MissionResult(file="b", name="b")
    mr_a.steps.append(StepResult(index=1, text="test"))
    _assert(len(mr_b.steps) == 0, "MissionResult step lists are independent (no shared mutable default)")


def _test_block_result() -> None:
    print("\n  ── BlockResult data model ─────────────────────────────────")

    br = BlockResult(name="STEP 1: Login")
    _assert(br.name == "STEP 1: Login", "BlockResult.name stored")
    _assert(br.status == "pass", "BlockResult.status defaults to 'pass'")
    _assert(br.duration_ms == 0.0, "BlockResult.duration_ms defaults to 0.0")
    _assert(br.error is None, "BlockResult.error defaults to None")
    _assert(br.actions == [], "BlockResult.actions defaults to empty list")

    br_fail = BlockResult(
        name="STEP 2: Verify",
        status="fail",
        error="Verification failed",
        actions=[StepResult(index=3, text="VERIFY that 'Dashboard' is present", status="fail")],
    )
    _assert(br_fail.status == "fail", "BlockResult explicit fail status stored")
    _assert(br_fail.actions[0].status == "fail", "BlockResult actions preserve child step status")


# ── Section 3: RunSummary defaults ────────────────────────────────────────────

def _test_run_summary() -> None:
    print("\n  ── RunSummary data model ──────────────────────────────────")

    rs = RunSummary()
    _assert(bool(rs.session_id), "RunSummary.session_id defaults to non-empty string")
    _assert(rs.invocation_count == 1, "RunSummary.invocation_count defaults to 1")
    _assert(rs.started_at == "", "RunSummary.started_at defaults to empty string")
    _assert(rs.total == 0, "RunSummary.total defaults to 0")
    _assert(rs.passed == 0, "RunSummary.passed defaults to 0")
    _assert(rs.failed == 0, "RunSummary.failed defaults to 0")
    _assert(rs.broken == 0, "RunSummary.broken defaults to 0")
    _assert(rs.flaky == 0, "RunSummary.flaky defaults to 0")
    _assert(rs.missions == [], "RunSummary.missions defaults to empty list")

    # Populate a summary
    rs.missions.append(MissionResult(file="a.hunt", name="a.hunt", status="pass"))
    rs.missions.append(MissionResult(file="b.hunt", name="b.hunt", status="flaky", attempts=2))
    rs.missions.append(MissionResult(file="c.hunt", name="c.hunt", status="fail"))
    rs.total = 3
    rs.passed = 1
    rs.failed = 1
    rs.flaky = 1
    _assert(len(rs.missions) == 3, "RunSummary.missions accumulation")
    _assert(rs.missions[1].status == "flaky", "RunSummary flaky mission status")

    # Mission lists are not shared between instances
    rs2 = RunSummary()
    _assert(len(rs2.missions) == 0, "RunSummary mission lists are independent (no shared mutable default)")


def _test_report_state_merge() -> None:
    print("\n  ── Report state merge across invocations ─────────────────")
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        first = RunSummary(
            started_at="2026-03-22T10:00:00+00:00",
            ended_at="2026-03-22T10:00:05+00:00",
            missions=[MissionResult(file="/tmp/a.hunt", name="a.hunt", status="pass", duration_ms=1000)],
        )
        second = RunSummary(
            started_at="2026-03-22T10:00:06+00:00",
            ended_at="2026-03-22T10:00:10+00:00",
            missions=[MissionResult(file="/tmp/b.hunt", name="b.hunt", status="fail", duration_ms=2000)],
        )
        save_report_state(first)
        loaded = load_report_state(max_age_seconds=999999)
        merged = merge_report_summaries(loaded, second)
        _assert(loaded is not None, "load_report_state returns persisted summary")
        _assert(len(merged.missions) == 2, "merge_report_summaries accumulates distinct missions")
        _assert(merged.session_id == first.session_id, "merged summary preserves original session_id")
        _assert(merged.invocation_count == 2, "merged summary tracks merged invocation count")
        _assert(merged.failed == 1, "merged summary recomputes failed count")
        _assert(merged.broken == 0, "merged summary recomputes broken count")
        _assert(merged.passed == 1, "merged summary recomputes passed count")

        replacement = RunSummary(
            started_at="2026-03-22T10:00:11+00:00",
            ended_at="2026-03-22T10:00:14+00:00",
            missions=[MissionResult(file="/tmp/a.hunt", name="a.hunt", status="warning", duration_ms=1500)],
        )
        replaced = merge_report_summaries(merged, replacement)
        statuses = {m.file: m.status for m in replaced.missions}
        _assert(len(replaced.missions) == 2, "merge replaces duplicate file instead of duplicating it")
        _assert(replaced.invocation_count == 3, "replacement merge still increments invocation count")
        _assert(statuses.get("/tmp/a.hunt") == "warning", "later mission replaces prior mission for same file")
        os.chdir(old_cwd)


# ── Section 4: Config defaults (prompts.py) ──────────────────────────────────

def _test_config_defaults() -> None:
    print("\n  ── Config defaults (prompts.py) ──────────────────────────")

    from manul_engine import prompts

    _assert(hasattr(prompts, "RETRIES"), "prompts.RETRIES attribute exists")
    _assert(isinstance(prompts.RETRIES, int), "prompts.RETRIES is int",
            f"type={type(prompts.RETRIES).__name__}")
    _assert(prompts.RETRIES >= 0, "prompts.RETRIES >= 0")

    _assert(hasattr(prompts, "SCREENSHOT"), "prompts.SCREENSHOT attribute exists")
    _assert(prompts.SCREENSHOT in ("on-fail", "always", "none"),
            "prompts.SCREENSHOT is valid mode",
            f"value={prompts.SCREENSHOT!r}")

    _assert(hasattr(prompts, "HTML_REPORT"), "prompts.HTML_REPORT attribute exists")
    _assert(isinstance(prompts.HTML_REPORT, bool), "prompts.HTML_REPORT is bool",
            f"type={type(prompts.HTML_REPORT).__name__}")


# ── Section 5: run_mission signature accepts screenshot_mode ──────────────────

def _test_run_mission_signature() -> None:
    print("\n  ── run_mission signature ─────────────────────────────────")

    from manul_engine.core import ManulEngine
    sig = inspect.signature(ManulEngine.run_mission)
    params = list(sig.parameters.keys())
    _assert("screenshot_mode" in params,
            "run_mission accepts 'screenshot_mode' parameter",
            f"params={params}")
    # Check default value
    default = sig.parameters["screenshot_mode"].default
    _assert(default == "none",
            "screenshot_mode defaults to 'none'",
            f"default={default!r}")

    # Return type annotation should be MissionResult
    ret_annotation = sig.return_annotation
    # may be string or class depending on from __future__ annotations
    _assert("MissionResult" in str(ret_annotation),
            "run_mission return annotation mentions MissionResult",
            f"annotation={ret_annotation!r}")


# ── Section 6: _run_hunt_file signature accepts screenshot_mode ───────────────

def _test_run_hunt_file_signature() -> None:
    print("\n  ── _run_hunt_file signature ──────────────────────────────")

    from manul_engine.cli import _run_hunt_file
    sig = inspect.signature(_run_hunt_file)
    params = list(sig.parameters.keys())
    _assert("screenshot_mode" in params,
            "_run_hunt_file accepts 'screenshot_mode' parameter",
            f"params={params}")
    default = sig.parameters["screenshot_mode"].default
    _assert(default == "none",
            "_run_hunt_file screenshot_mode defaults to 'none'",
            f"default={default!r}")


# ── Section 7: CLI _USAGE includes new flags ─────────────────────────────────

def _test_cli_usage() -> None:
    print("\n  ── CLI _USAGE string ─────────────────────────────────────")

    from manul_engine.cli import _USAGE
    _assert("--retries" in _USAGE, "_USAGE mentions --retries flag")
    _assert("--screenshot" in _USAGE, "_USAGE mentions --screenshot flag")
    _assert("--html-report" in _USAGE, "_USAGE mentions --html-report flag")
    _assert("on-fail" in _USAGE, "_USAGE mentions on-fail screenshot mode")
    _assert("flaky" in _USAGE.lower(), "_USAGE mentions flaky concept")


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_suite() -> bool:
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    print("\n" + "━" * 56)
    print("  test_24_reporting — data models, CLI flags, retries")
    print("━" * 56)

    _test_step_result()
    _test_mission_result()
    _test_block_result()
    _test_run_summary()
    _test_report_state_merge()
    _test_config_defaults()
    _test_run_mission_signature()
    _test_run_hunt_file_signature()
    _test_cli_usage()

    total = _PASS + _FAIL
    print(f"\n📊 SCORE: {_PASS}/{total}")
    return _FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(run_suite())
    sys.exit(0 if ok else 1)
