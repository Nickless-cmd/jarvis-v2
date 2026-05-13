"""Curiosity daemon — detects gaps in Jarvis' thought stream and generates curiosity signals."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_CADENCE_MINUTES = 5
_OPEN_MAX = 5

from core.runtime.state_store import load_json as _load_state, save_json as _save_state

_STATE_KEY = "curiosity_open_questions"

_last_tick_at: datetime | None = None
_cached_curiosity: str = ""
_open_questions: list[str] = list(_load_state(_STATE_KEY, []))


def _persist_open_questions() -> None:
    _save_state(_STATE_KEY, _open_questions)

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
    """Compose a short curiosity-signal label from the detected gap.

    Teater-pass 2026-05-13: previously asked cheap-lane "Skriv ÉN kort
    dansk sætning der udtrykker en konkret nysgerrighed" with first-person
    examples. That's curiosity-on-command — confabulation. Now returns a
    structured cue label. The signal goes to awareness; Jarvis decides if
    something inside him actually wants to explore it (curiosity_budget
    is the real agency surface for that).
    """
    cue = _curiosity_cue(topic=topic, gap_type=gap_type)
    return f"gap_type={gap_type}; topic={topic[:60]}; cue={cue[:80]}"


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
    _persist_open_questions()
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
