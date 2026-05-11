from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def fake_db(tmp_path, monkeypatch):
    """In-memory SQLite with aesthetic_motif_log + cognitive_taste_profiles tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE aesthetic_motif_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, motif TEXT, confidence REAL, created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE cognitive_taste_profiles (
            profile_id TEXT, version INTEGER, code_taste TEXT,
            design_taste TEXT, communication_taste TEXT,
            evidence_count INTEGER, updated_at TEXT
        )
    """)
    conn.commit()

    def fake_connect():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("core.runtime.db.connect", fake_connect)
    return conn


def test_fetch_recent_top_motif_empty_when_no_data(fake_db, monkeypatch):
    from core.services.creative_journal_runtime import _fetch_recent_top_motif
    assert _fetch_recent_top_motif() == ""


def test_fetch_recent_top_motif_returns_most_recent(fake_db, monkeypatch):
    from core.services.creative_journal_runtime import _fetch_recent_top_motif

    now = datetime.now(UTC)
    fake_db.execute(
        "INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at) VALUES (?,?,?,?)",
        ("daemon-a", "craft", 0.5, (now - timedelta(days=2)).isoformat()),
    )
    fake_db.execute(
        "INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at) VALUES (?,?,?,?)",
        ("daemon-b", "clarity", 0.7, (now - timedelta(hours=3)).isoformat()),
    )
    fake_db.commit()
    assert _fetch_recent_top_motif() == "clarity"


def test_fetch_recent_top_motif_filters_stale(fake_db, monkeypatch):
    from core.services.creative_journal_runtime import _fetch_recent_top_motif

    now = datetime.now(UTC)
    fake_db.execute(
        "INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at) VALUES (?,?,?,?)",
        ("daemon-old", "density", 0.5, (now - timedelta(days=14)).isoformat()),
    )
    fake_db.commit()
    assert _fetch_recent_top_motif() == ""


def test_fetch_dominant_taste_empty_when_no_profile(monkeypatch):
    from core.services import creative_journal_runtime as cjr
    import core.runtime.db as runtime_db
    monkeypatch.setattr(runtime_db, "get_latest_cognitive_taste_profile", lambda: None)
    assert cjr._fetch_dominant_taste() == ""


def test_fetch_dominant_taste_gated_on_evidence(monkeypatch):
    from core.services import creative_journal_runtime as cjr
    import core.runtime.db as runtime_db
    monkeypatch.setattr(
        runtime_db, "get_latest_cognitive_taste_profile",
        lambda: {
            "code_taste": json.dumps({"prefers_inline_styles": 0.9}),
            "design_taste": json.dumps({"compact_over_spacious": 0.5}),
            "communication_taste": json.dumps({"concise_over_verbose": 0.5}),
            "evidence_count": 3,
        },
    )
    assert cjr._fetch_dominant_taste() == ""


def test_fetch_dominant_taste_picks_largest_deviation(monkeypatch):
    from core.services import creative_journal_runtime as cjr
    import core.runtime.db as runtime_db
    monkeypatch.setattr(
        runtime_db, "get_latest_cognitive_taste_profile",
        lambda: {
            "code_taste": json.dumps({"prefers_inline_styles": 0.6}),
            "design_taste": json.dumps({"compact_over_spacious": 0.5}),
            "communication_taste": json.dumps({"concise_over_verbose": 0.85}),
            "evidence_count": 12,
        },
    )
    result = cjr._fetch_dominant_taste()
    assert "concise_over_verbose" in result
    assert "0.85" in result
