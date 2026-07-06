import sqlite3
from datetime import UTC, datetime, timedelta
from unittest import mock
import pytest
from core.services import central_dream_action as da


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "d.db")
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE central_hypotheses (hyp_id TEXT PRIMARY KEY, statement TEXT,
        prediction TEXT, confidence REAL, grounded_samples INT, status TEXT, created_at TEXT,
        resolved_at TEXT)""")
    conn.commit(); conn.close()

    def _connect():
        c = sqlite3.connect(path); c.row_factory = sqlite3.Row; return c

    with mock.patch("core.services.central_dream_action.connect", side_effect=_connect), \
            mock.patch("core.services.central_dream_action._observe"):
        yield path


def _add(path, hyp_id, conf, samples, status="active", resolved_at=None):
    c = sqlite3.connect(path)
    c.execute("INSERT INTO central_hypotheses VALUES (?,?,?,?,?,?,?,?)",
              (hyp_id, f"stmt {hyp_id}", "pred", conf, samples, status,
               datetime.now(UTC).isoformat(), resolved_at))
    c.commit(); c.close()


def test_select_actionable_only_mature(db):
    _add(db, "h1", 0.9, 5)                  # moden
    _add(db, "h2", 0.4, 5)                  # for lav confidence
    _add(db, "h3", 0.9, 1)                  # for få samples
    _add(db, "h4", 0.8, 4, status="falsified")  # ikke aktiv
    got = {h["hyp_id"] for h in da.select_actionable()}
    assert got == {"h1"}


def test_recorded_action_excludes_from_actionable(db):
    _add(db, "h1", 0.9, 5)
    da.record_action("h1", action="handlede", result="virkede")
    assert da.select_actionable() == []     # allerede handlet → ikke igen


def test_change_rate_counts_resolved_vs_backlog(db):
    _add(db, "h1", 0.9, 5, status="active")
    _add(db, "h2", 0.9, 5, status="active")
    _add(db, "h3", 0.9, 5, status="confirmed",
         resolved_at=datetime.now(UTC).isoformat())
    cr = da.change_rate(window_days=7)
    assert cr["active_backlog"] == 2 and cr["resolved_in_window"] == 1
    assert 0 < cr["change_ratio"] < 1


def test_surface_flags_accumulation(db):
    for i in range(12):
        _add(db, f"b{i}", 0.5, 1)           # backlog, ingen modne
    surf = da.build_dream_action_surface()
    assert surf["actionable"] == []
    assert "forandrer mig for langsomt" in surf["felt"]
