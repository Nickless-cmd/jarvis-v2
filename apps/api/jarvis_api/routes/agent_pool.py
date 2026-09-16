"""Agent-puljen — let liste, opsummering og seneste arbejde. Owner-only.

`/mc/agents` beriger HVER agent med fire ekstra opslag. Det er rigtigt naar man
kigger paa én agent og forkert naar man vil se listen: 306 agenter bliver til
over tolvhundrede forespoergsler, og der er hverken filter eller sideinddeling.
Disse tre svarer paa det foerste spoergsmaal med ét opslag; detaljen ligger
stadig i `/mc/agents/{id}`.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter

router = APIRouter(prefix="/mc/agent-pool", tags=["mc-agent-pool"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("")
async def liste(status: str = "", rolle: str = "", soeg: str = "",
                limit: int = 50, offset: int = 0) -> dict:
    """Agenterne med koerselstal. `status=aktive` daekker alle seks i-gang-statusser."""
    _require_owner()
    from core.services.agent_pool_surface import agent_liste
    return await asyncio.to_thread(agent_liste, status=status, rolle=rolle,
                                   soeg=soeg, limit=limit, offset=offset)


@router.get("/summary")
async def opsummering(timer: float = 24) -> dict:
    """Hvor mange, hvilke roller, hvad de kostede, og hvor graenserne gaar."""
    _require_owner()
    from core.services.agent_pool_surface import pool_opsummering
    return await asyncio.to_thread(pool_opsummering, timer=timer)


@router.get("/work")
async def arbejde(limit: int = 30) -> dict:
    """De nyeste koersler paa tvaers af agenter."""
    _require_owner()
    from core.services.agent_pool_surface import seneste_arbejde
    return await asyncio.to_thread(seneste_arbejde, limit=limit)
