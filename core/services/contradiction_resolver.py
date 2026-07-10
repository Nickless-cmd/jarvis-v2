"""Contradiction resolver (spec 2026-07-10).

Konsumerer contradiction_engine-findings og RESOLVER dem gennem Centralen —
ikke observe-only (Centralens formaal er at handle, Bjoern 10. jul). Detektionen
forbliver ren/uaendret i contradiction_engine. Denne fil ejer KUN handlings-siden.
"""
from __future__ import annotations
from typing import Any
import logging

from core.runtime.db import connect
from core.eventbus.bus import event_bus  # publish(kind, payload)

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


def _apply_supersede(decision_id: str, *, review_id: int, rule: str) -> bool:
    """Marker den tabende decision superseded (status-flip, reversibel, aldrig slettet).
    Returnerer True hvis en aktiv raekke blev flippet."""
    did = str(decision_id or "")
    if not did:
        return False
    try:
        with connect() as c:
            cur = c.execute(
                "UPDATE behavioral_decisions SET status='superseded'"
                " WHERE decision_id=? AND status='active'",
                (did,),
            )
            c.commit()
            changed = cur.rowcount > 0
    except Exception as exc:
        logger.debug("contradiction_resolver: supersede failed: %s", exc)
        return False
    if changed:
        try:
            event_bus.publish("contradiction.resolved", {
                "decision_id": did, "review_id": int(review_id or 0),
                "action": "superseded", "rule": rule,
            })
        except Exception:
            pass
    return changed


def revert_supersede(decision_id: str) -> bool:
    """Owner-reversal (Central-CLI): superseded → active igen."""
    did = str(decision_id or "")
    if not did:
        return False
    try:
        with connect() as c:
            cur = c.execute(
                "UPDATE behavioral_decisions SET status='active'"
                " WHERE decision_id=? AND status='superseded'",
                (did,),
            )
            c.commit()
            return cur.rowcount > 0
    except Exception as exc:
        logger.debug("contradiction_resolver: revert failed: %s", exc)
        return False


def _write_escalation_proposal(finding: dict[str, Any], *, rule: str, seen: set) -> bool:
    """Escalate-tier: publicer et resolution-FORSLAG (muterer intet). Deduppet pr.
    (decision_id, review_id) via ``seen`` (bygget fra nylige proposed-events denne tur)."""
    key = (str(finding.get("decision_id") or ""), int(finding.get("review_id") or 0))
    if key in seen:
        return False
    seen.add(key)
    try:
        event_bus.publish("contradiction.resolution_proposed", {
            "decision_id": key[0], "review_id": key[1],
            "decision_directive": str(finding.get("decision_directive") or "")[:200],
            "review_text": str(finding.get("review_text") or "")[:200],
            "rule": rule,
        })
    except Exception:
        pass
    return True
