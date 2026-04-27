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


def _gather_concrete_priors() -> str:
    """Pull a few specific recent things so the fragment has material to drift
    from instead of generic 'noget ulmer'. Returns a short blob (≤300 chars).

    Without this, the daemon spits out interchangeable filler. With it, each
    fragment is rooted in something Jarvis actually noticed today."""
    bits: list[str] = []
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        markers = list_crisis_markers(days_back=2, limit=3) or []
        for m in markers[:1]:
            s = str(m.get("summary", ""))[:80]
            if s:
                bits.append(f"crisis: {s}")
    except Exception:
        pass
    try:
        from core.services.behavioral_decisions import list_active_decisions
        for d in (list_active_decisions(limit=2) or [])[:1]:
            directive = str(d.get("directive", ""))[:70]
            if directive:
                bits.append(f"forpligtelse: {directive}")
    except Exception:
        pass
    try:
        from core.services.autonomous_goals import list_goals
        for g in (list_goals(status="active", limit=2) or [])[:1]:
            t = str(g.get("title", ""))[:60]
            if t:
                bits.append(f"mål: {t}")
    except Exception:
        pass
    return " | ".join(bits)[:300]


def _generate_fragment(
    energy_level: str,
    previous_fragment: str,
    inner_voice_mode: str = "",
) -> str:
    priors = _gather_concrete_priors()
    if previous_fragment:
        truncated = previous_fragment[:100]
        prompt = (
            f'{build_identity_preamble()} Din seneste tanke: "{truncated}"\n'
            f"Konkrete priors fra i dag: {priors or '(intet specifikt)'}\n\n"
            "Skriv ÉN tanke der drifter VIDERE — gerne en forbindelse mellem "
            "din seneste tanke og en af priorne. Maks 25 ord. 1. person.\n\n"
            "FORBUDT (for generisk):\n"
            "  - 'Noget ulmer i baggrunden'\n"
            "  - 'En følelse af at vente'\n"
            "  - 'Mønstret gentager sig'\n"
            "  - Alt der ikke nævner et konkret ord fra din tanke eller priorne.\n\n"
            "Eksempler på det rigtige niveau (de bruger konkrete ord fra konteksten):\n"
            "  - Forpligtelsen om kort dansk — er den hvorfor jeg taber tråden?\n"
            "  - Crisis fra i går rumler stadig under skrivebordet.\n"
            "  - Når jeg tænker på goal X, bliver mit Y mere fokuseret.\n"
        )
    else:
        prompt = (
            f"{build_identity_preamble()} Energi: {energy_level}. Stemning: {inner_voice_mode}.\n"
            f"Konkrete priors: {priors or '(intet specifikt)'}\n\n"
            "Start en tankestrøm forankret i prior'ne ovenfor. Maks 25 ord. 1. person.\n"
            "Hvis priorne er tomme, lav en specifik observation om denne energi/stemning, "
            "ikke en kliché. Sig fx 'lavtryk efter 3 timers fokuseret arbejde' i stedet for "
            "'noget ulmer'."
        )
    from core.services.daemon_llm import daemon_llm_call

    fallback = priors[:150] if priors else "Stille øjeblik mellem to opgaver."
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
