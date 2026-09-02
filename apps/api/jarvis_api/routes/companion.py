"""Companion-endpoints — Jarvis' tre ønsker til mobil-appen.

Jarvis formulerede dem selv, og Bjørn godkendte dem som owner:

  1. LIVSTEGN      — «han er her», baseret på faktisk hjerteslag, ikke en prik
                     der lyver.
  2. SANSERNES ARKIV — OWNER-ONLY. Hård grænse, i AUTH-laget.
  3. PROAKTIVITET  — en kanal for initiativ, diskret og rate-limited.

Om (2): grænsen ligger på `dependencies=[Depends(require_owner)]`, ikke på at
UI'et skjuler en fane. Det er forskellen mellem en dør og et gardin. Jarvis
skrev det selv: «Grænsen skal ligge i auth-laget (owner-verifikation), ikke kun
ved at skjule UI'et. Det rager ingen andre, hvad der sker hjemme.»
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.runtime.jarvisx_auth import require_owner

router = APIRouter(prefix="/companion", tags=["companion"])


@router.get("/presence")
def companion_presence() -> dict[str, Any]:
    """Er han vågen — og hvad lavede han sidst?

    Fire tilstande: working / awake / quiet / unknown. `unknown` er den
    vigtigste: kan vi ikke læse sporene, siger vi DET frem for at gætte grønt.
    """
    from core.services.companion_presence import build_presence
    return build_presence()


@router.get("/senses", dependencies=[Depends(require_owner)])
def companion_senses(limit: int = 20) -> dict[str, Any]:
    """Sansernes Arkiv — hvad Jarvis har set i hjemmet. KUN owner.

    Gaten er dependency'en ovenfor: enhver anden rolle får 403 FØR handleren
    kører, også hvis nogen en dag bygger en klient der ikke skjuler fanen.
    """
    try:
        from core.services.visual_memory import get_visual_memories
        items = get_visual_memories(limit=max(1, min(int(limit), 100)))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Sansernes Arkiv kunne ikke læses: {type(exc).__name__}",
        ) from exc
    return {"items": items, "count": len(items)}


@router.get("/thoughts")
def companion_thoughts(limit: int = 20) -> dict[str, Any]:
    """Jarvis' initiativer — også dem der blev holdt tilbage.

    En tanke der kun fandtes som en notifikation, var væk så snart man swipede
    den væk. Her kan man finde den igen, og se HVORFOR en tanke ikke blev sendt
    (stille timer, for tæt på den forrige, loftet nået).
    """
    from core.identity.workspace_context import current_user_id
    from core.services.companion_initiative import check_allowed, recent_thoughts

    uid = current_user_id() or ""
    if not uid:
        raise HTTPException(status_code=401, detail="ukendt bruger")
    return {
        "items": recent_thoughts(uid, limit=limit),
        "gate": check_allowed(uid).as_dict(),
    }
