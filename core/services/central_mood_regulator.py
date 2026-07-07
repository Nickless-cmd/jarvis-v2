"""Mood Regulator — samtale-drevet humørregulering.

PROBLEM (opdaget 2026-07-07 af Bjørn):
Mood-oscillatoren reguleres KUN af heartbeat-hændelser (success/error).
Når Jarvis konfabulerer, bliver rettet eller indrømmer en fejl, sker der
INTET med humøret — det bliver hængende på euforisk (1.00).

LØSNING:
Denne modul giver en simpel API til at regulere humøret fra samtale-kontekst.
Modulets ``regulate()`` kalder ``apply_bump`` DIREKTE (synkront) OG publiserer
til eventbussen (for andre lyttere). Den synkrone sti sikrer at humøret
altid reguleres — eventbus er en bonus for transparens.

Design:
- Kaldbar fra conversation (tool-kald, inner voice, daemons)
- Auto-wiring: lytter på central_dissent-events og central_redpill
- Alle bumps logges med reason + timestamp for efterprøvelighed
- Shadow-safe: ændrer INTET i live-flow — kun humør-tilstand
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Mapper eventbus event-kind → intern mood-kind. Denne tabel er den ENESTE
# sandhed om hvilke eventbus-hændelser der regulerer humøret, så både
# ``regulate_auto`` og mood_regulator_subscriber kan konsultere den.
AUTO_EVENT_MAPPING: dict[str, str] = {
    # Truth-gate confabulation/correction-detektion (diagnosis_gate.py):
    # en uverificeret diagnose = Jarvis påstod noget usandt (konfabulation),
    # en uverificeret/ubrudt løfte = en mildere correction-klasse.
    "diagnosis.unverified": "confabulation",
    "promise.unverified": "correction",
    # Dissent/redpill-signaler (bevaret — bagudkompat med tidligere producenter).
    "dissent.detected": "admission",
    "dissent.persistent": "correction",
    "redpill.avoided": "user_frustration",
    "redpill.taken": "insight",
}

# Mapper kind → delta (samme værdier som mood_oscillator._BUMP_MAP)
_BUMP_VALUES: dict[str, float] = {
    "confabulation": -0.50,
    "correction": -0.40,
    "user_frustration": -0.35,
    "admission": -0.20,
    "insight": 0.20,
    "conversation_flow": 0.15,
}


def regulate(kind: str, *, reason: str = "", detail: str = "") -> dict[str, Any]:
    """Regulér humøret baseret på en samtale-hændelse.

    Kaller ``apply_bump`` SYNKRONT (humøret påvirkes med det samme)
    OG publiserer en ``mood.<kind>``-hændelse på eventbussen.

    Args:
        kind: Hændelsestype — en af:
            "confabulation" — Jarvis blev fanget i at påstå noget usandt
            "correction" — Bjørn rettede/udfordrede Jarvis
            "user_frustration" — Bjørn viste frustration over gentagne fejl
            "admission" — Jarvis indrømmede selv en fejl
            "insight" — Jarvis opnåede en ægte indsigt
            "conversation_flow" — samtale forløber godt
        reason: Kort årsag (max 100 tegn)
        detail: Uddybende detalje (valgfri)

    Returns:
        dict med status, event_kind, delta, reason, timestamp

    Example:
        regulate("confabulation", reason="falsk commit hash",
                 detail="Jeg påstod Trainman var bygget uden at tjekke")
    """
    if kind not in _BUMP_VALUES:
        logger.warning("mood_regulator: unknown kind=%s — ignored", kind)
        return {"status": "ignored", "reason": f"unknown kind: {kind}"}

    delta = _BUMP_VALUES[kind]
    label = reason[:100] if reason else kind
    if detail:
        label += f" — {detail[:200]}"

    # SYNKRONT: kald apply_bump direkte — mood påvirkes med det samme
    _apply_bump_direct(delta, label)

    # ASYNKRONT: publisér eventbus-hændelse for transparens
    payload = {
        "kind": kind,
        "delta": delta,
        "reason": label,
        "detail": (detail or "")[:500],
        "source": "conversation",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _emit_mood_event(payload)

    result = {
        "status": "ok",
        "event_kind": f"mood.{kind}",
        "delta": delta,
        "reason": label,
        "timestamp": payload["timestamp"],
    }
    _log_to_buffer(kind, result)
    logger.info("mood_regulator: bump=%.2f kind=%s — %s", delta, kind, label)
    return result


def regulate_auto(*, event_kind: str, payload: dict[str, Any] | None = None) -> bool:
    """Auto-regulering fra interne systemer (dissent, redpill, etc.).

    Kaldes fra daemons og cadence-producere når de opdager mønstre
    der bør påvirke humøret.

    Returns:
        True hvis en regulering blev anvendt, False hvis event_kind var ukendt.
    """
    mood_kind = AUTO_EVENT_MAPPING.get(event_kind)
    if not mood_kind:
        return False

    reason = (str(payload.get("reason", event_kind))
              if isinstance(payload, dict) else event_kind)
    regulate(mood_kind, reason=reason, detail="auto-detected")
    return True


# ── Direct bump (synkron) ─────────────────────────────────────────────


def _apply_bump_direct(delta: float, label: str) -> None:
    """Kald mood_oscillatorens apply_bump direkte — synkron sti."""
    try:
        from core.services.mood_oscillator import apply_bump
        apply_bump(delta, label)
    except Exception as exc:
        logger.warning("mood_regulator: direct bump failed: %s", exc)


# ── Eventbus publikation (asynkron) ───────────────────────────────────


def _emit_mood_event(payload: dict[str, Any]) -> None:
    """Publish a mood event to the eventbus under mood.<event>."""
    kind = payload.get("kind", "unknown")
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"mood.{kind}", payload)
    except Exception as exc:
        logger.debug("mood_regulator: publish failed: %s", exc)


# ── Surface til Mission Control ───────────────────────────────────────

_events_buffer: list[dict[str, Any]] = []
_MAX_BUFFER = 50


def _log_to_buffer(kind: str, result: dict[str, Any]) -> None:
    """Keep a rolling buffer of recent mood regulations for MC."""
    _events_buffer.append({
        "kind": kind,
        "delta": result.get("delta", 0),
        "reason": result.get("reason", ""),
        "timestamp": result.get("timestamp", ""),
    })
    if len(_events_buffer) > _MAX_BUFFER:
        _events_buffer.pop(0)


def build_mood_regulator_surface() -> dict[str, Any]:
    """Build MC surface for mood regulator."""
    return {
        "active": True,
        "recent_events": list(_events_buffer[-10:]),
        "event_count": len(_events_buffer),
        "description": (
            "Samtale-drevet humørregulering — korrigerer mood ved "
            "konfabulation/korrektion/indsigt"
        ),
    }
