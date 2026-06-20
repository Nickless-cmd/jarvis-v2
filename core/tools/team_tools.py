"""Native team-tools til Jarvis (Teams-feature, spec 2026-06-20).

Conversational laget: Jarvis kan oprette teams, liste dem, og invitere medlemmer.
Tynde exec-wrappers oven på core.services.teams. Levering af invites (email +
in-app-kort) wires i Fase 2b — her oprettes selve invite-token'et + admin-gate.
"""
from __future__ import annotations

from typing import Any

import core.services.teams as teams


def _current_uid(args: dict[str, Any]) -> str:
    uid = str(args.get("_user_id") or args.get("owner_user_id") or "").strip()
    if uid:
        return uid
    try:
        from core.identity.workspace_context import current_user_id
        return current_user_id() or ""
    except Exception:
        return ""


def exec_create_team(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "team-navn mangler"}
    uid = _current_uid(args)
    if not uid:
        return {"status": "error", "error": "kunne ikke afgøre hvem der opretter teamet"}
    t = teams.create_team(name, owner_user_id=uid)
    return {"status": "ok", "team_id": t["team_id"], "name": t["name"],
            "message": f"Team '{t['name']}' oprettet — du er owner."}


def exec_list_teams(args: dict[str, Any]) -> dict[str, Any]:
    uid = _current_uid(args)
    if not uid:
        return {"status": "error", "error": "ingen bruger-kontekst"}
    mine = teams.list_teams_for_user(uid)
    return {"status": "ok", "count": len(mine),
            "teams": [{"team_id": t["team_id"], "name": t["name"],
                       "members": [m["user_id"] for m in teams.list_members(t["team_id"])
                                   if m["user_id"] != teams.JARVIS_USER_ID]}
                      for t in mine]}


def exec_invite_to_team(args: dict[str, Any]) -> dict[str, Any]:
    team_id = str(args.get("team_id") or "").strip()
    invitee = str(args.get("email") or args.get("user_id") or "").strip()
    uid = _current_uid(args)
    if not team_id or not invitee:
        return {"status": "error", "error": "team_id og email/user_id kræves"}
    if not teams.can_admin(team_id, uid):
        return {"status": "error", "error": "kun team-owner kan invitere"}
    tok = teams.create_invite(team_id, invited_email=invitee, invited_by=uid)
    # Levering (in-app-kort + email) wires i Fase 2b. Her returneres token'et.
    return {"status": "ok", "token": tok, "invited": invitee,
            "message": f"Invite oprettet til {invitee}. (Levering kommer i næste fase.)"}
