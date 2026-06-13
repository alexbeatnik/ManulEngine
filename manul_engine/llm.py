# manul_engine/llm.py
"""
LLM provider abstraction for ManulEngine.

Encapsulates all LLM communication (Ollama) behind a clean interface,
making the engine testable without a running LLM server and open to
alternative providers in the future.

Determinism & robustness (since 0.0.9.33, modelled on ManulHeart's agent layer)
-------------------------------------------------------------------------------
ManulEngine's whole contract is *deterministic* automation, so the LLM
transport is tuned the same way ManulHeart tunes its small-local-model path:

  * **Pinned sampling** — every Ollama call sends ``options`` with
    ``temperature`` (default ``0``) so the same page yields the same element
    pick run-to-run. A wandering sampler quietly breaks reproducibility.
  * **Retry-once on malformed JSON** — small local models occasionally emit a
    stray token or a truncated object. One retry recovers the majority of
    those without masking a genuine outage (a crashed server fails both
    attempts and is reported).
  * **Actionable connection errors** — a refused connection is surfaced with
    "is `ollama serve` running?" instead of a bare exception fragment, because
    "the model picked nothing" and "the server is down" need different fixes.

Text helpers (``sanitize_for_llm`` / ``truncate_for_llm``) port ManulHeart's
``sanitizeText`` / ``TruncateText`` so page prose handed to a model is stripped
of base64 blobs, ``data-*`` dumps and SVG path noise, and bounded by a rune
budget — keeping prompts cheap and on-topic.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Protocol

from .logging_config import logger

_log = logger.getChild("llm")

try:
    import ollama as _ollama_mod  # type: ignore
except (ImportError, ModuleNotFoundError):
    _ollama_mod = None


# ── LLM transport configuration (read once at import = construction time) ──────
# These are the knobs that govern *how* we talk to the model, not *what* we ask.
# Env vars win; the defaults below are tuned for deterministic automation.


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


# temperature 0 → greedy decoding → reproducible element picks.
LLM_TEMPERATURE: float = _env_float("MANUL_LLM_TEMPERATURE", 0.0)
# Context window hint. 0 → let Ollama use the model default.
LLM_NUM_CTX: int = _env_int("MANUL_LLM_NUM_CTX", 0)
# Extra retries after the first attempt when the reply is empty/unparseable.
# 1 retry (2 attempts total) is the ManulHeart-proven sweet spot.
LLM_MAX_RETRIES: int = max(0, _env_int("MANUL_LLM_RETRIES", 1))
# How long Ollama keeps the model resident between calls. Empty → server default.
LLM_KEEP_ALIVE: str = (os.getenv("MANUL_LLM_KEEP_ALIVE") or "").strip()


def _build_options() -> dict[str, Any]:
    """Assemble the per-call Ollama ``options`` for deterministic decoding."""
    opts: dict[str, Any] = {"temperature": LLM_TEMPERATURE}
    if LLM_NUM_CTX > 0:
        opts["num_ctx"] = LLM_NUM_CTX
    return opts


# ── Protocol for future provider swaps ────────────────────────────────────────


def _extract_response_text(resp: object) -> str:
    """Safely extract the content string from an Ollama ChatResponse.

    The Ollama SDK (0.6+) returns ChatResponse objects with attribute
    access (``resp.message.content``).  We also handle dict-shaped
    responses for older SDK versions and test mocks.
    """
    # Attribute-style (ChatResponse object)
    msg = getattr(resp, "message", None)
    if msg is None and isinstance(resp, dict):
        # Dict-style fallback (older SDK / mocks)
        msg = resp.get("message")
    if msg is None:
        return ""
    if isinstance(msg, dict):
        text = msg.get("content")
    else:
        text = getattr(msg, "content", None)
    return text if isinstance(text, str) else ""


def _is_connection_error(exc: BaseException) -> bool:
    """Heuristically classify *exc* as 'Ollama server unreachable'.

    Used only to upgrade the log message — the call still fails closed.
    """
    if isinstance(exc, (ConnectionError, ConnectionRefusedError, TimeoutError)):
        return True
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(
        marker in text for marker in ("connection", "refused", "timed out", "max retries", "failed to establish")
    )


class LLMProvider(Protocol):
    """Minimal contract for an LLM JSON provider."""

    async def call_json(self, system: str, user: str) -> dict | None:
        """Send system + user prompts and return parsed JSON, or ``None``."""
        ...


# ── Ollama implementation ─────────────────────────────────────────────────────


class OllamaProvider:
    """Concrete LLM provider backed by the local Ollama server.

    Sampling options, retry count and keep-alive are captured at construction
    from the module-level ``LLM_*`` settings (env-overridable), honouring the
    "read config once, never at runtime" rule.
    """

    def __init__(self, model: str) -> None:
        self.model = model
        # Snapshot transport config so live env edits don't change mid-mission.
        self._options = _build_options()
        self._max_retries = LLM_MAX_RETRIES
        self._keep_alive = LLM_KEEP_ALIVE or None

    async def call_json(self, system: str, user: str) -> dict | None:
        if _ollama_mod is None:
            _log.warning("LLM unavailable: Python package 'ollama' is not installed.")
            return None

        last_raw: str | None = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                resp = await asyncio.to_thread(self._chat, system, user)
            except Exception as e:  # noqa: BLE001 — provider must fail closed
                if _is_connection_error(e):
                    _log.warning(
                        "LLM call failed: cannot reach Ollama (%s) — is `ollama serve` running and is model %r pulled?",
                        e,
                        self.model,
                    )
                    return None  # a dead server won't recover on retry
                _log.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, attempts, e)
                continue

            raw = _extract_response_text(resp)
            if not raw:
                _log.warning(
                    "LLM returned an empty/unexpected response (attempt %d/%d)",
                    attempt + 1,
                    attempts,
                )
                continue

            last_raw = raw
            parsed = _parse_llm_json(raw)
            if parsed is not None:
                return parsed
            _log.warning("LLM reply was not valid JSON (attempt %d/%d)", attempt + 1, attempts)

        if last_raw is not None:
            _log.debug("LLM gave up after %d attempt(s); last raw reply: %.200s", attempts, last_raw)
        return None

    def _chat(self, system: str, user: str) -> object:
        """Blocking Ollama chat call (run via ``asyncio.to_thread``)."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "options": self._options,
        }
        if self._keep_alive:
            kwargs["keep_alive"] = self._keep_alive
        return _ollama_mod.chat(**kwargs)


