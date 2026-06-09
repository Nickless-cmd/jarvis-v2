"""Tests for B4 — Temporal Linking for brain entries.

Tests cover:
- _temporal_similarity_score — temporal proximity scoring
- _cosine_similarity — embedding similarity
- _compute_temporal_confidence — multi-signal fusion
- infer_temporal_edges — end-to-end inference pipeline
- get_temporal_neighbors — neighbor retrieval
- prune_stale_edges — edge cleanup
- temporal_boost_recall — recall-time boost computation
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, MagicMock, patch

import numpy as np
import pytest


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def mock_connect_index():
    """Mock connect_index() to return a controlled SQLite connection.

    The mock wraps a real :memory: connection so INSERT/SELECT work,
    but we patch connect_index so the module-level call uses our conn.
    """
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS brain_temporal_edges (
            from_id TEXT NOT NULL,
            to_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.0,
            inferred_at TEXT NOT NULL,
            PRIMARY KEY (from_id, to_id, relation_type)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_temporal_edges_from "
        "ON brain_temporal_edges(from_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_temporal_edges_to "
        "ON brain_temporal_edges(to_id)"
    )
    yield conn
    conn.close()


@pytest.fixture
def patch_connect(mock_connect_index):
    """Patch jarvis_brain.connect_index to return mock in-memory DB."""
    with patch("core.services.jarvis_brain.connect_index",
               return_value=mock_connect_index):
        yield





# ── _temporal_similarity_score ────────────────────────────────────


def test_temporal_score_same_hour():
    """Entries 30 min apart → score ≈ 1.0."""
    from core.services.jarvis_brain import _temporal_similarity_score
    score = _temporal_similarity_score(0.5)  # 30 min
    assert score == 1.0, f"Expected 1.0, got {score}"


def test_temporal_score_week_apart():
    """Entries 7 days apart → score ≈ 0.0."""
    from core.services.jarvis_brain import _temporal_similarity_score
    score = _temporal_similarity_score(168.0)  # 7 days
    assert score == 0.0, f"Expected 0.0, got {score}"


def test_temporal_score_12h_apart():
    """Entries 12 hours apart → score ≈ 0.52."""
    from core.services.jarvis_brain import _temporal_similarity_score
    score = _temporal_similarity_score(12.0)
    assert 0.4 < score < 0.6, f"Expected ~0.52, got {score}"


def test_temporal_score_edge_boundary():
    """Exactly at 24h boundary → score 0.0."""
    from core.services.jarvis_brain import _temporal_similarity_score
    score = _temporal_similarity_score(24.0)
    assert score == 0.0, f"Expected 0.0, got {score}"


# ── _cosine_similarity ────────────────────────────────────────────


def test_cosine_similarity_identical():
    """Same embedding → 1.0."""
    from core.services.jarvis_brain import _cosine_similarity
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    """Orthogonal vectors → 0.0."""
    from core.services.jarvis_brain import _cosine_similarity
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_zero_vector():
    """Zero vector → 0.0 (no division by zero)."""
    from core.services.jarvis_brain import _cosine_similarity
    v = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    assert _cosine_similarity(v, v) == 0.0


# ── _compute_temporal_confidence ──────────────────────────────────


def test_fuse_confidence_all_high():
    """All 3 signals high → 0.85+."""
    from core.services.jarvis_brain import _compute_temporal_confidence
    conf = _compute_temporal_confidence(temporal=1.0, semantic=1.0, entity=1.0, is_chain=False)
    assert 0.8 <= conf <= 0.98


def test_fuse_confidence_one_low():
    """2 high + 1 low → still ≥ 0.5."""
    from core.services.jarvis_brain import _compute_temporal_confidence
    conf = _compute_temporal_confidence(temporal=1.0, semantic=1.0, entity=0.0, is_chain=False)
    assert conf >= 0.5


def test_fuse_confidence_all_low():
    """All signals low → near 0."""
    from core.services.jarvis_brain import _compute_temporal_confidence
    conf = _compute_temporal_confidence(temporal=0.0, semantic=0.0, entity=0.0, is_chain=False)
    assert conf == pytest.approx(0.0, abs=1e-6)


def test_fuse_confidence_chain_boost():
    """Chain_score=1.0 adds +0.15 boost, capped at 0.98."""
    from core.services.jarvis_brain import _compute_temporal_confidence
    conf = _compute_temporal_confidence(temporal=0.9, semantic=0.9, entity=0.9, is_chain=True, chain_score=1.0)
    # 0.4*0.9 + 0.4*0.9 + 0.2*0.9 = 0.9, +0.15*1.0 chain = 1.05, capped at 0.98
    assert conf == 0.98


def test_fuse_confidence_partial_chain():
    """chain_score=0.5 gives half boost."""
    from core.services.jarvis_brain import _compute_temporal_confidence
    conf = _compute_temporal_confidence(temporal=0.5, semantic=0.5, entity=0.5, is_chain=True, chain_score=0.5)
    # 0.4*0.5 + 0.4*0.5 + 0.2*0.5 = 0.5, +0.15*0.5 = 0.075 → 0.575
    assert conf == pytest.approx(0.575, abs=0.001)


# ── get_temporal_neighbors (with mock DB) ─────────────────────────


def test_get_temporal_neighbors_empty(patch_connect):
    """No edges → empty list."""
    from core.services.jarvis_brain import get_temporal_neighbors
    neighbors = get_temporal_neighbors("brn_NONE")
    assert neighbors == []


def test_get_temporal_neighbors_with_data(mock_connect_index, patch_connect):
    """Edges present → returns sorted neighbors."""
    now = datetime.now(timezone.utc)
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.85, now.isoformat()),
    )
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_C", "combined", 0.65, now.isoformat()),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import get_temporal_neighbors
    neighbors = get_temporal_neighbors("brn_A", min_confidence=0.4)
    assert len(neighbors) == 2
    assert neighbors[0][0] == "brn_B"  # highest confidence first
    assert neighbors[0][1] == 0.85
    assert neighbors[1][0] == "brn_C"


def test_get_temporal_neighbors_min_confidence_filter(mock_connect_index, patch_connect):
    """Edges below min_confidence are excluded."""
    now = datetime.now(timezone.utc)
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_X", "brn_Y", "combined", 0.3, now.isoformat()),
    )
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_X", "brn_Z", "combined", 0.7, now.isoformat()),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import get_temporal_neighbors
    neighbors = get_temporal_neighbors("brn_X", min_confidence=0.5)
    assert len(neighbors) == 1
    assert neighbors[0][0] == "brn_Z"


# ── prune_stale_edges ─────────────────────────────────────────────


def test_prune_stale_low_conf(mock_connect_index, patch_connect):
    """Old + low confidence → deleted."""
    old = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.1, old),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import prune_stale_edges
    deleted = prune_stale_edges(max_age_days=90, min_confidence=0.2)
    assert deleted >= 1


def test_prune_preserves_high_conf(mock_connect_index, patch_connect):
    """Old but high confidence → preserved."""
    old = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.7, old),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import prune_stale_edges
    deleted = prune_stale_edges(max_age_days=90, min_confidence=0.5)
    assert deleted == 0


# ── temporal_boost_recall ─────────────────────────────────────────


def test_temporal_boost_recall_empty():
    """No entry_ids → empty boost dict."""
    from core.services.jarvis_brain import temporal_boost_recall
    boosts = temporal_boost_recall([])
    assert boosts == {}


def test_temporal_boost_recall_computes(
    mock_connect_index, patch_connect,
):
    """Entry with temporal neighbors gets boost scores."""
    now = datetime.now(timezone.utc)
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.85, now.isoformat()),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import temporal_boost_recall
    boosts = temporal_boost_recall(["brn_A"], boost_factor=0.15, min_confidence=0.4)
    assert "brn_B" in boosts
    expected = round(0.85 * 0.15, 4)
    assert boosts["brn_B"] == expected


def test_temporal_boost_recall_no_neighbors(
    mock_connect_index, patch_connect,
):
    """Entry with no temporal neighbors → empty boost dict."""
    from core.services.jarvis_brain import temporal_boost_recall
    boosts = temporal_boost_recall(["brn_X"], min_confidence=0.4)
    assert boosts == {}


# ── _compute_search_temporal_boost (B4 Phase 2, 2026-06-09) ──────


def test_search_temporal_boost_empty():
    """Empty candidate list → empty dict."""
    from core.services.jarvis_brain import _compute_search_temporal_boost
    boosts = _compute_search_temporal_boost([])
    assert boosts == {}


def test_search_temporal_boost_single_edge(
    mock_connect_index, patch_connect,
):
    """Candidate with a single strong edge → gets boost."""
    now = datetime.now(timezone.utc).isoformat()
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.9, now),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import _compute_search_temporal_boost
    boosts = _compute_search_temporal_boost(["brn_A"], boost_factor=0.15, min_confidence=0.4)
    expected = round(0.9 * 0.15, 4)
    assert boosts.get("brn_A") == expected, f"Expected {expected}, got {boosts}"


def test_search_temporal_boost_below_threshold(
    mock_connect_index, patch_connect,
):
    """Edge below min_confidence → no boost."""
    now = datetime.now(timezone.utc).isoformat()
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.3, now),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import _compute_search_temporal_boost
    boosts = _compute_search_temporal_boost(["brn_A"], boost_factor=0.15, min_confidence=0.5)
    assert boosts == {}


def test_search_temporal_boost_multiple_candidates(
    mock_connect_index, patch_connect,
):
    """Multiple candidates, some with edges, some without."""
    now = datetime.now(timezone.utc).isoformat()
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.85, now),
    )
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_C", "brn_B", "combined", 0.7, now),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import _compute_search_temporal_boost
    boosts = _compute_search_temporal_boost(
        ["brn_A", "brn_C", "brn_X"],
        boost_factor=0.15, min_confidence=0.4,
    )
    # brn_A has edge (0.85) → boost = 0.85*0.15
    expected_a = round(0.85 * 0.15, 4)
    assert boosts.get("brn_A") == expected_a
    # brn_C has edge (0.7) → boost = 0.7*0.15
    expected_c = round(0.7 * 0.15, 4)
    assert boosts.get("brn_C") == expected_c
    # brn_X has no edges
    assert "brn_X" not in boosts


def test_search_temporal_boost_max_confidence(
    mock_connect_index, patch_connect,
):
    """Candidate with multiple edges → uses MAX confidence."""
    now = datetime.now(timezone.utc).isoformat()
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.5, now),
    )
    mock_connect_index.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_C", "combined", 0.9, now),
    )
    mock_connect_index.commit()

    from core.services.jarvis_brain import _compute_search_temporal_boost
    boosts = _compute_search_temporal_boost(["brn_A"], boost_factor=0.15, min_confidence=0.4)
    expected = round(0.9 * 0.15, 4)  # MAX(0.5, 0.9) = 0.9
    assert boosts.get("brn_A") == expected, f"Expected {expected}, got {boosts.get('brn_A')}"


# ── _store_temporal_edge (via direct INSERT) ──────────────────────


def test_store_temporal_edge_creates_row(mock_connect_index):
    """INSERT creates a row with relation_type='combined' and confidence rounded."""
    conn = mock_connect_index
    conn.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.85, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()

    row = conn.execute(
        "SELECT from_id, to_id, relation_type, confidence FROM brain_temporal_edges"
    ).fetchone()
    assert row is not None
    assert row[0] == "brn_A"
    assert row[1] == "brn_B"
    assert row[2] == "combined"
    assert row[3] == 0.85


def test_store_temporal_edge_replaces_existing(mock_connect_index):
    """INSERT OR REPLACE overwrites existing edge for same PK."""
    conn = mock_connect_index
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.5, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO brain_temporal_edges VALUES (?, ?, ?, ?, ?)",
        ("brn_A", "brn_B", "combined", 0.95, now),
    )
    conn.commit()

    rows = conn.execute(
        "SELECT confidence FROM brain_temporal_edges"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 0.95


# ── Integration: infer_temporal_edges via write_entry ─────────────


def test_write_entry_triggers_inferens():
    """write_entry calls infer_temporal_edges for the new entry."""
    from core.services.jarvis_brain import write_entry
    with patch("core.services.jarvis_brain.infer_temporal_edges") as mock_infer:
        entry_id = write_entry(
            kind="observation",
            title="test edge trigger",
            content="test content",
            visibility="personal",
            domain="test",
            now=datetime(2026, 6, 9, tzinfo=timezone.utc),
        )
        mock_infer.assert_called_once_with(entry_id, now=ANY)


def test_write_entry_skip_temporal():
    """write_entry(skip_temporal=True) does NOT call infer_temporal_edges."""
    from core.services.jarvis_brain import write_entry
    with patch("core.services.jarvis_brain.infer_temporal_edges") as mock_infer:
        write_entry(
            kind="observation",
            title="test skip",
            content="should skip",
            visibility="personal",
            domain="test",
            skip_temporal=True,
            now=datetime(2026, 6, 9, tzinfo=timezone.utc),
        )
        mock_infer.assert_not_called()
