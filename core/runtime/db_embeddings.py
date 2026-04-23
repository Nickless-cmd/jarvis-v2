"""Embeddings store — unified vector index across all memory surfaces.

Stores a single embedding per (source_table, source_id). On re-embed,
the row is overwritten. Embedding payload is stored as raw float32 bytes
so numpy can parse it back cheaply.

Used by core.services.semantic_memory for cross-surface recall.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


def _ensure_memory_embeddings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_embeddings (
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            modality TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            embedding BLOB NOT NULL,
            model_version TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            PRIMARY KEY (source_table, source_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_embeddings_modality "
        "ON memory_embeddings (modality, indexed_at DESC)"
    )


def upsert_embedding(
    *,
    source_table: str,
    source_id: str,
    modality: str,
    content_hash: str,
    embedding_bytes: bytes,
    model_version: str,
) -> None:
    """Insert or overwrite the embedding for a given source row."""
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_memory_embeddings_table(conn)
        conn.execute(
            """
            INSERT INTO memory_embeddings (
                source_table, source_id, modality, content_hash,
                embedding, model_version, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_table, source_id) DO UPDATE SET
                modality = excluded.modality,
                content_hash = excluded.content_hash,
                embedding = excluded.embedding,
                model_version = excluded.model_version,
                indexed_at = excluded.indexed_at
            """,
            (
                source_table,
                source_id,
                modality,
                content_hash,
                embedding_bytes,
                model_version,
                now_iso,
            ),
        )
        conn.commit()


def get_embedding(
    source_table: str, source_id: str
) -> dict[str, Any] | None:
    with connect() as conn:
        _ensure_memory_embeddings_table(conn)
        row = conn.execute(
            "SELECT * FROM memory_embeddings "
            "WHERE source_table = ? AND source_id = ?",
            (source_table, source_id),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def delete_embedding(source_table: str, source_id: str) -> None:
    with connect() as conn:
        _ensure_memory_embeddings_table(conn)
        conn.execute(
            "DELETE FROM memory_embeddings "
            "WHERE source_table = ? AND source_id = ?",
            (source_table, source_id),
        )
        conn.commit()


def list_embeddings(
    *,
    modalities: list[str] | None = None,
    source_tables: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return raw embedding rows (including blobs). Caller decodes."""
    where: list[str] = []
    params: list[Any] = []
    if modalities:
        placeholders = ",".join("?" for _ in modalities)
        where.append(f"modality IN ({placeholders})")
        params.extend(modalities)
    if source_tables:
        placeholders = ",".join("?" for _ in source_tables)
        where.append(f"source_table IN ({placeholders})")
        params.extend(source_tables)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    limit_clause = f"LIMIT {int(limit)}" if limit else ""
    query = (
        f"SELECT * FROM memory_embeddings {clause} "
        f"ORDER BY indexed_at DESC {limit_clause}"
    )
    with connect() as conn:
        _ensure_memory_embeddings_table(conn)
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def count_embeddings(
    *,
    modality: str | None = None,
    source_table: str | None = None,
) -> int:
    where: list[str] = []
    params: list[Any] = []
    if modality:
        where.append("modality = ?")
        params.append(modality)
    if source_table:
        where.append("source_table = ?")
        params.append(source_table)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with connect() as conn:
        _ensure_memory_embeddings_table(conn)
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM memory_embeddings {clause}",
            params,
        ).fetchone()
    return int(row["c"] if row else 0)


def list_indexed_source_ids(source_table: str) -> set[str]:
    """Return the set of source_ids already indexed for a given table."""
    with connect() as conn:
        _ensure_memory_embeddings_table(conn)
        rows = conn.execute(
            "SELECT source_id FROM memory_embeddings WHERE source_table = ?",
            (source_table,),
        ).fetchall()
    return {str(r["source_id"]) for r in rows}
