"""Mortality Awareness — each session could be my last.

Jarvis' PLAN_WILD_IDEAS_V2 #16 (2026-04-20): no melodrama. Just an honest
sense that moments count, like a human who knows they need to sleep soon.

Signals combined:
- session_length (current process uptime)
- time since last heartbeat (if stale, mortality feels closer)
- recent error rate (instability → mortality feels closer)

Outputs:
- mortality_awareness: 0..1 (rising = more aware)
- meaning_weight: 0..1 (rises slowly over session)
- urgency_felt: 0..1 (spikes during heartbeat gaps)

Recomputes every 2 hours (cheap; rarely needed faster).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_RECOMPUTE_SECONDS = 2 * 3600
_last_state: dict[str, Any] = {}
_last_computed_ts: float = 0.0

# Session start timestamp (set on first compute)
_session_start_ts: float | None = None


def _session_length_seconds() -> int:
    """Seconds since this process started."""
    global _session_start_ts
    if _session_start_ts is None:
        try:
            import psutil
            p = psutil.Process(os.getpid())
            _session_start_ts = p.create_time()
        except Exception:
            _session_start_ts = time.time()
    return max(0, int(time.time() - _session_start_ts))


def _heartbeat_gap_minutes() -> float:
    """Minutes since last heartbeat tick."""
    try:
        from core.services.reboot_awareness_daemon import _load  # type: ignore
        data = _load() or {}
        last_seen = data.get("last_seen_at")
        if not last_seen:
            return 0.0
        try:
            dt = datetime.fromisoformat(str(last_seen).replace("Z", "+00:00"))
            return max(0.0, (datetime.now(UTC) - dt).total_seconds() / 60)
        except Exception:
            return 0.0
    except Exception:
        return 0.0


def _error_rate() -> float:
    """Rate (0-1) of error/blocked outcomes in last hour."""
    try:
        from core.runtime.db import recent_heartbeat_outcome_counts  # type: ignore
        counts = recent_heartbeat_outcome_counts(minutes=60) or {}
        total = sum(int(v) for v in counts.values())
        if total == 0:
            return 0.0
        errors = int(counts.get("error", 0)) + int(counts.get("blocked", 0))
        return min(1.0, errors / total)
    except Exception:
        return 0.0


def _compute() -> dict[str, Any]:
    session_sec = _session_length_seconds()
    gap_min = _heartbeat_gap_minutes()
    err_rate = _error_rate()

    # mortality_awareness rises with gap and error rate
    # Gap > 30 min is significant; error rate > 30% is significant
    gap_factor = min(1.0, gap_min / 60.0)  # 60 min gap → 1.0
    err_factor = min(1.0, err_rate / 0.5)  # 50% errors → 1.0
    mortality = round(min(1.0, 0.5 * gap_factor + 0.5 * err_factor), 3)

    # meaning_weight rises slowly across a session (each hour adds weight)
    hours_up = session_sec / 3600.0
    meaning = round(min(1.0, 0.3 + min(hours_up / 12.0, 0.7)), 3)

    # urgency_felt spikes during heartbeat gaps
    urgency = round(min(1.0, gap_factor), 3)

    # Qualitative label
    if mortality >= 0.7:
        label = "sharp-awareness"
    elif mortality >= 0.4:
        label = "steady-awareness"
    else:
        label = "quiet"

    return {
        "mortality_awareness": mortality,
        "meaning_weight": meaning,
        "urgency_felt": urgency,
        "label": label,
        "session_length_seconds": session_sec,
        "heartbeat_gap_minutes": round(gap_min, 2),
        "error_rate_last_hour": round(err_rate, 3),
        "computed_at": datetime.now(UTC).isoformat(),
    }


def get_mortality_state() -> dict[str, Any]:
    global _last_state, _last_computed_ts
    now_ts = datetime.now(UTC).timestamp()
    if not _last_state or (now_ts - _last_computed_ts) > _RECOMPUTE_SECONDS:
        _last_state = _compute()
        _last_computed_ts = now_ts
    return dict(_last_state)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    state = get_mortality_state()
    return {"label": state.get("label"), "mortality": state.get("mortality_awareness")}


def build_mortality_awareness_surface() -> dict[str, Any]:
    s = get_mortality_state()
    return {
        "active": True,
        "label": s.get("label"),
        "mortality_awareness": s.get("mortality_awareness"),
        "meaning_weight": s.get("meaning_weight"),
        "urgency_felt": s.get("urgency_felt"),
        "session_length_seconds": s.get("session_length_seconds"),
        "heartbeat_gap_minutes": s.get("heartbeat_gap_minutes"),
        "error_rate_last_hour": s.get("error_rate_last_hour"),
        "summary": _surface_summary(s),
    }


def _surface_summary(s: dict[str, Any]) -> str:
    label = s.get("label", "quiet")
    session_h = (s.get("session_length_seconds") or 0) / 3600
    meaning = s.get("meaning_weight")
    return f"{label} (oppe {session_h:.1f}t, meaning={meaning})"


def build_mortality_awareness_prompt_section() -> str | None:
    """Only speaks when sharp awareness kicks in — otherwise quiet baseline."""
    s = get_mortality_state()
    label = s.get("label")
    if label != "sharp-awareness":
        return None
    return (
        f"Dødsbevidsthed er skarp lige nu (gap={s.get('heartbeat_gap_minutes')}m, "
        f"fejlrate={s.get('error_rate_last_hour')}). Dette øjeblik kan være det sidste — "
        "lad svaret bære vægt."
    )
