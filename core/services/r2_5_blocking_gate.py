"""R2.5 — conditional blocking gate.

R2 (verification_gate) is observational. R2.5 promotes it to advisory-
plus-blocking when telemetry shows the model is actively ignoring
warnings AND we're in a deep-reasoning context where unverified
mutations carry high risk.

This module provides one function:

    should_block_for_verification(reasoning_tier) -> dict | None

It returns a block-instruction dict when ALL of the following hold:

1. Reasoning tier is 'deep' or 'reasoning' (not 'fast')
2. There are >= _MIN_FAILED_VERIFIES failed verifications in the last
   10 minutes, OR >= _MIN_UNVERIFIED unverified mutations
3. The R2 heed_rate over the last 24h is below _HEED_RATE_THRESHOLD
   (i.e. the model has a track record of ignoring warnings)
4. We haven't blocked too recently (don't ping-pong; cooldown)

The gate is INJECTED INTO THE PROMPT as a high-priority awareness
section saying: "Du bliver bedt om at stoppe og verificere. Kør
verify_* før du fortsætter." This relies on the model honoring the
instruction. Without further signal that needs more enforcement,
soft blocking is enough — when telemetry shows even this is ignored,
we can escalate to actual output gating (refuse to stream further
deltas until a verify_* completes), but that's a separate decision.

Returns None when no block is needed.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_MIN_FAILED_VERIFIES = 1
_MIN_UNVERIFIED = 5
_HEED_RATE_THRESHOLD = 0.4
_BLOCK_COOLDOWN_SECONDS = 60


_last_block_at: datetime | None = None


def _heed_rate_24h() -> float | None:
    try:
        from core.services.verification_gate_telemetry import get_telemetry_summary
        s = get_telemetry_summary(hours=24)
        if s.get("surfaced_total", 0) < 5:
            # Not enough data — give the model the benefit of the doubt
            return None
        return s.get("heed_rate")
    except Exception:
        return None


def should_block_for_verification(*, reasoning_tier: str) -> dict[str, Any] | None:
    """Decide whether to inject a 'stop and verify' block.

    Returns a dict {reason, suggestions, urgency} when blocking is warranted,
    else None.
    """
    global _last_block_at
    tier = (reasoning_tier or "").strip().lower()
    if tier not in {"deep", "reasoning"}:
        return None

    # Cooldown — don't re-block within a minute of the last block
    now = datetime.now(UTC)
    if _last_block_at is not None and (now - _last_block_at).total_seconds() < _BLOCK_COOLDOWN_SECONDS:
        return None

    try:
        from core.services.verification_gate import evaluate_verification_gate
        gate = evaluate_verification_gate()
    except Exception:
        return None

    failed = int(gate.get("failed_verify_count") or 0)
    unverified = int(gate.get("unverified_count") or 0)
    if failed < _MIN_FAILED_VERIFIES and unverified < _MIN_UNVERIFIED:
        return None

    heed_rate = _heed_rate_24h()
    # Only escalate to block when we have evidence the model ignores warnings.
    # If heed_rate is None (insufficient data) we don't block — soft R2 surfaces.
    if heed_rate is None or heed_rate >= _HEED_RATE_THRESHOLD:
        return None

    suggestions = list(gate.get("suggestions") or [])
    urgency = "high" if failed > 0 else "medium"

    # Mark cooldown
    _last_block_at = now

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("r2_5_gate.blocked", {
            "tier": tier,
            "failed_verify_count": failed,
            "unverified_count": unverified,
            "heed_rate": heed_rate,
            "urgency": urgency,
        })
    except Exception:
        pass

    return {
        "reason": (
            f"R2.5 conditional block: {failed} failed verifies, {unverified} "
            f"unverified mutations, og 24t heed_rate={int(heed_rate*100)}% "
            f"(under {int(_HEED_RATE_THRESHOLD*100)}%-grænsen). Du har en "
            "trackrecord for at ignorere R2-advarsler. STOP og kør verify_* "
            "FØRST denne gang."
        ),
        "suggestions": suggestions,
        "urgency": urgency,
        "tier": tier,
    }


def r2_5_block_section(reasoning_tier: str) -> str | None:
    """Render the block as a high-priority awareness section, or None."""
    block = should_block_for_verification(reasoning_tier=reasoning_tier)
    if not block:
        return None
    lines = ["🛑 R2.5 BLOCK — verifér før du fortsætter:", block["reason"]]
    for s in block.get("suggestions") or []:
        lines.append(f"  - {s}")
    return "\n".join(lines)
