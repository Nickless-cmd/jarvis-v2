"""Leverance A af agent-contract-v1: assignment, run-binding og terminal outbox.

Spec: docs/specs/2026-10-07-agentorkestrering-og-subagenter.md §4, §6 og §12.2.

Ansvar: varig sandhed for HVEM der ejer en agent, HVILKEN opgave den fik, og at
ét assignment giver PRÆCIS én terminal `agent_result` til den direkte parent.
Intet her kører en model; modulet er kun DB-kontrakten.

Additiv migration: `agent_registry` og `agent_runs` beholdes, og får nye
kolonner. Eksisterende rækker har INGEN verificerbar ejer og mærkes
`legacy_unscoped` — de backfilles aldrig med Bjørns id (§12.2).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from typing import Any

from core.runtime.db_core import _now_iso, connect

logger = logging.getLogger(__name__)

LEGACY_UNSCOPED = "legacy_unscoped"
CONTRACT_VERSION = "agent-contract-v1"

ASSIGNMENT_OPEN = frozenset({"queued", "active", "waiting"})
ASSIGNMENT_TERMINAL = frozenset({"completed", "failed", "cancelled", "timed_out"})
RESULT_TYPE = "agent_result"
DELIVERY_STATES = ("accepted", "delivered", "claimed_by_model_step", "acknowledged")


class ContractError(Exception):
    """Afvist kald med stabil kode, så adaptere kan svare entydigt."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _add_columns(conn: sqlite3.Connection, table: str, columns: list[tuple[str, str]]) -> None:
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, decl in columns:
        if name not in have:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
            except sqlite3.OperationalError as exc:  # begge units migrerer samme DB
                if "duplicate column" not in str(exc).lower():
                    raise


def ensure_agent_contract_tables(conn: sqlite3.Connection) -> None:
    """Idempotent skema. Kalder `_ensure_agent_runtime_tables` først, så de
    tabeller der udvides findes (hos en frisk DB såvel som den levende)."""
    from core.runtime.db_agent_runtime import _ensure_agent_runtime_tables

    _ensure_agent_runtime_tables(conn)
    _add_columns(conn, "agent_registry", [
        ("owner_user_id", f"TEXT NOT NULL DEFAULT '{LEGACY_UNSCOPED}'"),
        ("owner_session_id", "TEXT NOT NULL DEFAULT ''"),
        ("lifecycle_status", "TEXT NOT NULL DEFAULT 'available'"),
    ])
    _add_columns(conn, "agent_runs", [
        ("assignment_id", "TEXT NOT NULL DEFAULT ''"),
        ("owner_user_id", f"TEXT NOT NULL DEFAULT '{LEGACY_UNSCOPED}'"),
        ("attempt_no", "INTEGER NOT NULL DEFAULT 0"),
        ("error_phase", "TEXT NOT NULL DEFAULT ''"),
        ("error_code", "TEXT NOT NULL DEFAULT ''"),
        ("artifact_path", "TEXT NOT NULL DEFAULT ''"),
    ])
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_assignments (
            assignment_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            parent_agent_id TEXT NOT NULL DEFAULT '',
            parent_run_id TEXT NOT NULL DEFAULT '',
            goal TEXT NOT NULL,
            input_refs_json TEXT NOT NULL DEFAULT '[]',
            expected_result TEXT NOT NULL DEFAULT '',
            target TEXT NOT NULL DEFAULT 'runtime-container',
            deadline_at TEXT NOT NULL DEFAULT '',
            budget_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT NOT NULL DEFAULT '',
            operation TEXT NOT NULL DEFAULT 'dispatch',
            idempotency_key TEXT NOT NULL DEFAULT '',
            request_digest TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'queued',
            outcome_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            terminal_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_assignments_idem
        ON agent_assignments(owner_user_id, origin_session_id, operation, idempotency_key)
        WHERE idempotency_key != ''
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_assignments_agent "
        "ON agent_assignments(agent_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_runs_assignment "
        "ON agent_runs(assignment_id, attempt_no)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_result_outbox (
            message_id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL,
            result_type TEXT NOT NULL DEFAULT 'agent_result',
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            sender_agent_id TEXT NOT NULL,
            recipient_agent_id TEXT NOT NULL,
            parent_run_id TEXT NOT NULL DEFAULT '',
            last_run_id TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL,
            delivery_status TEXT NOT NULL DEFAULT 'accepted',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (assignment_id, result_type)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_result_outbox_recipient "
        "ON agent_result_outbox(owner_user_id, origin_session_id, delivery_status)"
    )
    from core.runtime.db_agent_wait import ensure_wait_tables

    ensure_wait_tables(conn)
    from core.runtime.db_agent_artifacts import ensure_artifact_tables

    ensure_artifact_tables(conn)
    from core.runtime.db_agent_lease import ensure_lease_tables

    ensure_lease_tables(conn)
    from core.services.agent_prompt_layers import ensure_prompt_tables

    ensure_prompt_tables(conn)
    from core.runtime.db_agent_memory import ensure_memory_tables

    ensure_memory_tables(conn)
    from core.services.agent_worktrees import ensure_worktree_tables

    ensure_worktree_tables(conn)
    from core.runtime.db_agent_approvals import ensure_approval_tables

    ensure_approval_tables(conn)


