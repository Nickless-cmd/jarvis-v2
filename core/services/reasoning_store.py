"""Reasoning Store — Phase 1 of Generalized Learning.

Automatically captures reasoning conclusions from deep_analyze,
reasoning_classify, self_evaluation, counterfactuals, and agent runs,
and makes them retrievable across sessions via semantic search.

Key design decisions:
- Embeddings stored as JSON float arrays in sqlite (no chromadb dependency)
- Semantic similarity computed at query time via cosine distance
- Eventbus integration: emits 'reasoning.conclusion.captured' on each write
- Killswitch: 'reasoning_store_enabled' setting in runtime.json
- Background daemon compacts stale entries (age > 30 days, low confidence)
"""
from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

_STORE_ENABLED_KEY = "reasoning_store_enabled"
_DEFAULT_TTL_DAYS = 30
_MAX_RECALL_RESULTS = 20


# ── helpers ──────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_table(conn) -> None:
    """Idempotent table creation."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reasoning_conclusions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conclusion_id TEXT NOT NULL UNIQUE DEFAULT (lower(hex(randomblob(16)))),
            source TEXT NOT NULL,
            conclusion_text TEXT NOT NULL,
            context TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0.0,
            embedding_json TEXT NOT NULL DEFAULT '[]',
            source_record_id TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_source "
        "ON reasoning_conclusions(source, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_created "
        "ON reasoning_conclusions(created_at DESC)"
    )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(av * bv for av, bv in zip(a, b, strict=False))
    na = math.sqrt(sum(av * av for av in a))
    nb = math.sqrt(sum(bv * bv for bv in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _parse_embedding(raw: str) -> list[float]:
    """Safely parse embedding JSON, return empty list on failure."""
    try:
        val = json.loads(raw)
        if isinstance(val, list) and all(isinstance(v, (int, float)) for v in val):
            return [float(v) for v in val]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return []


# ── public API ───────────────────────────────────────────────────────────


def capture_conclusion(
    *,
    source: str,
    conclusion_text: str,
    context: str = "",
    confidence: float = 0.0,
    embedding: list[float] | None = None,
    source_record_id: str = "",
    metadata: dict[str, Any] | None = None,
    emit_event: bool = True,
    dedup_key: str = "",
) -> str | None:
    """Store a reasoning conclusion and return its conclusion_id.

    Args:
        source: One of 'deep_analyze', 'reasoning_classify', 'self_evaluation',
            'counterfactual', 'agent_run', 'learning_policy', or custom.
        conclusion_text: The actual insight or conclusion.
        context: What was being analyzed (e.g. function name, question).
        confidence: 0.0-1.0 — self-reported certainty.
        embedding: Optional 384-dim float vector. If omitted, stored as [].
        source_record_id: Optional FK to the originating record.
        metadata: Optional dict for extra structured data.
        emit_event: If True, emit 'reasoning.conclusion.captured' on eventbus.

    Returns:
        conclusion_id string on success, None if store is disabled.
    """
    if not is_enabled():
        return None

    conn = connect()
    try:
        _ensure_table(conn)
        now = _now()
        # dedup_key (plan A): deterministisk conclusion_id + INSERT OR IGNORE, så
        # samme logiske konklusion ikke lagres dobbelt (kilde fyrer to gange, eller
        # både direkte-capture og orchestrator-route). Uden key = som før.
        if dedup_key:
            import hashlib
            cid = "dk_" + hashlib.sha1(f"{source}:{dedup_key}".encode("utf-8")).hexdigest()[:24]
            insert_sql = "INSERT OR IGNORE INTO"
        else:
            cid = _now().replace(":", "").replace("-", "") + f"_{source[:16]}"
            insert_sql = "INSERT INTO"
        emb_json = json.dumps(embedding or [], ensure_ascii=False)
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        cur = conn.execute(
            f"""
            {insert_sql} reasoning_conclusions
                (conclusion_id, source, conclusion_text, context,
                 confidence, embedding_json, source_record_id,
                 metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cid, source, conclusion_text, context,
             confidence, emb_json, source_record_id,
             meta_json, now),
        )
        conn.commit()
        _inserted = cur.rowcount > 0

        if emit_event and _inserted:
            # 2026-06-08: was event_bus.emit() which doesn't exist —
            # AttributeError waiting to fire the first time emit_event=True
            # is passed. Bus exposes publish() only (async since 2c82d5ba).
            event_bus.publish("reasoning.conclusion.captured", {
                "conclusion_id": cid,
                "source": source,
                "confidence": confidence,
                "conclusion_text": conclusion_text[:200],
            })

        return cid
    finally:
        conn.close()


