"""jc_tool_telemetry.py — per-tool eventbus telemetry for jarvis-code's
client-driven tool runs (Fase 5 Task 20).

One responsibility: server telemetry emission for client-owned tool
execution. jarvis-code (the client) runs tools LOCALLY (or forwards a
non-local one to /v1/tools/execute) and reports per-tool
{tool, status, duration_ms, bytes} back to the server in its step envelope
— this module is where that report becomes a real eventbus signal so
Central sees per-tool activity (closes part of the "blind lane": today the
server sees NOTHING about what tools jarvis-code ran locally).

Behind the `jc_tool_telemetry` flag (default OFF, DB-backed runtime flag —
see apps/api/jarvis_api/routes/agent_loop.py `_flag`). Self-safe: any
publish failure is swallowed, never raised — telemetry must never break the
tool call it's reporting on.
"""
from __future__ import annotations

from typing import Any


def publish_tool_step(*, tool: str, status: str, duration_ms: float = 0.0,
                      bytes_: int = 0, user_id: str = "", session_id: str = "") -> bool:
    """Publish one `tool.jc_step` eventbus event. Returns True on a
    best-effort publish (never raises)."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            kind="tool.jc_step",
            payload={
                "tool": tool,
                "status": status,
                "duration_ms": duration_ms,
                "bytes": bytes_,
                "user_id": user_id,
                "session_id": session_id,
            },
        )
        return True
    except Exception:
        return False


def publish_tool_steps(steps: list[dict[str, Any]], *, user_id: str = "",
                       session_id: str = "") -> int:
    """Publish a BATCH of per-tool steps (the client's step envelope may
    report several tool calls in one round). Returns the count actually
    published (best-effort per-item — one failure doesn't drop the rest)."""
    n = 0
    for step in steps or []:
        ok = publish_tool_step(
            tool=str(step.get("tool") or ""),
            status=str(step.get("status") or ""),
            duration_ms=float(step.get("duration_ms") or 0.0),
            bytes_=int(step.get("bytes") or 0),
            user_id=user_id, session_id=session_id,
        )
        if ok:
            n += 1
    return n
