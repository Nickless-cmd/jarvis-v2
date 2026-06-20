"""Teams Fase 1 — datamodel, scoping-regel A/B, workspace, guard, roller."""
import pytest

import core.runtime.db as db
import core.runtime.db_core as db_core


def _fresh_db(tmp_path, monkeypatch):
    """Redirect DB'en til en tom temp-fil. DB_PATH er en modul-konstant i db_core
    (sættes ved import), så connect() læser db_core.DB_PATH — patch DEN. Sæt også
    JARVIS_HOME så team_dir() git-init'er under temp (ikke ~/.jarvis-v2)."""
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
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


import core.services.teams as teams  # noqa: E402


def test_create_team_makes_owner_and_jarvis_members(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    monkeypatch.setattr(teams, "_now_iso", lambda: "2026-06-20T00:00:00Z")
    monkeypatch.setattr(teams, "_new_id", lambda: "team-abc")
    t = teams.create_team("Engineering", owner_user_id="bjorn")
    assert t["team_id"] == "team-abc"
    assert teams.is_member("team-abc", "bjorn") is True
    assert teams.member_role("team-abc", "bjorn") == "owner"
    assert teams.member_role("team-abc", "jarvis") == "jarvis"


def test_list_teams_for_user(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    teams.create_team("A", owner_user_id="bjorn")
    teams.create_team("B", owner_user_id="mikkel")
    mine = {t["name"] for t in teams.list_teams_for_user("bjorn")}
    assert mine == {"A"}


def test_add_member_default_editor(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("A", owner_user_id="bjorn")
    teams.add_member(t["team_id"], "mikkel")
    assert teams.member_role(t["team_id"], "mikkel") == "editor"
    names = {m["user_id"] for m in teams.list_members(t["team_id"])}
    assert names == {"bjorn", "jarvis", "mikkel"}
