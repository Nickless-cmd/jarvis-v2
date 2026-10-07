"""Failover som nyt synligt runforsoeg (agent-contract-v1 G, spec 7.1 og 6).

Svigter modellen foer nogen effektfuld handling, proever runtime den naeste tilladte kandidat. Det er et NYT
``agent_runs``-forsoeg i SAMME assignment (``attempt_no`` + 1), og det svigtede forsoeg faar sin egen
fejlpost (``error_phase='model'``, ``error_code='MODEL_FAILOVER'``) - saa et fejlet foerste forsoeg ikke
forsvinder bag et senere.

Et failover er IKKE et udfald: assignmentet forbliver aabent, der skrives ingen terminalbesked (praecis én pr.
assignment, ``commit_terminal_outcome``) og ingen ventekontrakt evalueres, saa parenten ikke vaekkes for tidligt.
Alt sker i ÉN ``BEGIN IMMEDIATE``: fejlpost, nyt run, rute-forsoeg, registeropdatering og prompt-snapshot.
Er arbejderens lease udloebet eller overtaget (fencing-token), skrives intet og ``LEASE_LOST`` rejses.
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_agent_contract import (
    ASSIGNMENT_OPEN, ContractError, _conn, _now_iso, _row)

logger = logging.getLogger(__name__)

FAILOVER_CODE = "MODEL_FAILOVER"
_RUN_OPEN = ("queued", "starting", "running", "active")


def _fence(conn: sqlite3.Connection, assignment_id: str) -> None:
    """Den koerende traads lease skal stadig vaere den gaeldende - tjekket INDE i transaktionen."""
    from core.runtime.db_agent_lease import _parse, _scope

    sc = _scope.get()
    if sc is None:
        return                              # ingen lease i scope (legacy / test) - intet at fence mod
    if sc["lost"].is_set() or sc["assignment_id"] != assignment_id:
        raise ContractError("LEASE_LOST", f"workerens lease for {assignment_id} er ikke gaeldende")
    row = conn.execute("SELECT fencing_token, state, lease_until FROM agent_leases WHERE assignment_id=?",
                       (assignment_id,)).fetchone()
    if not (row and row["state"] == "held" and row["fencing_token"] == sc["token"]
            and _parse(row["lease_until"]) > datetime.now(UTC)):
        sc["lost"].set()
        raise ContractError("LEASE_LOST", f"workerens lease for {assignment_id} er udloebet eller overtaget")


def begin_failover_attempt(*, from_run_id: str, decision: dict[str, Any], reason: str) -> dict[str, Any]:
    """Luk det svigtede forsoeg med en fejlpost og aabn det naeste (nyt ``run_id``, ``attempt_no`` + 1).

    ``decision`` er rutebeslutningen for det nye forsoeg (``provider``/``model``/``route_source``). Returnerer
    ``{"run_id", "attempt_no", "failed_run_id", "assignment_id", "route_attempt"}``."""
    from core.runtime import db_agent_route as route

    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        old = conn.execute("SELECT * FROM agent_runs WHERE run_id=?", (from_run_id,)).fetchone()
        if old is None or not old["assignment_id"]:
            raise ContractError("INVALID_SCOPE", "runnet findes ikke eller har intet assignment")
        aid = old["assignment_id"]
        a = conn.execute("SELECT status, owner_user_id FROM agent_assignments WHERE assignment_id=?",
                         (aid,)).fetchone()
        if a is None or a["status"] not in ASSIGNMENT_OPEN:
            raise ContractError("INVALID_TRANSITION", f"assignmentet er {a['status'] if a else 'ukendt'}")
        _fence(conn, aid)
        last = conn.execute("SELECT run_id, attempt_no FROM agent_runs WHERE assignment_id=? "
                            "ORDER BY attempt_no DESC LIMIT 1", (aid,)).fetchone()
        if last["run_id"] != from_run_id or old["status"] not in _RUN_OPEN:
            raise ContractError("INVALID_TRANSITION", f"{from_run_id} er allerede afsluttet eller afloest")
        now = _now_iso()
        new_id = f"run-{uuid.uuid4().hex[:16]}"
        attempt_no = int(last["attempt_no"]) + 1
        conn.execute("UPDATE agent_runs SET status='failed', failure_reason=?, error_phase='model', "
                     "error_code=?, provider_status='failed', finished_at=?, updated_at=? WHERE run_id=?",
                     (reason[:300], FAILOVER_CODE, now, now, from_run_id))
        conn.execute(
            "INSERT INTO agent_runs (run_id, agent_id, status, execution_mode, provider, model, "
            "input_summary, input_payload_json, started_at, created_at, updated_at, assignment_id, "
            "owner_user_id, attempt_no, policy_hash, policy_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_id, old["agent_id"], "running", old["execution_mode"], decision["provider"],
             decision["model"], old["input_summary"], old["input_payload_json"], now, now, now, aid,
             a["owner_user_id"], attempt_no, old["policy_hash"], old["policy_json"]))
        conn.execute(
            "INSERT OR REPLACE INTO agent_run_prompts (run_id, assignment_id, agent_id, owner_user_id, "
            "delegation_version, role_version, layer_digests_json, effective_text, provider, model, "
            "tool_names_json, tool_schema_sha256, created_at) "
            "SELECT ?, assignment_id, agent_id, owner_user_id, delegation_version, role_version, "
            "layer_digests_json, effective_text, ?, ?, tool_names_json, tool_schema_sha256, ? "
            "FROM agent_run_prompts WHERE run_id=?", (new_id, decision["provider"], decision["model"],
                                                      now, from_run_id))
        n = conn.execute("SELECT COALESCE(MAX(attempt),0)+1 FROM agent_route_decisions WHERE assignment_id=?",
                         (aid,)).fetchone()[0]
        route.record_decision(assignment_id=aid, agent_id=old["agent_id"], owner_user_id=a["owner_user_id"],
                              decision=dict(decision, run_id=new_id, failed_run_id=from_run_id),
                              attempt=int(n), conn=conn)
        conn.execute("UPDATE agent_registry SET provider=?, model=? WHERE agent_id=?",
                     (decision["provider"], decision["model"], old["agent_id"]))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    _write_failed_attempt_artifact(agent_id=old["agent_id"], run_id=from_run_id, assignment_id=aid,
                                   owner=a["owner_user_id"], reason=reason, successor=new_id,
                                   attempt_no=int(last["attempt_no"]))
    return {"run_id": new_id, "attempt_no": attempt_no, "failed_run_id": from_run_id,
            "assignment_id": aid, "route_attempt": int(n)}


def _write_failed_attempt_artifact(*, agent_id: str, run_id: str, assignment_id: str, owner: str,
                                   reason: str, successor: str, attempt_no: int) -> None:
    """``result.json`` for det svigtede forsoeg, saa manifestet viser det. Bedste indsats: en manglende
    artefakt aendrer aldrig failoveret - DB-fejlposten ovenfor er sandheden."""
    import json

    try:
        from core.runtime import db_agent_artifacts as art
        art.write_artifact(
            agent_id=agent_id, run_id=run_id, name="result.json", assignment_id=assignment_id,
            owner_user_id=owner,
            data=json.dumps({"status": "failed_attempt", "attempt_no": attempt_no, "run_id": run_id,
                             "error_phase": "model", "error_code": FAILOVER_CODE, "reason": reason[:300],
                             "successor_run_id": successor, "terminal": False},
                            ensure_ascii=False, indent=2))
    except Exception:
        logger.warning("artefakt for svigtet forsoeg %s kunne ikke gemmes", run_id, exc_info=True)


def live_run_id(run_id: str) -> str:
    """Foelg failover-kaeden fra ``run_id`` til det forsoeg der koerer nu. Et run der ikke er afloest af et
    failover (ogsaa et der er afsluttet af andre grunde) returneres uaendret."""
    rid = str(run_id or "")
    if not rid:
        return rid
    conn = _conn()
    for _ in range(16):                                    # kaeden er kort; loftet beskytter mod en cyklus
        row = conn.execute("SELECT assignment_id, attempt_no, error_code FROM agent_runs WHERE run_id=?",
                           (rid,)).fetchone()
        if row is None or not row["assignment_id"] or row["error_code"] != FAILOVER_CODE:
            return rid
        nxt = conn.execute("SELECT run_id FROM agent_runs WHERE assignment_id=? AND attempt_no=?",
                           (row["assignment_id"], int(row["attempt_no"]) + 1)).fetchone()
        if nxt is None:
            return rid
        rid = nxt["run_id"]
    return rid


def attempts_for_assignment(assignment_id: str) -> list[dict[str, Any]]:
    rows = _conn().execute("SELECT run_id, attempt_no, status, provider, model, error_phase, error_code, "
                           "failure_reason FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no",
                           (assignment_id,)).fetchall()
    return [_row(r) for r in rows]
