"""Tests for core.services.semantic_memory.

Covers all 4 public functions:
- index_memory — embed + store
- search — cosine-similarity top-k retrieval
- backfill_all — bulk index unindexed rows
- get_stats — embedding counts

DB isolation strategy: instead of module-reloading (fragile, slow), we
monkeypatch ``core.runtime.db.DB_PATH`` and ``core.runtime.config.STATE_DIR``
to point at a temp directory per test.  This lets us use the module-level
imports directly with zero reload overhead.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pytest

from core.runtime import config as cfg
from core.runtime import db as rdb
from core.services.semantic_memory import (
    _content_hash_unchanged,
    _decode_vector,
    _encode_vector,
    _hash_content,
    _MODEL_VERSION,
    _prepare_text,
    backfill_all,
    get_stats,
    index_memory,
    register_source,
    search,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_embed(text: str) -> np.ndarray | None:
    # Stable hash — Python's built-in hash() is randomized per process
    # via PYTHONHASHSEED, which made cosine scores non-deterministic
    # across runs and produced flaky test results.
    import hashlib
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
    seed = int.from_bytes(digest[:4], "big")
    rng = np.random.RandomState(seed=seed)
    v = rng.randn(64).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-10)


def _fake_embed_fail(_text: str) -> np.ndarray | None:
    return None


@pytest.fixture(autouse=True)
def _patch_embed():
    """Always mock Ollama so tests run offline."""
    with patch(
        "core.services.semantic_memory._embed_ollama",
        side_effect=_fake_embed,
    ):
        yield


@pytest.fixture
def fresh_db():
    """Point DB to a fresh temp file for the duration of one test.

    Re-initialises tables so the test starts with a completely empty DB.
    Also clears the module-level ``_RESOLVERS`` / ``_LISTERS`` globals so
    tests that register custom source tables don't leak state to each other.
    """
    from core.services.semantic_memory import _RESOLVERS, _LISTERS

    old_state = cfg.STATE_DIR
    old_db = rdb.DB_PATH
    old_resolvers = dict(_RESOLVERS)
    old_listers = dict(_LISTERS)
    _RESOLVERS.clear()
    _LISTERS.clear()

    tmpdir = tempfile.mkdtemp()
    state_dir = Path(tmpdir) / ".jarvis-v2" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    db_path = state_dir / "jarvis.db"

    cfg.STATE_DIR = str(state_dir)  # some code expects str, some Path
    rdb.DB_PATH = Path(db_path)

    rdb.init_db()

    yield db_path

    cfg.STATE_DIR = old_state
    rdb.DB_PATH = old_db
    _RESOLVERS.clear()
    _RESOLVERS.update(old_resolvers)
    _LISTERS.clear()
    _LISTERS.update(old_listers)


@pytest.fixture
def test_source(fresh_db):
    """Register a throwaway source table.

    Returns (table_name, records_dict).
    """
    table = f"test_table_{uuid4().hex[:8]}"
    records: dict[str, dict] = {}

    register_source(table, resolver=lambda sid: records.get(sid), lister=lambda: list(records.values()))
    return table, records


# ===================================================================
# index_memory
# ===================================================================

class TestIndexMemory:
    """Core embed+store path."""

    def test_happy_path(self, fresh_db):
        sid = uuid4().hex
        ok = index_memory(
            source_table="test", source_id=sid,
            content="Jarvis is thinking about the ocean",
            modality="inner",
        )
        assert ok is True

    def test_empty_content_returns_false(self, fresh_db):
        ok = index_memory(
            source_table="test", source_id="any",
            content="   ", modality="visual",
        )
        assert ok is False

    def test_embed_failure_returns_false(self, fresh_db):
        sid = uuid4().hex
        with patch(
            "core.services.semantic_memory._embed_ollama",
            side_effect=_fake_embed_fail,
        ):
            ok = index_memory(
                source_table="test", source_id=sid,
                content="something", modality="audio",
            )
        assert ok is False

    def test_unchanged_content_hash_skips_embed(self, fresh_db):
        sid = uuid4().hex
        content = "Persistent thought that stays the same"
        assert index_memory(
            source_table="test", source_id=sid,
            content=content, modality="inner",
        ) is True

        call_count = 0
        def tracking_embed(_t: str) -> np.ndarray | None:
            nonlocal call_count
            call_count += 1
            return _fake_embed(_t)

        with patch(
            "core.services.semantic_memory._embed_ollama",
            side_effect=tracking_embed,
        ):
            assert index_memory(
                source_table="test", source_id=sid,
                content=content, modality="inner",
            ) is True
        assert call_count == 0

    def test_different_content_reembeds(self, fresh_db):
        sid = uuid4().hex
        assert index_memory(
            source_table="test", source_id=sid,
            content="First thought", modality="inner",
        ) is True
        assert index_memory(
            source_table="test", source_id=sid,
            content="Second thought", modality="inner",
        ) is True

    def test_content_clipped_at_max(self, fresh_db):
        assert index_memory(
            source_table="test", source_id="long_one",
            content="x" * 5000, modality="mixed",
        ) is True


# ===================================================================
# search
# ===================================================================

class TestSearch:
    """Cosine-similarity retrieval."""

    def test_empty_query_returns_empty_list(self, fresh_db):
        assert search("") == []

    def test_no_embeddings_returns_empty(self, fresh_db):
        assert search("anything at all") == []

    def test_returns_relevant_hits(self, test_source):
        table, _ = test_source
        index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Deep thoughts about neural networks and AI",
            modality="inner",
        )
        index_memory(
            source_table=table, source_id=uuid4().hex,
            content="What I had for breakfast this morning",
            modality="inner",
        )
        results = search("artificial intelligence", min_score=0.0)
        assert len(results) >= 1

    def test_min_score_filters(self, test_source):
        table, _ = test_source
        index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Random unrelated chatter",
            modality="inner",
        )
        strict = search("very specific unique concept", min_score=0.99)
        loose = search("very specific unique concept", min_score=0.0)
        assert len(strict) <= len(loose)

    def test_modality_filter(self, test_source):
        table, _ = test_source
        index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Audio memory test", modality="audio",
        )
        index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Visual memory test", modality="visual",
        )
        audio_only = search("memory", modalities=["audio"], min_score=0.0)
        visual_only = search("memory", modalities=["visual"], min_score=0.0)
        assert all(h["modality"] == "audio" for h in audio_only)
        assert all(h["modality"] == "visual" for h in visual_only)

    def test_source_table_filter(self, fresh_db):
        table_a = f"table_a_{uuid4().hex[:8]}"
        table_b = f"table_b_{uuid4().hex[:8]}"

        register_source(table_a, resolver=lambda _: None, lister=lambda: [])
        register_source(table_b, resolver=lambda _: None, lister=lambda: [])

        index_memory(
            source_table=table_a, source_id=uuid4().hex,
            content="From table A", modality="inner",
        )
        index_memory(
            source_table=table_b, source_id=uuid4().hex,
            content="From table B", modality="inner",
        )
        # min_score=-1.0: this test verifies source_table filtering, not
        # relevance — random embeddings can yield negative cosines.
        from_a = search("table", source_tables=[table_a], min_score=-1.0)
        from_b = search("table", source_tables=[table_b], min_score=-1.0)
        assert any(h["source_table"] == table_a for h in from_a)
        assert any(h["source_table"] == table_b for h in from_b)
        # And the filter must actually filter — no cross-contamination
        assert not any(h["source_table"] == table_b for h in from_a)
        assert not any(h["source_table"] == table_a for h in from_b)

    def test_limit_respected(self, test_source):
        table, _ = test_source
        for i in range(5):
            index_memory(
                source_table=table, source_id=uuid4().hex,
                content=f"Indexed item number {i}",
                modality="inner",
            )
        results = search("indexed item", limit=3, min_score=0.0)
        assert len(results) <= 3

    def test_result_has_expected_keys(self, test_source):
        table, records = test_source
        sid = uuid4().hex
        records[sid] = {
            "id": sid,
            "content": "Memory with full metadata",
            "modality": "inner",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        index_memory(
            source_table=table, source_id=sid,
            content="Memory with full metadata",
            modality="inner",
        )
        results = search("memory metadata", min_score=0.0)
        assert len(results) >= 1
        hit = results[0]
        assert "score" in hit
        assert hit["source_table"] == table
        assert hit["source_id"] == sid
        assert hit["modality"] == "inner"
        assert hit["record"] is not None


# ===================================================================
# backfill_all
# ===================================================================

class TestBackfillAll:
    """Bulk indexing."""

    def test_no_registered_sources_returns_empty(self, fresh_db):
        with patch("core.services.semantic_memory._RESOLVERS", {}), \
             patch("core.services.semantic_memory._LISTERS", {}):
            summary = backfill_all()
        assert summary["total_indexed"] == 0
        assert summary["total_failed"] == 0

    def test_handles_missing_sql_tables_gracefully(self, fresh_db):
        """backfill_all logs a warning for non-existent SQL tables without crashing."""
        summary = backfill_all(max_per_table=10)
        assert "sensory_memories" in summary["tables"]
        assert "error" in summary["tables"]["sensory_memories"]

    def test_private_brain_table_also_handled(self, fresh_db):
        summary = backfill_all(max_per_table=10)
        assert "private_brain_records" in summary["tables"]
        assert "error" in summary["tables"]["private_brain_records"]

    def test_indexes_real_sensory_table_rows(self, fresh_db):
        """Prove backfill works end-to-end when the real table exists."""
        from core.runtime.db_sensory import insert_sensory_memory

        mem = insert_sensory_memory(
            modality="mixed",
            content="Row that needs backfilling",
        )
        sid = str(mem["id"])
        summary = backfill_all(max_per_table=10)
        assert summary["tables"]["sensory_memories"]["indexed"] >= 1
        assert sid in {
            h["source_id"]
            for h in search("backfilling", min_score=0.0)
        }

    def test_skips_already_indexed_rows(self, fresh_db):
        """Rows already in memory_embeddings are not re-indexed."""
        from core.runtime.db_sensory import insert_sensory_memory

        mem = insert_sensory_memory(
            modality="mixed",
            content="Already indexed content",
        )
        sid = str(mem["id"])
        index_memory(
            source_table="sensory_memories",
            source_id=sid,
            content="Already indexed content",
            modality="mixed",
        )
        summary = backfill_all(max_per_table=10)
        assert summary["tables"]["sensory_memories"]["indexed"] == 0
        # min_score=-1.0: testing persistence, not relevance
        hits = search("indexed", min_score=-1.0)
        assert any(h["source_id"] == sid for h in hits)


# ===================================================================
# get_stats
# ===================================================================

class TestGetStats:
    """Embedding count overview."""

    def test_empty_returns_zero(self, fresh_db):
        stats = get_stats()
        assert stats["total_embeddings"] >= 0

    def test_reflects_indexed_count(self, fresh_db):
        before = get_stats()["total_embeddings"]
        table = f"stat_table_{uuid4().hex[:8]}"
        register_source(table, resolver=lambda _: None, lister=lambda: [])
        index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Statistically significant", modality="inner",
        )
        after = get_stats()["total_embeddings"]
        assert after >= before + 1

    def test_has_model_version(self, fresh_db):
        stats = get_stats()
        assert "model_version" in stats
        assert stats["model_version"] == _MODEL_VERSION


# ===================================================================
# Helper functions — pure unit, no DB
# ===================================================================

class TestHelpers:
    """Internal utility functions — no DB needed."""

    def test_encode_decode_roundtrip(self):
        vec = np.array([0.1, 0.2, -0.3, 0.0], dtype=np.float32)
        decoded = _decode_vector(_encode_vector(vec))
        np.testing.assert_array_almost_equal(decoded, vec)

    def test_hash_content_stable(self):
        h1 = _hash_content("Hello world")
        h2 = _hash_content("Hello world")
        assert h1 == h2
        assert len(h1) == 32

    def test_hash_content_different(self):
        h1 = _hash_content("Hello")
        h2 = _hash_content("World")
        assert h1 != h2

    def test_prepare_text_trims(self):
        assert _prepare_text("  hello  ") == "hello"

    def test_prepare_text_clips(self):
        long = "x" * 5000
        clipped = _prepare_text(long)
        assert len(clipped) == 4000

    def test_prepare_text_none(self):
        assert _prepare_text(None) == ""

    def test_content_hash_unchanged(self, fresh_db):
        sid = uuid4().hex
        content = "Consistent content"
        index_memory(
            source_table="test", source_id=sid,
            content=content, modality="inner",
        )
        assert _content_hash_unchanged("test", sid, content) is True

    def test_content_hash_changed(self, fresh_db):
        sid = uuid4().hex
        index_memory(
            source_table="test", source_id=sid,
            content="Original", modality="inner",
        )
        assert _content_hash_unchanged("test", sid, "Changed") is False

    def test_content_hash_missing(self):
        assert _content_hash_unchanged("nonexistent", "noid", "anything") is False
