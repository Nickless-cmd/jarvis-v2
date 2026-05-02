"""Visible-run control state — udskilt fra visible_runs.py (Boy Scout).

Tightly coupled cluster der håndterer visible-run lifecycle state via
runtime_state-tabellen. Cross-worker sikker (state lever i DB).

Indhold:
  - Key prefixes/constants
  - Run-control state get/set/cancel
  - Active-run state tracker
  - Steer queue (mid-flight intervention via POST /chat/runs/{id}/steer)
  - Approval state get/set

Re-eksporteres fra visible_runs.py så eksisterende
visible_runs._set_visible_approval_state-monkeypatches i tests virker.
"""
from __future__ import annotations
from datetime import UTC, datetime

from core.runtime.db import get_runtime_state_value, set_runtime_state_value


_VISIBLE_RUN_CONTROL_PREFIX = "visible_runs.control."
_VISIBLE_RUN_ACTIVE_KEY = "visible_runs.active_run"
_VISIBLE_RUN_APPROVAL_PREFIX = "visible_runs.approval."


def _visible_run_control_key(run_id: str) -> str:
    return f"{_VISIBLE_RUN_CONTROL_PREFIX}{run_id}"


def _visible_run_approval_key(approval_id: str) -> str:
    return f"{_VISIBLE_RUN_APPROVAL_PREFIX}{approval_id}"


def _set_visible_run_control(run_id: str, payload: dict[str, object]) -> None:
    set_runtime_state_value(_visible_run_control_key(run_id), payload)


def _get_visible_run_control(run_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_control_key(run_id), default={})
    return payload if isinstance(payload, dict) else {}


def _set_active_visible_run(payload: dict[str, object] | None) -> None:
    set_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, payload or {})


def _get_active_visible_run_state() -> dict[str, object]:
    payload = get_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


def _visible_run_cancelled(run_id: str) -> bool:
    return bool(_get_visible_run_control(run_id).get("cancelled"))


def _mark_visible_run_cancelled(run_id: str, *, cancelled: bool = True) -> None:
    state = _get_visible_run_control(run_id)
    if not state:
        return
    state["cancelled"] = cancelled
    state["updated_at"] = datetime.now(UTC).isoformat()
    _set_visible_run_control(run_id, state)


def append_visible_run_steer(run_id: str, content: str) -> bool:
    """Append a mid-flight 'steer' message that the agentic loop will pick
    up between rounds. Cross-worker safe (state lives in DB).

    Used by POST /chat/runs/{run_id}/steer so the user can interject mid
    tool-loop without cancelling — Jarvis sees the steer at the next round
    boundary and either redirects, acknowledges, or stops."""
    state = _get_visible_run_control(run_id)
    if not state:
        return False
    queue = state.get("steers")
    if not isinstance(queue, list):
        queue = []
    queue.append({
        "content": str(content or "").strip(),
        "at": datetime.now(UTC).isoformat(),
        "consumed": False,
    })
    state["steers"] = queue
    state["updated_at"] = datetime.now(UTC).isoformat()
    _set_visible_run_control(run_id, state)
    return True


def consume_visible_run_steers(run_id: str) -> list[dict[str, object]]:
    """Pop unread steers for this run. Marks them consumed in shared state
    so they aren't re-consumed if the loop re-checks."""
    state = _get_visible_run_control(run_id)
    if not state:
        return []
    queue = state.get("steers")
    if not isinstance(queue, list):
        return []
    fresh = [s for s in queue if isinstance(s, dict) and not s.get("consumed")]
    if not fresh:
        return []
    for s in queue:
        if isinstance(s, dict) and not s.get("consumed"):
            s["consumed"] = True
    state["steers"] = queue
    state["updated_at"] = datetime.now(UTC).isoformat()
    _set_visible_run_control(run_id, state)
    return fresh


def _set_visible_approval_state(approval_id: str, payload: dict[str, object]) -> None:
    set_runtime_state_value(_visible_run_approval_key(approval_id), payload)


def _get_visible_approval_state(approval_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_approval_key(approval_id), default={})
    return payload if isinstance(payload, dict) else {}
