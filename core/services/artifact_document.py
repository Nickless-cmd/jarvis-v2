"""Persistent, versioned documents for the chat canvas."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime import db_core


class DocumentNotFound(LookupError):
    pass


class VersionConflict(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_artifact_documents (
            document_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT NOT NULL,
            version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_artifact_documents_session "
        "ON chat_artifact_documents(session_id, updated_at DESC)"
    )


def _as_dict(row) -> dict[str, Any]:
    return dict(row)


def create_document(
    *,
    session_id: str,
    title: str,
    content: str,
    content_type: str = "text/markdown",
) -> dict[str, Any]:
    sid = str(session_id or "").strip()
    if not sid:
        raise ValueError("session_id is required")
    document_id = f"doc-{uuid4().hex}"
    now = _now()
    with db_core.connect() as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO chat_artifact_documents
                (document_id, session_id, title, content, content_type,
                 version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                document_id,
                sid,
                str(title or "Untitled document").strip() or "Untitled document",
                str(content or ""),
                str(content_type or "text/markdown").strip() or "text/markdown",
                now,
                now,
            ),
        )
        row = conn.execute(
            "SELECT * FROM chat_artifact_documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()
    return _as_dict(row)


def get_document(document_id: str) -> dict[str, Any] | None:
    did = str(document_id or "").strip()
    if not did:
        return None
    with db_core.connect() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT * FROM chat_artifact_documents WHERE document_id = ?", (did,)
        ).fetchone()
    return _as_dict(row) if row is not None else None


def list_documents(session_id: str) -> list[dict[str, Any]]:
    sid = str(session_id or "").strip()
    if not sid:
        return []
    with db_core.connect() as conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT * FROM chat_artifact_documents WHERE session_id = ? "
            "ORDER BY updated_at DESC, document_id",
            (sid,),
        ).fetchall()
    return [_as_dict(row) for row in rows]


def update_document(
    document_id: str,
    *,
    content: str,
    expected_version: int,
    title: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    did = str(document_id or "").strip()
    if not did:
        raise ValueError("document_id is required")
    version = int(expected_version)
    if version < 1:
        raise ValueError("expected_version must be positive")
    now = _now()
    with db_core.connect() as conn:
        _ensure_table(conn)
        current = conn.execute(
            "SELECT title, content_type FROM chat_artifact_documents WHERE document_id = ?",
            (did,),
        ).fetchone()
        if current is None:
            raise DocumentNotFound(did)
        cursor = conn.execute(
            """
            UPDATE chat_artifact_documents
               SET title = ?, content = ?, content_type = ?,
                   version = version + 1, updated_at = ?
             WHERE document_id = ? AND version = ?
            """,
            (
                str(title).strip() if title is not None else current["title"],
                str(content or ""),
                str(content_type).strip() if content_type is not None else current["content_type"],
                now,
                did,
                version,
            ),
        )
        if cursor.rowcount != 1:
            raise VersionConflict(f"document {did} is not at version {version}")
        row = conn.execute(
            "SELECT * FROM chat_artifact_documents WHERE document_id = ?", (did,)
        ).fetchone()
    return _as_dict(row)
