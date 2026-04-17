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

    # Cadence gate: 24h
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
            return {"generated": False}

    # Trigger conditions: long absence + active thought stream
    if absence_hours < _MIN_ABSENCE_HOURS:
        return {"generated": False}

    if fragment_count < _MIN_FRAGMENT_COUNT:
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
    return {"generated": True, "wonder": wonder}


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
    from core.services.daemon_llm import daemon_llm_call

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
    text = daemon_llm_call(prompt, max_len=400, fallback=fallback, daemon_name="existential_wonder")
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
