"""Klient-tool-delegering — udskilt enhed (Boy Scout: holder visible_runs.py lille).

Fase 1 af jarvis-code↔v2-foreningen. Når serverens turn-loop rammer et
execution=="client"-tool (bash/read/write/edit på den forbundne overflades host),
eksekverer serveren det IKKE selv — den emitterer et tool_use (i selve loopet) og
DELEGERER eksekveringen til klienten:

    begin_client_tool(call_id, ...)      # gem pending-state
    <loopet emitterer tool_use over SSE>
    result = await await_client_tool_result(call_id)   # poll til klienten svarer

Klienten kører værktøjet lokalt og POSTer resultatet til
POST /chat/runs/{run_id}/tool-result → resolve_visible_client_tool(call_id, text)
→ pending flippes til resolved → poll'en returnerer result_text.

Spejler approval-gatens emit→pause→poll→resume-mønster (visible_runs.py ~1998),
men i stedet for bruger-godkendelse er det klient-eksekvering vi venter på.
State lever i runtime_state (DB) → cross-worker sikker.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from .run_control_state import (
    _get_visible_client_tool_state,
    _set_visible_client_tool_state,
)

# Samme 5-min-loft som approval-gaten (visible_runs.py:2065). En klient der dør
# midt i en delegeret tool holder ikke loopet i live for evigt.
_CLIENT_TOOL_TIMEOUT_S = 300.0
_POLL_INTERVAL_S = 0.25


def begin_client_tool(
    call_id: str,
    *,
    tool_name: str,
    arguments: dict | None,
    run_id: str,
    session_id: str,
) -> None:
    """Registrér en delegeret klient-tool som pending, før loopet emitterer tool_use."""
    _set_visible_client_tool_state(call_id, {
        "call_id": call_id,
        "status": "pending",
        "tool_name": tool_name,
        "arguments": arguments or {},
        "run_id": run_id,
        "session_id": session_id,
        "created_at": datetime.now(UTC).isoformat(),
    })


async def await_client_tool_result(
    call_id: str,
    *,
    timeout_s: float = _CLIENT_TOOL_TIMEOUT_S,
) -> str | None:
    """Blokér (poll) til klienten leverer resultatet, eller deadline rammes.
    Returnerer result_text ved resolved; None ved expired/denied/timeout.
    Ved timeout markeres state 'expired' (observability) hvis den stadig er pending."""
    deadline = asyncio.get_running_loop().time() + max(0.0, timeout_s)
    while asyncio.get_running_loop().time() < deadline:
        state = _get_visible_client_tool_state(call_id)
        status = str(state.get("status") or "")
        if status == "resolved":
            return str(state.get("result_text") or "")
        if status in {"denied", "expired"}:
            return None
        await asyncio.sleep(_POLL_INTERVAL_S)
    state = _get_visible_client_tool_state(call_id)
    if state and str(state.get("status") or "") == "pending":
        state["status"] = "expired"
        state["expired_at"] = datetime.now(UTC).isoformat()
        _set_visible_client_tool_state(call_id, state)
    return None
