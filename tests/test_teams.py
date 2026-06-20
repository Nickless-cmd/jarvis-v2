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


import core.services.chat_sessions as cs  # noqa: E402


def _post(session_id, user_id, team_id=None):
    """Opret session (+ team_id) og en besked stemplet med user_id."""
    with db.connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chat_sessions (session_id, title, created_at, updated_at, team_id) "
            "VALUES (?, ?, ?, ?, ?)", (session_id, session_id, "2026", "2026", team_id))
        conn.execute(
            "INSERT INTO chat_messages (message_id, session_id, role, content, user_id, created_at) "
            "VALUES (?, ?, 'user', 'hi', ?, '2026')", (f"m-{session_id}-{user_id}", session_id, user_id))


def test_private_session_only_visible_to_author(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    _post("priv1", "bjorn")
    assert {s["id"] for s in cs.list_chat_sessions(user_id="bjorn")} == {"priv1"}
    assert cs.list_chat_sessions(user_id="mikkel") == []  # #154 urørt


def test_team_session_visible_to_all_members(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    teams.add_member(t["team_id"], "mikkel")
    _post("team-s1", "bjorn", team_id=t["team_id"])  # kun bjorn har postet
    # Mikkel har IKKE postet, men er medlem → skal SE den (regel B)
    assert "team-s1" in {s["id"] for s in cs.list_chat_sessions(user_id="mikkel")}


def test_non_member_cannot_see_team_session(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    _post("team-s2", "bjorn", team_id=t["team_id"])
    assert cs.list_chat_sessions(user_id="fremmed") == []  # ikke-medlem afvist


import core.services.cross_user_share_guard as guard  # noqa: E402


def test_guard_allows_cross_user_inside_team_session(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    teams.add_member(t["team_id"], "mikkel")
    _post("team-s3", "bjorn", team_id=t["team_id"])
    known = [{"id": "mikkel", "name": "Mikkel"}]
    # Uden team-session ville "Mikkel" flagges:
    base = guard.check_outbound("Mikkel spurgte om X", current_user_id="bjorn", known_users=known)
    assert base["needs_confirmation"] is True
    # I team-sessionen skal det IKKE flagges (delt kontekst):
    res = guard.check_outbound("Mikkel spurgte om X", current_user_id="bjorn",
                               known_users=known, session_id="team-s3")
    assert res["needs_confirmation"] is False


def test_only_owner_can_admin(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    teams.add_member(t["team_id"], "mikkel")
    assert teams.can_admin(t["team_id"], "bjorn") is True
    assert teams.can_admin(t["team_id"], "mikkel") is False
    assert teams.can_admin(t["team_id"], "jarvis") is False


def test_kick_requires_admin(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    teams.add_member(t["team_id"], "mikkel")
    with pytest.raises(PermissionError):
        teams.remove_member(t["team_id"], "mikkel", acting_user_id="mikkel")
    with pytest.raises(PermissionError):
        teams.remove_member(t["team_id"], "jarvis", acting_user_id="bjorn")  # Jarvis kan ikke fjernes
    teams.remove_member(t["team_id"], "mikkel", acting_user_id="bjorn")
    assert teams.is_member(t["team_id"], "mikkel") is False


def test_invite_lifecycle_create_get_accept(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    tok = teams.create_invite(t["team_id"], invited_email="mikkel@x.dk", invited_by="bjorn")
    inv = teams.get_invite(tok)
    assert inv["status"] == "pending" and inv["team_id"] == t["team_id"]
    # accept → bliver medlem (editor) + status accepted
    tid = teams.accept_invite(tok, accepting_user_id="mikkel")
    assert tid == t["team_id"]
    assert teams.member_role(t["team_id"], "mikkel") == "editor"
    assert teams.get_invite(tok)["status"] == "accepted"


def test_invite_cannot_be_accepted_twice(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    tok = teams.create_invite(t["team_id"], invited_email="m@x.dk", invited_by="bjorn")
    teams.accept_invite(tok, accepting_user_id="mikkel")
    with pytest.raises(ValueError):
        teams.accept_invite(tok, accepting_user_id="mikkel")


def test_expired_invite_rejected(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    # tving udløb i fortiden
    monkeypatch.setattr(teams, "_invite_expiry_iso", lambda: "2000-01-01T00:00:00Z")
    tok = teams.create_invite(t["team_id"], invited_email="m@x.dk", invited_by="bjorn")
    with pytest.raises(ValueError):
        teams.accept_invite(tok, accepting_user_id="mikkel")


import core.tools.team_tools as tt  # noqa: E402


def test_tool_create_and_list(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    r = tt.exec_create_team({"name": "Eng", "_user_id": "bjorn"})
    assert r["status"] == "ok"
    lst = tt.exec_list_teams({"_user_id": "bjorn"})
    assert lst["count"] == 1 and lst["teams"][0]["members"] == ["bjorn"]  # jarvis filtreret væk


def test_tool_invite_requires_admin(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    teams.add_member(t["team_id"], "mikkel")  # editor, ikke admin
    bad = tt.exec_invite_to_team({"team_id": t["team_id"], "email": "x@y.dk", "_user_id": "mikkel"})
    assert bad["status"] == "error"
    ok = tt.exec_invite_to_team({"team_id": t["team_id"], "email": "x@y.dk", "_user_id": "bjorn"})
    assert ok["status"] == "ok" and ok["token"]


import core.services.team_mentions as tm  # noqa: E402


def test_parse_mentions_classifies():
    r = tm.parse_mentions("hej @mikkel kan du se @jarvis og @ukendt?", ["bjorn", "mikkel"])
    assert r["jarvis"] is True
    assert r["members"] == ["mikkel"]  # @ukendt ignoreret, @jarvis ikke i members


def test_parse_mentions_no_jarvis():
    r = tm.parse_mentions("@bjorn tjek lige", ["bjorn", "mikkel"])
    assert r["jarvis"] is False and r["members"] == ["bjorn"]


def test_should_jarvis_respond_summoned():
    assert tm.should_jarvis_respond("@jarvis hjælp") is True
    assert tm.should_jarvis_respond("bare en intern besked") is False
    assert tm.should_jarvis_respond("tak", is_reply_to_jarvis=True) is True


def test_mention_word_boundary_no_email():
    # en email skal ikke fanges som mention
    assert tm.extract_mentions("skriv til mikkel@x.dk") == []


def test_autocommit_records_author(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    import core.runtime.workspace_paths as wp
    ws = wp.team_dir(t["team_id"])
    (ws / "rapport.txt").write_text("data")
    ok = teams.autocommit(t["team_id"], message="upload rapport.txt", author_user_id="mikkel")
    assert ok is True
    import subprocess
    base = ws.parent
    log = subprocess.run(["git", "log", "-1", "--format=%an|%s"], cwd=str(base),
                         capture_output=True, text=True).stdout.strip()
    assert log == "mikkel|upload rapport.txt"
    # intet nyt → returnerer False (intet at committe)
    assert teams.autocommit(t["team_id"], message="noop", author_user_id="mikkel") is False


def test_invite_delivery_in_app_and_email(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    calls = {"route": [], "mail": []}
    import core.services.proactive_router as pr
    import core.tools.mail_tools as mail
    import core.identity.user_db as udb
    monkeypatch.setattr(pr, "route", lambda uid, payload, kind: calls["route"].append((uid, kind)))
    monkeypatch.setattr(mail, "_exec_send_mail", lambda a: calls["mail"].append(a["to"]) or {"success": True})
    monkeypatch.setattr(udb, "find_user_by_email", lambda e: {"user_id": "mikkel"})
    r = tt.exec_invite_to_team({"team_id": t["team_id"], "email": "mikkel@x.dk", "_user_id": "bjorn"})
    assert r["status"] == "ok"
    assert r["delivered"] == {"in_app": True, "email": True}
    assert calls["route"] == [("mikkel", "team_invite")]
    assert calls["mail"] == ["mikkel@x.dk"]


import asyncio  # noqa: E402
import apps.api.jarvis_api.routes.teams as troute  # noqa: E402
import pytest  # noqa: E402


def _as(monkeypatch, uid):
    monkeypatch.setattr(troute, "_current_user", lambda: uid)


def test_route_create_list_members(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    _as(monkeypatch, "bjorn")
    created = asyncio.run(troute.create_team(troute.CreateTeamBody(name="Eng")))
    tid = created["team_id"]
    lst = asyncio.run(troute.list_teams())
    assert [t["name"] for t in lst["teams"]] == ["Eng"]
    mem = asyncio.run(troute.team_members(tid))
    assert [m["user_id"] for m in mem["members"]] == ["bjorn"]  # jarvis skjult


def test_route_non_member_cannot_see_members(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    _as(monkeypatch, "fremmed")
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        asyncio.run(troute.team_members(t["team_id"]))
    assert ei.value.status_code == 403


def test_route_invite_and_accept(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    # deaktiver faktisk levering i invite
    import core.tools.team_tools as ttmod
    monkeypatch.setattr(ttmod, "_deliver_invite", lambda *a, **k: {"in_app": False, "email": False})
    _as(monkeypatch, "bjorn")
    r = asyncio.run(troute.invite(t["team_id"], troute.InviteBody(user_id="mikkel")))
    tok = r["token"]
    _as(monkeypatch, "mikkel")
    acc = asyncio.run(troute.accept(tok))
    assert acc["ok"] and teams.member_role(t["team_id"], "mikkel") == "editor"


def test_route_kick_requires_admin(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    t = teams.create_team("Eng", owner_user_id="bjorn")
    teams.add_member(t["team_id"], "mikkel")
    from fastapi import HTTPException
    _as(monkeypatch, "mikkel")
    with pytest.raises(HTTPException) as ei:
        asyncio.run(troute.kick(t["team_id"], "mikkel"))
    assert ei.value.status_code == 403
    _as(monkeypatch, "bjorn")
    assert asyncio.run(troute.kick(t["team_id"], "mikkel"))["ok"]
