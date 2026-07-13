"""Robustness envelope builder + plausibility guard for the dispatch-redesign.

A dispatch envelope is a small, fixed-shape dict that captures the outcome of
a single dispatch: its status plus token/cost/duration/tool accounting and the
result payload. `build_envelope` normalises types and never raises;
`validate_envelope` returns human-readable plausibility warnings (never raises).

Pure, dependency-light. Imports only the status taxonomy from dispatch_status.
"""

from __future__ import annotations

from core.services.dispatch_status import DispatchStatus


def _to_int(value: object) -> int:
    """Coerce to int; on any failure return 0."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        try:
            return int(float(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0


def _to_float(value: object) -> float:
    """Coerce to float; on any failure return 0.0."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def build_envelope(
    *,
    status,
    tokens_in=0,
    tokens_out=0,
    cost_usd=0.0,
    duration_ms=0,
    tool_calls=0,
    result=None,
) -> dict:
    """Build a fixed 7-key dispatch envelope with coerced types.

    Never raises: coercion failures fall back to 0 / 0.0.
    """
    return {
        "status": str(status),
        "tokens_in": _to_int(tokens_in),
        "tokens_out": _to_int(tokens_out),
        "cost_usd": _to_float(cost_usd),
        "duration_ms": _to_int(duration_ms),
        "tool_calls": _to_int(tool_calls),
        "result": result,
    }


def validate_envelope(env: dict) -> list[str]:
    """Return plausibility warnings for an envelope. Empty list = clean.

    Never raises. Checks:
      - completed but tokens_out == 0 -> hollow success
      - unknown status
      - negative tool_calls
    """
    warns: list[str] = []
    try:
        status = str(env.get("status"))
        tokens_out = _to_int(env.get("tokens_out", 0))
        tool_calls = _to_int(env.get("tool_calls", 0))

        if status == DispatchStatus.COMPLETED and tokens_out == 0:
            warns.append("completed with tokens_out==0 (suspicious hollow success)")

        if status not in DispatchStatus.all():
            warns.append(f"unknown status: {status}")

        if tool_calls < 0:
            warns.append("negative tool_calls")
    except Exception:  # pragma: no cover - guard: validation must never raise
        return warns
    return warns
