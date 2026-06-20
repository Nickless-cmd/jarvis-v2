"""Team data-lag: CRUD, medlemskab, rolle-opslag, scope-helper (Teams-feature,
spec 2026-06-20).

Eneste sted team-tabellerne tilgås. Holder scoping-reglen (regel B) ÉT sted så
chat_sessions + session_search deler den. 'jarvis'-rollen = deltager, ikke admin.
"""
from __future__ import annotations

import time
import uuid

from core.runtime.db import connect
from core.runtime.workspace_paths import team_dir

JARVIS_USER_ID = "jarvis"


def _now_iso() -> str:  # injicerbart i tests
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_id() -> str:  # injicerbart i tests
    return f"team-{uuid.uuid4().hex[:12]}"


def create_team(name: str, *, owner_user_id: str) -> dict:
    """Opret team + git-workspace; opretteren bliver owner, Jarvis bliver deltager."""
    tid = _new_id()
    ws = str(team_dir(tid))  # opretter + git-init'er mappen
    now = _now_iso()
    with connect() as conn:
        conn.execute(
            "INSERT INTO teams (team_id, name, owner_user_id, created_at, workspace_path) "
            "VALUES (?, ?, ?, ?, ?)",
            (tid, name.strip(), owner_user_id, now, ws),
        )
        conn.execute(
            "INSERT INTO team_members (team_id, user_id, team_role, joined_at) VALUES (?, ?, 'owner', ?)",
            (tid, owner_user_id, now),
        )
        conn.execute(
            "INSERT INTO team_members (team_id, user_id, team_role, joined_at) VALUES (?, ?, 'jarvis', ?)",
            (tid, JARVIS_USER_ID, now),
        )
    return {"team_id": tid, "name": name.strip(), "owner_user_id": owner_user_id,
            "created_at": now, "workspace_path": ws}


def add_member(team_id: str, user_id: str, team_role: str = "editor") -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO team_members (team_id, user_id, team_role, joined_at) "
            "VALUES (?, ?, ?, ?)",
            (team_id, user_id, team_role, _now_iso()),
        )


def member_role(team_id: str, user_id: str) -> str | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT team_role FROM team_members WHERE team_id = ? AND user_id = ?",
            (team_id, user_id),
        ).fetchone()
    return row[0] if row else None


def is_member(team_id: str, user_id: str) -> bool:
    return member_role(team_id, user_id) is not None


def list_members(team_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT user_id, team_role, joined_at FROM team_members WHERE team_id = ? ORDER BY joined_at",
            (team_id,),
        ).fetchall()
    return [{"user_id": r[0], "team_role": r[1], "joined_at": r[2]} for r in rows]


def list_teams_for_user(user_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT t.team_id, t.name, t.owner_user_id, t.created_at, t.workspace_path "
            "FROM teams t JOIN team_members m ON m.team_id = t.team_id "
            "WHERE m.user_id = ? ORDER BY t.created_at DESC",
            (user_id,),
        ).fetchall()
    return [{"team_id": r[0], "name": r[1], "owner_user_id": r[2],
             "created_at": r[3], "workspace_path": r[4]} for r in rows]


def get_team(team_id: str) -> dict | None:
    with connect() as conn:
        r = conn.execute(
            "SELECT team_id, name, owner_user_id, created_at, workspace_path FROM teams WHERE team_id = ?",
            (team_id,),
        ).fetchone()
    if not r:
        return None
    return {"team_id": r[0], "name": r[1], "owner_user_id": r[2],
            "created_at": r[3], "workspace_path": r[4]}


# ── Scoping-regel B (delt mellem chat_sessions + session_search) ───────────────
def team_scope_sql(session_alias: str = "s") -> str:
    """SQL-fragment: 'sessionen er en team-session jeg er medlem af'. Bruger
    placeholder ? for user_id. Returneres UDEN ledende OR — kalderen wrapper."""
    return (
        f"({session_alias}.team_id IS NOT NULL AND EXISTS ("
        f"SELECT 1 FROM team_members tmx WHERE tmx.team_id = {session_alias}.team_id "
        f"AND tmx.user_id = ?))"
    )


# ── Rolle-håndhævelse ──────────────────────────────────────────────────────────
def can_admin(team_id: str, user_id: str) -> bool:
    return member_role(team_id, user_id) == "owner"


def remove_member(team_id: str, user_id: str, *, acting_user_id: str) -> None:
    if not can_admin(team_id, acting_user_id):
        raise PermissionError("kun team-owner kan fjerne medlemmer")
    if user_id == JARVIS_USER_ID:
        raise PermissionError("Jarvis kan ikke fjernes fra et team")
    with connect() as conn:
        conn.execute("DELETE FROM team_members WHERE team_id = ? AND user_id = ?", (team_id, user_id))
