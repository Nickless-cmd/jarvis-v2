"""Tests for db_interlanguage_blind.submit_answer mode-aware return.

Codex audit watchpoint 2026-05-22: real-mode must not leak per-trial
correctness from server. Demo-mode still receives feedback (rater
training). Tests pin this contract.
"""
import sqlite3
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def tmp_db(monkeypatch):
    """Point DB connection at a fresh temp file for test isolation."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)

    def _connect():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    import core.runtime.db_interlanguage_blind as mod
    monkeypatch.setattr(mod, "connect", _connect)
    yield db_path
    db_path.unlink(missing_ok=True)


def _seed_alpha_trial(conn, trial_id: str, true_peer: str, mode: str) -> None:
    from core.runtime.db_interlanguage_blind import (
        _ensure_interlanguage_blind_trials_table,
    )
    _ensure_interlanguage_blind_trials_table(conn)
    conn.execute(
        """INSERT INTO interlanguage_blind_trials
           (trial_id, session_id, trial_type, trial_index, mode,
            expression_text, true_peer_id, created_at, presented_at)
           VALUES (?, 'sess-test', 'alpha', 0, ?, 'eksempel', ?,
                   '2026-05-22T19:00', '2026-05-22T19:00')""",
        (trial_id, mode, true_peer),
    )
    conn.commit()


def test_real_mode_includes_correct_internally(tmp_db):
    """submit_answer ALWAYS computes correct (for storage/aggregate),
    even in real-mode. The HTTP route is what filters it on response."""
    from core.runtime.db_interlanguage_blind import submit_answer, connect
    with connect() as c:
        _seed_alpha_trial(c, "t-real-1", "jarvis", "real")
    result = submit_answer(trial_id="t-real-1", user_answer="jarvis")
    assert result["correct"] is True
    assert result["mode"] == "real"


def test_demo_mode_returns_correct(tmp_db):
    from core.runtime.db_interlanguage_blind import submit_answer, connect
    with connect() as c:
        _seed_alpha_trial(c, "t-demo-1", "jarvis", "demo")
    result = submit_answer(trial_id="t-demo-1", user_answer="claude")
    assert result["correct"] is False
    assert result["mode"] == "demo"


def test_submit_answer_returns_mode_field(tmp_db):
    """The mode field must always be present so the HTTP route can
    filter the response."""
    from core.runtime.db_interlanguage_blind import submit_answer, connect
    with connect() as c:
        _seed_alpha_trial(c, "t-mode-1", "claude", "real")
    result = submit_answer(trial_id="t-mode-1", user_answer="claude")
    assert "mode" in result
    assert result["mode"] in ("demo", "real")


def test_unknown_trial_raises(tmp_db):
    from core.runtime.db_interlanguage_blind import submit_answer
    with pytest.raises(ValueError, match="trial_id ikke fundet"):
        submit_answer(trial_id="t-nonexistent", user_answer="any")
