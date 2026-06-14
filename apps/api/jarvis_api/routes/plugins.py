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
    """Oversigt: tilgængelige/forbundne plugins (skelet — §14-deferred) + regelsæt."""
    _require_owner()
    from core.services.plugin_ruleset_store import list_rulesets
    rulesets = await asyncio.to_thread(list_rulesets)
    return {
        "available": [],   # plugin-ramme deferred (§14: gateways-først)
        "connected": [],
        "rulesets": rulesets,
    }


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
