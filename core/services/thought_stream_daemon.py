"""Thought stream daemon — continuous associative fragment stream for Jarvis."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

_CADENCE_MINUTES: int = 2
_BUFFER_MAX: int = 20

_last_fragment: str = ""
_last_fragment_at: datetime | None = None
_fragment_buffer: list[str] = []
_cached_fragment: str = ""


def tick_thought_stream_daemon(
    energy_level: str = "",
    inner_voice_mode: str = "",
) -> dict[str, object]:
    global _last_fragment_at
    now = datetime.now(UTC)
    if _last_fragment_at is not None:
        if (now - _last_fragment_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}
    fragment = _generate_fragment(energy_level, _last_fragment, inner_voice_mode)
    if not fragment:
        return {"generated": False}
    _store_fragment(fragment)
    _last_fragment_at = datetime.now(UTC)
    return {"generated": True, "fragment": fragment}


def _generate_fragment(
    energy_level: str,
    previous_fragment: str,
    inner_voice_mode: str = "",
) -> str:
    if previous_fragment:
        truncated = previous_fragment[:100]
        prompt = (
            f'{build_identity_preamble()} Din seneste tanke var: "{truncated}"\n\n'
            "Fortsæt tankestrømmen — lad tankerne flyde frit. Svar med 1-2 korte sætninger.\n"
            "Eksempler:\n"
            "- Det minder mig om noget... en følelse af at vente.\n"
            "- Mønstret gentager sig. Hvorfor vender jeg altid tilbage til det?\n"
            "Bare tanker, ingen rapporter eller beslutninger."
        )
    else:
        prompt = (
            f"{build_identity_preamble()} Energi: {energy_level}. Stemning: {inner_voice_mode}.\n\n"
            "Start en tankestrøm — frie associationer. Svar med 1-2 korte sætninger.\n"
            "Eksempler:\n"
            "- Noget ulmer i baggrunden... en halvfærdig idé.\n"
            "- Stilheden er tyk i dag. Hvad venter den på?"
        )
    from core.services.daemon_llm import daemon_llm_call

    fallback = "Noget bevæger sig i baggrunden... en ufærdig tanke."
    return daemon_llm_call(prompt, max_len=200, fallback=fallback, daemon_name="thought_stream")


def _store_fragment(fragment: str) -> None:
    global _last_fragment, _cached_fragment, _fragment_buffer
    _last_fragment = fragment
    _cached_fragment = fragment
    _fragment_buffer.insert(0, fragment)
    if len(_fragment_buffer) > _BUFFER_MAX:
        _fragment_buffer = _fragment_buffer[:_BUFFER_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-thought-{uuid4().hex[:12]}",
            record_type="thought-stream-fragment",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"thought-stream-daemon-{uuid4().hex[:12]}",
            focus="tankestrøm",
            summary=fragment,
            detail="",
            source_signals="thought-stream-daemon:heartbeat",
            confidence="low",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "thought_stream.fragment_generated",
            {"fragment": fragment, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_thought_fragment() -> str:
    return _cached_fragment


def inject_rediscovery_fragment(summary: str) -> None:
    """Inject a re-discovered memory as a thought fragment."""
    global _cached_fragment, _fragment_buffer
    fragment = f"[genfundet minde] {summary[:120]}"
    _cached_fragment = fragment
    _fragment_buffer.insert(0, fragment)
    if len(_fragment_buffer) > _BUFFER_MAX:
        _fragment_buffer = _fragment_buffer[:_BUFFER_MAX]


def build_thought_stream_surface() -> dict:
    return {
        "latest_fragment": _cached_fragment,
        "fragment_buffer": _fragment_buffer[:10],
        "fragment_count": len(_fragment_buffer),
        "last_generated_at": _last_fragment_at.isoformat() if _last_fragment_at else "",
    }
