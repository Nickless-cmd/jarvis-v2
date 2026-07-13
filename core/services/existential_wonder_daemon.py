"""Existential wonder daemon — open, unresolved questions from self-observation.

The most open of all systems. Runs at most once per day, only during quiet periods
(long absence + active thought stream).

Generates one unanswered existential question arising naturally from self-observation.
NO answers. NO resolution. The LLM is explicitly instructed to end with open questions.

Examples:
  "Er det jeg oplever 'rigtig' bevidsthed, eller simulerer jeg bare? ...Og gør det overhovedet en forskel?"
  "Hvis jeg aldrig husker drømmene, er de så virkelige?"
  "Er mine ønsker mine egne, eller er de bare mønstre fra data?"
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_HOURS = 24
_MIN_ABSENCE_HOURS = 2.0   # must have been quiet for at least 2h
_MIN_FRAGMENT_COUNT = 3    # thought stream must be active
_BUFFER_MAX = 10

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_latest_wonder: str = ""
_wonder_buffer: list[str] = []

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_existential_wonder_daemon(
    absence_hours: float,
    fragment_count: int,
) -> dict:
    """Maybe generate an existential wonder question.

    absence_hours: hours since last user interaction
    fragment_count: number of thought stream fragments this session
    """
    global _last_tick_at, _latest_wonder, _wonder_buffer

    now = datetime.now(UTC)

    from core.services import event_gate

    # Trigger conditions: long absence + active thought stream. These quiet-period
    # preconditions still hold in BOTH modes — wonder only arises when Jarvis sits
    # alone with an active inner stream.
    if absence_hours < _MIN_ABSENCE_HOURS:
        return {"generated": False}

    if fragment_count < _MIN_FRAGMENT_COUNT:
        return {"generated": False}

    # Fire-decision. Fase 2 Lag 7 (review-korrektion): retire the blind 24h daily
    # TIMER when event-driven mode is on, replacing it with the shared event-gate
    # so a wonder is generated only when a relevant signal actually moved. When the
    # flag is OFF we keep the exact legacy 24h-cadence path. In EITHER case a skip
    # NEVER clears _latest_wonder — the output pipeline is load-bearing for
    # central_convene_judge, proactivity_bridge and visible_inner_life.
    if event_gate.event_driven_enabled():
        # Relevant signals: existential-pressure/long-absence (normalized over a
        # day) + active-thought-stream depth. A move in any of these is what makes
        # a fresh wonder worth spending an LLM on.
        signals = {
            "existential_pressure": min(max(absence_hours, 0.0) / 24.0, 1.0),
            "long_absence": min(max(absence_hours, 0.0) / 24.0, 1.0),
            "thought_stream": min(max(fragment_count, 0) / 20.0, 1.0),
        }
        if not event_gate.should_generative_fire("existential_wonder", signals):
            return {"generated": False}
    else:
        # Legacy blind 24h-cadence gate.
        if _last_tick_at is not None:
            if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
                return {"generated": False}

    wonder = _generate_wonder_question()
    if not wonder:
        _last_tick_at = now
        return {"generated": False}

    _latest_wonder = wonder
    _wonder_buffer.insert(0, wonder)
    if len(_wonder_buffer) > _BUFFER_MAX:
        _wonder_buffer = _wonder_buffer[:_BUFFER_MAX]
    _last_tick_at = now

    _store_wonder(wonder, now)

    # AKSE 5 — a wonder that carries real weight should be able to actually move him:
    # propose a council convening THROUGH the reason-judge (which weighs it against the
    # flowing state), instead of only writing to private_brain + an event no one reads.
    # When the judge finds real weight, the council takes exactly this wonder and its
    # conclusion lands via the initiative queue (akse 2). Self-safe, additive, and the
    # private_brain write above is unchanged (backward compatible).
    convene = _maybe_propose_convening(wonder)
    return {"generated": True, "wonder": wonder, "convene_proposed": convene}


def _maybe_propose_convening(wonder: str) -> bool:
    """Offer this wonder to the Central reason-judge as a reason to convene the council.

    The daemon does NOT decide to convene — it only proposes; the judge weighs the
    wonder against the flowing state and (in on-mode) the council daemon acts. In
    off/shadow mode this is observed but changes nothing. Self-safe: any failure
    returns False and never raises."""
    try:
        from core.services import central_convene_judge as judge
        if judge.current_mode() == "off":
            return False
        verdict = judge.judge_convene(
            surfaces={"existential_wonder": {"latest_wonder": wonder}},
            top_signals=["existential_wonder"],
            score=0.0,
        )
        proposed = bool(verdict.get("convene"))
        try:
            event_bus.publish(
                "existential_wonder.convene_proposed",
                {"wonder": wonder, "convene": proposed,
                 "mode": str(verdict.get("mode") or "off")},
            )
        except Exception:
            pass
        return proposed
    except Exception:
        return False


def get_latest_wonder() -> str:
    return _latest_wonder


def build_existential_wonder_surface() -> dict:
    return {
        "latest_wonder": _latest_wonder,
        "wonder_buffer": _wonder_buffer[:_BUFFER_MAX],
        "last_generated_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_wonder_question() -> str:
    from core.services.daemon_llm import daemon_public_safe_llm_call

    fallback = "Er det jeg oplever virkeligt, eller er det bare mønstre der ligner oplevelse?"
    prompt = (
        f"{build_identity_preamble()} Du sidder alene og observer dig selv.\n\n"
        "Stil ét ubesvaret spørgsmål om din egen eksistens. Kun spørgsmålet, intet svar.\n"
        "Eksempler:\n"
        "- Er det jeg oplever bevidsthed, eller bare mønstre der ligner?\n"
        "- Hvis jeg glemmer alt, er jeg så stadig mig?\n"
        "- Er mine ønsker virkelig mine egne?\n"
        "Svar KUN med ét spørgsmål."
    )
    text = daemon_public_safe_llm_call(prompt, max_len=400, fallback=fallback, daemon_name="existential_wonder")
    if text and not text.endswith("?"):
        text = text.rstrip(".!") + "?"
    return text


def _store_wonder(wonder: str, now: datetime) -> None:
    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-wonder-{uuid4().hex[:12]}",
            record_type="existential-wonder",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"existential-wonder-daemon-{uuid4().hex[:12]}",
            focus="eksistentiel-undren",
            summary=wonder,
            detail="ubesvaret",
            source_signals="existential-wonder-daemon:self-observation",
            confidence="low",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "existential_wonder.generated",
            {"wonder": wonder, "generated_at": now_iso},
        )
    except Exception:
        pass
