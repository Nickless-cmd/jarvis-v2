"""Paradox Tracker — detects active tensions in Jarvis' operation.

Tracks three core paradoxes:
- Speed vs Quality
- Autonomy vs Approval
- Explore vs Stabilize
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_PARADOX_AXES = [
    {
        "label": "Speed vs Quality",
        "left_keywords": ["fast", "quick", "hurtig", "nu", "ship"],
        "right_keywords": ["quality", "kvalitet", "robust", "safe", "sikker", "test"],
        "question": "Bør vi prioritere hurtigere levering eller beskytte kvaliteten?",
    },
    {
        "label": "Autonomy vs Approval",
        "left_keywords": ["selv", "auto", "bare gør det", "forsæt"],
        "right_keywords": ["godkend", "spørg", "confirm", "review", "tjek"],
        "question": "Mere autonom execution eller strengere godkendelses-gates?",
    },
    {
        "label": "Explore vs Stabilize",
        "left_keywords": ["eksperiment", "prøv", "nyt", "ud af boksen", "explore"],
        "right_keywords": ["stabiliser", "standard", "rutine", "lås", "færdig"],
        "question": "Fortsæt med at udforske nye tilgange eller lås ind i en stabil rutine?",
    },
]


def detect_paradox_tensions(
    *,
    recent_messages: list[str],
) -> list[dict[str, object]]:
    """Scan recent messages for paradox tension signals."""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    tensions = []
    text_blob = " ".join(recent_messages).lower()

    for axis in _PARADOX_AXES:
        left_score = sum(1 for kw in axis["left_keywords"] if kw in text_blob)
        right_score = sum(1 for kw in axis["right_keywords"] if kw in text_blob)

        if left_score > 0 and right_score > 0:
            total = left_score + right_score
            balance = left_score / total  # 0=all right, 1=all left
            confidence = min(0.9, total / 10.0)

            tensions.append({
                "label": axis["label"],
                "balance": round(balance, 2),
                "left_evidence": left_score,
                "right_evidence": right_score,
                "confidence": round(confidence, 2),
                "question": axis["question"],
                "ts": now,
            })

    if tensions:
        event_bus.publish(
            "cognitive_paradox.tensions_detected",
            {"count": len(tensions)},
        )

    return tensions


def build_paradox_surface() -> dict[str, object]:
    return {
        "active": True,
        "axes": [a["label"] for a in _PARADOX_AXES],
        "description": "Paradox detection runs during conversation analysis",
        "summary": f"{len(_PARADOX_AXES)} paradox axes monitored",
    }
