"""Teams Fase 1 — datamodel, scoping-regel A/B, workspace, guard, roller."""
import pytest

import core.runtime.db as db
import core.runtime.db_core as db_core


def _fresh_db(tmp_path, monkeypatch):
    """Redirect DB'en til en tom temp-fil. DB_PATH er en modul-konstant i db_core
    (sættes ved import), så connect() læser db_core.DB_PATH — patch DEN."""
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    db.init_db()


def test_teams_tables_exist_after_init(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()}
    assert {"teams", "team_members", "team_invites"} <= names
    assert "team_id" in cols


def test_team_dir_creates_git_repo(tmp_path, monkeypatch):
    import core.runtime.workspace_paths as wp
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    d = wp.team_dir("team-xyz")
    assert d.exists()
    assert (d.parent / ".git").exists()  # git-init'et på repo-roden over workspace
    assert "teams/team-xyz/workspace" in str(d)
