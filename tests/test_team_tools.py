"""Tests for core.tools.team_tools (conversational team-tools + auto-session)."""
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.tools.team_tools as team_tools
import core.services.teams as teams


def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()


def test_exec_create_team_creates_team_and_default_session(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    r = team_tools.exec_create_team({"name": "Familie", "_user_id": "bjorn"})
    assert r["status"] == "ok"
    tid = r["team_id"]
    # Auto-session: et nyt team SKAL have én delt default-session, så det straks
    # kan åbnes (Mikkel-test 2026-06-20: 0 sessioner → ikke-klikbart).
    sessions = teams.list_team_sessions(tid)
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Team-chat"


def test_exec_create_team_requires_name(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    r = team_tools.exec_create_team({"name": "  ", "_user_id": "bjorn"})
    assert r["status"] == "error"
