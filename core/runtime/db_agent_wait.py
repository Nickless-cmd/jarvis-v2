"""Ventekontrakter og brugerstop-spaerre for agent-contract-v1 (B2, §6).

En parent registrerer FOER sit run slutter hvilke assignments den venter paa og
hvornaar den skal vaekkes (`first_terminal` / `all_terminal`). Kontrakten
tjekkes straks ved registrering og atomisk ved hvert terminalcommit
(`evaluate_in_tx` koeres i commit-transaktionens egen forbindelse). Et opfyldt
ventepunkt faar PRAECIS én vaekning, ogsaa naar flere boern slutter samtidigt:
overgangen `registered -> fired` er en CAS inde i en BEGIN IMMEDIATE.

Et manuelt brugerstop skrives som en varig markoer for parentens run FOER
afbrydelsen sendes; det spaerrer registrerede kontrakter og aflyser en endnu
ikke startet vaekning. Resultaterne bliver i inbox (B1) og vaekker ingen.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from typing import Any

from core.runtime.db_agent_contract import (
    ASSIGNMENT_TERMINAL, ContractError, _conn, _now_iso, _require, _row)

logger = logging.getLogger(__name__)

CONDITIONS = ("first_terminal", "all_terminal")


def ensure_wait_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_wait_contracts (
            contract_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            parent_run_id TEXT NOT NULL DEFAULT '',
            condition TEXT NOT NULL,
            assignment_ids_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'registered',
            wake_task_id TEXT NOT NULL DEFAULT '',
            stop_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            fired_at TEXT NOT NULL DEFAULT ''
        )
        """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_wait_status "
                 "ON agent_wait_contracts(status, parent_run_id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_run_stops (
            run_id TEXT PRIMARY KEY,
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """)


def _satisfied(conn: sqlite3.Connection, ids: list[str], condition: str) -> bool:
    marks = ",".join("?" * len(ids))
    n = conn.execute(
        f"SELECT COUNT(*) FROM agent_assignments WHERE assignment_id IN ({marks}) "
        f"AND status IN ({','.join('?' * len(ASSIGNMENT_TERMINAL))})",
        [*ids, *sorted(ASSIGNMENT_TERMINAL)]).fetchone()[0]
    return n >= 1 if condition == "first_terminal" else n == len(ids)


def _fire_if_satisfied(conn: sqlite3.Connection, c: sqlite3.Row) -> bool:
    ids = json.loads(c["assignment_ids_json"])
    if not _satisfied(conn, ids, c["condition"]):
        return False
    now = _now_iso()
    cur = conn.execute(
        "UPDATE agent_wait_contracts SET status='fired', fired_at=?, updated_at=? "
        "WHERE contract_id=? AND status='registered'", (now, now, c["contract_id"]))
    return cur.rowcount == 1


def evaluate_in_tx(conn: sqlite3.Connection, assignment_id: str) -> list[str]:
    """Koeres i terminalcommittets transaktion. Returnerer de kontrakter der blev
    opfyldt (`fired`) af netop dette udfald."""
    fired = []
    for c in conn.execute("SELECT * FROM agent_wait_contracts WHERE status='registered' "
                          "AND assignment_ids_json LIKE ?", (f'%"{assignment_id}"%',)).fetchall():
        if assignment_id in json.loads(c["assignment_ids_json"]) and _fire_if_satisfied(conn, c):
            fired.append(c["contract_id"])
    return fired


def register_wait(*, owner_user_id: str, origin_session_id: str, parent_run_id: str,
                  assignment_ids: list[str], condition: str = "all_terminal") -> dict[str, Any]:
    """Registrer hvad parenten venter paa. Hver assignment skal tilhoere samme
    ejer og session. Er parentens run allerede brugerstoppet, registreres
    kontrakten som `stopped` (aldrig en vaekning). Opfyldt allerede nu -> `fired`."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    ids = sorted({str(a).strip() for a in assignment_ids if str(a).strip()})
    if not ids or condition not in CONDITIONS:
        raise ContractError("INVALID_SCOPE", "assignment_ids/condition ugyldig")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        marks = ",".join("?" * len(ids))
        own = conn.execute(
            f"SELECT COUNT(*) FROM agent_assignments WHERE assignment_id IN ({marks}) "
            "AND owner_user_id=? AND origin_session_id=?", [*ids, owner, session]).fetchone()[0]
        if own != len(ids):
            raise ContractError("INVALID_SCOPE", "assignment tilhoerer ikke ejer/session")
        now = _now_iso()
        cid = f"wait-{uuid.uuid4().hex[:16]}"
        stopped = parent_run_id and conn.execute(
            "SELECT reason FROM agent_run_stops WHERE run_id=?", (parent_run_id,)).fetchone()
        status = "stopped" if stopped else "registered"
        conn.execute(
            "INSERT INTO agent_wait_contracts (contract_id, owner_user_id, origin_session_id, "
            "parent_run_id, condition, assignment_ids_json, status, stop_reason, created_at, "
            "updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, owner, session, parent_run_id, condition, json.dumps(ids), status,
             stopped["reason"] if stopped else "", now, now))
        if status == "registered":
            c = conn.execute("SELECT * FROM agent_wait_contracts WHERE contract_id=?",
                             (cid,)).fetchone()
            _fire_if_satisfied(conn, c)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    out = get_contract(cid)
    materialize_pending_wakes()
    return get_contract(cid) or out


