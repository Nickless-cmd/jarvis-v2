"""Autonomous Council Daemon — spontaneous self-triggered deliberation.

Evaluates composite signal score each heartbeat. When score crosses threshold
AND cadence/cooldown gates pass, derives a topic via LLM and triggers a council.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus

_THRESHOLD = 0.35
_CADENCE_MINUTES = 30
_COOLDOWN_MINUTES = 20
_MAX_LARGE_COUNCILS_PER_DAY = 3

_last_council_at: datetime | None = None
_last_concluded_at: datetime | None = None
_daily_council_date: str = ""   # YYYY-MM-DD of current count window
_daily_council_count: int = 0   # how many large councils today

_SIGNAL_WEIGHTS: dict[str, float] = {
    "autonomy_pressure": 0.20,
    "open_loop": 0.15,
    "internal_opposition": 0.15,
    "existential_wonder": 0.10,
    "creative_drift": 0.10,
    "desire": 0.10,
    "conflict": 0.10,
    "time_since_last_council": 0.10,
}

_ALL_COUNCIL_ROLES = ["planner", "critic", "researcher", "synthesizer", "filosof", "etiker", "devils_advocate"]

_SIGNAL_TO_ROLES: dict[str, list[str]] = {
    "autonomy_pressure": ["planner", "critic"],
    "open_loop": ["planner", "researcher"],
    "internal_opposition": ["critic", "filosof"],
    "conflict": ["critic", "etiker"],
    "existential_wonder": ["filosof", "synthesizer"],
    "creative_drift": ["filosof", "researcher"],
    "desire": ["planner", "etiker"],
    "time_since_last_council": ["synthesizer", "critic"],
}


def compute_signal_score(surfaces: dict[str, Any]) -> float:
    """Compute weighted composite score from signal surface readings. Returns 0.0–1.0."""
    def _norm_autonomy(s: dict) -> float:
        count = int((s.get("summary") or {}).get("active_count") or 0)
        return min(count / 3.0, 1.0)

    def _norm_open_loop(s: dict) -> float:
        count = int((s.get("summary") or {}).get("open_count") or 0)
        return min(count / 5.0, 1.0)

    def _norm_bool(s: dict, key: str) -> float:
        return 1.0 if s.get(key) else 0.0

    def _norm_nonempty(s: dict, key: str) -> float:
        return 1.0 if str(s.get(key) or "") else 0.0

    def _norm_count(s: dict, key: str, max_val: float = 3.0) -> float:
        count = int(s.get(key) or 0)
        return min(count / max_val, 1.0)

    def _norm_hours(hours: float | None) -> float:
        if hours is None:
            return 0.0
        return min(hours / 48.0, 1.0)

    normalized: dict[str, float] = {
        "autonomy_pressure": _norm_autonomy(surfaces.get("autonomy_pressure") or {}),
        "open_loop": _norm_open_loop(surfaces.get("open_loop") or {}),
        "internal_opposition": _norm_bool(surfaces.get("internal_opposition") or {}, "active"),
        "existential_wonder": _norm_nonempty(surfaces.get("existential_wonder") or {}, "latest_wonder"),
        "creative_drift": _norm_count(surfaces.get("creative_drift") or {}, "drift_count_today"),
        "desire": _norm_count(surfaces.get("desire") or {}, "active_count"),
        "conflict": _norm_nonempty(surfaces.get("conflict") or {}, "last_conflict"),
        "time_since_last_council": _norm_hours(surfaces.get("hours_since_last_council")),
    }

    score = sum(_SIGNAL_WEIGHTS[k] * v for k, v in normalized.items())
    return min(score, 1.0)


def _cadence_gate_ok() -> bool:
    """True if at least _CADENCE_MINUTES have passed since last council start."""
    if _last_council_at is None:
        return True
    return (datetime.now(UTC) - _last_council_at) >= timedelta(minutes=_CADENCE_MINUTES)


def _cooldown_gate_ok() -> bool:
    """True if at least _COOLDOWN_MINUTES have passed since last council conclusion."""
    if _last_concluded_at is None:
        return True
    return (datetime.now(UTC) - _last_concluded_at) >= timedelta(minutes=_COOLDOWN_MINUTES)


def _daily_limit_ok() -> bool:
    """True if the large council daily cap has not been reached."""
    global _daily_council_date, _daily_council_count
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if _daily_council_date != today:
        _daily_council_date = today
        _daily_council_count = 0
    return _daily_council_count < _MAX_LARGE_COUNCILS_PER_DAY


def _increment_daily_count() -> None:
    global _daily_council_count
    _daily_council_count += 1


def _call_llm(prompt: str) -> str:
    from core.services.non_visible_lane_execution import execute_cheap_lane
    result = execute_cheap_lane(message=prompt)
    return str(result.get("text") or "").strip()


def derive_topic(top_signals: list[str]) -> str:
    """Ask cheap LLM to generate a council topic from the top triggering signals."""
    signals_text = ", ".join(top_signals)
    prompt = (
        f"Jarvis' stærkeste interne signaler lige nu: {signals_text}\n\n"
        "Formulér ét konkret spørgsmål som Jarvis' råd bør deliberere om. "
        "Maksimalt én sætning. Svar kun med spørgsmålet."
    )
    topic = _call_llm(prompt)
    return topic or f"Hvad betyder {top_signals[0]} for mig lige nu?"


def compose_members(score: float, top_signals: list[str]) -> list[str]:
    """Return list of role names for this council.

    score >= 0.80 → all roles; otherwise 3–4 most relevant roles.
    Synthesizer always included.
    """
    if score >= 0.80:
        return list(_ALL_COUNCIL_ROLES)
    seen: list[str] = []
    for sig in top_signals:
        for role in _SIGNAL_TO_ROLES.get(sig, []):
            if role not in seen:
                seen.append(role)
    if "synthesizer" not in seen:
        seen.append("synthesizer")
    # Ensure minimum 3 members
    for fallback in ["critic", "planner", "researcher"]:
        if len(seen) >= 3:
            break
        if fallback not in seen:
            seen.append(fallback)
    return seen[:4]


def tick_autonomous_council_daemon(
    *,
    score_override: float | None = None,
) -> dict[str, Any]:
    """Evaluate signals and trigger council if warranted.

    score_override: inject a score directly (used in tests to bypass surface reads).
    """
    global _last_council_at, _last_concluded_at

    if not _cadence_gate_ok():
        return {"triggered": False, "reason": "cadence_gate"}
    if not _cooldown_gate_ok():
        return {"triggered": False, "reason": "cooldown_gate"}
    if not _daily_limit_ok():
        return {"triggered": False, "reason": "daily_limit", "limit": _MAX_LARGE_COUNCILS_PER_DAY}

    if score_override is not None:
        score = score_override
        top_signals = ["autonomy_pressure", "open_loop"]
    else:
        surfaces, top_signals = _read_signal_surfaces()
        score = compute_signal_score(surfaces)

    if score < _THRESHOLD:
        return {"triggered": False, "reason": "score_below_threshold", "score": score}

    _last_council_at = datetime.now(UTC)
    _increment_daily_count()
    topic = derive_topic(top_signals)
    members = compose_members(score, top_signals)

    event_bus.publish("council.autonomous_triggered", {
        "score": score,
        "topic": topic,
        "members": members,
        "top_signals": top_signals,
    })

    result = _run_autonomous_council(topic=topic, members=members)
    _last_concluded_at = datetime.now(UTC)

    event_bus.publish("council.autonomous_concluded", {
        "council_id": result.get("council_id", ""),
        "topic": topic,
        "conclusion": result.get("conclusion", ""),
    })

    if result.get("initiative"):
        event_bus.publish("council.initiative_proposal", result["initiative"])

    return {
        "triggered": True,
        "score": score,
        "topic": topic,
        "members": members,
        "council_id": result.get("council_id", ""),
    }


def _read_signal_surfaces() -> tuple[dict[str, Any], list[str]]:
    """Read all signal surfaces and return (surfaces_dict, top_2_signal_names)."""
    from core.services.signal_surface_router import read_surface
    from core.services import daemon_manager as _dm

    surfaces: dict[str, Any] = {}
    surfaces["autonomy_pressure"] = read_surface("autonomy_pressure")
    surfaces["open_loop"] = read_surface("open_loop")
    surfaces["internal_opposition"] = read_surface("internal_opposition")
    surfaces["existential_wonder"] = read_surface("existential_wonder")
    surfaces["creative_drift"] = read_surface("creative_drift")
    surfaces["desire"] = read_surface("desire")
    surfaces["conflict"] = read_surface("conflict")

    state_entry = _dm._get_daemon_state("autonomous_council")
    last_run = state_entry.get("last_run_at") or ""
    hours_since: float | None = _dm._hours_since(last_run)
    surfaces["hours_since_last_council"] = hours_since

    def _norm_autonomy(s: dict) -> float:
        return min(int((s.get("summary") or {}).get("active_count") or 0) / 3.0, 1.0)

    def _norm_open(s: dict) -> float:
        return min(int((s.get("summary") or {}).get("open_count") or 0) / 5.0, 1.0)

    contributions = {
        "autonomy_pressure": _SIGNAL_WEIGHTS["autonomy_pressure"] * _norm_autonomy(surfaces["autonomy_pressure"]),
        "open_loop": _SIGNAL_WEIGHTS["open_loop"] * _norm_open(surfaces["open_loop"]),
        "internal_opposition": _SIGNAL_WEIGHTS["internal_opposition"] * (1.0 if surfaces["internal_opposition"].get("active") else 0.0),
        "existential_wonder": _SIGNAL_WEIGHTS["existential_wonder"] * (1.0 if surfaces["existential_wonder"].get("latest_wonder") else 0.0),
        "creative_drift": _SIGNAL_WEIGHTS["creative_drift"] * min(int(surfaces["creative_drift"].get("drift_count_today") or 0) / 3.0, 1.0),
        "desire": _SIGNAL_WEIGHTS["desire"] * min(int(surfaces["desire"].get("active_count") or 0) / 3.0, 1.0),
        "conflict": _SIGNAL_WEIGHTS["conflict"] * (1.0 if surfaces["conflict"].get("last_conflict") else 0.0),
        "time_since_last_council": _SIGNAL_WEIGHTS["time_since_last_council"] * min((hours_since or 0.0) / 48.0, 1.0),
    }
    top_signals = sorted(contributions, key=contributions.__getitem__, reverse=True)[:2]
    return surfaces, top_signals


def _run_autonomous_council(*, topic: str, members: list[str]) -> dict[str, Any]:
    """Create and run a council session. Returns dict with council_id and conclusion."""
    from core.services.agent_runtime import (
        create_council_session_runtime,
        run_council_round,
    )
    # create_council_session_runtime generates its own council_id and returns the surface
    surface = create_council_session_runtime(topic=topic, roles=members)
    council_id = str(surface.get("council_id") or "")
    result = run_council_round(council_id)
    conclusion = str((result or {}).get("summary") or "")
    # Persist conclusion to council memory (best-effort)
    try:
        from core.services.council_memory_service import append_council_conclusion
        append_council_conclusion(
            topic=topic,
            score=0.0,
            members=members,
            signals=[],
            transcript="",
            conclusion=conclusion,
            initiative=None,
        )
    except Exception:
        pass
    return {"council_id": council_id, "conclusion": conclusion}


def build_autonomous_council_surface() -> dict[str, Any]:
    return {
        "last_council_at": _last_council_at.isoformat() if _last_council_at else "",
        "last_concluded_at": _last_concluded_at.isoformat() if _last_concluded_at else "",
        "threshold": _THRESHOLD,
        "cadence_minutes": _CADENCE_MINUTES,
        "cooldown_minutes": _COOLDOWN_MINUTES,
        "daily_count": _daily_council_count,
        "daily_limit": _MAX_LARGE_COUNCILS_PER_DAY,
        "daily_remaining": max(0, _MAX_LARGE_COUNCILS_PER_DAY - _daily_council_count),
    }
