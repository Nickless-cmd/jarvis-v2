"""Teams REST-API (Teams-feature, spec 2026-06-20 §6). Scoper til auth'et bruger.

Apps (desktop + mobil) bruger disse til Teams-sidebar, opret/inviter/medlemsliste/
kick + accept. Al data-lag-logik bor i core.services.teams; her er kun HTTP-
adaption + scoping/rolle-gates (defense-in-depth oven på tool-laget).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import core.services.teams as teams

router = APIRouter(tags=["teams"])


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


class CreateTeamBody(BaseModel):
    name: str


class InviteBody(BaseModel):
    email: str = ""
    user_id: str = ""


def _team_view(t: dict) -> dict:
    members = [m for m in teams.list_members(t["team_id"]) if m["user_id"] != teams.JARVIS_USER_ID]
    return {"team_id": t["team_id"], "name": t["name"], "owner_user_id": t["owner_user_id"],
            "members": members}


@router.get("/teams")
async def list_teams() -> dict:
    uid = _current_user()
    if not uid:
        return {"teams": []}
    return {"teams": [_team_view(t) for t in teams.list_teams_for_user(uid)]}


@router.post("/teams")
async def create_team(body: CreateTeamBody) -> dict:
    uid = _current_user()
    if not uid:
        raise HTTPException(status_code=401, detail="ingen bruger-kontekst")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="team-navn mangler")
    t = teams.create_team(name, owner_user_id=uid)
    return _team_view(t)


@router.get("/teams/{team_id}/members")
async def team_members(team_id: str) -> dict:
    uid = _current_user()
    if not uid or not teams.is_member(team_id, uid):
        raise HTTPException(status_code=403, detail="ikke medlem af teamet")
    return {"members": [m for m in teams.list_members(team_id)
                        if m["user_id"] != teams.JARVIS_USER_ID]}


@router.post("/teams/{team_id}/invite")
async def invite(team_id: str, body: InviteBody) -> dict:
    uid = _current_user()
    if not uid:
        raise HTTPException(status_code=401, detail="ingen bruger-kontekst")
    if not teams.can_admin(team_id, uid):
        raise HTTPException(status_code=403, detail="kun team-owner kan invitere")
    from core.tools.team_tools import exec_invite_to_team
    r = exec_invite_to_team({"team_id": team_id, "email": body.email,
                             "user_id": body.user_id, "_user_id": uid})
    if r.get("status") != "ok":
        raise HTTPException(status_code=400, detail=r.get("error", "invite fejlede"))
    return {"token": r["token"], "invited": r["invited"], "delivered": r.get("delivered", {})}


class TeamSessionBody(BaseModel):
    title: str = "Team-chat"


@router.get("/teams/{team_id}/sessions")
async def team_sessions(team_id: str) -> dict:
    uid = _current_user()
    if not uid or not teams.is_member(team_id, uid):
        raise HTTPException(status_code=403, detail="ikke medlem af teamet")
    return {"sessions": teams.list_team_sessions(team_id)}


@router.post("/teams/{team_id}/sessions")
async def create_team_session(team_id: str, body: TeamSessionBody) -> dict:
    uid = _current_user()
    if not uid or not teams.is_member(team_id, uid):
        raise HTTPException(status_code=403, detail="ikke medlem af teamet")
    from core.services.chat_sessions import create_chat_session
    s = create_chat_session(title=(body.title or "Team-chat"), team_id=team_id)
    return {"session_id": s.get("session_id") or s.get("id"), "title": s.get("title")}


@router.post("/invites/{token}/accept")
async def accept(token: str) -> dict:
    uid = _current_user()
    if not uid:
        raise HTTPException(status_code=401, detail="ingen bruger-kontekst")
    try:
        team_id = teams.accept_invite(token, accepting_user_id=uid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "team_id": team_id}


@router.delete("/teams/{team_id}/members/{target_user_id}")
async def kick(team_id: str, target_user_id: str) -> dict:
    uid = _current_user()
    if not uid:
        raise HTTPException(status_code=401, detail="ingen bruger-kontekst")
    try:
        teams.remove_member(team_id, target_user_id, acting_user_id=uid)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return {"ok": True}
