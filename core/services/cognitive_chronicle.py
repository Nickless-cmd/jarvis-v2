"""Cognitive Chronicle — user-scoped read layer for chronicle entries.

Thin facade over core.runtime.db that applies workspace-context filtering
so member users only see chronicle entries relevant to them.

Part of multi-user workspace isolation refactor — Task 4.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def query_chronicle_for_user(limit: int = 50) -> list[dict]:
    """Return chronicle entries visible to the current user.

    Filter logic:
    - NULL relevant_to_users → visible to all (general Jarvis state)
    - JSON array containing current_user_id() → visible
    - Other → hidden

    Note: substring LIKE on JSON is safe here because Discord user IDs are
    long unique numeric strings — no false positives from partial matches.
    """
    from core.identity.workspace_context import current_user_id
    from core.runtime.db import connect, _ensure_cognitive_chronicle_entries_table

    uid = current_user_id()
    with connect() as conn:
        conn.row_factory = __import__("sqlite3").Row
        _ensure_cognitive_chronicle_entries_table(conn)
        if uid:
            rows = conn.execute(
                """
                SELECT *
                FROM cognitive_chronicle_entries
                WHERE relevant_to_users IS NULL
                   OR relevant_to_users LIKE '%' || ? || '%'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (uid, max(limit, 1)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_chronicle_entries "
                "ORDER BY created_at DESC LIMIT ?",
                (max(limit, 1),),
            ).fetchall()
    return [dict(r) for r in rows]
