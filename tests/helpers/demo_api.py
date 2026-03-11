"""Demo helper for tests/demo_variables.hunt — returns a synthetic OTP.

Usage in a hunt file:
    5. CALL PYTHON helpers.demo_api.get_demo_otp into {otp}
"""


def get_demo_otp() -> str:
    """Return a fixed demo OTP string for demonstration purposes."""
    return "481516"
