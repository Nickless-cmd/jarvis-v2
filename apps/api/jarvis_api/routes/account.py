"""Self-profile-route for cowork command center (spec §4.1 Account).

Enhver autentificeret bruger kan hente SIN EGEN profil-projektion — modsat
routes/users.py som er owner-only (/api/users/{id}). Privatlivs-reglen: en
bruger ser kun sig selv; ingen cross-bruger-opslag her.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from fastapi import APIRouter, Body

from core.identity import user_db
from core.identity.workspace_context import current_context_snapshot
from core.services import quota_store

router = APIRouter(prefix="/account", tags=["account"])


def build_account_profile(
    user_id: str,
    *,
    get_user: Callable[[str], dict[str, Any] | None],
    get_tier: Callable[[str], str],
) -> dict[str, Any]:
    """Ren projektion — testbar uden HTTP. Owner (uid='') har ingen række."""
    if not user_id:
        return {
            "user_id": "",
            "email": "",
            "email_verified": True,
            "language": "da",
            "role": "owner",
            "tier": get_tier("") or "owner",
        }
    row = get_user(user_id) or {}
    return {
        "user_id": user_id,
        "email": row.get("email", "") or "",
        "email_verified": bool(row.get("email_verified")),
        "language": row.get("language") or "da",
        "role": row.get("role") or "member",
        "tier": get_tier(user_id) or (row.get("tier") or "free"),
    }


@router.get("/me")
async def account_me() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    return await asyncio.to_thread(
        build_account_profile,
        user_id,
        get_user=user_db.get_user,
        get_tier=quota_store.get_tier,
    )


_QUOTA_KINDS = ("chat", "code", "cowork", "agent")


def build_quota_overview(
    user_id: str,
    *,
    check_quota: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Self-scope kvote-overblik: tier + forbrug pr. type. Ren — testbar uden HTTP."""
    items: list[dict[str, Any]] = []
    tier = ""
    for kind in _QUOTA_KINDS:
        q = check_quota(user_id, kind) or {}
        tier = tier or str(q.get("tier") or "")
        items.append({
            "kind": kind,
            "used": int(q.get("used") or 0),
            "limit": q.get("limit"),  # None = ubegrænset
            "remaining": q.get("remaining"),
            "warn": bool(q.get("warn")),
        })
    return {"tier": tier or "free", "items": items}


_VALID_LANGUAGES = ("da", "en", "auto")


@router.patch("/language")
async def account_set_language(payload: dict = Body(default={})) -> dict[str, Any]:
    """Self-scope sprogvalg. Owner (uid='') har ingen bruger-række → ingen DB-skrivning
    (owner bruger default-sproget)."""
    lang = str((payload or {}).get("language") or "").strip().lower()
    if lang not in _VALID_LANGUAGES:
        return {"status": "error", "error": f"sprog skal være en af {_VALID_LANGUAGES}"}
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    if user_id:
        await asyncio.to_thread(user_db.set_language, user_id, lang)
    return {"status": "ok", "language": lang}


@router.get("/quota")
async def account_quota() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    return await asyncio.to_thread(build_quota_overview, user_id, check_quota=quota_store.check_quota)
