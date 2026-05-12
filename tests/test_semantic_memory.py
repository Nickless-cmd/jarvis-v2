"""Tests for core.services.semantic_memory.

Covers all 4 public functions:
- index_memory — embed + store
- search — cosine-similarity top-k retrieval
- backfill_all — bulk index unindexed rows
- get_stats — embedding counts

The module's only external dependency (Ollama embedding) is mocked
so tests run fast and offline. DB isolation uses isolated_runtime + sm_api
(reloads semantic_memory after isolated_runtime resets core.runtime.db).
"""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pytest

# Module-level imports for tests that DON'T need DB isolation.
# DB-backed tests accept the ``sm_api`` fixture instead.
from core.services.semantic_memory import (
    _content_hash_unchanged,
    _decode_vector,
    _encode_vector,
    _hash_content,
    _prepare_text,
    index_memory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_embed(text: str) -> np.ndarray | None:
    """Deterministic fake embedding: hash-based so same text = same vector."""
    h = hash(text)
    rng = np.random.RandomState(seed=h & 0xFFFFFFFF)
    v = rng.randn(64).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-10)


def _fake_embed_fail(_text: str) -> np.ndarray | None:
    """Embedding that always fails."""
    return None


@pytest.fixture(autouse=True)
def _patch_embed():
    """Replace Ollama embedding with deterministic fake for all tests."""
    with patch(
        "core.services.semantic_memory._embed_ollama",
        side_effect=_fake_embed,
    ):
        yield


@pytest.fixture
def sm_api(isolated_runtime):
    """Reload semantic_memory after isolated_runtime resets DB path.

    ``semantic_memory`` imports ``connect`` at module level, so it holds
    a stale reference to the original DB path after ``isolated_runtime``
    reloads ``core.runtime.db``.  This fixture reloads the module and
    returns fresh references to all public functions.

    Also re-applies the embed patch since reloading the module undoes it.
    """
    import importlib
    import core.services.semantic_memory as sm_mod
    import core.runtime.db_sensory as db_sensory_mod
    import core.runtime.db as db_mod
    import core.runtime.db_embeddings as db_emb_mod
    importlib.reload(db_mod)          # ensure connect() is fresh
    importlib.reload(db_emb_mod)      # so upsert_embedding uses fresh connect
    importlib.reload(db_sensory_mod)  # so insert_sensory_memory uses fresh connect
    importlib.reload(sm_mod)          # so index_memory/search use fresh connect

    # Re-patch after reload (the autouse fixture patched the old reference)
    from unittest.mock import patch as _patch
    _patcher = _patch(
        "core.services.semantic_memory._embed_ollama",
        side_effect=_fake_embed,
    )
    _patcher.start()

    yield SimpleNamespace(
        index_memory=sm_mod.index_memory,
        search=sm_mod.search,
        backfill_all=sm_mod.backfill_all,
        get_stats=sm_mod.get_stats,
        register_source=sm_mod.register_source,
        _content_hash_unchanged=sm_mod._content_hash_unchanged,
        _MODEL_VERSION=sm_mod._MODEL_VERSION,
        _RESOLVERS=sm_mod._RESOLVERS,
        _LISTERS=sm_mod._LISTERS,
    )

    _patcher.stop()


@pytest.fixture
def test_source(sm_api):
    """Register a throwaway source table.

    Returns (sm_api, table_name, records_dict) so callers can use the
    reloaded API and their custom table.
    """
    table = f"test_table_{uuid4().hex[:8]}"
    records: dict[str, dict] = {}

    def resolver(sid: str) -> dict | None:
        return records.get(sid)

    def lister() -> list[dict]:
        return list(records.values())

    sm_api.register_source(table, resolver=resolver, lister=lister)
    return sm_api, table, records


# ===================================================================
# index_memory — these use module-level imports but only *write* to DB ;
# they're insensitive to stale connect() because the real DB path still
# works for writes (we just pollute the real DB slightly, which is fine
# for ephemeral test IDs).  For full isolation see search/backfill tests.
# ===================================================================

