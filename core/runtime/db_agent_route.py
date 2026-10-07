"""Varig rute-proveniens for agenter (agent-contract-v1 D, spec 7.1).

Hvert modelvalg gemmes som en raekke pr. FORSOEG: ``attempt`` 1 er valget ved dispatch, hoejere tal er
failover til naeste kandidat. Raekken bærer ``route_source``, den autentificerede ejer, hele
kandidatgrundlaget, afvisningsaarsagerne og den estimerede omkostning, saa "hvorfor koerte agenten paa
den model" kan besvares efter en genstart - ogsaa for en anden ejers agent.

Inde i en BEGIN IMMEDIATE bruges kun den medgivne conn (``connect()`` ruller en aaben transaktion tilbage).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from typing import Any

from core.runtime.db_agent_contract import _conn, _now_iso

logger = logging.getLogger(__name__)

SOURCES = ("explicit", "agent_pool", "owner_deepseek_fallback", "cheap_lane_fallback")


def ensure_route_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_route_decisions (
            decision_id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            attempt INTEGER NOT NULL,
            route_source TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            decision_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (assignment_id, attempt)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_route_agent "
                 "ON agent_route_decisions(agent_id, created_at)")


def record_decision(*, assignment_id: str, agent_id: str, owner_user_id: str,
                    decision: dict[str, Any], attempt: int = 1,
                    conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    source = str(decision.get("route_source") or "")
    if source not in SOURCES:
        raise ValueError(f"ukendt route_source {source!r}")
    own = conn is None
    c = conn or _conn()
    row = {"decision_id": f"rt-{uuid.uuid4().hex}", "assignment_id": assignment_id,
           "agent_id": agent_id, "owner_user_id": owner_user_id, "attempt": int(attempt),
           "route_source": source, "provider": str(decision.get("provider") or ""),
           "model": str(decision.get("model") or ""),
           "decision_json": json.dumps(decision, ensure_ascii=False, default=str),
           "created_at": _now_iso()}
    c.execute("INSERT INTO agent_route_decisions (decision_id, assignment_id, agent_id, owner_user_id, "
              "attempt, route_source, provider, model, decision_json, created_at) "
              "VALUES (:decision_id,:assignment_id,:agent_id,:owner_user_id,:attempt,:route_source,"
              ":provider,:model,:decision_json,:created_at)", row)
    if own:
        c.commit()
    return row


def _view(r: sqlite3.Row) -> dict[str, Any]:
    out = dict(r)
    try:
        out["decision"] = json.loads(out.pop("decision_json") or "{}")
    except ValueError:
        logger.warning("raekke %s har ulaeselig decision_json", out.get("decision_id"))
        out["decision"] = {}
    return out


def attempts_for_assignment(assignment_id: str) -> list[dict[str, Any]]:
    rows = _conn().execute("SELECT * FROM agent_route_decisions WHERE assignment_id=? "
                           "ORDER BY attempt", (assignment_id,)).fetchall()
    return [_view(r) for r in rows]


def latest_for_agent(agent_id: str) -> dict[str, Any] | None:
    """Det SENESTE forsoeg for agentens senest oprettede assignment (None for en legacy-agent)."""
    r = _conn().execute(
        "SELECT d.* FROM agent_route_decisions d JOIN agent_assignments a "
        "ON a.assignment_id = d.assignment_id WHERE d.agent_id=? "
        "ORDER BY a.created_at DESC, d.attempt DESC LIMIT 1", (agent_id,)).fetchone()
    return _view(r) if r else None
