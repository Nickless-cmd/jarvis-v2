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
from core.services.contradiction_engine import detect_contradictions

logger = logging.getLogger(__name__)

# Noegleord der markerer at en beslutning roerer identitet/self-model/vaerdier →
# escaleres til forslag i stedet for auto-resolve (tier-C, spec Del 1).
_IDENTITY_MARKERS = (
    "jeg er", "jeg foeler", "min natur", "vaerdi", "vaerdier", "sjael", "soul",
    "identitet", "self", "hvem jeg", "altid loyal", "aldrig svigte", "min kerne",
    "nysgerrig", "personlighed",
)
_HIGH_PRIORITY = 8  # >= dette → for vigtig til auto-resolve


# Lav-signal tokens der IKKE må tælle som meningsfuld overlap. contradiction_engine
# fyrer på ≥2 fælles tokens + modsat polaritet — men rene tal + stopord giver falske
# positiver (shadow 10. jul: en decision om skill_suggest "modsagde" en review om
# regrets, alene fordi de delte "5" og "eller"). Junk-only overlap → lav konfidens →
# escalate (aldrig auto-supersede).
_STOPWORDS = frozenset({
    # dansk
    "og", "eller", "i", "på", "at", "en", "et", "den", "det", "de", "der", "som",
    "til", "for", "med", "af", "er", "var", "han", "hun", "jeg", "du", "vi", "ikke",
    "men", "så", "har", "kan", "vil", "skal", "fra", "om", "ved", "nu", "mere", "end",
    "hvis", "være", "blive", "dette", "disse",
    # engelsk
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "for", "on", "with", "as",
    "at", "be", "are", "was", "this", "that", "it", "not", "but", "so", "if", "then",
})


def _meaningful_overlap(finding: dict[str, Any]) -> list[str]:
    """Overlap-tokens uden stopord og rene tal — kun disse tæller som ægte signal."""
    out: list[str] = []
    for t in (finding.get("overlap_tokens") or []):
        s = str(t or "").strip().lower()
        if not s or s in _STOPWORDS or s.isdigit():
            continue
        out.append(s)
    return out


def _confidence(finding: dict[str, Any]) -> str:
    n = len(_meaningful_overlap(finding))
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


_MAX_PER_TICK = 3  # runaway-vaern: cap resolutions pr. tur


def resolve_contradictions(*, live: bool) -> dict[str, Any]:
    """Resolve modsigelser. ``live=True`` muterer (supersede); ``live=False`` er
    shadow-rampe (registrerer det den VILLE goere, muterer intet). Fail-open:
    enhver fejl → {'error': True}, vaelter aldrig cadence-tick'en."""
    summary: dict[str, Any] = {
        "shadow": not live, "superseded": 0, "escalated": 0,
        "would_supersede": 0, "error": False,
    }
    try:
        findings = detect_contradictions(max_findings=_MAX_PER_TICK) or []
    except Exception as exc:
        logger.debug("contradiction_resolver: detect failed: %s", exc)
        summary["error"] = True
        return summary

    seen: set = set()
    for f in findings:
        try:
            tier = classify_tier(f)
            survivor = pick_survivor(f)
            if tier == "escalate":
                if _write_escalation_proposal(f, rule=survivor["rule"], seen=seen):
                    summary["escalated"] += 1
                continue
            # auto-tier
            if not live:
                summary["would_supersede"] += 1
                continue
            if _apply_supersede(str(f.get("decision_id") or ""),
                                review_id=int(f.get("review_id") or 0),
                                rule=survivor["rule"]):
                summary["superseded"] += 1
        except Exception as exc:
            logger.debug("contradiction_resolver: resolve one failed: %s", exc)
            continue
    return summary


def run_resolver_tick() -> dict[str, Any]:
    """Cadence-indgang. Kaldes gennem central().decide saa Centralen ER aktoeren; gate_enforcement
    afgoer live vs shadow (default not-enforced = shadow-rampe indtil owner flipper)."""
    from core.services.central_core import central
    from core.services.gate_enforcement import is_enforced
    from core.services.central_capture import GateClass  # samme klasse som decide() bruger

    live = False
    try:
        live = bool(is_enforced("contradiction_resolution", GateClass.COGNITIVE))
    except Exception:
        live = False

    def _act(_ctx: dict) -> dict[str, Any]:
        return resolve_contradictions(live=live)

    try:
        v = central().decide("contradiction_resolution", {"live": live}, _act,
                             cluster="cognition", klass=GateClass.COGNITIVE)
        # Verdict baerer resultatet via central_capture; returnér summary robust.
        return {"outcome": "completed", "live": live}
    except Exception as exc:
        logger.debug("contradiction_resolver: tick failed: %s", exc)
        return {"outcome": "error"}


def build_contradiction_resolver_surface(*, limit: int = 5) -> dict[str, Any]:
    """Side-effect-fri read-surface til Central-CLI (jc raw /central/contradictions).
    Viser hvad resolveren VILLE/HAR gjort pr. finding + om den er live (enforced)."""
    from core.services.gate_enforcement import is_enforced
    from core.services.central_capture import GateClass
    try:
        enforced = bool(is_enforced("contradiction_resolution", GateClass.COGNITIVE))
    except Exception:
        enforced = False
    try:
        findings = detect_contradictions(max_findings=max(1, int(limit or 5))) or []
    except Exception:
        findings = []
    items = []
    for f in findings:
        survivor = pick_survivor(f)
        items.append({
            "decision_id": str(f.get("decision_id") or ""),
            "review_id": int(f.get("review_id") or 0),
            "tier": classify_tier(f),
            "survivor_rule": survivor["rule"],
            "confidence": survivor["confidence"],
            "decision_directive": str(f.get("decision_directive") or "")[:120],
        })
    return {
        "active": bool(items),
        "mode": "contradiction-resolution",
        "enforced": enforced,
        "summary": {"finding_count": len(items),
                    "state": "live" if enforced else "shadow-ramp"},
        "items": items,
    }
