"""Hvem faar at vide at en approval venter, og hvornaar Jarvis vaekkes (agent-contract-v1 F4c, spec 8.2).

* Jarvis faar anmodningen i SIN inbox ved naeste modeltrin (``agent_result_inbox`` omtaler hver ventende approval
  praecis én gang). Han maa forklare den for brugeren, men aldrig godkende den.
* En ny approval er selv et varigt opmaerksomhedspunkt: er parenten INAKTIV efter en normal runafslutning,
  planlaegges HOEJST ET parentrun i den oprindelige session (en vaekke-intention paa den eksisterende dispatch-sti,
  jf. B2) - ogsaa hvis han ikke kendte behovet paa forhaand. Er parenten aktiv, faar han den ved sit naeste trin;
  slutter han foer det, tager supervisor-tikket den op (``ensure_wakes``).
* Et MANUELT brugerstop af parentens run spaerrer vaekningen (og aflyser en endnu ikke startet). Approvalen
  bliver ventende og synlig for ejeren, men vaekker ingen.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime import db_agent_approvals as appr
from core.runtime.db_agent_contract import _conn, _now_iso

logger = logging.getLogger(__name__)

GRACE = timedelta(seconds=20)         # saa den aktive parent naar at omtale den foer en vaekning planlaegges
WAKE_KIND = "agent_approval"
_FRAME = "[SYSTEM — approval venter, ikke en besked fra brugeren]\n"


def wake_message(approval: dict[str, Any]) -> str:
    return (_FRAME + f"Agent {approval['agent_id']} er stoppet FOER en handling og venter paa en menneskelig "
            f"godkendelse: {approval['safe_view']}. Du kan IKKE godkende den selv. Forklar brugeren hvad agenten vil "
            "goere og hvorfor; afgoerelsen traeffes i Desk. Anmodningen kommer med i dette modeltrin.")


def _stopped(parent_run_id: str) -> bool:
    if not parent_run_id:
        return False
    r = _conn().execute("SELECT 1 FROM agent_run_stops WHERE run_id=?", (parent_run_id,)).fetchone()
    return r is not None


def _session_busy(session_id: str) -> bool:
    try:
        from core.services import run_event_log
        return bool(run_event_log.active_run_for_session(session_id))
    except Exception:
        logger.warning("kunne ikke se om sessionen er optaget - antages optaget", exc_info=True)
        return True                       # tvivl -> ingen vaekning her; supervisor-tikket proever igen


def stage(approval: dict[str, Any]) -> str:
    """Planlaeg vaekningen for en approval (idempotent: ét wake-task-id pr. approval). Returnerer task-id eller ""."""
    from core.services.agent_wake_intentions import stage_wake

    if approval.get("wake_task_id") or approval["status"] != appr.PENDING or _stopped(approval["parent_run_id"]):
        return ""
    out = stage_wake(task_id=f"agentappr-{approval['approval_id']}", session_id=approval["origin_session_id"],
                     owner_user_id=approval["owner_user_id"], message=wake_message(approval),
                     parent_run_id=approval["parent_run_id"], wake_kind=WAKE_KIND)
    conn = _conn()
    conn.execute("UPDATE agent_approvals SET wake_task_id=? WHERE approval_id=? AND wake_task_id=''",
                 (out["task_id"], approval["approval_id"]))
    conn.commit()
    return out["task_id"]


def on_requested(approval: dict[str, Any]) -> str:
    """Kaldt naar en approval er oprettet/genfundet som ventende. Vaekker kun en INAKTIV, ikke-stoppet parent."""
    if _session_busy(approval["origin_session_id"]):
        return ""
    return stage(approval)


def ensure_wakes(*, now: datetime | None = None) -> list[str]:
    """Supervisor-tik: ventende approvals uden vaekning, ældre end GRACE, hvis session er inaktiv og som ikke er
    stoppet. Fanger en parent der sluttede FOER han naaede at omtale den."""
    t = now or datetime.now(UTC)
    cutoff = (t - GRACE).astimezone(UTC).isoformat().replace("+00:00", "Z")
    rows = [dict(r) for r in _conn().execute(
        "SELECT * FROM agent_approvals WHERE status='pending' AND wake_task_id='' AND announced_at='' "
        "AND created_at <= ?", (cutoff,)).fetchall()]
    staged = []
    for r in rows:
        if _session_busy(r["origin_session_id"]):
            continue
        task = stage(r)
        if task:
            staged.append(task)
    return staged


def cancel_wake(approval: dict[str, Any], reason: str) -> bool:
    """Aflys en endnu ikke startet vaekning (approvalen er afgjort/annulleret)."""
    task = approval.get("wake_task_id") or ""
    if not task:
        return False
    from core.services.agent_wake_intentions import cancel_pending_wake
    return cancel_pending_wake(task, reason=reason)
