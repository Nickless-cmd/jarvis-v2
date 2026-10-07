"""Tilstandsbesked ved ``outcome_unknown`` og dens afgoerelse (agent-contract-v1 G, spec 6, 9 og 12.2).

Et vaerktoejskald der er startet uden at vaere afsluttet (eller en bro der er tabt) kan have udfoert en skrivning.
Runnet gaar til ``outcome_unknown`` og assignmentet bliver ``waiting``: det maa IKKE afsluttes som succes og
skrivningen maa IKKE genforsoeges automatisk. Parent og Desk skal vide det STRAKS, og det sker her som en
SAERSKILT tilstandsbesked i den varige outbox:

* ``message_kind='state'`` + ``state_code='outcome_unknown'`` er DB-markeringen Desk projicerer fra (ikke tekst);
* ``result_type='outcome_unknown:<run_id>'`` holder den adskilt fra assignmentets ene ``agent_result`` (unik pr.
  assignment og type) - den er aldrig terminalbeskeden og opfylder ingen ventekontrakt;
* den claimes via ``agent_result_inbox`` som alle andre beskeder.

Afgoerelsen (``resolve_outcome_unknown``) kraever et menneske eller en verificering, flytter runnet ud af
``outcome_unknown`` og sender stadig KUN ÉN terminal ``agent_result`` for assignmentet.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from typing import Any

from core.runtime.db_agent_contract import ContractError, _add_columns, _conn, _now_iso, _row

logger = logging.getLogger(__name__)

STATE_CODE = "outcome_unknown"
KIND_STATE = "state"
ACTOR_KINDS = ("human", "verifier")
OUTCOMES = {"completed": "completed", "failed": "failed", "cancelled": "cancelled"}


def ensure_outcome_unknown_columns(conn: sqlite3.Connection) -> None:
    _add_columns(conn, "agent_result_outbox", [
        ("message_kind", "TEXT NOT NULL DEFAULT 'terminal'"),
        ("state_code", "TEXT NOT NULL DEFAULT ''"),
        ("resolved_at", "TEXT NOT NULL DEFAULT ''"),
    ])
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_result_outbox_state "
                 "ON agent_result_outbox(message_kind, state_code, resolved_at)")


def notify_outcome_unknown(conn: sqlite3.Connection, *, assignment_id: str, run_id: str, reason: str,
                           open_tool_calls: int = 0) -> str:
    """Skriv tilstandsbeskeden i kalderens transaktion (samme commit som runnets skift til ``outcome_unknown``).
    Idempotent pr. run. Returnerer ``message_id`` ('' hvis assignmentet er ukendt)."""
    a = conn.execute("SELECT * FROM agent_assignments WHERE assignment_id=?", (assignment_id,)).fetchone()
    if a is None:
        return ""
    mtype = f"{STATE_CODE}:{run_id}"
    have = conn.execute("SELECT message_id FROM agent_result_outbox WHERE assignment_id=? AND result_type=?",
                        (assignment_id, mtype)).fetchone()
    if have is not None:
        return str(have["message_id"])
    now = _now_iso()
    mid = f"msg-{uuid.uuid4().hex[:16]}"
    payload = {"state": STATE_CODE, "status": STATE_CODE, "terminal": False, "retry_allowed": False,
               "agent_id": a["agent_id"], "assignment_id": assignment_id, "run_id": run_id,
               "last_run_id": run_id, "reason": reason[:300], "open_tool_calls": int(open_tool_calls),
               "needs": "verified_or_human_decision"}
    conn.execute(
        "INSERT INTO agent_result_outbox (message_id, assignment_id, result_type, owner_user_id, "
        "origin_session_id, sender_agent_id, recipient_agent_id, parent_run_id, last_run_id, payload_json, "
        "created_at, updated_at, message_kind, state_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (mid, assignment_id, mtype, a["owner_user_id"], a["origin_session_id"], a["agent_id"],
         a["parent_agent_id"], a["parent_run_id"], run_id, json.dumps(payload, ensure_ascii=False), now, now,
         KIND_STATE, STATE_CODE))
    return mid


def publish_outcome_unknown(*, assignment_id: str, run_id: str, agent_id: str, owner_user_id: str) -> None:
    """Live-signal til Desk (efter committet). Bedste indsats: DB-markeringen er sandheden."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("agent.outcome_unknown", {
            "assignment_id": assignment_id, "run_id": run_id, "agent_id": agent_id,
            "owner_user_id": owner_user_id, "retry_allowed": False})
    except Exception:
        logger.debug("agent.outcome_unknown kunne ikke publiceres", exc_info=True)


