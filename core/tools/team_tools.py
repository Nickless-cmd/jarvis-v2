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
    # Auto-opret én default delt session så teamet straks kan åbnes (ellers
    # synligt men ikke-klikbart, 0 sessioner — Mikkel-test 2026-06-20).
    try:
        from core.services.chat_sessions import create_chat_session
        create_chat_session(title="Team-chat", team_id=t["team_id"])
    except Exception:
        pass
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


def _looks_like_email(s: str) -> bool:
    return "@" in s and "." in s.split("@")[-1]


def _deliver_invite(team_id: str, invitee: str, token: str, inviter: str) -> dict[str, bool]:
    """Best-effort levering: in-app proactive-kort til en eksisterende bruger +
    email hvis invitee er en email-adresse. Kaster aldrig."""
    delivered = {"in_app": False, "email": False}
    team = teams.get_team(team_id)
    team_name = team["name"] if team else "et team"

    # Resolve til eksisterende bruger → in-app-kort via presence-routing.
    target_uid = invitee
    if _looks_like_email(invitee):
        try:
            from core.identity.user_db import find_user_by_email
            u = find_user_by_email(invitee)
            target_uid = (u or {}).get("user_id") or ""
        except Exception:
            target_uid = ""
    if target_uid:
        try:
            import core.services.proactive_router as pr
            pr.route(target_uid, {
                "kind": "team_invite",
                "title": f"Invitation til {team_name}",
                "preview": f"{inviter} inviterede dig til {team_name}",
                "team_id": team_id, "token": token,
            }, "team_invite")
            delivered["in_app"] = True
        except Exception:
            pass

    # Email hvis invitee er en email-adresse.
    if _looks_like_email(invitee):
        try:
            from core.tools.mail_tools import _exec_send_mail
            r = _exec_send_mail({
                "to": invitee,
                "subject": f"Du er inviteret til {team_name} i Jarvis",
                "body": (f"{inviter} har inviteret dig til teamet '{team_name}'.\n\n"
                         f"Åbn Jarvis-appen og acceptér invitationen.\n"
                         f"Invite-kode: {token}\n"),
            })
            delivered["email"] = bool(r.get("success"))
        except Exception:
            pass
    return delivered


def exec_invite_to_team(args: dict[str, Any]) -> dict[str, Any]:
    team_id = str(args.get("team_id") or "").strip()
    invitee = str(args.get("email") or args.get("user_id") or "").strip()
    uid = _current_uid(args)
    if not team_id or not invitee:
        return {"status": "error", "error": "team_id og email/user_id kræves"}
    if not teams.can_admin(team_id, uid):
        return {"status": "error", "error": "kun team-owner kan invitere"}
    tok = teams.create_invite(team_id, invited_email=invitee, invited_by=uid)
    delivered = _deliver_invite(team_id, invitee, tok, uid)
    ways = [k for k, v in delivered.items() if v]
    msg = (f"Invite sendt til {invitee} via {', '.join(ways)}." if ways
           else f"Invite oprettet til {invitee}, men kunne ikke leveres automatisk "
                f"(de skal bruge koden i app'en).")
    return {"status": "ok", "token": tok, "invited": invitee,
            "delivered": delivered, "message": msg}
