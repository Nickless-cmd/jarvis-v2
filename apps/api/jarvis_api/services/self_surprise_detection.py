"""Self-Surprise Detection — "Huh, det havde jeg ikke forventet af mig selv."

Expected vs actual → discrepancy = surprise.
"""
from __future__ import annotations
from uuid import uuid4
from core.runtime.db import insert_cognitive_self_surprise, list_cognitive_self_surprises
from core.eventbus.bus import event_bus


def detect_self_surprise(
    *, expected_confidence: float, actual_outcome: str,
    domain: str = "", run_id: str = "",
) -> dict[str, object] | None:
    expected_success = expected_confidence > 0.6
    actual_success = actual_outcome in ("completed", "success")

    if expected_success == actual_success:
        return None  # No surprise

    if not expected_success and actual_success:
        surprise_type = "positive"
        narrative = f"Overraskende succes i {domain or 'ukendt domæne'} — forventede at fejle men klarede det."
    else:
        surprise_type = "negative"
        narrative = f"Uventet fejl i {domain or 'ukendt domæne'} — var sikker men tog fejl."

    surprise_id = f"surp-{uuid4().hex[:8]}"
    result = insert_cognitive_self_surprise(
        surprise_id=surprise_id, surprise_type=surprise_type,
        narrative=narrative, expected_confidence=expected_confidence,
        actual_outcome=actual_outcome, domain=domain, run_id=run_id,
    )
    event_bus.publish("cognitive_state.self_surprise",
                     {"type": surprise_type, "domain": domain})
    return result


def build_self_surprise_surface() -> dict[str, object]:
    items = list_cognitive_self_surprises(limit=10)
    positive = sum(1 for i in items if i.get("surprise_type") == "positive")
    negative = len(items) - positive
    return {"active": bool(items), "items": items,
            "positive_count": positive, "negative_count": negative,
            "summary": f"{len(items)} surprises ({positive}+, {negative}-)" if items else "No surprises yet"}
