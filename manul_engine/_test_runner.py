# manul_engine/_test_runner.py
"""
Internal synthetic DOM test runner (developer tool — not part of the public CLI).

Invoked from the repository dev launcher::

    python manul.py test

Runs all test_*.py suites inside manul_engine/test/ against locally rendered
HTML pages (no real websites, no internet required).

End users of the installed package do not have access to this command.
"""

import importlib
import io
import os
import re
import sys


# Directory that holds test_*.py suites (resolves correctly whether running from
# source or from an installed wheel).
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_TEST_DIR = os.path.join(_PKG_DIR, "test")


class _Tee:
    """Duplicate stdout to a log file."""

    def __init__(self, path: str) -> None:
        self._term = sys.stdout
        self._file = open(path, "w", encoding="utf-8")

    def write(self, msg: str) -> None:
        self._term.write(msg)
        self._file.write(msg)

    def flush(self) -> None:
        self._term.flush()
        self._file.flush()

    def isatty(self) -> bool:
        return False

    @property
    def term(self):
        return self._term

    def close(self) -> None:
        self._file.close()


async def run_tests(log_path: str) -> bool:
    """
    Discover and run all test_*.py suites in manul_engine/test/.

    Returns True if every suite passed, False otherwise.
    Writes a full log to *log_path*.
    """
    # Disable controls cache and dotenv override for deterministic runs.
    os.environ["MANUL_DOTENV_OVERRIDE"] = "False"
    os.environ["MANUL_CONTROLS_CACHE_ENABLED"] = "False"
    try:
        from manul_engine import prompts as _prompts
        _prompts.CONTROLS_CACHE_ENABLED = False
    except Exception:
        pass

    # Ensure UTF-8 output on Windows / misconfigured terminals.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.detach(), encoding="utf-8", errors="replace", line_buffering=True
        )

    tee = _Tee(log_path)
    real_stdout = sys.stdout
    score_lines: list[str] = []

    class _ScoreTee:
        def write(self, msg: str) -> None:
            real_stdout.write(msg)
            tee._file.write(msg)
            for line in msg.splitlines():
                if "SCORE:" in line:
                    score_lines.append(line.strip())

        def flush(self) -> None:
            real_stdout.flush()
            tee._file.flush()

        def isatty(self) -> bool:
            return False

    sys.stdout = _ScoreTee()

    test_files = sorted(
        f[:-3]
        for f in os.listdir(_TEST_DIR)
        if f.startswith("test_") and f.endswith(".py")
    )

    all_ok = True
    suite_results: list[tuple[str, int, int]] = []

    for mod_name in test_files:
        mod = importlib.import_module(f"manul_engine.test.{mod_name}")
        runner = getattr(mod, "run_laboratory", None) or getattr(mod, "run_suite", None)
        if runner is None:
            continue
        before = len(score_lines)
        ok = await runner()
        if not ok:
            all_ok = False
        for sl in score_lines[before:]:
            m = re.search(r"(\d+)/(\d+)", sl)
            if m:
                suite_results.append((mod_name, int(m.group(1)), int(m.group(2))))

    total_passed = sum(p for _, p, _ in suite_results)
    total_tests = sum(t for _, _, t in suite_results)

    print(f"\n\n{'=' * 70}")
    print("🐾 SYNTHETIC DOM LABORATORY SUMMARY")
    print(f"{'=' * 70}")
    for name, p, t in suite_results:
        icon = "✅" if p == t else "❌"
        label = name.replace("test_", "").replace("_", " ").upper()
        print(f"   {icon} {label:<30} {p:>4}/{t}")
    print(f"{'─' * 70}")
    print(f"   {'TOTAL':<30} {total_passed:>4}/{total_tests}")
    if total_passed == total_tests:
        print("\n🏆 ALL TESTS PASSED — THE ENGINE IS UNBREAKABLE!")
    print(f"{'=' * 70}")

    sys.stdout = real_stdout
    tee.close()

    return all_ok
