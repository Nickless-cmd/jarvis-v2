"""Curiosity daemon — detects gaps in Jarvis' thought stream and generates curiosity signals."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CADENCE_MINUTES = 5
_OPEN_MAX = 5

_last_tick_at: datetime | None = None
_cached_curiosity: str = ""
_open_questions: list[str] = []

_GAP_PATTERNS: list[tuple[str, str]] = [
    ("question", "?"),
    ("open", "ved ikke"),
    ("wonder", "undrer"),
    ("wonder", "nysgerrig"),
    ("question", "hvorfor"),
    ("question", "hvad hvis"),
    ("interrupted", "..."),
]


def tick_curiosity_daemon(fragments: list[str]) -> dict[str, object]:
    """Scan thought stream fragments for gaps. fragments: recent fragment buffer (latest first)."""
    global _last_tick_at

    if _last_tick_at is not None:
        if (datetime.now(UTC) - _last_tick_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    gap = _detect_gap(fragments)
    if not gap:
        return {"generated": False}

    topic, gap_type = gap
    signal = _generate_curiosity_signal(topic, gap_type)
    if not signal:
        return {"generated": False}

    _store_curiosity(signal)
    _last_tick_at = datetime.now(UTC)
    return {"generated": True, "curiosity": signal, "gap_type": gap_type}


def _detect_gap(fragments: list[str]) -> tuple[str, str] | None:
    for fragment in fragments:
        fl = fragment.lower()
        for gap_type, pattern in _GAP_PATTERNS:
            if pattern in fl:
                topic = fragment[:60].strip()
                return (topic, gap_type)
    return None


def _generate_curiosity_signal(topic: str, gap_type: str) -> str:
    from core.services.daemon_llm import daemon_public_safe_llm_call

    fallback = f"Jeg undrer mig over: {topic[:50]}"
    cue = _curiosity_cue(topic=topic, gap_type=gap_type)
    prompt = "\n".join(
        [
            "Skriv ÉN kort dansk sætning der udtrykker en konkret nysgerrighed.",
            "Start med noget i retning af 'Jeg undrer mig over...', 'Hvad nu hvis...',",
            "'Hvordan ville det være...' — og gør den SPECIFIK til cue'en.",
            "SVAR KUN PÅ DANSK. Ikke bare 'Hvorfor?' — vær konkret.",
            "Ingen identitet, ingen private tanker, ingen personlige navne.",
            "",
            "Eksempler på god output:",
            "- Jeg undrer mig over hvorfor visse mønstre kun dukker op om natten.",
            "- Hvad nu hvis den tavshed jeg lægger mærke til faktisk bærer information?",
            "- Hvordan forholder vægt sig til rytme i gentagne handlinger?",
            "",
            f"gap_type: {gap_type}",
            f"cue: {cue}",
            "",
            "Svar nu med én kort, specifik dansk sætning:",
        ]
    )
    return daemon_public_safe_llm_call(
        prompt, max_len=200, fallback=fallback, daemon_name="curiosity"
    )


def _curiosity_cue(*, topic: str, gap_type: str) -> str:
    lowered = str(topic or "").lower()
    if "hvorfor" in lowered:
        return "cause-seeking"
    if "hvad hvis" in lowered:
        return "counterfactual"
    if "ved ikke" in lowered:
        return "missing-knowledge"
    if "..." in lowered:
        return "interrupted-thread"
    if "?" in lowered:
        return "open-question"
    if "undrer" in lowered or "nysgerrig" in lowered:
        return "explicit-wonder"
    return f"generic-{gap_type}"


def _store_curiosity(signal: str) -> None:
    global _cached_curiosity, _open_questions
    _cached_curiosity = signal
    _open_questions.insert(0, signal)
    if len(_open_questions) > _OPEN_MAX:
        _open_questions = _open_questions[:_OPEN_MAX]
    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-curiosity-{uuid4().hex[:12]}",
            record_type="curiosity-signal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"curiosity-daemon-{uuid4().hex[:12]}",
            focus="nysgerrighed",
            summary=signal,
            detail="",
            source_signals="curiosity-daemon:thought-stream",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "curiosity.detected",
            {"signal": signal, "generated_at": now_iso},
        )
    except Exception:
        pass


def get_latest_curiosity() -> str:
    return _cached_curiosity


def build_curiosity_surface() -> dict:
    return {
        "latest_curiosity": _cached_curiosity,
        "open_questions": _open_questions[:5],
        "curiosity_count": len(_open_questions),
        "last_generated_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }
