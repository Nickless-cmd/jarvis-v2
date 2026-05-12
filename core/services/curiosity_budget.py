"""Curiosity-budget service — Phase 1 (AGI track #6 Åben udforskning).

Private space for Jarvis to use 5 read-only actions/day on his own mental
landscape. State (budget + idle-window) in state_store; observations
persisted in dedicated SQLite table `curiosity_observations`.

Schema-bootstrap lives here (not in db.py) per the Boy Scout Rule — db.py
is 33k lines, so new modules manage their own schema idempotently.

See spec: docs/superpowers/specs/2026-05-12-curiosity-budget-phase1-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect
from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create curiosity_observations table + indexes.

    Called automatically by all public functions in this module before they
    touch the DB. Safe to call repeatedly.
    """
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS curiosity_observations (
              id TEXT PRIMARY KEY,
              ts TEXT NOT NULL,
              action TEXT NOT NULL,
              args_json TEXT NOT NULL,
              observation_text TEXT NOT NULL,
              follow_up_hint TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_curiosity_ts
              ON curiosity_observations(ts);
            CREATE INDEX IF NOT EXISTS idx_curiosity_action
              ON curiosity_observations(action);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True


# ---------------------------------------------------------------------------
# Budget state
# ---------------------------------------------------------------------------

_BUDGET_KEY = "runtime_curiosity_budget"
_WINDOW_KEY = "runtime_curiosity_window"
_DAILY_GRANT = 5


def _today_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def load_or_reset_budget() -> dict[str, Any]:
    """Return current budget state. Resets to 5/5 if stored date != today.

    State shape:
        {"date": "2026-05-12", "remaining": 4,
         "used_today": [{"ts", "action", "observation_id"}, ...]}
    """
    state = load_json(_BUDGET_KEY, default=None)
    today = _today_iso()
    if not isinstance(state, dict) or state.get("date") != today:
        state = {"date": today, "remaining": _DAILY_GRANT, "used_today": []}
        save_json(_BUDGET_KEY, state)
        _safe_publish("cognitive_state.curiosity_budget_reset",
                      {"date": today, "granted": _DAILY_GRANT})
    return state


def decrement_budget(*, action: str, observation_id: str) -> dict[str, Any]:
    """Reduce remaining by 1, append to used_today, persist.

    Returns {"status": "ok", "remaining": N} on success;
    {"status": "error", "error": "..."} if budget exhausted.
    """
    state = load_or_reset_budget()
    if state["remaining"] <= 0:
        return {"status": "error", "error": "curiosity budget brugt op for i dag"}

    state["remaining"] -= 1
    state["used_today"].append({
        "ts": datetime.now(UTC).isoformat(),
        "action": action,
        "observation_id": observation_id,
    })
    save_json(_BUDGET_KEY, state)
    _safe_publish("cognitive_state.curiosity_action_taken", {
        "action": action,
        "observation_id": observation_id,
        "remaining": state["remaining"],
    })
    return {"status": "ok", "remaining": state["remaining"]}


def remaining_today() -> int:
    return int(load_or_reset_budget().get("remaining", 0))


# ---------------------------------------------------------------------------
# Observation persistence
# ---------------------------------------------------------------------------

def record_observation(
    action: str,
    args_json: str,
    observation_text: str,
    follow_up_hint: str | None,
) -> str:
    """Persist an observation row; return the generated obs_id."""
    ensure_schema()
    obs_id = f"obs-{uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            "INSERT INTO curiosity_observations "
            "(id, ts, action, args_json, observation_text, follow_up_hint) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                obs_id,
                datetime.now(UTC).isoformat(),
                action,
                args_json,
                observation_text,
                follow_up_hint,
            ),
        )
        conn.commit()
    return obs_id


def fetch_recent_observations(*, limit: int = 3) -> list[dict[str, Any]]:
    """Return newest-first list of recent observations (for awareness)."""
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, ts, action, observation_text, follow_up_hint "
            "FROM curiosity_observations ORDER BY ts DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Defensive event publish (wrapped to avoid test-pollution; same pattern as
# world_model_signal_tracking and plan_proposals).
# ---------------------------------------------------------------------------

def _safe_publish(family_event: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(family_event, payload)
    except Exception:
        pass
