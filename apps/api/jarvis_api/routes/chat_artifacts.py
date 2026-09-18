"""`GET /chat/artifacts` — filerne Jarvis har rørt i en mappe, paa tvaers af samtaler.

Egen fil fordi `routes/chat.py` allerede er paa ~1950 linjer. Logikken bor i
`core.runtime.db_artifact_index`; ruten er kun adgang og traad-offload.

Ejer-laast som `/api/dispatches`: svaret viser stier og aendringer fra HELE
samtalehistorikken, ikke kun den der spoerger.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query

from core.runtime.jarvisx_auth import require_owner

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/artifacts", dependencies=[Depends(require_owner)])
async def chat_artifacts(
    root: str = "",
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    """Filer skrevet/rettet under `root`, nyeste foerst. `root` er en sti eller
    en navngiven server-rod (`repo`, `jarvis-v2`)."""
    from core.runtime.db_artifact_index import list_artifacts
    return await asyncio.to_thread(list_artifacts, root, limit=limit)