def is_blocked(agent_id: str) -> bool:
    """Har agentens aabne assignment et uafklaret udfald? Saa maa den IKKE koeres igen (ingen automatisk retry af
    en skrivning der kan vaere udfoert) foer det er afgjort."""
    r = _conn().execute(
        "SELECT 1 FROM agent_assignments a JOIN agent_runs r ON r.assignment_id = a.assignment_id "
        "WHERE a.agent_id=? AND a.status='waiting' AND r.status='outcome_unknown' "
        "AND r.attempt_no = (SELECT MAX(attempt_no) FROM agent_runs WHERE assignment_id=a.assignment_id) LIMIT 1",
        (agent_id,)).fetchone()
    return r is not None


def list_unresolved(*, owner_user_id: str) -> list[dict[str, Any]]:
    """Ejerens uafgjorte ``outcome_unknown``-tilstande (Desk-projektion). Aldrig en andens."""
    rows = _conn().execute(
        "SELECT * FROM agent_result_outbox WHERE owner_user_id=? AND message_kind=? AND state_code=? "
        "AND resolved_at='' ORDER BY created_at", (owner_user_id, KIND_STATE, STATE_CODE)).fetchall()
    return [_row(r) for r in rows]


def resolve_outcome_unknown(*, owner_user_id: str, assignment_id: str, outcome: str, decided_by: str,
                            actor_kind: str, note: str = "") -> dict[str, Any]:
    """Afgoer et uafklaret udfald. Kun et menneske eller en verificering (``actor_kind``) og kun for ejerens egen
    assignment. Runnet forlader ``outcome_unknown`` til det afgjorte udfald, tilstandsbeskeden markeres afgjort,
    og assignmentet faar sin ENE terminalbesked (``commit_terminal_outcome`` er idempotent)."""
    from core.runtime.db_agent_contract import commit_terminal_outcome

    if outcome not in OUTCOMES:
        raise ContractError("INVALID_TRANSITION", f"ukendt udfald {outcome!r}")
    if actor_kind not in ACTOR_KINDS or not str(decided_by or "").strip():
        raise ContractError("POLICY_DENIED", "kun et menneske eller en verificering kan afgoere et uvist udfald")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        a = conn.execute("SELECT * FROM agent_assignments WHERE assignment_id=? AND owner_user_id=?",
                         (assignment_id, owner_user_id)).fetchone()
        if a is None:
            raise ContractError("INVALID_SCOPE", "ukendt assignment for denne ejer")
        run = conn.execute("SELECT * FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no DESC LIMIT 1",
                           (assignment_id,)).fetchone()
        if a["status"] != "waiting" or run is None or run["status"] != "outcome_unknown":
            raise ContractError("INVALID_TRANSITION", "assignmentet har intet uafklaret udfald")
        now = _now_iso()
        run_status = "completed" if outcome == "completed" else outcome
        conn.execute("UPDATE agent_runs SET status=?, failure_reason=?, error_phase='recovery', error_code=?, "
                     "finished_at=?, updated_at=? WHERE run_id=?",
                     (run_status, f"outcome_unknown afgjort ({actor_kind}:{decided_by}): {note}"[:300],
                      "" if outcome == "completed" else "OUTCOME_UNKNOWN", now, now, run["run_id"]))
        conn.execute("UPDATE agent_result_outbox SET resolved_at=?, updated_at=? WHERE assignment_id=? AND "
                     "message_kind=? AND state_code=? AND resolved_at=''", (now, now, assignment_id, KIND_STATE,
                                                                             STATE_CODE))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    summary = f"Uvist udfald afgjort af {actor_kind} {decided_by}: {outcome}. {note}".strip()[:500]
    out = commit_terminal_outcome(
        assignment_id=assignment_id, status=OUTCOMES[outcome], summary=summary,
        error_code="" if outcome == "completed" else "OUTCOME_UNKNOWN", error_phase="recovery",
        last_run_id=run["run_id"])
    return {"resolved": True, "outcome": outcome, "terminal": out}
