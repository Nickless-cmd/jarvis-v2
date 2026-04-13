"""Dream insight daemon — persists dream articulation output as private brain records.

L1: When the dream articulation cycle produces a new output, this daemon persists it
as a 'dream-insight' record in private brain. Jarvis wakes up with an insight he didn't
have yesterday.

This is a lightweight wrapper — it doesn't generate new content; it persists what the
existing dream_articulation.py already produces.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BUFFER_MAX = 10

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_insight: str = ""
_insight_buffer: list[str] = []
_last_persisted_signal_id: str = ""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_dream_insight_daemon(*, signal_id: str, signal_summary: str) -> dict:
    """Persist a dream articulation result if it's new.

    signal_id: unique id from dream_articulation result
    signal_summary: the generated dream hypothesis text
    """
    global _last_insight, _insight_buffer, _last_persisted_signal_id

    if not signal_id or not signal_summary:
        return {"persisted": False}

    if signal_id == _last_persisted_signal_id:
        return {"persisted": False}

    _last_insight = signal_summary
    _insight_buffer.insert(0, signal_summary)
    if len(_insight_buffer) > _BUFFER_MAX:
        _insight_buffer = _insight_buffer[:_BUFFER_MAX]
    _last_persisted_signal_id = signal_id

    now_iso = datetime.now(UTC).isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-dream-insight-{uuid4().hex[:12]}",
            record_type="dream-insight",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"dream-insight-daemon-{uuid4().hex[:12]}",
            focus="drøm-indsigt",
            summary=signal_summary[:300],
            detail=signal_id,
            source_signals="dream-articulation:dream-insight-daemon",
            confidence="low",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "dream_hypothesis_signal.insight_persisted",
            {"signal_id": signal_id, "summary": signal_summary[:100]},
        )
    except Exception:
        pass

    return {"persisted": True, "insight": signal_summary}


def get_latest_dream_insight() -> str:
    return _last_insight


def build_dream_insight_surface() -> dict:
    return {
        "latest_insight": _last_insight,
        "insight_buffer": _insight_buffer[:_BUFFER_MAX],
        "last_persisted_signal_id": _last_persisted_signal_id,
    }
