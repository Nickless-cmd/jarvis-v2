from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture()
def events_table(tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "events.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, payload_json TEXT, created_at TEXT)"
    )

    def fake_connect():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("core.runtime.db.connect", fake_connect)
    return conn


def test_fetch_broken_decisions_returns_recent_events(events_table):
    now = datetime.now(UTC)
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("decision_revoked", json.dumps({"reason": "vi tog det forkerte valg"}), now.isoformat()),
    )
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("conflict.detected", json.dumps({"description": "uoverensstemmelse om scope"}),
         (now - timedelta(days=2)).isoformat()),
    )
    # Old event → outside 7-day window
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("decision_revoked", json.dumps({"reason": "gammel sag"}),
         (now - timedelta(days=14)).isoformat()),
    )
    events_table.commit()

    from core.services.creative_journal_runtime import _fetch_broken_decisions

    out = _fetch_broken_decisions()
    assert len(out) == 2
    assert any("forkerte valg" in s for s in out)
    assert all("gammel sag" not in s for s in out)


def test_fetch_affective_klangbraet_present_keys():
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    out = _fetch_affective_klangbraet()
    assert isinstance(out, dict)
    assert set(out.keys()) == {"dream_bias", "user_temperature", "current_pull"}