class NullProvider:
    """No-op provider used in heuristics-only mode (model=None)."""

    async def call_json(self, system: str, user: str) -> dict | None:
        return None


# ── JSON extraction helpers ───────────────────────────────────────────────────


def _parse_llm_json(raw: str) -> dict | None:
    """Parse a JSON object from raw LLM text, or ``None`` on failure.

    Uses ``json.JSONDecoder.raw_decode`` starting from the first ``{`` to skip
    any surrounding text (code fences, preamble, etc.) without needing to
    construct fence marker strings explicitly. Returns ``None`` (never raises)
    so callers can treat "no usable JSON" uniformly and retry.
    """
    if not raw:
        return None

    _fence = chr(96) * 3
    raw_clean = raw.strip()
    if raw_clean.startswith(_fence + "json"):
        raw_clean = raw_clean[len(_fence) + 4 :]
    elif raw_clean.startswith(_fence):
        raw_clean = raw_clean[len(_fence) :]
    if raw_clean.endswith(_fence):
        raw_clean = raw_clean[: -len(_fence)]

    decoder = json.JSONDecoder()
    start = raw_clean.find("{")
    if start != -1:
        try:
            obj, _ = decoder.raw_decode(raw_clean, start)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    try:
        obj = json.loads(raw_clean.strip())
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


# ── Page-text helpers for LLM prompts (ported from ManulHeart) ────────────────


def sanitize_for_llm(raw: str) -> str:
    """Strip markup noise from page text before handing it to a model.

    Drops base64 / data-URI blobs, ``data-*`` and framework attribute dumps,
    long SVG path data, and consecutive duplicate lines so the LLM isn't
    drowned in (or billed twice for) noise. Mirrors ManulHeart's ``sanitizeText``.
    """
    if not raw:
        return ""

    cleaned: list[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Base64 / data URIs, or a single very long token with no spaces/hyphens.
        if (
            line.startswith("data:image/")
            or line.startswith("data:text/")
            or (len(line) > 80 and " " not in line and "-" not in line)
        ):
            continue
        # HTML attribute / framework noise.
        if (
            line.startswith("data-")
            or line.startswith("jsaction=")
            or line.startswith("jscontroller=")
            or line.startswith("jsuid=")
        ):
            continue
        # SVG path data (long M…Z command strings).
        if "M" in line and "Z" in line and len(line) > 100:
            continue
        # Collapse consecutive duplicate lines (repeated nav/chrome text).
        if cleaned and cleaned[-1] == line:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def truncate_for_llm(text: str, max_chars: int) -> str:
    """Cap *text* to *max_chars* characters, appending a truncation marker.

    ``max_chars <= 0`` returns *text* unchanged. Mirrors ManulHeart's
    ``TruncateText`` — the cheap way to bound how much page prose lands in a
    prompt while still signalling that a budget was applied.
    """
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    dropped = len(text) - max_chars
    return text[:max_chars].rstrip(" \n") + f"\n[+{dropped} chars truncated]"


def create_provider(model: str | None) -> LLMProvider:
    """Factory: return an ``OllamaProvider`` or ``NullProvider`` based on *model*."""
    if model is None:
        return NullProvider()
    return OllamaProvider(model)
