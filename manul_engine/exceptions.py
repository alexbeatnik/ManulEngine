"""Structured exception hierarchy for ManulEngine.

All public exceptions inherit from :class:`ManulEngineError` so callers can
catch the base class for blanket handling or use specific subclasses for
fine-grained control.
"""


class ManulEngineError(Exception):
    """Base exception for all ManulEngine errors."""


class ConfigurationError(ManulEngineError, ValueError):
    """Invalid or inconsistent engine configuration."""


class ElementResolutionError(ManulEngineError):
    """Element could not be resolved via heuristics or LLM fallback."""


class HookExecutionError(ManulEngineError):
    """A [SETUP] or [TEARDOWN] hook failed during execution."""


class HuntImportError(ManulEngineError):
    """Raised when an @import: directive cannot be resolved."""


class VerificationError(ManulEngineError):
    """A VERIFY step assertion failed."""


class SessionError(ManulEngineError, RuntimeError):
    """ManulSession lifecycle error (start/close/page access)."""


class ScheduleError(ManulEngineError, ValueError):
    """Invalid @schedule: expression."""


class ConditionalSyntaxError(ManulEngineError, SyntaxError):
    """Invalid if/elif/else conditional block syntax in a .hunt file."""
