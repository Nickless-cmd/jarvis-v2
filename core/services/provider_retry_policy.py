"""Provider retry policy — exponential backoff for transient failures.

Existing infrastructure:
- provider_circuit_breaker (3 fails / 5min → skip 10min)
- execute_with_role_or_fallback (primary fails → cheap_lane chain)

Missing: retry the SAME provider with backoff before falling through.
For transient errors (rate limit, brief network blip), one retry after
2s often succeeds. Falling immediately to fallback wastes the primary's
intended quality.

This module wraps a callable with: 2s → 4s → 8s exponential backoff,
max 3 retries, only for transient-looking errors.

Stateless — pure function. Caller decides whether to use it.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


_DEFAULT_RETRIES = 3
_DEFAULT_BASE_DELAY = 2.0
_DEFAULT_MAX_DELAY = 16.0


# Errors that look transient — worth retrying
_TRANSIENT_ERROR_PATTERNS: tuple[str, ...] = (
    "timeout", "timed out", "connection reset", "connection refused",
    "rate limit", "rate-limit", "too many requests", "429",
    "502", "503", "504", "service unavailable", "gateway",
    "temporarily unavailable", "try again",
)


_TRANSIENT_EXCEPTION_TYPES: tuple[str, ...] = (
    "TimeoutError", "ConnectionError", "ConnectionResetError",
    "ConnectionRefusedError", "BrokenPipeError",
)


def _is_transient(exc: Exception) -> bool:
    if type(exc).__name__ in _TRANSIENT_EXCEPTION_TYPES:
        return True
    msg = str(exc).lower()
    return any(p in msg for p in _TRANSIENT_ERROR_PATTERNS)


def retry_with_backoff(
    fn: Callable[[], Any],
    *,
    max_retries: int = _DEFAULT_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
    max_delay: float = _DEFAULT_MAX_DELAY,
    only_transient: bool = True,
    label: str = "",
) -> Any:
    """Run fn() with exponential backoff. Re-raises last exception on failure.

    Delays: base, base*2, base*4, ... capped at max_delay.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):  # initial + retries
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if only_transient and not _is_transient(exc):
                # Not a retryable error — fail fast
                raise
            if attempt >= max_retries:
                break
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.info(
                "retry_with_backoff: %s attempt %d failed (%s) — retrying in %.1fs",
                label or "call", attempt + 1, str(exc)[:80], delay,
            )
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish(
                    "runtime.retry_attempted",
                    {"label": label, "attempt": attempt + 1, "delay_s": delay,
                     "error": str(exc)[:160]},
                )
            except Exception:
                pass
            time.sleep(delay)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("retry_with_backoff: no exception captured but loop exited")


def _exec_test_retry(args: dict[str, Any]) -> dict[str, Any]:
    """Manual test handle — verify retry behaviour. Not for production use."""
    fail_count = int(args.get("fail_count") or 0)
    counter = {"n": 0}

    def _fn():
        counter["n"] += 1
        if counter["n"] <= fail_count:
            raise TimeoutError(f"simulated timeout {counter['n']}")
        return {"success_on_attempt": counter["n"]}

    try:
        result = retry_with_backoff(
            _fn,
            max_retries=int(args.get("max_retries") or 3),
            base_delay=float(args.get("base_delay") or 0.1),  # short for testing
            label="test_retry",
        )
        return {"status": "ok", **result, "total_attempts": counter["n"]}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "total_attempts": counter["n"]}


PROVIDER_RETRY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "test_retry_policy",
            "description": (
                "Manual test of retry-with-backoff behaviour. Simulates N "
                "failures before success. For verification only — not used in "
                "production paths."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "fail_count": {"type": "integer"},
                    "max_retries": {"type": "integer"},
                    "base_delay": {"type": "number"},
                },
                "required": [],
            },
        },
    },
]
