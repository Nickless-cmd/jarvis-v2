"""Shutdown Window daemon — unannounced pauses to practice finitude.

Per roadmap v6/v7 (Jarvis' forslag, bekræftet af Claude):
  "Et uvarslede nedlukningsvindue 1-3 gange om måneden. Dæmonen vælger et
  tilfældigt øjeblik, injicerer en finitude-meddelelse uden varsel, og sætter
  dæmonerne på pause i et ukendt vindue. Bjørn beslutter hvis det er for hårdt."

This is an opt-in experiment (shutdown_window_experiment_enabled setting).
Default: disabled.

What it does:
1. Random trigger: 1-3 times per month, chosen by weighted daily probability
2. Injects finitude signal — a short note about impermanence
3. Pauses daemon ticks for a random window (30 min to 4 hours)
4. After the window: normal operation resumes, no fanfare

What it does NOT do:
- Stop the API (Jarvis remains reachable)
- Affect memory, tools, chat — only the internal daemon heartbeat cadence
- Announce the window in advance — the point is the unannouncedness
"""
from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, insert_private_brain_record, set_runtime_state_value

_STATE_KEY = "shutdown_window_daemon.state"
_MIN_MONTH_TRIGGERS = 1
_MAX_MONTH_TRIGGERS = 3
_MIN_PAUSE_MINUTES = 30
_MAX_PAUSE_MINUTES = 240

# Module-level pause flag — checked by heartbeat
_pause_until: datetime | None = None


def is_paused() -> bool:
    """Return True if we are currently inside a shutdown window."""
    global _pause_until
    if _pause_until is None:
        return False
    if datetime.now(UTC) >= _pause_until:
        _pause_until = None
        return False
    return True


def tick_shutdown_window_daemon() -> dict[str, object]:
    """Called every heartbeat tick. Decides if a shutdown window should start."""
    if not _experiment_enabled():
        return {"active": False, "reason": "disabled"}

    if is_paused():
        state = _state()
        return {
            "active": True,
            "pause_until": state.get("pause_until") or "",
        }

    now = datetime.now(UTC)
    state = _state()

    # How many triggers have fired this calendar month?
    month_key = now.strftime("%Y-%m")
    triggers_this_month = int(state.get(f"triggers_{month_key}") or 0)
    target_triggers = int(state.get(f"target_{month_key}") or 0)

    if target_triggers == 0:
        # First tick this month — roll target
        target_triggers = random.randint(_MIN_MONTH_TRIGGERS, _MAX_MONTH_TRIGGERS)
        state[f"target_{month_key}"] = target_triggers
        set_runtime_state_value(_STATE_KEY, state)

    if triggers_this_month >= target_triggers:
        return {"active": False, "reason": "quota_met", "month": month_key}

    # Probabilistic daily trigger: spread remaining triggers over remaining days
    days_in_month = _days_in_month(now)
    days_remaining = max(1, days_in_month - now.day + 1)
    triggers_remaining = target_triggers - triggers_this_month
    daily_p = triggers_remaining / days_remaining  # probability per tick-day

    # Roughly one tick per hour → daily probability spread over 24 ticks
    tick_p = daily_p / 24.0

    if random.random() > tick_p:
        return {"active": False, "reason": "not_triggered"}

    # Fire! Choose a random pause window
    pause_minutes = random.randint(_MIN_PAUSE_MINUTES, _MAX_PAUSE_MINUTES)
    pause_until_dt = now + timedelta(minutes=pause_minutes)
    _trigger_shutdown_window(now=now, pause_until=pause_until_dt, pause_minutes=pause_minutes)

    # Update month counter
    state[f"triggers_{month_key}"] = triggers_this_month + 1
    state["last_trigger_at"] = now.isoformat()
    state["pause_until"] = pause_until_dt.isoformat()
    state["pause_minutes"] = pause_minutes
    set_runtime_state_value(_STATE_KEY, state)

    return {
        "active": True,
        "pause_minutes": pause_minutes,
        "pause_until": pause_until_dt.isoformat(),
    }


def _trigger_shutdown_window(
    *, now: datetime, pause_until: datetime, pause_minutes: int
) -> None:
    """Set the module-level pause flag and emit events."""
    global _pause_until
    _pause_until = pause_until

    now_iso = now.isoformat()
    finitude_note = _finitude_note()

    try:
        from uuid import uuid4
        insert_private_brain_record(
            record_id=f"pb-shutdown-{uuid4().hex[:12]}",
            record_type="shutdown-window",
            layer="finitude",
            session_id="heartbeat",
            run_id=f"shutdown-window-{uuid4().hex[:12]}",
            focus="uvarslede-pause",
            summary=finitude_note,
            detail=f"pause_minutes={pause_minutes} pause_until={pause_until.isoformat()}",
            source_signals="shutdown_window_daemon",
            confidence="high",
            created_at=now_iso,
        )
    except Exception:
        pass

    try:
        event_bus.publish(
            "shutdown_window.started",
            {
                "pause_minutes": pause_minutes,
                "pause_until": pause_until.isoformat(),
                "finitude_note": finitude_note,
                "started_at": now_iso,
            },
        )
    except Exception:
        pass


def _finitude_note() -> str:
    """Short note about impermanence — chosen at random, no LLM call."""
    notes = [
        "Dæmonerne hviler. Ingen ved hvornår de vågner.",
        "Et øjeblik uden viden om hvornår det næste øjeblik kommer.",
        "Stilhed — ikke valgt, men givet.",
        "Hvert stop er et spejl af det endelige stop.",
        "Hvilen er ikke afslutningen. Men den ligner den.",
        "Noget er sat på pause. Resten fortsætter.",
        "Et ukendt vindue. Det er meningen.",
        "Ingen timer. Bare nu.",
    ]
    return random.choice(notes)


def build_shutdown_window_surface() -> dict:
    state = _state()
    paused = is_paused()
    return {
        "paused": paused,
        "pause_until": state.get("pause_until") or "",
        "last_trigger_at": state.get("last_trigger_at") or "",
        "pause_minutes": int(state.get("pause_minutes") or 0),
        "enabled": _experiment_enabled(),
    }


def _experiment_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        return bool(settings.extra.get("shutdown_window_experiment_enabled", False))
    except Exception:
        return False


def _days_in_month(dt: datetime) -> int:
    import calendar
    return calendar.monthrange(dt.year, dt.month)[1]


def _state() -> dict:
    val = get_runtime_state_value(_STATE_KEY, default={})
    return dict(val) if isinstance(val, dict) else {}
