"""Raad paa agentmotoren (agent-contract-v1 F5, spec 5.1 + 7.1 om raad).

Et raad er IKKE en egen runtime: det er et moenster over de almindelige assignments. Tabellen her holder kun
sammenhaengen - hvilke medlems-assignments hoerer til raadet, og hvilket syntese-assignment der blev oprettet
da ALLE medlemmer var terminale. Selve arbejdet, udfaldene og beskederne ligger i assignment/outbox-tabellerne.

    gathering  -> medlemmerne arbejder
    synthesizing -> alle medlemmer er terminale; syntese-assignmentet er oprettet
    done       -> syntesen er terminal
    cancelled  -> raadet kunne ikke samles (intet halvt raad)
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from typing import Any

from core.runtime.db_agent_contract import ContractError, _conn, _now_iso

logger = logging.getLogger(__name__)

GATHERING, SYNTHESIZING, DONE, CANCELLED = "gathering", "synthesizing", "done", "cancelled"


def ensure_council_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_councils (
            council_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            parent_agent_id TEXT NOT NULL DEFAULT '',
            parent_run_id TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL,
            facts TEXT NOT NULL DEFAULT '',
            synthesis_role TEXT NOT NULL DEFAULT 'synthesizer',
            members_json TEXT NOT NULL DEFAULT '[]',
            synthesis_assignment_id TEXT NOT NULL DEFAULT '',
            budget_tokens INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_councils_idem ON agent_councils"
                 "(owner_user_id, origin_session_id, idempotency_key) WHERE idempotency_key != ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_councils_status ON agent_councils(status)")


def _view(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    out = dict(r)
    out["members"] = json.loads(out.pop("members_json") or "[]")
    return out


def create(*, owner_user_id: str, origin_session_id: str, parent_run_id: str, parent_agent_id: str, topic: str,
           facts: str, synthesis_role: str, budget_tokens: int, idempotency_key: str,
           council_id: str | None = None) -> dict[str, Any]:
    cid = council_id or f"council-{uuid.uuid4().hex[:16]}"
    now = _now_iso()
    conn = _conn()
    conn.execute(
        "INSERT INTO agent_councils (council_id, owner_user_id, origin_session_id, parent_agent_id, parent_run_id, "
        "topic, facts, synthesis_role, budget_tokens, idempotency_key, status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (cid, owner_user_id, origin_session_id, parent_agent_id, parent_run_id, topic, facts, synthesis_role,
         int(budget_tokens), idempotency_key, GATHERING, now, now))
    conn.commit()
    return get(cid, owner_user_id) or {}


def get(council_id: str, owner_user_id: str) -> dict[str, Any] | None:
    """Ejerfiltreret: et andet raad end ejerens er ``None``."""
    return _view(_conn().execute("SELECT * FROM agent_councils WHERE council_id=? AND owner_user_id=?",
                                 (council_id, owner_user_id)).fetchone())


def find_by_key(owner_user_id: str, origin_session_id: str, key: str) -> dict[str, Any] | None:
    if not key:
        return None
    return _view(_conn().execute(
        "SELECT * FROM agent_councils WHERE owner_user_id=? AND origin_session_id=? AND idempotency_key=?",
        (owner_user_id, origin_session_id, key)).fetchone())


def set_members(council_id: str, members: list[dict[str, Any]]) -> None:
    conn = _conn()
    conn.execute("UPDATE agent_councils SET members_json=?, updated_at=? WHERE council_id=?",
                 (json.dumps(members, ensure_ascii=False), _now_iso(), council_id))
    conn.commit()


def transition(council_id: str, *, frm: str, to: str, synthesis_assignment_id: str = "") -> bool:
    """Atomisk statusskifte; ``False`` hvis en anden supervisor allerede har flyttet raadet."""
    conn = _conn()
    cur = conn.execute("UPDATE agent_councils SET status=?, synthesis_assignment_id=CASE WHEN ?!='' THEN ? "
                       "ELSE synthesis_assignment_id END, updated_at=? WHERE council_id=? AND status=?",
                       (to, synthesis_assignment_id, synthesis_assignment_id, _now_iso(), council_id, frm))
    conn.commit()
    return cur.rowcount == 1


def open_councils() -> list[dict[str, Any]]:
    rows = _conn().execute("SELECT * FROM agent_councils WHERE status IN (?,?) ORDER BY created_at",
                           (GATHERING, SYNTHESIZING)).fetchall()
    return [_view(r) for r in rows]  # type: ignore[misc]


def require(council_id: str, owner_user_id: str) -> dict[str, Any]:
    c = get(council_id, owner_user_id)
    if c is None:
        raise ContractError("INVALID_SCOPE", "ukendt raad")
    return c
