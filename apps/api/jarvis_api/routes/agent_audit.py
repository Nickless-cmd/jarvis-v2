"""Agent-audit-trail route (Fase 5 Task 9) — GET /v1/agent/audit.

Per-user/per-tool execution audit log, DISTINCT from the cost-nerve (spend,
not who-ran-what). Rows are written from tools_execute() in agent_loop.py
behind the `jc_audit_trail` flag (default OFF) — this module owns the
owner-only readback endpoint and the write helper both call.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.runtime.db_agent_audit import read_rows, write_row
from core.runtime.db_core import get_runtime_state_value

router = APIRouter()


def _flag(name: str, default: bool = False) -> bool:
    """Mirror agent_loop.py's `_flag` — fail-safe DB-backed runtime flag read."""
    try:
        return bool(get_runtime_state_value(name, default))
    except Exception:
        return default


def record_if_enabled(*, user_id: str, role: str, tool: str,
                      target_summary: str = "", decision: str = "") -> None:
    """Write one audit row IFF `jc_audit_trail` is on. Inert (no-op, no DB
    touch at all) when the flag is off — never raises."""
    if not _flag("jc_audit_trail"):
        return
    try:
        write_row(user_id=user_id, role=role, tool=tool,
                 target_summary=target_summary, decision=decision)
    except Exception:
        pass


@router.get("/v1/agent/audit")
async def agent_audit(user_id: str | None = Query(default=None),
                      limit: int = Query(default=100)) -> dict[str, Any]:
    """Owner-only readback of the audit trail. Non-owner callers get 403."""
    from apps.api.jarvis_api.routes.agent_loop import _resolve_role
    role = _resolve_role()
    if role != "owner":
        raise HTTPException(status_code=403, detail="agent-audit er kun for owner")
    rows = read_rows(user_id=user_id, limit=limit)
    return {"rows": rows, "count": len(rows)}
