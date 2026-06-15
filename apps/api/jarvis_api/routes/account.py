"""Self-profile-route for cowork command center (spec §4.1 Account).

Enhver autentificeret bruger kan hente SIN EGEN profil-projektion — modsat
routes/users.py som er owner-only (/api/users/{id}). Privatlivs-reglen: en
bruger ser kun sig selv; ingen cross-bruger-opslag her.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from fastapi import APIRouter, Body, HTTPException

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


def _summarize_dir(path) -> tuple[int, int]:
    """(antal filer, samlede bytes) under path. Manglende mappe → (0, 0)."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return (0, 0)
    files = 0
    total = 0
    for f in p.rglob("*"):
        try:
            if f.is_file():
                files += 1
                total += f.stat().st_size
        except OSError:
            continue
    return (files, total)


def build_workspace_overview(
    user_id: str,
    *,
    ws_dir: Callable[[str], Any],
    should_encrypt: Callable[[str], bool],
    is_trusted: Callable[..., bool],
) -> dict[str, Any]:
    """Self-scope workspace-overblik: fil-antal, disk-forbrug, kryptering, trust."""
    d = ws_dir(user_id)
    files, total = _summarize_dir(d)
    return {
        "path_name": getattr(d, "name", str(d)),
        "files": files,
        "disk_bytes": total,
        "encrypted": bool(should_encrypt(user_id)),
        "trusted": bool(is_trusted(user_id, "code", str(d))),
    }


@router.get("/workspace")
async def account_workspace() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    from core.runtime.workspace_paths import workspace_dir
    from core.services.workspace_crypto import should_encrypt
    from core.services.workspace_trust import is_trusted
    return await asyncio.to_thread(
        build_workspace_overview,
        user_id,
        ws_dir=workspace_dir,
        should_encrypt=should_encrypt,
        is_trusted=is_trusted,
    )


def build_memory_overview(
    user_id: str,
    *,
    ws_dir: Callable[[str], Any],
    read_text: Callable[[Any], str | None],
    recent_sensory: Callable[[], list[dict[str, Any]]],
    brain_count: Callable[[], int],
) -> dict[str, Any]:
    """Self-scope memory-overblik: MEMORY.md + USER.md (afkortet) + seneste
    sansninger + brain-antal. Privatliv: alt scopet til den aktuelle bruger."""
    d = ws_dir(user_id)
    return {
        "memory_md": (read_text(d / "MEMORY.md") or "")[:8000],
        "user_md": (read_text(d / "USER.md") or "")[:8000],
        "recent_sensory": recent_sensory(),
        "brain_count": brain_count(),
    }


@router.get("/memory")
async def account_memory() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""

    def _assemble() -> dict[str, Any]:
        from core.runtime.db_private_brain import list_private_brain_records
        from core.runtime.db_sensory import list_sensory_memories
        from core.runtime.workspace_paths import workspace_dir
        from core.services.workspace_crypto import read_text_for_path
        return build_memory_overview(
            user_id,
            ws_dir=workspace_dir,
            read_text=lambda p: read_text_for_path(str(p)),
            recent_sensory=lambda: list_sensory_memories(limit=5),
            brain_count=lambda: len(list_private_brain_records(limit=500)),
        )

    return await asyncio.to_thread(_assemble)


@router.get("/memory/search")
async def account_memory_search(q: str = "") -> dict[str, Any]:
    query = (q or "").strip()
    if not query:
        return {"results": []}
    from core.runtime.db_sensory import search_sensory_memories
    results = await asyncio.to_thread(search_sensory_memories, query=query, limit=20)
    return {"results": results}


def _current_role(user_id: str) -> str:
    if not user_id:
        return "owner"
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(user_id)
        return getattr(u, "role", "member") or "member"
    except Exception:
        return "member"


def build_permissions_overview(
    role: str,
    *,
    allowed_tools: Callable[..., Any],
) -> dict[str, Any]:
    """Tool-adgangs-matrix pr. mode for en rolle. Owner → 'all' (sentinel er ikke
    iterérbar); member → sorteret liste."""
    modes: list[dict[str, Any]] = []
    for mode in ("chat", "code", "cowork"):
        perm = allowed_tools(role=role, mode=mode)
        try:
            tools = sorted(perm)
            is_all = False
        except TypeError:
            tools = []
            is_all = True
        modes.append({"mode": mode, "all": is_all, "tools": tools})
    return {"role": role, "modes": modes}


@router.get("/permissions")
async def account_permissions() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    role = _current_role(user_id)
    from core.services.computer_use_policy import computer_use_enabled
    from core.services.permission_engine import allowed_tools
    ov = await asyncio.to_thread(build_permissions_overview, role, allowed_tools=allowed_tools)
    ov["computer_use_enabled"] = bool(computer_use_enabled(user_id))
    return ov


@router.patch("/computer-use")
async def account_set_computer_use(payload: dict = Body(default={})) -> dict[str, Any]:
    enabled = bool((payload or {}).get("enabled"))
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    from core.services.computer_use_policy import set_computer_use
    return await asyncio.to_thread(set_computer_use, user_id, enabled)


def build_jarvis_overview(*, lane_targets: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Model pr. lane (§4.2). Read-only projektion af provider-router-targets."""
    targets = lane_targets() or {}
    lanes = []
    for lane, t in targets.items():
        lanes.append({
            "lane": lane,
            "provider": t.get("provider"),
            "model": t.get("model"),
            "active": bool(t.get("active")),
            "credentials_ready": bool(t.get("credentials_ready")),
        })
    return {"lanes": lanes}


@router.get("/jarvis")
async def account_jarvis() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    if _current_role(user_id) != "owner":
        raise HTTPException(status_code=403, detail="Jarvis-indstillinger er kun for owner")
    from core.runtime.provider_router import (
        list_provider_router_targets,
        provider_router_lane_targets,
    )

    def _assemble() -> dict[str, Any]:
        ov = build_jarvis_overview(lane_targets=provider_router_lane_targets)
        opts = list_provider_router_targets(lane="visible")
        ov["visible_options"] = [
            {"provider": o.get("provider"), "model": o.get("model")} for o in opts
        ]
        return ov

    return await asyncio.to_thread(_assemble)


@router.post("/jarvis/visible-model")
async def account_set_visible_model(payload: dict = Body(default={})) -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    if _current_role(user_id) != "owner":
        raise HTTPException(status_code=403, detail="model-valg er kun for owner")
    provider = str((payload or {}).get("provider") or "").strip()
    model = str((payload or {}).get("model") or "").strip()
    if not provider or not model:
        return {"status": "error", "error": "provider og model er påkrævet"}
    import core.runtime.provider_router as pr

    def _apply() -> dict[str, Any]:
        opts = pr.list_provider_router_targets(lane="visible")
        valid = any(str(o.get("provider")) == provider and str(o.get("model")) == model for o in opts)
        if not valid:
            return {"status": "error", "error": "ukendt provider/model for visible-lane"}
        pr.select_main_agent_target(provider=provider, model=model)
        return {"status": "ok", "provider": provider, "model": model}

    return await asyncio.to_thread(_apply)


@router.get("/quota")
async def account_quota() -> dict[str, Any]:
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    return await asyncio.to_thread(build_quota_overview, user_id, check_quota=quota_store.check_quota)