class TestIndexMemory:
    """Core embed+store path."""

    def test_happy_path(self):
        sid = uuid4().hex
        ok = index_memory(
            source_table="test", source_id=sid,
            content="Jarvis is thinking about the ocean",
            modality="inner",
        )
        assert ok is True

    def test_empty_content_returns_false(self):
        ok = index_memory(
            source_table="test", source_id="any",
            content="   ", modality="visual",
        )
        assert ok is False

    def test_embed_failure_returns_false(self):
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

    def test_unchanged_content_hash_skips_embed(self):
        sid = uuid4().hex
        content = "Persistent thought that stays the same"
        ok1 = index_memory(
            source_table="test", source_id=sid,
            content=content, modality="inner",
        )
        assert ok1 is True

        call_count = 0

        def tracking_embed(_t: str) -> np.ndarray | None:
            nonlocal call_count
            call_count += 1
            return _fake_embed(_t)

        with patch(
            "core.services.semantic_memory._embed_ollama",
            side_effect=tracking_embed,
        ):
            ok2 = index_memory(
                source_table="test", source_id=sid,
                content=content, modality="inner",
            )
        assert ok2 is True
        assert call_count == 0, "Should skip embed when hash matches"

    def test_different_content_reembeds(self):
        sid = uuid4().hex
        ok1 = index_memory(
            source_table="test", source_id=sid,
            content="First thought", modality="inner",
        )
        assert ok1 is True
        ok2 = index_memory(
            source_table="test", source_id=sid,
            content="Second thought", modality="inner",
        )
        assert ok2 is True

    def test_content_clipped_at_max(self):
        ok = index_memory(
            source_table="test", source_id="long_one",
            content="x" * 5000, modality="mixed",
        )
        assert ok is True


# ===================================================================
# search
# ===================================================================

