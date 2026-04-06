# manul_engine/logging_config.py
"""
Centralized logging configuration for ManulEngine.

Provides a package-level logger hierarchy under ``manul_engine``.
All engine modules should use::

    from .logging_config import logger

The logger is configured to write to stderr (not stdout) so it
does not interfere with the structured stdout output that tests
and the VS Code extension depend on.

Log levels:
    DEBUG   — internal diagnostics (frame routing, cache lookups)
    INFO    — noteworthy events (LLM calls, cache hits, self-healing)
    WARNING — recoverable problems (stale cache, frame detach)
    ERROR   — action failures, config issues
"""

import logging
import os

_LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

_env_level = os.environ.get("MANUL_LOG_LEVEL", "warning").strip().lower()
_level = _LOG_LEVEL_MAP.get(_env_level, logging.WARNING)

logger = logging.getLogger("manul_engine")
logger.setLevel(_level)
logger.propagate = False

if not logger.handlers:
    _handler = logging.StreamHandler()  # stderr by default
    _handler.setLevel(_level)
    _formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
