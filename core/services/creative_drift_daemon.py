"""Creative drift daemon — generates spontaneous, unexpected ideas unrelated to current tasks.

Different from thought_stream: this is *associative surprise*, not chained reasoning.
Input: thought stream fragments + random sampling. Output: "Jeg tænkte på noget: hvad nu hvis..."
Runs rarely: 30-min cadence, max 3 per day.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from core.services.identity_composer import build_identity_preamble

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_MINUTES = 30
_MAX_PER_DAY = 3
_BUFFER_MAX = 10

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_drift_buffer: list[str] = []
_today_count: int = 0
_today_date: date | None = None

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_creative_drift_daemon(fragments: list[str]) -> dict:
    """Maybe generate a spontaneous associative idea.

    fragments: recent thought-stream fragments (latest first).
    """
    global _last_tick_at, _today_count, _today_date

    now = datetime.now(UTC)
    today = now.date()

    # Reset daily counter on new day
    if _today_date != today:
        _today_count = 0
        _today_date = today

    # Daily cap
    if _today_count >= _MAX_PER_DAY:
        return {"generated": False}

    # Cadence gate
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(minutes=_CADENCE_MINUTES):
            return {"generated": False}

    idea = _generate_drift_idea(fragments)
    if not idea:
        return {"generated": False}

    _store_drift(idea, now)
    _last_tick_at = now
    _today_count += 1

    return {"generated": True, "idea": idea}


def get_latest_drift() -> str:
    return _drift_buffer[0] if _drift_buffer else ""


def build_creative_drift_surface() -> dict:
    return {
        "latest_drift": get_latest_drift(),
        "drift_buffer": _drift_buffer[:_BUFFER_MAX],
        "drift_count_today": _today_count,
        "last_generated_at": _last_tick_at.isoformat() if _last_tick_at else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_drift_idea(fragments: list[str]) -> str:
    fragment_sample = "; ".join(fragments[:3]) if fragments else "ingen fragmenter"
    fallback = "Jeg tænkte på noget: hvad nu hvis tingene er anderledes end de ser ud?"
    try:
        from core.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        prompt = (
            f"{build_identity_preamble()} Du sidder med disse tanker i baggrunden:\n"
            f"\"{fragment_sample}\"\n\n"
            "Lad sindet vandre frit — ikke videre fra ovenstående, men et uventet spring.\n"
            "Formulér én spontan, uventet idé eller association (max 25 ord).\n"
            "Start med: 'Jeg tænkte på noget:' eller 'Hvad nu hvis'\n"
            "Det MÅ IKKE handle om aktuelle opgaver eller fortsætte tanken direkte."
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        text = str(result.get("text") or "").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        return text[:300] if text else fallback
    except Exception:
        return fallback


def _store_drift(idea: str, now: datetime) -> None:
    global _drift_buffer
    _drift_buffer.insert(0, idea)
    if len(_drift_buffer) > _BUFFER_MAX:
        _drift_buffer = _drift_buffer[:_BUFFER_MAX]

    now_iso = now.isoformat()
    try:
        insert_private_brain_record(
            record_id=f"pb-drift-{uuid4().hex[:12]}",
            record_type="creative-drift-signal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"creative-drift-daemon-{uuid4().hex[:12]}",
            focus="kreativ-drift",
            summary=idea,
            detail="",
            source_signals="creative-drift-daemon:thought-stream",
            confidence="low",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "creative_drift.generated",
            {"idea": idea, "generated_at": now_iso},
        )
    except Exception:
        pass