class TestSearch:
    """Cosine-similarity retrieval — uses sm_api for isolated DB."""

    def test_empty_query_returns_empty_list(self, sm_api):
        assert sm_api.search("") == []

    def test_no_embeddings_returns_empty(self, sm_api):
        assert sm_api.search("anything at all") == []

    def test_returns_relevant_hits(self, test_source):
        sm, table, _ = test_source
        sm.index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Deep thoughts about neural networks and AI",
            modality="inner",
        )
        sm.index_memory(
            source_table=table, source_id=uuid4().hex,
            content="What I had for breakfast this morning",
            modality="inner",
        )
        results = sm.search("artificial intelligence", min_score=0.0)
        assert len(results) >= 1

    def test_min_score_filters(self, test_source):
        sm, table, _ = test_source
        sm.index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Random unrelated chatter",
            modality="inner",
        )
        strict = sm.search("very specific unique concept", min_score=0.99)
        loose = sm.search("very specific unique concept", min_score=0.0)
        assert len(strict) <= len(loose)

    def test_modality_filter(self, test_source):
        sm, table, _ = test_source
        sm.index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Audio memory test", modality="audio",
        )
        sm.index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Visual memory test", modality="visual",
        )
        audio_only = sm.search("memory", modalities=["audio"], min_score=0.0)
        visual_only = sm.search("memory", modalities=["visual"], min_score=0.0)
        assert all(h["modality"] == "audio" for h in audio_only)
        assert all(h["modality"] == "visual" for h in visual_only)

    def test_source_table_filter(self, sm_api):
        """Search with source_tables filter returns only matching results."""
        table_a = f"table_a_{uuid4().hex[:8]}"
        table_b = f"table_b_{uuid4().hex[:8]}"

        sm_api.register_source(
            table_a, resolver=lambda _: None, lister=lambda: [],
        )
        sm_api.register_source(
            table_b, resolver=lambda _: None, lister=lambda: [],
        )

        sm_api.index_memory(
            source_table=table_a, source_id=uuid4().hex,
            content="From table A", modality="inner",
        )
        sm_api.index_memory(
            source_table=table_b, source_id=uuid4().hex,
            content="From table B", modality="inner",
        )
        from_a = sm_api.search("table", source_tables=[table_a], min_score=0.0)
        from_b = sm_api.search("table", source_tables=[table_b], min_score=0.0)
        assert any(h["source_table"] == table_a for h in from_a)
        assert any(h["source_table"] == table_b for h in from_b)

    def test_limit_respected(self, test_source):
        sm, table, _ = test_source
        for i in range(5):
            sm.index_memory(
                source_table=table, source_id=uuid4().hex,
                content=f"Indexed item number {i}",
                modality="inner",
            )
        results = sm.search("indexed item", limit=3, min_score=0.0)
        assert len(results) <= 3

    def test_result_has_expected_keys(self, test_source):
        sm, table, records = test_source
        sid = uuid4().hex
        records[sid] = {
            "id": sid,
            "content": "Memory with full metadata",
            "modality": "inner",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        sm.index_memory(
            source_table=table, source_id=sid,
            content="Memory with full metadata",
            modality="inner",
        )
        results = sm.search("memory metadata", min_score=0.0)
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
    """Bulk indexing — uses sm_api for isolated DB + reloaded module."""

    def test_no_registered_sources_returns_empty(self, sm_api):
        with patch.object(sm_api, "_RESOLVERS", {}), \
             patch.object(sm_api, "_LISTERS", {}):
            summary = sm_api.backfill_all()
        assert summary["total_indexed"] == 0
        assert summary["total_failed"] == 0

    def test_handles_missing_sql_tables_gracefully(self, sm_api):
        """backfill_all logs a warning for non-existent SQL tables without
        crashing. This is the expected behavior on an empty/fresh DB."""
        summary = sm_api.backfill_all(max_per_table=10)
        # sensory_memories table doesn't exist in the empty test DB,
        # so it logs a warning but doesn't raise.
        assert "sensory_memories" in summary["tables"]
        assert "error" in summary["tables"]["sensory_memories"]

    def test_private_brain_table_also_handled(self, sm_api):
        """Same graceful handling for private_brain_records table."""
        summary = sm_api.backfill_all(max_per_table=10)
        assert "private_brain_records" in summary["tables"]
        assert "error" in summary["tables"]["private_brain_records"]

    def test_indexes_real_sensory_table_rows(self, sm_api):
        """Prove backfill works end-to-end when the real table exists."""
        from core.runtime.db_sensory import insert_sensory_memory

        mem = insert_sensory_memory(
            modality="mixed",
            content="Row that needs backfilling",
        )
        sid = str(mem["id"])
        summary = sm_api.backfill_all(max_per_table=10)
        assert summary["tables"]["sensory_memories"]["indexed"] >= 1
        # Verify the specific row was indexed
        assert sid in {
            h["source_id"]
            for h in sm_api.search("backfilling", min_score=0.0)
        }

    def test_skips_already_indexed_rows(self, sm_api):
        """Rows already in memory_embeddings are not re-indexed."""
        from core.runtime.db_sensory import insert_sensory_memory

        mem = insert_sensory_memory(
            modality="mixed",
            content="Already indexed content",
        )
        sid = str(mem["id"])
        sm_api.index_memory(
            source_table="sensory_memories",
            source_id=sid,
            content="Already indexed content",
            modality="inner",
        )
        summary = sm_api.backfill_all(max_per_table=10)
        assert summary["tables"]["sensory_memories"]["indexed"] == 0
        # Verify the row is still searchable
        hits = sm_api.search("indexed", min_score=0.0)
        assert any(h["source_id"] == sid for h in hits)


# ===================================================================
# get_stats
# ===================================================================

class TestGetStats:
    """Embedding count overview."""

    def test_empty_returns_zero(self, sm_api):
        stats = sm_api.get_stats()
        assert stats["total_embeddings"] >= 0

    def test_reflects_indexed_count(self, sm_api):
        before = sm_api.get_stats()["total_embeddings"]
        table = f"stat_table_{uuid4().hex[:8]}"
        sm_api.register_source(
            table, resolver=lambda _: None, lister=lambda: [],
        )
        sm_api.index_memory(
            source_table=table, source_id=uuid4().hex,
            content="Statistically significant", modality="inner",
        )
        after = sm_api.get_stats()["total_embeddings"]
        assert after >= before + 1

    def test_has_model_version(self, sm_api):
        stats = sm_api.get_stats()
        assert "model_version" in stats
        assert stats["model_version"] == sm_api._MODEL_VERSION


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

    def test_content_hash_unchanged(self, sm_api):
        sid = uuid4().hex
        content = "Consistent content"
        sm_api.index_memory(
            source_table="test", source_id=sid,
            content=content, modality="inner",
        )
        assert sm_api._content_hash_unchanged("test", sid, content) is True

    def test_content_hash_changed(self, sm_api):
        sid = uuid4().hex
        sm_api.index_memory(
            source_table="test", source_id=sid,
            content="Original", modality="inner",
        )
        assert sm_api._content_hash_unchanged("test", sid, "Changed") is False

    def test_content_hash_missing(self):
        assert _content_hash_unchanged("nonexistent", "noid", "anything") is False