def recall_reasoning(
    *,
    query_text: str | None = None,
    query_embedding: list[float] | None = None,
    source_filter: str | None = None,
    min_confidence: float = 0.0,
    limit: int = 10,
    days_back: int | None = 30,
) -> list[dict[str, Any]]:
    """Retrieve stored reasoning conclusions, ranked by relevance.

    If query_text or query_embedding is provided, conclusions are scored
    by cosine similarity against the stored embedding. Only rows with a
    non-empty embedding vector participate in similarity sorting;
    all rows are returned as a fallback.

    Args:
        query_text: Natural language query (embedding computed at call time
            if no query_embedding given — caller should compute externally).
        query_embedding: Pre-computed embedding vector.
        source_filter: Optional source type filter.
        min_confidence: Minimum confidence threshold (0.0-1.0).
        limit: Max results (default 10, max 20).
        days_back: Max age in days (None = no limit).

    Returns:
        List of dicts with keys: conclusion_id, source, conclusion_text,
        context, confidence, source_record_id, metadata_json, created_at,
        and 'score' (0.0-1.0) if similarity was computed.
    """
    if not is_enabled():
        return []

    conn = connect()
    try:
        _ensure_table(conn)
        where_clauses: list[str] = []
        params: list[Any] = []

        if source_filter:
            where_clauses.append("source = ?")
            params.append(source_filter)

        if min_confidence > 0:
            where_clauses.append("confidence >= ?")
            params.append(min_confidence)

        if days_back is not None:
            cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()
            where_clauses.append("created_at >= ?")
            params.append(cutoff)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        rows = conn.execute(
            f"""
            SELECT conclusion_id, source, conclusion_text, context,
                   confidence, source_record_id, metadata_json, created_at,
                   embedding_json
            FROM reasoning_conclusions
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (*params, min(limit, _MAX_RECALL_RESULTS)),
        ).fetchall()

        # Parse embedding from query if needed
        q_emb: list[float] = query_embedding or []

        results: list[dict[str, Any]] = []
        for row in rows:
            entry = {
                "conclusion_id": row["conclusion_id"],
                "source": row["source"],
                "conclusion_text": row["conclusion_text"],
                "context": row["context"],
                "confidence": row["confidence"],
                "source_record_id": row["source_record_id"],
                "metadata_json": row["metadata_json"],
                "created_at": row["created_at"],
                "score": 0.0,
            }

            if q_emb:
                stored_emb = _parse_embedding(row["embedding_json"])
                if stored_emb:
                    entry["score"] = round(_cosine_similarity(q_emb, stored_emb), 4)

            results.append(entry)

        # Sort by score if we have a query embedding
        if q_emb:
            results.sort(key=lambda r: r["score"], reverse=True)

        return results
    finally:
        conn.close()


def get_recent_conclusions(
    *,
    source: str | None = None,
    limit: int = 10,
    days_back: int = 7,
) -> list[dict[str, Any]]:
    """Quick access to recent conclusions, no embedding scoring."""
    return recall_reasoning(
        source_filter=source,
        limit=limit,
        days_back=days_back,
    )


def is_enabled() -> bool:
    """Check the killswitch setting."""
    from core.runtime.db import get_runtime_state_value
    return bool(get_runtime_state_value(_STORE_ENABLED_KEY, True))


def set_enabled(value: bool) -> None:
    """Set killswitch — toggle reasoning store on/off without restart."""
    from core.runtime.db import set_runtime_state_value
    set_runtime_state_value(_STORE_ENABLED_KEY, value)


def compact_stale(days: int = _DEFAULT_TTL_DAYS, min_confidence: float = 0.1) -> int:
    """Delete stale low-confidence conclusions. Returns count removed."""
    if not is_enabled():
        return 0

    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    conn = connect()
    try:
        _ensure_table(conn)
        result = conn.execute(
            """
            DELETE FROM reasoning_conclusions
            WHERE created_at < ? AND confidence < ?
            """,
            (cutoff, min_confidence),
        )
        conn.commit()
        return result.rowcount
    finally:
        conn.close()


def compute_embedding(text: str) -> list[float]:
    """Compute embedding vector for semantic search.

    Uses the HuggingFace sentence-similarity pipeline via hf_embed.
    Falls back to empty list if unavailable.
    The embedding column in the DB schema is pre-allocated for future
    use when a proper embedding pipeline is connected.
    """
    try:
        from core.tools.hf_inference_tools import _exec_hf_embed
        # hf_embed returns similarity scores, not raw embeddings.
        # For now, this is a placeholder for embedding computation.
        pass
    except Exception:
        pass
    return []