_ENSURED: set[str] = set()


def _conn() -> sqlite3.Connection:
    """Ensure-én-gang-per-proces-og-DB: ellers koster hvert statusskifte 8 DDL-kald."""
    from core.runtime import db_core

    conn = connect()
    key = str(db_core.DB_PATH)
    if key not in _ENSURED:
        ensure_agent_contract_tables(conn)
        conn.commit()
        _ENSURED.add(key)
    return conn


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    return None if r is None else {k: r[k] for k in r.keys()}


def _require(value: str, name: str) -> str:
    value = (value or "").strip()
    if not value or value == LEGACY_UNSCOPED:
        raise ContractError("INVALID_SCOPE", f"{name} mangler eller er ikke verificerbar")
    return value


def _digest(*parts: Any) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def mark_legacy_unscoped() -> dict[str, int]:
    """Gamle rækker uden ejer er allerede mærket via kolonne-default; denne
    tæller dem, så en administrativ læseflade kan vise dem (§12.2)."""
    conn = _conn()
    agents = conn.execute(
        "SELECT COUNT(*) FROM agent_registry WHERE owner_user_id = ?", (LEGACY_UNSCOPED,)
    ).fetchone()[0]
    runs = conn.execute(
        "SELECT COUNT(*) FROM agent_runs WHERE owner_user_id = ?", (LEGACY_UNSCOPED,)
    ).fetchone()[0]
    return {"agents": int(agents), "runs": int(runs)}


