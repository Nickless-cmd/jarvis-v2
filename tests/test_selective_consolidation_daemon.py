"""Tests for D1 — Selective Consolidation Daemon.

Tests use isolated DB and sensory tables so they never touch real data.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    """Point DB_PATH at a clean temp file."""
    from core.runtime import db_core
    db_file = tmp_path / "test_consolidation.db"
    monkeypatch.setattr(db_core, "DB_PATH", db_file)
    from core.runtime.db_core import invalidate_ensure_once_cache
    invalidate_ensure_once_cache()
    return db_file


def _insert_sensory(conn, content: str, mood_tone: str | None = None, days_ago: int = 0):
    """Insert a sensory memory row directly."""
    from core.runtime.db_sensory import _ensure_sensory_memories_table, _scope
    _ensure_sensory_memories_table(conn)
    ts = datetime.now(UTC).isoformat()
    if days_ago > 0:
        # For testing with "today" timestamps
        pass
    # Per-user scope (#154): count_sensory_memories() filters by scope_uid(),
    # so rows must carry the scoped user_id or they are invisible to the count.
    conn.execute(
        "INSERT INTO sensory_memories (id, timestamp, modality, content, mood_tone, metadata_json, user_id) "
        "VALUES (?, ?, ?, ?, ?, '{}', ?)",
        (uuid4().hex, ts, "visual", content, mood_tone, _scope()),
    )
    conn.commit()


def _insert_private_record(conn, summary: str, detail: str = "", salience: float = 1.0,
                           days_ago: int = 0):
    """Insert a private brain record directly."""
    from core.runtime.db import _ensure_private_brain_records_table
    _ensure_private_brain_records_table(conn)
    now = datetime.now(UTC)
    ts = now.isoformat()
    record_id = uuid4().hex
    conn.execute(
        "INSERT INTO private_brain_records "
        "(record_id, record_type, layer, summary, detail, salience, status, "
        "created_at, updated_at) "
        "VALUES (?, 'reflection', 'private_brain', ?, ?, ?, 'active', ?, ?)",
        (record_id, summary, detail, salience, ts, ts),
    )
    conn.commit()
    return record_id


# ── _score_sensory ────────────────────────────────────────────────────


def test_score_sensory_short_content_is_zero():
    """Content under _MIN_CONTENT_LENGTH must score 0."""
    from core.services.selective_consolidation_daemon import _score_sensory
    assert _score_sensory({"content": "hi"}) == 0.0
    assert _score_sensory({"content": ""}) == 0.0


def test_score_sensory_long_content_scores_above_zero():
    """Longer content must score > 0."""
    from core.services.selective_consolidation_daemon import _score_sensory
    content = "x" * 100
    score = _score_sensory({"content": content})
    assert 0.1 < score < 1.0


def test_score_sensory_with_mood_tone_gets_bonus():
    """mood_tone must add 0.2 to the score."""
    from core.services.selective_consolidation_daemon import _score_sensory
    base = _score_sensory({"content": "x" * 100, "mood_tone": None})
    boosted = _score_sensory({"content": "x" * 100, "mood_tone": "calm"})
    assert boosted == pytest.approx(base + 0.2, rel=0.01)


# ── _score_private ────────────────────────────────────────────────────


def test_score_private_uses_detail_and_salience():
    """Private record score must incorporate detail length and salience."""
    from core.services.selective_consolidation_daemon import _score_private
    score = _score_private({"detail": "x" * 100, "salience": 0.5})
    assert 0.5 < score < 1.0


def test_score_private_zero_for_short():
    """Short content must score 0."""
    from core.services.selective_consolidation_daemon import _score_private
    assert _score_private({"detail": "hi", "salience": 0.0}) == 0.0


# ── _consolidate_sensory ──────────────────────────────────────────────


def test_consolidate_sensory_archives_bottom_half(isolated_db):
    """With 10 sensory memories, bottom 50% must be deleted, top 5 kept."""
    from core.runtime.db import connect
    from core.services.selective_consolidation_daemon import _consolidate_sensory

    today_start = datetime.now(UTC).strftime("%Y-%m-%dT00:00:00")

    with connect() as conn:
        # Insert 5 short (low quality) + 5 long (high quality)
        for i in range(5):
            _insert_sensory(conn, "short", mood_tone=None)
        for i in range(5):
            _insert_sensory(conn, "x" * 500, mood_tone="calm")

    result = _consolidate_sensory(today_start)
    assert result["scored"] == 10
    assert result["archived"] == 5  # bottom 50% deleted

    # Verify: only 5 remain
    from core.runtime.db_sensory import count_sensory_memories
    remaining = count_sensory_memories()
    assert remaining == 5


def test_consolidate_sensory_no_today_records(isolated_db):
    """No records today = nothing archived."""
    from core.services.selective_consolidation_daemon import _consolidate_sensory
    future_start = "2099-01-01T00:00:00"
    result = _consolidate_sensory(future_start)
    assert result["scored"] == 0
    assert result["archived"] == 0


# ── _consolidate_private ──────────────────────────────────────────────


def test_consolidate_private_archives_bottom_half(isolated_db):
    """With 6 private records, bottom 50% must be archived."""
    from core.runtime.db import connect
    from core.services.selective_consolidation_daemon import _consolidate_private

    today_start = datetime.now(UTC).strftime("%Y-%m-%dT00:00:00")

    with connect() as conn:
        # 3 low-quality (short, low salience)
        for i in range(3):
            _insert_private_record(conn, "short", detail="x", salience=0.1)
        # 3 high-quality (long, high salience)
        for i in range(3):
            _insert_private_record(conn, "Long summary here", detail="x" * 500, salience=0.8)

    result = _consolidate_private(today_start)
    assert result["scored"] == 6
    assert result["archived"] >= 2  # bottom 50% → at least 2 archived (rounding)

    # Verify archived status
    from core.runtime.db import connect
    with connect() as conn:
        from core.runtime.db import _ensure_private_brain_records_table
        _ensure_private_brain_records_table(conn)
        active = conn.execute(
            "SELECT COUNT(*) as n FROM private_brain_records WHERE status = 'active'"
        ).fetchone()
        archived = conn.execute(
            "SELECT COUNT(*) as n FROM private_brain_records WHERE status = 'archived'"
        ).fetchone()
    assert active["n"] <= 4  # at most 4 remain (to-keep = ceil(6*0.5) = 3)
    assert archived["n"] >= 2


# ── tick (integration smoke) ──────────────────────────────────────────


def test_tick_no_data_returns_empty(isolated_db):
    """Running the daemon tick with no data must return empty layers."""
    from core.services.selective_consolidation_daemon import (
        tick_selective_consolidation_daemon,
    )

    # Temporarily lower cadence for testing
    import core.services.selective_consolidation_daemon as scd
    original = scd._last_tick_at
    scd._last_tick_at = None  # force tick to fire

    try:
        result = tick_selective_consolidation_daemon()
        assert result["consolidated"] is True
        for layer in result["layers"]:
            assert "error" not in layer, f"layer error: {layer.get('error')}"
            assert layer.get("scored", 0) == 0
    finally:
        scd._last_tick_at = original


def test_tick_respects_cadence(isolated_db):
    """Running tick twice rapidly must skip second run."""
    import core.services.selective_consolidation_daemon as scd
    from core.services.selective_consolidation_daemon import (
        tick_selective_consolidation_daemon,
    )

    # Cadence state lives in a module-level global, not the DB — reset it so a
    # prior tick (e.g. from another test/file) doesn't make the first run here
    # return cadence_not_reached.
    scd._last_tick_at = None

    first = tick_selective_consolidation_daemon()
    assert first["consolidated"] is True

    second = tick_selective_consolidation_daemon()
    assert second["consolidated"] is False
    assert second["reason"] == "cadence_not_reached"


def test_surface_returns_metadata(isolated_db):
    """build_selective_consolidation_surface must return config."""
    from core.services.selective_consolidation_daemon import (
        build_selective_consolidation_surface,
    )
    surface = build_selective_consolidation_surface()
    assert "cadence_hours" in surface
    assert "top_k_percent" in surface
    assert surface["top_k_percent"] == 50
