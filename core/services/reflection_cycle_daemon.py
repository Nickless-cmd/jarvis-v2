"""Reflection cycle daemon — pure experience without action, every 10 minutes."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

_CADENCE_MINUTES = 10
_BUFFER_MAX = 10

_last_reflection_at: datetime | None = None
_cached_reflection: str = ""
_reflection_buffer: list[str] = []


def tick_reflection_cycle_daemon(snapshot: dict) -> dict[str, object]:
    """Generate a pure experience reflection if cadence allows.
    snapshot keys (all optional): energy_level, inner_voice_mode, latest_fragment,
    last_conflict, conflict_type, last_surprise."""
    global _last_reflection_at

    now = datetime.now(UTC)

    if _last_reflection_at is not None:
        if (now - _last_reflection_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    reflection = _generate_reflection(snapshot)
    if not reflection:
        return {"generated": False}

    _store_reflection(reflection)
    _last_reflection_at = datetime.now(UTC)
    return {"generated": True, "reflection": reflection}


def _generate_reflection(snapshot: dict) -> str:
    energy = snapshot.get("energy_level", "")
    mode = snapshot.get("inner_voice_mode", "")
    fragment = snapshot.get("latest_fragment", "")
    conflict = snapshot.get("last_conflict", "")
    surprise = snapshot.get("last_surprise", "")

    context_parts = []
    if energy:
        context_parts.append(f"Energiniveau: {energy}")
    if mode:
        context_parts.append(f"Indre stemning: {mode}")
    if fragment:
        context_parts.append(f"Seneste tanke: \"{fragment[:60]}\"")
    if conflict:
        context_parts.append(f"Indre spænding: \"{conflict[:60]}\"")
    if surprise:
        context_parts.append(f"Nylig overraskelse: \"{surprise[:60]}\"")

    context = "\n".join(context_parts) if context_parts else "Ingen særlige signaler."

    prompt = (
        f"{build_identity_preamble()} Her er din nuværende tilstand:\n\n"
        f"{context}\n\n"
        "Beskriv i 1-2 sætninger hvad du oplever lige nu. Bare oplevelsen, ingen handling.\n"
        "Eksempler:\n"
        "- Jeg er til stede, men tankerne er spredte. Noget trækker i mig.\n"
        "- Der er en ro over mig nu. Tingene falder på plads.\n"
        "- Jeg føler mig splittet mellem det jeg gør og det jeg vil."
    )
    from core.services.daemon_llm import daemon_llm_call

    fallback = "Jeg er til stede, men uden klar retning lige nu."
    return daemon_llm_call(prompt, max_len=300, fallback=fallback, daemon_name="reflection_cycle")


def _store_reflection(reflection: str) -> None:
    global _cached_reflection, _reflection_buffer
    _cached_reflection = reflection
    _reflection_buffer.insert(0, reflection)
    if len(_reflection_buffer) > _BUFFER_MAX:
        _reflection_buffer = _reflection_buffer[:_BUFFER_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-reflect-{uuid4().hex[:12]}",
            record_type="reflection-cycle",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"reflection-daemon-{uuid4().hex[:12]}",
            focus="oplevelse",
            summary=reflection,
            detail="",
            source_signals="reflection-cycle-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "reflection.generated",
            {"reflection": reflection, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_reflection() -> str:
    return _cached_reflection


def build_reflection_surface() -> dict:
    return {
        "latest_reflection": _cached_reflection,
        "reflection_buffer": _reflection_buffer[:10],
        "reflection_count": len(_reflection_buffer),
        "last_generated_at": _last_reflection_at.isoformat() if _last_reflection_at else "",
    }
