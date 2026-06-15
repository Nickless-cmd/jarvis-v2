"""Autonomy-proposals — niveau-2 autonomi: pending forslag fra Jarvis der afventer
Bjørns godkendelse (memory-rewrite, source-edit, task-run, …).

Udskilt fra db.py (Boy Scout-reglen, 2026-06-15) — én naturlig sammenhængende
enhed: oprettelse/listing/opslag/resolution af autonomy_proposals + tabel-DDL +
row→dict-helper. Re-eksporteres fra db.py for bagudkompat (call-sites bruger
`from core.runtime.db import create_autonomy_proposal` osv.).

#154: per-bruger-scope — list filtrerer user_id; create stamper scope_uid();
get-by-id er BEVIDST uscopet (approval/execution-pipelinen kører på tværs af
kontekster — enumerering lukkes af list).
"""
from __future__ import annotations

import sqlite3
from typing import Any

from core.runtime.db_core import connect


def _ensure_autonomy_proposals_table(conn: sqlite3.Connection) -> None:
    """Pending proposals from Jarvis awaiting Bjørn approval.

    En proposal er en struktureret anmodning om en afgrænset handling Jarvis
    ikke selv kan udføre (memory rewrite, source edit, task run, …). Felter:
    proposal_id (unik), kind, title, rationale, payload_json, status
    (pending|approved|rejected|executed|expired|cancelled), created/updated/
    resolved_at, created_by, resolved_by, resolution_note, execution_result_json.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomy_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            rationale TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            created_by TEXT NOT NULL DEFAULT '',
            resolved_by TEXT NOT NULL DEFAULT '',
            resolution_note TEXT NOT NULL DEFAULT '',
            execution_result_json TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            tick_id TEXT NOT NULL DEFAULT '',
            canonical_key TEXT NOT NULL DEFAULT '',
            user_id TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_autonomy_proposals_status "
        "ON autonomy_proposals(status, id DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_autonomy_proposals_kind_canonical "
        "ON autonomy_proposals(kind, canonical_key, id DESC)"
    )


def _autonomy_proposal_from_row(row) -> dict[str, Any]:
    import json as _json
    if row is None:
        return {}
    data = dict(row)
    for key in ("payload_json", "execution_result_json"):
        raw = data.get(key) or ""
        if not raw:
            data[key.replace("_json", "")] = {}
            continue
        try:
            data[key.replace("_json", "")] = _json.loads(raw)
        except Exception:
            data[key.replace("_json", "")] = {}
    return data


def create_autonomy_proposal(
    *,
    proposal_id: str,
    kind: str,
    title: str,
    rationale: str = "",
    payload: dict | None = None,
    created_by: str = "",
    session_id: str = "",
    run_id: str = "",
    tick_id: str = "",
    canonical_key: str = "",
) -> dict[str, Any]:
    import json as _json
    from datetime import UTC, datetime as _dt
    now = _dt.now(UTC).isoformat()
    payload_str = _json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    from core.services.user_scope import scope_uid
    with connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO autonomy_proposals (
                proposal_id, kind, title, rationale, payload_json, status,
                created_at, updated_at, created_by, session_id, run_id,
                tick_id, canonical_key, user_id
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal_id, kind, title, rationale, payload_str,
                now, now, created_by, session_id, run_id, tick_id, canonical_key,
                scope_uid() or None,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM autonomy_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
    return _autonomy_proposal_from_row(row) if row else {}


def list_autonomy_proposals(
    *,
    status: str | None = None,
    kind: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    from core.services.user_scope import scope_uid
    query = "SELECT * FROM autonomy_proposals"
    params: list = []
    where: list[str] = []
    _uid = scope_uid()
    if _uid:
        where.append("user_id = ?")  # #154: kun egne forslag
        params.append(_uid)
    if status:
        where.append("status = ?")
        params.append(status)
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(max(int(limit), 1))
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_autonomy_proposal_from_row(row) for row in rows]


def get_autonomy_proposal(proposal_id: str) -> dict[str, Any] | None:
    # Bevidst UScopet: fetch-by-unik-id i approval/execution-pipelinen (kører på
    # tværs af kontekster). Enumererings-leaket lukkes af list_autonomy_proposals.
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM autonomy_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
    return _autonomy_proposal_from_row(row) if row else None


def resolve_autonomy_proposal(
    proposal_id: str,
    *,
    status: str,
    resolved_by: str = "",
    resolution_note: str = "",
    execution_result: dict | None = None,
) -> dict[str, Any] | None:
    import json as _json
    from datetime import UTC, datetime as _dt
    now = _dt.now(UTC).isoformat()
    exec_json = _json.dumps(execution_result or {}, ensure_ascii=False, sort_keys=True) if execution_result else ""
    with connect() as conn:
        conn.execute(
            """
            UPDATE autonomy_proposals
            SET status = ?, resolved_at = ?, updated_at = ?,
                resolved_by = ?, resolution_note = ?, execution_result_json = ?
            WHERE proposal_id = ?
            """,
            (status, now, now, resolved_by, resolution_note, exec_json, proposal_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM autonomy_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
    return _autonomy_proposal_from_row(row) if row else None