def accept_assignment(
    *,
    agent_id: str,
    owner_user_id: str,
    origin_session_id: str,
    goal: str,
    parent_agent_id: str = "",
    parent_run_id: str = "",
    input_refs: list[str] | None = None,
    expected_result: str = "",
    target: str = "runtime-container",
    deadline_at: str = "",
    budget: dict[str, Any] | None = None,
    created_by: str = "",
    operation: str = "dispatch",
    idempotency_key: str = "",
    request_digest: str = "",
) -> dict[str, Any]:
    """Accepter ét assignment atomisk sammen med dets første run.

    Samme idempotens-nøgle inden for (ejer, session, operation) returnerer
    SAMME accept; samme nøgle med andre argumenter afvises. Et afvist kald
    efterlader intet halvt assignment og intet run.
    """
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    if not (goal or "").strip():
        raise ContractError("INVALID_SCOPE", "goal mangler")
    # Kalderen kan angive sin egen digest (service-laget regner den paa ANMODNINGEN,
    # fordi agent_id foedes foerst efter idempotens-opslaget).
    digest = request_digest or _digest(
        agent_id, goal, parent_agent_id, parent_run_id, input_refs or [],
        expected_result, target, deadline_at, budget or {})
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if idempotency_key:
            hit = conn.execute(
                "SELECT * FROM agent_assignments WHERE owner_user_id=? AND "
                "origin_session_id=? AND operation=? AND idempotency_key=?",
                (owner, session, operation, idempotency_key),
            ).fetchone()
            if hit is not None:
                if hit["request_digest"] != digest:
                    raise ContractError("IDEMPOTENCY_CONFLICT", idempotency_key)
                run = conn.execute(
                    "SELECT run_id FROM agent_runs WHERE assignment_id=? "
                    "ORDER BY attempt_no LIMIT 1", (hit["assignment_id"],),
                ).fetchone()
                conn.rollback()
                return {"agent_id": hit["agent_id"], "assignment_id": hit["assignment_id"],
                        "run_id": run["run_id"] if run else "", "status": hit["status"],
                        "replayed": True, "contract_version": CONTRACT_VERSION}
        agent = conn.execute(
            "SELECT owner_user_id, lifecycle_status FROM agent_registry WHERE agent_id=?",
            (agent_id,),
        ).fetchone()
        if agent is None:
            raise ContractError("INVALID_SCOPE", "ukendt agent")
        if agent["owner_user_id"] not in (owner, LEGACY_UNSCOPED):
            raise ContractError("POLICY_DENIED", "agenten tilhører en anden ejer")
        if agent["owner_user_id"] == LEGACY_UNSCOPED:
            raise ContractError("POLICY_DENIED", "legacy_unscoped agent kan ikke dispatches")
        if agent["lifecycle_status"] in ("closing", "closed"):
            raise ContractError("POLICY_DENIED", f"agenten er {agent['lifecycle_status']}")
        busy = conn.execute(
            "SELECT 1 FROM agent_assignments WHERE agent_id=? AND status IN "
            "('queued','active','waiting') LIMIT 1", (agent_id,),
        ).fetchone()
        if busy is not None:
            raise ContractError("CAPACITY", "agenten har allerede et aktivt assignment")
        now = _now_iso()
        assignment_id = f"asg-{uuid.uuid4().hex[:16]}"
        run_id = f"run-{uuid.uuid4().hex[:16]}"
        conn.execute(
            "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id, "
            "origin_session_id, parent_agent_id, parent_run_id, goal, input_refs_json, "
            "expected_result, target, deadline_at, budget_json, created_by, operation, "
            "idempotency_key, request_digest, status, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'queued', ?, ?)",
            (assignment_id, agent_id, owner, session, parent_agent_id, parent_run_id,
             goal, json.dumps(input_refs or []), expected_result, target, deadline_at,
             json.dumps(budget or {}), created_by, operation, idempotency_key, digest,
             now, now),
        )
        conn.execute(
            "INSERT INTO agent_runs (run_id, agent_id, status, assignment_id, "
            "owner_user_id, attempt_no, created_at, updated_at) "
            "VALUES (?,?, 'queued', ?, ?, 1, ?, ?)",
            (run_id, agent_id, assignment_id, owner, now, now),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return {"agent_id": agent_id, "assignment_id": assignment_id, "run_id": run_id,
            "status": "queued", "replayed": False, "contract_version": CONTRACT_VERSION}


def commit_terminal_outcome(
    *,
    assignment_id: str,
    status: str,
    summary: str = "",
    error_code: str = "",
    error_phase: str = "",
    artifact_ref: str = "",
    last_run_id: str = "",
    artifact_error: str = "",
) -> dict[str, Any]:
    """Fastlæg assignmentets samlede udfald OG dets ene terminalbesked i SAMME
    transaktion. Et gentaget kald returnerer den eksisterende besked uden at
    ændre noget: terminale statusser er uforanderlige (§4, §6)."""
    if status not in ASSIGNMENT_TERMINAL:
        raise ContractError("INVALID_TRANSITION", f"{status} er ikke terminal")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        a = conn.execute(
            "SELECT * FROM agent_assignments WHERE assignment_id=?", (assignment_id,)
        ).fetchone()
        if a is None:
            raise ContractError("INVALID_SCOPE", "ukendt assignment")
        existing = conn.execute(
            "SELECT * FROM agent_result_outbox WHERE assignment_id=? AND result_type=?",
            (assignment_id, RESULT_TYPE),
        ).fetchone()
        if a["status"] in ASSIGNMENT_TERMINAL:
            conn.rollback()
            return {"committed": False, "assignment_status": a["status"],
                    "message": _row(existing)}
        last = last_run_id or (conn.execute(
            "SELECT run_id FROM agent_runs WHERE assignment_id=? "
            "ORDER BY attempt_no DESC LIMIT 1", (assignment_id,)).fetchone() or {"run_id": ""}
        )["run_id"]
        attempts = [r["run_id"] for r in conn.execute(
            "SELECT run_id FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no",
            (assignment_id,))]
        now = _now_iso()
        payload = {
            "status": status, "error_code": error_code, "error_phase": error_phase,
            "summary": summary, "agent_id": a["agent_id"], "assignment_id": assignment_id,
            "last_run_id": last, "attempt_run_ids": attempts, "artifact_ref": artifact_ref,
            "artifact_error": artifact_error,
        }
        conn.execute(
            "UPDATE agent_assignments SET status=?, outcome_json=?, terminal_at=?, "
            "updated_at=? WHERE assignment_id=?",
            (status, json.dumps(payload), now, now, assignment_id),
        )
        message_id = f"msg-{uuid.uuid4().hex[:16]}"
        conn.execute(
            "INSERT INTO agent_result_outbox (message_id, assignment_id, result_type, "
            "owner_user_id, origin_session_id, sender_agent_id, recipient_agent_id, "
            "parent_run_id, last_run_id, payload_json, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (message_id, assignment_id, RESULT_TYPE, a["owner_user_id"],
             a["origin_session_id"], a["agent_id"], a["parent_agent_id"],
             a["parent_run_id"], last, json.dumps(payload), now, now),
        )
        from core.runtime.db_agent_wait import evaluate_in_tx
        fired = evaluate_in_tx(conn, assignment_id)  # ventekontrakter, samme transaktion
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    # Agentens egen erindring: deterministisk resume af DETTE assignment, efter committet. En fejl
    # her registreres som hukommelsesfejl og aendrer aldrig udfaldet (§7.2).
    from core.runtime.db_agent_memory import project_summary
    project_summary(assignment_id)
    if fired:
        from core.runtime.db_agent_wait import materialize_pending_wakes
        try:
            materialize_pending_wakes()
        except Exception:
            logger.warning("vaekning kunne ikke skrives nu; tages op af dispatcheren",
                           exc_info=True)
    return {"committed": True, "assignment_status": status,
            "message": _row(conn.execute(
                "SELECT * FROM agent_result_outbox WHERE message_id=?", (message_id,)
            ).fetchone())}


