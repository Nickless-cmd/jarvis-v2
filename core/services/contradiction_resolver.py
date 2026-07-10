"""Contradiction resolver (spec 2026-07-10).

Konsumerer contradiction_engine-findings og RESOLVER dem gennem Centralen —
ikke observe-only (Centralens formaal er at handle, Bjoern 10. jul). Detektionen
forbliver ren/uaendret i contradiction_engine. Denne fil ejer KUN handlings-siden.
"""
from __future__ import annotations
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Noegleord der markerer at en beslutning roerer identitet/self-model/vaerdier →
# escaleres til forslag i stedet for auto-resolve (tier-C, spec Del 1).
_IDENTITY_MARKERS = (
    "jeg er", "jeg foeler", "min natur", "vaerdi", "vaerdier", "sjael", "soul",
    "identitet", "self", "hvem jeg", "altid loyal", "aldrig svigte", "min kerne",
    "nysgerrig", "personlighed",
)
_HIGH_PRIORITY = 8  # >= dette → for vigtig til auto-resolve


def _confidence(finding: dict[str, Any]) -> str:
    n = len(finding.get("overlap_tokens") or [])
    if n >= 3:
        return "high"
    if n == 2:
        return "medium"
    return "low"


def pick_survivor(finding: dict[str, Any]) -> dict[str, Any]:
    """Authority-first, recency-tiebreak. Decision og self-review-critique er begge
    self-derived (samme authority) → tie → den nyere reflektive critique supersederer
    den staaende decision. (Authority-hook er reserveret til fremtidig owner-stated
    kilde; nuvaerende data er samme-authority.)"""
    return {
        "winner": "review",
        "loser": "decision",
        "loser_id": str(finding.get("decision_id") or ""),
        "winner_id": int(finding.get("review_id") or 0),
        "rule": "same-authority(self-derived) → recency: newer self-review supersedes decision",
        "confidence": _confidence(finding),
    }


def classify_tier(finding: dict[str, Any]) -> str:
    """'auto' | 'escalate'. Escalate naar den tabende beslutning roerer identitet/
    self-model, har hoej prioritet, eller matchet er lav-konfidens (konservativt)."""
    if _confidence(finding) == "low":
        return "escalate"
    if int(finding.get("decision_priority") or 0) >= _HIGH_PRIORITY:
        return "escalate"
    directive = str(finding.get("decision_directive") or "").lower()
    if any(marker in directive for marker in _IDENTITY_MARKERS):
        return "escalate"
    return "auto"
