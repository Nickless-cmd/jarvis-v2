"""Tests for B4 — Temporal Linking af Brain Entries (2026-06-09)."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import pytest


# ---------------------------------------------------------------------------
# Hjælpefunktioner — enhedstests af signal-scores
# ---------------------------------------------------------------------------


class TestTemporalSimilarityScore:
    def test_returns_1_at_1_hour(self):
        from core.services.jarvis_brain import _temporal_similarity_score
        assert _temporal_similarity_score(0.5) == 1.0
        assert _temporal_similarity_score(1.0) == 1.0

    def test_returns_0_at_24_hours(self):
        from core.services.jarvis_brain import _temporal_similarity_score
        assert _temporal_similarity_score(24.0) == 0.0
        assert _temporal_similarity_score(48.0) == 0.0

    def test_decays_linearly_between_1_and_24(self):
        from core.services.jarvis_brain import _temporal_similarity_score
        # 12.5h → halfway between 1 and 24
        score = _temporal_similarity_score(12.5)
        assert 0.45 < score < 0.55  # ~0.5


class TestComputeTemporalConfidence:
    def test_basic_weighted_formula(self):
        from core.services.jarvis_brain import _compute_temporal_confidence
        # All signals at 1.0, no chain
        c = _compute_temporal_confidence(temporal=1.0, semantic=1.0, entity=1.0, is_chain=False)
        # 0.4*1 + 0.4*1 + 0.2*1 = 1.0, capped at 0.98
        assert c == pytest.approx(0.98, abs=0.01)

    def test_chain_boost(self):
        from core.services.jarvis_brain import _compute_temporal_confidence
        # Medium signals + chain boost
        c_no_chain = _compute_temporal_confidence(temporal=0.5, semantic=0.5, entity=0.5, is_chain=False)
        c_chain = _compute_temporal_confidence(temporal=0.5, semantic=0.5, entity=0.5, is_chain=True)
        assert c_chain == pytest.approx(c_no_chain + 0.15, abs=0.01)

    def test_caps_at_098(self):
        from core.services.jarvis_brain import _compute_temporal_confidence
        c = _compute_temporal_confidence(temporal=10.0, semantic=10.0, entity=10.0, is_chain=True)
        assert c <= 0.98

    def test_zero_signals(self):
        from core.services.jarvis_brain import _compute_temporal_confidence
        c = _compute_temporal_confidence(temporal=0.0, semantic=0.0, entity=0.0, is_chain=False)
        assert c == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# SQLite schema tests
# ---------------------------------------------------------------------------


def test_brain_temporal_edges_table_created(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    conn = jarvis_brain.connect_index()
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "brain_temporal_edges" in tables
    # Check columns
    cols = {
        r[1]: r[2]
        for r in conn.execute("PRAGMA table_info(brain_temporal_edges)").fetchall()
    }
    assert cols["from_id"] == "TEXT"
    assert cols["to_id"] == "TEXT"
    assert cols["relation_type"] == "TEXT"
    assert cols["confidence"] == "REAL"
    assert cols["inferred_at"] == "TEXT"
    conn.close()


# ---------------------------------------------------------------------------
# Integration tests — infer_temporal_edges
# ---------------------------------------------------------------------------


@pytest.fixture
def brain_with_entries(tmp_path, monkeypatch):
    """Two existing entries at known timestamps + deterministic embeddings."""
    import numpy as np
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    # Deterministic embeddings: all same direction → high semantic similarity
    _embed_counter = [0.0]

    def fake_embed(text: str) -> np.ndarray:
        _embed_counter[0] += 0.1
        # Entries with "alpha"/"beta"/"gamma" get different vectors
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.9, 0.1, 0.0], dtype=np.float32)
        if "gamma" in text.lower():
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.5, 0.5, 0.0], dtype=np.float32)
    monkeypatch.setattr(jarvis_brain, "_embed_text", fake_embed)

    now = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)

    # Entry A: 2 hours ago (temporal: score ~0.96)
    a_id = jarvis_brain.write_entry(
        kind="fakta", title="Alpha project",
        content="alpha details for project X", visibility="personal", domain="x",
        now=now - timedelta(hours=2),
    )
    # Entry B: 23 hours ago (temporal: low score ~0.04)
    b_id = jarvis_brain.write_entry(
        kind="observation", title="Beta observation",
        content="beta random observation", visibility="personal", domain="y",
        now=now - timedelta(hours=23),
    )
    # Entry C: 6 hours ago, different semantic cluster (temporal: ~0.78)
    c_id = jarvis_brain.write_entry(
        kind="indsigt", title="Gamma insight",
        content="gamma reflections on project Y", visibility="personal", domain="z",
        now=now - timedelta(hours=6),
    )

    # Embed the existing entries (they were written without embeddings)
    jarvis_brain.embed_pending_entries()

    return {"a": a_id, "b": b_id, "c": c_id, "now": now, "fake_embed": fake_embed}


def test_infer_temporal_edges_creates_qualified_edges(brain_with_entries, tmp_path, monkeypatch):
    """New entry close to A and C → should create edges but not B."""
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    now = brain_with_entries["now"]
    a_id = brain_with_entries["a"]
    b_id = brain_with_entries["b"]
    c_id = brain_with_entries["c"]

    # Write the test entry with skip_temporal=True (so we test infer explicitly)
    new_id = jarvis_brain.write_entry(
        kind="fakta", title="New alpha-related",
        content="alpha related new entry about project X",
        visibility="personal", domain="x",
        now=now - timedelta(hours=1),  # 1h ago → max temporal score to A
        skip_temporal=True,
    )

    # Embed the new entry (infer_temporal_edges does this inline, but write_entry
    # doesn't. The inference function calls _embed_text inline.)
    jarvis_brain.embed_pending_entries()

    # Run inference manually
    n = jarvis_brain.infer_temporal_edges(new_id, now=now)
    assert n >= 1  # At least A should qualify

    # Check edges created
    conn = jarvis_brain.connect_index()
    try:
        edges = conn.execute(
            "SELECT to_id, relation_type, confidence FROM brain_temporal_edges WHERE from_id = ?",
            (new_id,),
        ).fetchall()
    finally:
        conn.close()

    edge_targets = {row[0] for row in edges}
    assert a_id in edge_targets  # A is close in time + semantic
    # B is likely below threshold (23h gap + different domain)
    # C may or may not qualify depending on entity overlap

    # Verify get_temporal_neighbors works
    neighbors = jarvis_brain.get_temporal_neighbors(new_id, min_confidence=0.4)
    neighbor_ids = [n_id for n_id, _ in neighbors]
    assert a_id in neighbor_ids
    assert len(neighbors) >= 1


def test_write_entry_triggers_inference(tmp_path, monkeypatch):
    """write_entry with skip_temporal=False (default) triggers inference."""
    import numpy as np
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    def fake_embed(text: str) -> np.ndarray:
        return np.array([0.5, 0.5, 0.0], dtype=np.float32)
    monkeypatch.setattr(jarvis_brain, "_embed_text", fake_embed)

    now = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)

    # Create first entry
    first = jarvis_brain.write_entry(
        kind="fakta", title="First entry",
        content="initial content", visibility="personal", domain="x",
        now=now - timedelta(hours=1),
    )
    jarvis_brain.embed_pending_entries()

    # Create second entry — default skip_temporal=False
    second = jarvis_brain.write_entry(
        kind="fakta", title="Second entry",
        content="second content", visibility="personal", domain="x",
        now=now,  # same time window
    )

    # Check that temporal edges were created
    conn = jarvis_brain.connect_index()
    try:
        edge_count = conn.execute(
            "SELECT COUNT(*) FROM brain_temporal_edges WHERE from_id = ?",
            (second,),
        ).fetchone()[0]
    finally:
        conn.close()

    assert edge_count >= 1


def test_infer_temporal_edges_does_not_create_self_edges(brain_with_entries, tmp_path, monkeypatch):
    """New entry should only get edges to OTHER entries, not itself."""
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    now = brain_with_entries["now"]

    new_id = jarvis_brain.write_entry(
        kind="fakta", title="Self check",
        content="self edge check", visibility="personal", domain="x",
        now=now, skip_temporal=True,
    )
    jarvis_brain.embed_pending_entries()
    jarvis_brain.infer_temporal_edges(new_id, now=now)

    conn = jarvis_brain.connect_index()
    try:
        self_edges = conn.execute(
            "SELECT COUNT(*) FROM brain_temporal_edges WHERE from_id = ? AND to_id = ?",
            (new_id, new_id),
        ).fetchone()[0]
    finally:
        conn.close()

    assert self_edges == 0


def test_get_temporal_neighbors_returns_sorted_by_confidence(brain_with_entries, tmp_path, monkeypatch):
    """get_temporal_neighbors should return descending confidence."""
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    now = brain_with_entries["now"]
    a_id = brain_with_entries["a"]

    # Check that A has neighbors (it was close to others in time)
    neighbors = jarvis_brain.get_temporal_neighbors(a_id, min_confidence=0.4)
    # Results should be sorted descending by confidence
    confidences = [conf for _, conf in neighbors]
    assert confidences == sorted(confidences, reverse=True)


def test_write_entry_with_skip_temporal_still_works(tmp_path, monkeypatch):
    """skip_temporal=True should write normally without inference."""
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    entry_id = jarvis_brain.write_entry(
        kind="fakta", title="Skipped temporal",
        content="no inference please", visibility="personal", domain="x",
        skip_temporal=True,
    )

    e = jarvis_brain.read_entry(entry_id)
    assert e.title == "Skipped temporal"

    # No edges should exist
    conn = jarvis_brain.connect_index()
    try:
        edge_count = conn.execute(
            "SELECT COUNT(*) FROM brain_temporal_edges"
        ).fetchone()[0]
    finally:
        conn.close()
    assert edge_count == 0
