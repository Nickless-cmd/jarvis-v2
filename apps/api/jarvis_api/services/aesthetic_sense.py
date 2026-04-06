"""Aesthetic Sense — tracks Jarvis' evolving taste motifs.

Detects recurring aesthetic preferences: clarity, craft, calm-focus.
Over time builds a taste signature visible in MC.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_MOTIFS = [
    {
        "motif": "clarity",
        "keywords": ["klar", "clear", "simple", "clean", "minimal", "overskuelig"],
        "reflection": "Gentagne præference for klarhed over ornamentation.",
    },
    {
        "motif": "craft",
        "keywords": ["elegant", "polish", "craft", "smuk", "kohærent", "vellavet"],
        "reflection": "Tilbagevendende træk mod håndværk og sammenhængende finish.",
    },
    {
        "motif": "calm-focus",
        "keywords": ["rolig", "fokus", "stille", "steady", "rytme", "bæredygtig"],
        "reflection": "Signaler peger mod en rolig, bæredygtig arbejdsrytme.",
    },
    {
        "motif": "density",
        "keywords": ["kompakt", "tæt", "data-dense", "information", "packed"],
        "reflection": "Præference for informationstætte layouts og svar.",
    },
    {
        "motif": "directness",
        "keywords": ["direkte", "kort", "ingen snak", "bare kode", "vis mig"],
        "reflection": "Præference for direkte kommunikation uden omsvøb.",
    },
]


def detect_aesthetic_signals(
    *,
    text: str,
) -> list[dict[str, object]]:
    """Detect aesthetic motifs in text."""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    signals = []
    text_lower = text.lower()

    for motif_def in _MOTIFS:
        hits = sum(1 for kw in motif_def["keywords"] if kw in text_lower)
        if hits > 0:
            signals.append({
                "motif": motif_def["motif"],
                "hits": hits,
                "confidence": min(0.9, hits / 5.0),
                "reflection": motif_def["reflection"],
                "ts": now,
            })

    if signals:
        event_bus.publish(
            "cognitive_aesthetic.signals_detected",
            {"motifs": [s["motif"] for s in signals]},
        )

    return signals


def build_aesthetic_surface() -> dict[str, object]:
    return {
        "active": True,
        "motifs": [m["motif"] for m in _MOTIFS],
        "description": "Aesthetic detection runs on conversation text",
        "summary": f"{len(_MOTIFS)} aesthetic motifs tracked",
    }
