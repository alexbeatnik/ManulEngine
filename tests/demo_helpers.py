"""
demo_helpers.py — ManulEngine [SETUP] / [TEARDOWN] demo helper.

These functions are called from demo_login.hunt via:

    CALL PYTHON demo_helpers.inject_test_session
    CALL PYTHON demo_helpers.clean_database

Keep them synchronous — ManulEngine hooks reject async callables.
"""

import time


def inject_test_session() -> None:
    """Seed the test database with a fresh admin session before the UI run."""
    print("  [demo_helpers] Mocking DB injection — seeding test session...")
    time.sleep(1)
    print("  [demo_helpers] ✔ Test session ready (user: test@manul.com, role: admin)")


def clean_database() -> None:
    """Remove all test data created during the run."""
    print("  [demo_helpers] Mocking DB cleanup — removing test session data...")
    time.sleep(1)
    print("  [demo_helpers] ✔ Database clean — all test artefacts removed")
