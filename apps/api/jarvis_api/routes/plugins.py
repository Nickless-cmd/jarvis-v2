"""Plugins & Kanaler routes (spec §5.4, Fase 6 #2). Tynde — blokerende arbejde
via asyncio.to_thread (--workers 1 frys-fælde). Kun owner: regelsæt er privatlivs-
og sikkerheds-relevant. Plugin-rammen er §14-deferred, så 'available/connected'
er pt. tomme lister; den funktionelle del er regelsæt-editoren (plugin_ruleset)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/plugins", tags=["plugins"])


def _require_owner() -> None:
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid is None:
        return  # ubundet (no-auth) = owner
    try:
        from core.identity.users import find_user_by_discord_id
        if getattr(find_user_by_discord_id(str(uid)), "role", "") == "owner":
            return
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="plugins/regelsæt er kun for owner")


@router.get("")
async def plugins_overview() -> dict:
    """Oversigt: tilgængelige plugins (manifester) + status + regelsæt."""
    _require_owner()
    from core.services.channel_inbound import register_builtin_channel_plugins
    from core.plugins.base_plugin import available_plugins, get_status
    from core.services.plugin_ruleset_store import list_rulesets
    register_builtin_channel_plugins()

    def _gather() -> dict:
        manifests = [m.as_dict() for m in available_plugins()]
        connected = [
            {"plugin_id": m["plugin_id"], **get_status(m["plugin_id"])}
            for m in manifests
        ]
        return {"available": manifests, "connected": connected, "rulesets": list_rulesets()}

    return await asyncio.to_thread(_gather)


@router.post("/channel/{plugin_id}/status")
async def channel_status(plugin_id: str, status: str, detail: str = "") -> dict:
    """Lokal gateway rapporterer sin forbindelses-status (connected|failed|offline)."""
    _require_owner()
    from core.plugins.base_plugin import set_status
    await asyncio.to_thread(set_status, plugin_id, status, detail=detail)
    return {"status": "ok", "plugin_id": plugin_id, "reported": status}


@router.post("/channel/{plugin_id}/inbound")
async def channel_inbound_ep(plugin_id: str, body: dict) -> dict:
    """Lokal gateway ruter en indkommende besked hertil. Serveren HÅNDHÆVER
    plugin_ruleset (hardblock, §5.3) før Jarvis kaldes. Returnerer allow-beslutning;
    ved allow dispatches en Jarvis-run (svar-routing til gateway: Lag 2)."""
    _require_owner()
    from core.services.channel_inbound import route_inbound

    channel = str(body.get("channel") or "")
    text = str(body.get("text") or "")
    author_role = str(body.get("author_role") or "")
    hour = int(body.get("hour", -1))

    gate = await asyncio.to_thread(
        route_inbound, plugin_id=plugin_id, channel=channel,
        author_role=author_role, text=text, hour=hour,
    )
    if not gate["allowed"]:
        return {"allowed": False, "reason": gate["reason"]}

    # Dispatch en run for kanal-beskeden (best-effort, ikke-blokerende).
    session_id = f"plugin-{plugin_id}-{channel}"
    try:
        from core.services.visible_runs import start_autonomous_run
        await asyncio.to_thread(start_autonomous_run, text, session_id=session_id)
    except Exception:
        pass
    return {"allowed": True, "session_id": session_id, "reason": "dispatched"}


@router.get("/rulesets/{plugin_id}")
async def get_plugin_ruleset(plugin_id: str) -> dict:
    _require_owner()
    from core.services.plugin_ruleset_store import get_ruleset
    rs = await asyncio.to_thread(get_ruleset, plugin_id)
    return {"plugin_id": plugin_id, "ruleset": rs}


@router.put("/rulesets/{plugin_id}")
async def put_plugin_ruleset(plugin_id: str, ruleset: dict) -> dict:
    """Gem regelsæt for et kanal-plugin. Hardblock for ALLE inkl. owner (§5.3)."""
    _require_owner()
    from core.services.plugin_ruleset_store import set_ruleset
    saved = await asyncio.to_thread(set_ruleset, plugin_id, ruleset)
    return {"plugin_id": plugin_id, "ruleset": saved}
