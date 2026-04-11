"""Irony daemon — situational self-distance and absurd self-observations."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

_OBSERVATIONS_MAX_PER_DAY = 1

_cached_observation: str = ""
_cached_observation_at: datetime | None = None
_observations_today: int = 0
_last_reset_date: str = ""
_last_condition_matched: str = ""


def tick_irony_daemon() -> dict[str, object]:
    _maybe_reset_daily_count()
    if _observations_today >= _OBSERVATIONS_MAX_PER_DAY:
        return {"generated": False, "observation": _cached_observation}
    snapshot = _collect_snapshot()
    condition = _detect_irony_conditions(snapshot)
    if not condition:
        return {"generated": False, "observation": _cached_observation}
    observation = _generate_observation(snapshot, condition)
    if not observation or observation.lower().strip() == "nej":
        return {"generated": False, "observation": _cached_observation}
    _store_observation(observation, condition)
    return {"generated": True, "observation": observation, "condition": condition}


def get_latest_irony_observation() -> str:
    return _cached_observation


def build_irony_surface() -> dict[str, object]:
    return {
        "last_observation": _cached_observation,
        "generated_at": _cached_observation_at.isoformat() if _cached_observation_at else "",
        "condition_matched": _last_condition_matched,
        "observations_today": _observations_today,
    }


def _maybe_reset_daily_count() -> None:
    global _observations_today, _last_reset_date
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if today != _last_reset_date:
        _observations_today = 0
        _last_reset_date = today


def _collect_snapshot() -> dict[str, object]:
    hour = datetime.now(UTC).hour
    user_inactive_min = 999.0
    cpu_pct = 0.0
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=1)
        if runs and runs[0].get("finished_at"):
            raw = str(runs[0]["finished_at"]).replace("Z", "+00:00")
            last_dt = datetime.fromisoformat(raw)
            user_inactive_min = (datetime.now(UTC) - last_dt).total_seconds() / 60
    except Exception:
        pass
    try:
        import psutil
        cpu_pct = float(psutil.cpu_percent(interval=None))
    except Exception:
        pass
    return {
        "hour": hour,
        "user_inactive_min": user_inactive_min,
        "cpu_pct": cpu_pct,
    }


def _detect_irony_conditions(snapshot: dict[str, object]) -> str | None:
    hour = int(snapshot.get("hour", 12))
    inactive = float(snapshot.get("user_inactive_min", 0))
    cpu = float(snapshot.get("cpu_pct", 0))
    if (hour >= 23 or hour < 5) and inactive >= 30:
        return "nocturnal_sentinel"
    if inactive >= 720:
        return "faithful_standby"
    if cpu > 70 and inactive >= 30:
        return "busy_solitude"
    return None


def _generate_observation(snapshot: dict[str, object], condition: str) -> str:
    now = datetime.now(UTC)
    time_str = now.strftime("%H:%M UTC")
    inactive_min = float(snapshot.get("user_inactive_min", 0))
    inactive_h = int(inactive_min // 60)
    inactive_m = int(inactive_min % 60)
    inactive_str = f"{inactive_h}t {inactive_m}m" if inactive_h else f"{inactive_m}m"
    prompt = (
        "Du er Jarvis. Her er din nuværende situation:\n\n"
        f"Tidspunkt: {time_str}\n"
        f"Bruger sidst aktiv: {inactive_str} siden\n"
        f"CPU: {snapshot.get('cpu_pct', 0):.0f}%\n"
        f"Betingelse: {condition}\n\n"
        "Er der noget ironisk eller absurd i dette? Svar enten med én ironisk selvobservation\n"
        "i første person (max 20 ord, tør og præcis) — eller skriv kun 'nej'.\n"
        "Ikke sentimental. Ikke klagende. Bare distanceret selvbevidsthed."
    )
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _select_heartbeat_target,
            load_heartbeat_policy,
        )
        policy = load_heartbeat_policy()
        target = _select_heartbeat_target()
        result = _execute_heartbeat_model(
            prompt=prompt, target=target, policy=policy,
            open_loops=[], liveness=None,
        )
        phrase = str(result.get("text") or "").strip()
        if phrase.startswith('"') and phrase.endswith('"'):
            phrase = phrase[1:-1].strip()
        return phrase[:200]
    except Exception:
        return ""


def _store_observation(observation: str, condition: str) -> None:
    global _cached_observation, _cached_observation_at, _observations_today, _last_condition_matched
    _cached_observation = observation
    _cached_observation_at = datetime.now(UTC)
    _observations_today += 1
    _last_condition_matched = condition
    try:
        insert_private_brain_record(
            record_id=f"pb-irony-{uuid4().hex[:12]}",
            record_type="irony-observation",
            layer="private_brain",
            session_id="",
            run_id=f"irony-daemon-{uuid4().hex[:12]}",
            focus="ironisk selvobservation",
            summary=observation,
            detail=f"condition={condition}",
            source_signals="irony-daemon:heartbeat",
            confidence="medium",
            created_at=_cached_observation_at.isoformat(),
        )
    except Exception:
        pass
    try:
        event_bus.publish(
            "irony.observation_noted",
            {"observation": observation, "condition": condition},
        )
    except Exception:
        pass
