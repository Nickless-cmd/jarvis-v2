"""Sensory memories — persistent archive of Jarvis's sensory experiences.

Stores visual/audio/atmosphere snapshots with content, mood tone, and
metadata. Embeddings column is reserved for future semantic search; writes
leave it NULL for now.

Table is created on first use via _ensure_sensory_memories_table.
All public functions use the same connect() helper as the main db module
and return plain dicts.
"""
from __future__ import annotations

import json as _json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from core.runtime.db import connect

_VALID_MODALITIES = {"visual", "audio", "atmosphere", "mixed"}


def _scope() -> str:
    """Bruger-id til streng per-bruger-scope (#154). "" = ingen scope (fallback)."""
    from core.services.user_scope import scope_uid
    return scope_uid()


def _scope_ids() -> tuple[str, ...]:
    """Alle user_id-former der hører til den aktuelle bruger.

    Hvorfor ikke bare ``_scope()`` (målt 22/10-2026, uddybet 23/10-2026):
    ``scope_uid()`` returnerer ``current_user_id()`` når den er sat, ellers
    ``get_owner_discord_id()`` — altså det RÅ Discord-id. Kø-skrivevejen
    (``memory_write_queue`` → ``resolve_canonical_identity``) kanoniserer
    derimod til DB-``user_id``. Tabellen endte derfor med to identiteter for
    samme person, og en læsning scopet til den ene kunne ikke se den anden:
    3.156 råt-scopede poster mod 44 kanoniske (alle natrutine 14/10→22/10).
    ``recall_sensory_memories`` svarede 3.134 mens tabellen havde 3.179.

    Læs derfor på tværs af aliasserne i stedet for at migrere ~324k rækker på
    ni tabeller: det gør de kanoniske poster læsbare NU uden at gøre de
    råt-scopede blinde. Migrering er en separat beslutning om datahygiejne,
    ikke en forudsætning for at arkivet kan læses.

    Rækkefølgen er ikke vilkårlig: ``resolve`` FØRST (rå id → kanonisk),
    derefter ``aliases`` på det kanoniske — ``aliases()`` på et råt id giver
    kun sig selv, fordi det ikke står som ``user_id`` i ``users``.
    """
    raw = _scope()
    if not raw:
        return ()
    try:
        from core.services.routine_migration import (
            canonical_identity_aliases,
            resolve_canonical_identity,
        )

        canonical = resolve_canonical_identity(raw) or raw
        return canonical_identity_aliases(canonical) or (canonical,)
    except Exception:
        # En ulæselig alias-kæde må aldrig gøre arkivet tomt — fald tilbage til
        # den ene identitet vi faktisk har. Snævrere, ikke bredere.
        return (raw,)


def _scope_clause(clauses: list[str], params: list[object]) -> None:
    """Tilføj ``user_id IN (...)`` for alle brugerens identiteter, hvis nogen."""
    ids = _scope_ids()
    if ids:
        clauses.append(f"user_id IN ({','.join('?' * len(ids))})")
        params.extend(ids)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ensure_sensory_memories_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sensory_memories (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            modality TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            embedding TEXT,
            mood_tone TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            user_id TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sensory_memories_ts "
        "ON sensory_memories (timestamp DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sensory_memories_modality "
        "ON sensory_memories (modality, timestamp DESC)"
    )


def insert_sensory_memory(
    *,
    modality: str,
    content: str,
    mood_tone: str | None = None,
    metadata: dict | None = None,
    embedding: list[float] | None = None,
    timestamp: str | None = None,
) -> dict[str, object]:
    if modality not in _VALID_MODALITIES:
        raise ValueError(
            f"invalid modality {modality!r}; must be one of {sorted(_VALID_MODALITIES)}"
        )
    memory_id = uuid4().hex
    ts = timestamp or _now_iso()
    meta_str = _json.dumps(metadata or {}, ensure_ascii=False)
    emb_str = _json.dumps(embedding) if embedding else None
    with connect() as conn:
        _ensure_sensory_memories_table(conn)
        conn.execute(
            """INSERT INTO sensory_memories
               (id, timestamp, modality, content, embedding, mood_tone, metadata_json, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (memory_id, ts, modality, content, emb_str, mood_tone, meta_str, _scope() or None),
        )
    return {
        "id": memory_id,
        "timestamp": ts,
        "modality": modality,
        "content": content,
        "mood_tone": mood_tone,
        "metadata": metadata or {},
    }


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    try:
        metadata = _json.loads(row["metadata_json"] or "{}")
    except Exception:
        metadata = {}
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "modality": row["modality"],
        "content": row["content"],
        "mood_tone": row["mood_tone"],
        "metadata": metadata,
    }


def list_sensory_memories(
    *,
    modality: str | None = None,
    limit: int = 50,
    offset: int = 0,
    since: str | None = None,
) -> list[dict[str, object]]:
    clauses: list[str] = []
    params: list[object] = []
    _scope_clause(clauses, params)
    if modality:
        clauses.append("modality = ?")
        params.append(modality)
    if since:
        clauses.append("timestamp >= ?")
        params.append(since)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([int(limit), int(offset)])
    with connect() as conn:
        _ensure_sensory_memories_table(conn)
        rows = conn.execute(
            f"SELECT * FROM sensory_memories{where} "
            "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def search_sensory_memories(
    *,
    query: str,
    modality: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Simple LIKE-based substring search over content and mood_tone.

    Semantic search via embeddings is not yet implemented; leave the
    embedding column unused for now. Callers that care about ranking
    should pass a short, specific query.
    """
    like = f"%{query.strip()}%"
    clauses = ["(content LIKE ? OR mood_tone LIKE ?)"]
    params: list[object] = [like, like]
    _scope_clause(clauses, params)
    if modality:
        clauses.append("modality = ?")
        params.append(modality)
    params.append(int(limit))
    with connect() as conn:
        _ensure_sensory_memories_table(conn)
        rows = conn.execute(
            f"SELECT * FROM sensory_memories WHERE {' AND '.join(clauses)} "
            "ORDER BY timestamp DESC LIMIT ?",
            params,
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def count_sensory_memories(*, modality: str | None = None) -> int:
    clauses: list[str] = []
    params: list[object] = []
    _scope_clause(clauses, params)
    if modality:
        clauses.append("modality = ?")
        params.append(modality)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        _ensure_sensory_memories_table(conn)
        row = conn.execute(f"SELECT COUNT(*) AS n FROM sensory_memories{where}", params).fetchone()
    return int(row["n"] if row else 0)


def get_sensory_memory(memory_id: str) -> dict[str, object] | None:
    ids = _scope_ids()
    with connect() as conn:
        _ensure_sensory_memories_table(conn)
        if ids:
            row = conn.execute(
                "SELECT * FROM sensory_memories WHERE id = ? "
                f"AND user_id IN ({','.join('?' * len(ids))})",
                (memory_id, *ids),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM sensory_memories WHERE id = ?", (memory_id,)
            ).fetchone()
    return _row_to_dict(row) if row else None
