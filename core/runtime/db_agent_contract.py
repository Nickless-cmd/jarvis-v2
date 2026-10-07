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
import sqlite3
import uuid
from typing import Any

from core.runtime.db_core import _now_iso, connect

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
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


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


def _conn() -> sqlite3.Connection:
    conn = connect()
    ensure_agent_contract_tables(conn)
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
    digest = _digest(agent_id, goal, parent_agent_id, parent_run_id, input_refs or [],
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
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
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