def advance_delivery(*, message_id: str, owner_user_id: str, to_status: str) -> dict[str, Any]:
    """Flyt en terminalbesked fremad i leveringskæden. Kun fremad, kun ejeren."""
    if to_status not in DELIVERY_STATES:
        raise ContractError("INVALID_TRANSITION", to_status)
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        m = conn.execute(
            "SELECT * FROM agent_result_outbox WHERE message_id=? AND owner_user_id=?",
            (message_id, owner_user_id),
        ).fetchone()
        if m is None:
            raise ContractError("INVALID_SCOPE", "ukendt besked for denne ejer")
        if DELIVERY_STATES.index(to_status) <= DELIVERY_STATES.index(m["delivery_status"]):
            conn.rollback()
            return _row(m)  # idempotent: aldrig baglæns, aldrig dobbelt claim
        conn.execute(
            "UPDATE agent_result_outbox SET delivery_status=?, updated_at=? "
            "WHERE message_id=?", (to_status, _now_iso(), message_id),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return _row(_conn().execute(
        "SELECT * FROM agent_result_outbox WHERE message_id=?", (message_id,)).fetchone())


def list_pending_results(*, owner_user_id: str, origin_session_id: str) -> list[dict[str, Any]]:
    """Ubehandlede terminalbeskeder for NETOP denne ejer og session."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    rows = _conn().execute(
        "SELECT * FROM agent_result_outbox WHERE owner_user_id=? AND origin_session_id=? "
        "AND delivery_status != 'acknowledged' ORDER BY created_at", (owner, session),
    ).fetchall()
    return [_row(r) for r in rows]


def get_assignment(*, assignment_id: str, owner_user_id: str) -> dict[str, Any] | None:
    """Ejerfiltreret opslag; en anden ejers assignment er `None`, ikke 403."""
    return _row(_conn().execute(
        "SELECT * FROM agent_assignments WHERE assignment_id=? AND owner_user_id=?",
        (assignment_id, owner_user_id),
    ).fetchone())


# --- A2: kobling til den eksisterende agent-livscyklus -----------------------

# Registry-status -> assignmentets terminale status. `failed` for en
# PERSISTENT agent er et forsoeg, der genplanlaegges med backoff, ikke et
# slutresultat (§6), og saettes derfor ikke her.
_SETTLING = {"completed": "completed", "failed": "failed",
             "cancelled": "cancelled", "expired": "timed_out"}
_ERROR_PHASE = {"failed": "model", "cancelled": "recovery", "expired": "budget"}
_ERROR_CODE = {"failed": "AGENT_FAILED", "cancelled": "CANCELLED", "expired": "TIMED_OUT"}


def bind_agent_owner(*, agent_id: str, owner_user_id: str, owner_session_id: str) -> None:
    """Stempl den autentificerede ejer paa agenten. Skriver kun naar agenten
    endnu er `legacy_unscoped`; en eksisterende ejer ændres aldrig (§4)."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(owner_session_id, "owner_session_id")
    conn = _conn()
    conn.execute(
        "UPDATE agent_registry SET owner_user_id=?, owner_session_id=? "
        "WHERE agent_id=? AND owner_user_id=?", (owner, session, agent_id, LEGACY_UNSCOPED))
    conn.commit()


def queued_contract_run(agent_id: str) -> str:
    """Id på det run accept_assignment forudoprettede og som endnu ikke er startet."""
    r = _conn().execute(
        "SELECT run_id FROM agent_runs WHERE agent_id=? AND assignment_id != '' "
        "AND status='queued' AND started_at='' ORDER BY attempt_no LIMIT 1", (agent_id,),
    ).fetchone()
    return r["run_id"] if r else ""


def adopt_run(*, agent_id: str, run_id: str) -> str:
    """Bind et nyoprettet run til agentens åbne assignment som næste forsøg.
    Returnerer assignment_id, eller "" når agenten ikke har et (legacy-vej)."""
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        run = conn.execute("SELECT assignment_id FROM agent_runs WHERE run_id=?",
                           (run_id,)).fetchone()
        if run is None:
            conn.rollback()
            return ""
        if run["assignment_id"]:
            conn.execute("UPDATE agent_assignments SET status='active', updated_at=? "
                         "WHERE assignment_id=? AND status='queued'",
                         (_now_iso(), run["assignment_id"]))
            conn.commit()
            return run["assignment_id"]
        a = conn.execute(
            "SELECT assignment_id, owner_user_id FROM agent_assignments WHERE agent_id=? "
            "AND status IN ('queued','active','waiting') ORDER BY created_at DESC LIMIT 1",
            (agent_id,)).fetchone()
        if a is None:
            conn.rollback()
            return ""
        n = conn.execute("SELECT COALESCE(MAX(attempt_no),0)+1 FROM agent_runs "
                         "WHERE assignment_id=?", (a["assignment_id"],)).fetchone()[0]
        conn.execute("UPDATE agent_runs SET assignment_id=?, owner_user_id=?, attempt_no=? "
                     "WHERE run_id=?", (a["assignment_id"], a["owner_user_id"], n, run_id))
        conn.execute("UPDATE agent_assignments SET status='active', updated_at=? "
                     "WHERE assignment_id=? AND status='queued'",
                     (_now_iso(), a["assignment_id"]))
        conn.commit()
        return a["assignment_id"]
    except BaseException:
        conn.rollback()
        raise


def settle_agent_status(*, agent_id: str, registry_status: str) -> dict[str, Any] | None:
    """Kaldes når agentens registry-status bliver terminal. Fastlægger det åbne
    assignments udfald og den ene terminalbesked. `None` når intet skal ske."""
    target = _SETTLING.get(registry_status)
    if target is None:
        return None
    from core.runtime.db_agent_lease import scope_is_current
    if not scope_is_current():
        # En worker med udloebet/overtaget lease maa ikke skrive terminal status (§9).
        logger.warning("settle_agent_status afvist for %s: workerens lease er ikke laengere gaeldende",
                       agent_id)
        return None
    conn = _conn()
    agent = conn.execute("SELECT persistent, last_error FROM agent_registry WHERE agent_id=?",
                         (agent_id,)).fetchone()
    if agent is None or (registry_status == "failed" and agent["persistent"]):
        return None
    a = conn.execute("SELECT assignment_id FROM agent_assignments WHERE agent_id=? AND "
                     "status IN ('queued','active','waiting') ORDER BY created_at DESC LIMIT 1",
                     (agent_id,)).fetchone()
    if a is None:
        return None
    reply = conn.execute(
        "SELECT content FROM agent_messages WHERE agent_id=? AND direction='agent->jarvis' "
        "AND kind IN ('result','') ORDER BY created_at DESC LIMIT 1", (agent_id,)).fetchone()
    full = reply["content"] if reply else ""
    owner = conn.execute("SELECT owner_user_id FROM agent_assignments WHERE assignment_id=?",
                         (a["assignment_id"],)).fetchone()["owner_user_id"]
    # Resultatfilen faerdiggoeres FOER den terminale DB-transaktion (§9).
    from core.runtime.db_agent_artifacts import write_terminal_artifacts
    # Skrivende kodeagent: aendringerne (diff, filer, commits) afleveres som artefakter og worktree'et
    # BEVARES - det merges aldrig herfra (§8.1).
    wt_summary = None
    try:
        from core.services.agent_worktrees import snapshot_for_assignment
        wt_summary = snapshot_for_assignment(assignment_id=a["assignment_id"])
    except Exception:
        logger.warning("worktree-aflevering fejlede for %s", a["assignment_id"], exc_info=True)
    art = write_terminal_artifacts(
        agent_id=agent_id, assignment_id=a["assignment_id"], owner_user_id=owner, status=target,
        reply=full, summary=full[:500], error_code=_ERROR_CODE.get(registry_status, ""),
        error_phase=_ERROR_PHASE.get(registry_status, ""), worktree=wt_summary)
    return commit_terminal_outcome(
        assignment_id=a["assignment_id"], status=target, summary=full[:500],
        error_code=_ERROR_CODE.get(registry_status, ""),
        error_phase=_ERROR_PHASE.get(registry_status, ""),
        artifact_ref=art["artifact_ref"], artifact_error=art["artifact_error"],
    )


def claim_pending_results(*, owner_user_id: str, origin_session_id: str) -> list[dict[str, Any]]:
    """Atomisk claim: alle ubehandlede (accepted/delivered) terminalbeskeder for
    netop denne ejer og session flyttes til `claimed_by_model_step` i ÉN
    transaktion og returneres. To samtidige kaldere deler dem aldrig."""
    owner = _require(owner_user_id, "owner_user_id")
    session = _require(origin_session_id, "origin_session_id")
    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute(
            "SELECT * FROM agent_result_outbox WHERE owner_user_id=? AND "
            "origin_session_id=? AND delivery_status IN ('accepted','delivered') "
            "ORDER BY created_at, message_id", (owner, session)).fetchall()
        now = _now_iso()
        for r in rows:
            conn.execute("UPDATE agent_result_outbox SET delivery_status="
                         "'claimed_by_model_step', updated_at=? WHERE message_id=?",
                         (now, r["message_id"]))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    out = []
    for r in rows:
        d = _row(r)
        d["delivery_status"] = "claimed_by_model_step"
        out.append(d)
    return out


# --- F1: opslag til service-laget --------------------------------------------

def find_assignment_by_key(*, owner_user_id: str, origin_session_id: str, operation: str,
                           idempotency_key: str) -> dict[str, Any] | None:
    """Findes der allerede et assignment for netop denne ejer/session/operation/noegle?"""
    if not idempotency_key:
        return None
    return _row(_conn().execute(
        "SELECT * FROM agent_assignments WHERE owner_user_id=? AND origin_session_id=? "
        "AND operation=? AND idempotency_key=?",
        (owner_user_id, origin_session_id, operation, idempotency_key)).fetchone())


def open_assignment_for_agent(agent_id: str) -> dict[str, Any] | None:
    return _row(_conn().execute(
        "SELECT * FROM agent_assignments WHERE agent_id=? AND status IN "
        "('queued','active','waiting') ORDER BY created_at DESC LIMIT 1", (agent_id,)).fetchone())


def count_open_assignments(*, owner_user_id: str = "", parent_agent_id: str = "") -> int:
    """Aabne assignments, globalt eller afgraenset til en ejer / en direkte parent."""
    q = "SELECT COUNT(*) FROM agent_assignments WHERE status IN ('queued','active','waiting')"
    args: list[Any] = []
    if owner_user_id:
        q += " AND owner_user_id=?"
        args.append(owner_user_id)
    if parent_agent_id:
        q += " AND parent_agent_id=?"
        args.append(parent_agent_id)
    return int(_conn().execute(q, args).fetchone()[0])


def set_lifecycle(*, agent_id: str, owner_user_id: str, lifecycle_status: str) -> bool:
    """Agentens livstidsstatus (available/active/suspended/closing/closed). Kun ejeren,
    og `closed` kan aldrig aabnes igen af et almindeligt kald (§4, §12.2)."""
    if lifecycle_status not in ("available", "active", "suspended", "closing", "closed"):
        raise ContractError("INVALID_TRANSITION", lifecycle_status)
    conn = _conn()
    cur = conn.execute(
        "UPDATE agent_registry SET lifecycle_status=? WHERE agent_id=? AND owner_user_id=? "
        "AND lifecycle_status != 'closed'", (lifecycle_status, agent_id, owner_user_id))
    conn.commit()
    return cur.rowcount == 1


def discard_unstarted_assignment(*, agent_id: str, owner_user_id: str) -> bool:
    """Fjern et assignment (og dets agent) der ALDRIG er startet: status ``queued``, ingen terminalbesked,
    intet run med ``started_at``. Bruges naar en admission fejler EFTER accept (f.eks. et worktree der ikke
    kan reserveres), saa et afvist kald ikke efterlader et halvt barn (§11.1). Alt andet afvises."""
    import shutil

    conn = _conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        a = conn.execute("SELECT assignment_id FROM agent_assignments WHERE agent_id=? AND owner_user_id=? "
                         "AND status='queued'", (agent_id, owner_user_id)).fetchall()
        if len(a) != 1:
            conn.rollback()
            return False
        aid = a[0]["assignment_id"]
        started = conn.execute("SELECT 1 FROM agent_runs WHERE assignment_id=? AND started_at != ''",
                               (aid,)).fetchone()
        sent = conn.execute("SELECT 1 FROM agent_result_outbox WHERE assignment_id=?", (aid,)).fetchone()
        others = conn.execute("SELECT 1 FROM agent_assignments WHERE agent_id=? AND assignment_id != ?",
                              (agent_id, aid)).fetchone()
        if started or sent or others:
            conn.rollback()
            return False
        run_ids = [r["run_id"] for r in conn.execute("SELECT run_id FROM agent_runs WHERE assignment_id=?",
                                                     (aid,)).fetchall()]
        for rid in run_ids:
            conn.execute("DELETE FROM agent_artifacts WHERE run_id=?", (rid,))
        conn.execute("DELETE FROM agent_runs WHERE assignment_id=?", (aid,))
        conn.execute("DELETE FROM agent_leases WHERE assignment_id=?", (aid,))
        conn.execute("DELETE FROM agent_assignments WHERE assignment_id=?", (aid,))
        conn.execute("DELETE FROM agent_messages WHERE agent_id=?", (agent_id,))
        conn.execute("DELETE FROM agent_registry WHERE agent_id=? AND owner_user_id=?", (agent_id, owner_user_id))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    from core.runtime.db_agent_artifacts import artifact_root
    shutil.rmtree(artifact_root() / agent_id, ignore_errors=True)
    return True
