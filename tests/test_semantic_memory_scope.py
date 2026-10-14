from __future__ import annotations

import numpy as np


def test_private_embeddings_are_scoped_before_top_k(isolated_runtime, monkeypatch):
    from core.runtime import db
    from core.runtime.db_embeddings import upsert_embedding
    from core.runtime.db_private_brain import _ensure_private_brain_records_table
    from core.services import semantic_memory as semantic

    with db.connect() as conn:
        _ensure_private_brain_records_table(conn)
        for record_id, user_id, status in (
            ("mine-active", "u1", "active"),
            ("mine-archived", "u1", "archived"),
            ("other-active", "u2", "active"),
        ):
            conn.execute(
                "INSERT INTO private_brain_records "
                "(record_id, summary, status, created_at, updated_at, user_id) "
                "VALUES (?, ?, ?, 't', 't', ?)",
                (record_id, record_id, status, user_id),
            )
        conn.commit()
    vectors = {
        "mine-active": np.array([0.8, 0.2], dtype=np.float32),
        "mine-archived": np.array([1.0, 0.0], dtype=np.float32),
        "other-active": np.array([1.0, 0.0], dtype=np.float32),
    }
    for record_id, vector in vectors.items():
        upsert_embedding(
            source_table="private_brain_records", source_id=record_id,
            modality="inner", content_hash=record_id,
            embedding_bytes=semantic._encode_vector(vector), model_version="test",
        )
    monkeypatch.setattr(semantic, "require_private_scope", lambda: "u1")
    monkeypatch.setattr(
        semantic, "_embed_ollama", lambda query: np.array([1.0, 0.0], dtype=np.float32)
    )

    hits = semantic.search(
        "query", source_tables=["private_brain_records"], limit=1, min_score=0
    )
    assert [hit["source_id"] for hit in hits] == ["mine-active"]


def test_recall_memories_omits_unresolvable_hits(monkeypatch):
    from core.tools import recall_memory_tools as tools

    monkeypatch.setattr(tools, "recall_enabled", lambda: True)
    monkeypatch.setattr(tools.semantic_memory, "search", lambda *args, **kwargs: [{
        "source_id": "opaque", "source_table": "private_brain_records",
        "record": None, "score": 1.0,
    }])
    monkeypatch.setattr(tools.semantic_memory, "get_stats", lambda: {})
    assert tools._exec_recall_memories({"query": "x"})["items"] == []