def get_contract(contract_id: str) -> dict[str, Any] | None:
    return _row(_conn().execute("SELECT * FROM agent_wait_contracts WHERE contract_id=?",
                                (contract_id,)).fetchone())


def materialize_pending_wakes() -> list[str]:
    """Skriv vaekke-intentionen for hver `fired` kontrakt uden en. Idempotent og
    crash-sikker: DB-commitet sker foer filen, og en forsvundet skrivning tages
    op her ved naeste kald (dispatcherens tick)."""
    from core.services.agent_wake_intentions import stage_wake, wake_message

    done = []
    conn = _conn()
    for c in conn.execute("SELECT * FROM agent_wait_contracts WHERE status='fired' "
                          "AND wake_task_id=''").fetchall():
        task = f"agentwake-{c['contract_id']}"
        try:
            out = stage_wake(
                task_id=task, session_id=c["origin_session_id"], owner_user_id=c["owner_user_id"],
                parent_run_id=c["parent_run_id"],
                message=wake_message(condition=c["condition"],
                                     assignment_ids=json.loads(c["assignment_ids_json"])))
        except Exception:
            logger.warning("kunne ikke skrive vaekning for %s", c["contract_id"], exc_info=True)
            continue
        conn.execute("UPDATE agent_wait_contracts SET wake_task_id=?, updated_at=? "
                     "WHERE contract_id=? AND wake_task_id=''",
                     (out["task_id"], _now_iso(), c["contract_id"]))
        conn.commit()
        done.append(c["contract_id"])
    return done


def block_wakes_for_run(*, run_id: str, reason: str = "user-cancelled") -> dict[str, int]:
    """Manuelt brugerstop af parentens run: skriv markoeren FOER afbrydelsen,
    spaer registrerede kontrakter og aflys vaekninger der ikke er startet."""
    run_id = (run_id or "").strip()
    if not run_id:
        return {"blocked": 0, "cancelled": 0}
    from core.services.agent_wake_intentions import cancel_pending_wake

    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        now = _now_iso()
        conn.execute("INSERT OR IGNORE INTO agent_run_stops (run_id, reason, created_at) "
                     "VALUES (?,?,?)", (run_id, reason, now))
        blocked = conn.execute(
            "UPDATE agent_wait_contracts SET status='stopped', stop_reason=?, updated_at=? "
            "WHERE parent_run_id=? AND (status='registered' OR (status='fired' AND "
            "wake_task_id=''))", (reason, now, run_id)).rowcount
        tasks = [r["wake_task_id"] for r in conn.execute(
            "SELECT wake_task_id FROM agent_wait_contracts WHERE parent_run_id=? "
            "AND status='fired' AND wake_task_id!=''", (run_id,)).fetchall()]
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    cancelled = sum(1 for t in tasks if cancel_pending_wake(t, reason=f"brugerstop: {reason}"))
    return {"blocked": int(blocked), "cancelled": cancelled}
