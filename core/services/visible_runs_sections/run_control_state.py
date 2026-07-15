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
# Fase 1 (jarvis-code↔v2 forening): pending KLIENT-tool-delegering. Når serverens
# loop rammer et execution=="client"-tool emitteres det som tool_use og loopet
# venter (poll) her, indtil klienten POSTer resultatet via /chat/runs/{id}/tool-result.
# Spejler approval-state-mønstret: pending → resolved|expired, cross-worker via DB.
_VISIBLE_RUN_CLIENT_TOOL_PREFIX = "visible_runs.client_tool."


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


def touch_active_visible_run(run_id: str) -> None:
    """Heartbeat: opdatér last_activity_at i den DELTE active-run state (DB),
    så CROSS-PROCES liveness virker. /chat/active-runs (jarvis-api) kan ikke se
    et autonomt runs in-memory controller (det lever i jarvis-runtime), men kan
    se DB-heartbeat'en. Et levende run kalder denne hvert par sekunder; et dødt
    run holder op → freshness-vinduet udløber → klienten rydder hängende UI.
    Kun hvis det stadig er DETTE runs active-state (undgå at genoplive en afløst).
    """
    state = _get_active_visible_run_state()
    if str(state.get("run_id") or "") != str(run_id):
        return
    state["last_activity_at"] = datetime.now(UTC).isoformat()
    set_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, state)


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


# ── Fase 1: klient-tool-delegering state (spejler approval-state) ─────────────


def _visible_run_client_tool_key(call_id: str) -> str:
    return f"{_VISIBLE_RUN_CLIENT_TOOL_PREFIX}{call_id}"


def _set_visible_client_tool_state(call_id: str, payload: dict[str, object]) -> None:
    """Sæt state for en delegeret klient-tool (cross-worker via DB)."""
    set_runtime_state_value(_visible_run_client_tool_key(call_id), payload)


def _get_visible_client_tool_state(call_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_client_tool_key(call_id), default={})
    return payload if isinstance(payload, dict) else {}


def resolve_visible_client_tool(call_id: str, result_text: str) -> bool:
    """Klienten leverer resultatet af en delegeret tool. Flip pending → resolved
    med result_text, som loopet poller efter. False hvis call_id er ukendt eller
    ikke længere pending (idempotent — dobbelt-post skader ikke). Kaldes af
    POST /chat/runs/{run_id}/tool-result."""
    state = _get_visible_client_tool_state(call_id)
    if not state or str(state.get("status") or "") != "pending":
        return False
    state["status"] = "resolved"
    state["result_text"] = str(result_text or "")
    state["resolved_at"] = datetime.now(UTC).isoformat()
    _set_visible_client_tool_state(call_id, state)
    return True
