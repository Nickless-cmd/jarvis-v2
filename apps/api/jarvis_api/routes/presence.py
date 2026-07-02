"""Device-presence + proaktive desktop-notifikationer. Scoper til auth'et bruger."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import core.services.desktop_notifications as desktop_notifications
import core.services.device_presence as device_presence
import core.services.notification_router as notification_router

router = APIRouter(tags=["presence"])


class PingBody(BaseModel):
    device_key: str
    platform: str
    foreground: bool = False
    awake: bool = True
    network: str = "unknown"
    interaction: bool = False
    # Opt-in geolocation. None = ingen ændring; {} = brugeren slog det FRA (ryd);
    # {lat,lon,label,source,precision} = ny lokation.
    location: dict | None = None


class AckBody(BaseModel):
    notif_id: str


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


@router.post("/presence/ping")
async def presence_ping(body: PingBody) -> dict:
    uid = _current_user()
    if not uid or not (body.device_key or "").strip():
        return {"ok": False}
    device_presence.record_ping(
        uid, body.device_key, body.platform,
        foreground=body.foreground, awake=body.awake,
        network=body.network, interaction=body.interaction,
        location=body.location,
    )
    # Connections-cluster: forbindelses-livscyklus synlig i Centralen (metadata-only).
    try:
        from core.services.connections import note_presence
        note_presence(uid, body.device_key, body.platform,
                      foreground=body.foreground, network=body.network)
    except Exception:
        pass
    return {"ok": True}


@router.get("/notifications/pending")
async def notifications_pending() -> dict:
    uid = _current_user()
    if not uid:
        return {"items": []}
    return {"items": desktop_notifications.drain(uid)}


@router.post("/notifications/ack")
async def notifications_ack(body: AckBody) -> dict:
    if (body.notif_id or "").strip():
        notification_router.ack(body.notif_id)
    return {"ok": True}


@router.get("/notifications/preferences")
async def notification_preferences_get() -> dict:
    """Notif-routing §6: app-UI læser brugerens kanal-præferencer."""
    uid = _current_user()
    if not uid:
        raise HTTPException(status_code=401, detail="ingen bruger-kontekst")
    from core.services.notification_router import get_preferences
    return {"preferences": get_preferences(uid)}


@router.post("/notifications/preferences")
async def notification_preferences_set(body: dict) -> dict:
    """app-UI sætter kanal-præferencer (global + per-type + quiet hours)."""
    uid = _current_user()
    if not uid:
        raise HTTPException(status_code=401, detail="ingen bruger-kontekst")
    from core.services.notification_router import set_preferences
    allowed = {k: body[k] for k in
               ("global", "briefing", "reminder", "reach_out", "team_invite", "wakeup",
                "quiet_start", "quiet_end") if k in body and body[k] is not None}
    try:
        return {"preferences": set_preferences(uid, **allowed)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/presence/debug")
async def presence_debug() -> dict:
    uid = _current_user()
    if not uid:
        return {"error": "no user"}
    snap = device_presence.debug_snapshot(uid)
    # Dry-run: hvad ville route() levere til (uden at sende noget)?
    delivered: list[str] = []
    try:
        orig_fcm = notification_router._send_fcm
        orig_desk = notification_router._send_desktop
        orig_blast = notification_router._fallback_blast
        orig_timer = notification_router._arm_timer
        notification_router._send_fcm = lambda u, k, d: delivered.append(f"fcm:{k[:10]}")
        notification_router._send_desktop = lambda u, i: delivered.append(f"desktop_queue:{i.get('notif_id', '')[:10]}")
        notification_router._fallback_blast = lambda u, d: delivered.append("fallback_fcm_blast")
        notification_router._arm_timer = lambda n: None
        notification_router.route_device_aware(uid, {"kind": "initiative", "preview": "DRYRUN"}, "initiative")
    except Exception as e:
        delivered.append(f"error:{e}")
    finally:
        notification_router._send_fcm = orig_fcm
        notification_router._send_desktop = orig_desk
        notification_router._fallback_blast = orig_blast
        notification_router._arm_timer = orig_timer
        notification_router.reset_delivery()  # ryd dry-run pending
    snap["dryrun_delivers_to"] = delivered
    return snap


@router.get("/presence/state")
async def presence_state() -> dict:
    """Spec E / E0 — TILSTANDS-KONTRAKTEN: Centralens ægte valens + selv-tilstand → jarvis-desk kan
    drive tilstedeværelsen (orb/ansigt) fra hans FØLTE tilstand. OWNER-ONLY (privat inder-liv).
    Tekst+skalarer; klienten renderer. Self-safe → tom-neutral ved fejl."""
    uid = _current_user()
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        owner = (get_owner_discord_id() or "").strip()
    except Exception:
        owner = ""
    if not uid or not owner or uid != owner:
        raise HTTPException(status_code=403, detail="owner only")
    try:
        from core.services.central_valence import get_valence_state
        from core.services.central_self_state import get_self_state, describe_self, render_self_state_il
        val = get_valence_state() or {}
        st = get_self_state() or {}
        return {
            "valence": {"tone": val.get("tone") or "neutral", "score": val.get("score") or 0.0,
                        "intensity": val.get("intensity") or 0.0, "trend": val.get("trend")},
            "self": {"describe": describe_self(), "il": render_self_state_il(),
                     "attention": (st.get("attention") or {}).get("foreground"),
                     "completeness": (st.get("self_model") or {}).get("completeness")},
            "generation": (st.get("continuity") or {}).get("generation"),
        }
    except Exception:
        return {"valence": {"tone": "neutral", "score": 0.0, "intensity": 0.0, "trend": None},
                "self": {}, "generation": None}
